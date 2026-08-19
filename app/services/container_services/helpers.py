import os

class DockerHelper:
    @staticmethod
    def is_running_in_docker() -> bool:
        return os.getenv('IS_DOCKER') == 'true'
