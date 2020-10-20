from reproducer import Reproducer
from listener import Listener
from protocol import IdentityProtocol
import concurrent.futures
import pyaudio
import time


def thread_reproduce(reproducer, protocol, signal):
    encoded_signal = protocol.encode(signal)
    melody_time = reproducer.get_time(encoded_signal)
    time.sleep(1) #tyhere seems to be a half a second mute recording on the listener
    reproducer.send_info(encoded_signal)
    time.sleep(melody_time+1)
    return encoded_signal

def thread_listen(listener, protocol, duration, filename):
    encoded_signal = listener.listen_and_extract(duration, filename)
    signal = protocol.decode(encoded_signal)
    return signal


if __name__ == '__main__':
    start_signal = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
    signal = b'\xFF\x7F\x3F\x1F\x07\x03\x01'
    starting_freq = 18500
    jumps = 200
    bits = 8
    pulse_duration = 100
    silence_duration = 100
    chunk = 1024
    fmat = pyaudio.paInt16
    channels = 1
    rate = 44100
    filename = 'test_futures1.wav'
    protocol = IdentityProtocol()

    encoded_signal = protocol.encode(signal)
    reproducer = Reproducer(starting_freq, jumps, bits, pulse_duration, silence_duration)
    melody_time = reproducer.get_time(encoded_signal)  # In seconds

    listen_time = melody_time + 2  # we add two seconds to be sure we hear all the message
    listener = Listener(chunk, fmat, channels, rate, starting_freq, jumps, bits, pulse_duration, silence_duration)
    with concurrent.futures.ProcessPoolExecutor() as executor:
        listen_future = executor.submit(thread_listen, listener, protocol, listen_time, filename)
        reproducer_future = executor.submit(thread_reproduce, reproducer, protocol, signal)
        enocoded_signal = reproducer_future.result()  # blocking
        recieved_signal = listen_future.result()
        print(encoded_signal, recieved_signal)
