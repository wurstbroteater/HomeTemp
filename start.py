import argparse
from typing import Optional
from core.core_configuration import get_instance_name, load_config
from core.core_log import setup_logging
from core.instance import CoreSkeleton, get_supported_instance_type
from endpoint.instance import SUPPORTED_INSTANCES, FetchTemp

def init(instance_name:Optional[str] = None):
    load_config()
    instance_type: Optional[CoreSkeleton]
    setup_logging()
    if instance_name is None:
        instance_name = get_instance_name()
        instance_type = get_supported_instance_type(instance_name)

    elif instance_name.lower() == SUPPORTED_INSTANCES[0].lower():
        instance_type = FetchTemp

    if instance_type is not None:
        instance:CoreSkeleton = instance_type(instance_name)
        instance.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start an instance with an optional instance name.")
    parser.add_argument("--instance", type=str, help="Optional instance name to start")
    args = parser.parse_args()
    
    init(instance_name=args.instance)
    init()
