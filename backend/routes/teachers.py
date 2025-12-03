from fastapi import APIRouter, Depends, HTTPException, status
from models.teacher import TeacherCreate, TeacherUpdate, AttendanceCreate
from middleware.auth import get_current_user, require_role
from config.database import get_db
from utils.security import get_password_hash
import asyncpg
from datetime import date

router = APIRouter(prefix="/teachers", tags=["teachers"])

@router.post("", dependencies=[Depends(require_role(["admin"]))], status_code=status.HTTP_201_CREATED)
async def create_teacher(teacher: TeacherCreate, db: asyncpg.Connection = Depends(get_db)):
    try:
        result = await db.fetchrow(
            """INSERT INTO teachers (first_name, last_name, dni, phone, email, specialization)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            teacher.first_name, teacher.last_name, teacher.dni, teacher.phone,
            teacher.email, teacher.specialization
        )
        
        teacher_id = result['id']
        
        # Create user for teacher
        try:
            password_hash = get_password_hash(teacher.dni)
            await db.execute(
                "INSERT INTO users (username, password_hash, role, related_id) VALUES ($1, $2, $3, $4)",
                teacher.dni, password_hash, "teacher", teacher_id
            )
        except asyncpg.UniqueViolationError:
            pass  # User already exists
        
        return {"id": teacher_id, "message": "Profesor creado correctamente"}
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=400, detail="El profesor ya está registrado")

@router.get("", dependencies=[Depends(require_role(["admin"]))])
async def get_all_teachers(db: asyncpg.Connection = Depends(get_db)):
    teachers = await db.fetch(
        "SELECT id, first_name, last_name, dni, phone, email, specialization FROM teachers"
    )
    return [dict(t) | {"name": f"{t['first_name']} {t['last_name']}"} for t in teachers]

@router.get("/{teacher_id}")
async def get_teacher(teacher_id: int, db: asyncpg.Connection = Depends(get_db)):
    teacher = await db.fetchrow(
        "SELECT id, first_name, last_name, dni, phone, email, specialization FROM teachers WHERE id = $1",
        teacher_id
    )
    if not teacher:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    return dict(teacher) | {"name": f"{teacher['first_name']} {teacher['last_name']}"}

@router.put("/{teacher_id}", dependencies=[Depends(require_role(["admin"]))])
async def update_teacher(teacher_id: int, teacher: TeacherUpdate, db: asyncpg.Connection = Depends(get_db)):
    fields = []
    values = []
    idx = 1
    
    for field, value in teacher.dict(exclude_unset=True).items():
        fields.append(f"{field} = ${idx}")
        values.append(value)
        idx += 1
    
    if not fields:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    values.append(teacher_id)
    query = f"UPDATE teachers SET {', '.join(fields)} WHERE id = ${idx}"
    
    await db.execute(query, *values)
    return {"message": "Profesor actualizado correctamente"}

@router.delete("/{teacher_id}", dependencies=[Depends(require_role(["admin"]))])
async def delete_teacher(teacher_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute("DELETE FROM teachers WHERE id = $1", teacher_id)
    return {"message": "Profesor eliminado correctamente"}

@router.post("/{teacher_id}/reset-password", dependencies=[Depends(require_role(["admin"]))])
async def reset_password(teacher_id: int, db: asyncpg.Connection = Depends(get_db)):
    teacher = await db.fetchrow("SELECT dni FROM teachers WHERE id = $1", teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    
    dni = teacher['dni']
    password_hash = get_password_hash(dni)
    
    result = await db.execute(
        "UPDATE users SET password_hash = $1 WHERE role = $2 AND related_id = $3",
        password_hash, "teacher", teacher_id
    )
    
    if result == "UPDATE 0":
        # Create user if doesn't exist
        try:
            await db.execute(
                "INSERT INTO users (username, password_hash, role, related_id) VALUES ($1, $2, $3, $4)",
                dni, password_hash, "teacher", teacher_id
            )
        except:
            pass
    
    return {"message": "Contraseña restablecida al DNI"}

@router.get("/{teacher_id}/students", dependencies=[Depends(require_role(["admin", "teacher"]))])
async def get_teacher_students(teacher_id: int, db: asyncpg.Connection = Depends(get_db)):
    students = await db.fetch(
        """SELECT DISTINCT s.*
           FROM students s
           JOIN enrollments e ON s.id = e.student_id
           JOIN course_offerings co ON e.course_offering_id = co.id
           WHERE co.teacher_id = $1 AND e.enrollment_type = 'course' AND e.status = 'aceptado'""",
        teacher_id
    )
    return [dict(s) for s in students]

@router.post("/{teacher_id}/attendance", dependencies=[Depends(require_role(["admin", "teacher"]))])
async def mark_attendance(
    teacher_id: int,
    attendance: AttendanceCreate,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    # Verify teacher permission
    if current_user["role"] == "teacher" and current_user.get("related_id") != teacher_id:
        raise HTTPException(status_code=403, detail="No autorizado para marcar asistencia como este profesor")
    
    # Verify teacher is assigned to course
    course_check = await db.fetchrow(
        """SELECT co.* FROM course_offerings co
           JOIN schedules s ON co.id = s.course_offering_id
           WHERE s.id = $1 AND co.teacher_id = $2""",
        attendance.schedule_id, teacher_id
    )
    
    if not course_check:
        raise HTTPException(status_code=403, detail="No tienes permiso para marcar asistencia en este curso")
    
    # Verify student enrollment
    enrollment_check = await db.fetchrow(
        """SELECT e.id FROM enrollments e
           JOIN schedules s ON s.course_offering_id = e.course_offering_id
           WHERE s.id = $1 AND e.student_id = $2 AND e.enrollment_type = 'course' AND e.status = 'aceptado'
           LIMIT 1""",
        attendance.schedule_id, attendance.student_id
    )
    
    if not enrollment_check:
        raise HTTPException(status_code=400, detail="El estudiante no tiene una matrícula aceptada en este curso")
    
    today = date.today()
    
    # Check if attendance already exists
    existing = await db.fetchrow(
        "SELECT id FROM attendance WHERE schedule_id = $1 AND student_id = $2 AND date = $3",
        attendance.schedule_id, attendance.student_id, today
    )
    
    if existing:
        await db.execute(
            "UPDATE attendance SET status = $1 WHERE id = $2",
            attendance.status, existing['id']
        )
    else:
        await db.execute(
            "INSERT INTO attendance (schedule_id, student_id, date, status) VALUES ($1, $2, $3, $4)",
            attendance.schedule_id, attendance.student_id, today, attendance.status
        )
    
    # Check absences and notify if >= 3
    if attendance.status == "ausente":
        absences = await db.fetchrow(
            "SELECT COUNT(*) as count FROM attendance WHERE student_id = $1 AND status = 'ausente' AND schedule_id = $2",
            attendance.student_id, attendance.schedule_id
        )
        
        if absences['count'] >= 3:
            student = await db.fetchrow("SELECT * FROM students WHERE id = $1", attendance.student_id)
            if student and student['parent_phone']:
                # TODO: Send notification
                pass
    
    return {"message": "Asistencia marcada correctamente"}
