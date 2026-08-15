import docker

class DockerService:
    def __init__(self, port, path, entrypoint, runtime):
        self.client = docker.from_env()
        self.path = path
        self.port = port
        self.entrypoint = entrypoint
        self.runtime = runtime

        self.container = None

    def start(self):
        client = docker.from_env()

        container = client.containers.run(
            image=self.runtime,
            command=f"python /app/{self.entrypoint}",
            volumes={
                self.path: {
                    'bind': '/app',
                    'mode': 'rw'
                }
            },
            ports={f"{self.port}/tcp": None},
            detach=True,
            network_mode="bridge"
        )

        self.container = container
        self.container.start()

    def stop(self):
        if self.container:
            self.container.stop()
            self.container = None
