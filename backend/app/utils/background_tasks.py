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


async def process_meta_values_calculation(task_id: str, db_pool):
    """
    Background Task für Meta-Values Berechnung - genau wie die ursprüngliche Route
    """
    # Task Status initialisieren (wie bei metadata)
    task_store[task_id] = {
        "status": TaskStatus.RUNNING,
        "started_at": datetime.now().isoformat(),
        "message": "Starting optimized Meta-Values calculation...",
        "total_rows": 0,
        "processed_rows": 0
    }

    try:
        async with db_pool.acquire() as conn:
            logger.info("Starting optimized Meta-Values calculation...")

            # Standard-Parameter und Gewichtungen (genau wie vorher)
            selected_parameters = {
                'duration', 'weight', 'length', 'movement_type',
                'direction_x', 'direction_y', 'direction_z'
            }
            weights = {
                'duration': 1.0, 'weight': 1.0, 'length': 1.0, 'movement_type': 1.0,
                'direction_x': 1.0, 'direction_y': 1.0, 'direction_z': 1.0
            }

            # OPTIMIERUNG 1: Nur Spalten laden, die wir brauchen
            numeric_columns = [
                'duration', 'weight', 'length',
                'direction_x', 'direction_y', 'direction_z'
            ]

            # OPTIMIERUNG 2: Simplified Query ohne LEFT JOIN
            columns_str = ', '.join(['bm.' + col for col in numeric_columns])
            query = f"""
                    SELECT bm.bahn_id,
                           bm.segment_id,
                           {columns_str}
                    FROM robotervermessung.bewegungsdaten.bahn_meta bm
                    WHERE bm.duration IS NOT NULL 
                      AND bm.weight IS NOT NULL
                      AND bm.length IS NOT NULL
                    """

            task_store[task_id]["message"] = "Loading data from database..."

            rows = await conn.fetch(query)
            if not rows:
                task_store[task_id].update({
                    "status": TaskStatus.FAILED,
                    "failed_at": datetime.now().isoformat(),
                    "error": "Keine gültigen Daten in bahn_meta gefunden"
                })
                return

            total_rows = len(rows)
            task_store[task_id].update({
                "total_rows": total_rows,
                "message": f"Processing {total_rows} rows..."
            })

            logger.info(f"Gefunden: {len(rows)} Datensätze mit vollständigen Daten")

            # OPTIMIERUNG 3: Direkte NumPy Array Erstellung
            import numpy as np
            from sklearn.preprocessing import StandardScaler

            task_store[task_id]["message"] = "Creating data matrix and calculating meta-values..."

            # Erstelle Data Matrix direkt
            data_matrix = np.array([
                [float(row[col]) if row[col] is not None else 0.0 for col in numeric_columns]
                for row in rows
            ])

            # OPTIMIERUNG 4: Batch Normalisierung
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(data_matrix)

            # OPTIMIERUNG 5: Vectorized Meta-Value Berechnung
            weight_vector = np.array([weights.get(col, 1.0) for col in numeric_columns])
            abs_scaled = np.abs(scaled_data)
            weighted_sums = abs_scaled @ weight_vector

            # Movement type handling (falls benötigt)
            if 'movement_type' in selected_parameters:
                movement_weight = weights.get('movement_type', 1.0)
                # Vectorized movement type processing
                movement_scores = np.array([
                    (len(str(row.get('movement_type', ''))) / 10.0 +
                     (0.5 if 'c' in str(row.get('movement_type', '')).lower() else 0) +
                     (0.3 if 's' in str(row.get('movement_type', '')).lower() else 0))
                    for row in rows
                ])
                weighted_sums += movement_scores * movement_weight
                total_weight = weight_vector.sum() + movement_weight
            else:
                total_weight = weight_vector.sum()

            meta_values = weighted_sums / total_weight if total_weight > 0 else weighted_sums

            logger.info(f"Meta-Value Statistiken: Min={meta_values.min():.6f}, "
                        f"Max={meta_values.max():.6f}, Avg={meta_values.mean():.6f}")

            # OPTIMIERUNG 6: Direct SQL UPDATE
            task_store[task_id]["message"] = "Updating database with calculated meta-values..."

            async with conn.transaction():
                # Bereite Update-Values vor
                update_values = [
                    (float(meta_values[i]), str(row['bahn_id']), str(row['segment_id']))
                    for i, row in enumerate(rows)
                ]

                # OPTIMIERUNG 7: Simplified UPDATE Logic
                await conn.executemany("""
                                       UPDATE robotervermessung.bewegungsdaten.bahn_meta
                                       SET meta_value = CAST(ROUND($1::numeric, 4) AS DOUBLE PRECISION)
                                       WHERE bahn_id = $2
                                         AND segment_id = $3
                                       """, update_values)

            logger.info(f"Meta-Value Berechnung abgeschlossen: {len(rows)} Datensätze aktualisiert")

            # Task als completed markieren
            task_store[task_id].update({
                "status": TaskStatus.COMPLETED,
                "completed_at": datetime.now().isoformat(),
                "message": f"Meta-Values erfolgreich berechnet für {len(rows)} Datensätze",
                "summary": {
                    "processed_rows": len(rows),
                    "parameters_used": list(selected_parameters),
                    "stats": {
                        "min_meta_value": float(meta_values.min()),
                        "max_meta_value": float(meta_values.max()),
                        "avg_meta_value": float(meta_values.mean())
                    }
                }
            })

    except Exception as e:
        logger.error(f"Meta-values task {task_id} failed: {str(e)}")
        task_store[task_id].update({
            "status": TaskStatus.FAILED,
            "failed_at": datetime.now().isoformat(),
            "error": str(e),
            "message": f"Meta-values calculation failed: {str(e)}"
        })

