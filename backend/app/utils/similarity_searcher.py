# backend/app/utils/similarity_searcher.py - Complex Core Functions

import asyncio
import asyncpg
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from decimal import Decimal


class SimilaritySearcher:
    def __init__(self, connection):
        self.connection = connection
        # Default weights - können später konfigurierbar gemacht werden
        self.default_weights = {
            'duration': 1.0,
            'weight': 1.0, 
            'length': 1.0,
            'movement_type': 1.0,
            'direction_x': 1.0,
            'direction_y': 1.0,
            'direction_z': 1.0
        }

    def normalize_id(self, id_value) -> Optional[str]:
        """
        Normalisiert IDs für konsistente Vergleiche
        """
        if not id_value:
            return None
        
        id_str = str(id_value)
        
        if '_' in id_str:
            return id_str
        
        try:
            id_float = float(id_str)
            if id_float.is_integer():
                return str(int(id_float))
            else:
                return str(id_float)
        except (ValueError, TypeError):
            return id_str

    def detect_id_type(self, target_id: str) -> str:
        """
        Erkennt automatisch ob es sich um eine Bahn-ID oder Segment-ID handelt
        """
        normalized_id = self.normalize_id(target_id)
        if normalized_id and '_' in normalized_id:
            return 'segment'
        return 'bahn'

    def _calculate_percentile_threshold(self, target_value: float, all_values: np.ndarray) -> float:
        """
        Berechnet Schwellwert basierend auf Perzentil-Position des Target-Values
        """
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

    async def calculate_weighted_similarity_optimized(self, target_row: pd.DataFrame, 
                                                     compare_df: pd.DataFrame, 
                                                     weights: Dict[str, float]) -> pd.DataFrame:
        """
        KOMPLEXE Ähnlichkeitsberechnung aus der Python-App - optimiert für async
        """
        # Numerische Spalten die verfügbar sind
        available_columns = [col for col in weights.keys()
                           if col in target_row.columns
                           and col in compare_df.columns
                           and col != 'movement_type']

        if not available_columns:
            # Fallback auf minimale Spalten
            available_columns = ['duration', 'length', 'direction_x', 'direction_y', 'direction_z']
            available_columns = [col for col in available_columns
                               if col in target_row.columns and col in compare_df.columns]

        # Direkte NumPy Arrays für Performance
        target_values = target_row[available_columns].fillna(0).values[0]
        compare_values = compare_df[available_columns].fillna(0).values

        # Normalisierung mit Broadcasting (wie in Python-App)
        all_values = np.vstack([target_values, compare_values])

        # StandardScaler-ähnliche Normalisierung
        means = np.mean(all_values, axis=0)
        stds = np.std(all_values, axis=0)
        stds[stds == 0] = 1  # Verhindere Division durch 0

        target_normalized = (target_values - means) / stds
        compare_normalized = (compare_values - means) / stds

        # Gewichtungsvektor
        weight_vector = np.array([weights.get(col, 1.0) for col in available_columns])

        # Vektorisierte Distanzberechnung (absolute Werte wie in Python-App)
        distances = np.abs(compare_normalized - target_normalized)
        weighted_distances = (distances @ weight_vector) / weight_vector.sum()

        # Movement type handling (komplexe Logik aus Python-App)
        if 'movement_type' in target_row.columns and 'movement_type' in compare_df.columns:
            target_movement = str(target_row['movement_type'].iloc[0])
            movement_weight = weights.get('movement_type', 1.0)

            # Vektorisierte String-Vergleiche
            compare_movements = compare_df['movement_type'].astype(str).values
            movement_mismatch = (compare_movements != target_movement).astype(float)

            # Movement penalty wie in Python-App
            movement_penalty = movement_mismatch * movement_weight / (weight_vector.sum() + movement_weight)
            weighted_distances = weighted_distances + movement_penalty

        # Ergebnis zuweisen
        result_df = compare_df.copy()
        result_df['similarity_score'] = weighted_distances

        # Sortierung
        return result_df.sort_values('similarity_score', inplace=False)

    async def load_data_with_features(self, where_condition: str, params: tuple = None) -> pd.DataFrame:
        """
        Lädt Daten mit allen Features für komplexe Ähnlichkeitsberechnung
        """
        query = """
        SELECT bm.bahn_id, bm.segment_id, bm.meta_value,
               CAST(bm.duration AS FLOAT) as duration,
               CAST(bm.weight AS FLOAT) as weight,
               CAST(bm.length AS FLOAT) as length,
               bm.movement_type,
               CAST(bm.direction_x AS FLOAT) as direction_x,
               CAST(bm.direction_y AS FLOAT) as direction_y,
               CAST(bm.direction_z AS FLOAT) as direction_z,
               CAST(bm.min_position_x_soll AS FLOAT) as min_position_x_soll,
               CAST(bm.min_position_y_soll AS FLOAT) as min_position_y_soll,
               CAST(bm.min_position_z_soll AS FLOAT) as min_position_z_soll,
               CAST(bm.max_position_x_soll AS FLOAT) as max_position_x_soll,
               CAST(bm.max_position_y_soll AS FLOAT) as max_position_y_soll,
               CAST(bm.max_position_z_soll AS FLOAT) as max_position_z_soll,
               CAST(ist.sidtw_average_distance AS FLOAT) as sidtw_average_distance,
               CAST(bm.bahn_id AS TEXT) as bahn_id_normalized,
               CAST(bm.segment_id AS TEXT) as segment_id_normalized
        FROM robotervermessung.bewegungsdaten.bahn_meta bm
        LEFT JOIN robotervermessung.auswertung.info_sidtw ist 
            ON CAST(bm.segment_id AS TEXT) = ist.segment_id 
            AND ist.evaluation = 'position'
        """ + where_condition

        if params:
            results = await self.connection.fetch(query, *params)
        else:
            results = await self.connection.fetch(query)

        # Konvertiere zu DataFrame
        if not results:
            return pd.DataFrame()

        # Konvertiere Ergebnisse zu DataFrame
        df = pd.DataFrame([dict(row) for row in results])
        return df
    
