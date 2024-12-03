import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from ...database import get_db
import logging
from fastapi_cache.decorator import cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

########################## AUSWERTUNGSDATEN #########################################

@router.get("/auswertung_info")
async def get_auswertung_info(conn=Depends(get_db)):
    try:
        # 1. Finde alle relevanten Tabellen
        table_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'auswertung' 
        AND table_name LIKE '%_info'
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

        # 3. Hole Bahn-Info Daten
        bahn_info_query = f"""
        WITH unique_bahn_ids AS ({bahn_ids_query})
        SELECT bi.* 
        FROM bewegungsdaten.bahn_info bi
        INNER JOIN unique_bahn_ids ubi ON bi.bahn_id = ubi.bahn_id
        ORDER BY bi.recording_date DESC, bi.bahn_id
        """

        bahn_info_rows = await conn.fetch(bahn_info_query)

        if not bahn_info_rows:
            logger.warning("No bahn info found")
            raise HTTPException(status_code=404, detail="No bahn info found")

        # 4. Hole Daten aus allen auswertung._info Tabellen
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
            WHERE bahn_id IN (SELECT bahn_id FROM ({bahn_ids_query}) AS unique_ids)
            ORDER BY bahn_id
            """

            rows = await conn.fetch(query)
            if rows:
                result["auswertung_info"][table_name] = [dict(row) for row in rows]

        return result

    except Exception as e:
        logger.error(f"Error fetching info tables data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/euclidean_deviation/{bahn_id}")
@cache(expire=2400)
async def get_euclidean_deviation_by_id(bahn_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            bahn_id,
            segment_id,
            euclidean_distances,
            points_order,
            evaluation
        FROM auswertung.euclidean_deviation 
        WHERE bahn_id = $1
        ORDER BY points_order ASC
        """

        rows = await conn.fetch(query, bahn_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No euclidean deviation data found for bahn_id {bahn_id}")

        return {
            "euclidean_deviation": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching euclidean deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/dfd_deviation/{bahn_id}")
@cache(expire=2400)
async def get_dfd_deviation_by_id(bahn_id: str, conn=Depends(get_db)):
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
            points_order,
            evaluation
        FROM auswertung.dfd_deviation 
        WHERE bahn_id = $1
        ORDER BY points_order ASC
        """

        rows = await conn.fetch(query, bahn_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No DFD deviation data found for bahn_id {bahn_id}")

        return {
            "dfd_deviation": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching DFD deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/sidtw_deviation/{bahn_id}")
@cache(expire=2400)
async def get_sidtw_deviation_by_id(bahn_id: str, conn=Depends(get_db)):
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
            points_order,
            evaluation
        FROM auswertung.sidtw_deviation 
        WHERE bahn_id = $1
        ORDER BY points_order ASC
        """

        rows = await conn.fetch(query, bahn_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No SIDTW deviation data found for bahn_id {bahn_id}")

        return {
            "sidtw_deviation": [dict(row) for row in rows]
        }

    except Exception as e:
        logger.error(f"Error fetching SIDTW deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/has_deviation_data/{bahn_id}")
@cache(expire=2400)
async def check_deviation_data(bahn_id: str, conn=Depends(get_db)):
    try:
        query = """
        SELECT 
            CASE 
                WHEN EXISTS (SELECT 1 FROM auswertung.euclidean_deviation WHERE bahn_id = $1) AND
                     EXISTS (SELECT 1 FROM auswertung.dfd_deviation WHERE bahn_id = $1) AND
                     EXISTS (SELECT 1 FROM auswertung.sidtw_deviation WHERE bahn_id = $1)
                THEN true
                ELSE false
            END as has_data
        """

        result = await conn.fetchrow(query, bahn_id)
        return {"has_deviation_data": result['has_data']}

    except Exception as e:
        logger.error(f"Error checking deviation data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