async def process_metadata_background(
        task_id: str,
        service,  # MetadataCalculatorService instance
        mode: str,
        bahn_ids: List[str],
        duplicate_handling: str,
        batch_size: int = 10
):
    """
    Background Task für die Metadaten-Verarbeitung
    """

    # Task Status initialisieren
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
            "batch_size": batch_size
        }
    }

    try:
        logger.info(f"Starting background task {task_id} for {len(bahn_ids)} bahns")

        # Duplikat-Behandlung
        if duplicate_handling == "replace":
            existing_bahns = await service.check_existing_bahns(bahn_ids)
            if existing_bahns:
                deleted_count = await service.delete_existing_metadata(existing_bahns)
                logger.info(f"Deleted {deleted_count} existing metadata rows")
                task_store[task_id]["details"]["deleted_existing"] = deleted_count

        elif duplicate_handling == "skip":
            existing_bahns = await service.check_existing_bahns(bahn_ids)
            bahn_ids = [bid for bid in bahn_ids if bid not in existing_bahns]
            task_store[task_id]["details"]["skipped_existing"] = len(existing_bahns)
            task_store[task_id]["total_bahns"] = len(bahn_ids)
            logger.info(f"Skipping {len(existing_bahns)} existing bahns, processing {len(bahn_ids)} new ones")

        # Verarbeitung in Batches
        successful_results = []
        failed_results = []

        for i in range(0, len(bahn_ids), batch_size):
            batch = bahn_ids[i:i + batch_size]
            batch_tasks = []

            for bahn_id in batch:
                task_store[task_id]["current_bahn"] = bahn_id
                batch_tasks.append(service.process_single_bahn(bahn_id))

            # Batch parallel verarbeiten
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for j, result in enumerate(batch_results):
                bahn_id = batch[j]
                task_store[task_id]["processed_bahns"] += 1

                if isinstance(result, Exception):
                    logger.error(f"Exception processing bahn_id {bahn_id}: {result}")
                    failed_results.append({
                        "bahn_id": bahn_id,
                        "error": str(result)
                    })
                    task_store[task_id]["failed_bahns"] += 1
                    task_store[task_id]["errors"].append(f"bahn_id {bahn_id}: {str(result)}")

                elif result and result.get("success"):
                    successful_results.append(result)
                    task_store[task_id]["successful_bahns"] += 1
                    logger.debug(f"Successfully processed bahn_id {bahn_id}")

                else:
                    error_msg = result.get("error", "Unknown error") if result else "No result returned"
                    failed_results.append({
                        "bahn_id": bahn_id,
                        "error": error_msg
                    })
                    task_store[task_id]["failed_bahns"] += 1
                    task_store[task_id]["errors"].append(f"bahn_id {bahn_id}: {error_msg}")

            # Progress Update
            progress = (task_store[task_id]["processed_bahns"] / task_store[task_id]["total_bahns"]) * 100
            logger.info(
                f"Task {task_id} progress: {progress:.1f}% ({task_store[task_id]['processed_bahns']}/{task_store[task_id]['total_bahns']})")

            # Kurze Pause zwischen Batches
            if i + batch_size < len(bahn_ids):
                await asyncio.sleep(0.1)

        # Task erfolgreich abgeschlossen
        task_store[task_id].update({
            "status": TaskStatus.COMPLETED,
            "completed_at": datetime.now().isoformat(),
            "current_bahn": None,
            "summary": {
                "total_processed": len(successful_results) + len(failed_results),
                "successful": len(successful_results),
                "failed": len(failed_results),
                "success_rate": (len(successful_results) / len(bahn_ids)) * 100 if bahn_ids else 0
            }
        })

        logger.info(
            f"Task {task_id} completed successfully. {len(successful_results)}/{len(bahn_ids)} bahns processed successfully")

    except Exception as e:
        logger.error(f"Task {task_id} failed with error: {e}")
        task_store[task_id].update({
            "status": TaskStatus.FAILED,
            "failed_at": datetime.now().isoformat(),
            "error": str(e)
        })

def create_task_id() -> str:
    """Generiert eine eindeutige Task-ID"""
    return f"metadata_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"


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