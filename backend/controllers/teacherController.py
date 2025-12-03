import asyncpg
from models.teacher import TeacherCreate, TeacherUpdate, AttendanceCreate

async def get_all_teachers(db: asyncpg.Connection):
    teachers = await db.fetch("SELECT * FROM teachers ORDER BY last_name, first_name")
    return [dict(t) for t in teachers]

async def get_teacher_by_id(teacher_id: int, db: asyncpg.Connection):
    teacher = await db.fetchrow("SELECT * FROM teachers WHERE id = $1", teacher_id)
    if not teacher:
        return None
    return dict(teacher)

async def create_teacher(data: TeacherCreate, db: asyncpg.Connection):
    from utils.security import get_password_hash
    
    # Create user for teacher
    user_result = await db.fetchrow(
        """INSERT INTO users (username, password_hash, role, related_id)
           VALUES ($1, $2, 'teacher', NULL) RETURNING id""",
        data.dni, get_password_hash(data.dni)
    )
    user_id = user_result['id']
    
    # Create teacher
    result = await db.fetchrow(
        """INSERT INTO teachers (first_name, last_name, dni, phone, email, specialization)
           VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
        data.first_name, data.last_name, data.dni, data.phone, data.email, data.specialization
    )
    teacher_id = result['id']
    
    # Update user with teacher_id
    await db.execute("UPDATE users SET related_id = $1 WHERE id = $2", teacher_id, user_id)
    
    return {"id": teacher_id, "message": "Docente creado exitosamente"}

async def update_teacher(teacher_id: int, data: TeacherUpdate, db: asyncpg.Connection):
    fields = []
    values = []
    idx = 1
    
    for field, value in data.dict(exclude_unset=True).items():
        fields.append(f"{field} = ${idx}")
        values.append(value)
        idx += 1
    
    if not fields:
        return {"message": "No hay campos para actualizar"}
    
    values.append(teacher_id)
    query = f"UPDATE teachers SET {', '.join(fields)} WHERE id = ${idx}"
    await db.execute(query, *values)
    return {"message": "Docente actualizado correctamente"}

async def reset_teacher_password(teacher_id: int, db: asyncpg.Connection):
    from utils.security import get_password_hash
    
    teacher = await db.fetchrow("SELECT dni FROM teachers WHERE id = $1", teacher_id)
    if not teacher:
        return None
    
    await db.execute(
        "UPDATE users SET password_hash = $1 WHERE username = $2",
        get_password_hash(teacher['dni']), teacher['dni']
    )
    return {"message": "Contraseña reseteada al DNI del docente"}

async def get_teacher_students(teacher_id: int, db: asyncpg.Connection):
    students = await db.fetch(
        """SELECT DISTINCT s.id, s.first_name, s.last_name, s.dni, s.phone
           FROM students s
           JOIN enrollments e ON s.id = e.student_id
           JOIN course_offerings co ON e.course_offering_id = co.id
           WHERE co.teacher_id = $1 AND e.status = 'aceptado'
           ORDER BY s.last_name, s.first_name""",
        teacher_id
    )
    return [dict(s) for s in students]

async def mark_attendance(teacher_id: int, data: AttendanceCreate, db: asyncpg.Connection):
    from datetime import date
    
    # Verify teacher owns this schedule
    schedule = await db.fetchrow(
        """SELECT co.teacher_id FROM schedules s
           JOIN course_offerings co ON s.course_offering_id = co.id
           WHERE s.id = $1""",
        data.schedule_id
    )
    
    if not schedule or schedule['teacher_id'] != teacher_id:
        return None
    
    # Check if attendance already exists
    existing = await db.fetchrow(
        """SELECT id FROM attendance 
           WHERE student_id = $1 AND schedule_id = $2 AND date = $3""",
        data.student_id, data.schedule_id, date.today()
    )
    
    if existing:
        await db.execute(
            "UPDATE attendance SET status = $1 WHERE id = $2",
            data.status, existing['id']
        )
    else:
        await db.execute(
            """INSERT INTO attendance (student_id, schedule_id, date, status)
               VALUES ($1, $2, $3, $4)""",
            data.student_id, data.schedule_id, date.today(), data.status
        )
    
    return {"message": "Asistencia registrada correctamente"}
