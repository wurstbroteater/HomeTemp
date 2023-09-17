from util.manager import PostgresDockerManager
import configparser

config = configparser.ConfigParser()
config.read('hometemp.ini')

if __name__ == "__main__":
    auth = config["db"]
    docker_manager = PostgresDockerManager(auth["db_name"], auth["db_user"], auth["db_pw"])
    container_name = auth["container_name"]
    print(docker_manager.container_exists(container_name))
    print(docker_manager.is_container_running(container_name))

    # print(docker_manager.start_container(container_name))
    # if not docker_manager.container_exists(container_name):
    #    if docker_manager.pull_postgres_image(postgres_image):
    #        docker_manager.create_postgres_container(container_name, postgres_image, postgres_environment)
    # else:
    #    print(f"Container {container_name} already exists.")
