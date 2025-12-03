import asyncio
import asyncpg
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

async def create_test_data():
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'academia_final'),
        port=int(os.getenv('DB_PORT', '5432'))
    )
    
    print('📊 Creando datos de prueba...\n')
    
    # This script is mainly for compatibility
    # In the original it created teachers and users
    # But createTestUsers.py already does this
    
    print('✅ Los datos de prueba se crean con createTestUsers.py')
    print('   Ejecuta: python scripts/createTestUsers.py')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(create_test_data())