################## BAHNEN #####################

    async def calculate_adaptive_threshold_bahn(self, target_meta_value: float, strategy: str = "percentile") -> float:
        """
        Berechnet automatisch optimalen Schwellwert für Bahnen basierend auf Meta-Value-Verteilung
        """
        try:
            query = """
            SELECT CAST(meta_value AS FLOAT) as meta_value 
            FROM robotervermessung.bewegungsdaten.bahn_meta bm
            WHERE CAST(bm.bahn_id AS TEXT) = CAST(bm.segment_id AS TEXT)
            AND meta_value IS NOT NULL
            ORDER BY meta_value
            """
            
            results = await self.connection.fetch(query)
            if len(results) < 10:
                return 20.0
            
            meta_values = np.array([row['meta_value'] for row in results])
            
            if strategy == "percentile":
                return self._calculate_percentile_threshold(target_meta_value, meta_values)
            else:
                return 20.0
                
        except Exception as e:
            print(f"Fehler bei adaptive Schwellwert-Berechnung: {e}")
            return 20.0

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
        
        result = await self.connection.fetchrow(query, self.normalize_id(bahn_id))
        return result['meta_value'] if result and result['meta_value'] is not None else None

    async def find_similar_bahnen_complex(self, target_bahn_id: str, limit: int = 10, 
                                        weights: Dict[str, float] = None) -> Dict[str, Any]:
        """
        KOMPLEXE Bahn-Ähnlichkeitssuche mit vollständiger Feature-Berechnung
        """
        try:
            if weights is None:
                weights = self.default_weights.copy()
                
            target_bahn_id_normalized = self.normalize_id(target_bahn_id)
            
            # 1. Target Meta-Value für Threshold-Berechnung laden
            target_meta_value = await self.get_target_bahn_meta_value(target_bahn_id_normalized)
            if target_meta_value is None:
                return {"error": f"Target-Bahn {target_bahn_id} hat keinen Meta-Value"}
            
            # 2. Adaptive Schwellwert-Berechnung
            adaptive_threshold = await self.calculate_adaptive_threshold_bahn(target_meta_value)
            
            # 3. Meta-Value Bereich für Vorfilterung
            threshold_factor = adaptive_threshold / 100.0
            meta_value_min = target_meta_value * (1 - threshold_factor)
            meta_value_max = target_meta_value * (1 + threshold_factor)
            
            # 4. Alle Bahnen im Meta-Value-Bereich laden (mit allen Features)
            where_condition = """
            WHERE CAST(bm.bahn_id AS TEXT) = CAST(bm.segment_id AS TEXT)
            AND bm.meta_value BETWEEN $1 AND $2
            ORDER BY bm.meta_value
            """
            
            df_all = await self.load_data_with_features(
                where_condition, 
                (meta_value_min, meta_value_max)
            )
            
            if df_all.empty:
                return {"error": f"Keine Bahnen im Meta-Value-Bereich gefunden"}
            
            # 5. Target und andere Bahnen trennen
            target_mask = df_all['bahn_id_normalized'] == target_bahn_id_normalized
            target_row = df_all[target_mask]
            other_bahnen = df_all[~target_mask].copy()
            
            if target_row.empty:
                return {"error": f"Target-Bahn nicht in gefilterten Daten gefunden"}
            
            if other_bahnen.empty:
                # Nur Target zurückgeben
                result = target_row.copy()
                result['similarity_score'] = 0.0
                return {
                    "target": result.iloc[0].to_dict(),
                    "similar_bahnen": [],
                    "auto_threshold": adaptive_threshold,
                    "total_found": 0
                }
            
            # 6. KOMPLEXE Ähnlichkeitsberechnung (wie Python-App)
            similarities = await self.calculate_weighted_similarity_optimized(
                target_row, other_bahnen, weights
            )
            
            # 7. Ergebnisse formatieren
            target_data = target_row.iloc[0].to_dict()
            target_data['similarity_score'] = 0.0
            
            # Top ähnliche Bahnen
            top_similar = similarities.head(limit)
            similar_bahnen = []
            
            for _, row in top_similar.iterrows():
                bahn_data = {
                    "bahn_id": row['bahn_id_normalized'],
                    "meta_value": row['meta_value'],
                    "similarity_score": row['similarity_score'],
                    "sidtw_average_distance": row['sidtw_average_distance'] if pd.notna(row['sidtw_average_distance']) else None,
                    "duration": row['duration'],
                    "weight": row['weight'],
                    "length": row['length'],
                    "movement_type": row['movement_type'],
                    "direction_x": row['direction_x'],
                    "direction_y": row['direction_y'],
                    "direction_z": row['direction_z']
                }
                similar_bahnen.append(bahn_data)
            
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

    async def calculate_adaptive_threshold_segment(self, target_meta_value: float, strategy: str = "percentile") -> float:
        """
        Berechnet automatisch optimalen Schwellwert für Segmente basierend auf Meta-Value-Verteilung
        """
        try:
            query = """
            SELECT CAST(meta_value AS FLOAT) as meta_value 
            FROM robotervermessung.bewegungsdaten.bahn_meta bm
            WHERE CAST(bm.bahn_id AS TEXT) != CAST(bm.segment_id AS TEXT)
            AND meta_value IS NOT NULL
            ORDER BY meta_value
            """
            
            results = await self.connection.fetch(query)
            if len(results) < 10:
                return 20.0
            
            meta_values = np.array([row['meta_value'] for row in results])
            
            if strategy == "percentile":
                return self._calculate_percentile_threshold(target_meta_value, meta_values)
            else:
                return 20.0
                
        except Exception as e:
            print(f"Fehler bei adaptive Schwellwert-Berechnung für Segmente: {e}")
            return 20.0

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
        
        result = await self.connection.fetchrow(query, self.normalize_id(segment_id))
        return result['meta_value'] if result and result['meta_value'] is not None else None

    async def find_similar_segmente_complex(self, target_segment_id: str, limit: int = 10, 
                                        weights: Dict[str, float] = None) -> Dict[str, Any]:
        """
        KOMPLEXE Segment-Ähnlichkeitssuche mit vollständiger Feature-Berechnung
        """
        try:
            if weights is None:
                weights = self.default_weights.copy()
                
            target_segment_id_normalized = self.normalize_id(target_segment_id)
            
            # 1. Target Meta-Value für Threshold-Berechnung laden
            target_meta_value = await self.get_target_segment_meta_value(target_segment_id_normalized)
            if target_meta_value is None:
                return {"error": f"Target-Segment {target_segment_id} hat keinen Meta-Value"}
            
            # 2. Adaptive Schwellwert-Berechnung
            adaptive_threshold = await self.calculate_adaptive_threshold_segment(target_meta_value)
            
            # 3. Meta-Value Bereich für Vorfilterung
            threshold_factor = adaptive_threshold / 100.0
            meta_value_min = target_meta_value * (1 - threshold_factor)
            meta_value_max = target_meta_value * (1 + threshold_factor)
            
            # 4. Alle Segmente im Meta-Value-Bereich laden (mit allen Features)
            where_condition = """
            WHERE CAST(bm.bahn_id AS TEXT) != CAST(bm.segment_id AS TEXT)
            AND bm.meta_value BETWEEN $1 AND $2
            ORDER BY bm.meta_value
            """
            
            df_all = await self.load_data_with_features(
                where_condition, 
                (meta_value_min, meta_value_max)
            )
            
            if df_all.empty:
                return {"error": f"Keine Segmente im Meta-Value-Bereich gefunden"}
            
            # 5. Target und andere Segmente trennen
            target_mask = df_all['segment_id_normalized'] == target_segment_id_normalized
            target_row = df_all[target_mask]
            other_segmente = df_all[~target_mask].copy()
            
            if target_row.empty:
                return {"error": f"Target-Segment nicht in gefilterten Daten gefunden"}
            
            if other_segmente.empty:
                # Nur Target zurückgeben
                result = target_row.copy()
                result['similarity_score'] = 0.0
                return {
                    "target": result.iloc[0].to_dict(),
                    "similar_segmente": [],
                    "auto_threshold": adaptive_threshold,
                    "total_found": 0
                }
            
            # 6. KOMPLEXE Ähnlichkeitsberechnung (wie Python-App)
            similarities = await self.calculate_weighted_similarity_optimized(
                target_row, other_segmente, weights
            )
            
            # 7. Ergebnisse formatieren
            target_data = target_row.iloc[0].to_dict()
            target_data['similarity_score'] = 0.0
            
            # Top ähnliche Segmente
            top_similar = similarities.head(limit)
            similar_segmente = []
            
            for _, row in top_similar.iterrows():
                segment_data = {
                    "segment_id": row['segment_id_normalized'],
                    "bahn_id": row['bahn_id_normalized'],
                    "meta_value": row['meta_value'],
                    "similarity_score": row['similarity_score'],
                    "sidtw_average_distance": row['sidtw_average_distance'] if pd.notna(row['sidtw_average_distance']) else None,
                    "duration": row['duration'],
                    "weight": row['weight'],
                    "length": row['length'],
                    "movement_type": row['movement_type'],
                    "direction_x": row['direction_x'],
                    "direction_y": row['direction_y'],
                    "direction_z": row['direction_z'],
                    "min_position_x_soll": row['min_position_x_soll'],
                    "min_position_y_soll": row['min_position_y_soll'],
                    "min_position_z_soll": row['min_position_z_soll'],
                    "max_position_x_soll": row['max_position_x_soll'],
                    "max_position_y_soll": row['max_position_y_soll'],
                    "max_position_z_soll": row['max_position_z_soll']
                }
                similar_segmente.append(segment_data)
            
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
            bahn_id_normalized = self.normalize_id(bahn_id)
            
            query = """
            SELECT CAST(segment_id AS TEXT) as segment_id
            FROM robotervermessung.bewegungsdaten.bahn_meta bm
            WHERE CAST(bahn_id AS TEXT) = $1
            AND CAST(bahn_id AS TEXT) != CAST(segment_id AS TEXT)
            AND meta_value IS NOT NULL
            ORDER BY segment_id
            """
            
            results = await self.connection.fetch(query, bahn_id_normalized)
            return [row['segment_id'] for row in results]
            
        except Exception as e:
            print(f"Fehler beim Laden der Bahn-Segmente: {e}")
            return []


