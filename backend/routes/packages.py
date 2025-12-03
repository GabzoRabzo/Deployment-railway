from fastapi import APIRouter, Depends, HTTPException, status
from models.enrollment import PackageCreate, PackageUpdate, PackageOfferingCreate
from middleware.auth import require_role
from config.database import get_db
import asyncpg
import controllers.packageController as packageController

router = APIRouter(prefix="/packages", tags=["packages"])

@router.get("")
async def get_packages(db: asyncpg.Connection = Depends(get_db)):
    return await packageController.get_all_packages(db)

@router.post("", dependencies=[Depends(require_role(["admin"]))], status_code=status.HTTP_201_CREATED)
async def create_package(package: PackageCreate, db: asyncpg.Connection = Depends(get_db)):
    return await packageController.create_package(package, db)

@router.put("/{package_id}", dependencies=[Depends(require_role(["admin"]))])
async def update_package(package_id: int, package: PackageUpdate, db: asyncpg.Connection = Depends(get_db)):
    return await packageController.update_package(package_id, package, db)

@router.delete("/{package_id}", dependencies=[Depends(require_role(["admin"]))])
async def delete_package(package_id: int, db: asyncpg.Connection = Depends(get_db)):
    return await packageController.delete_package(package_id, db)

@router.get("/offerings/{cycle_id}")
async def get_offerings(cycle_id: int, db: asyncpg.Connection = Depends(get_db)):
    return await packageController.get_package_offerings(cycle_id, db)

@router.post("/offerings", dependencies=[Depends(require_role(["admin"]))], status_code=status.HTTP_201_CREATED)
async def create_offering(offering: PackageOfferingCreate, db: asyncpg.Connection = Depends(get_db)):
    return await packageController.create_package_offering(offering, db)
