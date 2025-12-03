from fastapi import APIRouter, Depends, HTTPException, status
from models.course import CourseCreate, CourseUpdate, CourseOfferingCreate, CourseOfferingUpdate
from middleware.auth import require_role
from config.database import get_db
import asyncpg

router = APIRouter(prefix="/courses", tags=["courses"])

@router.post("", dependencies=[Depends(require_role(["admin"]))], status_code=status.HTTP_201_CREATED)
async def create_course(course: CourseCreate, db: asyncpg.Connection = Depends(get_db)):
    result = await db.fetchrow(
        "INSERT INTO courses (name, description, base_price) VALUES ($1, $2, $3) RETURNING id",
        course.name, course.description, course.base_price
    )
    return {"id": result['id'], "message": "Curso creado correctamente"}

@router.get("")
async def get_all_courses(db: asyncpg.Connection = Depends(get_db)):
    courses = await db.fetch("SELECT id, name, description, base_price FROM courses")
    return [dict(c) for c in courses]

@router.get("/{course_id}")
async def get_course(course_id: int, db: asyncpg.Connection = Depends(get_db)):
    course = await db.fetchrow(
        "SELECT id, name, description, base_price FROM courses WHERE id = $1",
        course_id
    )
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return dict(course)

@router.put("/{course_id}", dependencies=[Depends(require_role(["admin"]))])
async def update_course(course_id: int, course: CourseUpdate, db: asyncpg.Connection = Depends(get_db)):
    fields = []
    values = []
    idx = 1
    
    for field, value in course.dict(exclude_unset=True).items():
        fields.append(f"{field} = ${idx}")
        values.append(value)
        idx += 1
    
    if not fields:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    values.append(course_id)
    query = f"UPDATE courses SET {', '.join(fields)} WHERE id = ${idx}"
    
    await db.execute(query, *values)
    return {"message": "Curso actualizado correctamente"}

@router.delete("/{course_id}", dependencies=[Depends(require_role(["admin"]))])
async def delete_course(course_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute("DELETE FROM courses WHERE id = $1", course_id)
    return {"message": "Curso eliminado correctamente"}

# Course Offerings
@router.post("/offerings", dependencies=[Depends(require_role(["admin"]))], status_code=status.HTTP_201_CREATED)
async def create_course_offering(offering: CourseOfferingCreate, db: asyncpg.Connection = Depends(get_db)):
    result = await db.fetchrow(
        """INSERT INTO course_offerings (course_id, cycle_id, group_label, teacher_id, price_override, capacity)
           VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
        offering.course_id, offering.cycle_id, offering.group_label,
        offering.teacher_id, offering.price_override, offering.capacity
    )
    return {"id": result['id'], "message": "Oferta de curso creada correctamente"}

@router.get("/offerings")
async def get_all_course_offerings(cycle_id: int = None, db: asyncpg.Connection = Depends(get_db)):
    if cycle_id:
        offerings = await db.fetch(
            """SELECT co.*, c.name as course_name, c.base_price, cyc.name as cycle_name,
                      t.first_name as teacher_first_name, t.last_name as teacher_last_name
               FROM course_offerings co
               JOIN courses c ON co.course_id = c.id
               LEFT JOIN cycles cyc ON co.cycle_id = cyc.id
               LEFT JOIN teachers t ON co.teacher_id = t.id
               WHERE co.cycle_id = $1""",
            cycle_id
        )
    else:
        offerings = await db.fetch(
            """SELECT co.*, c.name as course_name, c.base_price, cyc.name as cycle_name,
                      t.first_name as teacher_first_name, t.last_name as teacher_last_name
               FROM course_offerings co
               JOIN courses c ON co.course_id = c.id
               LEFT JOIN cycles cyc ON co.cycle_id = cyc.id
               LEFT JOIN teachers t ON co.teacher_id = t.id"""
        )
    return [dict(o) for o in offerings]

@router.get("/offerings/{offering_id}")
async def get_course_offering(offering_id: int, db: asyncpg.Connection = Depends(get_db)):
    offering = await db.fetchrow(
        """SELECT co.*, c.name as course_name, c.base_price, cyc.name as cycle_name,
                  t.first_name as teacher_first_name, t.last_name as teacher_last_name
           FROM course_offerings co
           JOIN courses c ON co.course_id = c.id
           LEFT JOIN cycles cyc ON co.cycle_id = cyc.id
           LEFT JOIN teachers t ON co.teacher_id = t.id
           WHERE co.id = $1""",
        offering_id
    )
    if not offering:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    return dict(offering)

@router.put("/offerings/{offering_id}", dependencies=[Depends(require_role(["admin"]))])
async def update_course_offering(offering_id: int, offering: CourseOfferingUpdate, db: asyncpg.Connection = Depends(get_db)):
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
    query = f"UPDATE course_offerings SET {', '.join(fields)} WHERE id = ${idx}"
    
    await db.execute(query, *values)
    return {"message": "Oferta actualizada correctamente"}

@router.delete("/offerings/{offering_id}", dependencies=[Depends(require_role(["admin"]))])
async def delete_course_offering(offering_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute("DELETE FROM course_offerings WHERE id = $1", offering_id)
    return {"message": "Oferta eliminada correctamente"}
