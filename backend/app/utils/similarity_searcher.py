from typing import Dict, List, Any, Optional
import numpy as np


class SimilaritySearcher:
    def __init__(self, connection):
        self.connection = connection
        # Cache für Threshold-Berechnungen
        self._bahn_meta_values_cache = None
        self._segment_meta_values_cache = None

        # Default weights
        self.default_weights = {
            'duration': 1.0,
            'weight': 1.0,
            'length': 1.0,
            'movement_type': 1.0,
            'direction_x': 1.0,
            'direction_y': 1.0,
            'direction_z': 1.0
        }

    def detect_id_type(self, target_id: str) -> str:
        if target_id and '_' in target_id:
            return 'segment'
        return 'bahn'

    def _calculate_percentile_threshold(self, target_value: float, all_values: np.ndarray) -> float:
        target_percentile = np.searchsorted(all_values, target_value) / len(all_values) * 100

        if target_percentile < 2 or target_percentile > 94:
            threshold_percent = 70.0
        elif target_percentile < 10 or target_percentile > 90:
            threshold_percent = 50.0
        elif target_percentile < 25 or target_percentile > 75:
            threshold_percent = 35.0
        else:
            threshold_percent = 25.0

        return max(15.0, min(threshold_percent, 80.0))

    async def calculate_adaptive_threshold_bahn(self, target_meta_value: float) -> float:
        """Berechnet Schwellwert für Bahnen - mit Cache"""
        try:
            if self._bahn_meta_values_cache is None:
                query = """
                        SELECT meta_value as meta_value
                        FROM robotervermessung.bewegungsdaten.bahn_meta bm
                        WHERE bm.bahn_id = bm.segment_id
                          AND meta_value IS NOT NULL
                        ORDER BY meta_value \
                        """
                results = await self.connection.fetch(query)
                if len(results) < 10:
                    return 20.0

                self._bahn_meta_values_cache = np.array([row['meta_value'] for row in results])

            return self._calculate_percentile_threshold(target_meta_value, self._bahn_meta_values_cache)
        except Exception as e:
            print(f"Fehler bei adaptive Schwellwert-Berechnung: {e}")
            return 20.0

    async def calculate_adaptive_threshold_segment(self, target_meta_value: float) -> float:
        """Berechnet Schwellwert für Segmente - mit Cache"""
        try:
            if self._segment_meta_values_cache is None:
                query = """
                        SELECT meta_value  as meta_value
                        FROM robotervermessung.bewegungsdaten.bahn_meta bm
                        WHERE bm.bahn_id != bm.segment_id
                AND meta_value IS NOT NULL
                        ORDER BY meta_value \
                        """
                results = await self.connection.fetch(query)
                if len(results) < 10:
                    return 20.0

                self._segment_meta_values_cache = np.array([row['meta_value'] for row in results])

            return self._calculate_percentile_threshold(target_meta_value, self._segment_meta_values_cache)
        except Exception as e:
            print(f"Fehler bei adaptive Schwellwert-Berechnung für Segmente: {e}")
            return 20.0

    async def calculate_weighted_similarity_optimized(self, target_row: Dict,
                                                      compare_data: List[Dict],
                                                      weights: Dict[str, float]) -> List[Dict]:
        """
        KOMPLEXE Ähnlichkeitsberechnung - optimiert mit NumPy statt Pandas
        """
        # Numerische Spalten die verfügbar sind
        available_columns = [col for col in weights.keys()
                             if col in target_row
                             and all(col in row for row in compare_data)
                             and col != 'movement_type']

        if not available_columns:
            available_columns = ['duration', 'length', 'direction_x', 'direction_y', 'direction_z']
            available_columns = [col for col in available_columns
                                 if col in target_row and all(col in row for row in compare_data)]

        # NumPy Arrays direkt erstellen (ohne Pandas)
        target_values = np.array([target_row.get(col, 0.0) for col in available_columns])
        compare_matrix = np.array([[row.get(col, 0.0) for col in available_columns] for row in compare_data])

        # Normalisierung
        all_values = np.vstack([target_values, compare_matrix])
        means = np.mean(all_values, axis=0)
        stds = np.std(all_values, axis=0)
        stds[stds == 0] = 1  # Verhindere Division durch 0

        target_normalized = (target_values - means) / stds
        compare_normalized = (compare_matrix - means) / stds

        # Gewichtungsvektor
        weight_vector = np.array([weights.get(col, 1.0) for col in available_columns])

        # Vektorisierte Distanzberechnung
        distances = np.abs(compare_normalized - target_normalized)
        weighted_distances = (distances @ weight_vector) / weight_vector.sum()

        # Movement type handling
        if 'movement_type' in target_row and all('movement_type' in row for row in compare_data):
            target_movement = str(target_row['movement_type'])
            movement_weight = weights.get('movement_type', 1.0)

            movement_mismatch = np.array([1.0 if str(row['movement_type']) != target_movement else 0.0
                                          for row in compare_data])
            movement_penalty = movement_mismatch * movement_weight / (weight_vector.sum() + movement_weight)
            weighted_distances = weighted_distances + movement_penalty

        # Ergebnisse mit Similarity Score erweitern und sortieren (ohne Pandas)
        for i, row in enumerate(compare_data):
            row['similarity_score'] = weighted_distances[i]

        return sorted(compare_data, key=lambda x: x['similarity_score'])

    async def load_data_with_features(self, where_condition: str, params: tuple = None) -> List[Dict]:
        """
        Lädt Daten mit allen Features für komplexe Ähnlichkeitsberechnung - NumPy optimiert
        """
        query = """
                SELECT bm.bahn_id, \
                       bm.segment_id, \
                       bm.meta_value,
                       CAST(bm.duration AS FLOAT)                as duration,
                       CAST(bm.weight AS FLOAT)                  as weight,
                       CAST(bm.length AS FLOAT)                  as length,
                       bm.movement_type,
                       CAST(bm.direction_x AS FLOAT)             as direction_x,
                       CAST(bm.direction_y AS FLOAT)             as direction_y,
                       CAST(bm.direction_z AS FLOAT)             as direction_z,
                       CAST(bm.min_position_x_soll AS FLOAT)     as min_position_x_soll,
                       CAST(bm.min_position_y_soll AS FLOAT)     as min_position_y_soll,
                       CAST(bm.min_position_z_soll AS FLOAT)     as min_position_z_soll,
                       CAST(bm.max_position_x_soll AS FLOAT)     as max_position_x_soll,
                       CAST(bm.max_position_y_soll AS FLOAT)     as max_position_y_soll,
                       CAST(bm.max_position_z_soll AS FLOAT)     as max_position_z_soll,
                       CAST(ist.sidtw_average_distance AS FLOAT) as sidtw_average_distance
                FROM robotervermessung.bewegungsdaten.bahn_meta bm
                         LEFT JOIN robotervermessung.auswertung.info_sidtw ist
                                   ON CAST(bm.segment_id AS TEXT) = ist.segment_id
                                       AND ist.evaluation = 'position' \
                """ + where_condition

        if params:
            results = await self.connection.fetch(query, *params)
        else:
            results = await self.connection.fetch(query)

        # Konvertiere direkt zu Liste von Dicts (ohne Pandas)
        return [dict(row) for row in results]


