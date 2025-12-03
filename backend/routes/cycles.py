from fastapi import APIRouter, Depends, HTTPException, status
from models.cycle import CycleCreate, CycleUpdate
from middleware.auth import require_role
from config.database import get_db
import asyncpg

router = APIRouter(prefix="/cycles", tags=["cycles"])

@router.post("", dependencies=[Depends(require_role(["admin"]))], status_code=status.HTTP_201_CREATED)
async def create_cycle(cycle: CycleCreate, db: asyncpg.Connection = Depends(get_db)):
    result = await db.fetchrow(
        """INSERT INTO cycles (name, start_date, end_date, duration_months, status)
           VALUES ($1, $2, $3, $4, $5) RETURNING id""",
        cycle.name, cycle.start_date, cycle.end_date, cycle.duration_months, cycle.status
    )
    return {"id": result['id'], "message": "Ciclo creado correctamente"}

@router.get("")
async def get_all_cycles(db: asyncpg.Connection = Depends(get_db)):
    cycles = await db.fetch("SELECT id, name, start_date, end_date, duration_months, status FROM cycles")
    return [dict(c) for c in cycles]

@router.get("/{cycle_id}")
async def get_cycle(cycle_id: int, db: asyncpg.Connection = Depends(get_db)):
    cycle = await db.fetchrow(
        "SELECT id, name, start_date, end_date, duration_months, status FROM cycles WHERE id = $1",
        cycle_id
    )
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo no encontrado")
    return dict(cycle)

@router.put("/{cycle_id}", dependencies=[Depends(require_role(["admin"]))])
async def update_cycle(cycle_id: int, cycle: CycleUpdate, db: asyncpg.Connection = Depends(get_db)):
    fields = []
    values = []
    idx = 1
    
    for field, value in cycle.dict(exclude_unset=True).items():
        fields.append(f"{field} = ${idx}")
        values.append(value)
        idx += 1
    
    if not fields:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    values.append(cycle_id)
    query = f"UPDATE cycles SET {', '.join(fields)} WHERE id = ${idx}"
    
    await db.execute(query, *values)
    return {"message": "Ciclo actualizado correctamente"}

@router.delete("/{cycle_id}", dependencies=[Depends(require_role(["admin"]))])
async def delete_cycle(cycle_id: int, db: asyncpg.Connection = Depends(get_db)):
    await db.execute("DELETE FROM cycles WHERE id = $1", cycle_id)
    return {"message": "Ciclo eliminado correctamente"}
