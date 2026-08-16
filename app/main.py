import os.path
import uuid
import logging

import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.ai.ai_agent import RedTeamAgent
from app.services.container_services.docker import DockerService
from app.services.module_manager.manager import ModuleManager
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PatchRequest(BaseModel):
    module: str
    submodule: str
    filename: str
    code: str


class AIAnalysisRequest(BaseModel):
    module: str = Field(min_length=1, max_length=100)
    submodule: str = Field(min_length=1, max_length=100)
    code: str = Field(max_length=200_000)

async def lifespan(app: FastAPI):
    yield
    DockerService.cleanup_all_redpatch_containers()
app = FastAPI(title="RedPatch", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")
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
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
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
    if not module or not submodule:
        raise HTTPException(status_code=404, detail="Module or submodule not specified")

    if not module_mngr.is_module_exist(module) or not module_mngr.is_submodule_exist(submodule, module):
        raise HTTPException(status_code=404, detail="Submodule not found")

    sub_entry = module_mngr.get_submodule_entry(submodule)
    runtime = sub_entry.get("runtime")
    entrypoint = sub_entry.get("entrypoint")
    internal_port = sub_entry.get("internal_port")
    path = sub_entry["submodule_folder"]
    if not runtime or not entrypoint or not internal_port or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Submodule configuration is incomplete")
    session_id = get_session_id(request)
    tmp_workdir = DockerService.get_work_dir_for(session_id, path)
    files_bundle = module_mngr.get_workspace_files(module, submodule, tmp_workdir)
    return templates.TemplateResponse(request, "workspace.html", {"module": module, "submodule": submodule, "mode": mode, "codes": files_bundle})

@app.post("/api/workspace/ai-analysis")
async def ai_analysis(payload: AIAnalysisRequest):
    module, submodule, code = payload.module, payload.submodule, payload.code
    module_mngr = ModuleManager()
    if not module or not submodule:
        raise HTTPException(status_code=404, detail="Module or submodule not specified")
    if not module_mngr.is_module_exist(module) or not module_mngr.is_submodule_exist(submodule, module):
        raise HTTPException(status_code=404, detail="Module or submodule not found")

    vulnerability_type = f"{module}_{submodule}"
    internal_port = module_mngr.get_submodule_entry(submodule).get("internal_port")
    container_port = DockerService.get_container_port(
        f"redpatch_{module}_{submodule}", internal_port
    )
    lab_link = (
        f"http://localhost:{container_port}/"
        if container_port
        else "The lab is not currently running; analyze the code and routes only."
    )
    routes = module_mngr.get_routes_from_submodule(submodule)

    try:
        result = await RedTeamAgent().run_attack(code, vulnerability_type, routes, lab_link)
    except ValueError as e:
        logger.warning("AI analysis configuration or response error: %s", e)
        raise HTTPException(status_code=503, detail="AI analysis is unavailable. Check the API configuration.") from e
    except Exception as e:
        logger.exception("AI analysis provider request failed %s", e)
        raise HTTPException(status_code=502, detail="AI analysis provider request failed. Please try again later. And look at the logs for more details.") from e

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "vulnerability_analysis": result.model_dump()
        }
    )


@app.api_route("/api/workspace/reset", methods=["POST"])
async def workspace_reset(request: Request, module: str = None, submodule: str = None):
    module_mngr = ModuleManager()
    if not module or not submodule:
        raise HTTPException(status_code=404, detail="Module or submodule not specified")

    if not module_mngr.is_module_exist(module) or not module_mngr.is_submodule_exist(submodule, module):
        raise HTTPException(status_code=404, detail="Module or submodule not found")

    sub_entry = module_mngr.get_submodule_entry(submodule)
    runtime = sub_entry.get("runtime")
    entrypoint = sub_entry.get("entrypoint")
    internal_port = sub_entry.get("internal_port")
    path = sub_entry["submodule_folder"]
    if not runtime or not entrypoint or not internal_port or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Submodule configuration is incomplete")

    container = DockerService.get_container(f"redpatch_{module}_{submodule}")
    if not container:
        raise HTTPException(status_code=404, detail="Submodule does not exist")

    try:
        container.stop(timeout=2)
    except Exception:
        pass
    try:
        container.remove(force=True)
    except Exception as exc:
        logger.exception("Could not remove lab container %s", container.name)
        raise HTTPException(status_code=503, detail="The lab container could not be reset.") from exc

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
    if not module or not submodule:
        raise HTTPException(status_code=404, detail="Module or submodule not specified")

    if not module_mngr.is_module_exist(module) or not module_mngr.is_submodule_exist(submodule, module):
        raise HTTPException(status_code=404, detail="Submodule not found")

    sub_entry = module_mngr.get_submodule_entry(submodule)
    runtime = sub_entry.get("runtime")
    entrypoint = sub_entry.get("entrypoint")
    internal_port = sub_entry.get("internal_port")
    pth = sub_entry["submodule_folder"]
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


@app.get("/api/workspace/files")
async def workspace_files(request: Request, module: str = None, submodule: str = None):
    session_id = get_session_id(request)
    module_mngr = ModuleManager()

    if not module_mngr.is_module_exist(module) or not module_mngr.is_submodule_exist(submodule, module):
        raise HTTPException(status_code=404, detail="Submodule not found")

    sub_entry = module_mngr.get_submodule_entry(submodule)
    tmp_workdir = DockerService.get_work_dir_for(session_id, sub_entry["submodule_folder"])
    return JSONResponse(status_code=200, content=module_mngr.get_workspace_files(module, submodule, tmp_workdir))

@app.post("/api/workspace/patch")
async def workspace_patch(request: Request, payload: PatchRequest):
    session_id = get_session_id(request)
    module_mngr = ModuleManager()

    if not module_mngr.is_module_exist(
        payload.module
    ) or not module_mngr.is_submodule_exist(payload.submodule, payload.module):
        raise HTTPException(status_code=404, detail="Submodule not found")

    runtime = module_mngr.get_submodule_entry(payload.submodule).get("runtime")
    entrypoint = module_mngr.get_submodule_entry(payload.submodule).get(
        "entrypoint"
    )
    internal_port = module_mngr.get_submodule_entry(payload.submodule).get(
        "internal_port"
    )
    path = module_mngr.get_submodule_entry(payload.submodule)["submodule_folder"]

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

    # Resolve the relative path inside the submodule so we patch the correct nested file
    def find_relative_path(base_path: str, target_name: str) -> str | None:
        for root, dirs, files in os.walk(base_path):
            if target_name in files:
                return os.path.relpath(os.path.join(root, target_name), base_path)
        return None

    relpath = find_relative_path(path, payload.filename)
    target_rel = relpath or payload.filename

    patched = docker_service.patch_code(target_rel, payload.code)

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
