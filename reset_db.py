import asyncio
import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent))

from core.database import engine, Base
from core.models import User, Service, Master, Appointment, Review

async def reset_database():
    print("Сейчас будут УДАЛЕНЫ все данные из базы")
    print("Нажмите Y для подтверждения или любую другую клавишу для отмены:")
    
    print("Удаление всех таблиц...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("Создание новых таблиц...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("База данных очищена и пересоздана!")
    print("Теперь запустите: python seed_db.py")

if __name__ == "__main__":
    asyncio.run(reset_database())