from reproducer import Reproducer
from listener import Listener
from protocol import IdentityProtocol


if __name__ == '__main__':
    start_signal = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
    signal = b'\xFF\x7F\x3F\x1F\x07\x03\x01'
    starting_freq = 18500
    jumps = 200
    bits = 8
    pulse_duration = 100
    silence_duration = 100
    protocol = IdentityProtocol()

    reproducer = Reproducer(starting_freq, jumps, bits, pulse_duration, silence_duration)
    encoded_signal = protocol.encode(signal)
    reproducer.send_info(encoded_signal)