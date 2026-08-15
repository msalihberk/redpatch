import os
import json

class ModuleManager:
    """Discover and manage cyber-security modules stored under a '/app/modules/' folder.

    Each subfolder of `modules/` must contain a `config.json` with the keys:
    {"name": "SQL Injection", "description": "...", "sub_modules": [...]}

    """

    def __init__(self, modules_directory="modules"):
        self.modules_directory = self.get_modules_path(modules_directory)
        self._module_index = {}
        self._submodule_index = {}
        self.discover_modules()

    def get_modules_path(self, modules_directory):
        PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
        return os.path.join(PROJECT_ROOT, modules_directory)

    def is_module_exist(self, module_name):
        if not module_name:
            return False
        if module_name in self._module_index:
            return True
        return False

    def is_submodule_exist(self, module_name):
        if not module_name:
            return False
        if module_name in self._module_index:
            return True
        return False

    def discover_modules(self):
        """Scan the modules directory and populate the internal index.

        Missing or malformed modules are skipped silently to keep output tight.
        """
        self._module_index.clear()
        if not os.path.isdir(self.modules_directory):
            return

        for entry in os.listdir(self.modules_directory):
            entry_path = os.path.join(self.modules_directory, entry)
            if not os.path.isdir(entry_path):
                continue

            config_path = os.path.join(entry_path, "config.json")
            if not os.path.isfile(config_path):
                continue

            try:
                with open(config_path, "r", encoding="utf-8") as fh:
                    config = json.load(fh)
                name = str(config.get("name", "")).strip().upper()
                description = str(config.get("description", "")).strip()
                sub_modules = config.get("sub_modules", [])

                for sub_module in sub_modules:
                    sub_module_name = str(sub_module.get("name", "")).strip().upper()
                    sub_module_description = str(sub_module.get("description", "")).strip()

                    if not sub_module_name:
                        continue

                    runtime = str(sub_module.get("runtime", "")).strip()
                    entrypoint = str(sub_module.get("entrypoint", "")).strip()
                    internal_port = int(sub_module.get("internal_port", 0))

                    codes = sub_module.get("codes", {})
                    if not codes or not runtime or not entrypoint or not internal_port:
                        continue

                    if sub_module_name in self._submodule_index:
                        raise Exception(f"Submodule {sub_module_name} already exists")

                    self._submodule_index[sub_module_name] = {
                        "main" : name,
                        "submodule_description": sub_module_description,
                        "submodule_name": sub_module_name,
                        "codes": codes,
                        "runtime": runtime,
                        "entrypoint": entrypoint,
                        "internal_port": internal_port,
                    }

                if name in self._module_index:
                    raise Exception(f"Module {name} already exists")

                self._module_index[name] = {
                    "description": description,
                    "module_folder": entry_path,
                    "submodules": sub_modules,
                }
            except Exception as e:
                print(f"Error in module manager: {e}")
                continue

    def list_modules(self):
        """Return a list of (name, description) tuples sorted by command."""
        return sorted(((k, v.get("description", "")) for k, v in self._module_index.items()), key=lambda x: x[0])

    def list_submodules(self):
        """Return a list of (name, description) tuples sorted by command."""
        return sorted(((k, v.get("description", "")) for k, v in self._submodule_index.items()), key=lambda x: x[0])

    def get_module_entry(self, module_name):
        """Return a module entry dict."""
        if not module_name:
            return None
        module_name = module_name.strip().upper()
        entry = self._module_index.get(module_name)
        if not entry:
            return None
        return {
            "description": entry.get("description", ""),
            "module_folder": entry.get("module_folder"),
            "submodules": entry.get("submodules", []),
        }

    def get_submodule_entry(self, submodule_name):
        """Return a submodule entry dict."""
        if not submodule_name:
            return None
        submodule_name = submodule_name.strip().upper()
        entry = self._submodule_index.get(submodule_name)
        if not entry:
            return None
        return {
            "main" : entry.get("main", ""),
            "submodule_description": entry.get("submodule_description", ""),
            "submodule_name": entry.get("submodule_name", ""),
            "codes": entry.get("codes", {}),
            "runtime": entry.get("runtime", ""),
            "entrypoint": entry.get("entrypoint", ""),
            "internal_port": entry.get("internal_port", 0),
        }

    def get_module_entries(self):
        """Return all discovered module entries as a list of dicts."""
        return [self.get_module_entry(command) for command, _ in self.list_modules()]

    def get_submodule_entries(self):
        """Return all discovered submodule entries as a list of dicts."""
        return [self.get_submodule_entry(command) for command, _ in self.list_submodules()]
