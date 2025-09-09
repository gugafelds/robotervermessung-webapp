import csv
import re
from datetime import datetime
from .db_config import MAPPINGS

class CSVProcessor:
    def __init__(self, file_path):
        self.ist_segments = None
        self.soll_segments = None
        self.soll_segments_with_ap = None
        self.ist_segments_with_ap = None
        self.file_path = file_path
        self.mappings = MAPPINGS

    def process_csv(self, robot_model, bahnplanung, source_data_ist,
                    source_data_soll, record_filename, segmentation_method="fixed_segments",
                    num_segments=3, reference_position=None):
        """Verarbeitet die CSV-Datei und bereitet Daten für den Datenbankupload vor."""

        print(f'Verarbeite CSV-Datei: {record_filename}')
        try:
            matrix_info = None
            with open(self.file_path, 'r') as matrixfile:
                for line in matrixfile:
                    if line.strip().startswith('# transformation_matrix:'):
                        matrix_info = line.strip().split(':', 1)[1].strip()
                        break

            with open(self.file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)

            #print(str(reference_position))
            #print(segmentation_method)

            # Pick&Place Metadaten extrahieren
            is_pickplace = "pickplace" in record_filename
            self.record_filename = record_filename
            weight, velocity_picking, velocity_handling = None, None, None
            handling_height = None

            if is_pickplace:
                # Extrahiere Pick&Place Metadaten
                for row in rows:
                    if velocity_picking is None and row.get('Velocity Picking', '').strip():
                        try:
                            velocity_picking = float(row['Velocity Picking'])
                        except ValueError:
                            print(f"Warnung: Ungültiger Wert für Velocity Picking: {row['Velocity Picking']}")

                    if velocity_handling is None and row.get('Velocity Handling', '').strip():
                        try:
                            velocity_handling = float(row['Velocity Handling'])
                        except ValueError:
                            print(f"Warnung: Ungültiger Wert für Velocity Handling: {row['Velocity Handling']}")

                    if all(v is not None for v in [velocity_picking, velocity_handling, weight]):
                        break

            # NEU: Teile die Daten in IST und SOLL Zeilen auf basierend auf den Spalten
            # IST-Spalten: timestamp, pv_x, pv_y, pv_z, ov_x, ov_y, ov_z, ov_w, pt_x, pt_y, pt_z, ot_x, ot_y, ot_z, ot_w,
            # tcp_speedv, tcp_angularv, tcp_accelv, tcp_accelv_angular, tcp_accel_pi, tcp_angular_vel_pi, segment_id_ist
            ist_spalten = ['timestamp', 'pv_x', 'pv_y', 'pv_z', 'ov_x', 'ov_y', 'ov_z', 'ov_w',
                           'pt_x', 'pt_y', 'pt_z', 'ot_x', 'ot_y', 'ot_z', 'ot_w', 'tcp_speedv',
                           'tcp_angularv', 'tcp_accelv', 'tcp_accel_pi',
                           'tcp_angular_vel_pi', 'segment_id_ist']

            # SOLL-Spalten: ps_x, ps_y, ps_z, os_x, os_y, os_z, os_w, tcp_speeds, joint_1, joint_2,
            # joint_3, joint_4, joint_5, joint_6, ap_x, ap_y, ap_z, aq_x, aq_y, aq_z, aq_w, DO_Signal,
            # Movement Type, Weight, Velocity Picking, Velocity Handling, segment_soll_id
            soll_spalten = ['ps_x', 'ps_y', 'ps_z', 'os_x', 'os_y', 'os_z', 'os_w', 'tcp_speedbs', 'tcp_accelbs',
                            'joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6',
                            'ap_x', 'ap_y', 'ap_z', 'aq_x', 'aq_y', 'aq_z', 'aq_w', 'DO_Signal',
                            'Movement Type', 'Weight', 'Velocity Picking', 'Velocity Handling',
                            'segment_id_soll']

            # Filtere Zeilen für IST-Daten anhand der IST-Spalten
            rows_ist = []
            for row in rows:
                # Prüfe, ob die Zeile gültige IST-Daten enthält
                if row.get('segment_id_ist') is not None and row.get('segment_id_ist') != '' and row.get(
                        'segment_id_ist') != 'NaN':
                    # Prüfe, ob die erforderlichen IST-Spalten Werte enthalten
                    if any(row.get(spalte) not in [None, '', 'NaN'] for spalte in ist_spalten if spalte in row):
                        rows_ist.append(row)

            # Filtere Zeilen für SOLL-Daten anhand der SOLL-Spalten
            rows_soll = []
            for row in rows:
                # Prüfe, ob die Zeile gültige SOLL-Daten enthält
                if row.get('segment_id_soll') is not None and row.get('segment_id_soll') != '' and row.get(
                        'segment_id_soll') != 'NaN':
                    # Prüfe, ob die erforderlichen SOLL-Spalten Werte enthalten
                    if any(row.get(spalte) not in [None, '', 'NaN'] for spalte in soll_spalten if
                           spalte in row):
                        rows_soll.append(row)

            # Wenn reference_position definiert ist, führe die positionsbasierte Segmentierung durch
            if segmentation_method == "reference_position":
                ref_x = float(reference_position[0])
                ref_y = float(reference_position[1])
                ref_z = float(reference_position[2])
                threshold = 0.3

                # print(f"Suche nach AP-Positionen nahe der Referenzposition: x={ref_x}, y={ref_y}, z={ref_z} mit Schwellenwert {threshold}mm")

                # Finde alle Zeilen mit AP-Positionen nahe der Referenzposition
                matching_rows = []

                for row in rows_soll:
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

                for i, row in enumerate(rows_soll[:200]):
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
                for row in rows_soll:
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
                        bahn_segments = all_segment_ids[start_idx:end_idx]
                        bahnen.append(bahn_segments)

                # Filtere Bahnen, die zu wenige Segmente haben (≤ 2)
                min_segments_per_bahn = 1
                valid_bahnen = []
                removed_bahnen = []

                for i, bahn_segments in enumerate(bahnen):
                    if len(bahn_segments) > min_segments_per_bahn:
                        valid_bahnen.append(bahn_segments)
                    else:
                        removed_bahnen.append((i, bahn_segments))

                # print(f"\nDefiniere {len(bahnen)} Bahnen basierend auf Referenzpunkten:")
                # for i, bahn_segments in enumerate(bahnen):
                #     start_segment = bahn_segments[0]
                #     end_segment = bahn_segments[-1]
                #
                #     print(f"  Bahn {i}: Segment {start_segment} bis {end_segment} ({len(bahn_segments)} Segmente)")
                #     if start_segment in segments_with_matches:
                #         ref_matches = segments_with_matches[start_segment]
                #         ref_count = len(ref_matches)
                #         avg_distance = sum(match['distance'] for match in ref_matches) / ref_count if ref_count > 0 else 0
                #         print(f"    Beginnt mit Referenzpunkt: {ref_count} Punkte, Ø Abstand: {avg_distance:.3f}mm")
                #     print(f"    Enthaltene Segmente: {', '.join(bahn_segments)}")

                # print(f"\nNach Filterung: {len(valid_bahnen)} gültige Bahnen (mehr als {min_segments_per_bahn} Segmente):")

                # Entfernte Bahnen ausgeben
                # if removed_bahnen:
                #     print(f"Entfernte Bahnen (≤ {min_segments_per_bahn} Segmente):")
                #     for bahn_idx, segments in removed_bahnen:
                #         print(f"  Bahn {bahn_idx}: {', '.join(segments)}")

                # Neue Bahn-Indizes zuweisen
                new_bahnen = {}
                for new_idx, bahn_segments in enumerate(valid_bahnen):
                    original_idx = bahnen.index(bahn_segments)
                    new_bahnen[new_idx] = {"segments": bahn_segments, "original_idx": original_idx}

                    # start_segment = bahn_segments[0]
                    # end_segment = bahn_segments[-1]
                    #
                    # print(f"  Bahn {new_idx} (ursprünglich Bahn {original_idx}): Segment {start_segment} bis {end_segment} ({len(bahn_segments)} Segmente)")
                    # print(f"    Enthaltene Segmente: {', '.join(bahn_segments)}")

                # Segment zu Bahn Mapping mit neuen Indizes
                segment_to_bahn = {}

                # Initialisiere alle Segmente mit "?"
                for segment_id in all_segment_ids:
                    segment_to_bahn[segment_id] = "?"

                # Weise Bahn-IDs zu
                for new_bahn_idx, bahn_info in new_bahnen.items():
                    for segment_id in bahn_info["segments"]:
                        segment_to_bahn[segment_id] = str(new_bahn_idx)

                #print("\nSegment zu Bahn Mapping (nach Filterung):")
                #for segment_id in all_segment_ids:
                #    bahn_id = segment_to_bahn.get(segment_id, "?")
                #    print(f"  Segment {segment_id} → Bahn {bahn_id}")

                # print("\nZusammenfassung der finalen Bahnen:")
                # for bahn_idx, bahn_info in new_bahnen.items():
                #     segments = bahn_info["segments"]
                #     print(f"  Bahn {bahn_idx}: {len(segments)} Segmente - {', '.join(segments)}")

                # Sammle alle Segmente aus den validen Bahnen
                valid_segments = []
                for bahn_info in new_bahnen.values():
                    valid_segments.extend(bahn_info["segments"])

                #print(f"\nVerwende {len(valid_segments)} Segmente für die weitere Verarbeitung:")
                #print(f"  {', '.join(valid_segments)}")

                # Filtere Zeilen für IST-Daten basierend auf den gültigen Segmenten
                rows_ist_filtered = []
                for row in rows_ist:
                    segment_id = row.get('segment_id_ist')
                    if segment_id in valid_segments:
                        rows_ist_filtered.append(row)

                # Filtere Zeilen für SOLL-Daten basierend auf den gültigen Segmenten
                rows_soll_filtered = []
                for row in rows_soll:
                    segment_id = row.get('segment_id_soll')
                    if segment_id in valid_segments:
                        rows_soll_filtered.append(row)

                # print(f"IST: Originale Anzahl Zeilen: {len(rows_ist)}, Nach Segment-Filterung: {len(rows_ist_filtered)}")
                # print(f"SOLL: Originale Anzahl Zeilen: {len(rows_soll)}, Nach Segment-Filterung: {len(rows_soll_filtered)}")

                # Bereite ein Mapping von Segment zu Bahn vor, das an process_data übergeben wird
                reference_segment_to_bahn = {}
                for segment_id in all_segment_ids:
                    bahn_id = segment_to_bahn.get(segment_id, None)
                    if bahn_id != "?" and bahn_id is not None:
                        reference_segment_to_bahn[segment_id] = bahn_id

                if robot_starts_at_ref:
                    print(f"DEBUG: Start-Segment: {start_segment}")
                    print(f"DEBUG: all_segment_ids: {all_segment_ids}")
                    print(f"DEBUG: ref_segment_ids VOR Änderung: {ref_segment_ids}")

                    print(f"DEBUG: ref_segment_ids NACH Änderung: {ref_segment_ids}")
                    print(f"DEBUG: Erste Bahn sollte beginnen bei Index: {all_segment_ids.index(start_segment) + 2 if start_segment in all_segment_ids else 'NICHT GEFUNDEN'}")

                # Verarbeite die Daten mit der reference_position Methode
                ist_rows_processed, ist_processed_data, ist_point_counts, ist_max_bahn, ist_bahn_ids = self.process_data(
                    rows_ist_filtered, source_data_ist, "ist", "reference_position",
                    segment_to_bahn_mapping=reference_segment_to_bahn
                )

                soll_rows_processed, soll_processed_data, soll_point_counts, soll_max_bahn, soll_bahn_ids = self.process_data(
                    rows_soll_filtered, source_data_soll, "soll", "reference_position",
                    segment_to_bahn_mapping=reference_segment_to_bahn
                )

            else:  # Bei allen anderen Methoden (z.B. fixed_segments) den ursprünglichen Code verwenden
                # Sammle alle eindeutigen IST-Segmente
                ist_segments = []
                for row in rows_ist:
                    segment_id = row.get('segment_id_ist')
                    if segment_id not in ist_segments:
                        ist_segments.append(segment_id)

                # Sammle alle eindeutigen SOLL-Segmente
                soll_segments = []
                for row in rows_soll:
                    segment_id = row.get('segment_id_soll')
                    if segment_id not in soll_segments:
                        soll_segments.append(segment_id)

                # Bestimme, welche IST-Segmente zu entfernen sind
                ist_segments_to_remove = []
                if len(ist_segments) >= 3:
                    ist_segments_to_remove = [ist_segments[0], ist_segments[-1]]
                    # print(f"IST: Entferne erstes Segment {ist_segments_to_remove[0]} und letztes Segment {ist_segments_to_remove[-1]}")
                else:
                    print(f"Warnung: Nur {len(ist_segments)} IST-Segmente gefunden, entferne keine")

                # Bestimme, welche SOLL-Segmente zu entfernen sind
                soll_segments_to_remove = []
                if len(soll_segments) >= 3:
                    soll_segments_to_remove = [soll_segments[0], soll_segments[-1]]
                    # print(f"SOLL: Entferne erstes Segment {soll_segments_to_remove[0]} und letztes Segment {soll_segments_to_remove[-1]}")
                else:
                    print(f"Warnung: Nur {len(soll_segments)} SOLL-Segmente gefunden, entferne keine")

                # Filtere IST-Zeilen
                rows_ist_filtered = []
                for row in rows_ist:
                    segment_id = row.get('segment_id_ist')
                    if segment_id not in ist_segments_to_remove:
                        rows_ist_filtered.append(row)

                # Filtere SOLL-Zeilen
                rows_soll_filtered = []
                for row in rows_soll:
                    segment_id = row.get('segment_id_soll')
                    if segment_id not in soll_segments_to_remove:
                        rows_soll_filtered.append(row)

                # print(f"IST: Originale Anzahl Zeilen: {len(rows_ist)}, Nach Filterung: {len(rows_ist_filtered)}")
                # print(f"SOLL: Originale Anzahl Zeilen: {len(rows_soll)}, Nach Filterung: {len(rows_soll_filtered)}")

                # Verwende:
                ist_rows_processed, ist_processed_data, ist_point_counts, ist_max_bahn, ist_bahn_ids = self.process_data(
                    rows_ist_filtered, source_data_ist, "ist", segmentation_method, num_segments
                )

                soll_rows_processed, soll_processed_data, soll_point_counts, soll_max_bahn, soll_bahn_ids = self.process_data(
                    rows_soll_filtered, source_data_soll, "soll", segmentation_method, num_segments
                )

            # Bestimme die maximale Anzahl von Bahnen
            max_bahnen = max(ist_max_bahn, soll_max_bahn)

            print("\nSynchronisiere IST- und SOLL-Bahn-IDs...")

            for bahn_idx in range(max_bahnen + 1):
                bahn_key = str(bahn_idx)

                # Hole IST- und SOLL-Bahn-IDs für diese Bahn
                ist_bahn_id = ist_bahn_ids.get(bahn_key, None)
                soll_bahn_id = soll_bahn_ids.get(bahn_key, None)

                # Prüfe, ob beide Bahn-IDs existieren
                if ist_bahn_id is not None and soll_bahn_id is not None:
                    # Prüfe, ob sie unterschiedlich sind
                    if ist_bahn_id != soll_bahn_id:
                        print(
                            f"  Bahn {bahn_idx}: IST-ID '{ist_bahn_id}' ≠ SOLL-ID '{soll_bahn_id}' -> Verwende IST-ID")

                        # Ersetze alle SOLL-Bahn-IDs mit der IST-Bahn-ID
                        for mapping_name in soll_processed_data.keys():
                            if bahn_key in soll_processed_data[mapping_name]:
                                for i in range(len(soll_processed_data[mapping_name][bahn_key])):
                                    row_data = soll_processed_data[mapping_name][bahn_key][i]
                                    if row_data and len(row_data) > 1:
                                        # Ersetze Bahn-ID an Position 0 und segment_id an Position 1
                                        old_segment_parts = row_data[1].split('_', 1)  # Format: [bahn_id]_[segment_nr]
                                        if len(old_segment_parts) == 2:
                                            new_segment_id = f"{ist_bahn_id}_{old_segment_parts[1]}"
                                        else:
                                            new_segment_id = f"{ist_bahn_id}_{old_segment_parts[0]}"

                                        soll_processed_data[mapping_name][bahn_key][i] = [
                                            ist_bahn_id,  # Neue Bahn-ID an Position 0
                                            new_segment_id,  # Neue segment_id an Position 1
                                            *row_data[2:]  # Rest der Daten unverändert
                                        ]

                        # Aktualisiere auch das soll_bahn_ids Dictionary
                        soll_bahn_ids[bahn_key] = ist_bahn_id

                    else:
                        print(f"  Bahn {bahn_idx}: IST-ID '{ist_bahn_id}' = SOLL-ID '{soll_bahn_id}' -> OK")
                elif ist_bahn_id is not None:
                    print(f"  Bahn {bahn_idx}: Nur IST-ID '{ist_bahn_id}' vorhanden")
                elif soll_bahn_id is not None:
                    print(f"  Bahn {bahn_idx}: Nur SOLL-ID '{soll_bahn_id}' vorhanden")

            print("Bahn-ID Synchronisation abgeschlossen.")

            print(f"Gefunden: {ist_max_bahn + 1} IST-Bahnen, {soll_max_bahn + 1} SOLL-Bahnen")

            # Kombiniere IST- und SOLL-Daten zu einer Liste von Bahnen pro Bahn-ID
            all_processed_data = []

            for bahn_idx in range(max_bahnen + 1):
                # Nehme die entsprechenden Daten für diese Bahn
                bahndaten = {
                    key: [] for key in self.mappings.keys()
                }

                # Sammle IST-Daten für diese Bahn
                for mapping_name in ist_processed_data.keys():
                    bahn_key = f"{bahn_idx}"
                    if bahn_key in ist_processed_data[mapping_name]:
                        bahndaten[mapping_name] = ist_processed_data[mapping_name][bahn_key]

                # Sammle SOLL-Daten für diese Bahn
                for mapping_name in soll_processed_data.keys():
                    bahn_key = f"{bahn_idx}"
                    if bahn_key in soll_processed_data[mapping_name]:
                        bahndaten[mapping_name] = soll_processed_data[mapping_name][bahn_key]

                # Wenn keine Daten für diese Bahn vorhanden sind, überspringe sie
                has_data = any(len(bahndaten[key]) > 0 for key in bahndaten.keys())
                if not has_data:
                    continue

                calibration_run = "calibration_run" in record_filename

                # Bestimme Zeitstempel der Bahn
                all_timestamps = []
                for key, data in bahndaten.items():
                    for row in data:
                        if len(row) > 2:  # Prüfe, ob Zeitstempel vorhanden
                            all_timestamps.append(row[2])  # Zeitstempel ist an Position 2

                if all_timestamps:
                    all_timestamps.sort()
                    start_time = str(self.convert_timestamp(all_timestamps[0]))
                    end_time = str(self.convert_timestamp(all_timestamps[-1]))
                    recording_date = start_time
                else:
                    # Fallback auf globale Zeitstempel
                    start_time = str(self.convert_timestamp(rows[0]['timestamp']))
                    end_time = str(self.convert_timestamp(rows[-1]['timestamp']))
                    recording_date = start_time

                bahn_id = None
                for key, data in bahndaten.items():
                    if data and len(data) > 0 and len(data[0]) > 0:
                        bahn_id = data[0][0]  # Nehme die erste Komponente der ersten Zeile
                        break

                # Berechne Punktzahlen für diese Bahn
                bahn_point_counts = {
                    'np_ereignisse': 0,
                    'np_pose_ist': len(bahndaten.get('POSE_MAPPING', [])),
                    'np_twist_ist': len(bahndaten.get('TWIST_IST_MAPPING', [])),
                    'np_accel_ist': len(bahndaten.get('ACCEL_IST_MAPPING', [])),
                    'np_accel_soll': len(bahndaten.get('ACCEL_SOLL_MAPPING', [])),
                    'np_pos_soll': len(bahndaten.get('POSITION_SOLL_MAPPING', [])),
                    'np_orient_soll': len(bahndaten.get('ORIENTATION_SOLL_MAPPING', [])),
                    'np_twist_soll': len(bahndaten.get('TWIST_SOLL_MAPPING', [])),
                    'np_jointstates': len(bahndaten.get('JOINT_MAPPING', [])),
                }

                # Berechne AP-Ereignisse basierend auf RAPID_EVENTS
                bahn_point_counts['np_ereignisse'] = len(bahndaten.get('RAPID_EVENTS_MAPPING', []))

                # Berechne Frequenzen basierend auf den Zeitstempeln
                bahn_frequencies = {
                    'frequency_pose': self.calculate_frequency_from_data(bahndaten.get('POSE_MAPPING', [])),
                    'frequency_position_soll': self.calculate_frequency_from_data(
                        bahndaten.get('POSITION_SOLL_MAPPING', [])),
                    'frequency_orientation_soll': self.calculate_frequency_from_data(
                        bahndaten.get('ORIENTATION_SOLL_MAPPING', [])),
                    'frequency_twist_ist': self.calculate_frequency_from_data(bahndaten.get('TWIST_IST_MAPPING', [])),
                    'frequency_twist_soll': self.calculate_frequency_from_data(bahndaten.get('TWIST_SOLL_MAPPING', [])),
                    'frequency_accel_ist': self.calculate_frequency_from_data(bahndaten.get('ACCEL_IST_MAPPING', [])),
                    'frequency_accel_soll': self.calculate_frequency_from_data(bahndaten.get('ACCEL_SOLL_MAPPING', [])),
                    'frequency_joint': self.calculate_frequency_from_data(bahndaten.get('JOINT_MAPPING', [])),
                    'frequency_imu': self.calculate_frequency_from_data(bahndaten.get('IMU_MAPPING', []))
                }

                # Erstelle Basis-Bahn-Info
                base_info = [
                    bahn_id,
                    robot_model,
                    bahnplanung,
                    recording_date,
                    start_time,
                    end_time,
                    source_data_ist,
                    source_data_soll,
                    self.extract_record_part(record_filename),
                    bahn_point_counts['np_ereignisse'],
                    bahn_frequencies['frequency_pose'],
                    bahn_frequencies['frequency_position_soll'],
                    bahn_frequencies['frequency_orientation_soll'],
                    bahn_frequencies['frequency_twist_ist'],
                    bahn_frequencies['frequency_twist_soll'],
                    bahn_frequencies['frequency_accel_ist'],
                    bahn_frequencies['frequency_joint'],
                    calibration_run,
                    bahn_point_counts['np_pose_ist'],
                    bahn_point_counts['np_twist_ist'],
                    bahn_point_counts['np_accel_ist'],
                    bahn_point_counts['np_pos_soll'],
                    bahn_point_counts['np_orient_soll'],
                    bahn_point_counts['np_twist_soll'],
                    bahn_point_counts['np_jointstates'],
                    self.extract_tool_weight_from_filename(record_filename),
                    handling_height,
                    velocity_handling,
                    velocity_picking,
                    is_pickplace,
                    matrix_info,
                    bahn_point_counts['np_accel_soll'],
                    bahn_frequencies['frequency_accel_soll'],
                    self.extract_velocity_from_filename(record_filename),
                    self.extract_stop_point_from_filename(record_filename),
                    self.extract_wait_time_from_filename(record_filename),
                ]

                if is_pickplace:
                    bahn_info_data = tuple(base_info + [
                        weight,
                        handling_height,
                        velocity_handling,
                        velocity_picking,
                        is_pickplace,
                    ])
                else:
                    bahn_info_data = tuple(base_info)

                bahndaten['bahn_info_data'] = bahn_info_data

                all_processed_data.append(bahndaten)

            print(f"CSV-Verarbeitung abgeschlossen: {len(all_processed_data)} Bahnen gefunden")
            return all_processed_data

        except Exception as e:
            import traceback
            print(f"Fehler bei der CSV-Verarbeitung: {e}")
            print(traceback.format_exc())
            return None

    def process_data(self, rows, source_data, data_type, segmentation_method="fixed_segments", num_segments=3,
                     segment_to_bahn_mapping=None):
        """
        Verarbeitet IST- oder SOLL-Daten aus den CSV-Zeilen.
        Die ersten und letzten Segmente wurden bereits entfernt.
        Bei reference_position werden die Bahnen anhand des übergebenen segment_to_bahn_mapping zugeordnet.
        Bei fixed_segments enthält jede Bahn genau num_segments Segmente,
        außer die letzte, die auch mehr enthalten kann, wenn Restsegmente vorhanden sind.

        Args:
            rows: Die CSV-Zeilen
            source_data: Die Datenquelle (z.B. "ros" oder "rapid")
            data_type: "ist" oder "soll"
            segmentation_method: Die Segmentierungsmethode
            num_segments: Anzahl der Segmente pro Bahn
            segment_to_bahn_mapping: Mapping von Segment-ID zu Bahn-ID (nur für reference_position)

        Returns:
            Tuple mit (rows_processed, processed_data, point_counts, max_bahn, bahn_ids)
        """
        # Definiere, welche Mappings für den Datentyp verwendet werden
        if data_type.lower() == "ist":
            segment_id_field = 'segment_id_ist'
            mappings_to_use = ['POSE_MAPPING', 'TWIST_IST_MAPPING', 'ACCEL_IST_MAPPING', 'TRANSFORM_MAPPING', 'IMU_MAPPING']
        elif data_type.lower() == "soll":
            segment_id_field = 'segment_id_soll'
            mappings_to_use = ['POSITION_SOLL_MAPPING', 'ORIENTATION_SOLL_MAPPING', 'TWIST_SOLL_MAPPING', 'ACCEL_SOLL_MAPPING',
                               'JOINT_MAPPING', 'RAPID_EVENTS_MAPPING']
        else:
            raise ValueError(f"Ungültiger Datentyp: {data_type}. Muss 'ist' oder 'soll' sein.")

        # Zähler für die Verarbeitung
        rows_processed = {key: 0 for key in mappings_to_use}

        # Container für verarbeitete Daten, getrennt nach Bahn
        processed_data = {key: {} for key in mappings_to_use}

        # Punktzähler initialisieren
        point_counts = {
            'np_ereignisse': 0,
            'np_pose_ist': 0,
            'np_twist_ist': 0,
            'np_accel_ist': 0,
            'np_accel_soll': 0,
            'np_pos_soll': 0,
            'np_orient_soll': 0,
            'np_twist_soll': 0,
            'np_jointstates': 0,
        }

        # Sammle zuerst alle eindeutigen Segmente
        all_segments = []
        for row in rows:
            segment_id = row.get(segment_id_field)
            if segment_id is not None and segment_id != '' and segment_id not in all_segments:
                all_segments.append(segment_id)

        # print(f"{data_type.upper()}: Verarbeite {len(all_segments)} gefilterte Segmente: {', '.join(all_segments)}")
        #print('Segment to Bahn Mapping:', segment_to_bahn_mapping)
        # Je nach Segmentierungsmethode unterschiedliche Verarbeitung
        if segmentation_method == "reference_position" and segment_to_bahn_mapping:
            # Bei reference_position wird das übergebene Mapping verwendet
            # print(f"{data_type.upper()}: Verwende reference_position Segmentierung mit vorgegebenem Bahn-Mapping")

            # Verwende das übergebene Mapping direkt
            segment_to_bahn = segment_to_bahn_mapping

            # Erstelle bahn_to_segments (umgekehrtes Mapping)
            bahn_to_segments = {}
            for segment_id, bahn_key in segment_to_bahn.items():
                if bahn_key not in bahn_to_segments:
                    bahn_to_segments[bahn_key] = []
                bahn_to_segments[bahn_key].append(segment_id)

            # Gib das verwendete Mapping aus
            # print(f"{data_type.upper()}: Bahn-Segmente basierend auf reference_position:")
            # for bahn_key, segments in sorted(bahn_to_segments.items(), key=lambda x: int(x[0])):
            #     print(f"  Bahn {bahn_key}: {', '.join(segments)}")

            # Bestimme maximale Bahn-ID
            max_bahn = max([int(bahn) for bahn in bahn_to_segments.keys()]) if bahn_to_segments else 0

        else:
            # Bei fixed_segments die ursprüngliche Segmentierung verwenden
            # Teile die Segmente in Bahnen mit je num_segments Segmenten ein,
            # wobei die letzte Bahn mehr Segmente haben kann, wenn Restsegmente übrig bleiben
            bahn_to_segments = {}

            # Wenn wir weniger Segmente haben als in einer Bahn sein sollten
            if len(all_segments) < num_segments:
                # Keine Bahnen erstellen, da nicht genug Segmente vorhanden
                bahn_to_segments = {}
                max_bahn = -1  # Keine Bahnen
                print(
                    f"Warnung: Nur {len(all_segments)} Segmente vorhanden, benötigt werden {num_segments}. Keine Bahnen erstellt.")
            else:
                # Berechne, wie viele vollständige Bahnen wir haben werden
                complete_bahnen = len(all_segments) // num_segments

                # Berechne, wie viele Restsegmente übrig bleiben
                remaining_segments = len(all_segments) % num_segments

                # Erstelle nur vollständige Bahnen mit exakt num_segments Segmenten
                for i in range(complete_bahnen):
                    start_idx = i * num_segments
                    end_idx = (i + 1) * num_segments
                    bahn_to_segments[str(i)] = all_segments[start_idx:end_idx]

                # Restsegmente werden NICHT verarbeitet (weggelassen)
                if remaining_segments > 0:
                    remaining_segment_list = all_segments[complete_bahnen * num_segments:]
                    print(
                        f"Info: {remaining_segments} Restsegmente werden weggelassen: {', '.join(remaining_segment_list)}")

                max_bahn = complete_bahnen - 1 if complete_bahnen > 0 else -1

            # Debug-Ausgabe
            # print(f"{data_type.upper()}-Segmente pro Bahn:")
            # for bahn, segments in sorted(bahn_to_segments.items(), key=lambda x: int(x[0])):
            #     print(f"  Bahn {bahn}: {', '.join(segments)}")

            # Erstelle ein Mapping von Segment-ID zu Bahn
            segment_to_bahn = {}
            for bahn_key, segments in bahn_to_segments.items():
                for segment_id in segments:
                    segment_to_bahn[segment_id] = bahn_key

        # Erstelle ein Mapping für neu nummerierte Segment-IDs innerhalb jeder Bahn
        segment_id_mapping = {}
        for bahn_key, segments in bahn_to_segments.items():
            for i, segment_id in enumerate(segments):
                segment_id_mapping[(bahn_key, segment_id)] = i + 1  # Segment-IDs beginnen bei 1

        # Neue Datenstruktur für Bahn-Zeitstempel
        bahn_timestamps = {}

        # Verarbeite jede Zeile
        for i, row in enumerate(rows):
            timestamp = row['timestamp']
            segment_id = row.get(segment_id_field)

            # Überspringen, wenn keine gültige Segment-ID
            if segment_id is None or segment_id == '':
                continue

            # Bestimme die Bahn für dieses Segment
            bahn_key = segment_to_bahn.get(segment_id)
            if bahn_key is None:
                continue  # Dieses Segment wurde keiner Bahn zugeordnet

            # Initialisiere Bahn-Zeitstempel, falls noch nicht vorhanden
            if bahn_key not in bahn_timestamps:
                bahn_timestamps[bahn_key] = []
            bahn_timestamps[bahn_key].append(timestamp)

            # Verarbeite Mappings
            for mapping_name in mappings_to_use:
                if mapping_name not in self.mappings:
                    continue

                mapping = self.mappings[mapping_name]

                # Verwende gemappte Segment-ID
                bahn_segment_id = str(segment_id_mapping.get((bahn_key, segment_id), 0))
                if bahn_segment_id == '0':
                    continue  # Keine gültige Zuordnung gefunden

                # Erstelle die Bahn-Schlüssel, falls noch nicht vorhanden
                if bahn_key not in processed_data[mapping_name]:
                    processed_data[mapping_name][bahn_key] = []

                # Verarbeite die Daten und speichere sie nach Bahn gruppiert
                result = self.process_mapping_row(
                    row, mapping, bahn_key, bahn_segment_id, timestamp,
                    source_data, point_counts, mapping_name
                )

                if result:
                    processed_data[mapping_name][bahn_key].append(result)
                    rows_processed[mapping_name] += 1

        # Generiere für jede Bahn eine eindeutige ID basierend auf dem ersten Zeitstempel
        bahn_ids = {}
        for bahn_key, timestamps in bahn_timestamps.items():
            if timestamps:
                # Verwende den frühesten Zeitstempel
                earliest_timestamp = min(timestamps)
                bahn_ids[bahn_key] = str(earliest_timestamp[:10])

        # Aktualisiere alle verarbeiteten Daten mit der richtigen Bahn-ID
        for mapping_name in processed_data.keys():
            for bahn_key in processed_data[mapping_name]:
                if bahn_key in bahn_ids:
                    bahn_id = bahn_ids[bahn_key]
                    for i in range(len(processed_data[mapping_name][bahn_key])):
                        # Ersetze die Bahn-ID und aktualisiere das segment_id Format
                        if processed_data[mapping_name][bahn_key][i]:
                            row_data = processed_data[mapping_name][bahn_key][i]
                            processed_data[mapping_name][bahn_key][i] = [
                                bahn_id,  # Bahn-ID an Position 0
                                f"{bahn_id}_{row_data[1]}",  # Neue segment_id im Format [bahn_id]_[segmentzahl]
                                *row_data[2:]  # Rest der Daten unverändert
                            ]

        # Gib am Ende die gefundenen Bahn-IDs und die zugehörigen Segment-IDs aus
        # print(f"\n{data_type.upper()}-Bahnen und zugehörige Segmente:")
        # for bahn_key, segments in sorted(bahn_to_segments.items(), key=lambda x: int(x[0])):
        #     bahn_id = bahn_ids.get(bahn_key, "Unbekannt")
        #     segment_list = []
        #     for segment in segments:
        #         mapped_id = segment_id_mapping.get((bahn_key, segment), "?")
        #         segment_list.append(f"{segment} (ID: {mapped_id})")
        #     print(f"  Bahn {bahn_key} (ID: {bahn_id}): Segmente = {', '.join(segment_list)}")

        # Detaillierte Ausgabe der Bahn-ID-Zuordnungen
        print(f"\n{data_type.upper()}-Bahn-ID-Zuordnungen:")
        for bahn_key, bahn_id in sorted(bahn_ids.items(), key=lambda x: int(x[0])):
            print(f"  Bahn {bahn_key} hat ID: {bahn_id}")
            print(f"    Enthält Segmente: {', '.join(bahn_to_segments.get(bahn_key, []))}")
            # Zeige die gemappten Segment-IDs
            mapped_segments = []
            for segment in bahn_to_segments.get(bahn_key, []):
                mapped_id = segment_id_mapping.get((bahn_key, segment), "?")
                mapped_segments.append(f"{segment} → {mapped_id}")
            print(f"    Segment-Mapping: {', '.join(mapped_segments)}")

        # print(f"{data_type.upper()}-Datenverarbeitung: {sum(rows_processed.values())} Zeilen, {max_bahn + 1} Bahnen")
        return rows_processed, processed_data, point_counts, max_bahn, bahn_ids

    def process_mapping_row(self, row, mapping, bahn_id, segment_id, timestamp, source_data,
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

        # Für RAPID_EVENTS (AP-Punkte) - spezielle Behandlung
        if mapping_name == 'RAPID_EVENTS_MAPPING':
            # Nur verarbeiten, wenn mindestens ein Wert vorhanden ist
            if any(row.get(csv_col, '').strip() for csv_col in mapping):
                # Erstelle Datenzeile
                data_row = [bahn_id, segment_id, timestamp]
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
                data_row.append(source_data)

                # Bewegungstyp hinzufügen (falls verfügbar)
                if movement_types and "pickplace" in getattr(self, 'record_filename', ''):
                    data_row.append(movement_types.get(segment_id))
                else:
                    data_row.append(None)

                return data_row

        # Für alle anderen Mappings
        else:
            # Nur verarbeiten, wenn alle erforderlichen Werte vorhanden sind
            if all(row.get(csv_col, '').strip() for csv_col in mapping):
                data_row = [bahn_id, segment_id, timestamp]
                values = []

                # Werte aus dem Mapping extrahieren
                for csv_col in mapping:
                    value = row.get(csv_col, '')
                    values.append(convert_value(value))

                data_row.extend(values)

                # Quelle hinzufügen (speziell für IMU-Daten)
                if mapping_name == 'IMU_MAPPING':
                    data_row.append('sensehat')
                else:
                    data_row.append(source_data)

                # Punktzähler aktualisieren
                if mapping_name == 'POSE_MAPPING':
                    point_counts['np_pose_ist'] += 1
                elif mapping_name == 'TWIST_IST_MAPPING':
                    point_counts['np_twist_ist'] += 1
                elif mapping_name == 'ACCEL_IST_MAPPING':
                    point_counts['np_accel_ist'] += 1
                elif mapping_name == 'POSITION_SOLL_MAPPING':
                    point_counts['np_pos_soll'] += 1
                elif mapping_name == 'ORIENTATION_SOLL_MAPPING':
                    point_counts['np_orient_soll'] += 1
                elif mapping_name == 'TWIST_SOLL_MAPPING':
                    point_counts['np_twist_soll'] += 1
                elif mapping_name == 'JOINT_MAPPING':
                    point_counts['np_jointstates'] += 1
                elif mapping_name == 'ACCEL_SOLL_MAPPING':
                    point_counts['np_accel_soll'] += 1
                elif mapping_name == 'IMU_MAPPING':
                    point_counts['np_imu'] += 1

                return data_row

        return None

    def calculate_frequency_from_data(self, data_rows):
        """Berechnet die Frequenz basierend auf Zeitstempeln in den Datenzeilen."""
        if not data_rows or len(data_rows) < 2:
            return 0.0

        timestamps = [row[2] for row in data_rows if len(row) > 2]  # Zeitstempel an Position 2
        if not timestamps or len(timestamps) < 2:
            return 0.0

        converted_timestamps = [self.convert_timestamp(ts) for ts in timestamps]
        diffs = [(converted_timestamps[i + 1] - converted_timestamps[i]).total_seconds()
                 for i in range(len(converted_timestamps) - 1)]

        avg_diff = sum(diffs) / len(diffs) if diffs else 0
        return 1 / avg_diff if avg_diff > 0 else 0.0

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
    def extract_velocity_from_filename(filename):
        match = re.search(r'_v(\d+)_', filename)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def extract_tool_weight_from_filename(filename):
        tool_weights = {
            'TProbeZylWW': 3.7
        }

        for tool_name, weight in tool_weights.items():
            if tool_name in filename:
                return weight
        return None

    @staticmethod
    def extract_stop_point_from_filename(filename):
        match = re.search(r'_inpos(\d+(?:\.\d+)?)_', filename)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def extract_wait_time_from_filename(filename):
        match = re.search(r'_wt(\d+(?:\.\d+)?)_', filename)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def calculate_distance(x1, y1, z1, x2, y2, z2):
        """Berechnet den Abstand zwischen zwei 3D-Punkten."""
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2) ** 0.5