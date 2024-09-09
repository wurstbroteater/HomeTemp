from gpiozero import CPUTemperature


# ----------------------------------------------------------------------------------------------------------------
# Module for utility methods not only related to one module of sensors.
# ----------------------------------------------------------------------------------------------------------------

def get_temperature():
    cpu = CPUTemperature()
    return float(cpu.temperature)
