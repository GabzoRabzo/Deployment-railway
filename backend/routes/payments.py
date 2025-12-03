from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from middleware.auth import get_current_user, require_role
from config.database import get_db
import asyncpg
from datetime import date
import os

router = APIRouter(prefix="/payments", tags=["payments"])

@router.get("/student")
async def get_student_payments(
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    student_id = current_user.get("id")
    if not student_id:
        raise HTTPException(status_code=401, detail="No autenticado")
    
    payments = await db.fetch(
        """SELECT i.*, pp.enrollment_id, pp.total_amount as plan_total,
                  e.enrollment_type,
                  COALESCE(c.name, p.name) as item_name
           FROM installments i
           JOIN payment_plans pp ON i.payment_plan_id = pp.id
           JOIN enrollments e ON pp.enrollment_id = e.id
           LEFT JOIN course_offerings co ON e.course_offering_id = co.id
           LEFT JOIN courses c ON co.course_id = c.id
           LEFT JOIN package_offerings po ON e.package_offering_id = po.id
           LEFT JOIN packages p ON po.package_id = p.id
           WHERE e.student_id = $1
           ORDER BY i.due_date""",
        student_id
    )
    return [dict(p) for p in payments]

@router.get("/pending")
async def get_pending_payments(
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    student_id = current_user.get("id")
    if not student_id:
        raise HTTPException(status_code=401, detail="No autenticado")
    
    pending = await db.fetch(
        """SELECT i.*, pp.enrollment_id,
                  COALESCE(c.name, p.name) as item_name,
                  CASE 
                    WHEN i.due_date < CURRENT_DATE THEN 'vencido'
                    WHEN i.due_date <= CURRENT_DATE + INTERVAL '7 days' THEN 'proximo'
                    ELSE 'pendiente'
                  END as urgency
           FROM installments i
           JOIN payment_plans pp ON i.payment_plan_id = pp.id
           JOIN enrollments e ON pp.enrollment_id = e.id
           LEFT JOIN course_offerings co ON e.course_offering_id = co.id
           LEFT JOIN courses c ON co.course_id = c.id
           LEFT JOIN package_offerings po ON e.package_offering_id = po.id
           LEFT JOIN packages p ON po.package_id = p.id
           WHERE e.student_id = $1 AND i.status = 'pending'
           ORDER BY i.due_date""",
        student_id
    )
    return [dict(p) for p in pending]

@router.post("/upload-voucher")
async def upload_voucher(
    installment_id: int = Form(...),
    voucher: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    # Verify installment belongs to student
    installment = await db.fetchrow(
        """SELECT i.*, e.student_id
           FROM installments i
           JOIN payment_plans pp ON i.payment_plan_id = pp.id
           JOIN enrollments e ON pp.enrollment_id = e.id
           WHERE i.id = $1""",
        installment_id
    )
    
    if not installment:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")
    
    if installment['student_id'] != current_user.get("id"):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Save file
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_extension = os.path.splitext(voucher.filename)[1]
    filename = f"voucher_{installment_id}_{date.today().isoformat()}{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, "wb") as f:
        content = await voucher.read()
        f.write(content)
    
    # Update installment
    await db.execute(
        "UPDATE installments SET voucher_path = $1, status = 'pending_approval' WHERE id = $2",
        file_path, installment_id
    )
    
    return {"message": "Comprobante subido correctamente", "filename": filename}

@router.put("/approve/{installment_id}", dependencies=[Depends(require_role(["admin"]))])
async def approve_payment(installment_id: int, db: asyncpg.Connection = Depends(get_db)):
    installment = await db.fetchrow("SELECT * FROM installments WHERE id = $1", installment_id)
    
    if not installment:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")
    
    await db.execute(
        "UPDATE installments SET status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE id = $1",
        installment_id
    )
    
    return {"message": "Pago aprobado"}

@router.put("/reject/{installment_id}", dependencies=[Depends(require_role(["admin"]))])
async def reject_payment(installment_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute(
        "UPDATE installments SET status = 'pending', voucher_url = NULL WHERE id = $1",
        installment_id
    )
    return {"message": "Pago rechazado"}

@router.get("/admin/pending", dependencies=[Depends(require_role(["admin"]))])
async def get_admin_pending_payments(db: asyncpg.Connection = Depends(get_db)):
    pending = await db.fetch(
        """SELECT i.*, pp.enrollment_id, s.first_name, s.last_name, s.dni,
                  COALESCE(c.name, p.name) as item_name
           FROM installments i
           JOIN payment_plans pp ON i.payment_plan_id = pp.id
           JOIN enrollments e ON pp.enrollment_id = e.id
           JOIN students s ON e.student_id = s.id
           LEFT JOIN course_offerings co ON e.course_offering_id = co.id
           LEFT JOIN courses c ON co.course_id = c.id
           LEFT JOIN package_offerings po ON e.package_offering_id = po.id
           LEFT JOIN packages p ON po.package_id = p.id
           WHERE i.status = 'pending_approval'
           ORDER BY i.due_date"""
    )
    return [dict(p) for p in pending]

@router.get("/admin/overdue", dependencies=[Depends(require_role(["admin"]))])
async def get_overdue_payments(db: asyncpg.Connection = Depends(get_db)):
    overdue = await db.fetch(
        """SELECT i.*, pp.enrollment_id, s.first_name, s.last_name, s.dni, s.parent_phone,
                  COALESCE(c.name, p.name) as item_name,
                  CURRENT_DATE - i.due_date as days_overdue
           FROM installments i
           JOIN payment_plans pp ON i.payment_plan_id = pp.id
           JOIN enrollments e ON pp.enrollment_id = e.id
           JOIN students s ON e.student_id = s.id
           LEFT JOIN course_offerings co ON e.course_offering_id = co.id
           LEFT JOIN courses c ON co.course_id = c.id
           LEFT JOIN package_offerings po ON e.package_offering_id = po.id
           LEFT JOIN packages p ON po.package_id = p.id
           WHERE i.status = 'pending' AND i.due_date < CURRENT_DATE
           ORDER BY i.due_date"""
    )
    return [dict(p) for p in overdue]
