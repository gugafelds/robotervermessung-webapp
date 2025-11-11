import os
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from ...database import get_db
import logging
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

########################## AUSWERTUNGSDATEN #########################################


@router.get("/auswertung_info_overview")
async def get_auswertung_info_overview(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Number of entries per page"),
        conn=Depends(get_db)
):
    """
    Endpoint to retrieve bahn_ids from info tables and corresponding bahn_info details
    with pagination support.

    This endpoint does the following:
    1. Finds all info tables in the auswertung schema
    2. Retrieves unique bahn_ids from these tables
    3. Fetches corresponding bahn_info details with pagination
    """
    try:
        # 1. Find all relevant info tables
        table_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'auswertung' 
        AND table_name LIKE 'info_%'
        """

        tables = await conn.fetch(table_query)

        if not tables:
            logger.warning("No info tables found in schema auswertung")
            raise HTTPException(status_code=404, detail="No info tables found")

        # 2. Create UNION query for all bahn_ids
        union_queries = [
            f"SELECT DISTINCT bahn_id FROM auswertung.{table['table_name']}"
            for table in tables
        ]
        bahn_ids_query = " UNION ".join(union_queries)

        # 3. Count total unique bahn_ids for pagination
        count_query = f"""
        WITH unique_bahn_ids AS ({bahn_ids_query})
        SELECT COUNT(DISTINCT bahn_id) FROM unique_bahn_ids
        """
        total_count = await conn.fetchval(count_query)

        # Calculate offset for SQL query
        offset = (page - 1) * page_size

        # 4. Fetch Bahn-Info data with pagination
        bahn_info_query = f"""
        WITH unique_bahn_ids AS ({bahn_ids_query})
        SELECT bi.* 
        FROM bewegungsdaten.bahn_info bi
        INNER JOIN unique_bahn_ids ubi ON bi.bahn_id = ubi.bahn_id
        ORDER BY bi.recording_date DESC, bi.bahn_id
        LIMIT {page_size} OFFSET {offset}
        """

        bahn_info_rows = await conn.fetch(bahn_info_query)

        if not bahn_info_rows and page > 1:
            # If requested page has no data but previous pages exist
            raise HTTPException(status_code=404, detail="Page number exceeds available pages")

        # Calculate total pages
        total_pages = (total_count + page_size - 1) // page_size

        return {
            "bahn_info": [dict(row) for row in bahn_info_rows],
            "pagination": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }

    except Exception as e:
        logger.error(f"Error fetching info tables overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/auswertung_info/{bahn_id}")
async def get_auswertung_info_by_id(
        bahn_id: str,
        conn=Depends(get_db)
):
    """
    Endpoint to retrieve auswertung info data for a specific bahn_id
    from all info tables.

    This endpoint:
    1. Finds all info tables in the auswertung schema
    2. Retrieves info data for the given bahn_id from these tables
    """
    try:
        # 1. Find all relevant info tables
        table_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'auswertung' 
        AND table_name LIKE 'info_%'
        """

        tables = await conn.fetch(table_query)

        if not tables:
            logger.warning("No info tables found in schema auswertung")
            raise HTTPException(status_code=404, detail="No info tables found")

        # 2. Retrieve data from info tables for specific bahn_id
        result: Dict[str, List[Dict[str, Any]]] = {}

        for table in tables:
            table_name = table['table_name']
            query = """
            SELECT *
            FROM auswertung.{} 
            WHERE bahn_id = $1
            """.format(table_name)

            rows = await conn.fetch(query, bahn_id)

            if rows:
                result[table_name] = [dict(row) for row in rows]

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No auswertung info found for bahn_id {bahn_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error fetching auswertung info for {bahn_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/auswertung_info")
async def get_auswertung_info(
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Anzahl der Einträge pro Seite"),
        conn=Depends(get_db)
):
    try:
        # 1. Finde alle relevanten Tabellen
        table_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'auswertung' 
        AND table_name LIKE 'info_%'
        """

        tables = await conn.fetch(table_query)

        if not tables:
            logger.warning("No info tables found in schema auswertung")
            raise HTTPException(status_code=404, detail="No info tables found")

        # 2. UNION Query für alle bahn_ids erstellen
        union_queries = []
        for table in tables:
            table_name = table['table_name']
            union_queries.append(f"SELECT DISTINCT bahn_id FROM auswertung.{table_name}")

        bahn_ids_query = " UNION ".join(union_queries)

        # 3. Zähle die Gesamtanzahl der einzigartigen bahn_ids für Pagination
        count_query = f"""
        WITH unique_bahn_ids AS ({bahn_ids_query})
        SELECT COUNT(DISTINCT bahn_id) FROM unique_bahn_ids
        """
        total_count = await conn.fetchval(count_query)

        # Berechne den Offset für die SQL-Abfrage
        offset = (page - 1) * page_size

        # 4. Hole Bahn-Info Daten mit Pagination
        bahn_info_query = f"""
        WITH unique_bahn_ids AS ({bahn_ids_query})
        SELECT bi.* 
        FROM bewegungsdaten.bahn_info bi
        INNER JOIN unique_bahn_ids ubi ON bi.bahn_id = ubi.bahn_id
        ORDER BY bi.recording_date DESC, bi.bahn_id
        LIMIT {page_size} OFFSET {offset}
        """

        bahn_info_rows = await conn.fetch(bahn_info_query)

        if not bahn_info_rows and page > 1:
            # Falls die angeforderte Seite keine Daten enthält, aber es gibt vorherige Seiten
            raise HTTPException(status_code=404, detail="Page number exceeds available pages")

        # 5. Hole nur die bahn_ids für die aktuelle Seite
        current_bahn_ids = [row['bahn_id'] for row in bahn_info_rows]
        bahn_ids_list = ', '.join(f"'{bid}'" for bid in current_bahn_ids)

        # 6. Hole Daten aus allen auswertung._info Tabellen für die aktuelle Seite
        result = {}

        # Zuerst die bahn_info Daten
        result["bahn_info"] = [dict(row) for row in bahn_info_rows]

        # Dann die Daten aus den auswertung._info Tabellen
        result["auswertung_info"] = {}

        for table in tables:
            table_name = table['table_name']
            query = f"""
            SELECT *
            FROM auswertung.{table_name}
            WHERE bahn_id IN ({bahn_ids_list})
            ORDER BY bahn_id
            """

            rows = await conn.fetch(query)
            if rows:
                result["auswertung_info"][table_name] = [dict(row) for row in rows]

        # Berechne die Gesamtanzahl der Seiten
        total_pages = (total_count + page_size - 1) // page_size

        # Pagination-Metadaten zum Ergebnis hinzufügen
        result["pagination"] = {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }

        return result

    except Exception as e:
        logger.error(f"Error fetching info tables data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/position_euclidean/{bahn_id}")
@cache(expire=2400)
async def get_position_euclidean_by_id(bahn_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            bahn_id,
            segment_id,
            euclidean_distances,
            ea_soll_x,
            ea_soll_y,
            ea_soll_z,
            ea_ist_x,
            ea_ist_y,
            ea_ist_z,
            points_order
        FROM auswertung.position_euclidean 
        WHERE bahn_id = $1
        ORDER BY points_order ASC
        """

        rows = await conn.fetch(query, bahn_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No euclidean deviation data found for bahn_id {bahn_id}")

        return {
            "position_euclidean": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching euclidean deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/position_dfd/{bahn_id}")
@cache(expire=2400)
async def get_position_dfd_by_id(bahn_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            bahn_id,
            segment_id,
            dfd_distances,
            dfd_soll_x,
            dfd_soll_y,
            dfd_soll_z,
            dfd_ist_x,
            dfd_ist_y,
            dfd_ist_z,
            points_order
        FROM auswertung.position_dfd 
        WHERE bahn_id = $1
        ORDER BY points_order ASC
        """

        rows = await conn.fetch(query, bahn_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No DFD deviation data found for bahn_id {bahn_id}")

        return {
            "position_dfd": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching DFD deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/position_sidtw/{bahn_id}")
@cache(expire=2400)
async def get_position_sidtw_by_id(bahn_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            bahn_id,
            segment_id,
            sidtw_distances,
            sidtw_soll_x,
            sidtw_soll_y,
            sidtw_soll_z,
            sidtw_ist_x,
            sidtw_ist_y,
            sidtw_ist_z,
            points_order
        FROM auswertung.position_sidtw 
        WHERE bahn_id = $1
        ORDER BY points_order ASC
        """

        rows = await conn.fetch(query, bahn_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No SIDTW deviation data found for bahn_id {bahn_id}")

        return {
            "position_sidtw": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching SIDTW deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/position_dtw/{bahn_id}")
@cache(expire=2400)
async def get_position_dtw_by_id(bahn_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            bahn_id,
            segment_id,
            dtw_distances,
            dtw_soll_x,
            dtw_soll_y,
            dtw_soll_z,
            dtw_ist_x,
            dtw_ist_y,
            dtw_ist_z,
            points_order
        FROM auswertung.position_dtw 
        WHERE bahn_id = $1
        ORDER BY points_order ASC
        """

        rows = await conn.fetch(query, bahn_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No DTW deviation data found for bahn_id {bahn_id}")

        return {
            "position_dtw": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching DTW deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/has_deviation_data/{bahn_id}")
@cache(expire=2400)
async def check_deviation_data(bahn_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            CASE 
                WHEN EXISTS (SELECT 1 FROM auswertung.position_euclidean WHERE bahn_id = $1) OR
                     EXISTS (SELECT 1 FROM auswertung.position_dfd WHERE bahn_id = $1) OR
                     EXISTS (SELECT 1 FROM auswertung.position_sidtw WHERE bahn_id = $1) OR 
                     EXISTS (SELECT 1 FROM auswertung.position_dtw WHERE bahn_id = $1)
                THEN true
                ELSE false
            END as has_data
        """

        result = await conn.fetchrow(query, bahn_id)
        return {"has_deviation_data": result['has_data']}

    except Exception as e:
        logger.error(f"Error checking deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/has_orientation_data/{bahn_id}")
@cache(expire=2400)
async def check_orientation_data(bahn_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            CASE 
                WHEN EXISTS (SELECT 1 FROM auswertung.orientation_qad WHERE bahn_id = $1) OR
                     EXISTS (SELECT 1 FROM auswertung.orientation_qdtw WHERE bahn_id = $1)
                THEN true
                ELSE false
            END as has_data
        """

        result = await conn.fetchrow(query, bahn_id)
        return {"has_orientation_data": result['has_data']}

    except Exception as e:
        logger.error(f"Error checking orientation data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_auswertung_bahn_ids(
        query: str = Query(None, description="Suchbegriff für Freitext-Suche (Filename, ID, Datum)"),
        calibration: bool = Query(None, description="Nur Kalibrierungsläufe"),
        pick_place: bool = Query(None, description="Nur Pick-and-Place-Läufe"),
        points_events: int = Query(None, description="Anzahl der Punktereignisse"),
        weight: float = Query(None, description="Gewicht"),
        velocity: int = Query(None, description="Geschwindigkeit"),
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Einträge pro Seite"),
        conn=Depends(get_db)
):
    try:
        # Der entscheidende Unterschied: Wir verbinden die bahn_info mit auswertung_info_euclidean
        # Wir selektieren nur die Bahnen, für die auch Auswertungsdaten existieren
        base_query = """
        SELECT DISTINCT bi.* 
        FROM bewegungsdaten.bahn_info bi
        JOIN auswertung.info_euclidean ie ON bi.bahn_id = ie.bahn_id
        WHERE 1=1
        """

        params = []
        param_index = 1

        # Filter hinzufügen basierend auf Parametern
        if query:
            # Da bahn_id ein varchar ist, behandeln wir alle Suchen als Text
            search_conditions = []

            # bahn_id (teilweise Übereinstimmung)
            search_conditions.append(f"bi.bahn_id ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Dateiname (teilweise Übereinstimmung)
            search_conditions.append(f"bi.record_filename ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Datum
            search_conditions.append(f"bi.recording_date ILIKE ${param_index}")
            params.append(f"%{query}%")
            param_index += 1

            # Alle Bedingungen mit OR verbinden
            base_query += f" AND ({' OR '.join(search_conditions)})"

        if calibration is not None:
            base_query += f" AND bi.calibration_run = ${param_index}"
            params.append(calibration)
            param_index += 1

        if pick_place is not None:
            base_query += f" AND bi.pick_and_place_run = ${param_index}"
            params.append(pick_place)
            param_index += 1

        if points_events is not None:
            base_query += f" AND bi.np_ereignisse = ${param_index}"
            params.append(points_events)
            param_index += 1

        if weight is not None:
            base_query += f" AND bi.weight = ${param_index}"
            params.append(weight)
            param_index += 1

        if velocity is not None:
            base_query += f" AND bi.velocity_picking = ${param_index}"
            params.append(velocity)
            param_index += 1

        # Zähle Gesamtanzahl für Pagination
        count_query = f"SELECT COUNT(*) FROM ({base_query}) AS filtered_data"
        total_count = await conn.fetchval(count_query, *params)

        # Füge Sortierung und Pagination hinzu
        query = base_query + f" ORDER BY bi.recording_date DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.extend([page_size, (page - 1) * page_size])

        rows = await conn.fetch(query, *params)
        bahn_info_list = [dict(row) for row in rows]

        # Keine Ergebnisse und Seite > 1
        if not bahn_info_list and page > 1:
            raise HTTPException(status_code=404, detail="Page number exceeds available pages")

        total_pages = (total_count + page_size - 1) // page_size

        return {
            "bahn_info": bahn_info_list,
            "pagination": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }

    except Exception as e:
        logger.error(f"Error searching Auswertung bahn info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    
    
@router.get("/orientation_qad/{bahn_id}")
async def get_orientation_qad_by_id(bahn_id: str, conn=Depends(get_db)):
    try:
        query = """
                SELECT 
                    bahn_id,
                    segment_id,
                    qad_distances,
                    qad_soll_x,
                    qad_soll_y,
                    qad_soll_z,
                    qad_soll_w,
                    qad_ist_x,
                    qad_ist_y,
                    qad_ist_z,
                    qad_ist_w,
                    points_order
                FROM auswertung.orientation_qad 
                WHERE bahn_id = $1
                ORDER BY points_order ASC
                """

        rows = await conn.fetch(query, bahn_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No QAD orientation data found for bahn_id {bahn_id}")

        return {
            "orientation_qad": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching QAD orientation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/orientation_qdtw/{bahn_id}")
@cache(expire=2400)
async def get_orientation_qdtw_by_id(bahn_id: str, conn=Depends(get_db)):
    try:
        query = """
                SELECT 
                    bahn_id,
                    segment_id,
                    qdtw_distances,
                    qdtw_soll_x,
                    qdtw_soll_y,
                    qdtw_soll_z,
                    qdtw_soll_w,
                    qdtw_ist_x,
                    qdtw_ist_y,
                    qdtw_ist_z,
                    qdtw_ist_w,
                    points_order
                FROM auswertung.orientation_qdtw 
                WHERE bahn_id = $1
                ORDER BY points_order ASC
                """

        rows = await conn.fetch(query, bahn_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No QDTW deviation data found for bahn_id {bahn_id}")

        return {
            "orientation_qdtw": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching qdtw deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")