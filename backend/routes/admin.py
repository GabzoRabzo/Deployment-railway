from fastapi import APIRouter, Depends, Query
from middleware.auth import require_role
from config.database import get_db
import asyncpg
from typing import Optional

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard", dependencies=[Depends(require_role(["admin"]))])
async def get_dashboard(
    cycle_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: asyncpg.Connection = Depends(get_db)
):
    query = "SELECT * FROM view_dashboard_admin_extended WHERE 1=1"
    params = []
    idx = 1
    
    if cycle_id:
        query += f" AND cycle_id = ${idx}"
        params.append(cycle_id)
        idx += 1
    
    if status:
        query += f" AND enrollment_status = ${idx}"
        params.append(status)
        idx += 1
    
    query += " ORDER BY student_id DESC"
    
    dashboard = await db.fetch(query, *params)
    return [dict(d) for d in dashboard]

@router.get("/analytics", dependencies=[Depends(require_role(["admin"]))])
async def get_analytics(
    cycle_id: Optional[int] = Query(None),
    db: asyncpg.Connection = Depends(get_db)
):
    query = """
        SELECT 
            s.id as student_id,
            s.first_name,
            s.last_name,
            s.dni,
            c.id as cycle_id,
            c.name as cycle_name,
            COUNT(DISTINCT e.id) as total_enrollments,
            COUNT(DISTINCT CASE WHEN e.status = 'aceptado' THEN e.id END) as accepted_enrollments,
            COALESCE(SUM(pp.total_amount), 0) as total_debt,
            COALESCE(SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END), 0) as total_paid,
            COALESCE(SUM(pp.total_amount) - SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END), 0) as pending_amount,
            COUNT(DISTINCT CASE WHEN a.status = 'presente' THEN a.id END) as total_attendance,
            COUNT(DISTINCT CASE WHEN a.status = 'ausente' THEN a.id END) as total_absences,
            CASE 
                WHEN COUNT(DISTINCT a.id) > 0 THEN 
                    ROUND(100.0 * COUNT(DISTINCT CASE WHEN a.status = 'presente' THEN a.id END) / COUNT(DISTINCT a.id), 2)
                ELSE 0
            END as attendance_percentage
        FROM students s
        LEFT JOIN enrollments e ON s.id = e.student_id
        LEFT JOIN cycles c ON c.id = COALESCE(
            (SELECT cycle_id FROM course_offerings WHERE id = e.course_offering_id),
            (SELECT cycle_id FROM package_offerings WHERE id = e.package_offering_id)
        )
        LEFT JOIN payment_plans pp ON pp.enrollment_id = e.id
        LEFT JOIN installments i ON i.payment_plan_id = pp.id AND i.status = 'paid'
        LEFT JOIN attendance a ON a.student_id = s.id
    """
    
    params = []
    idx = 1
    
    if cycle_id:
        query += f" WHERE c.id = ${idx}"
        params.append(cycle_id)
        idx += 1
    
    query += """
        GROUP BY s.id, s.first_name, s.last_name, s.dni, c.id, c.name
        ORDER BY s.last_name, s.first_name
    """
    
    analytics = await db.fetch(query, *params)
    return [dict(a) for a in analytics]

@router.get("/stats", dependencies=[Depends(require_role(["admin"]))])
async def get_stats(db: asyncpg.Connection = Depends(get_db)):
    stats = {}
    
    # Total students
    result = await db.fetchrow("SELECT COUNT(*) as count FROM students")
    stats['total_students'] = result['count']
    
    # Total teachers
    result = await db.fetchrow("SELECT COUNT(*) as count FROM teachers")
    stats['total_teachers'] = result['count']
    
    # Total courses
    result = await db.fetchrow("SELECT COUNT(*) as count FROM courses")
    stats['total_courses'] = result['count']
    
    # Active enrollments
    result = await db.fetchrow("SELECT COUNT(*) as count FROM enrollments WHERE status = 'aceptado'")
    stats['active_enrollments'] = result['count']
    
    # Pending enrollments
    result = await db.fetchrow("SELECT COUNT(*) as count FROM enrollments WHERE status = 'pendiente'")
    stats['pending_enrollments'] = result['count']
    
    # Total revenue
    result = await db.fetchrow("SELECT COALESCE(SUM(amount), 0) as total FROM installments WHERE status = 'paid'")
    stats['total_revenue'] = float(result['total'])
    
    # Pending payments
    result = await db.fetchrow(
        "SELECT COALESCE(SUM(amount), 0) as total FROM installments WHERE status = 'pending'"
    )
    stats['pending_payments'] = float(result['total'])
    
    return stats
