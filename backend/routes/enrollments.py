from fastapi import APIRouter, Depends, HTTPException, status
from models.enrollment import EnrollmentCreate, EnrollmentStatusUpdate
from middleware.auth import get_current_user, require_role
from config.database import get_db
import asyncpg
from datetime import date, timedelta

router = APIRouter(prefix="/enrollments", tags=["enrollments"])

@router.get("")
async def get_enrollments(
    student_id: int = None,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    # If student, use their ID
    if current_user["role"] == "student":
        student_id = current_user["id"]
    # If admin, can specify student_id
    elif current_user["role"] == "admin" and student_id:
        pass
    else:
        raise HTTPException(status_code=400, detail="Falta student_id o no tienes permisos")
    
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

@router.get("/by-offering")
async def get_enrollments_by_offering(
    type: str,
    id: int,
    status: str = "aceptado",
    db: asyncpg.Connection = Depends(get_db)
):
    if not type or not id:
        raise HTTPException(status_code=400, detail="Faltan parámetros: type e id")
    
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

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_enrollment(
    enrollment: EnrollmentCreate,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    student_id = current_user.get("id")
    if not student_id:
        raise HTTPException(status_code=401, detail="No autenticado")
    
    if not enrollment.items or len(enrollment.items) == 0:
        raise HTTPException(status_code=400, detail="No se enviaron items para matricular")
    
    created = []
    
    for item in enrollment.items:
        try:
            # Check if already enrolled
            if item.type == "course":
                existing = await db.fetchrow(
                    "SELECT id FROM enrollments WHERE student_id = $1 AND course_offering_id = $2",
                    student_id, item.id
                )
                if existing:
                    raise HTTPException(status_code=400, detail="El estudiante ya está matriculado en este curso")
                
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
                    raise HTTPException(status_code=400, detail="El estudiante ya está matriculado en este paquete")
                
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
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return {"message": "Matrículas creadas correctamente", "created": created}

@router.put("/status", dependencies=[Depends(require_role(["admin"]))])
async def update_enrollment_status(
    update: EnrollmentStatusUpdate,
    db: asyncpg.Connection = Depends(get_db)
):
    # Check payment status if accepting
    if update.status == "aceptado":
        payment_check = await db.fetchrow(
            """SELECT pp.id, pp.total_amount,
                      COALESCE(SUM(CASE WHEN i.status = 'paid' THEN i.amount ELSE 0 END), 0) as total_paid
               FROM payment_plans pp
               LEFT JOIN installments i ON i.payment_plan_id = pp.id AND i.status = 'paid'
               WHERE pp.enrollment_id = $1
               GROUP BY pp.id, pp.total_amount""",
            update.enrollment_id
        )
        
        if not payment_check or payment_check['total_paid'] < payment_check['total_amount']:
            raise HTTPException(status_code=400, detail="No se puede aceptar: pago no aprobado completamente")
    
    await db.execute(
        "UPDATE enrollments SET status = $1 WHERE id = $2",
        update.status, update.enrollment_id
    )
    
    return {"message": f"Matrícula {update.status}"}

@router.get("/admin", dependencies=[Depends(require_role(["admin"]))])
async def get_admin_enrollments(db: asyncpg.Connection = Depends(get_db)):
    try:
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
        if enrollments:
            first = enrollments[0]
            for k, v in first.items():
                print(f"DEBUG: {k}: {type(v)} = {v}")
        
        return [dict(e) for e in enrollments]
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error getting admin enrollments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{enrollment_id}", dependencies=[Depends(require_role(["admin"]))])
async def delete_enrollment(enrollment_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute("DELETE FROM enrollments WHERE id = $1", enrollment_id)
    return {"message": "Matrícula eliminada correctamente"}
