import os
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from ...database import get_db
import logging
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/evaluation_info/{traj_id}")
async def get_evaluation_info_by_id(
        traj_id: str,
        conn=Depends(get_db)
):
    """
    Endpoint to retrieve evaluation info data for a specific traj_id
    from all info tables.

    This endpoint:
    1. Finds all info tables in the evaluation schema
    2. Retrieves info data for the given traj_id from these tables
    """
    try:
        # 1. Find all relevant info tables
        table_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'evaluation' 
        AND table_name LIKE '%info%'
        """

        tables = await conn.fetch(table_query)

        if not tables:
            logger.warning("No info tables found in schema evaluation")
            raise HTTPException(status_code=404, detail="No info tables found")

        # 2. Retrieve data from info tables for specific traj_id
        result: Dict[str, List[Dict[str, Any]]] = {}

        for table in tables:
            table_name = table['table_name']
            query = """
            SELECT *
            FROM evaluation.{} 
            WHERE traj_id = $1
            """.format(table_name)

            rows = await conn.fetch(query, traj_id)

            if rows:
                result[table_name] = [dict(row) for row in rows]

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No evaluation info found for traj_id {traj_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error fetching evaluation info for {traj_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/evaluation_info")
async def get_evaluation_info(
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Anzahl der Einträge pro Seite"),
        conn=Depends(get_db)
):
    try:
        # 1. Finde alle relevanten Tabellen
        table_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'evaluation' 
        AND table_name LIKE '%_info'
        """

        tables = await conn.fetch(table_query)

        if not tables:
            logger.warning("No info tables found in schema evaluation")
            raise HTTPException(status_code=404, detail="No info tables found")

        # 2. UNION Query für alle traj_ids erstellen
        union_queries = []
        for table in tables:
            table_name = table['table_name']
            union_queries.append(f"SELECT DISTINCT traj_id FROM evaluation.{table_name}")

        traj_ids_query = " UNION ".join(union_queries)

        # 3. Zähle die Gesamtanzahl der einzigartigen traj_ids für Pagination
        count_query = f"""
        WITH unique_traj_ids AS ({traj_ids_query})
        SELECT COUNT(DISTINCT traj_id) FROM unique_traj_ids
        """
        total_count = await conn.fetchval(count_query)

        # Berechne den Offset für die SQL-Abfrage
        offset = (page - 1) * page_size

        # 4. Hole Bahn-Info Daten mit Pagination
        traj_info_query = f"""
        WITH unique_traj_ids AS ({traj_ids_query})
        SELECT bi.* 
        FROM motion.traj_info bi
        INNER JOIN unique_traj_ids ubi ON bi.traj_id = ubi.traj_id
        ORDER BY bi.recording_date DESC, bi.traj_id
        LIMIT {page_size} OFFSET {offset}
        """

        traj_info_rows = await conn.fetch(traj_info_query)

        if not traj_info_rows and page > 1:
            # Falls die angeforderte Seite keine Daten enthält, aber es gibt vorherige Seiten
            raise HTTPException(status_code=404, detail="Page number exceeds available pages")

        # 5. Hole nur die traj_ids für die aktuelle Seite
        current_traj_ids = [row['traj_id'] for row in traj_info_rows]
        traj_ids_list = ', '.join(f"'{bid}'" for bid in current_traj_ids)

        # 6. Hole Daten aus allen evaluation._info Tabellen für die aktuelle Seite
        result = {}

        # Zuerst die traj_info Daten
        result["traj_info"] = [dict(row) for row in traj_info_rows]

        # Dann die Daten aus den evaluation._info Tabellen
        result["evaluation_info"] = {}

        for table in tables:
            table_name = table['table_name']
            query = f"""
            SELECT *
            FROM evaluation.{table_name}
            WHERE traj_id IN ({traj_ids_list})
            ORDER BY traj_id
            """

            rows = await conn.fetch(query)
            if rows:
                result["evaluation_info"][table_name] = [dict(row) for row in rows]

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


