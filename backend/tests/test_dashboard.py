import asyncio
import asyncpg
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

async def test_dashboard():
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'academia_final'),
        port=int(os.getenv('DB_PORT', '5432'))
    )
    
    print('=== Probando Vista Dashboard ===\n')
    
    # Test 1: Check view exists
    try:
        result = await conn.fetch(
            "SELECT table_name FROM information_schema.views WHERE table_schema = 'public'"
        )
        views = [r['table_name'] for r in result]
        
        if 'view_dashboard_admin_extended' in views:
            print('✓ Vista view_dashboard_admin_extended existe\n')
        else:
            print('✗ Vista view_dashboard_admin_extended NO existe\n')
            await conn.close()
            return
    except Exception as e:
        print(f'Error verificando vista: {e}')
        await conn.close()
        return
    
    # Test 2: Simple query
    print('Test 2: Consulta simple a la vista')
    try:
        result = await conn.fetch('SELECT * FROM view_dashboard_admin_extended LIMIT 1')
        print(f'✓ Consulta simple exitosa')
        print(f'Resultados: {len(result)} filas\n')
    except Exception as e:
        print(f'✗ Error en consulta simple: {e}\n')
    
    # Test 3: Query with ORDER BY
    print('Test 3: Consulta con ORDER BY')
    try:
        result = await conn.fetch(
            'SELECT * FROM view_dashboard_admin_extended ORDER BY student_id DESC LIMIT 10'
        )
        print(f'✓ Consulta con ORDER BY exitosa')
        print(f'Resultados: {len(result)} filas')
        if result:
            print(f'Primera fila: {list(result[0].keys())}')
        print()
    except Exception as e:
        print(f'✗ Error en consulta con ORDER BY: {e}\n')
    
    # Test 4: View structure
    print('Test 4: Estructura de la vista')
    try:
        result = await conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'view_dashboard_admin_extended'"
        )
        print('✓ Estructura de la vista:')
        for col in result:
            print(f"  - {col['column_name']} ({col['data_type']})")
        print()
    except Exception as e:
        print(f'✗ Error obteniendo estructura: {e}\n')
    
    # Test 5: Check related tables
    print('Test 5: Verificar datos en tablas relacionadas')
    try:
        enrollments = await conn.fetchrow('SELECT COUNT(*) as count FROM enrollments')
        students = await conn.fetchrow('SELECT COUNT(*) as count FROM students')
        cycles = await conn.fetchrow('SELECT COUNT(*) as count FROM cycles')
        analytics = await conn.fetchrow('SELECT COUNT(*) as count FROM analytics_summary')
        
        print('✓ Datos en tablas:')
        print(f"  - Enrollments: {enrollments['count']}")
        print(f"  - Students: {students['count']}")
        print(f"  - Cycles: {cycles['count']}")
        print(f"  - Analytics: {analytics['count']}")
        print()
    except Exception as e:
        print(f'✗ Error verificando datos: {e}\n')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(test_dashboard())
