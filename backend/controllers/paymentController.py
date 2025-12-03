import asyncpg
from fastapi import UploadFile
import os

async def get_payment_plan(enrollment_id: int, db: asyncpg.Connection):
    plan = await db.fetchrow(
        """SELECT pp.*, e.student_id
           FROM payment_plans pp
           JOIN enrollments e ON pp.enrollment_id = e.id
           WHERE pp.enrollment_id = $1""",
        enrollment_id
    )
    if not plan:
        return None
    return dict(plan)

async def get_installments(payment_plan_id: int, db: asyncpg.Connection):
    installments = await db.fetch(
        """SELECT * FROM installments 
           WHERE payment_plan_id = $1 
           ORDER BY installment_number""",
        payment_plan_id
    )
    return [dict(i) for i in installments]

async def upload_voucher(installment_id: int, file: UploadFile, db: asyncpg.Connection):
    # Save file
    upload_dir = "uploads/vouchers"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = f"{upload_dir}/{installment_id}_{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Update installment
    await db.execute(
        "UPDATE installments SET voucher_url = $1 WHERE id = $2",
        file_path, installment_id
    )
    
    return {"message": "Voucher subido correctamente", "path": file_path}

async def get_pending_payments(db: asyncpg.Connection):
    payments = await db.fetch(
        """SELECT i.*, pp.enrollment_id, e.student_id,
                  s.first_name, s.last_name, s.dni
           FROM installments i
           JOIN payment_plans pp ON i.payment_plan_id = pp.id
           JOIN enrollments e ON pp.enrollment_id = e.id
           JOIN students s ON e.student_id = s.id
           WHERE i.voucher_url IS NOT NULL AND i.status = 'pending'
           ORDER BY i.due_date"""
    )
    return [dict(p) for p in payments]

async def approve_payment(installment_id: int, db: asyncpg.Connection):
    # Check if installment exists
    installment = await db.fetchrow("SELECT id FROM installments WHERE id = $1", installment_id)
    if not installment:
        return None
    
    await db.execute(
        "UPDATE installments SET status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE id = $1",
        installment_id
    )
    
    return {"message": "Pago aprobado correctamente"}

async def reject_payment(installment_id: int, db: asyncpg.Connection):
    await db.execute(
        "UPDATE installments SET status = 'pending', voucher_url = NULL WHERE id = $1",
        installment_id
    )
    return {"message": "Pago rechazado"}
