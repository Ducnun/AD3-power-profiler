import numpy as np

from instruments import AD3

with AD3() as ad3:

    capture = ad3.analog.capture(
        channels=[0],
        sample_rate=10_000,
        sample_count=1_000,
        range=10.0
    )

    voltage = capture.channel(0)

    print(f"Min:  {np.min(voltage):.6f} V")
    print(f"Max:  {np.max(voltage):.6f} V")
    print(f"Mean: {np.mean(voltage):.6f} V")
