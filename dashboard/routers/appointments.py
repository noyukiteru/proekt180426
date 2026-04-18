from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from core.database import get_db
from core.models import Appointment, User, Master, Service
from datetime import datetime, timedelta
router = APIRouter(prefix="/api/appointments", tags=["Appointments"])

def parse_datetime(dt_str: str) -> datetime:
    """Парсинг строки даты в объект datetime"""
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

# ПОЛУЧЕНИЕ ВСЕХ ЗАПИСЕЙ
@router.get("/")  
async def get_appointments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Appointment))
    appointments = result.scalars().all()
    
    return [
        {
            "id": app.id,
            "user_id": app.user_id,
            "master_id": app.master_id,
            "service_id": app.service_id,
            "date_time": app.date_time,
            "status": app.status
        }
        for app in appointments
    ]

# СОЗДАНИЕ ЗАПИСИ
@router.post("/")
async def create_appointment(data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    required = ["user_id", "master_id", "service_id", "date_time"]
    for field in required:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Отсутствует поле: {field}")

    # Проверка существования связанных сущностей
    user = await db.get(User, data["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    master = await db.get(Master, data["master_id"])
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")

    service = await db.get(Service, data["service_id"])
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")

    # БИЗНЕС-ЛОГИКА
    try:
        requested_start = parse_datetime(data["date_time"])
        requested_end = requested_start + timedelta(minutes=service.duration_min)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD HH:MM")

    # Запрашиваем все записи этого мастера
    stmt = select(Appointment).where(Appointment.master_id == data["master_id"])
    result = await db.execute(stmt)
    existing_apps = result.scalars().all()

    for app in existing_apps:
        try:
            existing_start = parse_datetime(app.date_time)
            existing_service = await db.get(Service, app.service_id)
            existing_end = existing_start + timedelta(minutes=existing_service.duration_min)
            
            # Математическая проверка пересечения интервалов
            if requested_start < existing_end and requested_end > existing_start:
                raise HTTPException(status_code=409, detail="Это время уже занято у выбранного мастера!")
        except (ValueError, TypeError):
            continue  # Пропускаем записи с битой датой

    # Создание записи
    new_app = Appointment(
        user_id=data["user_id"],
        master_id=data["master_id"],
        service_id=data["service_id"],
        date_time=data["date_time"],
        status="pending"
    )
    db.add(new_app)
    await db.commit()
    await db.refresh(new_app)
    
    return {
        "id": new_app.id,
        "user_id": new_app.user_id,
        "master_id": new_app.master_id,
        "service_id": new_app.service_id,
        "date_time": new_app.date_time,
        "status": new_app.status
    }

# ОБНОВЛЕНИЕ СТАТУСА/ВРЕМЕНИ 
@router.put("/{appointment_id}")
async def update_appointment(appointment_id: int, data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    app = await db.get(Appointment, appointment_id)
    if not app:
        raise HTTPException(status_code=404, detail="Запись не найдена")
        
    if "status" in data:  # ← ИСПРАВЛЕНО
        app.status = data["status"]
    if "date_time" in data:
        try:
            parse_datetime(data["date_time"])
            app.date_time = data["date_time"]
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты")
            
    await db.commit()
    await db.refresh(app)
    
    return {
        "id": app.id,
        "status": app.status,
        "date_time": app.date_time
    }

# ОТМЕНА ЗАПИСИ
@router.delete("/{appointment_id}")
async def delete_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    app = await db.get(Appointment, appointment_id)
    if not app:
        raise HTTPException(status_code=404, detail="Запись не найдена")
        
    # Мягкое удаление через смену статуса (согласно отчёту)
    app.status = "cancelled"
    await db.commit()
    return {"message": f"Запись #{appointment_id} отменена"}

@router.get("/slots/")
async def get_available_slots(
    master_id: int, 
    service_id: int, 
    date: str, 
    db: AsyncSession = Depends(get_db)
):

    # Получаем длительность услуги
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    
    duration = service.duration_min
    

    work_start = datetime.strptime(f"{date} 09:00", "%Y-%m-%d %H:%M")
    work_end = datetime.strptime(f"{date} 18:00", "%Y-%m-%d %H:%M")
    
    # 3. Получаем занятые слоты этого мастера на эту дату
    stmt = select(Appointment).where(
        Appointment.master_id == master_id,
        Appointment.date_time.like(f"{date}%")
    )
    result = await db.execute(stmt)
    busy_appointments = result.scalars().all()
    
    # 4. Генерируем свободные слоты
    available_slots = []
    current_slot = work_start
    
    while current_slot + timedelta(minutes=duration) <= work_end:
        slot_end = current_slot + timedelta(minutes=duration)
        
        # Проверяем пересечение с занятыми записями
        is_busy = False
        for app in busy_appointments:
            # Парсим занятое время из БД
            try:
                busy_start = datetime.strptime(app.date_time, "%Y-%m-%d %H:%M")
                busy_end = busy_start + timedelta(minutes=service.duration_min) # Условно берем ту же длительность
                
                # Логика пересечения
                if current_slot < busy_end and slot_end > busy_start:
                    is_busy = True
                    break
            except:
                continue
        
        if not is_busy:
            available_slots.append(current_slot.strftime("%H:%M"))
            
        step = max(duration, 30) 
        current_slot += timedelta(minutes=step)
        
    return available_slots