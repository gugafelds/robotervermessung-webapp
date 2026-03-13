# backend/app/utils/filter_searcher.py

import asyncpg
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FilterSearcher:
    """
    Filter Searcher für Feature-basierte Kandidaten-Filterung
    Reduziert Suchraum vor Vector Search

    Einfache Logik: ±10% Tolerance für numerische Features, Similarity für movement_type
    """

    def __init__(self, connection: asyncpg.Connection):
        self.connection = connection
        self.default_tolerance = 0.10  # ±10%
        self.movement_type_threshold = 0.9  # Mindest-Similarity für movement_type
        self.profile_tolerance = 0.10  # ±10% für velocity/acceleration profiles

    async def _filter_only_trajs(self, seg_ids: List[str]) -> List[str]:
        """Filtert Liste: Nur Bahnen (seg_id = traj_id)"""
        if not seg_ids:
            return []

        query = """
                SELECT seg_id
                FROM motion.traj_metadata
                WHERE seg_id = ANY ($1)
                  AND seg_id = traj_id \
                """
        results = await self.connection.fetch(query, seg_ids)
        return [r['seg_id'] for r in results]

    async def _filter_only_segments(self, seg_ids: List[str]) -> List[str]:
        """Filtert Liste: Nur Segmente (seg_id != traj_id)"""
        if not seg_ids:
            return []

        query = """
                SELECT seg_id
                FROM motion.traj_metadata
                WHERE seg_id = ANY ($1)
                  AND seg_id != traj_id \
                """
        results = await self.connection.fetch(query, seg_ids)
        return [r['seg_id'] for r in results]

    def calculate_movement_type_similarity(self, target_type: str, candidate_type: str) -> float:
        """
        Berechnet Ähnlichkeit zwischen zwei movement_type Strings

        Priorisiert:
        1. Gleiche Länge (wichtiger)
        2. Character-Übereinstimmung (weniger wichtig)

        Returns:
            Score zwischen 0.0 (keine Ähnlichkeit) und 1.0 (identisch)
        """
        if not target_type or not candidate_type:
            return 0.0

        if target_type == candidate_type:
            return 1.0

        # Length difference penalty
        len_target = len(target_type)
        len_candidate = len(candidate_type)
        len_diff = abs(len_target - len_candidate)

        # Length similarity (0.0 bis 1.0)
        max_len = max(len_target, len_candidate)
        length_similarity = 1.0 - (len_diff / max_len) if max_len > 0 else 0.0

        # Character overlap (Jaccard-ähnlich)
        min_len = min(len_target, len_candidate)
        matches = sum(1 for i in range(min_len) if target_type[i] == candidate_type[i])
        char_similarity = matches / max_len if max_len > 0 else 0.0

        # Gewichtung: 60% Länge, 40% Characters
        total_score = (0.6 * length_similarity) + (0.4 * char_similarity)

        return total_score

    async def get_target_features(self, target_id: str) -> Optional[Dict]:
        """
        Holt Features für Target Bahn/Segment

        Returns:
            Dict mit: duration, length, movement_type
            None wenn nicht gefunden
        """
        try:
            query = """
                    SELECT seg_id,
                           traj_id,
                           duration,
                           weight,
                           length,
                           movement_type,
                           mean_vel_act,
                           max_vel_act,
                           std_vel_act,
                           min_accel_act,
                           max_accel_act,
                           mean_accel_act,
                           std_accel_act,
                           position_x,
                           position_y,
                           position_z
                    FROM motion.traj_metadata
                    WHERE seg_id = $1 \
                    """

            result = await self.connection.fetchrow(query, target_id)

            if not result:
                logger.warning(f"Target {target_id} not found in traj_metadata")
                return None

            return {
                'seg_id': result['seg_id'],
                'traj_id': result['traj_id'],
                'duration': float(result['duration']) if result['duration'] else None,
                'length': float(result['length']) if result['length'] else None,
                'movement_type': result['movement_type'] if result['movement_type'] else None,
                # Twist Profile
                'mean_vel_act': float(result['mean_vel_act']) if result['mean_vel_act'] else None,
                'max_vel_act': float(result['max_vel_act']) if result['max_vel_act'] else None,
                'std_vel_act': float(result['std_vel_act']) if result['std_vel_act'] else None,
                # Acceleration Profile
                'min_accel_act': float(result['min_accel_act']) if result[
                    'min_accel_act'] else None,
                'max_accel_act': float(result['max_accel_act']) if result[
                    'max_accel_act'] else None,
                'mean_accel_act': float(result['mean_accel_act']) if result[
                    'mean_accel_act'] else None,
                'std_accel_act': float(result['std_accel_act']) if result[
                    'std_accel_act'] else None,
                # Position 3D
                'position_x': float(result['position_x']) if result['position_x'] else None,
                'position_y': float(result['position_y']) if result['position_y'] else None,
                'position_z': float(result['position_z']) if result['position_z'] else None,
            }

        except Exception as e:
            logger.error(f"Error getting target features for {target_id}: {e}")
            return None

    async def get_filtered_candidates(
            self,
            target_id: str,
            features_to_use: Optional[List[str]] = None,
            tolerance: float = None
    ) -> List[str]:
        """
        Hauptfunktion: Pre-Filter basierend auf ausgewählten Features

        Einfache Logik:
        - Numerische Features (duration, length): ±10% Range
        - movement_type: Similarity-basiert (Exakt bevorzugt, dann ähnlich)

        Args:
            target_id: Target Segment/Bahn ID
            features_to_use: Welche Features filtern? ['duration', 'length', 'movement_type']
            tolerance: Override für default tolerance (0.10 = ±10%)

        Returns:
            List von seg_ids die den Filter passieren
        """
        try:
            # 1. Hole Target Features
            target_features = await self.get_target_features(target_id)

            if not target_features:
                logger.error(f"Cannot get features for target {target_id}")
                return []

            # Default: Alle Features nutzen
            if not features_to_use or len(features_to_use) == 0:
                logger.info(f"No prefilter features selected, returning all candidates")
                query = """
                        SELECT seg_id
                        FROM motion.traj_metadata
                        WHERE seg_id != $1 \
                        """
                results = await self.connection.fetch(query, target_id)
                candidate_ids = [row['seg_id'] for row in results]
                logger.info(f"No prefilter: {len(candidate_ids)} total candidates")
                return candidate_ids

            # Default tolerance
            if tolerance is None:
                tolerance = self.default_tolerance

            # 2. Baue WHERE Clause dynamisch
            where_clauses = []
            params = []
            param_idx = 1

            # Numerische Features: duration, length
            if 'duration' in features_to_use and target_features['duration']:
                duration = target_features['duration']
                min_duration = duration * (1 - tolerance)
                max_duration = duration * (1 + tolerance)
                where_clauses.append(f"duration BETWEEN ${param_idx} AND ${param_idx + 1}")
                params.extend([min_duration, max_duration])
                param_idx += 2
                logger.info(f"Duration filter: {min_duration:.2f} - {max_duration:.2f}")

            if 'length' in features_to_use and target_features['length']:
                length = target_features['length']
                min_length = length * (1 - tolerance)
                max_length = length * (1 + tolerance)
                where_clauses.append(f"length BETWEEN ${param_idx} AND ${param_idx + 1}")
                params.extend([min_length, max_length])
                param_idx += 2
                logger.info(f"Length filter: {min_length:.2f} - {max_length:.2f}")

            if 'velocity_profile' in features_to_use:
                velocity_keys = ['mean_vel_act', 'max_vel_act', 'std_vel_act']
                if all(target_features.get(k) for k in velocity_keys):
                    # ✅ Berechne absolute Toleranz von STD
                    std_val = target_features['max_vel_act']
                    absolute_tolerance = std_val * self.profile_tolerance

                    for key in velocity_keys:
                        val = target_features[key]
                        min_val = val - absolute_tolerance
                        max_val = val + absolute_tolerance

                        where_clauses.append(f"{key} BETWEEN ${param_idx} AND ${param_idx + 1}")
                        params.extend([min_val, max_val])
                        param_idx += 2

                    logger.info(
                        f"Velocity profile filter: ±{absolute_tolerance:.1f} "
                        f"(based on std={std_val:.1f})"
                    )

            if 'acceleration_profile' in features_to_use:
                accel_keys = ['min_accel_act', 'max_accel_act', 'mean_accel_act',
                              'std_accel_act']

                if all(target_features.get(k) for k in accel_keys):
                    # ✅ Berechne absolute Toleranz von STD
                    std_val = target_features['max_accel_act']
                    absolute_tolerance = std_val * self.profile_tolerance

                    for key in accel_keys:
                        val = target_features[key]
                        min_val = val - absolute_tolerance
                        max_val = val + absolute_tolerance

                        where_clauses.append(f"{key} BETWEEN ${param_idx} AND ${param_idx + 1}")
                        params.extend([min_val, max_val])
                        param_idx += 2

                    logger.info(
                        f"Acceleration profile filter: ±{absolute_tolerance:.1f} "
                        f"(based on std={std_val:.1f})"
                    )

            if 'position_3d' in features_to_use:
                position_keys = ['position_x', 'position_y', 'position_z']
                if all(target_features.get(k) is not None for k in position_keys):

                    # ✅ Absolute Toleranz in mm
                    spatial_tolerance_mm = 200.0  # ±200mm in alle Richtungen

                    for key in position_keys:
                        val = target_features[key]
                        min_val = val - spatial_tolerance_mm  # ✅ Funktioniert bei negativen!
                        max_val = val + spatial_tolerance_mm
                        where_clauses.append(f"{key} BETWEEN ${param_idx} AND ${param_idx + 1}")
                        params.extend([min_val, max_val])
                        param_idx += 2

                    logger.info(
                        f"Position 3D filter (±{spatial_tolerance_mm}mm): "
                        f"X=[{target_features['position_x'] - spatial_tolerance_mm:.1f}, "
                        f"{target_features['position_x'] + spatial_tolerance_mm:.1f}], "
                        f"Y=[{target_features['position_y'] - spatial_tolerance_mm:.1f}, "
                        f"{target_features['position_y'] + spatial_tolerance_mm:.1f}], "
                        f"Z=[{target_features['position_z'] - spatial_tolerance_mm:.1f}, "
                        f"{target_features['position_z'] + spatial_tolerance_mm:.1f}]"
                    )

            # Exclude Target
            where_clauses.append(f"seg_id != ${param_idx}")
            params.append(target_id)
            param_idx += 1

            where_clause = " AND ".join(where_clauses) if where_clauses else "TRUE"

            # 3. Check ob movement_type gefiltert werden soll
            use_movement_type = 'movement_type' in features_to_use
            target_movement_type = target_features.get('movement_type')

            # 4. SQL Query
            query = f"""
                SELECT seg_id{', movement_type' if use_movement_type else ''}
                FROM motion.traj_metadata
                WHERE {where_clause}
            """

            logger.info(f"Pre-filter query with {len(where_clauses)} conditions")

            results = await self.connection.fetch(query, *params)

            # 5. Movement Type Filtering (falls aktiviert)
            candidate_ids = []

            if use_movement_type and target_movement_type:
                # 2-Stufen-Strategie: Exakt zuerst, dann Similarity
                exact_matches = []
                similarity_matches = []

                for row in results:
                    candidate_movement_type = row['movement_type']

                    if not candidate_movement_type:
                        continue

                    # Exakter Match?
                    if target_movement_type == candidate_movement_type:
                        exact_matches.append(row['seg_id'])
                    else:
                        # Similarity berechnen
                        similarity = self.calculate_movement_type_similarity(
                            target_movement_type,
                            candidate_movement_type
                        )

                        if similarity >= self.movement_type_threshold:
                            similarity_matches.append(row['seg_id'])

                # Bevorzuge exakte Matches, dann Similarity
                candidate_ids = exact_matches + similarity_matches

                logger.info(
                    f"Movement type filter '{target_movement_type}': "
                    f"{len(exact_matches)} exact, {len(similarity_matches)} similar "
                    f"(>= {self.movement_type_threshold})"
                )

            else:
                # Kein movement_type filtering
                candidate_ids = [row['seg_id'] for row in results]

            logger.info(f"Pre-filter found {len(candidate_ids)} candidates for {target_id}")

            return candidate_ids

        except Exception as e:
            logger.error(f"Error in pre-filter search for {target_id}: {e}")
            return []