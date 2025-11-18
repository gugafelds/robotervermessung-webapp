import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# In-Memory Task Store (für Production sollte Redis verwendet werden)
task_store: Dict[str, Dict] = {}


class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# In background_tasks.py - Korrektur für process_segment_similarity_background:

async def process_metadata_background(
        task_id: str,
        service,
        mode: str,
        bahn_ids: List[str],
        duplicate_handling: str
):
    """
    Background Task mit Batch-Processing (100 Bahnen auf einmal)
    """
    BATCH_SIZE = 100
    
    task_store[task_id] = {
        "status": TaskStatus.RUNNING,
        "started_at": datetime.now().isoformat(),
        "total_bahns": len(bahn_ids),
        "processed_bahns": 0,
        "successful_bahns": 0,
        "failed_bahns": 0,
        "current_bahn": None,
        "errors": [],
        "details": {"mode": mode, "duplicate_handling": duplicate_handling}
    }

    async with service.db_pool.acquire() as conn:
        try:
            logger.info(f"Starting task {task_id} for {len(bahn_ids)} bahns")

            # Duplikat-Behandlung
            if duplicate_handling == "replace":
                existing = await service.check_existing_bahns(bahn_ids)
                if existing:
                    await service.delete_existing_metadata(existing)
                    await service.delete_existing_embeddings(existing)
            elif duplicate_handling == "skip":
                existing = await service.check_existing_bahns(bahn_ids)
                bahn_ids = [b for b in bahn_ids if b not in existing]
                task_store[task_id]["total_bahns"] = len(bahn_ids)

            successful_results = []
            failed_results = []

            # ✅ Batch-Processing
            for batch_idx in range(0, len(bahn_ids), BATCH_SIZE):
                batch = bahn_ids[batch_idx:batch_idx + BATCH_SIZE]
                batch_metadata = []
                batch_embeddings = []
                
                # Verarbeite Batch
                for bahn_id in batch:
                    task_store[task_id]["current_bahn"] = bahn_id
                    
                    try:
                        result = await service.process_single_bahn(conn, bahn_id)
                        
                        if result.get('error'):
                            failed_results.append(result)
                            task_store[task_id]["failed_bahns"] += 1
                        else:
                            batch_metadata.extend(result['metadata'])
                            batch_embeddings.extend(result['embeddings'])
                            successful_results.append(result)
                            task_store[task_id]["successful_bahns"] += 1
                            
                    except Exception as e:
                        logger.error(f"Error {bahn_id}: {e}")
                        failed_results.append({"bahn_id": bahn_id, "error": str(e)})
                        task_store[task_id]["failed_bahns"] += 1
                    
                    task_store[task_id]["processed_bahns"] += 1
                
                # ✅ Schreibe kompletten Batch
                if batch_metadata or batch_embeddings:
                    await service.batch_write_everything(conn, batch_metadata, batch_embeddings)
                    logger.info(
                        f"✓ Batch {batch_idx//BATCH_SIZE + 1} done: "
                        f"{len(batch_metadata)} metadata, {len(batch_embeddings)} embeddings"
                    )

            # Task abschließen
            task_store[task_id].update({
                "status": TaskStatus.COMPLETED,
                "completed_at": datetime.now().isoformat(),
                "summary": {
                    "total_processed": len(bahn_ids),
                    "successful": len(successful_results),
                    "failed": len(failed_results)
                }
            })

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            task_store[task_id].update({
                "status": TaskStatus.FAILED,
                "failed_at": datetime.now().isoformat(),
                "error": str(e)
            })

def create_task_id(type) -> str:
    """Generiert eine eindeutige Task-ID"""
    return f"{type}_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"


def get_task_status(task_id: str) -> Optional[Dict]:
    """Holt den aktuellen Status einer Task"""
    return task_store.get(task_id)


def cleanup_old_tasks(max_age_hours: int = 24):
    """Entfernt alte Tasks aus dem Store"""
    current_time = datetime.now()
    to_remove = []

    for task_id, task_data in task_store.items():
        if "completed_at" in task_data or "failed_at" in task_data:
            # Parse completion time
            completion_time_str = task_data.get("completed_at") or task_data.get("failed_at")
            completion_time = datetime.fromisoformat(completion_time_str)

            # Check if older than max_age_hours
            age_hours = (current_time - completion_time).total_seconds() / 3600
            if age_hours > max_age_hours:
                to_remove.append(task_id)

    for task_id in to_remove:
        del task_store[task_id]

    if to_remove:
        logger.info(f"Cleaned up {len(to_remove)} old tasks")


def get_all_tasks() -> Dict[str, Dict]:
    """Holt alle Tasks (für Admin/Debugging)"""
    return dict(task_store)


def find_running_task(task_type: str, target_bahn_id: str = None, **kwargs) -> Optional[str]:
    """
    Sucht nach bereits laufenden Tasks für gleiche Parameter

    Args:
        task_type: Art des Tasks ("segment_similarity", "metadata_calculation", etc.)
        target_bahn_id: Bahn-ID für Segment-Tasks
        **kwargs: Weitere Parameter je nach Task-Type

    Returns:
        task_id falls laufender Task gefunden, sonst None
    """
    for task_id, task_data in task_store.items():
        if task_data["status"] in [TaskStatus.PENDING, TaskStatus.RUNNING]:

            # Segment Similarity Tasks
            if (task_type == "segment_similarity" and
                    task_data.get("task_type") == "segment_similarity" and
                    task_data.get("target_bahn_id") == target_bahn_id):
                return task_id

            # Metadata Calculation Tasks
            elif (task_type == "metadata_calculation" and
                  task_data.get("details", {}).get("mode") is not None):  # Hat metadata structure
                mode = kwargs.get("mode")
                bahn_id = kwargs.get("bahn_id")

                task_mode = task_data.get("details", {}).get("mode")
                task_bahn_id = task_data.get("details", {}).get("bahn_id")

                # Prüfe je nach Mode
                if mode == "single" and task_mode == "single" and task_bahn_id == bahn_id:
                    return task_id
                elif mode == "all_missing" and task_mode == "all_missing":
                    return task_id
                elif mode == "timerange" and task_mode == "timerange":
                    # Bei timerange könnten wir auch start/end_time vergleichen
                    return task_id

            # Meta Values Tasks (global, nur ein Task zur Zeit)
            elif (task_type == "meta_values" and
                  task_data.get("total_rows") is not None):  # Hat meta_values structure
                return task_id

    return None