from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from core.database import engine, Base, async_session
from core.models import Service, Master
from sqlalchemy import select
from dashboard.routers import pages, users, masters, services, appointments, reviews

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="secret_key")

app.include_router(pages.router)
app.include_router(users.router)
app.include_router(masters.router)
app.include_router(services.router)
app.include_router(appointments.router)
app.include_router(reviews.router)

@app.on_event("startup")
async def startup():
    # 1. Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("[OK] Таблицы базы данных готовы.")

    # 2. ПРОВЕРЯЕМ И ДОБАВЛЯЕМ ДАННЫЕ, ЕСЛИ ПУСТО
    async with async_session() as db:
        result = await db.execute(select(Service))
        services = result.scalars().all()

        if len(services) == 0:
            print("База пуста! Добавляю тестовые данные...")
            
            # Добавляем Услуги
            db.add_all([
                Service(title="Шиномонтаж", price=1500.0, duration_min=40),
                Service(title="Балансировка", price=800.0, duration_min=20),
                Service(title="Замена масла", price=1200.0, duration_min=30),
                Service(title="Диагностика", price=500.0, duration_min=15)
            ])
            
            # Добавляем Мастеров
            db.add_all([
                Master(name="Иван Петров", specialization="Шиномонтаж", is_active=True),
                Master(name="Алексей Сидоров", specialization="Балансировка", is_active=True),
                Master(name="Дмитрий Козлов", specialization="Общий", is_active=True)
            ])
            
            await db.commit()
            print("Тестовые данные успешно добавлены!")
        else:
            print(f"В базе уже есть {len(services)} услуг. Данные не дублирую.")