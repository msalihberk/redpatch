import time
import docker
from docker.errors import NotFound, APIError


class DockerService:
    def __init__(self, port: int, path: str, entrypoint: str, runtime: str, container_name: str | None = None):
        self.client = docker.from_env()
        self.internal_port = port
        self.path = path
        self.entrypoint = entrypoint
        self.runtime = runtime
        self.container_name = container_name or f"redpatch_{entrypoint.replace('.py', '').lower()}"

        self.container = None
        self.mapped_host_port = None

    @staticmethod
    def get_container(container_name: str):
        try:
            client = docker.from_env()
            container = client.containers.get(container_name)
            container.reload()
            return container
        except NotFound:
            return None

    def start(self) -> int:
        existing = DockerService.get_container(self.container_name)
        if existing:
            if existing.status == "running":
                self.container = existing
                self.mapped_host_port = self._resolve_mapped_port()
                return self.mapped_host_port
            else:
                self._force_cleanup(existing)

        start_command = (
            f"sh -c 'if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi && "
            f"exec python /app/{self.entrypoint}'"
        )

        self.container = self.client.containers.run(
            image=self.runtime,
            name=self.container_name,
            command=start_command,
            volumes={
                self.path: {
                    'bind': '/app',
                    'mode': 'rw'
                }
            },
            ports={f"{self.internal_port}/tcp": None},
            detach=True,
            network_mode="bridge"
        )
        self.mapped_host_port = self._resolve_mapped_port()
        return self.mapped_host_port

    def _resolve_mapped_port(self) -> int:
        if not self.container:
            raise RuntimeError("Cannot resolve port: Container reference is missing.")

        retries = 10
        while retries > 0:
            self.container.reload()
            ports = self.container.attrs.get('NetworkSettings', {}).get('Ports', {})
            port_bindings = ports.get(f"{self.internal_port}/tcp")

            if port_bindings and len(port_bindings) > 0:
                return int(port_bindings[0]['HostPort'])

            time.sleep(0.5)
            retries -= 1

        raise RuntimeError(f"Failed to resolve mapped host port for container '{self.container_name}'.")

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
    def cleanup_all_redpatch_containers():
        """Stops and removes all containers matching the 'redpatch_' prefix"""
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
