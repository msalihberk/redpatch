# Copyright (C) 2026  Mustafa Salih Berk
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import uuid
import logging
import base64
import json

import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.responses import RedirectResponse

from app.services.ai.ai_agent import RedTeamAgent
from app.services.container_services.docker import DockerService
from app.services.module_manager.lab_manager import LabManager
from app.services.container_services.helpers import DockerHelper
from app.core.config import settings

from pydantic import BaseModel, Field
from pathlib import Path

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
    # DockerService.cleanup_all_redpatch_containers()
    pass
app = FastAPI(title="RedPatch", lifespan=lifespan)
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

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


def get_manifest_lab(module: str, lab_id: str) -> dict:
    lab = LabManager().get_lab_info(module, lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found in manifest")
    try:
        lab["port"] = int(lab["port"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Lab manifest has an invalid port") from exc
    if not lab.get("image_tag") or not lab.get("download_url"):
        raise HTTPException(status_code=500, detail="Lab manifest is incomplete")
    return lab


def manifest_docker_service(lab: dict, session_id: str, source_path: Path | None = None) -> DockerService:
    return DockerService(
        port=lab["port"], path=source_path, entrypoint="main.py" if source_path else None, runtime=lab["image_tag"],
        container_name=f"redpatch_{lab['module']}_{lab['id']}", session_id=session_id,
    )

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


@app.get("/documentation/contributing", response_class=HTMLResponse)
async def contributing_guide(request: Request):
    return templates.TemplateResponse(request, "documentation.html")

@app.api_route("/change-settings", methods=["GET", "POST"])
async def change_settings(
        request: Request,
        llm_provider: str = Form(None),
        api_key: str = Form(None),
        model: str = Form(None)
    ):
    if request.method == "POST":
        config_data = {
            "LLM_PROVIDER": llm_provider,
            "API_KEY": api_key,
            "MODEL": model
        }
        settings.set_options(config_data)
    return templates.TemplateResponse(request, "settings.html", settings.get_options())

@app.get("/modules", response_class=HTMLResponse)
async def get_modules(request: Request, action: str = None, module: str = None, mode: str = None):
    lab_mngr = LabManager()
    if action == "submodules" and not lab_mngr.is_module_exist(module):
        raise HTTPException(status_code=404, detail="Module not found in manifest")
    submodules = lab_mngr.get_submodules(module) if action == "submodules" else None
    return templates.TemplateResponse(request, "modules.html", {"modules": lab_mngr.list_modules(), "mode": mode, "module": module, "action": action, "submodules": submodules})


@app.get("/api/labs/manifest")
async def labs_manifest():
    """Expose the manifest-backed lab catalogue without local implementation paths."""
    manager = LabManager()
    return {"labs": manager.modules}

@app.get("/workspace", response_class=HTMLResponse)
async def workspace(request: Request, module: str = None, submodule: str = None, mode: str = None):
    if not module or not submodule:
        raise HTTPException(status_code=404, detail="Module or submodule not specified")
    lab = get_manifest_lab(module, submodule)
    manager = LabManager()
    source_path = manager.workspace_source_path(lab)
    work_dir = DockerService.get_work_dir_for(get_session_id(request), source_path)
    codes = manager.get_workspace_files(module, submodule, work_dir)
    return templates.TemplateResponse(request, "workspace.html", {"module": module, "submodule": submodule, "mode": mode, "codes": codes})

@app.get("/api/{module}/{lab_id}/lab-data")
async def get_lab_data(module: str, lab_id: str):
    return JSONResponse(
        status_code=200,
        content={
            "data" : LabManager().get_workspace_files(module, lab_id)
        }
    )

@app.get("/api/check_flag/{module}/{lab_id}/{flag}")
async def check_flag(module: str, lab_id: str, flag: str):
    if not module or not lab_id or not flag:
        raise HTTPException(status_code=404, detail="Module or submodule not specified")

    lab_mngr = LabManager()

    if not lab_mngr.is_module_exist(module) or not lab_mngr.is_submodule_exist(lab_id, module):
        raise HTTPException(status_code=404, detail="Module or submodule not exist")

    return JSONResponse(
        status_code=200,
        content={
            "is_correct": lab_mngr.check_flag(module, lab_id, flag)
        }
    )

@app.post("/api/workspace/ai-analysis")
async def ai_analysis(payload: AIAnalysisRequest):
    module, submodule, code = payload.module, payload.submodule, payload.code
    lab_mngr = LabManager()
    if not module or not submodule:
        raise HTTPException(status_code=404, detail="Module or submodule not specified")
    if not lab_mngr.is_module_exist(module) or not lab_mngr.is_submodule_exist(submodule, module):
        raise HTTPException(status_code=404, detail="Module or submodule not found")

    vulnerability_type = f"{module}_{submodule}"
    internal_port = lab_mngr.get_lab_info(module, submodule).get("port")
    container_port = DockerService.get_container_port(
        f"redpatch_{module}_{submodule}", internal_port
    )
    lab_link = (
        f"http://localhost:{container_port}/"
        if container_port
        else "The lab is not currently running; analyze the code and routes only."
    )
    routes = lab_mngr.get_routes_from_submodule(submodule, module)

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


@app.post("/api/labs/{module}/{lab_id}/launch")
async def launch_lab(request: Request, module: str, lab_id: str):
    lab = get_manifest_lab(module, lab_id)
    manager = LabManager()
    try:
        _, archive, downloaded = await run_in_threadpool(manager.download_lab, module, lab_id)
        loaded = await run_in_threadpool(DockerService.load_lab_image, lab, archive)
        source_path = await run_in_threadpool(manager.extract_lab_workspace, lab)
        port = await run_in_threadpool(
            manifest_docker_service(lab, get_session_id(request), source_path).start
        )
    except RuntimeError as exc:
        logger.warning("Lab launch failed for %s/%s: %s", module, lab_id, exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "success", "downloaded": downloaded, "loaded": loaded, "port": port}


@app.post("/api/labs/{module}/{lab_id}/download")
async def download_lab(module: str, lab_id: str):
    get_manifest_lab(module, lab_id)
    try:
        _, _, downloaded = await run_in_threadpool(LabManager().download_lab, module, lab_id)
    except RuntimeError as exc:
        logger.warning("Lab download failed for %s/%s: %s", module, lab_id, exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "status": "success",
        "downloaded": downloaded,
        "message": "Lab archive downloaded." if downloaded else "Lab archive is already cached.",
    }


@app.post("/api/labs/{module}/{lab_id}/reset")
async def reset_lab(request: Request, module: str, lab_id: str):
    """Remove the active lab session; the user explicitly starts the next session."""
    lab = get_manifest_lab(module, lab_id)
    if not await run_in_threadpool(DockerHelper.is_image_loaded, lab["image_tag"]):
        raise HTTPException(status_code=409, detail="Lab image is not loaded yet. Launch the lab first.")
    source_path = LabManager().workspace_source_path(lab)
    docker_service = manifest_docker_service(lab, get_session_id(request), source_path)
    await run_in_threadpool(docker_service.stop)
    await run_in_threadpool(docker_service.remove_workspace)
    return {"status": "success", "message": f"Lab '{lab_id}' was reset. Start it when you are ready."}

@app.get("/api/labs/{lab_id}/is_downloaded")
async def is_downloaded(request: Request, lab_id: str):
    result = LabManager().is_lab_downloaded(lab_id)
    return {"is_downloaded": result}

@app.delete("/api/labs/{lab_id}")
async def delete_lab(request: Request, lab_id: str):
    try:
        LabManager().delete_lab_file(lab_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/workspace/reset")
async def workspace_reset(request: Request, module: str = None, submodule: str = None):
    if not module or not submodule:
        raise HTTPException(status_code=404, detail="Module or submodule not specified")
    return await reset_lab(request, module, submodule)

@app.api_route("/proxy/{module}/{submodule}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@app.api_route("/proxy/{module}/{submodule}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_submodule(module: str, submodule: str, request: Request, path: str = ""):
    lab = get_manifest_lab(module, submodule)
    internal_port = lab["port"]
    container_name = f"redpatch_{module}_{submodule}"
    container_port = DockerService.get_container_port(container_name, internal_port)

    if not container_port:
        raise HTTPException(
            status_code=409,
            detail=f"'{submodule}' is not active. Launch it through the manifest endpoint first."
        )

    requested_method = request.query_params.get("_redpatch_method", request.method).upper()
    if requested_method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise HTTPException(status_code=405, detail="Unsupported proxy request method")

    if not path and not request.url.path.endswith("/"):
        redirect_url = str(request.url.replace(path=f"{request.url.path}/"))
        return RedirectResponse(url=redirect_url, status_code=307)

    clean_path = path.lstrip("/")

    if DockerHelper.is_running_in_docker():
        base_target = f"http://{container_name}:{internal_port}"
    else:
        base_target = f"http://127.0.0.1:{container_port}"

    if clean_path:
        target_url = f"{base_target}/{clean_path}"
    else:
        target_url = f"{base_target}/"

    control_params = {"_redpatch_method", "_redpatch_headers", "_redpatch_json_body"}
    query_params = [
        (key, value)
        for key, value in request.query_params.multi_items()
        if key not in control_params
    ]

    def decode_proxy_metadata(parameter_name: str):
        encoded_value = request.query_params.get(parameter_name)
        if not encoded_value:
            return None
        try:
            padding = "=" * (-len(encoded_value) % 4)
            return json.loads(base64.b64decode(encoded_value + padding).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid {parameter_name} metadata") from exc

    async with httpx.AsyncClient(follow_redirects=True) as client:
        body = await request.body()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

        exploit_headers = decode_proxy_metadata("_redpatch_headers")
        if exploit_headers is not None:
            if not isinstance(exploit_headers, dict):
                raise HTTPException(status_code=400, detail="Invalid exploit request headers")
            blocked_headers = {"host", "content-length", "cookie", "connection", "transfer-encoding"}
            for name, value in exploit_headers.items():
                normalized_name = str(name).lower()
                normalized_value = str(value)
                if (
                        normalized_name in blocked_headers
                        or "\r" in str(name)
                        or "\n" in str(name)
                        or "\r" in normalized_value
                        or "\n" in normalized_value
                ):
                    continue
                headers[str(name)] = normalized_value

        json_body = decode_proxy_metadata("_redpatch_json_body")
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            headers["content-type"] = "application/json"

        try:
            resp = await client.request(
                method=requested_method,
                url=target_url,
                headers=headers,
                params=query_params,
                content=body,
                timeout=10.0
            )

            response_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() not in ("content-length", "transfer-encoding", "content-encoding")
            }

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=response_headers
            )
        except (httpx.HTTPError, Exception):
            return Response(
                content=f'{{"status": "starting"}}',
                status_code=200,
                headers={
                    "content-type": "application/json",
                    "X-Container-Status": "starting"
                }
            )

@app.post("/api/workspace/patch")
async def workspace_patch(request: Request, payload: PatchRequest):
    session_id = get_session_id(request)
    lab = get_manifest_lab(payload.module, payload.submodule)
    manager = LabManager()
    source_path = manager.workspace_source_path(lab)
    if not source_path.is_dir():
        raise HTTPException(status_code=409, detail="Lab workspace is not prepared yet. Launch the lab first.")

    docker_service = manifest_docker_service(lab, session_id, source_path)
    workspace_files = manager.get_workspace_files(payload.module, payload.submodule)
    target_paths = workspace_files.get("target_paths", {})
    allowed_filenames = set(target_paths)
    if payload.filename not in allowed_filenames:
        raise HTTPException(
            status_code=400,
            detail=f"Target file '{payload.filename}' is not allowed to be modified.",
        )

    patched = docker_service.patch_code(target_paths[payload.filename], payload.code)

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
