import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.ai.ai_agent import RedTeamAgent
from app.services.module_manager.manager import ModuleManager

app = FastAPI(title="RedPatch")
templates = Jinja2Templates(directory="app/templates")
agent = RedTeamAgent()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request,
        "error.html",
        {
            "request": request,
            "status_code": exc.status_code,
            "message": exc.detail
        },
        status_code=exc.status_code
    )

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/modules", response_class=HTMLResponse)
async def get_modules(request: Request, mode: str = None, module: str = None, action: str = None):
    module_mngr = ModuleManager()
    if not module and action == "submodules":
        raise HTTPException(status_code=404, detail="Module not found")
    if not module_mngr.is_module_exist(module):
        raise HTTPException(status_code=404, detail="Module not found")

    return templates.TemplateResponse(request, "modules.html", {"modules": module_mngr.list_modules(), "mode": mode, "module": module, "action": action})

@app.websocket("/ws/attack")
async def websocket_attack(websocket: WebSocket):
    await websocket.accept()
    try:
        code = await websocket.receive_text()

        await websocket.send_text("🔍 [SYSTEM] RedPatch Ajanı başlatıldı...")
        await asyncio.sleep(0.4)
        await websocket.send_text("🤖 [AI RED TEAM] Koddaki zafiyet vektörleri taranıyor...")

        result = await agent.run_attack(code)

        if result.vulnerability_found:
            await websocket.send_text(f"🚨 [ALERT] Zafiyet Tespiti: {result.vulnerability_type}")
            await websocket.send_text(f"📍 [LOCATION] Hedef Satır: {result.target_line}")
            await websocket.send_text(f"💣 [PAYLOAD] `{result.exploit_payload}`")
            await websocket.send_text(f"💥 [STATUS] Sızma Başarılı!")
            await websocket.send_text(f"📝 [DETAILS] {result.explanation}")
        else:
            await websocket.send_text("🛡️ [DEFENSE SUCCESS] Kod güvenli! RedPatch sızmayı başaramadı.")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(f"❌ [ERROR] Hata: {str(e)}")
