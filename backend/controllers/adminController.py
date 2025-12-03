import asyncpg

async def get_dashboard_data(db: asyncpg.Connection):
    dashboard = await db.fetch(
        """SELECT 
            e.id as enrollment_id,
            e.student_id,
            s.first_name || ' ' || s.last_name as student_name,
            s.dni,
            s.phone,
            s.parent_name,
            s.parent_phone,
            cyc.id as cycle_id,
            cyc.name as cycle_name,
            cyc.start_date,
            cyc.end_date,
            e.enrollment_type,
            COALESCE(co.group_label, po.group_label) as grupo,
            COALESCE(c.name, p.name) as enrolled_item,
            e.status as enrollment_status,
            COUNT(DISTINCT CASE WHEN a.status = 'presente' THEN a.id END) as attendance_count,
            COUNT(DISTINCT a.id) as total_classes,
            CASE 
                WHEN COUNT(DISTINCT a.id) > 0 
                THEN ROUND(COUNT(DISTINCT CASE WHEN a.status = 'presente' THEN a.id END)::numeric / COUNT(DISTINCT a.id)::numeric * 100, 2)
                ELSE 0 
            END as attendance_pct,
            COALESCE(SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END), 0) as total_paid,
            COALESCE(SUM(pp.total_amount) - SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END), 0) as pending_amount,
            COUNT(DISTINCT CASE WHEN a.status = 'ausente' THEN a.id END) as total_absences,
            CASE 
                WHEN COUNT(DISTINCT CASE WHEN a.status = 'ausente' THEN a.id END) >= 3 THEN 'Alerta: 3+ faltas'
                WHEN COALESCE(SUM(pp.total_amount) - SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END), 0) > 0 THEN 'Pago pendiente'
                ELSE 'OK'
            END as alert_status
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        LEFT JOIN course_offerings co ON e.course_offering_id = co.id
        LEFT JOIN courses c ON co.course_id = c.id
        LEFT JOIN package_offerings po ON e.package_offering_id = po.id
        LEFT JOIN packages p ON po.package_id = p.id
        LEFT JOIN cycles cyc ON cyc.id = COALESCE(co.cycle_id, po.cycle_id)
        LEFT JOIN payment_plans pp ON pp.enrollment_id = e.id
        LEFT JOIN installments i ON i.payment_plan_id = pp.id
        LEFT JOIN schedules sch ON sch.course_offering_id = COALESCE(e.course_offering_id, 
            (SELECT poc.course_offering_id FROM package_offering_courses poc WHERE poc.package_offering_id = e.package_offering_id LIMIT 1))
        LEFT JOIN attendance a ON a.student_id = e.student_id AND a.schedule_id = sch.id
        WHERE e.status = 'aceptado'
        GROUP BY e.id, e.student_id, s.first_name, s.last_name, s.dni, s.phone, s.parent_name, s.parent_phone,
                 cyc.id, cyc.name, cyc.start_date, cyc.end_date, e.enrollment_type, grupo, enrolled_item, e.status
        ORDER BY s.last_name, s.first_name"""
    )
    return [dict(d) for d in dashboard]

async def get_analytics(cycle_id: int, db: asyncpg.Connection):
    analytics = await db.fetch(
        """SELECT 
            cyc.id as cycle_id,
            cyc.name as cycle_name,
            COUNT(DISTINCT e.id) as total_enrollments,
            COUNT(DISTINCT CASE WHEN e.status = 'aceptado' THEN e.id END) as accepted_enrollments,
            COALESCE(SUM(pp.total_amount), 0) as total_debt,
            COALESCE(SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END), 0) as total_paid,
            COALESCE(SUM(pp.total_amount) - SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END), 0) as pending_amount,
            COUNT(DISTINCT CASE WHEN a.status = 'presente' THEN a.id END) as total_attendance,
            COUNT(DISTINCT CASE WHEN a.status = 'ausente' THEN a.id END) as total_absences,
            CASE 
                WHEN COUNT(DISTINCT CASE WHEN a.status = 'ausente' THEN a.id END) >= 3 THEN 'high'
                WHEN COUNT(DISTINCT CASE WHEN a.status = 'ausente' THEN a.id END) > 0 THEN 'medium'
                ELSE 'low'
            END as absence_alert_level
        FROM cycles cyc
        LEFT JOIN course_offerings co ON co.cycle_id = cyc.id
        LEFT JOIN package_offerings po ON po.cycle_id = cyc.id
        LEFT JOIN enrollments e ON e.course_offering_id = co.id OR e.package_offering_id = po.id
        LEFT JOIN payment_plans pp ON pp.enrollment_id = e.id
        LEFT JOIN installments i ON i.payment_plan_id = pp.id
        LEFT JOIN schedules sch ON sch.course_offering_id = co.id
        LEFT JOIN attendance a ON a.schedule_id = sch.id AND a.student_id = e.student_id
        WHERE cyc.id = $1
        GROUP BY cyc.id, cyc.name""",
        cycle_id
    )
    return [dict(a) for a in analytics]

async def get_general_stats(db: asyncpg.Connection):
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
