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

async def process_segment_similarity_background(
        task_id: str,
        target_bahn_id: str,
        segment_limit: int,
        weights: Dict[str, float],
        total_segments: int
):
    """
    Background Task für Segment-Ähnlichkeitssuche mit Live Progress Updates
    """
    from ..database import get_db_pool
    from ..utils.similarity_searcher import SimilaritySearcher
    from datetime import datetime
    import traceback
    import asyncio

    # Task initialisieren
    task_data = {
        "task_id": task_id,
        "status": TaskStatus.RUNNING,
        "started_at": datetime.now().isoformat(),
        "task_type": "segment_similarity",
        "target_bahn_id": target_bahn_id,
        "total_segments": total_segments,
        "processed_segments": 0,
        "successful_segments": 0,
        "failed_segments": 0,
        "current_segment": None,
        "errors": [],
        "details": {
            "segment_limit": segment_limit,
            "weights": weights
        }
    }

    task_store[task_id] = task_data

    try:
        # Database Pool holen
        db_pool = await get_db_pool()

        async with db_pool.acquire() as conn:
            searcher = SimilaritySearcher(conn)

            # Hole Target-Segmente für schrittweise Verarbeitung
            target_segments = await searcher.get_bahn_segments(target_bahn_id)

            if not target_segments:
                task_data["status"] = TaskStatus.FAILED
                task_data["error"] = f"Keine Segmente gefunden für Bahn {target_bahn_id}"
                task_data["failed_at"] = datetime.now().isoformat()
                return

            # Update total count falls unterschiedlich
            task_data["total_segments"] = len(target_segments)

            # Sammle alle Segment-Ergebnisse
            all_segment_results = []

            # SCHRITTWEISE VERARBEITUNG mit Progress Updates
            for i, target_segment_id in enumerate(target_segments):
                # Progress Update
                task_data["current_segment"] = target_segment_id
                task_data["processed_segments"] = i + 1

                try:
                    # Einzelnes Segment verarbeiten
                    # Hier müssen wir eine neue Methode in SimilaritySearcher erstellen
                    segment_result = await searcher.find_similar_single_segment(
                        target_segment_id,
                        segment_limit,
                        weights
                    )

                    if "error" in segment_result:
                        task_data["failed_segments"] += 1
                        task_data["errors"].append(f"Segment {target_segment_id}: {segment_result['error']}")
                    else:
                        task_data["successful_segments"] += 1
                        all_segment_results.append({
                            "target_segment": target_segment_id,
                            "similarity_data": segment_result
                        })

                except Exception as segment_error:
                    task_data["failed_segments"] += 1
                    error_msg = f"Segment {target_segment_id}: {str(segment_error)}"
                    task_data["errors"].append(error_msg)
                    logger.error(f"Task {task_id} - {error_msg}")

                # Kurze Pause für Polling-Updates
                await asyncio.sleep(0.1)

            # Task erfolgreich abgeschlossen
            task_data["results"] = all_segment_results
            task_data["status"] = TaskStatus.COMPLETED
            task_data["completed_at"] = datetime.now().isoformat()
            task_data["current_segment"] = None

            # Summary erstellen
            task_data["summary"] = {
                "total_segments_processed": len(target_segments),
                "successful_segments": task_data["successful_segments"],
                "failed_segments": task_data["failed_segments"],
                "total_similar_segments_found": sum(
                    len(result["similarity_data"].get("similar_segmente", []))
                    for result in all_segment_results
                ),
                "processing_time_seconds": (
                        datetime.fromisoformat(task_data["completed_at"]) -
                        datetime.fromisoformat(task_data["started_at"])
                ).total_seconds(),
                "average_segments_per_target": (
                    sum(len(result["similarity_data"].get("similar_segmente", []))
                        for result in all_segment_results) / len(all_segment_results)
                    if all_segment_results else 0
                )
            }

            logger.info(
                f"Segment similarity task {task_id} completed: {task_data['successful_segments']}/{len(target_segments)} segments processed successfully")

    except Exception as e:
        error_msg = f"Segment similarity task failed: {str(e)}"
        logger.error(f"Task {task_id}: {error_msg}")
        logger.error(traceback.format_exc())

        task_data["status"] = TaskStatus.FAILED
        task_data["error"] = error_msg
        task_data["failed_at"] = datetime.now().isoformat()
        task_data["current_segment"] = None
        task_data["errors"].append(error_msg)


