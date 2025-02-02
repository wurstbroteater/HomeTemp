from core.core_configuration import get_instance_name, load_config
from core.core_log import setup_logging
from core.instance import get_supported_instance_type


def init():
    load_config()
    instance_name = get_instance_name()
    setup_logging(log_file=f"{instance_name}.log")
    instance_type = get_supported_instance_type(instance_name)
    instance = instance_type(instance_name)
    instance.start()


if __name__ == "__main__":
    init()
