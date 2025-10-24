# backend/app/utils/prefilter_searcher.py

import asyncpg
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class PreFilterSearcher:
    """
    Pre-Filter Searcher für Feature-basierte Kandidaten-Filterung
    Reduziert Suchraum vor Vector Search
    """

    def __init__(self, connection: asyncpg.Connection):
        self.connection = connection
        self.default_tolerance = 25  # ±25% Range

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
        Holt ALLE Features für Target Bahn/Segment

        Returns:
            Dict mit: duration, length, ALL twist columns, ALL accel columns
            None wenn nicht gefunden
        """
        try:
            query = """
                    SELECT segment_id, \
                           bahn_id, \
                           duration, \
                           length, \
                           movement_type, \
                           min_twist_ist, \
                           max_twist_ist, \
                           mean_twist_ist, \
                           median_twist_ist, \
                           std_twist_ist, \
                           min_acceleration_ist, \
                           max_acceleration_ist, \
                           mean_acceleration_ist, \
                           median_acceleration_ist, \
                           std_acceleration_ist
                    FROM bewegungsdaten.bahn_metadata
                    WHERE segment_id = $1 \
                    """

            result = await self.connection.fetchrow(query, target_id)

            if not result:
                logger.warning(f"Target {target_id} not found in bahn_metadata")
                return None

            return {
                'segment_id': result['segment_id'],
                'bahn_id': result['bahn_id'],
                'duration': float(result['duration']) if result['duration'] else None,
                'length': float(result['length']) if result['length'] else None,
                'movement_type': (result['movement_type']) if result['movement_type'] else None,
                # Twist (5 Spalten)
                'min_twist_ist': float(result['min_twist_ist']) if result['min_twist_ist'] else None,
                'max_twist_ist': float(result['max_twist_ist']) if result['max_twist_ist'] else None,
                'mean_twist_ist': float(result['mean_twist_ist']) if result['mean_twist_ist'] else None,
                'median_twist_ist': float(result['median_twist_ist']) if result['median_twist_ist'] else None,
                'std_twist_ist': float(result['std_twist_ist']) if result['std_twist_ist'] else None,
                # Acceleration (5 Spalten)
                'min_acceleration_ist': float(result['min_acceleration_ist']) if result[
                    'min_acceleration_ist'] else None,
                'max_acceleration_ist': float(result['max_acceleration_ist']) if result[
                    'max_acceleration_ist'] else None,
                'mean_acceleration_ist': float(result['mean_acceleration_ist']) if result[
                    'mean_acceleration_ist'] else None,
                'median_acceleration_ist': float(result['median_acceleration_ist']) if result[
                    'median_acceleration_ist'] else None,
                'std_acceleration_ist': float(result['std_acceleration_ist']) if result[
                    'std_acceleration_ist'] else None
            }

        except Exception as e:
            logger.error(f"Error getting target features for {target_id}: {e}")
            return None

    def calculate_ranges(
            self,
            target_features: Dict,
            tolerance: float = None,
            custom_ranges: Optional[Dict[str, Tuple[float, float]]] = None,
            features_to_use: Optional[List[str]] = None
    ) -> Dict[str, Tuple[float, float]]:
        """
        Berechnet Min/Max Ranges für Pre-Filter

        Args:
            target_features: Dict mit Target-Werten
            tolerance: ±Prozent Range (default: 0.25 = ±25%)
            custom_ranges: Optional Dict mit expliziten Ranges
            features_to_use: Welche Features filtern? (None = alle verfügbaren)

        Returns:
            Dict: {'duration': (min, max), 'mean_twist_ist': (min, max), ...}
        """
        if tolerance is None:
            tolerance = self.default_tolerance

        ranges = {}

        # ALLE verfügbaren Filter-Features (14 Spalten - 3 = 11 numerische)
        all_filter_features = [
            'duration',
            'length',
            'min_twist_ist',
            'max_twist_ist',
            'mean_twist_ist',
            'median_twist_ist',
            'std_twist_ist',
            'min_acceleration_ist',
            'max_acceleration_ist',
            'mean_acceleration_ist',
            'median_acceleration_ist',
            'std_acceleration_ist'
        ]

        # Welche Features nutzen?
        if features_to_use is None:
            features_to_use = all_filter_features

        for feature in features_to_use:
            value = target_features.get(feature)

            if value is None or value == 0:
                # Skip features ohne Werte
                continue

            # Custom Range hat Priorität
            if custom_ranges and feature in custom_ranges:
                ranges[feature] = custom_ranges[feature]
            else:
                # ±tolerance Range
                min_val = value * (1 - tolerance)
                max_val = value * (1 + tolerance)
                ranges[feature] = (min_val, max_val)

        return ranges

    async def get_filtered_candidates(
            self,
            target_id: str,
            tolerance: float = None,
            custom_ranges: Optional[Dict[str, Tuple[float, float]]] = None,
            features_to_use: Optional[List[str]] = None,
            exclude_target: bool = True,
            same_bahn_only: bool = False,
            limit: Optional[int] = None,
            movement_type_threshold: float = 0.7
    ) -> List[str]:
        """
        Hauptfunktion: Pre-Filter basierend auf Target Features

        Args:
            target_id: Target Segment/Bahn ID
            tolerance: ±Prozent Range (default: 0.25)
            custom_ranges: Optional custom ranges
            features_to_use: Welche Features filtern? (None = alle)
            exclude_target: Target aus Ergebnissen ausschließen
            same_bahn_only: Nur Segmente der gleichen Bahn (für Segment-Search)
            limit: Max Anzahl Kandidaten (None = unbegrenzt)
            movement_type_threshold: Mindest-Ähnlichkeit für movement_type String-Match

        Returns:
            List von segment_ids die den Filter passieren
        """
        try:
            # 1. Hole Target Features
            target_features = await self.get_target_features(target_id)

            if not target_features:
                logger.error(f"Cannot get features for target {target_id}")
                return []

            target_movement_type = target_features.get('movement_type')
            
            # Check ob movement_type überhaupt gefiltert werden soll
            use_movement_type_filter = features_to_use and 'movement_type' in features_to_use

            # 2. Berechne Ranges (nur für numerische Features)
            # Filtere movement_type aus features_to_use bevor calculate_ranges aufgerufen wird
            if features_to_use:
                numeric_features = [f for f in features_to_use if f != 'movement_type']
            else:
                numeric_features = None
            
            ranges = self.calculate_ranges(target_features, tolerance, custom_ranges, numeric_features)

            # 3. Baue WHERE Clause (nur numerische Features)
            where_clauses = []
            params = []
            param_idx = 1

            for feature, (min_val, max_val) in ranges.items():
                where_clauses.append(f"{feature} BETWEEN ${param_idx} AND ${param_idx + 1}")
                params.extend([min_val, max_val])
                param_idx += 2

            # Exclude Target
            if exclude_target:
                where_clauses.append(f"segment_id != ${param_idx}")
                params.append(target_id)
                param_idx += 1

            # Same Bahn Filter
            if same_bahn_only:
                target_bahn_id = target_features['bahn_id']
                where_clauses.append(f"bahn_id = ${param_idx}")
                params.append(target_bahn_id)
                param_idx += 1

            where_clause = " AND ".join(where_clauses) if where_clauses else "TRUE"

            # 4. Query - hole auch movement_type zurück wenn nötig
            query = f"""
                SELECT segment_id{', movement_type' if use_movement_type_filter else ''}
                FROM bewegungsdaten.bahn_metadata
                WHERE {where_clause}
                ORDER BY duration
            """

            logger.info(f"Pre-filter query for {target_id}: {len(where_clauses)} conditions, {len(ranges)} numeric features")

            results = await self.connection.fetch(query, *params)

            # 5. Movement Type Filtering (falls aktiviert)
            candidate_ids = []
            
            if use_movement_type_filter:
                for row in results:
                    candidate_movement_type = row['movement_type']
                    
                    if target_movement_type and candidate_movement_type:
                        similarity = self.calculate_movement_type_similarity(
                            target_movement_type, 
                            candidate_movement_type
                        )
                        
                        if similarity >= movement_type_threshold:
                            candidate_ids.append(row['segment_id'])
                    elif not target_movement_type:
                        # Kein movement_type beim Target -> alle nehmen
                        candidate_ids.append(row['segment_id'])
            else:
                # Kein movement_type filtering
                candidate_ids = [row['segment_id'] for row in results]
            
            # 6. Apply Limit nach movement_type filtering
            if limit and len(candidate_ids) > limit:
                candidate_ids = candidate_ids[:limit]

            logger.info(f"Pre-filter found {len(candidate_ids)} candidates for {target_id}")

            return candidate_ids

        except Exception as e:
            logger.error(f"Error in pre-filter search for {target_id}: {e}")
            return []

    async def estimate_candidate_count(
            self,
            target_id: str,
            tolerance: float = None,
            custom_ranges: Optional[Dict[str, Tuple[float, float]]] = None,
            features_to_use: Optional[List[str]] = None
    ) -> int:
        """
        Schätzt Anzahl Kandidaten OHNE sie zu laden (für Optimization)

        Returns:
            Geschätzte Anzahl Kandidaten
        """
        try:
            target_features = await self.get_target_features(target_id)

            if not target_features:
                return 0

            ranges = self.calculate_ranges(target_features, tolerance, custom_ranges, features_to_use)

            if not ranges:
                return 0

            # COUNT Query
            where_clauses = []
            params = []
            param_idx = 1

            for feature, (min_val, max_val) in ranges.items():
                where_clauses.append(f"{feature} BETWEEN ${param_idx} AND ${param_idx + 1}")
                params.extend([min_val, max_val])
                param_idx += 2

            where_clauses.append(f"segment_id != ${param_idx}")
            params.append(target_id)

            where_clause = " AND ".join(where_clauses)

            query = f"""
                SELECT COUNT(*) as count
                FROM bewegungsdaten.bahn_metadata
                WHERE {where_clause}
            """

            result = await self.connection.fetchrow(query, *params)
            count = result['count'] if result else 0

            logger.info(f"Estimated {count} candidates for {target_id} (tolerance={tolerance}, features={len(ranges)})")

            return count

        except Exception as e:
            logger.error(f"Error estimating candidate count: {e}")
            return 0

    async def adaptive_prefilter(
            self,
            target_id: str,
            max_candidates: int = 10000,
            min_candidates: int = 100,
            features_to_use: Optional[List[str]] = None
    ) -> Tuple[List[str], float]:
        """
        ADAPTIVE Pre-Filter: Passt Tolerance an um optimale Kandidaten-Anzahl zu finden

        Args:
            target_id: Target ID
            max_candidates: Max gewünschte Kandidaten
            min_candidates: Min gewünschte Kandidaten
            features_to_use: Welche Features nutzen?

        Returns:
            (candidate_ids, verwendete_tolerance)
        """
        try:
            # Versuche verschiedene Tolerances
            tolerances = [0.15, 0.25, 0.35, 0.50, 0.75, 1.0]

            for tolerance in tolerances:
                count = await self.estimate_candidate_count(target_id, tolerance, features_to_use=features_to_use)

                logger.info(f"Tolerance {tolerance}: ~{count} candidates")

                if min_candidates <= count <= max_candidates:
                    # Perfect range!
                    candidates = await self.get_filtered_candidates(
                        target_id,
                        tolerance,
                        features_to_use=features_to_use
                    )
                    return candidates, tolerance

                elif count > max_candidates:
                    # Zu viele, nutze kleinere tolerance
                    if tolerance == tolerances[0]:
                        # Schon kleinste tolerance, nehme limit
                        candidates = await self.get_filtered_candidates(
                            target_id,
                            tolerance,
                            features_to_use=features_to_use,
                            limit=max_candidates
                        )
                        return candidates, tolerance
                    continue

            # Fallback: Nutze größte tolerance
            candidates = await self.get_filtered_candidates(
                target_id,
                tolerances[-1],
                features_to_use=features_to_use
            )
            return candidates, tolerances[-1]

        except Exception as e:
            logger.error(f"Error in adaptive prefilter: {e}")
            return [], 0.25
        
