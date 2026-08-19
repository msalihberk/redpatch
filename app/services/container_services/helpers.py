import os

class DockerHelper:
    @staticmethod
    def is_running_in_docker() -> bool:
        return os.getenv('IS_DOCKER') == 'true'

    @staticmethod
    def is_image_loaded(image_tag: str) -> bool:
        import docker
        try:
            docker.from_env().images.get(image_tag)
            return True
        except Exception:
            return False