@router.get("/ed_evaluation/{traj_id}")
@cache(expire=2400)
async def get_position_euclidean_by_id(traj_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            traj_id,
            seg_id,
            ed_deviation,
            ed_cmd_x,
            ed_cmd_y,
            ed_cmd_z,
            ed_act_x,
            ed_act_y,
            ed_act_z,
            points_order
        FROM evaluation.ed_evaluation 
        WHERE traj_id = $1
        ORDER BY points_order ASC
        """

        rows = await conn.fetch(query, traj_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No euclidean deviation data found for traj_id {traj_id}")

        return {
            "position_euclidean": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching euclidean deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

'''
@router.get("/position_dfd/{traj_id}")
@cache(expire=2400)
async def get_position_dfd_by_id(traj_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            traj_id,
            seg_id,
            dfd_deviation,
            dfd_cmd_x,
            dfd_cmd_y,
            dfd_cmd_z,
            dfd_act_x,
            dfd_act_y,
            dfd_act_z,
            points_order
        FROM evaluation.position_dfd 
        WHERE traj_id = $1
        ORDER BY points_order ASC
        """

        rows = await conn.fetch(query, traj_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No DFD deviation data found for traj_id {traj_id}")

        return {
            "position_dfd": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching DFD deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
'''

@router.get("/sidtw_evaluation/{traj_id}")
@cache(expire=2400)
async def get_position_sidtw_by_id(traj_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            traj_id,
            seg_id,
            sidtw_deviation,
            sidtw_cmd_x,
            sidtw_cmd_y,
            sidtw_cmd_z,
            sidtw_act_x,
            sidtw_act_y,
            sidtw_act_z,
            points_order
        FROM evaluation.sidtw_evaluation 
        WHERE traj_id = $1
        ORDER BY points_order ASC
        """

        rows = await conn.fetch(query, traj_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No SIDTW deviation data found for traj_id {traj_id}")

        return {
            "position_sidtw": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching SIDTW deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

'''
@router.get("/position_dtw/{traj_id}")
@cache(expire=2400)
async def get_position_dtw_by_id(traj_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            traj_id,
            seg_id,
            dtw_deviation,
            dtw_cmd_x,
            dtw_cmd_y,
            dtw_cmd_z,
            dtw_act_x,
            dtw_act_y,
            dtw_act_z,
            points_order
        FROM evaluation.position_dtw 
        WHERE traj_id = $1
        ORDER BY points_order ASC
        """

        rows = await conn.fetch(query, traj_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No DTW deviation data found for traj_id {traj_id}")

        return {
            "position_dtw": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching DTW deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
'''

@router.get("/has_deviation_data/{traj_id}")
@cache(expire=2400)
async def check_deviation_data(traj_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            CASE 
                WHEN EXISTS (SELECT 1 FROM evaluation.ed_evaluation WHERE traj_id = $1) OR
                     EXISTS (SELECT 1 FROM evaluation.sidtw_evaluation WHERE traj_id = $1)
                THEN true
                ELSE false
            END as has_data
        """

        result = await conn.fetchrow(query, traj_id)
        return {"has_deviation_data": result['has_data']}

    except Exception as e:
        logger.error(f"Error checking deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/has_orientation_data/{traj_id}")
@cache(expire=2400)
async def check_orientation_data(traj_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            CASE 
                WHEN EXISTS (SELECT 1 FROM evaluation.gd_evaluation WHERE traj_id = $1) OR
                     EXISTS (SELECT 1 FROM evaluation.qdtw_evaluation WHERE traj_id = $1)
                THEN true
                ELSE false
            END as has_data
        """

        result = await conn.fetchrow(query, traj_id)
        return {"has_orientation_data": result['has_data']}

    except Exception as e:
        logger.error(f"Error checking orientation data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_evaluation_traj_ids(
        query: str = Query(None, description="Suchbegriff für Freitext-Suche (Filename, ID, Datum)"),
        points_events: int = Query(None, description="Anzahl der Punktereignisse"),
        weight: float = Query(None, description="Gewicht"),
        velocity: int = Query(None, description="Geschwindigkeit"),
        page: int = Query(1, ge=1, description="Seitennummer"),
        page_size: int = Query(20, ge=1, le=100, description="Einträge pro Seite"),
        conn=Depends(get_db)
):
    try:
        # Der entscheidende Unterschied: Wir verbinden die traj_info mit evaluation_ed_info
        # Wir selektieren nur die Bahnen, für die auch Auswertungsdaten existieren
        base_query = """
        SELECT DISTINCT bi.* 
        FROM motion.traj_info bi
        JOIN evaluation.ed_info ie ON bi.traj_id = ie.traj_id
        WHERE 1=1
        """

        params = []
        param_index = 1

        # Filter hinzufügen basierend auf Parametern
        if query:
            # Da traj_id ein varchar ist, behandeln wir alle Suchen als Text
            search_conditions = []

            # traj_id (teilweise Übereinstimmung)
            search_conditions.append(f"bi.traj_id ILIKE ${param_index}")
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

        if points_events is not None:
            base_query += f" AND bi.number_setpoints = ${param_index}"
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
        traj_info_list = [dict(row) for row in rows]

        # Keine Ergebnisse und Seite > 1
        if not traj_info_list and page > 1:
            raise HTTPException(status_code=404, detail="Page number exceeds available pages")

        total_pages = (total_count + page_size - 1) // page_size

        return {
            "traj_info": traj_info_list,
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
        logger.error(f"Error searching evaluation traj info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    
    
@router.get("/gd_evaluation/{traj_id}")
async def get_gd_evaluation_by_id(traj_id: str, conn=Depends(get_db)):
    try:
        query = """
                SELECT 
                    traj_id,
                    seg_id,
                    gd_deviation,
                    gd_cmd_x,
                    gd_cmd_y,
                    gd_cmd_z,
                    gd_cmd_w,
                    gd_act_x,
                    gd_act_y,
                    gd_act_z,
                    gd_act_w,
                    points_order
                FROM evaluation.gd_evaluation 
                WHERE traj_id = $1
                ORDER BY points_order ASC
                """

        rows = await conn.fetch(query, traj_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No GD orientation data found for traj_id {traj_id}")

        return {
            "gd_evaluation": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching GD orientation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/qdtw_evaluation/{traj_id}")
@cache(expire=2400)
async def get_qdtw_evaluation_by_id(traj_id: str, conn=Depends(get_db)):
    try:
        query = """
                SELECT 
                    traj_id,
                    seg_id,
                    qdtw_deviation,
                    qdtw_cmd_x,
                    qdtw_cmd_y,
                    qdtw_cmd_z,
                    qdtw_cmd_w,
                    qdtw_act_x,
                    qdtw_act_y,
                    qdtw_act_z,
                    qdtw_act_w,
                    points_order
                FROM evaluation.qdtw_evaluation 
                WHERE traj_id = $1
                ORDER BY points_order ASC
                """

        rows = await conn.fetch(query, traj_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No QDTW deviation data found for traj_id {traj_id}")

        return {
            "qdtw_evaluation": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching qdtw deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")