from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "dashboard" / "templates")

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin123":
        request.session["admin"] = True
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин или пароль"})

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

async def check_auth(request: Request):
    if not request.session.get("admin"):
        raise HTTPException(status_code=401, detail="Требуется авторизация")

@router.get("/dashboard")
async def dashboard(request: Request, auth=Depends(check_auth)):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/analytics")
async def analytics(request: Request, auth=Depends(check_auth)):
    return templates.TemplateResponse("analytics.html", {"request": request})