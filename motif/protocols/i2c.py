from ..engine import Config


def target(address=0x52, watchdog=0, ack_address=True, ack_data=True):
    return Config(frame="two_wire", clock_pin=1, rx_pin=2, tx_pin=2,
                  open_drain=6, exchange=True, address=address,
                  watchdog=watchdog, ack_address=ack_address, ack_data=ack_data)
