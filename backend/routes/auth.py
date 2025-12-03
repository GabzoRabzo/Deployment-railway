from fastapi import APIRouter, Depends, HTTPException, status
from models.user import UserCreate, UserLogin, TokenResponse, UserResponse
from utils.security import get_password_hash, verify_password, create_access_token
from config.database import get_db
import asyncpg

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: asyncpg.Connection = Depends(get_db)):
    try:
        password_hash = get_password_hash(user.password)
        
        result = await db.fetchrow(
            "INSERT INTO users (username, password_hash, role, related_id) VALUES ($1, $2, $3, $4) RETURNING id",
            user.username, password_hash, user.role, user.related_id
        )
        
        user_id = result['id']
        token = create_access_token({"id": user_id, "role": user.role})
        
        return {
            "token": token,
            "user": {
                "id": user_id,
                "username": user.username,
                "role": user.role,
                "related_id": user.related_id
            }
        }
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya está registrado"
        )

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: asyncpg.Connection = Depends(get_db)):
    # Try to find user by username (DNI)
    user = await db.fetchrow(
        "SELECT id, username, password_hash, role, related_id FROM users WHERE username = $1",
        credentials.dni
    )
    
    # If not found, try to find student by DNI
    if not user:
        student = await db.fetchrow(
            "SELECT id, dni, password_hash FROM students WHERE dni = $1",
            credentials.dni
        )
        if student and verify_password(credentials.password, student['password_hash']):
            token = create_access_token({"id": student['id'], "role": "student"})
            return {
                "token": token,
                "user": {
                    "id": student['id'],
                    "username": student['dni'],
                    "role": "student",
                    "related_id": None
                }
            }
    
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta"
        )
    
    token = create_access_token({"id": user['id'], "role": user['role']})
    
    return {
        "token": token,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "related_id": user['related_id']
        }
    }
