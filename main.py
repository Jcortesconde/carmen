from reproducer import Reproducer
import subprocess
from protocol import IdentityProtocol

import pyaudio
import time


def thread_reproduce(reproducer, protocol, signal):
    encoded_signal = protocol.encode(signal)
    melody_time = reproducer.get_time(encoded_signal)
    time.sleep(1)  # tyhere seems to be a half a second mute recording on the listener
    reproducer.send_info(encoded_signal)
    time.sleep(melody_time + 1)
    return encoded_signal


def thread_listen(listener, protocol, duration, filename):
    encoded_signal = listener.listen_and_extract(duration, filename)
    signal = protocol.decode(encoded_signal)
    return signal

if __name__ == '__main__':
    signals = {
        'noname_signal': b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF',
        'noname2_signal': b'\xFF\x7F\x3F\x1F\x0F\x07\x03',
        'noname3_signal': b'\xFF\x00\xFF\x00\xFF\x00\xFF',
        'noname4_signal': b'\xAA\xAA\xAA\xAA\xAA\xAA\xAA',
        'noname5_signal': b'\xAA\x55\xAA\x55\xAA\x55\xAA'
    }
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
    for name, signal in signals.items():

        encoded_signal = protocol.encode(signal)
        reproducer = Reproducer(starting_freq, jumps, bits, pulse_duration, silence_duration)
        melody_time = reproducer.get_time(encoded_signal)  # In seconds

        listen_time = int(melody_time) + 3  # we add three seconds to be sure we hear all the message

        reproducer_string = 'python reproducer.py '+str(starting_freq)+' '+str(jumps)+' '+str(bits)
        reproducer_string += ' '+str(pulse_duration)+' '+str(silence_duration)+' '+ signal.hex()

        listener_string = 'python listener.py '+str(starting_freq)+' '+str(jumps)+' '+str(bits)
        listener_string += ' '+str(pulse_duration)+' '+str(silence_duration)+' '+str(listen_time)
        listener_string += ' --filename '+name +'_test_console.wav'
        ans = subprocess.run(listener_string+' & '+reproducer_string, shell=True, capture_output=True)
        hexy = str(ans.stdout).split()[1][:-3] #black magic to transform from b'' to string to real b'' we need
        info_retrieved = bytes.fromhex(hexy)
        #print(ans.stdout, info_retrieved) # To check conversion was done right
        print(signal, info_retrieved)
        true_signal = int.from_bytes(signal, byteorder='big')
        ones = int.from_bytes(b'\FF'*len(signal), byteorder='big')
        not_in_signal = true_signal ^ ones #xor operation
        retrieved_signal = int.from_bytes(info_retrieved, byteorder='big') #bytes does not have bitwise opreators very not nice
        wrongly_heard = not_in_signal & retrieved_signal
        correctly_heard = true_signal & retrieved_signal
        not_heard = true_signal ^ correctly_heard
        amount_of_ones = lambda num : bin(num).count('1')
        print('correctly heard', amount_of_ones(correctly_heard), 'not heard', amount_of_ones(not_heard), 'wrongly heard', amount_of_ones(wrongly_heard), 'total amount', 8*len(signal))
        #Dos tipos de errores, el de escuchar algo que no esta y el de no escuchar algo que esta
        #para ver el primero hago un xor entre la señal y todos unos, eso me da los apagados de la señal
        #si hago un xor con lo escuchado me quedan prendidos los que tendria que haber escuchado, eso xor con la señal y quedan los que faltan
        #para ver el primero con el