import os.path
import uuid

import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.ai.ai_agent import RedTeamAgent
from app.services.container_services.docker import DockerService
from app.services.module_manager.manager import ModuleManager
from pydantic import BaseModel


class PatchRequest(BaseModel):
    module: str
    submodule: str
    filename: str
    code: str

async def lifespan(app: FastAPI):
    yield
    DockerService.cleanup_all_redpatch_containers()
app = FastAPI(title="RedPatch", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")
agent = RedTeamAgent()

@app.middleware("http")
async def ensure_session_cookie(request: Request, call_next):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        request.state.session_id = session_id
        response = await call_next(request)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response

    request.state.session_id = session_id
    return await call_next(request)


def get_session_id(request: Request) -> str:
    return getattr(request.state, "session_id", request.cookies.get("session_id", "default"))

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
    if not submodule and not module and not module_mngr.is_submodule_exist(submodule) and not module_mngr.is_module_exist(module):
        raise HTTPException(status_code=404, detail="Submodule not found")
    runtime = module_mngr.get_submodule_entry(submodule).get("runtime")
    entrypoint = module_mngr.get_submodule_entry(submodule).get("entrypoint")
    internal_port = module_mngr.get_submodule_entry(submodule).get("internal_port")
    path = os.path.join(module_mngr.modules_directory, module, "submodules", submodule)
    if not runtime or not entrypoint or not internal_port or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Submodule configuration is incomplete")
    # Prefer session-specific temporary workspace copies when available so the editor
    # shows the current session's working files (changes applied there on 'Apply').
    session_id = get_session_id(request)
    tmp_workdir = DockerService.get_work_dir_for(session_id, path)

    codes = {}
    sub_entry = module_mngr.get_submodule_entry(submodule)
    for filename in sub_entry.get("codes", {}).keys():
        # check session temp copy first
        tmp_path = os.path.join(tmp_workdir, filename)
        orig_path = os.path.join(path, filename)
        if os.path.isfile(tmp_path):
            with open(tmp_path, "r", encoding="utf-8") as fh:
                codes[filename] = fh.read()
        elif os.path.isfile(orig_path):
            with open(orig_path, "r", encoding="utf-8") as fh:
                codes[filename] = fh.read()
        else:
            codes[filename] = ""
    return templates.TemplateResponse(request, "workspace.html", {"module": module, "submodule": submodule, "mode": mode, "codes": codes})


@app.api_route("/api/workspace/reset", methods=["POST"])
async def workspace_reset(request: Request, module: str = None, submodule: str = None):
    module_mngr = ModuleManager()
    if not submodule and not module and not module_mngr.is_submodule_exist(submodule):
        raise HTTPException(status_code=404, detail="Submodule not found")
    runtime = module_mngr.get_submodule_entry(submodule).get("runtime")
    entrypoint = module_mngr.get_submodule_entry(submodule).get("entrypoint")
    internal_port = module_mngr.get_submodule_entry(submodule).get("internal_port")
    path = os.path.join(module_mngr.modules_directory, module, "submodules", submodule)
    if not runtime or not entrypoint or not internal_port or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Submodule configuration is incomplete")

    container = DockerService.get_container(f"redpatch_{module}_{submodule}")
    if not container:
        raise HTTPException(status_code=404, detail="Submodule does not exist")

    try:
        container.stop(timeout=2)
    except Exception:
        pass
    container.remove(force=True)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": f"Lab '{submodule}' reset successfully."
        }
    )

@app.api_route("/proxy/{module}/{submodule}", methods=["GET", "POST", "PUT", "DELETE"])
@app.api_route("/proxy/{module}/{submodule}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_submodule(module: str, submodule: str, request: Request, path: str = ""):
    module_mngr = ModuleManager()
    runtime = module_mngr.get_submodule_entry(submodule).get("runtime")
    entrypoint = module_mngr.get_submodule_entry(submodule).get("entrypoint")
    internal_port = module_mngr.get_submodule_entry(submodule).get("internal_port")
    pth = os.path.join(module_mngr.modules_directory, module, "submodules", submodule)
    if not runtime or not entrypoint or not internal_port or not os.path.exists(pth):
        raise HTTPException(status_code=404, detail="Submodule configuration is incomplete")
    docker_service = DockerService(internal_port, pth, entrypoint, runtime, f"redpatch_{module}_{submodule}", get_session_id(request))
    container_port = docker_service.start()

    if not container_port:
        raise HTTPException(
            status_code=503,
            detail=f"'{submodule}' No active port was found. The container may not have started. "
        )

    target_url = f"http://127.0.0.1:{container_port}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    async with httpx.AsyncClient() as client:
        body = await request.body()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

        resp = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            timeout=10.0
        )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers)
        )

@app.post("/api/workspace/patch")
async def workspace_patch(request: Request, payload: PatchRequest):
    session_id = get_session_id(request)
    module_mngr = ModuleManager()

    if not module_mngr.is_module_exist(
        payload.module
    ) or not module_mngr.is_submodule_exist(payload.submodule):
        raise HTTPException(status_code=404, detail="Submodule not found")

    runtime = module_mngr.get_submodule_entry(payload.submodule).get("runtime")
    entrypoint = module_mngr.get_submodule_entry(payload.submodule).get(
        "entrypoint"
    )
    internal_port = module_mngr.get_submodule_entry(payload.submodule).get(
        "internal_port"
    )
    path = os.path.join(
        module_mngr.modules_directory,
        payload.module,
        "submodules",
        payload.submodule,
    )

    if not runtime or not entrypoint or not internal_port or not os.path.exists(path):
        raise HTTPException(
            status_code=404, detail="Submodule configuration is incomplete"
        )

    container_name = f"redpatch_{payload.module}_{payload.submodule}"

    docker_service = DockerService(
        port=internal_port,
        path=path,
        entrypoint=entrypoint,
        runtime=runtime,
        container_name=container_name,
        session_id=session_id,
    )

    # Validate that the filename is part of the declared submodule codes mapping.
    sub_entry = module_mngr.get_submodule_entry(payload.submodule)
    allowed_filenames = set(sub_entry.get("codes", {}).keys())
    if payload.filename not in allowed_filenames:
        raise HTTPException(
            status_code=400,
            detail=f"Target file '{payload.filename}' is not allowed to be modified.",
        )

    patched = docker_service.patch_code(payload.filename, payload.code)

    if not patched:
        raise HTTPException(
            status_code=400,
            detail=f"Target file '{payload.filename}' could not be patched or does not exist in workspace.",
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": f"File '{payload.filename}' patched successfully.",
        },
    )
