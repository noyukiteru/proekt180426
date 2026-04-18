from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.models import Master

router = APIRouter(prefix="/api/masters", tags=["Masters"])

@router.get("/")
async def get_masters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Master))
    return result.scalars().all()

@router.post("/")
async def create_master(master_data: dict, db: AsyncSession = Depends(get_db)):
    new_master = Master(**master_data)
    db.add(new_master)
    await db.commit()
    await db.refresh(new_master)
    return new_master

@router.put("/{master_id}")
async def update_master(master_id: int, master_data: dict, db: AsyncSession = Depends(get_db)):
    master = await db.get(Master, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    for key, value in master_data.items():
        setattr(master, key, value)
    await db.commit()
    await db.refresh(master)
    return master

@router.delete("/{master_id}")
async def delete_master(master_id: int, db: AsyncSession = Depends(get_db)):
    master = await db.get(Master, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    await db.delete(master)
    await db.commit()
    return {"message": "Master deleted"}