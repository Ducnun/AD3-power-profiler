class WaveGenerator:

    def __init__(self, analog_output):
        self._output = analog_output

    def start(
        self,
        channel,
        waveform,
        *,
        frequency=1000,
        amplitude=1.0,
        offset=0.0,
    ):
        """
        Start a waveform.

        channel:
            Zero-based WaveGen channel.

        waveform:
            e.g. "sine", "square", "triangle".
        """

        self._output[channel].setup(
            waveform,
            frequency=frequency,
            amplitude=amplitude,
            offset=offset,
            start=True,
        )

    def stop(self, channel):
        self._output[channel].stop()
