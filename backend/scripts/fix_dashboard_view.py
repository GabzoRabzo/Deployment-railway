import asyncio
import asyncpg
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

async def fix_dashboard_view():
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'academia_final'),
        port=int(os.getenv('DB_PORT', '5432'))
    )
    
    print('🔧 Reparando vista del dashboard...\n')
    
    # Read SQL file
    sql_file = Path(__file__).parent.parent / 'tests' / 'crear-vista-corregida.sql'
    
    if not sql_file.exists():
        print(f'⚠️  Archivo SQL no encontrado: {sql_file}')
        await conn.close()
        return
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    try:
        await conn.execute(sql)
        print('✅ Vista del dashboard reparada correctamente')
    except Exception as e:
        print(f'✗ Error al reparar vista: {e}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_dashboard_view())
