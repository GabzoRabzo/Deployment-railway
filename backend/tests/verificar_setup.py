import asyncio
import asyncpg
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

async def verify_setup():
    print('═══════════════════════════════════════════════════════════')
    print('  VERIFICACIÓN DE CONFIGURACIÓN - ACADEMIA V2 (FastAPI)')
    print('═══════════════════════════════════════════════════════════\n')
    
    errors = 0
    warnings = 0
    
    # Check .env
    print('Verificando archivo .env...')
    if os.path.exists('.env'):
        print('✓ Archivo .env encontrado')
        if os.getenv('JWT_SECRET'):
            print('✓ JWT_SECRET configurado')
        else:
            print('✗ JWT_SECRET no está configurado')
            errors += 1
    else:
        print('⚠ Archivo .env no encontrado')
        warnings += 1
    
    # Check database connection
    print('\nVerificando conexión a la base de datos...')
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'academia_final'),
            port=int(os.getenv('DB_PORT', '5432'))
        )
        
        await conn.execute('SELECT 1')
        print('✓ Conexión a la base de datos exitosa')
        print('✓ Base de datos academia_final existe')
        
        # Check tables
        print('\nVerificando tablas principales...')
        tables = [
            'users', 'students', 'teachers', 'cycles', 'courses', 'packages',
            'course_offerings', 'package_offerings', 'schedules', 'enrollments',
            'payment_plans', 'installments', 'attendance', 'notifications_log',
            'analytics_summary'
        ]
        
        result = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        existing_tables = [r['table_name'] for r in result]
        
        for table in tables:
            if table in existing_tables:
                print(f'✓ Tabla {table} existe')
            else:
                print(f'✗ Tabla {table} no existe')
                errors += 1
        
        # Check view
        print('\nVerificando vista admin...')
        result = await conn.fetch(
            "SELECT table_name FROM information_schema.views WHERE table_schema = 'public'"
        )
        views = [r['table_name'] for r in result]
        
        if 'view_dashboard_admin_extended' in views:
            print('✓ Vista view_dashboard_admin_extended existe')
        else:
            print('⚠ Vista view_dashboard_admin_extended no existe')
            warnings += 1
        
        # Check admin user
        print('\nVerificando usuario admin...')
        admin = await conn.fetchrow(
            "SELECT * FROM users WHERE role = $1 AND username = $2",
            'admin', 'admin'
        )
        
        if admin:
            print('✓ Usuario admin existe')
        else:
            print('⚠ Usuario admin no existe')
            print('  Ejecuta: python scripts/createAdmin.py')
            warnings += 1
        
        await conn.close()
        
    except Exception as e:
        print(f'✗ Error conectando a la base de datos: {e}')
        errors += 1
    
    # Summary
    print('\n═══════════════════════════════════════════════════════════')
    print('  RESUMEN')
    print('═══════════════════════════════════════════════════════════')
    
    if errors == 0 and warnings == 0:
        print('✓ Todo está configurado correctamente')
        print('Puedes ejecutar: uvicorn main:app --reload')
    else:
        if errors > 0:
            print(f'✗ Se encontraron {errors} error(es)')
        if warnings > 0:
            print(f'⚠ Se encontraron {warnings} advertencia(s)')
        print('Corrige los problemas antes de continuar')

if __name__ == "__main__":
    asyncio.run(verify_setup())