async def process_meta_values_calculation(task_id: str, db_pool):
    """
    Background Task für Meta-Values Berechnung - OPTIMIERT
    Mit Optimierungen #2, #3, #4
    """
    # Task Status initialisieren
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

            # Standard-Parameter und Gewichtungen
            selected_parameters = {
                'duration', 'weight', 'length', 'movement_type',
                'direction_x', 'direction_y', 'direction_z'
            }
            weights = {
                'duration': 1.0, 'weight': 1.0, 'length': 1.0, 'movement_type': 1.0,
                'direction_x': 1.0, 'direction_y': 1.0, 'direction_z': 1.0
            }

            # Nur numerische Spalten
            numeric_columns = [
                'duration', 'weight', 'length',
                'direction_x', 'direction_y', 'direction_z'
            ]

            # Query - hole auch movement_type für Optimierung #3
            columns_str = ', '.join(['bm.' + col for col in numeric_columns])
            query = f"""
                SELECT bm.bahn_id,
                       bm.segment_id,
                       bm.movement_type,
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
                    "error": "Keine gültigen Daten in bahn_metadata gefunden"
                })
                return

            total_rows = len(rows)
            task_store[task_id].update({
                "total_rows": total_rows,
                "message": f"Processing {total_rows} rows..."
            })

            logger.info(f"Gefunden: {len(rows)} Datensätze mit vollständigen Daten")

            # OPTIMIERUNG 2: Direkte NumPy Array Erstellung (vektorisiert!)
            import numpy as np
            from sklearn.preprocessing import StandardScaler

            task_store[task_id]["message"] = "Creating data matrix and calculating meta-values..."

            # Extrahiere Daten direkt als NumPy Array
            data_matrix = np.array(
                [[row[col] for col in numeric_columns] for row in rows],
                dtype=np.float64
            )

            # In-place NaN handling (schneller als if-checks)
            np.nan_to_num(data_matrix, copy=False, nan=0.0)

            logger.info(f"Data matrix created: shape={data_matrix.shape}")

            # Batch Normalisierung
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(data_matrix)

            # Vectorized Meta-Value Berechnung
            weight_vector = np.array([weights.get(col, 1.0) for col in numeric_columns])
            abs_scaled = np.abs(scaled_data)
            weighted_sums = abs_scaled @ weight_vector

            # OPTIMIERUNG 3: Movement Type vektorisiert!
            if 'movement_type' in selected_parameters:
                movement_weight = weights.get('movement_type', 1.0)

                # Extrahiere alle movement_types auf einmal
                movement_types = np.array([str(row.get('movement_type', '')) for row in rows])

                # Vektorisierte Berechnungen (5-10x schneller!)
                lengths = np.char.str_len(movement_types).astype(np.float64) / 10.0
                has_c = (np.char.find(np.char.lower(movement_types), 'c') >= 0).astype(np.float64)
                has_s = (np.char.find(np.char.lower(movement_types), 's') >= 0).astype(np.float64)

                movement_scores = lengths + (has_c * 0.5) + (has_s * 0.3)

                weighted_sums += movement_scores * movement_weight
                total_weight = weight_vector.sum() + movement_weight
            else:
                total_weight = weight_vector.sum()

            meta_values = weighted_sums / total_weight if total_weight > 0 else weighted_sums

            logger.info(f"Meta-Value Statistiken: Min={meta_values.min():.6f}, "
                        f"Max={meta_values.max():.6f}, Avg={meta_values.mean():.6f}")

            # OPTIMIERUNG 4: Batch Updates mit temp table (3-5x schneller!)
            task_store[task_id]["message"] = "Updating database with calculated meta-values..."

            BATCH_SIZE = 50000  # Optimale Batch-Größe
            total_updated = 0

            for batch_start in range(0, len(rows), BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, len(rows))
                batch_rows = rows[batch_start:batch_end]
                batch_values = meta_values[batch_start:batch_end]

                async with conn.transaction():
                    # Erstelle temporäre Tabelle
                    await conn.execute("""
                                       CREATE
                                       TEMP TABLE IF NOT EXISTS temp_meta_updates (
                            bahn_id TEXT,
                            segment_id TEXT,
                            meta_value DOUBLE PRECISION
                        ) ON COMMIT DROP
                                       """)

                    # Bereite Daten vor (runde in Python, nicht SQL!)
                    temp_values = [
                        (str(row['bahn_id']),
                         str(row['segment_id']),
                         round(float(batch_values[i]), 4))
                        for i, row in enumerate(batch_rows)
                    ]

                    # Bulk Insert in temp table (super schnell mit COPY!)
                    await conn.copy_records_to_table(
                        'temp_meta_updates',
                        records=temp_values,
                        columns=['bahn_id', 'segment_id', 'meta_value']
                    )

                    # Single UPDATE mit JOIN (viel schneller als executemany!)
                    await conn.execute("""
                                       UPDATE robotervermessung.bewegungsdaten.bahn_meta bm
                                       SET meta_value = tmp.meta_value FROM temp_meta_updates tmp
                                       WHERE bm.bahn_id = tmp.bahn_id
                                         AND bm.segment_id = tmp.segment_id
                                       """)

                total_updated += len(batch_rows)

                # Update Progress (nur alle 5000 Rows)
                task_store[task_id]["processed_rows"] = total_updated

                if total_updated % 10000 == 0:  # Log nur alle 10k
                    logger.info(
                        f"Updated {total_updated}/{total_rows} rows ({(total_updated / total_rows) * 100:.1f}%)")

            logger.info(f"Meta-Value Berechnung abgeschlossen: {total_updated} Datensätze aktualisiert")

            # Task als completed markieren
            task_store[task_id].update({
                "status": TaskStatus.COMPLETED,
                "completed_at": datetime.now().isoformat(),
                "message": f"Meta-Values erfolgreich berechnet für {total_updated} Datensätze",
                "summary": {
                    "processed_rows": total_updated,
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
        import traceback
        logger.error(traceback.format_exc())
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
        duplicate_handling: str
):
    """
    Background Task für die Metadaten-Verarbeitung
    NEU: In-Memory Processing mit Batch-Write am Ende
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
            "duplicate_handling": duplicate_handling
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

        # NEU: In-Memory Processing mit Batch-Write
        successful_results = []
        failed_results = []
        all_metadata_rows = []  # Sammle alle Metadaten hier

        # Verarbeite alle Bahnen sequentiell (schnell, da nur in-memory)
        for bahn_id in bahn_ids:
            task_store[task_id]["current_bahn"] = bahn_id

            try:
                # Hole und verarbeite Bahn (gibt Liste von Metadaten zurück)
                bahn_metadata = await service.process_single_bahn_in_memory(bahn_id)

                if bahn_metadata.get('error'):
                    failed_results.append(bahn_metadata)
                    task_store[task_id]["failed_bahns"] += 1
                    task_store[task_id]["errors"].append(f"{bahn_id}: {bahn_metadata['error']}")
                else:
                    # Sammle Metadaten (Liste von Dicts)
                    all_metadata_rows.extend(bahn_metadata['metadata'])
                    successful_results.append(bahn_metadata)
                    task_store[task_id]["successful_bahns"] += 1

                task_store[task_id]["processed_bahns"] += 1

                # Progress logging
                if task_store[task_id]["processed_bahns"] % 100 == 0:
                    progress = (task_store[task_id]["processed_bahns"] / task_store[task_id]["total_bahns"]) * 100
                    logger.info(
                        f"Task {task_id} progress: {progress:.1f}% ({task_store[task_id]['processed_bahns']}/{task_store[task_id]['total_bahns']})")

            except Exception as e:
                logger.error(f"Exception processing bahn_id {bahn_id}: {e}")
                failed_results.append({
                    "bahn_id": bahn_id,
                    "error": str(e)
                })
                task_store[task_id]["failed_bahns"] += 1
                task_store[task_id]["errors"].append(f"{bahn_id}: {str(e)}")
                task_store[task_id]["processed_bahns"] += 1

        # Batch-Write: Schreibe ALLE Metadaten auf einmal
        if all_metadata_rows:
            logger.info(f"Writing {len(all_metadata_rows)} metadata rows in batch...")
            await service.batch_write_metadata(all_metadata_rows)
            logger.info(f"Batch write completed successfully!")

        # Task abschließen
        task_store[task_id].update({
            "status": TaskStatus.COMPLETED,
            "completed_at": datetime.now().isoformat(),
            "current_bahn": None,
            "summary": {
                "total_processed": len(bahn_ids),
                "successful": len(successful_results),
                "failed": len(failed_results),
                "total_metadata_rows": len(all_metadata_rows)
            }
        })

        logger.info(
            f"Task {task_id} completed successfully. {len(successful_results)}/{len(bahn_ids)} bahns processed successfully")

    except Exception as e:
        logger.error(f"Task {task_id} failed with exception: {e}")
        task_store[task_id].update({
            "status": TaskStatus.FAILED,
            "failed_at": datetime.now().isoformat(),
            "error": str(e),
            "current_bahn": None
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