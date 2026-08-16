import os
import shutil
import time
import pathlib
import tempfile
import docker
from docker.errors import NotFound, APIError


class DockerService:
    def __init__(
        self,
        port: int,
        path: str,
        entrypoint: str,
        runtime: str,
        container_name: str | None = None,
        session_id: str | None = None,
    ):
        self.client = docker.from_env()
        self.internal_port = port
        self.original_path = pathlib.Path(path).resolve()
        self.entrypoint = entrypoint
        self.runtime = runtime
        self.session_id = session_id or "default"

        self.container_name = (
            container_name
            or f"redpatch_{entrypoint.replace('.py', '').lower()}"
        )

        # Isolated temporary workspace for each session (portable temp dir)
        base_tmp = pathlib.Path(tempfile.gettempdir())
        self.work_dir = base_tmp / f"redpatch_sessions" / f"{self.session_id}_{self.original_path.name}"

        self.container = None
        self.mapped_host_port = None

    @staticmethod
    def get_container(container_name: str):
        try:
            client = docker.from_env()
            container = client.containers.get(container_name)
            container.reload()
            return container
        except Exception:
            return None

    @staticmethod
    def get_container_port(container_name: str, internal_port: int) -> int | None:
        container = DockerService.get_container(container_name)
        if not container:
            return None

        try:
            container.reload()
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            port_bindings = ports.get(f"{internal_port}/tcp")
            if port_bindings and len(port_bindings) > 0:
                return int(port_bindings[0]["HostPort"])
            return None
        except Exception:
            return None

    def _prepare_workspace(self, force_reset: bool = False) -> None:
        """Copies the original source code to the isolated temporary workspace."""
        if force_reset and self.work_dir.exists():
            shutil.rmtree(self.work_dir)

        if not self.work_dir.exists():
            shutil.copytree(self.original_path, self.work_dir)

    def remove_workspace(self) -> None:
        """Removes the isolated temporary workspace."""
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)

    def set_exist(self):
        existing = DockerService.get_container(self.container_name)
        if existing:
            self.container = existing
            self.mapped_host_port = self._resolve_mapped_port()

    def start(self, force_reset: bool = False) -> int:
        existing = DockerService.get_container(self.container_name)
        if existing and not force_reset:
            if existing.status == "running":
                self.container = existing
                self.mapped_host_port = self._resolve_mapped_port()
                return self.mapped_host_port
            else:
                self._force_cleanup(existing)
        elif existing and force_reset:
            self._force_cleanup(existing)

        self._prepare_workspace(force_reset=force_reset)

        module_name = self.entrypoint.replace(".py", "")
        start_command = (
            f"sh -c 'if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi && "
            f"exec uvicorn {module_name}:app --host 0.0.0.0 --port {self.internal_port} --reload'"
        )

        self.container = self.client.containers.run(
            image=self.runtime,
            name=self.container_name,
            command=start_command,
            working_dir="/app",
            volumes={
                str(self.work_dir.resolve()): {
                    "bind": "/app",
                    "mode": "rw",
                }
            },
            ports={f"{self.internal_port}/tcp": None},
            detach=True,
            network_mode="bridge",
        )
        self.mapped_host_port = self._resolve_mapped_port()
        return self.mapped_host_port

    def reset_lab(self) -> int:
        """Resets the lab environment by stopping the container, purging the temp directory, and restarting."""
        self.stop()
        return self.start(force_reset=True)

    def patch_code(self, relative_filepath: str, content: str) -> bool:
        """Writes updated code content directly to the isolated workspace."""
        try:
            self._prepare_workspace()
            target_file = (self.work_dir / relative_filepath).resolve()
            target_file.relative_to(self.work_dir.resolve())
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(content, encoding="utf-8")
            return True
        except (OSError, ValueError):
            return False

    def _resolve_mapped_port(self) -> int:
        if not self.container:
            raise RuntimeError("Cannot resolve port: Container reference is missing.")

        retries = 10
        while retries > 0:
            self.container.reload()
            ports = self.container.attrs.get("NetworkSettings", {}).get("Ports", {})
            port_bindings = ports.get(f"{self.internal_port}/tcp")

            if port_bindings and len(port_bindings) > 0:
                return int(port_bindings[0]["HostPort"])

            time.sleep(0.5)
            retries -= 1

        raise RuntimeError(
            f"Failed to resolve mapped host port for container '{self.container_name}'."
        )

    def _force_cleanup(self, container_obj) -> None:
        try:
            container_obj.kill()
        except APIError:
            pass

        try:
            container_obj.remove(force=True)
        except APIError:
            pass

    def stop(self) -> None:
        target = self.container or DockerService.get_container(self.container_name)
        if target:
            try:
                target.reload()
                target.stop(timeout=1)
            except APIError:
                pass

            self._force_cleanup(target)
            self.container = None
            self.mapped_host_port = None

    @staticmethod
    def cleanup_all_redpatch_containers() -> None:
        """Stops and removes all containers matching the 'redpatch_' prefix and cleans temp directories."""
        try:
            client = docker.from_env()
            containers = client.containers.list(all=True, filters={"name": "redpatch_"})
            for container in containers:
                try:
                    container.kill()
                except Exception:
                    pass
                try:
                    container.remove(force=True)
                except Exception:
                    pass
        except Exception:
            pass

        base_tmp = pathlib.Path(tempfile.gettempdir())
        sessions_dir = base_tmp / "redpatch_sessions"
        if sessions_dir.exists():
            shutil.rmtree(sessions_dir, ignore_errors=True)

    @staticmethod
    def get_work_dir_for(session_id: str, original_path: str) -> pathlib.Path:
        """Return the expected session work directory for a given original path and session id.

        This is a helper to allow other components to read session-specific copies
        without instantiating a full DockerService.
        """
        base_tmp = pathlib.Path(tempfile.gettempdir())
        original_name = pathlib.Path(original_path).resolve().name
        return base_tmp / "redpatch_sessions" / f"{session_id}_{original_name}"
