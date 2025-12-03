from fastapi import APIRouter, Depends
from middleware.auth import require_role
from config.database import get_db
import asyncpg
import controllers.adminController as adminController

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard", dependencies=[Depends(require_role(["admin"]))])
async def get_dashboard(db: asyncpg.Connection = Depends(get_db)):
    return await adminController.get_dashboard_data(db)

@router.get("/analytics", dependencies=[Depends(require_role(["admin"]))])
async def get_analytics(cycle_id: int, db: asyncpg.Connection = Depends(get_db)):
    return await adminController.get_analytics(cycle_id, db)

@router.get("/stats", dependencies=[Depends(require_role(["admin"]))])
async def get_stats(db: asyncpg.Connection = Depends(get_db)):
    return await adminController.get_general_stats(db)
