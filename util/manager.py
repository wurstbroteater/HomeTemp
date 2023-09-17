import docker
from docker import errors as de
from util.utilities_logger import util_logger as log


class DockerManager:
    """
    Provides methods for primitive docker container handling.
    This class should be extended for the purpose of specifying a certain image instance.
    """

    def __init__(self):
        self.client = docker.from_env()

    def container_exists(self, container_name):
        try:
            self.client.containers.get(container_name)
            return True
        except de.NotFound:
            return False

    def start_container(self, container_name):
        try:
            container = self.client.containers.get(container_name)
            container.start()
            log.info(f"Container {container_name} started successfully.")
            return True
        except de.NotFound:
            log.error(f"Container {container_name} not found.")
            return False
        except de.APIError as e:
            log.error(f"Error starting container {container_name}: {e}")
            return False

    def is_container_running(self, container_name):
        try:
            container = self.client.containers.get(container_name)
            return container.status == "running"
        except de.NotFound:
            return False


class PostgresDockerManager(DockerManager):
    """
    Extends DockerManager for image postgres:latest and adds methods for postgres image pulling, environment variables,
    port bindings and postgres container creation.
    """

    def __init__(self, db_name, user, password, port_range=["5432:5432"]):
        self.image_name = "postgres:latest"
        self.db_name = db_name
        self.port_range = self._create_port_bindings(port_range)
        self.user = user
        self.password = password
        super().__init__()

    @staticmethod
    def _create_port_bindings(ports=None):
        # Format: list(str("host_port:container_port"))
        port_bindings = {}
        if ports:
            for port in ports:
                host_port, container_port = port.split(":")
                port_bindings[int(container_port)] = int(host_port)
        else:
            log.warning("Port bindings are empty!")
        return port_bindings

    def _create_environment_variables(self):
        return {
            "POSTGRES_USER": self.user,
            "POSTGRES_PASSWORD": self.password,
            "POSTGRES_DB": self.db_name
        }

    def pull_postgres_image(self):
        try:
            self.client.images.pull(self.image_name)
            return True
        except de.APIError as e:
            log.error(f"Error pulling image {self.image_name}: {e}")
            return False

    def create_postgres_container(self, container_name):
        if not self.container_exists(container_name):
            try:
                self.client.containers.run(
                    image=self.image_name,
                    name=container_name,
                    detach=True,
                    environment=self._create_environment_variables(),
                    ports=self.port_range
                )
                log.info(f"Container {container_name} created successfully.")
            except de.APIError as e:
                log.error(f"Error creating container {container_name}: {e}")
        else:
            log.info(f"Container {container_name} already exists.")
