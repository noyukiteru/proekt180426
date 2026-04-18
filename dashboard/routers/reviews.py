from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.models import Review

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])

@router.get("/")
async def get_reviews(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review))
    return result.scalars().all()

@router.post("/")
async def create_review(review_data: dict, db: AsyncSession = Depends(get_db)):
    new_review = Review(**review_data)
    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)
    return new_review