################ HIERARCHISCHE SUCHE #####################

    async def find_similar_unified_complex(self, target_id: str, bahn_limit: int = 10, 
                                        segment_limit: int = 5, weights: Dict[str, float] = None) -> Dict[str, Any]:
        """
        KOMPLEXE hierarchische Ähnlichkeitssuche: Erst Bahnen, dann alle Segmente der Target-Bahn
        Nutzt die vollständige Feature-Berechnung aus der Python-App
        
        Args:
            target_id: Eingabe-ID (kann Bahn oder Segment sein)
            bahn_limit: Anzahl ähnlicher Bahnen
            segment_limit: Anzahl ähnlicher Segmente pro Target-Segment
            weights: Gewichtungen für verschiedene Parameter
        
        Returns:
            Dict mit komplexen bahn_similarity und segment_similarity Ergebnissen
        """
        try:
            if weights is None:
                weights = self.default_weights.copy()
                
            # 1. ID-Typ erkennen und Target-Bahn bestimmen
            id_type = self.detect_id_type(target_id)
            
            if id_type == 'bahn':
                target_bahn_id = target_id
            else:
                # Segment-ID: Extrahiere Bahn-ID (Teil vor dem ersten Unterstrich)
                target_bahn_id = target_id.split('_')[0]
            
            print(f"🔍 Komplexe hierarchische Suche für {target_id} (Typ: {id_type})")
            print(f"   Target-Bahn: {target_bahn_id}")
            print(f"   Gewichtungen: {weights}")
            
            # 2. Phase 1: KOMPLEXE Bahn-Ähnlichkeitssuche
            print(f"Phase 1: Komplexe Bahn-Ähnlichkeitssuche für {target_bahn_id}")
            bahn_results = await self.find_similar_bahnen_complex(target_bahn_id, bahn_limit, weights)
            
            if "error" in bahn_results:
                return {"error": f"Bahn-Suche fehlgeschlagen: {bahn_results['error']}"}
            
            # 3. Phase 2: Segment-Ähnlichkeitssuche für alle Segmente der Target-Bahn
            print(f"Phase 2: Lade Segmente für Bahn {target_bahn_id}")
            target_segments = await self.get_bahn_segments(target_bahn_id)
            
            if not target_segments:
                return {
                    "target_bahn_id": target_bahn_id,
                    "original_input": target_id,
                    "input_type": id_type,
                    "bahn_similarity": bahn_results,
                    "segment_similarity": [],
                    "summary": {
                        "total_similar_bahnen": len(bahn_results.get("similar_bahnen", [])),
                        "total_target_segments": 0,
                        "segments_processed": 0,
                        "bahn_threshold": bahn_results.get("auto_threshold"),
                        "avg_segment_threshold": None,
                        "weights_used": weights
                    },
                    "info": f"Keine Segmente gefunden für Bahn {target_bahn_id}"
                }
            
            print(f"Gefunden: {len(target_segments)} Segmente")
            
            # 4. Für jedes Target-Segment: KOMPLEXE Ähnliche Segmente finden
            segment_results = []
            segment_thresholds = []
            
            for i, segment_id in enumerate(target_segments):
                print(f"Phase 2.{i+1}: Komplexe Segment-Ähnlichkeitssuche für {segment_id}")
                
                segment_similarity = await self.find_similar_segmente_complex(
                    segment_id, segment_limit, weights
                )
                
                if "error" not in segment_similarity:
                    segment_results.append({
                        "target_segment": segment_id,
                        "similarity_data": segment_similarity
                    })
                    
                    # Sammle Threshold für Durchschnittsberechnung
                    threshold = segment_similarity.get("auto_threshold")
                    if threshold is not None:
                        segment_thresholds.append(threshold)
                else:
                    print(f"Fehler bei Segment {segment_id}: {segment_similarity['error']}")
            
            # 5. Erweiterte Statistiken berechnen
            avg_segment_threshold = (
                sum(segment_thresholds) / len(segment_thresholds) 
                if segment_thresholds else None
            )
            
            # 6. Detaillierte finale Zusammenfassung
            return {
                "target_bahn_id": target_bahn_id,
                "original_input": target_id,
                "input_type": id_type,
                "bahn_similarity": bahn_results,
                "segment_similarity": segment_results,
                "summary": {
                    "total_similar_bahnen": len(bahn_results.get("similar_bahnen", [])),
                    "total_target_segments": len(target_segments),
                    "segments_processed": len(segment_results),
                    "bahn_threshold": bahn_results.get("auto_threshold"),
                    "avg_segment_threshold": avg_segment_threshold,
                    "weights_used": weights,
                    "meta_value_ranges": {
                        "bahn": bahn_results.get("meta_value_range"),
                        "segments": [
                            result["similarity_data"].get("meta_value_range") 
                            for result in segment_results
                            if "meta_value_range" in result["similarity_data"]
                        ]
                    }
                },
                "performance_info": {
                    "features_used": list(weights.keys()),
                    "calculation_method": "complex_weighted_similarity",
                    "normalization": "standardscaler_equivalent",
                    "movement_type_handling": "movement_type" in weights
                }
            }
            
        except Exception as e:
            return {"error": f"Fehler bei komplexer hierarchischer Ähnlichkeitssuche: {str(e)}"}

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