import asyncio
import os.path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.ai.ai_agent import RedTeamAgent
from app.services.module_manager.manager import ModuleManager
from app.services.container_services.docker import DockerService

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
async def get_modules(request: Request, action: str = None, module: str = None, mode: str = None):
    module_mngr = ModuleManager()
    if not module and action == "submodules":
        raise HTTPException(status_code=404, detail="Module not found")
    if not module_mngr.is_module_exist(module) and action == "submodules":
        raise HTTPException(status_code=404, detail="Module not exist")
    submodules = [
        sub for sub in module_mngr.get_submodule_entries()
        if sub and sub.get("main") == module
    ]
    return templates.TemplateResponse(request, "modules.html", {"modules": module_mngr.list_modules(), "mode": mode, "module": module, "action": action, "submodules": submodules})

@app.get("/workspace", response_class=HTMLResponse)
async def workspace(request: Request, module: str = None, submodule: str = None, mode: str = None):
    module_mngr = ModuleManager()
    if not submodule and module and not module_mngr.is_submodule_exist(submodule) and not module_mngr.is_module_exist(module):
        raise HTTPException(status_code=404, detail="Submodule not found")
    runtime = module_mngr.get_submodule_entry(submodule).get("runtime")
    entrypoint = module_mngr.get_submodule_entry(submodule).get("entrypoint")
    internal_port = module_mngr.get_submodule_entry(submodule).get("internal_port")
    path = os.path.join(module_mngr.modules_directory, module, "submodules", submodule)
    if not runtime or not entrypoint or not internal_port or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Submodule configuration is incomplete")
    docker_service = DockerService(internal_port, path, entrypoint, runtime)
    docker_service.start()
    codes = module_mngr.read_submodule(module, submodule)
    return templates.TemplateResponse(request, "workspace.html", {"module": module, "submodule": submodule, "mode": mode, "codes": codes})
