from fastapi import APIRouter, Depends, HTTPException, status
from models.enrollment import PackageCreate, PackageUpdate, PackageOfferingCreate, PackageOfferingUpdate, PackageOfferingCourseAdd
from middleware.auth import require_role
from config.database import get_db
import asyncpg

router = APIRouter(prefix="/packages", tags=["packages"])

@router.post("", dependencies=[Depends(require_role(["admin"]))], status_code=status.HTTP_201_CREATED)
async def create_package(package: PackageCreate, db: asyncpg.Connection = Depends(get_db)):
    result = await db.fetchrow(
        "INSERT INTO packages (name, description, base_price) VALUES ($1, $2, $3) RETURNING id",
        package.name, package.description, package.base_price or 0
    )
    return {"id": result['id'], "message": "Paquete creado correctamente"}

@router.get("")
async def get_all_packages(db: asyncpg.Connection = Depends(get_db)):
    packages = await db.fetch(
        """SELECT p.*, STRING_AGG(c.name, ',') as courses
           FROM packages p
           LEFT JOIN package_courses pc ON p.id = pc.package_id
           LEFT JOIN courses c ON pc.course_id = c.id
           GROUP BY p.id"""
    )
    return [dict(p) for p in packages]

@router.get("/{package_id}")
async def get_package(package_id: int, db: asyncpg.Connection = Depends(get_db)):
    package = await db.fetchrow(
        """SELECT p.*, STRING_AGG(c.name, ',') as courses
           FROM packages p
           LEFT JOIN package_courses pc ON p.id = pc.package_id
           LEFT JOIN courses c ON pc.course_id = c.id
           WHERE p.id = $1
           GROUP BY p.id""",
        package_id
    )
    if not package:
        raise HTTPException(status_code=404, detail="Paquete no encontrado")
    return dict(package)

@router.put("/{package_id}", dependencies=[Depends(require_role(["admin"]))])
async def update_package(package_id: int, package: PackageUpdate, db: asyncpg.Connection = Depends(get_db)):
    fields = []
    values = []
    idx = 1
    
    for field, value in package.dict(exclude_unset=True).items():
        fields.append(f"{field} = ${idx}")
        values.append(value)
        idx += 1
    
    if not fields:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    values.append(package_id)
    query = f"UPDATE packages SET {', '.join(fields)} WHERE id = ${idx}"
    
    await db.execute(query, *values)
    return {"message": "Paquete actualizado correctamente"}

@router.delete("/{package_id}", dependencies=[Depends(require_role(["admin"]))])
async def delete_package(package_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute("DELETE FROM packages WHERE id = $1", package_id)
    return {"message": "Paquete eliminado correctamente"}

@router.post("/{package_id}/courses", dependencies=[Depends(require_role(["admin"]))])
async def add_course_to_package(package_id: int, course_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute(
        "INSERT INTO package_courses (package_id, course_id) VALUES ($1, $2)",
        package_id, course_id
    )
    return {"message": "Curso añadido al paquete correctamente"}

@router.delete("/{package_id}/courses/{course_id}", dependencies=[Depends(require_role(["admin"]))])
async def remove_course_from_package(package_id: int, course_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute(
        "DELETE FROM package_courses WHERE package_id = $1 AND course_id = $2",
        package_id, course_id
    )
    return {"message": "Curso removido del paquete correctamente"}

# Package Offerings
@router.post("/offerings", dependencies=[Depends(require_role(["admin"]))], status_code=status.HTTP_201_CREATED)
async def create_package_offering(offering: PackageOfferingCreate, db: asyncpg.Connection = Depends(get_db)):
    result = await db.fetchrow(
        """INSERT INTO package_offerings (package_id, cycle_id, group_label, price_override)
           VALUES ($1, $2, $3, $4) RETURNING id""",
        offering.package_id, offering.cycle_id, offering.group_label, offering.price_override
    )
    return {"id": result['id'], "message": "Package offering creado"}

@router.get("/offerings")
async def get_package_offerings(db: asyncpg.Connection = Depends(get_db)):
    offerings = await db.fetch(
        """SELECT po.*, pkg.name AS package_name, pkg.base_price AS base_price, cyc.name AS cycle_name
           FROM package_offerings po
           JOIN packages pkg ON po.package_id = pkg.id
           LEFT JOIN cycles cyc ON po.cycle_id = cyc.id
           ORDER BY po.id DESC"""
    )
    return [dict(o) for o in offerings]

@router.put("/offerings/{offering_id}", dependencies=[Depends(require_role(["admin"]))])
async def update_package_offering(offering_id: int, offering: PackageOfferingUpdate, db: asyncpg.Connection = Depends(get_db)):
    fields = []
    values = []
    idx = 1
    
    for field, value in offering.dict(exclude_unset=True).items():
        fields.append(f"{field} = ${idx}")
        values.append(value)
        idx += 1
    
    if not fields:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    values.append(offering_id)
    query = f"UPDATE package_offerings SET {', '.join(fields)} WHERE id = ${idx}"
    
    await db.execute(query, *values)
    return {"message": "Package offering actualizado"}

@router.delete("/offerings/{offering_id}", dependencies=[Depends(require_role(["admin"]))])
async def delete_package_offering(offering_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute("DELETE FROM package_offerings WHERE id = $1", offering_id)
    return {"message": "Package offering eliminado"}

@router.get("/offerings/{offering_id}/courses")
async def get_offering_courses(offering_id: int, db: asyncpg.Connection = Depends(get_db)):
    courses = await db.fetch(
        "SELECT poc.course_offering_id FROM package_offering_courses poc WHERE poc.package_offering_id = $1",
        offering_id
    )
    return [dict(c) for c in courses]

@router.post("/offerings/{offering_id}/courses", dependencies=[Depends(require_role(["admin"]))])
async def add_offering_course(offering_id: int, course: PackageOfferingCourseAdd, db: asyncpg.Connection = Depends(get_db)):
    try:
        await db.execute(
            "INSERT INTO package_offering_courses (package_offering_id, course_offering_id) VALUES ($1, $2)",
            offering_id, course.course_offering_id
        )
        return {"message": "Curso ofrecido vinculado al paquete"}
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Este curso ofrecido ya está vinculado")

@router.delete("/offerings/{offering_id}/courses/{course_offering_id}", dependencies=[Depends(require_role(["admin"]))])
async def remove_offering_course(offering_id: int, course_offering_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute(
        "DELETE FROM package_offering_courses WHERE package_offering_id = $1 AND course_offering_id = $2",
        offering_id, course_offering_id
    )
    return {"message": "Curso ofrecido desvinculado del paquete"}
