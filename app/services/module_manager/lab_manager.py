import json
import os
from pathlib import Path
from app.core.config import Settings
import requests

class LabManager:
    def __init__(self, labs_dir:str="labs", manifest_file:str = "official_manifest.json"):
        self.labs_directory = self.get_labs_path(labs_dir)
        self.manifest = manifest_file
        self.modules = {}
        self.discover()

    def get_labs_path(self, modules_directory):
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
    def ensure_archive_dir():
        if not os.path.exists(Settings.ARCHIVE_DIR):
            os.makedirs(Settings.ARCHIVE_DIR)

    def get_lab_info(self, module:str, id:str):
        for lab in self.modules[module]["submodules"]:
            if lab["id"] == id:
                return lab
        return None

    def download_lab(self, module:str, id:str):
        LabManager.ensure_archive_dir()
        lab = self.get_lab_info(module, id)

        tar_path = os.path.join(Settings.ARCHIVE_DIR, f"{lab['id']}.tar.gz")
        image_tag = lab["image_tag"]
        download_url = lab["download_url"]

        if not os.path.exists(tar_path):
            print(f"[+] Lab downloading... : {download_url}")
            response = requests.get(download_url, stream=True)

            if response.status_code == 200:
                with open(tar_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"[✔] Lab saved : {tar_path}")
            else:
                raise Exception(f"Error, HTTP Code : {response.status_code}")
        else:
            print(f"[+] Lab is already exist : {tar_path}")

        print(f"[+] Docker load...")
        # TODO: Add docker logic
        # with open(tar_path, "rb") as f:
        #     client.images.load(f.read())

        print(f"[✔] The image has been successfully transferred to Docker : {image_tag}")





    def is_module_exist(self, module_name):
        return bool(module_name) and module_name.strip().upper() in self._module_index

    def is_submodule_exist(self, submodule_name, module_name=None):
        if not submodule_name:
            return False
        entry = self._submodule_index.get(submodule_name.strip().upper())
        return bool(entry) and (not module_name or entry["main"] == module_name.strip().upper())

    def discover(self):
        self.modules.clear()
        manifest = self._load_json(self.labs_directory / self.manifest)
        for module in manifest.get("labs", {}):
            self.modules[module] = manifest.get("labs", {})[module]

        print(self.modules)

    def list_modules(self):
        return sorted((name, entry["description"]) for name, entry in self.modules.items())

    def get_submodules(self, main:str):
        if not self.modules[main]:
            raise ValueError("Invalid module name")

        return self.modules[main]["submodules"]

    def get_module_entry(self, module_name):
        if not self.is_module_exist(module_name):
            return None
        entry = self._module_index[module_name.strip().upper()]
        return {**entry}

    def get_submodule_entry(self, submodule_name):
        if not self.is_submodule_exist(submodule_name):
            return None
        return {**self._submodule_index[submodule_name.strip().upper()]}

    def get_module_entries(self):
        return [self.get_module_entry(name) for name, _ in self.list_modules()]

    def get_submodule_entries(self):
        return [self.get_submodule_entry(name) for name, _ in self.list_submodules()]

    def get_workspace_files(self, module_name, submodule_name, workspace_path=None):
        """Return editable files, hints, and configured solutions for one submodule."""
        if not self.is_submodule_exist(submodule_name, module_name):
            return None

        entry = self.get_submodule_entry(submodule_name)
        source_path = Path(entry["submodule_folder"])
        active_path = Path(workspace_path) if workspace_path else source_path
        config = self._load_json(source_path / "config.json")
        configured_hints = config.get("hints", {})
        configured_solutions = config.get("solutions", {})
        if not isinstance(configured_hints, dict):
            configured_hints = {}
        if not isinstance(configured_solutions, dict):
            configured_solutions = {}

        vulnerables, hints, solutions = {}, {}, {}
        for filename, kind in entry["codes"].items():
            entry_type = kind.get("type", "") if isinstance(kind, dict) else kind
            if str(entry_type).lower() not in {"vulnerable", "vulnerables", "vuln"}:
                continue

            relative_path = self._relative_file_path(source_path, filename)
            if relative_path is None:
                continue
            active_file = active_path / relative_path
            vulnerables[filename] = self._read_file(
                active_file if active_file.is_file() else source_path / relative_path
            )

            file_hints = configured_hints.get(filename, [])
            if isinstance(file_hints, list):
                hints[filename] = [hint for hint in file_hints if isinstance(hint, str)]

            solution_path = configured_solutions.get(filename)
            if not isinstance(solution_path, str) or not solution_path:
                continue
            candidate = (source_path / solution_path).resolve()
            try:
                candidate.relative_to(source_path.resolve())
            except ValueError:
                continue
            if candidate.is_file():
                solutions[filename] = self._read_file(candidate)

        return {"vulnerables": vulnerables, "solutions": solutions, "hints": hints}

