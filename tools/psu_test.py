from instruments import SPD3303C
import time


with SPD3303C() as psu:

    print(psu.identify())

    print("Setting 3.0 V")
    psu.set_voltage(1, 3.0)
    time.sleep(2)

    print("Setting 4.0 V")
    psu.set_voltage(1, 4.0)
    time.sleep(2)

    print("Setting 5.0 V")
    psu.set_voltage(1, 5.0)
    time.sleep(2)

    print("Done")