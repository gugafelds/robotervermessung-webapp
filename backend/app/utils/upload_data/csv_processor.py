import csv
import re
from datetime import datetime

from fastapi import logger
from .db_config import MAPPINGS

class CSVProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.mappings = MAPPINGS

    def process_csv(self, robot_model, path_planning, source_data_act,
                    source_data_cmd, record_filename, segmentation_method="fixed_segments",
                    num_segments=3, reference_position=None):
        """Verarbeitet die CSV-Datei und bereitet Daten für den Datenbankupload vor."""

        print(f'Verarbeite CSV-Datei: {record_filename}')
        try:
            matrix_info = None
            traj_comments = self._parse_trajectory_comments()

            with open(self.file_path, 'r') as matrixfile:
                for line in matrixfile:
                    if line.strip().startswith('# transformation_matrix:'):
                        matrix_info = line.strip().split(':', 1)[1].strip()
                        break

            with open(self.file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)

            self.record_filename = record_filename

            act_spalten = ['timestamp', 'pv_x', 'pv_y', 'pv_z', 'ov_x', 'ov_y', 'ov_z', 'ov_w',
                           'pt_x', 'pt_y', 'pt_z', 'ot_x', 'ot_y', 'ot_z', 'ot_w', 'tcp_speedv',
                           'tcp_angularv', 'tcp_accelv', 'tcp_accel_pi',
                           'tcp_angular_vel_pi', 'segment_id_ist']

            cmd_spalten = ['ps_x', 'ps_y', 'ps_z', 'os_x', 'os_y', 'os_z', 'os_w', 'tcp_speedbs', 'tcp_accelbs',
                            'joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6',
                            'ap_x', 'ap_y', 'ap_z', 'aq_x', 'aq_y', 'aq_z', 'aq_w', 'DO_Signal',
                            'Movement Type', 'Weight', 'Velocity Picking', 'Velocity Handling',
                            'segment_id_soll']

            # Filtere Zeilen für IST-Daten anhand der IST-Spalten
            rows_act = []
            for row in rows:
                # Prüfe, ob die Zeile gültige IST-Daten enthält
                if row.get('segment_id_ist') is not None and row.get('segment_id_ist') != '' and row.get(
                        'segment_id_ist') != 'NaN':
                    # Prüfe, ob die erforderlichen IST-Spalten Werte enthalten
                    if any(row.get(spalte) not in [None, '', 'NaN'] for spalte in act_spalten if spalte in row):
                        rows_act.append(row)

            # Filtere Zeilen für SOLL-Daten anhand der SOLL-Spalten
            rows_cmd = []
            for row in rows:
                # Prüfe, ob die Zeile gültige SOLL-Daten enthält
                if row.get('segment_id_soll') is not None and row.get('segment_id_soll') != '' and row.get(
                        'segment_id_soll') != 'NaN':
                    # Prüfe, ob die erforderlichen SOLL-Spalten Werte enthalten
                    if any(row.get(spalte) not in [None, '', 'NaN'] for spalte in cmd_spalten if
                           spalte in row):
                        rows_cmd.append(row)

            # Wenn reference_position definiert ist, führe die positionsbasierte Segmentierung durch
            if segmentation_method == "reference_position":
                ref_x = float(reference_position[0])
                ref_y = float(reference_position[1])
                ref_z = float(reference_position[2])
                threshold = 0.3

                # print(f"Suche nach AP-Positionen nahe der Referenzposition: x={ref_x}, y={ref_y}, z={ref_z} mit Schwellenwert {threshold}mm")

                # Finde alle Zeilen mit AP-Positionen nahe der Referenzposition
                matching_rows = []

                for row in rows_cmd:
                    # Überprüfe, ob die AP-Werte vorhanden und gültig sind
                    ap_x = row.get('ap_x', '')
                    ap_y = row.get('ap_y', '')
                    ap_z = row.get('ap_z', '')

                    if ap_x and ap_y and ap_z and ap_x != 'NaN' and ap_y != 'NaN' and ap_z != 'NaN':
                        try:
                            ap_x = float(ap_x)
                            ap_y = float(ap_y)
                            ap_z = float(ap_z)

                            # Berechne den Abstand zur Referenzposition
                            distance = self.calculate_distance(ap_x, ap_y, ap_z, ref_x, ref_y, ref_z)

                            # Wenn der Abstand unter dem Schwellenwert liegt, speichere diese Zeile
                            if distance <= threshold:
                                matching_rows.append({
                                    'segment_id': row.get('segment_id_soll'),
                                    'timestamp': row.get('timestamp'),
                                    'distance': distance,
                                    'ap_x': ap_x,
                                    'ap_y': ap_y,
                                    'ap_z': ap_z
                                })
                        except ValueError:
                            # Ignoriere Zeilen mit ungültigen AP-Werten
                            continue

                # Gruppiere die Treffer nach Segment-ID
                segments_with_matches = {}
                for match in matching_rows:
                    segment_id = match['segment_id']
                    if segment_id not in segments_with_matches:
                        segments_with_matches[segment_id] = []
                    segments_with_matches[segment_id].append(match)

                print(f"Gefunden: {len(matching_rows)} Zeilen mit AP-Positionen nahe der Referenzposition")
                print(f"Verteilt auf {len(segments_with_matches)} Segmente:")

                robot_starts_at_ref = False
                start_segment = None

                for i, row in enumerate(rows_cmd[:200]):
                    ps_x = row.get('ps_x', '')
                    ps_y = row.get('ps_y', '')
                    ps_z = row.get('ps_z', '')
                    segment_id = row.get('segment_id_soll', '')  # Hole segment_id hier
                    
                    if ps_x and ps_y and ps_z and ps_x != 'NaN' and ps_y != 'NaN' and ps_z != 'NaN':
                        try:
                            ps_x = float(ps_x)
                            ps_y = float(ps_y)
                            ps_z = float(ps_z)
                            
                            distance = self.calculate_distance(ps_x, ps_y, ps_z, ref_x, ref_y, ref_z)
                            
                            if distance <= threshold and segment_id and segment_id != 'NaN':  # Prüfe auch segment_id
                                robot_starts_at_ref = True
                                start_segment = segment_id  # Verwende die bereits geholte segment_id
                                print(f"Roboter startet an Referenzposition in Segment {start_segment}")
                                break
                        except ValueError:
                            continue

                #for segment_id, matches in segments_with_matches.items():
                #    print(f"  Segment {segment_id}: {len(matches)} Referenzpunkte gefunden")
                #    # Zeige den ersten und letzten gefundenen Punkt für dieses Segment
                #    if matches:
                #        first = matches[0]
                #        last = matches[-1]
                #        print(f"    Erster Punkt: AP=({first['ap_x']:.3f}, {first['ap_y']:.3f}, {first['ap_z']:.3f}), Abstand={first['distance']:.3f}mm")
                #        print(f"    Letzter Punkt: AP=({last['ap_x']:.3f}, {last['ap_y']:.3f}, {last['ap_z']:.3f}), Abstand={last['distance']:.3f}mm")

                # Sammle alle eindeutigen Segment-IDs (alle, nicht nur die mit Matches)
                all_segment_ids = []
                for row in rows_cmd:
                    segment_id = row.get('segment_id_soll')
                    if segment_id and segment_id not in all_segment_ids:
                        all_segment_ids.append(segment_id)

                # Sortiere alle Segment-IDs numerisch
                all_segment_ids.sort(key=lambda x: int(x) if x.isdigit() else float('inf'))

                # Entferne das erste und letzte Segment, wie bei der ursprünglichen Methode
                if len(all_segment_ids) >= 2:
                    all_segment_ids = all_segment_ids[1:-1]

                # Sortiere die Segmente mit Matches (Referenzpunkte)
                ref_segment_ids = sorted([s for s in segments_with_matches.keys() if s in all_segment_ids],
                                         key=lambda x: int(x) if x.isdigit() else float('inf'))

                # Definiere Bahnen als Bereiche zwischen Referenzpunkten
                if robot_starts_at_ref and start_segment == '0':
                    # Segment 0 wurde entfernt, also beginnt die erste Bahn bei Segment 1
                    # Aber wir wollen Segment 1 auch überspringen (Bewegung zum nächsten Punkt)
                    # Also beginnen wir bei Segment 2
                    
                    bahnen = []
                    
                    # Erste Bahn: Von Segment 2 bis zum ersten AP-Referenzpunkt
                    if '1' in all_segment_ids and ref_segment_ids:
                        start_idx = all_segment_ids.index('1')  # Beginne bei Segment 2
                        first_ap_ref = ref_segment_ids[0]  # Das ist '5'
                        if first_ap_ref in all_segment_ids:
                            end_idx = all_segment_ids.index(first_ap_ref)
                            if start_idx < end_idx:
                                bahnen.append(all_segment_ids[start_idx:end_idx])
                                print(f"Erste Bahn (Start an Ref): Segmente {all_segment_ids[start_idx]} bis {all_segment_ids[end_idx-1]}")
                else:
                    bahnen = []

                if robot_starts_at_ref and start_segment and start_segment in all_segment_ids:
                    # Spezialbehandlung für Start an Referenzposition
                    start_idx = all_segment_ids.index(start_segment) + 2  # +2 um Start und Bewegung zu überspringen
                    
                    # Finde das Ende dieser ersten Bahn
                    if ref_segment_ids:  # ref_segment_ids enthält NUR AP-Referenzpunkte
                        first_ap_ref = ref_segment_ids[0]
                        if first_ap_ref in all_segment_ids:
                            end_idx = all_segment_ids.index(first_ap_ref)
                            if start_idx < end_idx:
                                bahnen.append(all_segment_ids[start_idx:end_idx])
                                print(f"Erste Bahn (Start an Ref): Segmente {all_segment_ids[start_idx]} bis {all_segment_ids[end_idx-1]}")

                # Für jedes Referenzsegment (außer dem letzten) finden wir alle Segmente bis zum nächsten Referenzsegment
                for i in range(len(ref_segment_ids)):
                    home_segment_idx = all_segment_ids.index(ref_segment_ids[i])
                    start_idx = home_segment_idx + 2  # Starte nach dem Home-Segment (2 Segmente weiter)

                    # Für das letzte Referenzsegment nehmen wir alle verbleibenden Segmente
                    if i == len(ref_segment_ids) - 1:
                        end_idx = len(all_segment_ids)
                    else:
                        # Für alle anderen nehmen wir bis zum nächsten Home-Segment (exklusiv)
                        # aber schließen das Segment VOR dem nächsten Home-Punkt mit ein
                        next_home_idx = all_segment_ids.index(ref_segment_ids[i + 1])
                        end_idx = next_home_idx  # Stoppe VOR dem nächsten Home-Segment

                    # Sammle alle Segmente für diese Bahn (nur wenn start_idx < end_idx)
                    if start_idx < end_idx:
                        traj_segs = all_segment_ids[start_idx:end_idx]
                        bahnen.append(traj_segs)

                # Filtere Bahnen, die zu wenige Segmente haben (≤ 2)
                min_segments_per_bahn = 1
                valid_bahnen = []
                removed_bahnen = []

                for i, traj_segs in enumerate(bahnen):
                    if len(traj_segs) > min_segments_per_bahn:
                        valid_bahnen.append(traj_segs)
                    else:
                        removed_bahnen.append((i, traj_segs))

                # print(f"\nDefiniere {len(bahnen)} Bahnen basierend auf Referenzpunkten:")
                # for i, traj_segs in enumerate(bahnen):
                #     start_segment = traj_segs[0]
                #     end_segment = traj_segs[-1]
                #
                #     print(f"  Bahn {i}: Segment {start_segment} bis {end_segment} ({len(traj_segs)} Segmente)")
                #     if start_segment in segments_with_matches:
                #         ref_matches = segments_with_matches[start_segment]
                #         ref_count = len(ref_matches)
                #         avg_distance = sum(match['distance'] for match in ref_matches) / ref_count if ref_count > 0 else 0
                #         print(f"    Beginnt mit Referenzpunkt: {ref_count} Punkte, Ø Abstand: {avg_distance:.3f}mm")
                #     print(f"    Enthaltene Segmente: {', '.join(traj_segs)}")

                # print(f"\nNach Filterung: {len(valid_bahnen)} gültige Bahnen (mehr als {min_segments_per_bahn} Segmente):")

                # Entfernte Bahnen ausgeben
                # if removed_bahnen:
                #     print(f"Entfernte Bahnen (≤ {min_segments_per_bahn} Segmente):")
                #     for traj_idx, segments in removed_bahnen:
                #         print(f"  Bahn {traj_idx}: {', '.join(segments)}")

                # Neue Bahn-Indizes zuweisen
                new_trajs = {}
                for new_idx, traj_segs in enumerate(valid_bahnen):
                    original_idx = bahnen.index(traj_segs)
                    new_trajs[new_idx] = {"segments": traj_segs, "original_idx": original_idx}

                    # start_segment = traj_segs[0]
                    # end_segment = traj_segs[-1]
                    #
                    # print(f"  Bahn {new_idx} (ursprünglich Bahn {original_idx}): Segment {start_segment} bis {end_segment} ({len(traj_segs)} Segmente)")
                    # print(f"    Enthaltene Segmente: {', '.join(traj_segs)}")

                # Segment zu Bahn Mapping mit neuen Indizes
                segment_to_bahn = {}

                # Initialisiere alle Segmente mit "?"
                for segment_id in all_segment_ids:
                    segment_to_bahn[segment_id] = "?"

                # Weise Bahn-IDs zu
                for new_traj_idx, traj_info in new_trajs.items():
                    for segment_id in traj_info["segments"]:
                        segment_to_bahn[segment_id] = str(new_traj_idx)

                #print("\nSegment zu Bahn Mapping (nach Filterung):")
                #for segment_id in all_segment_ids:
                #    traj_id = segment_to_bahn.get(segment_id, "?")
                #    print(f"  Segment {segment_id} → Bahn {traj_id}")

                # print("\nZusammenfassung der finalen Bahnen:")
                # for traj_idx, traj_info in new_trajs.items():
                #     segments = traj_info["segments"]
                #     print(f"  Bahn {traj_idx}: {len(segments)} Segmente - {', '.join(segments)}")

                # Sammle alle Segmente aus den validen Bahnen
                valid_segments = []
                for traj_info in new_trajs.values():
                    valid_segments.extend(traj_info["segments"])

                #print(f"\nVerwende {len(valid_segments)} Segmente für die weitere Verarbeitung:")
                #print(f"  {', '.join(valid_segments)}")

                # Filtere Zeilen für IST-Daten basierend auf den gültigen Segmenten
                rows_act_filtered = []
                for row in rows_act:
                    segment_id = row.get('segment_id_ist')
                    if segment_id in valid_segments:
                        rows_act_filtered.append(row)

                # Filtere Zeilen für SOLL-Daten basierend auf den gültigen Segmenten
                rows_cmd_filtered = []
                for row in rows_cmd:
                    segment_id = row.get('segment_id_soll')
                    if segment_id in valid_segments:
                        rows_cmd_filtered.append(row)

                # print(f"IST: Originale Anzahl Zeilen: {len(rows_act)}, Nach Segment-Filterung: {len(rows_act_filtered)}")
                # print(f"SOLL: Originale Anzahl Zeilen: {len(rows_cmd)}, Nach Segment-Filterung: {len(rows_cmd_filtered)}")

                # Bereite ein Mapping von Segment zu Bahn vor, das an process_data übergeben wird
                reference_segment_to_bahn = {}
                for segment_id in all_segment_ids:
                    traj_id = segment_to_bahn.get(segment_id, None)
                    if traj_id != "?" and traj_id is not None:
                        reference_segment_to_bahn[segment_id] = traj_id

                if robot_starts_at_ref:
                    print(f"DEBUG: Start-Segment: {start_segment}")
                    print(f"DEBUG: all_segment_ids: {all_segment_ids}")
                    print(f"DEBUG: ref_segment_ids VOR Änderung: {ref_segment_ids}")

                    print(f"DEBUG: ref_segment_ids NACH Änderung: {ref_segment_ids}")
                    print(f"DEBUG: Erste Bahn sollte beginnen bei Index: {all_segment_ids.index(start_segment) + 2 if start_segment in all_segment_ids else 'NICHT GEFUNDEN'}")

                # Verarbeite die Daten mit der reference_position Methode
                act_rows_processed, act_processed_data, act_point_counts, act_max_bahn, act_traj_ids = self.process_data(
                    rows_act_filtered, source_data_act, "ist", "reference_position",
                    segment_to_traj_mapping=reference_segment_to_bahn
                )

                cmd_rows_processed, cmd_processed_data, cmd_point_counts, cmd_max_bahn, cmd_traj_ids = self.process_data(
                    rows_cmd_filtered, source_data_cmd, "soll", "reference_position",
                    segment_to_traj_mapping=reference_segment_to_bahn
                )

            else:  # Bei allen anderen Methoden (z.B. fixed_segments) den ursprünglichen Code verwenden
                # Sammle alle eindeutigen IST-Segmente
                act_segments = []
                for row in rows_act:
                    segment_id = row.get('segment_id_ist')
                    if segment_id not in act_segments:
                        act_segments.append(segment_id)

                # Sammle alle eindeutigen SOLL-Segmente
                cmd_segments = []
                for row in rows_cmd:
                    segment_id = row.get('segment_id_soll')
                    if segment_id not in cmd_segments:
                        cmd_segments.append(segment_id)

                # Bestimme, welche IST-Segmente zu entfernen sind
                act_segments_to_remove = []
                if len(act_segments) >= 3:
                    act_segments_to_remove = [act_segments[0], act_segments[-1]]
                    # print(f"IST: Entferne erstes Segment {act_segments_to_remove[0]} und letztes Segment {act_segments_to_remove[-1]}")
                else:
                    print(f"Warnung: Nur {len(act_segments)} IST-Segmente gefunden, entferne keine")

                # Bestimme, welche SOLL-Segmente zu entfernen sind
                cmd_segments_to_remove = []
                if len(cmd_segments) >= 3:
                    cmd_segments_to_remove = [cmd_segments[0], cmd_segments[-1]]
                    # print(f"SOLL: Entferne erstes Segment {cmd_segments_to_remove[0]} und letztes Segment {cmd_segments_to_remove[-1]}")
                else:
                    print(f"Warnung: Nur {len(cmd_segments)} SOLL-Segmente gefunden, entferne keine")

                # Filtere IST-Zeilen
                rows_act_filtered = []
                for row in rows_act:
                    segment_id = row.get('segment_id_ist')
                    if segment_id not in act_segments_to_remove:
                        rows_act_filtered.append(row)

                # Filtere SOLL-Zeilen
                rows_cmd_filtered = []
                for row in rows_cmd:
                    segment_id = row.get('segment_id_soll')
                    if segment_id not in cmd_segments_to_remove:
                        rows_cmd_filtered.append(row)

                # print(f"IST: Originale Anzahl Zeilen: {len(rows_act)}, Nach Filterung: {len(rows_act_filtered)}")
                # print(f"SOLL: Originale Anzahl Zeilen: {len(rows_cmd)}, Nach Filterung: {len(rows_cmd_filtered)}")

                # Verwende:
                act_rows_processed, act_processed_data, act_point_counts, act_max_bahn, act_traj_ids = self.process_data(
                    rows_act_filtered, source_data_act, "ist", segmentation_method, num_segments
                )

                cmd_rows_processed, cmd_processed_data, cmd_point_counts, cmd_max_bahn, cmd_traj_ids = self.process_data(
                    rows_cmd_filtered, source_data_cmd, "soll", segmentation_method, num_segments
                )

            # Bestimme die maximale Anzahl von Bahnen
            max_bahnen = max(act_max_bahn, cmd_max_bahn)

            print("\nSynchronisiere IST- und SOLL-Bahn-IDs...")

            for traj_idx in range(max_bahnen + 1):
                traj_key = str(traj_idx)

                # Hole IST- und SOLL-Bahn-IDs für diese Bahn
                act_traj_id = act_traj_ids.get(traj_key, None)
                cmd_traj_id = cmd_traj_ids.get(traj_key, None)

                # Prüfe, ob beide Bahn-IDs existieren
                if act_traj_id is not None and cmd_traj_id is not None:
                    # Prüfe, ob sie unterschiedlich sind
                    if act_traj_id != cmd_traj_id:
                        print(
                            f"  Bahn {traj_idx}: IST-ID '{act_traj_id}' ≠ SOLL-ID '{cmd_traj_id}' -> Verwende IST-ID")

                        # Ersetze alle SOLL-Bahn-IDs mit der IST-Bahn-ID
                        for mapping_name in cmd_processed_data.keys():
                            if traj_key in cmd_processed_data[mapping_name]:
                                for i in range(len(cmd_processed_data[mapping_name][traj_key])):
                                    row_data = cmd_processed_data[mapping_name][traj_key][i]
                                    if row_data and len(row_data) > 1:
                                        # Ersetze Bahn-ID an Position 0 und segment_id an Position 1
                                        old_segment_parts = row_data[1].split('_', 1)  # Format: [traj_id]_[segment_nr]
                                        if len(old_segment_parts) == 2:
                                            new_segment_id = f"{act_traj_id}_{old_segment_parts[1]}"
                                        else:
                                            new_segment_id = f"{act_traj_id}_{old_segment_parts[0]}"

                                        cmd_processed_data[mapping_name][traj_key][i] = [
                                            act_traj_id,  # Neue Bahn-ID an Position 0
                                            new_segment_id,  # Neue segment_id an Position 1
                                            *row_data[2:]  # Rest der Daten unverändert
                                        ]

                        # Aktualisiere auch das cmd_traj_ids Dictionary
                        cmd_traj_ids[traj_key] = act_traj_id

                    else:
                        print(f"  Bahn {traj_idx}: IST-ID '{act_traj_id}' = SOLL-ID '{cmd_traj_id}' -> OK")
                elif act_traj_id is not None:
                    print(f"  Bahn {traj_idx}: Nur IST-ID '{act_traj_id}' vorhanden")
                elif cmd_traj_id is not None:
                    print(f"  Bahn {traj_idx}: Nur SOLL-ID '{cmd_traj_id}' vorhanden")

            print("Bahn-ID Synchronisation abgeschlossen.")

            print(f"Gefunden: {act_max_bahn + 1} IST-Bahnen, {cmd_max_bahn + 1} SOLL-Bahnen")

            # Kombiniere IST- und SOLL-Daten zu einer Liste von Bahnen pro Bahn-ID
            all_processed_data = []

            for traj_idx in range(max_bahnen + 1):
                # Nehme die entsprechenden Daten für diese Bahn
                traj_data = {
                    key: [] for key in self.mappings.keys()
                }

                # Sammle IST-Daten für diese Bahn
                for mapping_name in act_processed_data.keys():
                    traj_key = f"{traj_idx}"
                    if traj_key in act_processed_data[mapping_name]:
                        traj_data[mapping_name] = act_processed_data[mapping_name][traj_key]

                for mapping_name in cmd_processed_data.keys():
                    traj_key = f"{traj_idx}"
                    if traj_key in cmd_processed_data[mapping_name]:
                        traj_data[mapping_name] = cmd_processed_data[mapping_name][traj_key]

                has_data = any(len(traj_data[key]) > 0 for key in traj_data.keys())
                if not has_data:
                    continue

                all_timestamps = []
                for key, data in traj_data.items():
                    for row in data:
                        if len(row) > 2:  # Prüfe, ob Zeitstempel vorhanden
                            all_timestamps.append(row[2])  # Zeitstempel ist an Position 2

                if all_timestamps:
                    all_timestamps.sort()
                    start_time = str(self.convert_timestamp(all_timestamps[0]))
                    end_time = str(self.convert_timestamp(all_timestamps[-1]))
                    recording_date = start_time
                else:
                    start_time = str(self.convert_timestamp(rows[0]['timestamp']))
                    end_time = str(self.convert_timestamp(rows[-1]['timestamp']))
                    recording_date = start_time

                traj_id = None
                for key, data in traj_data.items():
                    if data and len(data) > 0 and len(data[0]) > 0:
                        traj_id = data[0][0]  # Nehme die erste Komponente der ersten Zeile
                        break

                traj_point_counts = {'number_setpoints': len(traj_data.get('RAPID_SETPOINTS_MAPPING', [])),
                                     'number_pose_act': len(traj_data.get('POSE_MAPPING', [])),
                                     'number_vel_act': len(traj_data.get('VEL_ACT_MAPPING', [])),
                                     'number_accel_act': len(traj_data.get('ACCEL_ACT_MAPPING', [])),
                                     'number_accel_cmd': len(traj_data.get('ACCEL_CMD_MAPPING', [])),
                                     'number_position_cmd': len(traj_data.get('POSITION_CMD_MAPPING', [])),
                                     'number_orientation_cmd': len(traj_data.get('ORIENTATION_CMD_MAPPING', [])),
                                     'number_vel_cmd': len(traj_data.get('VEL_CMD_MAPPING', [])),
                                     'number_joint_states': len(traj_data.get('JOINT_MAPPING', []))}

                traj_frequencies = {
                    'freq_pose': self.calculate_freq_from_data(traj_data.get('POSE_MAPPING', [])),
                    'freq_position_cmd': self.calculate_freq_from_data(
                        traj_data.get('POSITION_CMD_MAPPING', [])),
                    'freq_orientation_cmd': self.calculate_freq_from_data(
                        traj_data.get('ORIENTATION_CMD_MAPPING', [])),
                    'freq_vel_act': self.calculate_freq_from_data(traj_data.get('VEL_ACT_MAPPING', [])),
                    'freq_vel_cmd': self.calculate_freq_from_data(traj_data.get('VEL_CMD_MAPPING', [])),
                    'freq_accel_act': self.calculate_freq_from_data(traj_data.get('ACCEL_ACT_MAPPING', [])),
                    'freq_accel_cmd': self.calculate_freq_from_data(traj_data.get('ACCEL_CMD_MAPPING', [])),
                    'freq_joint': self.calculate_freq_from_data(traj_data.get('JOINT_MAPPING', [])),
                }

                # Erstelle Basis-Bahn-Info
                base_info = [
                    traj_id,
                    robot_model,
                    path_planning,
                    recording_date,
                    start_time,
                    end_time,
                    source_data_act,
                    source_data_cmd,
                    self.extract_record_part(record_filename),
                    traj_point_counts['number_setpoints'],
                    traj_frequencies['freq_pose'],
                    traj_frequencies['freq_position_cmd'],
                    traj_frequencies['freq_orientation_cmd'],
                    traj_frequencies['freq_vel_act'],
                    traj_frequencies['freq_vel_cmd'],
                    traj_frequencies['freq_accel_act'],
                    traj_frequencies['freq_joint'],
                    traj_point_counts['number_pose_act'],
                    traj_point_counts['number_vel_act'],
                    traj_point_counts['number_accel_act'],
                    traj_point_counts['number_position_cmd'],
                    traj_point_counts['number_orientation_cmd'],
                    traj_point_counts['number_vel_cmd'],
                    traj_point_counts['number_joint_states'],
                    traj_comments.get('weight'),
                    matrix_info,
                    traj_point_counts['number_accel_cmd'],
                    traj_frequencies['freq_accel_cmd'],
                    traj_comments.get('velocity'),
                    traj_comments.get('stop_point'),
                    traj_comments.get('wait_time'),
                ]

                traj_info_data = tuple(base_info)

                traj_data['traj_info_data'] = traj_info_data
                traj_data['traj_comments'] = traj_comments

                waypoints = traj_comments.get('waypoints', [])
                if waypoints and traj_data.get('RAPID_SETPOINTS_MAPPING'):
                    traj_data['RAPID_SETPOINTS_MAPPING'] = self._match_waypoints_to_setpoints(
                        traj_data['RAPID_SETPOINTS_MAPPING'],
                        waypoints
                    )

                all_processed_data.append(traj_data)

            print(f"CSV-Verarbeitung abgeschlossen: {len(all_processed_data)} Bahnen gefunden")
            return all_processed_data

        except Exception as e:
            import traceback
            print(f"Fehler bei der CSV-Verarbeitung: {e}")
            print(traceback.format_exc())
            return None

    def process_data(self, rows, source_data, data_type, segmentation_method="fixed_segments", num_segments=3,
                     segment_to_traj_mapping=None):
        """
        Verarbeitet IST- oder SOLL-Daten aus den CSV-Zeilen.
        Die ersten und letzten Segmente wurden bereits entfernt.
        Bei reference_position werden die Bahnen anhand des übergebenen segment_to_traj_mapping zugeordnet.
        Bei fixed_segments enthält jede Bahn genau num_segments Segmente,
        außer die letzte, die auch mehr enthalten kann, wenn Restsegmente vorhanden sind.

        Args:
            rows: Die CSV-Zeilen
            source_data: Die Datenquelle (z.B. "ros" oder "rapid")
            data_type: "ist" oder "soll"
            segmentation_method: Die Segmentierungsmethode
            num_segments: Anzahl der Segmente pro Bahn
            segment_to_traj_mapping: Mapping von Segment-ID zu Bahn-ID (nur für reference_position)

        Returns:
            Tuple mit (rows_processed, processed_data, point_counts, max_bahn, traj_ids)
        """
        if data_type.lower() == "ist":
            segment_id_field = 'segment_id_ist'
            mappings_to_use = ['POSE_MAPPING', 'VEL_ACT_MAPPING', 'ACCEL_ACT_MAPPING', 'TRANSFORM_MAPPING']
        elif data_type.lower() == "soll":
            segment_id_field = 'segment_id_soll'
            mappings_to_use = ['POSITION_CMD_MAPPING', 'ORIENTATION_CMD_MAPPING', 'VEL_CMD_MAPPING', 'ACCEL_CMD_MAPPING',
                               'JOINT_MAPPING', 'RAPID_SETPOINTS_MAPPING']
        else:
            raise ValueError(f"Ungültiger Datentyp: {data_type}. Muss 'ist' oder 'soll' sein.")

        # Zähler für die Verarbeitung
        rows_processed = {key: 0 for key in mappings_to_use}

        # Container für verarbeitete Daten, getrennt nach Bahn
        processed_data = {key: {} for key in mappings_to_use}

        # Punktzähler initialisieren
        point_counts = {
            'number_setpoints': 0,
            'number_pose_act': 0,
            'number_vel_act': 0,
            'number_accel_act': 0,
            'number_accel_cmd': 0,
            'number_position_cmd': 0,
            'number_orientation_cmd': 0,
            'number_vel_cmd': 0,
            'number_joint_states': 0,
        }

        all_segments = []
        for row in rows:
            segment_id = row.get(segment_id_field)
            if segment_id is not None and segment_id != '' and segment_id not in all_segments:
                all_segments.append(segment_id)

        if segmentation_method == "reference_position" and segment_to_traj_mapping:
            segment_to_bahn = segment_to_traj_mapping

            traj_to_segments = {}
            for segment_id, traj_key in segment_to_bahn.items():
                if traj_key not in traj_to_segments:
                    traj_to_segments[traj_key] = []
                traj_to_segments[traj_key].append(segment_id)

            max_bahn = max([int(bahn) for bahn in traj_to_segments.keys()]) if traj_to_segments else 0

        else:
            traj_to_segments = {}

            if len(all_segments) < num_segments:
                traj_to_segments = {}
                max_bahn = -1 
                print(
                    f"Warnung: Nur {len(all_segments)} Segmente vorhanden, benötigt werden {num_segments}. Keine Bahnen erstellt.")
            else:
                # Berechne, wie viele vollständige Bahnen wir haben werden
                complete_bahnen = len(all_segments) // num_segments

                # Berechne, wie viele Restsegmente übrig bleiben
                remaining_segments = len(all_segments) % num_segments

                for i in range(complete_bahnen):
                    start_idx = i * num_segments
                    end_idx = (i + 1) * num_segments
                    traj_to_segments[str(i)] = all_segments[start_idx:end_idx]

                if remaining_segments > 0:
                    remaining_segment_list = all_segments[complete_bahnen * num_segments:]
                    print(
                        f"Info: {remaining_segments} Restsegmente werden weggelassen: {', '.join(remaining_segment_list)}")

                max_bahn = complete_bahnen - 1 if complete_bahnen > 0 else -1

            # Debug-Ausgabe
            # print(f"{data_type.upper()}-Segmente pro Bahn:")
            # for bahn, segments in sorted(traj_to_segments.items(), key=lambda x: int(x[0])):
            #     print(f"  Bahn {bahn}: {', '.join(segments)}")

            segment_to_bahn = {}
            for traj_key, segments in traj_to_segments.items():
                for segment_id in segments:
                    segment_to_bahn[segment_id] = traj_key

        segment_id_mapping = {}
        for traj_key, segments in traj_to_segments.items():
            for i, segment_id in enumerate(segments):
                segment_id_mapping[(traj_key, segment_id)] = i + 1  # Segment-IDs beginnen bei 1

        traj_timestamps = {}

        for i, row in enumerate(rows):
            timestamp = row['timestamp']
            segment_id = row.get(segment_id_field)

            if segment_id is None or segment_id == '':
                continue

            traj_key = segment_to_bahn.get(segment_id)
            if traj_key is None:
                continue  # Dieses Segment wurde keiner Bahn zugeordnet

            if traj_key not in traj_timestamps:
                traj_timestamps[traj_key] = []
            traj_timestamps[traj_key].append(timestamp)

            for mapping_name in mappings_to_use:
                if mapping_name not in self.mappings:
                    continue

                mapping = self.mappings[mapping_name]

                traj_segment_id = str(segment_id_mapping.get((traj_key, segment_id), 0))
                if traj_segment_id == '0':
                    continue  # Keine gültige Zuordnung gefunden

                if traj_key not in processed_data[mapping_name]:
                    processed_data[mapping_name][traj_key] = []

                result = self.process_mapping_row(
                    row, mapping, traj_key, traj_segment_id, timestamp,
                    source_data, point_counts, mapping_name
                )

                if result:
                    processed_data[mapping_name][traj_key].append(result)
                    rows_processed[mapping_name] += 1

        traj_ids = {}
        for traj_key, timestamps in traj_timestamps.items():
            if timestamps:
                # Verwende den frühesten Zeitstempel
                earliest_timestamp = min(timestamps)
                traj_ids[traj_key] = str(earliest_timestamp[:10])

        # Aktualisiere alle verarbeiteten Daten mit der richtigen Bahn-ID
        for mapping_name in processed_data.keys():
            for traj_key in processed_data[mapping_name]:
                if traj_key in traj_ids:
                    traj_id = traj_ids[traj_key]
                    for i in range(len(processed_data[mapping_name][traj_key])):
                        # Ersetze die Bahn-ID und aktualisiere das segment_id Format
                        if processed_data[mapping_name][traj_key][i]:
                            row_data = processed_data[mapping_name][traj_key][i]
                            processed_data[mapping_name][traj_key][i] = [
                                traj_id,  # Bahn-ID an Position 0
                                f"{traj_id}_{row_data[1]}",  # Neue segment_id im Format [traj_id]_[segmentzahl]
                                *row_data[2:]  # Rest der Daten unverändert
                            ]

        # Gib am Ende die gefundenen Bahn-IDs und die zugehörigen Segment-IDs aus
        # print(f"\n{data_type.upper()}-Bahnen und zugehörige Segmente:")
        # for traj_key, segments in sorted(traj_to_segments.items(), key=lambda x: int(x[0])):
        #     traj_id = traj_ids.get(traj_key, "Unbekannt")
        #     segment_list = []
        #     for segment in segments:
        #         mapped_id = segment_id_mapping.get((traj_key, segment), "?")
        #         segment_list.append(f"{segment} (ID: {mapped_id})")
        #     print(f"  Bahn {traj_key} (ID: {traj_id}): Segmente = {', '.join(segment_list)}")

        print(f"\n{data_type.upper()}-Bahn-ID-Zuordnungen:")
        for traj_key, traj_id in sorted(traj_ids.items(), key=lambda x: int(x[0])):
            print(f"  Bahn {traj_key} hat ID: {traj_id}")
            print(f"    Enthält Segmente: {', '.join(traj_to_segments.get(traj_key, []))}")
            # Zeige die gemappten Segment-IDs
            mapped_segments = []
            for segment in traj_to_segments.get(traj_key, []):
                mapped_id = segment_id_mapping.get((traj_key, segment), "?")
                mapped_segments.append(f"{segment} → {mapped_id}")
            print(f"    Segment-Mapping: {', '.join(mapped_segments)}")

        return rows_processed, processed_data, point_counts, max_bahn, traj_ids

    def process_mapping_row(self, row, mapping, traj_id, segment_id, timestamp,
                            point_counts, mapping_name, movement_types=None):
        """
        Verarbeitet eine Zeile gemäß einem bestimmten Mapping und gibt die Datenzeile zurück.
        """

        # Hilfsfunktion zur Wertkonvertierung
        def convert_value(value):
            if value is None:
                return None

            if isinstance(value, str):
                value = value.strip()

            if value == '0' or value == '0.0':
                return 0.0
            elif value:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None
            return None

        # Für RAPID_SETPOINTS (AP-Punkte) - spezielle Behandlung
        if mapping_name == 'RAPID_SETPOINTS_MAPPING':
            # Nur verarbeiten, wenn mindestens ein Wert vorhanden ist
            if any(row.get(csv_col, '').strip() for csv_col in mapping):
                # Erstelle Datenzeile
                data_row = [traj_id, segment_id, timestamp]
                values = []

                # Werte aus dem Mapping extrahieren
                for csv_col in mapping:
                    value = row.get(csv_col, '')
                    if any(x in csv_col for x in ['x_reached', 'y_reached', 'z_reached',
                                                  'qx_reached', 'qy_reached', 'qz_reached', 'qw_reached']):
                        values.append(convert_value(value))
                    else:
                        values.append(value.strip() if value.strip() else None)

                data_row.extend(values)

                return data_row

        # Für alle anderen Mappings
        else:
            # Nur verarbeiten, wenn alle erforderlichen Werte vorhanden sind
            if all(row.get(csv_col, '').strip() for csv_col in mapping):
                data_row = [traj_id, segment_id, timestamp]
                values = []

                # Werte aus dem Mapping extrahieren
                for csv_col in mapping:
                    value = row.get(csv_col, '')
                    values.append(convert_value(value))

                data_row.extend(values)

                # Punktzähler aktualisieren
                if mapping_name == 'POSE_MAPPING':
                    point_counts['number_pose_act'] += 1
                elif mapping_name == 'VEL_ACT_MAPPING':
                    point_counts['number_vel_act'] += 1
                elif mapping_name == 'ACCEL_ACT_MAPPING':
                    point_counts['number_accel_act'] += 1
                elif mapping_name == 'POSITION_CMD_MAPPING':
                    point_counts['number_position_cmd'] += 1
                elif mapping_name == 'ORIENTATION_CMD_MAPPING':
                    point_counts['number_orientation_cmd'] += 1
                elif mapping_name == 'VEL_CMD_MAPPING':
                    point_counts['number_vel_cmd'] += 1
                elif mapping_name == 'JOINT_MAPPING':
                    point_counts['number_joint_states'] += 1
                elif mapping_name == 'ACCEL_CMD_MAPPING':
                    point_counts['number_accel_cmd'] += 1
                elif mapping_name == 'IMU_MAPPING':
                    point_counts['number_imu'] += 1

                return data_row

        return None

    def calculate_freq_from_data(self, data_rows):
        """Berechnet die Frequenz basierend auf Zeitstempeln in den Datenzeilen."""
        if not data_rows or len(data_rows) < 2:
            return 0.0

        timestamps = [row[2] for row in data_rows if len(row) > 2]
        if not timestamps or len(timestamps) < 2:
            return 0.0

        converted_timestamps = [self.convert_timestamp(ts) for ts in timestamps]
        diffs = [(converted_timestamps[i + 1] - converted_timestamps[i]).total_seconds()
                 for i in range(len(converted_timestamps) - 1)]

        avg_diff = sum(diffs) / len(diffs) if diffs else 0
        return 1 / avg_diff if avg_diff > 0 else 0.0

    def _parse_trajectory_comments(self) -> dict:
        """
        Parse comment lines at the end of CSV file.
        Extracts velocity, load_data, and waypoint list.
        """
        result = {
            'velocity': None,
            'load_data': None,
            'waypoints': []
        }

        tool_weights = {
            'Goodarzi35':  15.5,
            'Goodarzi75':  19.5,
            'Goodarzi100': 22.0,
            'Goodarzi':    12.0,
            'Prototyp3D':  2.4,
        }

        def parse_vec(s: str) -> list[float]:
            """Parse '[1085.0000 -189.0000 965.5000]' → [1085.0, -189.0, 965.5]"""
            s = s.strip().strip('[]')
            return [float(x) for x in s.split()]

        with open(self.file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line.startswith('#'):
                    continue

                content = line[1:].strip()

                # velocity
                if content.startswith('velocity:'):
                    try:
                        result['velocity'] = float(content.split(':', 1)[1].strip())
                    except ValueError:
                        pass

                # load_data → weight
                elif content.startswith('load_data:'):
                    tool = content.split(':', 1)[1].strip()
                    result['load_data'] = tool
                    # longest match first
                    for name in sorted(tool_weights, key=len, reverse=True):
                        if name in tool:
                            result['weight'] = tool_weights[name]
                            break
                
                # stop_point
                elif content.startswith('stop_point:'):
                    try:
                        result['stop_point'] = float(content.split(':', 1)[1].strip())
                    except ValueError:
                        pass

                # wait_time
                elif content.startswith('wait_time:'):
                    try:
                        result['wait_time'] = float(content.split(':', 1)[1].strip())
                    except ValueError:
                        pass

                # seg_N: move_type; pos=[...]; quat=[...]; support_pos=[...]; support_quat=[...]
                elif content.startswith('seg_'):
                    try:
                        # split by ';'
                        parts = [p.strip() for p in content.split(';')]
                        # parts[0] = 'seg_1: linear'
                        move_type = parts[0].split(':', 1)[1].strip()

                        wp = {'move_type': move_type}

                        for part in parts[1:]:
                            if part.startswith('pos='):
                                wp['pos'] = parse_vec(part[4:])
                            elif part.startswith('quat='):
                                wp['quat'] = parse_vec(part[5:])
                            elif part.startswith('support_pos='):
                                wp['support_pos'] = parse_vec(part[12:])
                            elif part.startswith('support_quat='):
                                wp['support_quat'] = parse_vec(part[13:])

                        result['waypoints'].append(wp)
                    except Exception as e:
                        logger.warning(f'Could not parse waypoint line: {line} — {e}')

        return result

    def _match_waypoints_to_setpoints(
        self,
        setpoints_data: list,
        waypoints: list[dict]
    ) -> list:
        """
        Match waypoints from CSV comments to setpoints via exact position match.
        Fills move_type and support columns for circular waypoints.

        setpoints_data: list of records [traj_id, seg_id, timestamp, x, y, z, qx, qy, qz, qw]
        waypoints:      list of dicts with pos, quat, move_type, support_pos, support_quat

        Returns updated setpoints_data with support columns appended.
        """
        if not waypoints:
            return setpoints_data

        # Build position lookup from waypoints
        # key: (round(x,4), round(y,4), round(z,4)) → waypoint dict
        wp_lookup = {}
        for wp in waypoints:
            if 'pos' not in wp:
                continue
            key = (round(wp['pos'][0], 4), round(wp['pos'][1], 4), round(wp['pos'][2], 4))
            wp_lookup[key] = wp

        updated = []
        for record in setpoints_data:
            # record: [traj_id, seg_id, timestamp, x_reached, y_reached, z_reached,
            #          qx_reached, qy_reached, qz_reached, qw_reached]
            x = round(float(record[3]), 4) if record[3] is not None else None
            y = round(float(record[4]), 4) if record[4] is not None else None
            z = round(float(record[5]), 4) if record[5] is not None else None

            wp = wp_lookup.get((x, y, z))

            if wp and wp.get('move_type') == 'circular' and wp.get('support_pos'):
                sp = wp['support_pos']
                sq = wp.get('support_quat') or [None, None, None, None]
                record = list(record) + [
                    sp[0], sp[1], sp[2],
                    sq[0], sq[1], sq[2], sq[3]
                ]
            else:
                # linear or no match — support columns are NULL
                record = list(record) + [None, None, None, None, None, None, None]

            updated.append(tuple(record))

        return updated

    @staticmethod
    def convert_timestamp(ts):
        try:
            timestamp_seconds = int(ts) / 1_000_000_000.0
            return datetime.fromtimestamp(timestamp_seconds)
        except ValueError as e:
            print(f"Error converting timestamp {ts}: {e}")
            return None

    @staticmethod
    def extract_record_part(record_filename):
        if 'record' in record_filename:
            match = re.search(r'(record_\d{8}_\d{6})', record_filename)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def calculate_distance(x1, y1, z1, x2, y2, z2):
        """Berechnet den Abstand zwischen zwei 3D-Punkten."""
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2) ** 0.5