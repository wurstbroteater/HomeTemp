from core.monitoring import PrometheusManager


manager1 = PrometheusManager("hometemp")
manager2 = PrometheusManager()

assert manager1 is manager2  # check singleton