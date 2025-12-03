import asyncio
import httpx
import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = 'http://localhost:4000/api'

async def debug_schedule():
    print('DEBUG: Testing Schedule Creation')
    
    async with httpx.AsyncClient() as client:
        # 1. Login Admin
        resp = await client.post(f'{BASE_URL}/auth/login', json={'dni': 'admin', 'password': 'admin123'})
        token = resp.json()['token']
        headers = {'Authorization': f'Bearer {token}'}
        print('Admin logged in')

        # 2. Create Cycle
        resp = await client.post(f'{BASE_URL}/cycles', json={
            'name': f'Ciclo Debug {int(time.time())}', 'start_date': '2024-01-01', 
            'end_date': '2024-06-30', 'duration_months': 6, 'status': 'open'
        }, headers=headers)
        cycle_id = resp.json()['id']
        print(f'Cycle created: {cycle_id}')

        # 3. Create Course
        resp = await client.post(f'{BASE_URL}/courses', json={
            'name': 'Curso Debug', 'description': 'Desc', 'base_price': 100
        }, headers=headers)
        course_id = resp.json()['id']
        print(f'Course created: {course_id}')

        # 4. Create Teacher
        resp = await client.post(f'{BASE_URL}/teachers', json={
            'first_name': 'T', 'last_name': 'T', 'dni': f'999{int(time.time())}', 
            'phone': '123', 'email': 't@t.com', 'specialization': 'S'
        }, headers=headers)
        teacher_id = resp.json()['id']
        print(f'Teacher created: {teacher_id}')

        # 5. Create Offering
        resp = await client.post(f'{BASE_URL}/courses/offerings', json={
            'course_id': course_id, 'cycle_id': cycle_id, 'group_label': 'A',
            'teacher_id': teacher_id, 'price_override': 100, 'capacity': 20
        }, headers=headers)
        offering_id = resp.json()['id']
        print(f'Offering created: {offering_id}')

        # 6. Create Schedule (THE FAILING STEP)
        print('Attempting to create schedule...')
        payload = {
            'course_offering_id': offering_id,
            'day_of_week': 'Lunes',
            'start_time': '09:00:00',
            'end_time': '11:00:00',
            'classroom': 'A1'
        }
        resp = await client.post(f'{BASE_URL}/schedules', json=payload, headers=headers)
        print(f'Status: {resp.status_code}')
        print(f'Response: {resp.text}')

if __name__ == "__main__":
    asyncio.run(debug_schedule())
