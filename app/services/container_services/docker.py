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
            existing = docker.from_env().containers.get(container_name)
            return existing
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
                existing.remove(force=True)

        start_command = (
            f"sh -c 'if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi && "
            f"python /app/{self.entrypoint}'"
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
        """Extracts the dynamically assigned host port from container settings."""
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

    def stop(self) -> None:
        """Stops and removes the running container."""
        if self.container:
            try:
                print("Stopping container...")
                self.container.stop()
                self.container.remove()
            except APIError:
                pass
            finally:
                self.container = None
                self.mapped_host_port = None
