from ..engine import Config


def receiver(period=434):
    return Config(frame="falling", frame_pin=2, rx_pin=2, sample="timer",
                  transmit=False, lsb_first=True, period=period,
                  validate_start=True, validate_stop=True)
