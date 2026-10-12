from dataclasses import dataclass

import numpy as np


@dataclass
class DigitalCapture:
    samples: np.ndarray
    sample_rate: float

    @property
    def sample_count(self):
        return len(self.samples)

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

    def pin(self, pin):
        return (
            (self.samples >> pin) & 1
        ).astype(bool)

    def bit(self, pin):
        return self.pin(pin)


class DigitalInput:

    def __init__(self, digital_input):
        self._logic = digital_input

    def capture(
        self,
        sample_rate,
        sample_count,
    ):
        samples = self._logic.single(
            sample_rate=sample_rate,
            buffer_size=sample_count,
            configure=True,
            start=True,
        )

        return DigitalCapture(
            samples=np.asarray(samples),
            sample_rate=sample_rate,
        )

    def record(
        self,
        sample_rate,
        sample_count,
    ):
        recorder = self._logic.record(
            sample_rate=sample_rate,
            sample_count=sample_count,
            configure=True,
            start=True,
        )

        return DigitalCapture(
            samples=np.asarray(recorder.data_samples),
            sample_rate=sample_rate,
        )

    def wait_for_activity(
        self,
        sample_rate,
        sample_count,
        pins=None,
    ):
        """
        Repeatedly perform short captures until activity is
        detected on one or more specified pins.

        Returns the capture containing the activity.
        """

        if pins is None:
            mask = None
        else:
            mask = 0

            for pin in pins:
                mask |= 1 << pin

        while True:
            capture = self.capture(
                sample_rate=sample_rate,
                sample_count=sample_count,
            )

            samples = capture.samples

            if mask is not None:
                samples = samples & mask

            if np.any(samples[1:] != samples[:-1]):
                return capture
