import os
import json

class ModuleManager:
    """Discover and manage cyber-security modules stored under a '/app/modules/' folder.

    Each subfolder of `modules/` must contain a `config.json` with the keys:
    {"name": "SQL Injection", "description": "...", "sub_modules": {}, "codes": {}, "solutions": {}}

    """

    def __init__(self, modules_directory="modules"):
        self.modules_directory = self.get_modules_path(modules_directory)
        self._module_index = {}
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
                sub_modules = config.get("sub_modules", {})

                # Submodule Config
                codes = sub_modules.get("codes", {})
                solutions = sub_modules.get("solutions", {})

                if not name or not sub_modules:
                    continue

                self._module_index[name] = {
                    "description": description,
                    "module_folder": entry_path,
                    "sub_modules": sub_modules,
                    "codes": codes,
                    "solutions": solutions,
                }
            except Exception as e:
                print(f"Error in module manager: {e}")
                continue

    def list_modules(self):
        """Return a list of (name, description) tuples sorted by command."""
        return sorted(((k, v.get("description", "")) for k, v in self._module_index.items()), key=lambda x: x[0])

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
            "sub_modules": entry.get("sub_modules", {}),
            "codes": entry.get("codes", {}),
            "solutions": entry.get("solutions", {}),
        }

    def get_module_entries(self):
        """Return all discovered module entries as a list of dicts."""
        return [self.get_module_entry(command) for command, _ in self.list_modules()]
