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
    ✅ ERWEITERT: Prüft Metadata UND Embeddings separat
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
        "details": {
            "mode": mode, 
            "duplicate_handling": duplicate_handling,
            "metadata_written": 0,
            "embeddings_written": 0
        }
    }

    async with service.db_pool.acquire() as conn:
        try:
            logger.info(f"Starting task {task_id} for {len(bahn_ids)} bahns")

            # ✅ SCHRITT 1: Prüfe welche Bahnen Metadata/Embeddings brauchen
            bahns_needing_metadata = []
            bahns_needing_embeddings = []

            if duplicate_handling == "replace":
                # Replace: Alles neu berechnen
                existing_metadata = await service.check_existing_bahns(bahn_ids)
                existing_embeddings = existing_metadata  # Gleiche Liste
                
                if existing_metadata:
                    await service.delete_existing_metadata(existing_metadata)
                    await service.delete_existing_embeddings(existing_embeddings)
                
                bahns_needing_metadata = bahn_ids
                bahns_needing_embeddings = bahn_ids
                
            elif duplicate_handling == "skip":
                # ✅ Skip: Prüfe separat für Metadata und Embeddings
                existing_metadata = await service.check_existing_bahns(bahn_ids)
                bahns_needing_metadata = [b for b in bahn_ids if b not in existing_metadata]
                
                # Prüfe welche Bahnen Embeddings fehlen
                existing_embeddings = await service.check_existing_embeddings(bahn_ids)
                bahns_needing_embeddings = [b for b in bahn_ids if b not in existing_embeddings]
                
            else:  # append (default)
                bahns_needing_metadata = bahn_ids
                bahns_needing_embeddings = bahn_ids

            # Kombiniere: Alle Bahnen die IRGENDWAS brauchen
            all_bahns_to_process = list(set(bahns_needing_metadata + bahns_needing_embeddings))
            
            task_store[task_id]["total_bahns"] = len(all_bahns_to_process)
            task_store[task_id]["details"]["bahns_needing_metadata"] = len(bahns_needing_metadata)
            task_store[task_id]["details"]["bahns_needing_embeddings"] = len(bahns_needing_embeddings)

            logger.info(
                f"Task {task_id}: {len(bahns_needing_metadata)} need metadata, "
                f"{len(bahns_needing_embeddings)} need embeddings"
            )

            successful_results = []
            failed_results = []

            # ✅ SCHRITT 2: Batch-Processing
            for batch_idx in range(0, len(all_bahns_to_process), BATCH_SIZE):
                batch = all_bahns_to_process[batch_idx:batch_idx + BATCH_SIZE]
                batch_metadata = []
                batch_embeddings = []
                
                for bahn_id in batch:
                    task_store[task_id]["current_bahn"] = bahn_id
                    
                    needs_metadata = bahn_id in bahns_needing_metadata
                    needs_embeddings = bahn_id in bahns_needing_embeddings
                    
                    try:
                        # Verarbeite mit Flag was benötigt wird
                        result = await service.process_single_bahn(
                            conn, bahn_id, 
                            compute_metadata=needs_metadata,
                            compute_embeddings=needs_embeddings
                        )
                        
                        if result.get('error'):
                            failed_results.append(result)
                            task_store[task_id]["failed_bahns"] += 1
                        else:
                            # Nur hinzufügen was auch berechnet wurde
                            if needs_metadata and result.get('metadata'):
                                batch_metadata.extend(result['metadata'])
                            if needs_embeddings and result.get('embeddings'):
                                batch_embeddings.extend(result['embeddings'])
                            
                            successful_results.append(result)
                            task_store[task_id]["successful_bahns"] += 1
                            
                    except Exception as e:
                        logger.error(f"Error {bahn_id}: {e}")
                        failed_results.append({"bahn_id": bahn_id, "error": str(e)})
                        task_store[task_id]["failed_bahns"] += 1
                    
                    task_store[task_id]["processed_bahns"] += 1
                
                # ✅ Schreibe Batch (nur was vorhanden ist)
                if batch_metadata:
                    await service.batch_write_metadata(conn, batch_metadata)
                    task_store[task_id]["details"]["metadata_written"] += len(batch_metadata)
                
                if batch_embeddings:
                    await service.batch_write_embeddings(conn, batch_embeddings)
                    task_store[task_id]["details"]["embeddings_written"] += len(batch_embeddings)
                
                logger.info(
                    f"✓ Batch {batch_idx//BATCH_SIZE + 1}: "
                    f"{len(batch_metadata)} metadata, {len(batch_embeddings)} embeddings"
                )

            # Task abschließen
            task_store[task_id].update({
                "status": TaskStatus.COMPLETED,
                "completed_at": datetime.now().isoformat(),
                "summary": {
                    "total_processed": len(all_bahns_to_process),
                    "successful": len(successful_results),
                    "failed": len(failed_results),
                    "metadata_rows": task_store[task_id]["details"]["metadata_written"],
                    "embedding_rows": task_store[task_id]["details"]["embeddings_written"]
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