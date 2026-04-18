import httpx
from typing import List, Dict, Any

BASE_URL = "http://127.0.0.1:8000/api"

async def get_services() -> List[Dict[str, Any]]:
    """Получить список всех услуг"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BASE_URL}/services/", timeout=10.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        print(f"❌ Ошибка при загрузке услуг: {e}")
        return []
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return []

async def get_masters() -> List[Dict[str, Any]]:
    """Получить список всех мастеров"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BASE_URL}/masters/", timeout=10.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        print(f"❌ Ошибка при загрузке мастеров: {e}")
        return []
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return []

async def create_appointment(user_id: int, master_id: int, service_id: int, date_time: str) -> Dict[str, Any]:
    """Создать запись"""
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "user_id": user_id,
                "master_id": master_id,
                "service_id": service_id,
                "date_time": date_time
            }
            resp = await client.post(f"{BASE_URL}/appointments/", json=payload, timeout=10.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise Exception("Это время уже занято! Выберите другое.")
        raise Exception(f"Ошибка сервера: {e.response.status_code}")
    except httpx.HTTPError as e:
        raise Exception(f"Ошибка соединения: {e}")
    except Exception as e:
        raise Exception(f"Неожиданная ошибка: {e}")

async def get_user_appointments(telegram_id: str) -> List[Dict[str, Any]]:
    """Получить все записи пользователя"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BASE_URL}/appointments/", timeout=10.0)
            resp.raise_for_status()
            all_apps = resp.json()
            # Фильтруем записи по telegram_id (в реальном проекте лучше делать фильтр на сервере)
            return [app for app in all_apps if str(app.get("user", {}).get("telegram_id")) == telegram_id]
    except httpx.HTTPError as e:
        print(f"❌ Ошибка при загрузке записей: {e}")
        return []
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return []

async def cancel_appointment(app_id: int) -> bool:
    """Отменить запись"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{BASE_URL}/appointments/{app_id}",
                json={"status": "cancelled"},
                timeout=10.0
            )
            resp.raise_for_status()
            return True
    except httpx.HTTPError as e:
        print(f"❌ Ошибка при отмене записи: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

async def reschedule_appointment(app_id: int, new_datetime: str) -> bool:
    """Перенести запись"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{BASE_URL}/appointments/{app_id}",
                json={"date_time": new_datetime},
                timeout=10.0
            )
            resp.raise_for_status()
            return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise Exception("Новое время занято!")
        return False
    except Exception as e:
        print(f"❌ Ошибка при переносе: {e}")
        return False

async def create_review(appointment_id: int, rating: int, comment: str) -> bool:
    """Оставить отзыв"""
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "appointment_id": appointment_id,
                "rating": rating,
                "comment": comment
            }
            resp = await client.post(f"{BASE_URL}/reviews/", json=payload, timeout=10.0)
            resp.raise_for_status()
            return True
    except httpx.HTTPError as e:
        print(f"❌ Ошибка при отправке отзыва: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False