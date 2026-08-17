import os

class DockerHelper:
    @staticmethod
    def is_running_in_docker() -> bool:
        if os.path.exists('/.dockerenv'):
            return True

        try:
            with open('/proc/1/cgroup', 'rt') as f:
                content = f.read()
                if 'docker' in content or 'containerd' in content:
                    return True
        except Exception:
            pass

        return False
