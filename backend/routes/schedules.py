from fastapi import APIRouter, Depends, HTTPException, status
from models.course import ScheduleCreate, ScheduleUpdate
from middleware.auth import require_role
from config.database import get_db
import asyncpg

router = APIRouter(prefix="/schedules", tags=["schedules"])

@router.post("", dependencies=[Depends(require_role(["admin"]))], status_code=status.HTTP_201_CREATED)
async def create_schedule(schedule: ScheduleCreate, db: asyncpg.Connection = Depends(get_db)):
    if not schedule.course_offering_id:
        raise HTTPException(status_code=400, detail="course_offering_id es requerido")
    
    try:
        st = schedule.start_time
        et = schedule.end_time
        
        # Defensive conversion: if it's a time object, format it. If it's a string, use it.
        if hasattr(st, 'strftime'):
            st = st.strftime("%H:%M:%S")
        else:
            st = str(st)
            
        if hasattr(et, 'strftime'):
            et = et.strftime("%H:%M:%S")
        else:
            et = str(et)

        # Parse strings to time objects manually to satisfy asyncpg
        from datetime import time as py_time
        
        try:
            h, m, s = map(int, st.split(':'))
            t_start = py_time(h, m, s)
            
            h, m, s = map(int, et.split(':'))
            t_end = py_time(h, m, s)
        except Exception as e:
            print(f"Error parsing time: {e}")
            raise HTTPException(status_code=400, detail="Invalid time format")

        print(f"DEBUG: t_start: {t_start} ({type(t_start)}), t_end: {t_end} ({type(t_end)})")

        result = await db.fetchrow(
            """INSERT INTO schedules (course_offering_id, day_of_week, start_time, end_time, classroom)
               VALUES ($1, $2::day_of_week, $3, $4, $5) RETURNING id""",
            schedule.course_offering_id, schedule.day_of_week,
            t_start, t_end,
            schedule.classroom
        )
        return {"id": result['id'], "message": "Horario creado exitosamente"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error creating schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/course-offering/{course_offering_id}")
async def get_schedules_by_course_offering(course_offering_id: int, db: asyncpg.Connection = Depends(get_db)):
    schedules = await db.fetch(
        """SELECT s.*, co.id as course_offering_id, co.course_id, co.group_label,
                  c.name as course_name, cyc.name as cycle_name
           FROM schedules s
           LEFT JOIN course_offerings co ON s.course_offering_id = co.id
           LEFT JOIN courses c ON co.course_id = c.id
           LEFT JOIN cycles cyc ON co.cycle_id = cyc.id
           WHERE s.course_offering_id = $1
           ORDER BY s.day_of_week, s.start_time""",
        course_offering_id
    )
    return [dict(s) for s in schedules]

@router.get("/package-offering/{package_offering_id}")
async def get_schedules_by_package_offering(package_offering_id: int, db: asyncpg.Connection = Depends(get_db)):
    # Try exact mapping first
    mapped = await db.fetch(
        """SELECT s.*, co.id AS course_offering_id, co.course_id, co.group_label,
                  c.name AS course_name, cyc.name AS cycle_name,
                  t.first_name AS teacher_first_name, t.last_name AS teacher_last_name
           FROM package_offering_courses poc
           JOIN course_offerings co ON co.id = poc.course_offering_id
           JOIN courses c ON c.id = co.course_id
           LEFT JOIN teachers t ON t.id = co.teacher_id
           JOIN cycles cyc ON cyc.id = co.cycle_id
           LEFT JOIN schedules s ON s.course_offering_id = co.id
           WHERE poc.package_offering_id = $1
           ORDER BY c.id, co.id, s.day_of_week, s.start_time""",
        package_offering_id
    )
    
    if mapped:
        return [dict(s) for s in mapped]
    
    # Fallback: by courses/cycle
    rows = await db.fetch(
        """SELECT s.*, co.id as course_offering_id, co.course_id, co.group_label,
                  c.name as course_name, cyc.name as cycle_name,
                  t.first_name AS teacher_first_name, t.last_name AS teacher_last_name
           FROM package_offerings po
           JOIN packages p ON po.package_id = p.id
           JOIN package_courses pc ON pc.package_id = p.id
           JOIN course_offerings co ON co.course_id = pc.course_id AND co.cycle_id = po.cycle_id
           JOIN courses c ON c.id = co.course_id
           LEFT JOIN teachers t ON t.id = co.teacher_id
           JOIN cycles cyc ON cyc.id = co.cycle_id
           LEFT JOIN schedules s ON s.course_offering_id = co.id
           WHERE po.id = $1
           ORDER BY c.id, co.id, s.day_of_week, s.start_time""",
        package_offering_id
    )
    return [dict(s) for s in rows]

@router.put("/{schedule_id}", dependencies=[Depends(require_role(["admin"]))])
async def update_schedule(schedule_id: int, schedule: ScheduleUpdate, db: asyncpg.Connection = Depends(get_db)):
    fields = []
    values = []
    idx = 1
    
    for field, value in schedule.dict(exclude_unset=True).items():
        fields.append(f"{field} = ${idx}")
        values.append(value)
        idx += 1
    
    if not fields:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    values.append(schedule_id)
    query = f"UPDATE schedules SET {', '.join(fields)} WHERE id = ${idx}"
    
    await db.execute(query, *values)
    return {"message": "Horario actualizado correctamente"}

@router.delete("/{schedule_id}", dependencies=[Depends(require_role(["admin"]))])
async def delete_schedule(schedule_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute("DELETE FROM schedules WHERE id = $1", schedule_id)
    return {"message": "Horario eliminado correctamente"}

@router.get("")
async def get_all_schedules(db: asyncpg.Connection = Depends(get_db)):
    schedules = await db.fetch(
        """SELECT s.*, co.id as course_offering_id, co.course_id, co.group_label,
                  c.name as course_name, cyc.name as cycle_name
           FROM schedules s
           LEFT JOIN course_offerings co ON s.course_offering_id = co.id
           LEFT JOIN courses c ON co.course_id = c.id
           LEFT JOIN cycles cyc ON co.cycle_id = cyc.id
           ORDER BY co.course_id, s.day_of_week, s.start_time"""
    )
    return [dict(s) for s in schedules]
