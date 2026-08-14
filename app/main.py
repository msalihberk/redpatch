import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.ai.ai_agent import RedTeamAgent
from app.services.module_manager.manager import ModuleManager

app = FastAPI(title="RedPatch")
templates = Jinja2Templates(directory="app/templates")
agent = RedTeamAgent()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/modules", response_class=HTMLResponse)
async def get_modules(request: Request, mode: str = None):
    module_mngr = ModuleManager()
    return templates.TemplateResponse(request, "modules.html", {"modules": module_mngr.list_modules(), "mode": mode})

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
