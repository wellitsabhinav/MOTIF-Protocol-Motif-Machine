from ..engine import Config


def receiver(period=32):
    return Config(sample="timer", transmit=False, period=period)
