import asyncio
import httpx
import sys
from pathlib import Path
from datetime import date
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = 'http://localhost:4000/api'

# Colors
class colors:
    reset = '\033[0m'
    green = '\033[32m'
    red = '\033[31m'
    yellow = '\033[33m'
    blue = '\033[34m'
    cyan = '\033[36m'

def log(message, type='info'):
    prefix = f'{colors.green}✓' if type == 'success' else \
             f'{colors.red}✗' if type == 'error' else \
             f'{colors.yellow}⚠' if type == 'warning' else \
             f'{colors.cyan}ℹ'
    print(f'{prefix} {message}{colors.reset}')

# Global variables
admin_token = ''
student_token = ''
teacher_token = ''
cycle_id = None
course_id = None
teacher_id = None
course_offering_id = None
student_id = None
enrollment_id = None
payment_plan_id = None
installment_id = None
schedule_id = None

async def paso0_verificar_servidor(client):
    log('\n=== PASO 0: Verificar que el servidor esté funcionando ===', 'info')
    
    try:
        response = await client.get(f'{BASE_URL}/cycles')
        if response.status_code in [200, 401, 403]:
            log('Servidor está funcionando', 'success')
            return True
        else:
            log('Servidor no responde correctamente', 'error')
            return False
    except Exception as e:
        log(f'Error conectando al servidor: {e}', 'error')
        log('Asegúrate de que el servidor esté corriendo en http://localhost:4000', 'warning')
        return False

