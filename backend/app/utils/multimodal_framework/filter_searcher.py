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
                  AND seg_id = traj_id
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
                  AND seg_id != traj_id
                """
        results = await self.connection.fetch(query, seg_ids)
        return [r['seg_id'] for r in results]

    def calculate_movement_type_similarity(self, target_type: str, candidate_type: str) -> float:
        if not target_type or not candidate_type:
            return 0.0
        if target_type == candidate_type:
            return 1.0

        len_target = len(target_type)
        len_candidate = len(candidate_type)
        len_diff = abs(len_target - len_candidate)
        max_len = max(len_target, len_candidate)
        length_similarity = 1.0 - (len_diff / max_len) if max_len > 0 else 0.0

        min_len = min(len_target, len_candidate)
        matches = sum(1 for i in range(min_len) if target_type[i] == candidate_type[i])
        char_similarity = matches / max_len if max_len > 0 else 0.0

        return (0.6 * length_similarity) + (0.4 * char_similarity)

    async def get_target_features(self, target_id: str) -> Optional[Dict]:
        try:
            query = """
                    SELECT seg_id, traj_id, duration, weight, length, movement_type,
                           mean_vel, max_vel, std_vel,
                           min_accel, max_accel, mean_accel, std_accel,
                           position_x, position_y, position_z
                    FROM motion.traj_metadata
                    WHERE seg_id = $1
                    """
            result = await self.connection.fetchrow(query, target_id)
            if not result:
                logger.warning(f"Target {target_id} not found in traj_metadata")
                return None

            return {
                'seg_id':        result['seg_id'],
                'traj_id':       result['traj_id'],
                'duration':      float(result['duration'])   if result['duration']   else None,
                'length':        float(result['length'])     if result['length']     else None,
                'movement_type': result['movement_type']     if result['movement_type'] else None,
                'mean_vel':      float(result['mean_vel'])   if result['mean_vel']   else None,
                'max_vel':       float(result['max_vel'])    if result['max_vel']    else None,
                'std_vel':       float(result['std_vel'])    if result['std_vel']    else None,
                'min_accel':     float(result['min_accel'])  if result['min_accel']  else None,
                'max_accel':     float(result['max_accel'])  if result['max_accel']  else None,
                'mean_accel':    float(result['mean_accel']) if result['mean_accel'] else None,
                'std_accel':     float(result['std_accel'])  if result['std_accel']  else None,
                'position_x':    float(result['position_x']) if result['position_x'] else None,
                'position_y':    float(result['position_y']) if result['position_y'] else None,
                'position_z':    float(result['position_z']) if result['position_z'] else None,
            }

        except Exception as e:
            logger.error(f"Error getting target features for {target_id}: {e}")
            return None

    async def get_filtered_candidates(
        self,
        target_id: str,
        features_to_use: Optional[List[str]] = None,
        tolerance: float = None,
        include_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[str]:
        try:
            # ── Wenn nur Tag/ID-Filter ohne Feature-Filter ────────────────
            # (z.B. für externe Kandidaten die keine DB-Features haben)
            features_needed = features_to_use and len(features_to_use) > 0
            
            if not features_needed:
                # Direkt Tag/ID-Filter ohne target_features
                target_features = None
            else:
                target_features = await self.get_target_features(target_id)
                if not target_features:
                    logger.error(f"Cannot get features for target {target_id}")
                    return []

            if tolerance is None:
                tolerance = self.default_tolerance

            # Brauchen wir einen JOIN auf traj_info?
            need_join = bool(include_tags or exclude_tags or exclude_ids)

            # ── WHERE Clause aufbauen ─────────────────────────────────────
            where_clauses = []
            params = []
            param_idx = 1

            # Tag / Exclude Filter (benötigen JOIN)
            if include_tags:
                where_clauses.append(f"ti.tag = ANY(${param_idx})")
                params.append(include_tags)
                param_idx += 1
                logger.info(f"include_tags filter: {include_tags}")

            if exclude_tags:
                # NULL-Tags bleiben drin — nur explizit gesetzte Tags ausschließen
                where_clauses.append(
                    f"(ti.tag IS NULL OR ti.tag != ALL(${param_idx}))"
                )
                params.append(exclude_tags)
                param_idx += 1
                logger.info(f"exclude_tags filter: {exclude_tags}")

            if exclude_ids:
                # Ganzen traj_id-Eintrag ausschließen (trifft auch alle Segmente)
                where_clauses.append(
                    f"{'tm' if need_join else 'traj_metadata'}.traj_id != ALL(${param_idx})"
                )
                params.append(exclude_ids)
                param_idx += 1
                logger.info(f"exclude_ids filter: {len(exclude_ids)} IDs")

            # Feature-Filter (nur wenn features_to_use gesetzt)
            if features_to_use and len(features_to_use) > 0:

                if 'duration' in features_to_use and target_features['duration']:
                    dur = target_features['duration']
                    where_clauses.append(f"{'tm.' if need_join else ''}duration BETWEEN ${param_idx} AND ${param_idx + 1}")
                    params.extend([dur * (1 - tolerance), dur * (1 + tolerance)])
                    param_idx += 2

                if 'length' in features_to_use and target_features['length']:
                    length = target_features['length']
                    where_clauses.append(f"{'tm.' if need_join else ''}length BETWEEN ${param_idx} AND ${param_idx + 1}")
                    params.extend([length * (1 - tolerance), length * (1 + tolerance)])
                    param_idx += 2

                if 'velocity_profile' in features_to_use:
                    velocity_keys = ['mean_vel', 'max_vel', 'std_vel']
                    if all(target_features.get(k) for k in velocity_keys):
                        abs_tol = target_features['max_vel'] * self.profile_tolerance
                        for key in velocity_keys:
                            val = target_features[key]
                            prefix = 'tm.' if need_join else ''
                            where_clauses.append(f"{prefix}{key} BETWEEN ${param_idx} AND ${param_idx + 1}")
                            params.extend([val - abs_tol, val + abs_tol])
                            param_idx += 2

                if 'acceleration_profile' in features_to_use:
                    accel_keys = ['min_accel', 'max_accel', 'mean_accel', 'std_accel']
                    if all(target_features.get(k) for k in accel_keys):
                        abs_tol = target_features['max_accel'] * self.profile_tolerance
                        for key in accel_keys:
                            val = target_features[key]
                            prefix = 'tm.' if need_join else ''
                            where_clauses.append(f"{prefix}{key} BETWEEN ${param_idx} AND ${param_idx + 1}")
                            params.extend([val - abs_tol, val + abs_tol])
                            param_idx += 2

                if 'position_3d' in features_to_use:
                    position_keys = ['position_x', 'position_y', 'position_z']
                    if all(target_features.get(k) is not None for k in position_keys):
                        spatial_tol = 200.0
                        for key in position_keys:
                            val = target_features[key]
                            prefix = 'tm.' if need_join else ''
                            where_clauses.append(f"{prefix}{key} BETWEEN ${param_idx} AND ${param_idx + 1}")
                            params.extend([val - spatial_tol, val + spatial_tol])
                            param_idx += 2

            # Exclude Target selbst
            seg_col = "tm.seg_id" if need_join else "seg_id"
            where_clauses.append(f"{seg_col} != ${param_idx}")
            params.append(target_id)
            param_idx += 1

            where_clause = " AND ".join(where_clauses) if where_clauses else "TRUE"

            # ── SQL Query bauen ───────────────────────────────────────────
            use_movement_type = (
                features_to_use
                and 'movement_type' in features_to_use
            )

            if need_join:
                select_cols = "tm.seg_id" + (", tm.movement_type" if use_movement_type else "")
                query = f"""
                    SELECT {select_cols}
                    FROM motion.traj_metadata tm
                    JOIN motion.traj_info ti ON tm.traj_id = ti.traj_id
                    WHERE {where_clause}
                """
            else:
                select_cols = "seg_id" + (", movement_type" if use_movement_type else "")
                query = f"""
                    SELECT {select_cols}
                    FROM motion.traj_metadata
                    WHERE {where_clause}
                """

            logger.info(f"Pre-filter query with {len(where_clauses)} conditions "
                        f"(join={'yes' if need_join else 'no'})")

            results = await self.connection.fetch(query, *params)

            # ── Movement Type Filtering ───────────────────────────────────
            target_movement_type = target_features.get('movement_type')

            if use_movement_type and target_movement_type:
                exact_matches = []
                similarity_matches = []
                for row in results:
                    cmt = row['movement_type']
                    if not cmt:
                        continue
                    if cmt == target_movement_type:
                        exact_matches.append(row['seg_id'])
                    else:
                        sim = self.calculate_movement_type_similarity(
                            target_movement_type, cmt
                        )
                        if sim >= self.movement_type_threshold:
                            similarity_matches.append(row['seg_id'])

                candidate_ids = exact_matches + similarity_matches
                logger.info(
                    f"Movement type filter '{target_movement_type}': "
                    f"{len(exact_matches)} exact, {len(similarity_matches)} similar"
                )
            else:
                candidate_ids = [row['seg_id'] for row in results]

            logger.info(f"Pre-filter found {len(candidate_ids)} candidates for {target_id}")
            return candidate_ids

        except Exception as e:
            logger.error(f"Error in pre-filter search for {target_id}: {e}")
            return []