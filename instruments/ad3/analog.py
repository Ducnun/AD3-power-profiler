from dataclasses import dataclass

import numpy as np
import time


@dataclass
class AnalogCapture:
    """
    Result of an analog acquisition.

    samples:
        Dictionary mapping channel number to numpy array.

    sample_rate:
        Actual requested sample rate in samples/second.

    """

    samples: dict[int, np.ndarray]
    sample_rate: float

    @property
    def sample_count(self):
        if not self.samples:
            return 0

        return len(next(iter(self.samples.values())))

    @property
    def duration(self):
        if self.sample_rate <= 0:
            return 0.0

        return self.sample_count / self.sample_rate

    @property
    def time(self):
        return np.arange(
            self.sample_count,
            dtype=float,
        ) / self.sample_rate

    def channel(self, channel):
        return self.samples[channel]


class AnalogInput:
    """
    Wrapper around the AD3 oscilloscope/analog input.
    """

    def __init__(self, analog_input):
        self._scope = analog_input

    # ------------------------------------------------------------------
    # Channel configuration
    # ------------------------------------------------------------------

    def setup_channel(
        self,
        channel,
        range=5.0,
        offset=0.0,
    ):
        """
        Configure an analog input channel.

        channel:
            Zero-based channel number.

        range:
            Input voltage range.

        offset:
            Input offset.
        """

        self._scope[channel].setup(
            range=range,
            offset=offset,
        )

    # ------------------------------------------------------------------
    # Single acquisition
    # ------------------------------------------------------------------

    def capture(
        self,
        channels,
        sample_rate,
        sample_count,
        *,
        range: float = 25.0,
        offset: float = 0.0,
        settle=0.1,
    ):
        channels = list(channels)

        for channel in channels:
            self.setup_channel(channel, range=range, offset=offset)

        time.sleep(settle)

        self._scope.single(
            sample_rate=sample_rate,
            buffer_size=sample_count,
            configure=True,
            start=True,
        )

        samples = {}

        for channel in channels:
            samples[channel] = np.asarray(
                self._scope[channel].get_data()
            )

        return AnalogCapture(
            samples=samples,
            sample_rate=sample_rate,
        )
