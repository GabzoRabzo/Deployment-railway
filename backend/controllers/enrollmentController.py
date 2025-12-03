import asyncpg
from models.enrollment import EnrollmentCreate, EnrollmentStatusUpdate
from datetime import date, timedelta

async def get_student_enrollments(student_id: int, db: asyncpg.Connection):
    enrollments = await db.fetch(
        """SELECT e.*, 
                  COALESCE(c.name, p.name) as item_name,
                  COALESCE(co.group_label, po.group_label) as group_label,
                  cyc.name as cycle_name
           FROM enrollments e
           LEFT JOIN course_offerings co ON e.course_offering_id = co.id
           LEFT JOIN courses c ON co.course_id = c.id
           LEFT JOIN package_offerings po ON e.package_offering_id = po.id
           LEFT JOIN packages p ON po.package_id = p.id
           LEFT JOIN cycles cyc ON cyc.id = COALESCE(co.cycle_id, po.cycle_id)
           WHERE e.student_id = $1
           ORDER BY e.registered_at DESC""",
        student_id
    )
    return [dict(e) for e in enrollments]

async def get_enrollments_by_offering(type: str, id: int, status: str, db: asyncpg.Connection):
    where = "e.enrollment_type = $1 AND e.status = $2"
    params = [type if type == "course" else "package", status]
    
    if type == "course":
        where += " AND e.course_offering_id = $3"
    else:
        where += " AND e.package_offering_id = $3"
    params.append(id)
    
    enrollments = await db.fetch(
        f"""SELECT 
              MIN(e.id) as enrollment_id,
              e.enrollment_type,
              MIN(e.status) as status,
              s.id as student_id, s.first_name, s.last_name, s.dni,
              COALESCE(c.name, p.name) as item_name
           FROM enrollments e
           JOIN students s ON s.id = e.student_id
           LEFT JOIN course_offerings co ON e.course_offering_id = co.id
           LEFT JOIN courses c ON co.course_id = c.id
           LEFT JOIN package_offerings po ON e.package_offering_id = po.id
           LEFT JOIN packages p ON po.package_id = p.id
           WHERE {where}
           GROUP BY e.enrollment_type, s.id, s.first_name, s.last_name, s.dni, item_name
           ORDER BY s.last_name, s.first_name""",
        *params
    )
    return [dict(e) for e in enrollments]

async def create_enrollment(student_id: int, data: EnrollmentCreate, db: asyncpg.Connection):
    created = []
    
    for item in data.items:
        # Check if already enrolled
        if item.type == "course":
            existing = await db.fetchrow(
                "SELECT id FROM enrollments WHERE student_id = $1 AND course_offering_id = $2",
                student_id, item.id
            )
            if existing:
                return {"error": "El estudiante ya está matriculado en este curso"}
            
            # Get price
            offering = await db.fetchrow(
                """SELECT COALESCE(price_override, c.base_price) as price
                   FROM course_offerings co
                   JOIN courses c ON co.course_id = c.id
                   WHERE co.id = $1""",
                item.id
            )
            price = offering['price'] if offering else 0
            
            # Create enrollment
            enr_result = await db.fetchrow(
                """INSERT INTO enrollments (student_id, course_offering_id, enrollment_type, status)
                   VALUES ($1, $2, 'course', 'pendiente') RETURNING id""",
                student_id, item.id
            )
            enrollment_id = enr_result['id']
            
        else:  # package
            existing = await db.fetchrow(
                "SELECT id FROM enrollments WHERE student_id = $1 AND package_offering_id = $2",
                student_id, item.id
            )
            if existing:
                return {"error": "El estudiante ya está matriculado en este paquete"}
            
            # Get price
            offering = await db.fetchrow(
                """SELECT COALESCE(price_override, p.base_price) as price
                   FROM package_offerings po
                   JOIN packages p ON po.package_id = p.id
                   WHERE po.id = $1""",
                item.id
            )
            price = offering['price'] if offering else 0
            
            # Create enrollment
            enr_result = await db.fetchrow(
                """INSERT INTO enrollments (student_id, package_offering_id, enrollment_type, status)
                   VALUES ($1, $2, 'package', 'pendiente') RETURNING id""",
                student_id, item.id
            )
            enrollment_id = enr_result['id']
        
        # Create payment plan
        plan_result = await db.fetchrow(
            """INSERT INTO payment_plans (enrollment_id, total_amount, installments)
               VALUES ($1, $2, 1) RETURNING id""",
            enrollment_id, price
        )
        payment_plan_id = plan_result['id']
        
        # Create installment
        first_due_date = date.today() + timedelta(days=7)
        inst_result = await db.fetchrow(
            """INSERT INTO installments (payment_plan_id, installment_number, due_date, amount, status)
               VALUES ($1, 1, $2, $3, 'pending') RETURNING id""",
            payment_plan_id, first_due_date, price
        )
        installment_id = inst_result['id']
        
        created.append({
            "enrollmentId": enrollment_id,
            "payment_plan_id": payment_plan_id,
            "installment_id": installment_id
        })
    
    return {"message": "Matrículas creadas correctamente", "created": created}

async def update_enrollment_status(data: EnrollmentStatusUpdate, db: asyncpg.Connection):
    # Check payment status if accepting
    if data.status == "aceptado":
        payment_check = await db.fetchrow(
            """SELECT pp.id, pp.total_amount,
                      COALESCE(SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END), 0) as total_paid
               FROM payment_plans pp
               LEFT JOIN installments i ON i.payment_plan_id = pp.id AND i.status = 'paid'
               WHERE pp.enrollment_id = $1
               GROUP BY pp.id, pp.total_amount""",
            data.enrollment_id
        )
        
        if not payment_check or payment_check['total_paid'] < payment_check['total_amount']:
            return {"error": "No se puede aceptar: pago no aprobado completamente"}
    
    await db.execute(
        "UPDATE enrollments SET status = $1 WHERE id = $2",
        data.status, data.enrollment_id
    )
    
    return {"message": f"Matrícula {data.status}"}

async def get_admin_enrollments(db: asyncpg.Connection):
    enrollments = await db.fetch(
        """SELECT e.*, s.first_name, s.last_name, s.dni,
                  COALESCE(c.name, p.name) as item_name,
                  COALESCE(co.group_label, po.group_label) as group_label,
                  cyc.name as cycle_name
           FROM enrollments e
           JOIN students s ON e.student_id = s.id
           LEFT JOIN course_offerings co ON e.course_offering_id = co.id
           LEFT JOIN courses c ON co.course_id = c.id
           LEFT JOIN package_offerings po ON e.package_offering_id = po.id
           LEFT JOIN packages p ON po.package_id = p.id
           LEFT JOIN cycles cyc ON cyc.id = COALESCE(co.cycle_id, po.cycle_id)
           ORDER BY e.registered_at DESC"""
    )
    return [dict(e) for e in enrollments]

async def delete_enrollment(enrollment_id: int, db: asyncpg.Connection):
    await db.execute("DELETE FROM enrollments WHERE id = $1", enrollment_id)
    return {"message": "Matrícula eliminada correctamente"}
