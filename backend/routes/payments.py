from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from middleware.auth import require_role
from config.database import get_db
import asyncpg
import controllers.paymentController as paymentController

router = APIRouter(prefix="/payments", tags=["payments"])

@router.get("/plan/{enrollment_id}")
async def get_plan(enrollment_id: int, db: asyncpg.Connection = Depends(get_db)):
    plan = await paymentController.get_payment_plan(enrollment_id, db)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan de pago no encontrado")
    return plan

@router.get("/installments/{payment_plan_id}")
async def get_installments(payment_plan_id: int, db: asyncpg.Connection = Depends(get_db)):
    return await paymentController.get_installments(payment_plan_id, db)

@router.post("/upload-voucher/{installment_id}")
async def upload_voucher(
    installment_id: int,
    file: UploadFile = File(...),
    db: asyncpg.Connection = Depends(get_db)
):
    return await paymentController.upload_voucher(installment_id, file, db)

@router.get("/pending", dependencies=[Depends(require_role(["admin"]))])
async def get_pending(db: asyncpg.Connection = Depends(get_db)):
    return await paymentController.get_pending_payments(db)

@router.put("/approve/{installment_id}", dependencies=[Depends(require_role(["admin"]))])
async def approve(installment_id: int, db: asyncpg.Connection = Depends(get_db)):
    result = await paymentController.approve_payment(installment_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")
    return result

@router.put("/reject/{installment_id}", dependencies=[Depends(require_role(["admin"]))])
async def reject(installment_id: int, db: asyncpg.Connection = Depends(get_db)):
    return await paymentController.reject_payment(installment_id, db)
