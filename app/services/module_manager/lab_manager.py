import json
import io
import os
import shutil
import tarfile
from pathlib import Path
from app.core.config import Settings
import requests

class LabManager:
    def __init__(self, labs_dir:str="labs", manifest_file:str = "manifest.json"):
        self.labs_directory = LabManager.get_labs_path(labs_dir)
        self.manifest = manifest_file
        self.modules = {}
        self.discover()

    @staticmethod
    def get_labs_path(modules_directory):
        return Path(__file__).resolve().parents[2] / modules_directory

    @staticmethod
    def _load_json(path):
        try:
            with Path(path).open(encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _read_file(path):
        try:
            return Path(path).read_text(encoding="utf-8")
        except OSError:
            return ""

    @staticmethod
    def _relative_file_path(base_path, filename):
        matches = list(Path(base_path).rglob(filename))
        if len(matches) != 1 or not matches[0].is_file():
            return None
        return matches[0].relative_to(base_path)

    @staticmethod
    def ensure_archive_dir() -> Path:
        archive_dir = Path(Settings.ARCHIVE_DIR)
        archive_dir.mkdir(parents=True, exist_ok=True)
        return archive_dir

    def get_lab_info(self, module: str, lab_id: str):
        module_entry = self.modules.get(module)
        if not module_entry:
            return None
        for lab in module_entry.get("submodules", []):
            if lab.get("id") == lab_id:
                return {**lab, "module": module}
        return None

    def archive_path(self, lab: dict) -> Path:
        return self.ensure_archive_dir() / f"{lab['id']}.tar.gz"

    def workspace_source_path(self, lab: dict) -> Path:
        return self.ensure_archive_dir() / "workspaces" / lab["id"]

    def extract_lab_workspace(self, lab: dict) -> Path:
        """Extract the image package's /app source tree once for DockerService workspaces."""
        destination = self.workspace_source_path(lab)
        if (destination / "main.py").is_file():
            return destination

        temporary = destination.with_name(f"{destination.name}.part")
        shutil.rmtree(temporary, ignore_errors=True)
        try:
            import docker
            container = docker.from_env().containers.create(lab["image_tag"])
            try:
                stream, _ = container.get_archive("/app")
                archive_data = b"".join(stream)
            finally:
                container.remove(force=True)

            with tarfile.open(fileobj=io.BytesIO(archive_data)) as tar:
                tar.extractall(temporary, filter="data")
            extracted_app = temporary / "app"
            if not (extracted_app / "main.py").is_file():
                raise RuntimeError("The lab image does not contain an /app/main.py workspace.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.rmtree(destination, ignore_errors=True)
            extracted_app.replace(destination)
        except (OSError, tarfile.TarError, Exception) as exc:
            shutil.rmtree(temporary, ignore_errors=True)
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(f"Lab workspace extraction failed: {exc}") from exc
        finally:
            shutil.rmtree(temporary, ignore_errors=True)
        return destination

    def download_lab(self, module: str, lab_id: str) -> tuple[dict, Path, bool]:
        """Stream a package once into the local cache; never retain partial files."""
        lab = self.get_lab_info(module, lab_id)
        if not lab:
            raise ValueError("Lab not found in manifest")
        archive = self.archive_path(lab)
        if archive.is_file() and archive.stat().st_size > 0:
            return lab, archive, False

        temporary = archive.with_suffix(".part")
        temporary.unlink(missing_ok=True)
        try:
            with requests.get(lab["download_url"], stream=True, timeout=(10, 300)) as response:
                response.raise_for_status()
                with temporary.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            file.write(chunk)
            temporary.replace(archive)
        except requests.RequestException as exc:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"Lab archive download failed: {exc}") from exc
        return lab, archive, True

    def is_module_exist(self, module_name):
        return bool(module_name) and module_name in self.modules

    def is_submodule_exist(self, submodule_name, module_name=None):
        return bool(module_name and self.get_lab_info(module_name, submodule_name))

    def discover(self):
        self.modules.clear()
        manifest = self._load_json(self.labs_directory / self.manifest)
        for module, entry in manifest.get("labs", {}).items():
            if isinstance(entry, dict) and isinstance(entry.get("submodules"), list):
                self.modules[module] = entry

    def list_modules(self):
        return sorted((name, entry["description"]) for name, entry in self.modules.items())

    def get_submodules(self, main:str):
        if main not in self.modules:
            raise ValueError("Invalid module name")

        return [{**lab, "module": main} for lab in self.modules[main]["submodules"]]

    def get_workspace_files(self, module_name, submodule_name, workspace_path=None):
        """Return editable files, hints, and configured solutions for one submodule."""
        lab = self.get_lab_info(module_name, submodule_name)
        if not lab:
            return None

        source_path = self.workspace_source_path(lab)
        if not source_path.is_dir():
            return {"vulnerables": {}, "solutions": {}, "hints": {}}

        active_path = Path(workspace_path) if workspace_path else source_path
        config = self._load_json(source_path / "config.json")

        configured_hints = config.get("hints", {})
        configured_solutions = config.get("solutions", {})
        configured_targets = config.get("targets", {})

        if not isinstance(configured_hints, dict):
            configured_hints = {}
        if not isinstance(configured_solutions, dict):
            configured_solutions = {}
        if not isinstance(configured_targets, dict):
            configured_targets = {}

        vulnerables, hints, solutions, target_paths = {}, {}, {}, {}

        for filename, configured_path in configured_targets.items():
            if not isinstance(filename, str) or not isinstance(configured_path, str):
                continue
            relative_path = Path(configured_path)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                continue
            source_file = (source_path / relative_path).resolve()
            try:
                source_file.relative_to(source_path.resolve())
            except ValueError:
                continue
            if not source_file.is_file():
                continue

            target_paths[filename] = relative_path.as_posix()
            active_file = active_path / relative_path
            vulnerables[filename] = self._read_file(
                active_file if active_file.is_file() else source_file
            )

            file_hints = configured_hints.get(filename, [])
            if isinstance(file_hints, list):
                hints[filename] = [hint for hint in file_hints if isinstance(hint, str)]

        for sol_key, sol_rel_path in configured_solutions.items():
            if not isinstance(sol_key, str) or not isinstance(sol_rel_path, str):
                continue

            rel_path = Path(sol_rel_path)
            if rel_path.is_absolute() or ".." in rel_path.parts:
                continue

            source_sol_file = (source_path / rel_path).resolve()
            try:
                source_sol_file.relative_to(source_path.resolve())
            except ValueError:
                continue

            active_sol_file = active_path / rel_path
            final_sol_file = active_sol_file if active_sol_file.is_file() else source_sol_file

            if final_sol_file.is_file():
                solutions[sol_key] = self._read_file(final_sol_file)

        return {
            "vulnerables": vulnerables,
            "solutions": solutions,
            "hints": hints,
            "target_paths": target_paths,
        }

    def get_routes_from_submodule(self, submodule_name: str, module_name:str) -> str:
        if not submodule_name:
            return ""

        if not self.is_submodule_exist(submodule_name, module_name):
            raise ValueError("Invalid submodule name")

        main_py = os.path.join(self.labs_directory, "archives/workspaces", submodule_name, "main.py")

        if not os.path.exists(main_py) or not os.path.isfile(main_py):
            raise ValueError("Invalid main python file")

        routes = []

        with open(main_py) as file:
            for line in file.readlines():
                stripped = line.strip()
                if stripped.startswith("@app.") or stripped.startswith("async def "):
                    routes.append(stripped)

        return "\n".join(routes)