################## BAHNEN #####################

    async def get_target_bahn_meta_value(self, bahn_id: str) -> Optional[float]:
        """
        Holt Meta-Value für eine Bahn-ID
        """
        query = """
        SELECT CAST(meta_value AS FLOAT) as meta_value
        FROM robotervermessung.bewegungsdaten.bahn_meta bm
        WHERE CAST(bm.bahn_id AS TEXT) = $1
        AND CAST(bm.bahn_id AS TEXT) = CAST(bm.segment_id AS TEXT)
        """

        result = await self.connection.fetchrow(query, bahn_id)
        return result['meta_value'] if result and result['meta_value'] is not None else None

    async def find_similar_bahnen_complex(self, target_bahn_id: str, limit: int = 10,
                                          weights: Dict[str, float] = None) -> Dict[str, Any]:
        """
        KOMPLEXE Bahn-Ähnlichkeitssuche mit vollständiger Feature-Berechnung - NumPy optimiert
        """
        try:
            if weights is None:
                weights = self.default_weights.copy()

            # 1. Target Meta-Value für Threshold-Berechnung laden
            target_meta_value = await self.get_target_bahn_meta_value(target_bahn_id)
            if target_meta_value is None:
                return {"error": f"Target-Bahn {target_bahn_id} hat keinen Meta-Value"}

            # 2. Adaptive Schwellwert-Berechnung
            adaptive_threshold = await self.calculate_adaptive_threshold_bahn(target_meta_value)

            # 3. Meta-Value Bereich für Vorfilterung
            threshold_factor = adaptive_threshold / 100.0
            meta_value_min = target_meta_value * (1 - threshold_factor)
            meta_value_max = target_meta_value * (1 + threshold_factor)

            # 4. Alle Bahnen im Meta-Value-Bereich laden (ohne Pandas)
            where_condition = """
            WHERE CAST(bm.bahn_id AS TEXT) = CAST(bm.segment_id AS TEXT)
            AND bm.meta_value BETWEEN $1 AND $2
            ORDER BY bm.meta_value
            """

            data_all = await self.load_data_with_features(
                where_condition,
                (meta_value_min, meta_value_max)
            )

            if not data_all:
                return {"error": f"Keine Bahnen im Meta-Value-Bereich gefunden"}

            # 5. Target und andere Bahnen trennen (ohne Pandas)
            target_data = None
            other_bahnen = []

            for row in data_all:
                if row['bahn_id'] == target_bahn_id:
                    target_data = row
                else:
                    other_bahnen.append(row)

            if target_data is None:
                return {"error": f"Target-Bahn nicht in gefilterten Daten gefunden"}

            if not other_bahnen:
                target_data['similarity_score'] = 0.0
                return {
                    "target": target_data,
                    "similar_bahnen": [],
                    "auto_threshold": adaptive_threshold,
                    "total_found": 0
                }

            # 6. KOMPLEXE Ähnlichkeitsberechnung (NumPy)
            similarities = await self.calculate_weighted_similarity_optimized(
                target_data, other_bahnen, weights
            )

            # 7. Ergebnisse formatieren (ohne Pandas)
            target_data['similarity_score'] = 0.0

            # Top ähnliche Bahnen (einfaches List Slicing)
            similar_bahnen = similarities[:limit]

            return {
                "target": target_data,
                "similar_bahnen": similar_bahnen,
                "auto_threshold": adaptive_threshold,
                "total_found": len(similarities),
                "weights_used": weights,
                "meta_value_range": {
                    "min": meta_value_min,
                    "max": meta_value_max
                }
            }

        except Exception as e:
            return {"error": f"Fehler bei komplexer Bahn-Ähnlichkeitssuche: {str(e)}"}

    async def find_similar_bahnen_auto(self, target_bahn_id: str, limit: int = 10,
                                    weights: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Wrapper-Funktion für komplexe Bahn-Ähnlichkeitssuche mit Auto-Threshold
        """
        return await self.find_similar_bahnen_complex(target_bahn_id, limit, weights)

################## SEGMENTE #####################

    async def get_target_segment_meta_value(self, segment_id: str) -> Optional[float]:
        """
        Holt Meta-Value für eine Segment-ID
        """
        query = """
        SELECT CAST(meta_value AS FLOAT) as meta_value
        FROM robotervermessung.bewegungsdaten.bahn_meta bm
        WHERE CAST(bm.segment_id AS TEXT) = $1
        AND CAST(bm.bahn_id AS TEXT) != CAST(bm.segment_id AS TEXT)
        """

        result = await self.connection.fetchrow(query, segment_id)
        return result['meta_value'] if result and result['meta_value'] is not None else None

    async def load_all_segments_batch(self, target_bahn_id: str, segment_limit: int, weights: Dict[str, float]) -> Dict[
        str, Any]:
        """
        Lädt ALLE Segmente einer Bahn mit KONSISTENTER Ähnlichkeitsberechnung
        """
        try:
            # 1. Target-Segmente der Bahn holen
            target_segments = await self.get_bahn_segments(target_bahn_id)
            if not target_segments:
                return {"segment_results": [], "info": f"Keine Segmente gefunden für Bahn {target_bahn_id}"}

            # 2. EINHEITLICHER THRESHOLD: Basierend auf der ganzen Bahn
            target_bahn_meta_value = await self.get_target_bahn_meta_value(target_bahn_id)
            if target_bahn_meta_value is None:
                return {"error": f"Bahn {target_bahn_id} hat keinen Meta-Value"}

            adaptive_threshold = await self.calculate_adaptive_threshold_bahn(target_bahn_meta_value)

            # 3. EINHEITLICHER META-VALUE-BEREICH
            threshold_factor = adaptive_threshold / 100.0
            bahn_meta_min = target_bahn_meta_value * (1 - threshold_factor)
            bahn_meta_max = target_bahn_meta_value * (1 + threshold_factor)

            # 4. Lade ALLE Segmente in diesem Bereich
            where_condition = """
            WHERE CAST(bm.bahn_id AS TEXT) != CAST(bm.segment_id AS TEXT)
            AND bm.meta_value IS NOT NULL
            AND bm.meta_value BETWEEN $1 AND $2
            ORDER BY bm.meta_value
            """

            all_segment_data = await self.load_data_with_features(where_condition, (bahn_meta_min, bahn_meta_max))

            if not all_segment_data:
                return {"segment_results": [], "info": "Keine Segmente in Bereich gefunden"}

            # 5. Trenne Target und Vergleichsdaten
            target_data_lookup = {}
            other_segments = []

            for row in all_segment_data:
                segment_id = row['segment_id']
                if segment_id in target_segments:
                    target_data_lookup[segment_id] = row
                else:
                    other_segments.append(row)

            if not other_segments:
                return {"segment_results": [], "info": "Keine Vergleichssegmente gefunden"}

            # 6. KONSISTENTE NORMALISIERUNG

            # Numerische Spalten bestimmen
            available_columns = [col for col in weights.keys()
                                 if col != 'movement_type'
                                 and all(col in row for row in all_segment_data)]

            if not available_columns:
                available_columns = ['duration', 'length', 'direction_x', 'direction_y', 'direction_z']
                available_columns = [col for col in available_columns
                                     if all(col in row for row in all_segment_data)]

            # 7. Für jedes Target-Segment: Ähnlichkeitsberechnung
            segment_results = []

            for target_segment_id in target_segments:
                if target_segment_id not in target_data_lookup:
                    continue

                target_data = target_data_lookup[target_segment_id]

                # Erstelle target_row und compare_df
                target_row_dict = {col: target_data.get(col, 0.0) for col in available_columns}
                compare_data_dicts = [{col: row.get(col, 0.0) for col in available_columns} for row in other_segments]

                # Kombiniere für StandardScaler
                all_data_for_scaling = [target_row_dict] + compare_data_dicts

                # StandardScaler
                from sklearn.preprocessing import StandardScaler
                scaler = StandardScaler()

                # Erstelle Matrix für Scaler
                data_matrix = np.array([[row[col] for col in available_columns] for row in all_data_for_scaling])
                scaled_data = scaler.fit_transform(data_matrix)

                # Trenne Target und Compare
                target_scaled = scaled_data[0:1]  # Erste Zeile
                compare_scaled = scaled_data[1:]  # Rest

                # Gewichtungsvektor
                weight_vector = np.array([weights.get(col, 1.0) for col in available_columns])

                # Distanzberechnung
                distances = np.abs(compare_scaled - target_scaled)
                weighted_distances = (distances @ weight_vector) / weight_vector.sum()

                # Movement type handling
                if 'movement_type' in weights and 'movement_type' in target_data:
                    target_movement = str(target_data['movement_type'])
                    movement_weight = weights.get('movement_type', 1.0)
                    if movement_weight > 0:
                        movement_mismatch = np.array(
                            [1.0 if str(row.get('movement_type', '')) != target_movement else 0.0
                             for row in other_segments], dtype=np.float32)
                        movement_penalty = movement_mismatch * movement_weight
                        weighted_distances = weighted_distances + (
                                    movement_penalty / (weight_vector.sum() + movement_weight))

                # Ergebnisse mit Similarity Scores
                similarities_with_scores = []
                for j, row in enumerate(other_segments):
                    row_copy = row.copy()
                    row_copy['similarity_score'] = weighted_distances[j]
                    similarities_with_scores.append(row_copy)

                similarities_sorted = sorted(similarities_with_scores, key=lambda x: x['similarity_score'])

                # Formatierung
                target_data['similarity_score'] = 0.0
                similar_segmente = similarities_sorted[:segment_limit]

                segment_results.append({
                    "target_segment": target_segment_id,
                    "similarity_data": {
                        "target": target_data,
                        "similar_segmente": similar_segmente,
                        "auto_threshold": adaptive_threshold,
                        "total_found": len(similarities_sorted),
                        "weights_used": weights,
                        "meta_value_range": {
                            "min": bahn_meta_min,
                            "max": bahn_meta_max
                        }
                    }
                })

            return {"segment_results": segment_results}

        except Exception as e:
            import traceback
            return {"error": f"Fehler bei konsistenter Segment-Ähnlichkeitssuche: {str(e)}"}

    async def calculate_batch_thresholds_segment(self, target_meta_values: List[float]) -> List[float]:
        """
        Berechnet Schwellwerte für alle Segmente auf einmal (Batch-Optimierung)
        """
        try:
            # Cache laden falls nicht vorhanden (einmalig)
            if self._segment_meta_values_cache is None:
                query = """
                        SELECT meta_value as meta_value
                        FROM robotervermessung.bewegungsdaten.bahn_meta bm
                        WHERE bm.bahn_id != bm.segment_id
                AND meta_value IS NOT NULL
                        ORDER BY meta_value \
                        """
                results = await self.connection.fetch(query)
                if len(results) < 10:
                    return [20.0] * len(target_meta_values)

                self._segment_meta_values_cache = np.array([row['meta_value'] for row in results])

            # Batch-Berechnung für alle Target-Meta-Values auf einmal
            thresholds = []
            for target_value in target_meta_values:
                threshold = self._calculate_percentile_threshold(target_value, self._segment_meta_values_cache)
                thresholds.append(threshold)

            return thresholds

        except Exception as e:
            print(f"Fehler bei Batch-Schwellwert-Berechnung für Segmente: {e}")
            return [20.0] * len(target_meta_values)

    async def find_similar_segmente_complex(self, target_segment_id: str, limit: int = 10,
                                            weights: Dict[str, float] = None) -> Dict[str, Any]:
        """
        KOMPLEXE Segment-Ähnlichkeitssuche mit vollständiger Feature-Berechnung - NumPy optimiert
        """
        try:
            if weights is None:
                weights = self.default_weights.copy()

            # 1. Target Meta-Value für Threshold-Berechnung laden
            target_meta_value = await self.get_target_segment_meta_value(target_segment_id)
            if target_meta_value is None:
                return {"error": f"Target-Segment {target_segment_id} hat keinen Meta-Value"}

            # 2. Adaptive Schwellwert-Berechnung
            adaptive_threshold = await self.calculate_adaptive_threshold_segment(target_meta_value)

            # 3. Meta-Value Bereich für Vorfilterung
            threshold_factor = adaptive_threshold / 100.0
            meta_value_min = target_meta_value * (1 - threshold_factor)
            meta_value_max = target_meta_value * (1 + threshold_factor)

            # 4. Alle Segmente im Meta-Value-Bereich laden (ohne Pandas)
            where_condition = """
            WHERE CAST(bm.bahn_id AS TEXT) != CAST(bm.segment_id AS TEXT)
            AND bm.meta_value BETWEEN $1 AND $2
            ORDER BY bm.meta_value
            """

            data_all = await self.load_data_with_features(
                where_condition,
                (meta_value_min, meta_value_max)
            )

            if not data_all:
                return {"error": f"Keine Segmente im Meta-Value-Bereich gefunden"}

            # 5. Target und andere Segmente trennen (ohne Pandas)
            target_data = None
            other_segmente = []

            for row in data_all:
                if row['segment_id'] == target_segment_id:
                    target_data = row
                else:
                    other_segmente.append(row)

            if target_data is None:
                return {"error": f"Target-Segment nicht in gefilterten Daten gefunden"}

            if not other_segmente:
                target_data['similarity_score'] = 0.0
                return {
                    "target": target_data,
                    "similar_segmente": [],
                    "auto_threshold": adaptive_threshold,
                    "total_found": 0
                }

            # 6. KOMPLEXE Ähnlichkeitsberechnung (NumPy)
            similarities = await self.calculate_weighted_similarity_optimized(
                target_data, other_segmente, weights
            )

            # 7. Ergebnisse formatieren (ohne Pandas)
            target_data['similarity_score'] = 0.0

            # Top ähnliche Segmente (einfaches List Slicing)
            similar_segmente = similarities[:limit]

            return {
                "target": target_data,
                "similar_segmente": similar_segmente,
                "auto_threshold": adaptive_threshold,
                "total_found": len(similarities),
                "weights_used": weights,
                "meta_value_range": {
                    "min": meta_value_min,
                    "max": meta_value_max
                }
            }

        except Exception as e:
            return {"error": f"Fehler bei komplexer Segment-Ähnlichkeitssuche: {str(e)}"}

    async def find_similar_segmente_auto(self, target_segment_id: str, limit: int = 10,
                                        weights: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Wrapper-Funktion für komplexe Segment-Ähnlichkeitssuche mit Auto-Threshold
        """
        return await self.find_similar_segmente_complex(target_segment_id, limit, weights)

    async def get_bahn_segments(self, bahn_id: str) -> List[str]:
        """
        Holt alle Segment-IDs einer Bahn
        """
        try:
            query = """
            SELECT CAST(segment_id AS TEXT) as segment_id
            FROM robotervermessung.bewegungsdaten.bahn_meta bm
            WHERE CAST(bahn_id AS TEXT) = $1
            AND CAST(bahn_id AS TEXT) != CAST(segment_id AS TEXT)
            AND meta_value IS NOT NULL
            ORDER BY segment_id
            """

            results = await self.connection.fetch(query, bahn_id)
            return [row['segment_id'] for row in results]

        except Exception as e:
            print(f"Fehler beim Laden der Bahn-Segmente: {e}")
            return []


################ HIERARCHISCHE SUCHE #####################

    async def find_similar_unified_complex(self, target_id: str, bahn_limit: int = 10,
                                           segment_limit: int = 5, weights: Dict[str, float] = None) -> Dict[str, Any]:
        """
        KOMPLEXE hierarchische Ähnlichkeitssuche - optimiert mit Batch-Loading
        """
        try:
            if weights is None:
                weights = self.default_weights.copy()

            # 1. ID-Typ erkennen und Target-Bahn bestimmen
            id_type = self.detect_id_type(target_id)

            if id_type == 'bahn':
                target_bahn_id = target_id
            else:
                target_bahn_id = target_id.split('_')[0]

            print(f"🔍 Optimierte hierarchische Suche für {target_id} (Typ: {id_type})")
            print(f"   Target-Bahn: {target_bahn_id}")

            # 2. Phase 1: Bahn-Ähnlichkeitssuche (bleibt gleich)
            print(f"Phase 1: Bahn-Ähnlichkeitssuche für {target_bahn_id}")
            bahn_results = await self.find_similar_bahnen_complex(target_bahn_id, bahn_limit, weights)

            if "error" in bahn_results:
                return {"error": f"Bahn-Suche fehlgeschlagen: {bahn_results['error']}"}

            # 3. Phase 2: BATCH Segment-Ähnlichkeitssuche (NEUE optimierte Version)
            print(f"Phase 2: Batch-Segment-Loading für Bahn {target_bahn_id}")
            batch_results = await self.load_all_segments_batch(target_bahn_id, segment_limit, weights)

            # DEBUG: Prüfe was zurückkommt
            print(
                f"DEBUG: batch_results keys = {batch_results.keys() if isinstance(batch_results, dict) else 'Not dict'}")

            if "error" in batch_results:
                print(f"DEBUG: Batch error = {batch_results['error']}")
                segment_results = []
            elif "segment_results" in batch_results:
                segment_results = batch_results["segment_results"]
                print(f"DEBUG: Found {len(segment_results)} segment results")
            else:
                print(f"DEBUG: No segment_results key found")
                segment_results = []

            # 4. Statistiken berechnen
            segment_thresholds = []
            for result in segment_results:
                threshold = result.get("similarity_data", {}).get("auto_threshold")
                if threshold is not None:
                    segment_thresholds.append(threshold)

            avg_segment_threshold = (
                sum(segment_thresholds) / len(segment_thresholds)
                if segment_thresholds else None
            )

            print(f"DEBUG: Final segment_results count = {len(segment_results)}")

            # 5. Finale Zusammenfassung
            return {
                "target_bahn_id": target_bahn_id,
                "original_input": target_id,
                "input_type": id_type,
                "bahn_similarity": bahn_results,
                "segment_similarity": segment_results,
                "summary": {
                    "total_similar_bahnen": len(bahn_results.get("similar_bahnen", [])),
                    "total_target_segments": len(segment_results),
                    "segments_processed": len(segment_results),
                    "bahn_threshold": bahn_results.get("auto_threshold"),
                    "avg_segment_threshold": avg_segment_threshold,
                    "weights_used": weights,
                    "optimization": "batch_loading_enabled"
                },
                "performance_info": {
                    "features_used": list(weights.keys()),
                    "calculation_method": "batch_weighted_similarity",
                    "database_queries": "minimized_with_batch_loading"
                }
            }

        except Exception as e:
            print(f"DEBUG: Exception in find_similar_unified_complex: {str(e)}")
            return {"error": f"Fehler bei optimierter hierarchischer Ähnlichkeitssuche: {str(e)}"}

    def _calculate_avg_segment_threshold(self, segment_results: List[Dict]) -> Optional[float]:
        """
        Berechnet durchschnittlichen Schwellwert aller Segment-Suchen
        """
        if not segment_results:
            return None

        thresholds = []
        for result in segment_results:
            threshold = result.get("similarity_data", {}).get("auto_threshold")
            if threshold is not None:
                thresholds.append(threshold)

        return sum(thresholds) / len(thresholds) if thresholds else None