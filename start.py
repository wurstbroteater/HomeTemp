import argparse
import uvicorn
from threading import Thread
from typing import Optional, Type
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from core.core_configuration import get_instance_name, initialize, FileManager
from core.core_log import setup_logging
from core.instance import BaseTemp, CoreSkeleton, get_supported_instance_type
from core.monitoring import PrometheusManager
from endpoint.instance import SUPPORTED_INSTANCES, FetchTemp

setup_logging()
app = FastAPI()

# Expose Prometheus metrics
@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/trigger")
async def grafana_method_trigger(method: Optional[str] = None) -> None:
    #param e.g., http://localhost:8800/trigger?method=hello_from_grafana
    instance: CoreSkeleton = getattr(app.state, "instance", None)
    if instance is None:
        print("ERROR:app Instance not initialized")
        return None
    elif method is None:
        print("WARN:app Grafna trigger did not specify method")
        return None
    elif str(method).lower()  == 'take_picture':
        if isinstance(instance, BaseTemp):
            print("INFO:app Grafana trigger taking new picture")
            i: BaseTemp = instance
            i.take_picture_commanded(None)
        else:
            print("WARN:app Grafana trigger requested new picture but instance is not BaseTemp")
        return None
    elif str(method).lower()  == 'check_commands':
        print("INFO:app Grafana trigger checking commands")
        instance.run_received_commands()
        return None
    elif str(method).lower() == 'trigger_sensor':
        print("INFO:app Grafana trigger pulling data from sensor")
        # this data wont be saved to database
        room_temp, humidity = instance.collect_data()
        if room_temp is not None and humidity is not None:
            print("INFO:app Grafana trigger pulled data from sensor: Room={0:f}*C, Humidity={1:f}%".format(room_temp, humidity))
        else:
            print("WARN:app Grafana trigger pulled NONE data from sensor")
        return None
    print(f"WARN:app Grafna trigger receceived unknown method trigger: {method}")
    return None



def start_fastapi(instance_name: str, port: int) -> None:
    """Start FastAPI server in a separate thread."""
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


def init(port:int, instance_name: Optional[str] = None):
    # Ensure PrometheusManager singleton is initialized
    prom_manager = PrometheusManager(instance_name) if instance_name else None
    fm: FileManager = initialize()
    instance_type: Optional[Type[CoreSkeleton]] = None

    if instance_name is None:
        fm.root_data_structure()
        instance_name = get_instance_name()
        # Ensure PrometheusManager singleton is initialized
        prom_manager = PrometheusManager(instance_name)
        instance_type = get_supported_instance_type(instance_name)

    elif instance_name.lower() == SUPPORTED_INSTANCES[0].lower():
        instance_type = FetchTemp

    # Start FastAPI thread
    fastapi_thread = Thread(target=start_fastapi, args=(instance_name, port), daemon=True)
    fastapi_thread.start()

    if instance_type is not None:
        instance: CoreSkeleton = instance_type(instance_name)
        # Store in FastAPI app state and access with getattr(app.state, "instance", None)
        app.state.instance = instance
        instance.start()
        print("INFO: Shutting down...")
        instance.shutdown()
        print("INFO: Goodbye!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start an instance with an optional instance name.")
    parser.add_argument("--instance", type=str, help="Optional instance name to start")
    parser.add_argument("--port", type=int, help="Port for FastAPI")
    args = parser.parse_args()

    init(args.port, instance_name=args.instance)