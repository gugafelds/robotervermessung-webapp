from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from ...database import get_db
from pydantic import BaseModel
from ...database import get_db_pool
from ...utils.metadata_calculator import MetadataCalculatorService
from ...utils.background_tasks import (
    process_segment_similarity_background,
    process_metadata_background,
    create_task_id,
    get_task_status,
    cleanup_old_tasks,
    get_all_tasks,
    TaskStatus, find_running_task
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
    duplicate_handling: str = "replace"  # "replace" oder "skip"

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
    results: Optional[List[dict]] = None
    error: Optional[str] = None


class MetadataCalculationResponse(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_duration_minutes: Optional[float] = None

class SegmentSimilarityRequest(BaseModel):
    segment_limit: int = 5
    weight_duration: float = 1.0
    weight_weight: float = 1.0
    weight_length: float = 1.0
    weight_movement_type: float = 1.0
    weight_direction_x: float = 1.0
    weight_direction_y: float = 1.0
    weight_direction_z: float = 1.0

############################ METADATA BERECHNEN #################################################################

@router.post("/calculate-metadata", response_model=MetadataCalculationResponse)
async def calculate_metadata(
        request: MetadataCalculationRequest,
        background_tasks: BackgroundTasks,
        db_pool=Depends(get_db_pool)
):
    """
    Startet die Berechnung von Bahn-Metadaten als Background Task
    Mit Duplikat-Prüfung
    """
    try:
        # Cleanup alte Tasks
        cleanup_old_tasks()

        # DUPLIKAT-PRÜFUNG für Metadata-Tasks
        existing_task = find_running_task(
            "metadata_calculation",
            mode=request.mode,
            bahn_id=request.bahn_id if request.mode == "single" else None
        )
        if existing_task:
            logger.info(f"Metadata-Task für Mode {request.mode} läuft bereits: {existing_task}")
            return MetadataCalculationResponse(
                task_id=existing_task,
                status="already_running",
                message=f"Metadata-Berechnung für {request.mode} läuft bereits"
            )

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
        task_id = create_task_id("metadata")

        # Geschätzte Dauer berechnen (ca. 0.5-2 Sekunden pro Bahn)
        estimated_seconds = len(bahn_ids) * 0.3  # Durchschnitt 1 Sekunde pro Bahn
        estimated_minutes = estimated_seconds / 60

        # Background Task starten
        background_tasks.add_task(
            process_metadata_background,
            task_id=task_id,
            service=service,
            mode=request.mode,
            bahn_ids=bahn_ids,
            duplicate_handling=request.duplicate_handling,
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

    # Progress berechnen - flexibel für Bahn- und Segment-Tasks
    progress_percent = 0.0
    total_items = 0
    processed_items = 0

    # Prüfe Task-Typ anhand vorhandener Felder
    if task_data.get("total_bahns", 0) > 0:
        # Bahn-Task
        total_items = task_data.get("total_bahns", 0)
        processed_items = task_data.get("processed_bahns", 0)
    elif task_data.get("total_segments", 0) > 0:
        # Segment-Task
        total_items = task_data.get("total_segments", 0)
        processed_items = task_data.get("processed_segments", 0)

    if total_items > 0:
        progress_percent = (processed_items / total_items) * 100

    return TaskStatusResponse(
        task_id=task_id,
        status=task_data.get("status", "unknown"),
        started_at=task_data.get("started_at"),
        completed_at=task_data.get("completed_at"),
        failed_at=task_data.get("failed_at"),
        total_bahns=total_items,
        processed_bahns=processed_items,
        successful_bahns=task_data.get("successful_bahns") or task_data.get("successful_segments", 0),
        failed_bahns=task_data.get("failed_bahns") or task_data.get("failed_segments", 0),
        current_bahn=task_data.get("current_bahn") or task_data.get("current_segment"),
        progress_percent=round(progress_percent, 1),
        errors=task_data.get("errors", []),
        details=task_data.get("details", {}),
        summary=task_data.get("summary"),
        results=task_data.get("results"),
        error=task_data.get("error")
    )


@router.get("/tasks")
async def list_all_tasks():
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
                                        FROM robotervermessung.bewegungsdaten.bahn_metadata
                                        WHERE segment_id = bahn_id -- Nur Gesamtbahn-Zeilen zählen \
                                        """
            bahns_with_metadata = await conn.fetchval(bahns_with_metadata_query)

            # Gesamtzahl Metadaten-Zeilen
            total_metadata_rows_query = """
                                        SELECT COUNT(*) as total_rows
                                        FROM robotervermessung.bewegungsdaten.bahn_metadata \
                                        """
            total_metadata_rows = await conn.fetchval(total_metadata_rows_query)

            # Movement Type Verteilung
            movement_type_query = """
                                  SELECT movement_type, COUNT(*) as count
                                  FROM robotervermessung.bewegungsdaten.bahn_metadata
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