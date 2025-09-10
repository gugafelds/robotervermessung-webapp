from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, field_validator
from ...database import get_db_pool, get_db
from ...utils.metadata_calculator import MetadataCalculatorService
from ...utils.background_tasks import (
    process_metadata_background,
    process_meta_values_calculation,
    create_task_id,
    get_task_status,
    cleanup_old_tasks,
    get_all_tasks,
    TaskStatus
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic Models
class MetadataCalculationRequest(BaseModel):
    mode: str  # "single", "timerange", "all_missing"
    bahn_id: Optional[str] = None
    start_time: Optional[str] = None  # Format: "26.06.2025 12:12:10"
    end_time: Optional[str] = None
    duplicate_handling: str = "skip"  # "replace" oder "skip"
    batch_size: int = 10

    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        if v not in ['single', 'timerange', 'all_missing']:
            raise ValueError('mode must be one of: single, timerange, all_missing')
        return v

    @field_validator('duplicate_handling')
    @classmethod
    def validate_duplicate_handling(cls, v):
        if v not in ['replace', 'skip']:
            raise ValueError('duplicate_handling must be either "replace" or "skip"')
        return v

    @field_validator('batch_size')
    @classmethod
    def validate_batch_size(cls, v):
        if v < 1 or v > 100:
            raise ValueError('batch_size must be between 1 and 100')
        return v

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    total_bahns: int = 0
    processed_bahns: int = 0
    successful_bahns: int = 0
    failed_bahns: int = 0
    current_bahn: Optional[str] = None
    progress_percent: float = 0.0
    errors: List[str] = []
    details: dict = {}
    summary: Optional[dict] = None
    error: Optional[str] = None


class MetadataCalculationResponse(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_duration_minutes: Optional[float] = None

############################ METADATA BERECHNEN #################################################################

@router.post("/calculate-metadata", response_model=MetadataCalculationResponse)
async def calculate_metadata(
        request: MetadataCalculationRequest,
        background_tasks: BackgroundTasks,
        db_pool=Depends(get_db_pool)
):
    """
    Startet die Berechnung von Bahn-Metadaten als Background Task
    """
    try:
        # Cleanup alte Tasks
        cleanup_old_tasks()

        # Service initialisieren
        service = MetadataCalculatorService(db_pool)

        # Bahn-IDs ermitteln basierend auf Modus
        bahn_ids = []

        if request.mode == "single":
            bahn_ids = [request.bahn_id]
            logger.info(f"Processing single bahn: {request.bahn_id}")

        elif request.mode == "timerange":
            # Validiere und konvertiere Zeitangaben
            start_unix = await service.validate_datetime_input(request.start_time)
            end_unix = await service.validate_datetime_input(request.end_time)

            if start_unix is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid start_time format. Expected: DD.MM.YYYY HH:MM:SS, got: {request.start_time}"
                )
            if end_unix is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_time format. Expected: DD.MM.YYYY HH:MM:SS, got: {request.end_time}"
                )
            if end_unix <= start_unix:
                raise HTTPException(
                    status_code=400,
                    detail="end_time must be after start_time"
                )

            bahn_ids = await service.get_bahn_ids_for_timerange(start_unix, end_unix)
            logger.info(f"Found {len(bahn_ids)} bahns in timerange {request.start_time} - {request.end_time}")

        elif request.mode == "all_missing":
            bahn_ids = await service.get_all_missing_bahn_ids()
            logger.info(f"Found {len(bahn_ids)} bahns without metadata")

        if not bahn_ids:
            return MetadataCalculationResponse(
                task_id="",
                status="completed",
                message="No bahns found to process"
            )

        # Task-ID generieren
        task_id = create_task_id()

        # Geschätzte Dauer berechnen (ca. 0.5-2 Sekunden pro Bahn)
        estimated_seconds = len(bahn_ids) * 1.0  # Durchschnitt 1 Sekunde pro Bahn
        estimated_minutes = estimated_seconds / 60

        # Background Task starten
        background_tasks.add_task(
            process_metadata_background,
            task_id=task_id,
            service=service,
            mode=request.mode,
            bahn_ids=bahn_ids,
            duplicate_handling=request.duplicate_handling,
            batch_size=request.batch_size
        )

        logger.info(f"Started background task {task_id} for {len(bahn_ids)} bahns")

        return MetadataCalculationResponse(
            task_id=task_id,
            status="started",
            message=f"Started processing {len(bahn_ids)} bahns in background",
            estimated_duration_minutes=round(estimated_minutes, 1)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting metadata calculation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status_endpoint(task_id: str):
    """
    Holt den aktuellen Status einer Background Task
    """
    task_data = get_task_status(task_id)

    if not task_data:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Progress berechnen
    progress_percent = 0.0
    if task_data.get("total_bahns", 0) > 0:
        progress_percent = (task_data.get("processed_bahns", 0) / task_data["total_bahns"]) * 100

    return TaskStatusResponse(
        task_id=task_id,
        status=task_data.get("status", "unknown"),
        started_at=task_data.get("started_at"),
        completed_at=task_data.get("completed_at"),
        failed_at=task_data.get("failed_at"),
        total_bahns=task_data.get("total_bahns", 0),
        processed_bahns=task_data.get("processed_bahns", 0),
        successful_bahns=task_data.get("successful_bahns", 0),
        failed_bahns=task_data.get("failed_bahns", 0),
        current_bahn=task_data.get("current_bahn"),
        progress_percent=round(progress_percent, 1),
        errors=task_data.get("errors", []),
        details=task_data.get("details", {}),
        summary=task_data.get("summary"),
        error=task_data.get("error")
    )


@router.get("/tasks")
async def list_all_tasks():
    """
    Listet alle Tasks auf (für Admin/Debugging)
    """
    tasks = get_all_tasks()

    # Formatiere für bessere Übersicht
    formatted_tasks = {}
    for task_id, task_data in tasks.items():
        progress_percent = 0.0
        if task_data.get("total_bahns", 0) > 0:
            progress_percent = (task_data.get("processed_bahns", 0) / task_data["total_bahns"]) * 100

        formatted_tasks[task_id] = {
            "status": task_data.get("status"),
            "started_at": task_data.get("started_at"),
            "progress": f"{progress_percent:.1f}%",
            "bahns": f"{task_data.get('processed_bahns', 0)}/{task_data.get('total_bahns', 0)}",
            "success_rate": f"{task_data.get('successful_bahns', 0)}/{task_data.get('processed_bahns', 0)}" if task_data.get(
                'processed_bahns', 0) > 0 else "0/0"
        }

    return {
        "total_tasks": len(tasks),
        "tasks": formatted_tasks
    }

@router.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """
    Bricht eine laufende Task ab (falls möglich)
    """
    task_data = get_task_status(task_id)

    if not task_data:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task_data.get("status") == TaskStatus.RUNNING:
        # Task als cancelled markieren
        task_data["status"] = "cancelled"
        task_data["cancelled_at"] = datetime.now().isoformat()

        return {"message": f"Task {task_id} marked for cancellation"}

    return {"message": f"Task {task_id} is not running (status: {task_data.get('status')})"}


@router.post("/cleanup-tasks")
async def cleanup_tasks_endpoint(max_age_hours: int = 24):
    """
    Bereinigt alte Tasks
    """
    initial_count = len(get_all_tasks())
    cleanup_old_tasks(max_age_hours)
    final_count = len(get_all_tasks())

    return {
        "message": f"Cleaned up {initial_count - final_count} old tasks",
        "remaining_tasks": final_count
    }

@router.get("/metadata-stats")
async def get_metadata_stats(db_pool=Depends(get_db_pool)):
    """
    Zeigt Statistiken über vorhandene Metadaten
    """
    try:
        async with db_pool.acquire() as conn:
            # Gesamtzahl Bahnen
            total_bahns_query = """
                                SELECT COUNT(DISTINCT bahn_id) as total_bahns
                                FROM robotervermessung.bewegungsdaten.bahn_info \
                                """
            total_bahns = await conn.fetchval(total_bahns_query)

            # Bahnen mit Metadaten
            bahns_with_metadata_query = """
                                        SELECT COUNT(DISTINCT bahn_id) as bahns_with_metadata
                                        FROM robotervermessung.bewegungsdaten.bahn_meta
                                        WHERE segment_id = bahn_id -- Nur Gesamtbahn-Zeilen zählen \
                                        """
            bahns_with_metadata = await conn.fetchval(bahns_with_metadata_query)

            # Gesamtzahl Metadaten-Zeilen
            total_metadata_rows_query = """
                                        SELECT COUNT(*) as total_rows
                                        FROM robotervermessung.bewegungsdaten.bahn_meta \
                                        """
            total_metadata_rows = await conn.fetchval(total_metadata_rows_query)

            # Movement Type Verteilung
            movement_type_query = """
                                  SELECT movement_type, COUNT(*) as count
                                  FROM robotervermessung.bewegungsdaten.bahn_meta
                                  WHERE segment_id != bahn_id -- Nur Segmente, nicht Gesamtbahn
                                  GROUP BY movement_type
                                  ORDER BY count DESC \
                                  """
            movement_types = await conn.fetch(movement_type_query)

            missing_bahns = total_bahns - bahns_with_metadata
            coverage_percent = (bahns_with_metadata / total_bahns * 100) if total_bahns > 0 else 0

            return {
                "total_bahns": total_bahns,
                "bahns_with_metadata": bahns_with_metadata,
                "missing_metadata": missing_bahns,
                "coverage_percent": round(coverage_percent, 1),
                "total_metadata_rows": total_metadata_rows,
                "movement_type_distribution": [dict(row) for row in movement_types]
            }

    except Exception as e:
        logger.error(f"Error getting metadata stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available-dates")
async def get_available_dates(db_pool=Depends(get_db_pool)):
    """
    Ermittelt verfügbare recording_dates aus bahn_info (nur Datum)
    """
    try:
        async with db_pool.acquire() as conn:
            query = """
                    SELECT DISTINCT LEFT (recording_date, 10) as date
                    FROM robotervermessung.bewegungsdaten.bahn_info
                    WHERE recording_date IS NOT NULL
                    ORDER BY LEFT (recording_date, 10) DESC \
                    """

            rows = await conn.fetch(query)

            available_dates = []
            for row in rows:
                available_dates.append({
                    "date": row['date'],  # z.B. "2024-07-02"
                })

            return {"available_dates": available_dates}

    except Exception as e:
        logger.error(f"Error getting available dates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


############################ METAVALUES BERECHNEN #################################################################

@router.get("/meta-values-status")
async def get_meta_values_status(conn=Depends(get_db)):
    """Prüft Status der Meta-Values"""
    try:
        query = """
                SELECT COUNT(*)          as total_rows, \
                       COUNT(meta_value) as meta_values_count, \
                       AVG(meta_value)   as avg_meta_value, \
                       MIN(meta_value)   as min_meta_value, \
                       MAX(meta_value)   as max_meta_value
                FROM robotervermessung.bewegungsdaten.bahn_meta bm \
                WHERE bm.duration IS NOT NULL
                    AND bm.weight IS NOT NULL
                    AND bm.length IS NOT NULL
                """

        result = await conn.fetchrow(query)

        has_meta_values = result['meta_values_count'] > 0
        completion_rate = (result['meta_values_count'] / result['total_rows'] * 100) if result['total_rows'] > 0 else 0

        return {
            "has_meta_values": has_meta_values,
            "total_rows": int(result['total_rows']),
            "meta_values_count": int(result['meta_values_count']),
            "completion_rate": round(completion_rate, 1),
            "avg_meta_value": float(result['avg_meta_value']) if result['avg_meta_value'] else None,
            "min_meta_value": float(result['min_meta_value']) if result['min_meta_value'] else None,
            "max_meta_value": float(result['max_meta_value']) if result['max_meta_value'] else None
        }

    except Exception as e:
        logger.error(f"Error checking meta values status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available-parameters")
def get_available_parameters():
    """Gibt verfügbare Parameter zurück"""
    return {
        'basic': ['duration', 'weight', 'length', 'movement_type'],
        'direction': ['direction_x', 'direction_y', 'direction_z'],
        'position_soll': [
            'min_position_x_soll', 'min_position_y_soll', 'min_position_z_soll',
            'max_position_x_soll', 'max_position_y_soll', 'max_position_z_soll'
        ],
        'orientation_soll': [
            'min_orientation_qw_soll', 'min_orientation_qx_soll', 'min_orientation_qy_soll', 'min_orientation_qz_soll',
            'max_orientation_qw_soll', 'max_orientation_qx_soll', 'max_orientation_qy_soll', 'max_orientation_qz_soll'
        ],
        'twist_ist': ['min_twist_ist', 'max_twist_ist', 'median_twist_ist', 'std_twist_ist'],
        'acceleration_ist': ['min_acceleration_ist', 'max_acceleration_ist', 'median_acceleration_ist',
                             'std_acceleration_ist'],
        'joints': [
            'min_states_joint_1', 'min_states_joint_2', 'min_states_joint_3',
            'min_states_joint_4', 'min_states_joint_5', 'min_states_joint_6',
            'max_states_joint_1', 'max_states_joint_2', 'max_states_joint_3',
            'max_states_joint_4', 'max_states_joint_5', 'max_states_joint_6'
        ]
    }

@router.post("/calculate-meta-values")
async def calculate_meta_values(
        background_tasks: BackgroundTasks,
        db_pool=Depends(get_db_pool)
):
    """Startet Meta-Values Berechnung als Background Task"""
    try:
        # Cleanup alte Tasks
        cleanup_old_tasks()

        # Task-ID generieren
        task_id = create_task_id()

        # Geschätzte Anzahl Rows ermitteln
        async with db_pool.acquire() as conn:
            count_query = """
                          SELECT COUNT(*) as total_rows
                          FROM robotervermessung.bewegungsdaten.bahn_meta bm
                          WHERE bm.duration IS NOT NULL 
                            AND bm.weight IS NOT NULL
                            AND bm.length IS NOT NULL
                          """
            total_rows = await conn.fetchval(count_query)

        if total_rows == 0:
            return {
                "status": "completed",
                "message": "Keine gültigen Daten in bahn_meta gefunden",
                "task_id": "",
                "processed_rows": 0
            }

        # Geschätzte Dauer (sehr schnell, da optimiert)
        estimated_seconds = total_rows * 0.001  # 1ms pro Row
        estimated_minutes = estimated_seconds / 60

        # Background Task starten
        background_tasks.add_task(
            process_meta_values_calculation,
            task_id=task_id,
            db_pool=db_pool
        )

        logger.info(f"Started meta-values background task {task_id} for {total_rows} rows")

        return {
            "status": "started",
            "message": f"Meta-Values Berechnung gestartet für {total_rows} Datensätze",
            "task_id": task_id,
            "estimated_duration_minutes": round(estimated_minutes, 2),
            "total_rows": total_rows
        }

    except Exception as e:
        logger.error(f"Error starting meta-values calculation: {e}")
        raise HTTPException(status_code=500, detail=str(e))