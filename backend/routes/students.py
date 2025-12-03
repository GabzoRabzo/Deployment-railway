from fastapi import APIRouter, Depends, HTTPException, status
from models.student import StudentCreate, StudentUpdate, StudentResponse
from models.user import TokenResponse
from utils.security import get_password_hash
from middleware.auth import get_current_user, require_role
from config.database import get_db
import asyncpg

router = APIRouter(prefix="/students", tags=["students"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_student(student: StudentCreate, db: asyncpg.Connection = Depends(get_db)):
    try:
        password_hash = get_password_hash(student.password)
        
        result = await db.fetchrow(
            """INSERT INTO students (dni, first_name, last_name, phone, parent_name, parent_phone, password_hash)
               VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
            student.dni, student.first_name, student.last_name, student.phone,
            student.parent_name, student.parent_phone, password_hash
        )
        
        student_id = result['id']
        from utils.security import create_access_token
        token = create_access_token({"id": student_id, "role": "student"})
        
        return {
            "token": token,
            "user": {
                "id": student_id,
                "username": student.dni,
                "role": "student",
                "related_id": None
            }
        }
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estudiante ya está registrado"
        )

@router.get("", dependencies=[Depends(require_role(["admin"]))])
async def get_all_students(db: asyncpg.Connection = Depends(get_db)):
    students = await db.fetch("SELECT id, dni, first_name, last_name, phone, parent_name, parent_phone FROM students")
    return [dict(s) for s in students]

@router.get("/{student_id}", dependencies=[Depends(require_role(["admin", "student"]))])
async def get_student(student_id: int, db: asyncpg.Connection = Depends(get_db)):
    student = await db.fetchrow(
        "SELECT id, dni, first_name, last_name, phone, parent_name, parent_phone FROM students WHERE id = $1",
        student_id
    )
    if not student:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return dict(student)

@router.put("/{student_id}", dependencies=[Depends(require_role(["admin"]))])
async def update_student(student_id: int, student: StudentUpdate, db: asyncpg.Connection = Depends(get_db)):
    fields = []
    values = []
    idx = 1
    
    for field, value in student.dict(exclude_unset=True).items():
        fields.append(f"{field} = ${idx}")
        values.append(value)
        idx += 1
    
    if not fields:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    values.append(student_id)
    query = f"UPDATE students SET {', '.join(fields)} WHERE id = ${idx}"
    
    await db.execute(query, *values)
    return {"message": "Estudiante actualizado correctamente"}

@router.delete("/{student_id}", dependencies=[Depends(require_role(["admin"]))])
async def delete_student(student_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute("DELETE FROM students WHERE id = $1", student_id)
    return {"message": "Estudiante eliminado correctamente"}
