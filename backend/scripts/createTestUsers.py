import asyncio
import asyncpg
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.security import get_password_hash
from dotenv import load_dotenv

load_dotenv()

async def create_test_users():
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'academia_final'),
        port=int(os.getenv('DB_PORT', '5432'))
    )
    
    print('🔐 Creando usuarios de prueba...\n')
    
    # Admin
    print('📌 Creando Administrador...')
    try:
        password_hash = get_password_hash('admin123')
        await conn.execute(
            'INSERT INTO users (username, password_hash, role) VALUES ($1, $2, $3)',
            'admin', password_hash, 'admin'
        )
        print('✅ Administrador creado: admin / admin123\n')
    except asyncpg.UniqueViolationError:
        print('⚠️  El administrador ya existe\n')
    
    # Teachers
    print('👨‍🏫 Creando Docentes...')
    teachers = [
        {'dni': '12345678', 'first_name': 'Juan', 'last_name': 'Pérez', 'phone': '987654321', 
         'email': 'juan.perez@academia.edu', 'specialization': 'Matemáticas', 'password': 'docente123'},
        {'dni': '87654321', 'first_name': 'María', 'last_name': 'García', 'phone': '987654322',
         'email': 'maria.garcia@academia.edu', 'specialization': 'Física', 'password': 'docente123'},
        {'dni': '11223344', 'first_name': 'Carlos', 'last_name': 'López', 'phone': '987654323',
         'email': 'carlos.lopez@academia.edu', 'specialization': 'Química', 'password': 'docente123'}
    ]
    
    for teacher in teachers:
        try:
            result = await conn.fetchrow(
                'INSERT INTO teachers (first_name, last_name, dni, phone, email, specialization) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id',
                teacher['first_name'], teacher['last_name'], teacher['dni'], teacher['phone'],
                teacher['email'], teacher['specialization']
            )
            
            password_hash = get_password_hash(teacher['password'])
            await conn.execute(
                'INSERT INTO users (username, password_hash, role, related_id) VALUES ($1, $2, $3, $4)',
                teacher['dni'], password_hash, 'teacher', result['id']
            )
            
            print(f"✅ Docente creado: {teacher['first_name']} {teacher['last_name']} - DNI: {teacher['dni']}")
        except asyncpg.UniqueViolationError:
            print(f"⚠️  El docente con DNI {teacher['dni']} ya existe")
    
    # Students
    print('\n👨‍🎓 Creando Estudiantes...')
    students = [
        {'dni': '76543210', 'first_name': 'Ana', 'last_name': 'Martínez', 'phone': '987654324',
         'parent_name': 'Pedro Martínez', 'parent_phone': '987654325', 'password': 'estudiante123'},
        {'dni': '65432109', 'first_name': 'Luis', 'last_name': 'Rodríguez', 'phone': '987654326',
         'parent_name': 'Carmen Rodríguez', 'parent_phone': '987654327', 'password': 'estudiante123'},
        {'dni': '54321098', 'first_name': 'Sofía', 'last_name': 'Fernández', 'phone': '987654328',
         'parent_name': 'Miguel Fernández', 'parent_phone': '987654329', 'password': 'estudiante123'}
    ]
    
    for student in students:
        try:
            password_hash = get_password_hash(student['password'])
            await conn.execute(
                'INSERT INTO students (dni, first_name, last_name, phone, parent_name, parent_phone, password_hash) VALUES ($1, $2, $3, $4, $5, $6, $7)',
                student['dni'], student['first_name'], student['last_name'], student['phone'],
                student['parent_name'], student['parent_phone'], password_hash
            )
            print(f"✅ Estudiante creado: {student['first_name']} {student['last_name']} - DNI: {student['dni']}")
        except asyncpg.UniqueViolationError:
            print(f"⚠️  El estudiante con DNI {student['dni']} ya existe")
    
    print('\n✅ Usuarios de prueba creados correctamente!')
    await conn.close()

if __name__ == "__main__":
    asyncio.run(create_test_users())
