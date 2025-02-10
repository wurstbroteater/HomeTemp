import argparse
from typing import Optional, Type
from core.core_configuration import get_instance_name, initialize, FileManager
from core.core_log import setup_logging
from core.instance import CoreSkeleton, get_supported_instance_type
from endpoint.instance import SUPPORTED_INSTANCES, FetchTemp


def init(instance_name: Optional[str] = None):
    setup_logging()
    fm: FileManager = initialize()
    instance_type: Optional[Type[CoreSkeleton]] = None

    if instance_name is None:
        fm.root_data_structure()
        instance_name = get_instance_name()
        instance_type = get_supported_instance_type(instance_name)

    elif instance_name.lower() == SUPPORTED_INSTANCES[0].lower():
        instance_type = FetchTemp

    if instance_type is not None:
        instance: CoreSkeleton = instance_type(instance_name)
        instance.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start an instance with an optional instance name.")
    parser.add_argument("--instance", type=str, help="Optional instance name to start")
    args = parser.parse_args()

    init(instance_name=args.instance)