async def paso1_crear_ciclo(client):
    global admin_token, cycle_id
    log('\n=== PASO 1: Admin crea ciclo ===', 'info')
    
    # Login admin
    try:
        response = await client.post(f'{BASE_URL}/auth/login', json={
            'dni': 'admin',
            'password': 'admin123'
        })
        
        if response.status_code == 200:
            admin_token = response.json()['token']
            log('Admin autenticado', 'success')
        else:
            log(f'Error en login: {response.json()}', 'error')
            log('Ejecuta: python scripts/createAdmin.py', 'warning')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False
    
    # Create cycle
    try:
        response = await client.post(
            f'{BASE_URL}/cycles',
            json={
                'name': 'Ciclo 2024-1',
                'start_date': '2024-01-01',
                'end_date': '2024-06-30',
                'duration_months': 6,
                'status': 'open'
            },
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 201:
            cycle_id = response.json()['id']
            log(f'Ciclo creado: {cycle_id}', 'success')
            return True
        else:
            log(f'Error creando ciclo: {response.json()}', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False

async def paso2_agregar_cursos_y_docentes(client):
    global course_id, teacher_id
    log('\n=== PASO 2: Admin agrega cursos y docentes ===', 'info')
    
    # Create course
    timestamp = int(time.time())
    try:
        response = await client.post(
            f'{BASE_URL}/courses',
            json={
                'name': f'Matemáticas Básicas {timestamp}',
                'description': 'Curso de matemáticas para principiantes',
                'base_price': 500.00
            },
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 201:
            course_id = response.json()['id']
            log(f'Curso creado: {course_id}', 'success')
        else:
            log(f'Error creando curso: {response.json()}', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False
    
    # Create teacher
    try:
        dni = f'12345{timestamp % 100000}'
        response = await client.post(
            f'{BASE_URL}/teachers',
            json={
                'first_name': 'Juan',
                'last_name': 'Pérez',
                'dni': dni,
                'phone': '987654321',
                'email': f'juan.perez.{timestamp}@academia.com',
                'specialization': 'Matemáticas'
            },
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 201:
            teacher_id = response.json()['id']
            log(f'Docente creado: {teacher_id}', 'success')
        else:
            # Try to get existing teacher
            response = await client.get(
                f'{BASE_URL}/teachers',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
            if response.status_code == 200 and response.json():
                teacher_id = response.json()[0]['id']
                log(f'Usando docente existente: {teacher_id}', 'success')
            else:
                log(f'Error creando docente: {response.json()}', 'error')
                return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False
    
    return True

async def paso3_publicar_ofertas(client):
    global course_offering_id
    log('\n=== PASO 3: Admin publica ofertas ===', 'info')
    
    try:
        response = await client.post(
            f'{BASE_URL}/courses/offerings',
            json={
                'course_id': course_id,
                'cycle_id': cycle_id,
                'group_label': 'Grupo A',
                'teacher_id': teacher_id,
                'price_override': 450.00,
                'capacity': 30
            },
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 201:
            course_offering_id = response.json()['id']
            log(f'Oferta de curso creada: {course_offering_id}', 'success')
            return True
        else:
            log(f'Error creando oferta: {response.json()}', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False

async def paso4_definir_horarios(client):
    global schedule_id
    log('\n=== PASO 4: Admin define horarios ===', 'info')
    
    try:
        response = await client.post(
            f'{BASE_URL}/schedules',
            json={
                'course_offering_id': course_offering_id,
                'day_of_week': 'Lunes',
                'start_time': '09:00:00',
                'end_time': '11:00:00',
                'classroom': 'Aula 101'
            },
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 201:
            schedule_id = response.json()['id']
            log(f'Horario creado: {schedule_id}', 'success')
            return True
        else:
            log(f'Error creando horario: {response.json()}', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False

async def paso5_alumno_se_registra(client):
    global student_token, student_id
    log('\n=== PASO 5: Alumno se registra ===', 'info')
    
    timestamp = int(time.time())
    dni = f'87654{timestamp % 100000}'
    
    try:
        response = await client.post(
            f'{BASE_URL}/students/register',
            json={
                'dni': dni,
                'first_name': 'María',
                'last_name': 'García',
                'phone': '987654322',
                'parent_name': 'Pedro García',
                'parent_phone': '987654323',
                'password': 'student123'
            }
        )
        
        if response.status_code == 201:
            student_token = response.json()['token']
            student_id = response.json()['user']['id']
            log(f'Estudiante registrado: {student_id}', 'success')
            return True
        else:
            log(f'Error registrando estudiante: {response.json()}', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False

async def paso6_alumno_se_matricula(client):
    global enrollment_id, payment_plan_id, installment_id
    log('\n=== PASO 6: Alumno elige curso y se matricula ===', 'info')
    
    try:
        response = await client.post(
            f'{BASE_URL}/enrollments',
            json={
                'items': [
                    {
                        'type': 'course',
                        'id': course_offering_id
                    }
                ]
            },
            headers={'Authorization': f'Bearer {student_token}'}
        )
        
        if response.status_code == 201:
            data = response.json()
            enrollment_id = data['created'][0]['enrollmentId']
            payment_plan_id = data['created'][0]['payment_plan_id']
            installment_id = data['created'][0]['installment_id']
            log(f'Matrícula creada: {enrollment_id}', 'success')
            log(f'Plan de pago creado: {payment_plan_id}', 'success')
            log(f'Cuota creada: {installment_id}', 'success')
            return True
        else:
            log(f'Error creando matrícula: {response.json()}', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False

async def paso7_admin_revisa_matriculas(client):
    global enrollment_id
    log('\n=== PASO 7: Admin revisa matrículas ===', 'info')
    
    try:
        response = await client.get(
            f'{BASE_URL}/enrollments/admin',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 200:
            enrollments = response.json()
            pending = [e for e in enrollments if e['status'] == 'pendiente']
            
            if pending:
                enrollment_id = pending[0]['id']
                log(f'Matrícula pendiente encontrada: {enrollment_id}', 'success')
                return True
            else:
                log('No se encontraron matrículas pendientes', 'warning')
                return False
        else:
            log(f'Error obteniendo matrículas: {response.json()}', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False

async def paso8_admin_acepta_matricula(client):
    log('\n=== PASO 8: Admin acepta matrícula ===', 'info')
    
    try:
        # First approve payment
        response = await client.put(
            f'{BASE_URL}/payments/approve/{installment_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 200:
            log('Pago aprobado', 'success')
        
        # Then accept enrollment
        response = await client.put(
            f'{BASE_URL}/enrollments/status',
            json={
                'enrollment_id': enrollment_id,
                'status': 'aceptado'
            },
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 200:
            log(f'Matrícula aceptada: {enrollment_id}', 'success')
            return True
        else:
            log(f'Error aceptando matrícula: {response.json()}', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False

async def paso9_docente_marca_asistencias(client):
    global teacher_token
    log('\n=== PASO 9: Docente marca asistencias ===', 'info')
    
    # Get teacher info
    try:
        response = await client.get(
            f'{BASE_URL}/teachers/{teacher_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 200:
            teacher_dni = response.json()['dni']
            log(f'DNI del docente: {teacher_dni}', 'info')
        else:
            log('Error obteniendo docente', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False
    
    # Login teacher
    try:
        response = await client.post(
            f'{BASE_URL}/auth/login',
            json={
                'dni': teacher_dni,
                'password': teacher_dni
            }
        )
        
        if response.status_code == 200:
            teacher_token = response.json()['token']
            log('Docente autenticado', 'success')
        else:
            log(f'Error en login de docente: {response.json()}', 'warning')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False
    
    # Mark attendance
    try:
        response = await client.post(
            f'{BASE_URL}/teachers/{teacher_id}/attendance',
            json={
                'schedule_id': schedule_id,
                'student_id': student_id,
                'status': 'presente'
            },
            headers={'Authorization': f'Bearer {teacher_token}'}
        )
        
        if response.status_code == 200:
            log('Asistencia marcada correctamente', 'success')
            return True
        else:
            log(f'Error marcando asistencia: {response.json()}', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False

async def paso10_verificar_dashboard_admin(client):
    log('\n=== PASO 10: Verificar dashboard admin ===', 'info')
    
    try:
        response = await client.get(
            f'{BASE_URL}/admin/dashboard',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 200:
            dashboard = response.json()
            log(f'Dashboard obtenido con {len(dashboard)} registros', 'success')
            
            if dashboard:
                student_record = [d for d in dashboard if d.get('student_id') == student_id]
                if student_record:
                    log(f"Estudiante encontrado en dashboard: {student_record[0].get('student_name')}", 'success')
                    return True
                else:
                    log('Estudiante no encontrado en dashboard', 'warning')
                    return False
            else:
                log('Dashboard vacío', 'warning')
                return False
        else:
            log(f'Error obteniendo dashboard: {response.json()}', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False

async def paso11_verificar_analytics(client):
    log('\n=== PASO 11: Verificar analytics ===', 'info')
    
    try:
        response = await client.get(
            f'{BASE_URL}/admin/analytics?cycle_id={cycle_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        if response.status_code == 200:
            analytics = response.json()
            log(f'Analytics obtenidos: {len(analytics)} registros', 'success')
            return True
        else:
            log(f'Error obteniendo analytics: {response.json()}', 'error')
            return False
    except Exception as e:
        log(f'Error: {e}', 'error')
        return False

async def ejecutar_pruebas():
    print(f'{colors.blue}═══════════════════════════════════════════════════════════{colors.reset}')
    print(f'{colors.blue}  PRUEBAS DEL FLUJO DEL SISTEMA - ACADEMIA V2 (FastAPI){colors.reset}')
    print(f'{colors.blue}═══════════════════════════════════════════════════════════{colors.reset}')
    
    pasos = [
        {'nombre': 'PASO 0: Verificar servidor', 'fn': paso0_verificar_servidor},
        {'nombre': 'PASO 1: Crear ciclo', 'fn': paso1_crear_ciclo},
        {'nombre': 'PASO 2: Agregar cursos y docentes', 'fn': paso2_agregar_cursos_y_docentes},
        {'nombre': 'PASO 3: Publicar ofertas', 'fn': paso3_publicar_ofertas},
        {'nombre': 'PASO 4: Definir horarios', 'fn': paso4_definir_horarios},
        {'nombre': 'PASO 5: Alumno se registra', 'fn': paso5_alumno_se_registra},
        {'nombre': 'PASO 6: Alumno se matricula', 'fn': paso6_alumno_se_matricula},
        {'nombre': 'PASO 7: Admin revisa matrículas', 'fn': paso7_admin_revisa_matriculas},
        {'nombre': 'PASO 8: Admin acepta matrícula', 'fn': paso8_admin_acepta_matricula},
        {'nombre': 'PASO 9: Docente marca asistencias', 'fn': paso9_docente_marca_asistencias},
        {'nombre': 'PASO 10: Verificar dashboard admin', 'fn': paso10_verificar_dashboard_admin},
        {'nombre': 'PASO 11: Verificar analytics', 'fn': paso11_verificar_analytics}
    ]
    
    exitosas = 0
    fallidas = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for paso in pasos:
            try:
                resultado = await paso['fn'](client)
                if resultado:
                    exitosas += 1
                else:
                    fallidas += 1
                    log(f"Paso fallido: {paso['nombre']}", 'error')
            except Exception as e:
                fallidas += 1
                log(f"Error en {paso['nombre']}: {e}", 'error')
    
    print(f'\n{colors.blue}═══════════════════════════════════════════════════════════{colors.reset}')
    print(f'{colors.blue}  RESUMEN DE PRUEBAS{colors.reset}')
    print(f'{colors.blue}═══════════════════════════════════════════════════════════{colors.reset}')
    print(f'{colors.green}Pruebas exitosas: {exitosas}{colors.reset}')
    print(f'{colors.red}Pruebas fallidas: {fallidas}{colors.reset}')
    print(f'{colors.cyan}Total de pruebas: {len(pasos)}{colors.reset}')
    print(f'{colors.blue}═══════════════════════════════════════════════════════════{colors.reset}\n')
    
    if fallidas == 0:
        print(f'{colors.green}¡Todas las pruebas pasaron exitosamente!{colors.reset}\n')
        return 0
    else:
        print(f'{colors.red}Algunas pruebas fallaron. Revisa los errores arriba.{colors.reset}\n')
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(ejecutar_pruebas())
    sys.exit(exit_code)
