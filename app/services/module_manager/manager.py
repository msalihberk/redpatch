import json
from pathlib import Path


class ModuleManager:
    def __init__(self, modules_directory="modules"):
        self.modules_directory = self.get_modules_path(modules_directory)
        self._module_index = {}
        self._submodule_index = {}
        self.discover_modules()

    def get_modules_path(self, modules_directory):
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

    def is_module_exist(self, module_name):
        return bool(module_name) and module_name.strip().upper() in self._module_index

    def is_submodule_exist(self, submodule_name, module_name=None):
        if not submodule_name:
            return False
        entry = self._submodule_index.get(submodule_name.strip().upper())
        return bool(entry) and (not module_name or entry["main"] == module_name.strip().upper())

    def discover_modules(self):
        self._module_index.clear()
        self._submodule_index.clear()
        modules_path = Path(self.modules_directory)
        if not modules_path.is_dir():
            return

        for module_folder in modules_path.iterdir():
            if not module_folder.is_dir():
                continue

            config = self._load_json(module_folder / "config.json")
            name = str(config.get("name", "")).strip().upper()
            submodules = config.get("sub_modules", [])
            if not name or not isinstance(submodules, list) or name in self._module_index:
                continue

            valid_submodules = []
            for submodule in submodules:
                if not isinstance(submodule, dict):
                    continue
                submodule_name = str(submodule.get("name", "")).strip().upper()
                runtime = str(submodule.get("runtime", "")).strip()
                entrypoint = str(submodule.get("entrypoint", "")).strip()
                codes = submodule.get("codes", {})
                try:
                    internal_port = int(submodule.get("internal_port", 0))
                except (TypeError, ValueError):
                    internal_port = 0

                if (
                    not submodule_name
                    or submodule_name in self._submodule_index
                    or not runtime
                    or not entrypoint
                    or not internal_port
                    or not isinstance(codes, dict)
                ):
                    continue

                submodule_folder = module_folder / "submodules" / submodule_name
                self._submodule_index[submodule_name] = {
                    "main": name,
                    "submodule_description": str(submodule.get("description", "")).strip(),
                    "submodule_name": submodule_name,
                    "submodule_folder": submodule_folder,
                    "codes": codes,
                    "runtime": runtime,
                    "entrypoint": entrypoint,
                    "internal_port": internal_port,
                }
                valid_submodules.append(submodule)

            self._module_index[name] = {
                "description": str(config.get("description", "")).strip(),
                "module_folder": module_folder,
                "submodules": valid_submodules,
            }

    def list_modules(self):
        return sorted((name, entry["description"]) for name, entry in self._module_index.items())

    def list_submodules(self):
        return sorted(
            (name, entry["submodule_description"])
            for name, entry in self._submodule_index.items()
        )

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
