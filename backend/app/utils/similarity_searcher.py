from typing import Dict, List, Any, Optional
import numpy as np
from sklearn.preprocessing import StandardScaler


class SimilaritySearcher:
    def __init__(self, connection):
        self.connection = connection

        # Default weights for similarity calculation
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
        """Detect if ID is for 'bahn' or 'segment'"""
        return 'segment' if target_id and '_' in target_id else 'bahn'

    # =================== DATA LOADING ===================

    async def load_data_with_features(self, where_condition: str, params: tuple = None) -> List[Dict]:
        """Load data with all features for similarity calculation"""
        query = """
                SELECT bm.bahn_id,
                       bm.segment_id,
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

        return [dict(row) for row in results]

    # =================== SIMILARITY CALCULATION ===================

    async def calculate_weighted_similarity_optimized(self, target_row: Dict,
                                                      compare_data: List[Dict],
                                                      weights: Dict[str, float]) -> List[Dict]:
        """Calculate weighted similarity using NumPy optimization"""

        # Get available numerical columns
        available_columns = [col for col in weights.keys()
                             if col in target_row
                             and all(col in row for row in compare_data)
                             and col != 'movement_type']

        if not available_columns:
            available_columns = ['duration', 'length', 'direction_x', 'direction_y', 'direction_z']
            available_columns = [col for col in available_columns
                                 if col in target_row and all(col in row for row in compare_data)]

        # Create NumPy arrays
        target_values = np.array([target_row.get(col, 0.0) for col in available_columns])
        compare_matrix = np.array([[row.get(col, 0.0) for col in available_columns]
                                   for row in compare_data])

        # Normalization using StandardScaler
        all_values = np.vstack([target_values, compare_matrix])
        scaler = StandardScaler()
        scaled_values = scaler.fit_transform(all_values)

        target_normalized = scaled_values[0:1]
        compare_normalized = scaled_values[1:]

        # Weight vector
        weight_vector = np.array([weights.get(col, 1.0) for col in available_columns])

        # Calculate weighted distances
        distances = np.abs(compare_normalized - target_normalized)
        weighted_distances = (distances @ weight_vector) / weight_vector.sum()

        # Handle movement type
        if 'movement_type' in target_row and all('movement_type' in row for row in compare_data):
            target_movement = str(target_row['movement_type'])
            movement_weight = weights.get('movement_type', 1.0)

            compare_movements = np.array([str(row.get('movement_type', '')) for row in compare_data])
            movement_mismatch = (compare_movements != target_movement).astype(float)
            movement_penalty = movement_mismatch * movement_weight / (weight_vector.sum() + movement_weight)
            weighted_distances = weighted_distances + movement_penalty

        # Add similarity scores to results
        for i, row in enumerate(compare_data):
            row['similarity_score'] = weighted_distances[i]

        return sorted(compare_data, key=lambda x: x['similarity_score'])

    # =================== BAHN FUNCTIONS ===================

    async def get_target_bahn_meta_value(self, bahn_id: str) -> Optional[float]:
        """Get meta value for a bahn ID"""
        query = """
                SELECT CAST(meta_value AS FLOAT) as meta_value
                FROM robotervermessung.bewegungsdaten.bahn_meta bm
                WHERE CAST(bm.bahn_id AS TEXT) = $1
                  AND CAST(bm.bahn_id AS TEXT) = CAST(bm.segment_id AS TEXT) \
                """
        result = await self.connection.fetchrow(query, bahn_id)
        return result['meta_value'] if result and result['meta_value'] is not None else None

    async def find_similar_bahnen(self, target_bahn_id: str, limit: int = 10,
                                  weights: Dict[str, float] = None) -> Dict[str, Any]:
        try:
            if weights is None:
                weights = self.default_weights.copy()

            # Get target meta value
            target_meta_value = await self.get_target_bahn_meta_value(target_bahn_id)
            if target_meta_value is None:
                return {"error": f"Target-Bahn {target_bahn_id} has no meta_value"}

            # Use fixed threshold of 100% (as per original logic)
            threshold_factor = 1.0  # 100%
            meta_value_min = target_meta_value * (1 - threshold_factor)
            meta_value_max = target_meta_value * (1 + threshold_factor)

            # Load all bahnen in meta value range
            where_condition = """
                WHERE CAST(bm.bahn_id AS TEXT) = CAST(bm.segment_id AS TEXT)
                AND bm.meta_value BETWEEN $1 AND $2
                ORDER BY bm.meta_value
            """

            data_all = await self.load_data_with_features(where_condition, (meta_value_min, meta_value_max))

            if not data_all:
                return {"error": "No bahnen found in meta_value range"}

            # Separate target and comparison data
            target_data = None
            other_bahnen = []

            for row in data_all:
                if row['bahn_id'] == target_bahn_id:
                    target_data = row
                else:
                    other_bahnen.append(row)

            if target_data is None:
                return {"error": "Target-Bahn not found in filtered data"}

            if not other_bahnen:
                target_data['similarity_score'] = 0.0
                return {
                    "target": target_data,
                    "similar_bahnen": [],
                    "auto_threshold": 100.0,
                    "total_found": 0
                }

            # Calculate similarities
            similarities = await self.calculate_weighted_similarity_optimized(
                target_data, other_bahnen, weights
            )

            target_data['similarity_score'] = 0.0
            similar_bahnen = similarities[:limit]

            return {
                "target": target_data,
                "similar_bahnen": similar_bahnen,
                "auto_threshold": 100.0,
                "total_found": len(similarities),
                "weights_used": weights,
                "meta_value_range": {
                    "min": meta_value_min,
                    "max": meta_value_max
                }
            }

        except Exception as e:
            return {"error": f"Error in bahn similarity search: {str(e)}"}

    # =================== SEGMENT FUNCTIONS ===================

    async def get_target_segment_meta_value(self, segment_id: str) -> Optional[float]:
        """Get meta value for a segment ID"""
        query = """
                SELECT CAST(meta_value AS FLOAT) as meta_value
                FROM robotervermessung.bewegungsdaten.bahn_meta bm
                WHERE CAST(bm.segment_id AS TEXT) = $1
                  AND CAST(bm.bahn_id AS TEXT) != CAST(bm.segment_id AS TEXT) \
                """
        result = await self.connection.fetchrow(query, segment_id)
        return result['meta_value'] if result and result['meta_value'] is not None else None

    async def get_bahn_segments(self, bahn_id: str) -> List[str]:
        """Get all segment IDs for a bahn"""
        try:
            query = """
                    SELECT CAST(segment_id AS TEXT) as segment_id
                    FROM robotervermessung.bewegungsdaten.bahn_meta bm
                    WHERE CAST(bahn_id AS TEXT) = $1
                      AND CAST(bahn_id AS TEXT) != CAST(segment_id AS TEXT)
                AND meta_value IS NOT NULL
                    ORDER BY segment_id \
                    """
            results = await self.connection.fetch(query, bahn_id)
            return [row['segment_id'] for row in results]
        except Exception as e:
            print(f"Error loading bahn segments: {e}")
            return []

    async def find_similar_single_segment(self, target_segment_id: str, limit: int,
                                          weights: Dict[str, float]) -> Dict[str, Any]:
        """
        Findet ähnliche Segmente für ein einzelnes Target-Segment
        Extrahiert aus der find_similar_segments Logik
        """
        try:
            # Get target segment meta value
            target_meta_value = await self.get_target_segment_meta_value(target_segment_id)
            if target_meta_value is None:
                return {"error": f"Target-Segment {target_segment_id} hat keinen Meta-Value"}

            # Extract bahn_id from segment_id
            target_bahn_id = target_segment_id.split('_')[0]

            # Get bahn meta value for consistent threshold
            target_bahn_meta_value = await self.get_target_bahn_meta_value(target_bahn_id)
            if target_bahn_meta_value is None:
                return {"error": f"Parent-Bahn {target_bahn_id} hat keinen Meta-Value"}

            # Use fixed threshold of 100%
            threshold_factor = 1.0
            bahn_meta_min = target_bahn_meta_value * (1 - threshold_factor)
            bahn_meta_max = target_bahn_meta_value * (1 + threshold_factor)

            # Load all segments in this range (including the target)
            where_condition = """
                WHERE CAST(bm.bahn_id AS TEXT) != CAST(bm.segment_id AS TEXT)
                AND bm.meta_value IS NOT NULL
                AND bm.meta_value BETWEEN $1 AND $2
                ORDER BY bm.meta_value
            """

            all_segment_data = await self.load_data_with_features(
                where_condition, (bahn_meta_min, bahn_meta_max)
            )

            if not all_segment_data:
                return {"error": "Keine Segmente im Meta-Value-Bereich gefunden"}

            # Separate target and comparison data
            target_data = None
            other_segments = []

            for row in all_segment_data:
                if row['segment_id'] == target_segment_id:
                    target_data = row
                else:
                    other_segments.append(row)

            if target_data is None:
                return {"error": "Target-Segment nicht in gefilterten Daten gefunden"}

            if not other_segments:
                target_data['similarity_score'] = 0.0
                return {
                    "target": target_data,
                    "similar_segmente": [],
                    "auto_threshold": 100.0,
                    "total_found": 0,
                    "weights_used": weights,
                    "meta_value_range": {
                        "min": bahn_meta_min,
                        "max": bahn_meta_max
                    }
                }

            # Get numerical columns for normalization
            available_columns = [col for col in weights.keys()
                                 if col != 'movement_type'
                                 and col in target_data
                                 and all(col in row for row in other_segments)]

            if not available_columns:
                available_columns = ['duration', 'length', 'direction_x', 'direction_y', 'direction_z']
                available_columns = [col for col in available_columns
                                     if col in target_data and all(col in row for row in other_segments)]

            # Prepare data for StandardScaler
            target_row_dict = {col: target_data.get(col, 0.0) for col in available_columns}
            compare_data_dicts = [{col: row.get(col, 0.0) for col in available_columns}
                                  for row in other_segments]

            all_data_for_scaling = [target_row_dict] + compare_data_dicts

            # Apply StandardScaler
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            data_matrix = np.array([[row[col] for col in available_columns]
                                    for row in all_data_for_scaling])
            scaled_data = scaler.fit_transform(data_matrix)

            target_scaled = scaled_data[0:1]
            compare_scaled = scaled_data[1:]

            # Calculate weighted distances
            weight_vector = np.array([weights.get(col, 1.0) for col in available_columns])
            distances = np.abs(compare_scaled - target_scaled)
            weighted_distances = (distances @ weight_vector) / weight_vector.sum()

            # Handle movement type
            if 'movement_type' in weights and 'movement_type' in target_data:
                target_movement = str(target_data['movement_type'])
                movement_weight = weights.get('movement_type', 1.0)
                if movement_weight > 0:
                    movement_mismatch = np.array([
                        1.0 if str(row.get('movement_type', '')) != target_movement else 0.0
                        for row in other_segments
                    ], dtype=np.float32)
                    movement_penalty = movement_mismatch * movement_weight
                    weighted_distances = weighted_distances + (
                            movement_penalty / (weight_vector.sum() + movement_weight)
                    )

            # Create results with similarity scores
            similarities_with_scores = []
            for j, row in enumerate(other_segments):
                row_copy = row.copy()
                row_copy['similarity_score'] = weighted_distances[j]
                similarities_with_scores.append(row_copy)

            similarities_sorted = sorted(similarities_with_scores, key=lambda x: x['similarity_score'])

            target_data['similarity_score'] = 0.0
            similar_segmente = similarities_sorted[:limit]

            return {
                "target": target_data,
                "similar_segmente": similar_segmente,
                "auto_threshold": 100.0,
                "total_found": len(similarities_sorted),
                "weights_used": weights,
                "meta_value_range": {
                    "min": bahn_meta_min,
                    "max": bahn_meta_max
                }
            }

        except Exception as e:
            return {"error": f"Fehler bei Einzelsegment-Ähnlichkeitssuche: {str(e)}"}

    async def find_similar_segments(self, target_bahn_id: str, segment_limit: int,
                                      weights: Dict[str, float]) -> Dict[str, Any]:
        """Load all segments of a bahn with consistent similarity calculation"""
        try:
            # Get target segments
            target_segments = await self.get_bahn_segments(target_bahn_id)
            if not target_segments:
                return {"segment_results": [], "info": f"No segments found for bahn {target_bahn_id}"}

            # Get bahn meta value for consistent threshold
            target_bahn_meta_value = await self.get_target_bahn_meta_value(target_bahn_id)
            if target_bahn_meta_value is None:
                return {"error": f"Bahn {target_bahn_id} has no meta_value"}

            # Use fixed threshold of 100%
            threshold_factor = 1.0
            bahn_meta_min = target_bahn_meta_value * (1 - threshold_factor)
            bahn_meta_max = target_bahn_meta_value * (1 + threshold_factor)

            # Load all segments in this range
            where_condition = """
                WHERE (
                    (CAST(bm.bahn_id AS TEXT) != CAST(bm.segment_id AS TEXT)
                    AND bm.meta_value IS NOT NULL
                    AND bm.meta_value BETWEEN $1 AND $2)
                    OR 
                    CAST(bm.segment_id AS TEXT) = ANY($3)
                )
                ORDER BY bm.meta_value
            """

            all_segment_data = await self.load_data_with_features(
                where_condition, (bahn_meta_min, bahn_meta_max, target_segments)
            )

            if not all_segment_data:
                return {"segment_results": [], "info": "No segments found in range"}

            # Separate target and comparison data
            target_data_lookup = {}
            other_segments = []

            for row in all_segment_data:
                segment_id = row['segment_id']
                if segment_id in target_segments:
                    target_data_lookup[segment_id] = row
                else:
                    other_segments.append(row)

            if not other_segments:
                return {"segment_results": [], "info": "No comparison segments found"}

            # Get numerical columns for consistent normalization
            available_columns = [col for col in weights.keys()
                                 if col != 'movement_type'
                                 and all(col in row for row in all_segment_data)]

            if not available_columns:
                available_columns = ['duration', 'length', 'direction_x', 'direction_y', 'direction_z']
                available_columns = [col for col in available_columns
                                     if all(col in row for row in all_segment_data)]

            # Calculate similarity for each target segment
            segment_results = []

            for target_segment_id in target_segments:
                if target_segment_id not in target_data_lookup:
                    continue

                target_data = target_data_lookup[target_segment_id]

                # Prepare data for StandardScaler
                target_row_dict = {col: target_data.get(col, 0.0) for col in available_columns}
                compare_data_dicts = [{col: row.get(col, 0.0) for col in available_columns}
                                      for row in other_segments]

                all_data_for_scaling = [target_row_dict] + compare_data_dicts

                # Apply StandardScaler
                scaler = StandardScaler()
                data_matrix = np.array([[row[col] for col in available_columns]
                                        for row in all_data_for_scaling])
                scaled_data = scaler.fit_transform(data_matrix)

                target_scaled = scaled_data[0:1]
                compare_scaled = scaled_data[1:]

                # Calculate weighted distances
                weight_vector = np.array([weights.get(col, 1.0) for col in available_columns])
                distances = np.abs(compare_scaled - target_scaled)
                weighted_distances = (distances @ weight_vector) / weight_vector.sum()

                # Handle movement type
                if 'movement_type' in weights and 'movement_type' in target_data:
                    target_movement = str(target_data['movement_type'])
                    movement_weight = weights.get('movement_type', 1.0)
                    if movement_weight > 0:
                        movement_mismatch = np.array([
                            1.0 if str(row.get('movement_type', '')) != target_movement else 0.0
                            for row in other_segments
                        ], dtype=np.float32)
                        movement_penalty = movement_mismatch * movement_weight
                        weighted_distances = weighted_distances + (
                                movement_penalty / (weight_vector.sum() + movement_weight)
                        )

                # Create results with similarity scores
                similarities_with_scores = []
                for j, row in enumerate(other_segments):
                    row_copy = row.copy()
                    row_copy['similarity_score'] = weighted_distances[j]
                    similarities_with_scores.append(row_copy)

                similarities_sorted = sorted(similarities_with_scores, key=lambda x: x['similarity_score'])

                target_data['similarity_score'] = 0.0
                similar_segmente = similarities_sorted[:segment_limit]

                segment_results.append({
                    "target_segment": target_segment_id,
                    "similarity_data": {
                        "target": target_data,
                        "similar_segmente": similar_segmente,
                        "auto_threshold": 100.0,
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
            return {"error": f"Error in batch segment similarity search: {str(e)}"}

    # =================== UNIFIED HIERARCHICAL SEARCH ===================

    async def find_similar_bs(self, target_id: str, bahn_limit: int = 10,
                              segment_limit: int = 5,
                              weights: Dict[str, float] = None) -> Dict[str, Any]:
        """Hierarchical similarity search with batch optimization"""
        try:
            if weights is None:
                weights = self.default_weights.copy()

            # Detect ID type and determine target bahn
            id_type = self.detect_id_type(target_id)
            target_bahn_id = target_id if id_type == 'bahn' else target_id.split('_')[0]

            # Phase 1: Bahn similarity search
            bahn_results = await self.find_similar_bahnen(target_bahn_id, bahn_limit, weights)

            if "error" in bahn_results:
                return {"error": f"Bahn search failed: {bahn_results['error']}"}

            # Phase 2: Batch segment similarity search
            batch_results = await self.find_similar_segments(target_bahn_id, segment_limit, weights)

            if "error" in batch_results:
                segment_results = []
            elif "segment_results" in batch_results:
                segment_results = batch_results["segment_results"]
            else:
                segment_results = []

            # Calculate average segment threshold
            segment_thresholds = []
            for result in segment_results:
                threshold = result.get("similarity_data", {}).get("auto_threshold")
                if threshold is not None:
                    segment_thresholds.append(threshold)

            avg_segment_threshold = (
                sum(segment_thresholds) / len(segment_thresholds)
                if segment_thresholds else None
            )

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
            return {"error": f"Error in hierarchical similarity search: {str(e)}"}