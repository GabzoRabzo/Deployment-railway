import asyncpg
from models.student import StudentCreate
from models.user import UserLogin
from utils.security import get_password_hash, verify_password, create_access_token

async def register_student(data: StudentCreate, db: asyncpg.Connection):
    # Check if student exists
    existing = await db.fetchrow("SELECT id FROM students WHERE dni = $1", data.dni)
    if existing:
        return {"error": "El estudiante ya existe"}
    
    password_hash = get_password_hash(data.password)
    
    result = await db.fetchrow(
        """INSERT INTO students (dni, first_name, last_name, phone, parent_name, parent_phone, password_hash)
           VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
        data.dni, data.first_name, data.last_name, data.phone,
        data.parent_name, data.parent_phone, password_hash
    )
    
    token = create_access_token({"id": result['id'], "role": "student"})
    
    return {
        "token": token,
        "user": {
            "id": result['id'],
            "dni": data.dni,
            "role": "student",
            "first_name": data.first_name,
            "last_name": data.last_name
        }
    }

async def login_user(credentials: UserLogin, db: asyncpg.Connection):
    # Try student first
    student = await db.fetchrow(
        "SELECT id, dni, first_name, last_name, password_hash FROM students WHERE dni = $1",
        credentials.dni
    )
    
    if student and verify_password(credentials.password, student['password_hash']):
        token = create_access_token({"id": student['id'], "role": "student"})
        return {
            "token": token,
            "user": {
                "id": student['id'],
                "dni": student['dni'],
                "role": "student",
                "first_name": student['first_name'],
                "last_name": student['last_name']
            }
        }
    
    # Try user (admin/teacher)
    user = await db.fetchrow(
        "SELECT id, username, role, password_hash, related_id FROM users WHERE username = $1",
        credentials.dni
    )
    
    if not user:
        return {"error": "Usuario no encontrado"}
    
    if not verify_password(credentials.password, user['password_hash']):
        return {"error": "Contraseña incorrecta"}
    
    token = create_access_token({"id": user['id'], "role": user['role']})
    
    user_data = {
        "id": user['id'],
        "username": user['username'],
        "role": user['role']
    }
    
    # Get additional info for teacher
    if user['role'] == 'teacher' and user['related_id']:
        teacher = await db.fetchrow(
            "SELECT first_name, last_name FROM teachers WHERE id = $1",
            user['related_id']
        )
        if teacher:
            user_data['first_name'] = teacher['first_name']
            user_data['last_name'] = teacher['last_name']
    
    return {"token": token, "user": user_data}
