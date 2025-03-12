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
            WHERE bahn_id = $1 AND evaluation = 'position'
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
            WHERE bahn_id IN ({bahn_ids_list}) AND evaluation = 'position'
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

