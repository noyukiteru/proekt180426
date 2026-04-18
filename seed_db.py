import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from core.database import engine, Base, async_session
from core.models import Service, Master, User

async def seed_database():
    print("Подключение к базе данных...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as db:
        result = await db.execute(select(Service))
        if result.scalars().first():
            print("База уже содержит услуги. Пропускаем заполнение.")
            return
        
        print("Добавляем услуги...")
        services = [
            Service(title="Шиномонтаж", price=1500.0, duration_min=40),
            Service(title="Балансировка колёс", price=800.0, duration_min=20),
            Service(title="Замена масла", price=1200.0, duration_min=30),
            Service(title="Диагностика подвески", price=500.0, duration_min=15),
        ]
        db.add_all(services)
        await db.commit()
        
        print("Добавляем мастеров (с графиком)...")
        masters = [
            Master(name="Иван Петров", specialization="Шиномонтаж", is_active=True, schedule="Пн-Пт: 09:00-18:00"),
            Master(name="Алексей Сидоров", specialization="Балансировка", is_active=True, schedule="Пн-Сб: 10:00-19:00"),
            Master(name="Дмитрий Козлов", specialization="Диагностика", is_active=True, schedule="Пн-Пт: 08:00-20:00"),
        ]
        db.add_all(masters)
        await db.commit()
        
        print("База данных успешно заполнена!")
        print(f"   - Услуг: {len(services)}")
        print(f"   - Мастеров: {len(masters)}")

if __name__ == "__main__":
    asyncio.run(seed_database())