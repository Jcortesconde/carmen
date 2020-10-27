from reproducer import Reproducer
import subprocess
from protocol import IdentityProtocol
import csv
import numpy as np

def generate_console_string(params):
    console_string = ''
    starting_freq = str(params['starting_freq'])
    jumps = str(params['jumps'])
    bits = str(params['bits'])
    pulse_duration = str(params['pulse_duration'])
    silence_duration = str(params['silence_duration'])
    signal = params['signal']
    listen_time = str(params['listen_time'])
    file_name = params['name']
    same_section = starting_freq + ' ' + jumps + ' ' + bits + ' ' + pulse_duration + ' ' + silence_duration + ' '
    reproducer_string = 'python reproducer.py ' + same_section + signal.hex()

    listener_string = 'python listener.py ' + same_section + listen_time + ' --filename ' + file_name + '.wav'
    listener_string += ' --magnitude_percentage ' + str(params['magnitude_percentage']) + ' --time_threshold ' + str(
        params['time_threshold']) + ' --center_error ' + str(params['center_error'])
    if params['both']:

        console_string = reproducer_string + ' & ' + listener_string
    else:
        listener_string += ' --extract'
        console_string = listener_string
    return console_string


def sending_and_retrieval(params):
    encoded_signal = protocol.encode(signal)
    reproducer = Reproducer(starting_freq, jumps, bits, pulse_duration, silence_duration)
    melody_time = reproducer.get_time(encoded_signal)  # In seconds

    params['melody_time'] = melody_time
    params['listen_time'] = int(melody_time) + 3  # we add three seconds to be sure we hear all the message
    console_string = generate_console_string(params)
    print(console_string)
    ans = subprocess.run(console_string, shell=True, capture_output=True)
    print(str(ans.stdout))
    if len(ans.stdout) != 0:
        hexy = str(ans.stdout).split()[1][:-3]  # black magic to transform from b'' to string to real b'' we need
        info_retrieved = bytes.fromhex(hexy)
        # print(ans.stdout, info_retrieved) # To check conversion was done right
        return info_retrieved
    else:
        return b''

def confusion_matrix(signal, info_retrieved):
    true_signal = int.from_bytes(signal, byteorder='big')
    ones = int.from_bytes(b'\xFF' * len(signal), byteorder='big')
    not_in_signal = true_signal ^ ones  # xor operation
    retrieved_signal = int.from_bytes(info_retrieved,
                                      byteorder='big')  # bytes does not have bitwise operators very not nice
    wrongly_heard = not_in_signal & retrieved_signal
    correctly_heard = true_signal & retrieved_signal
    not_heard = true_signal ^ correctly_heard
    amount_of_ones = lambda num: bin(num).count('1')
    confusion = {
        'True Positive': amount_of_ones(correctly_heard),
        'False Positive': amount_of_ones(wrongly_heard),
        'False Negative': amount_of_ones(not_heard),
        'True Negative': 8 * len(signal) - (
                amount_of_ones(correctly_heard) + amount_of_ones(wrongly_heard) + amount_of_ones(not_heard))
    }
    print('correctly heard', confusion['True Positive'], 'not heard', confusion['False Negative'],
          'wrongly heard', confusion['False Positive'], 'correctly not heard', confusion['True Negative'],
          'total amount', 8 * len(signal))
    return confusion


if __name__ == '__main__':
    signals = {  # TODO rename tests
        'full_signal': b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF',
        'decreasing_signal': b'\xFF\x7F\x3F\x1F\x0F\x07\x03',
        'alternating_signal': b'\xFF\x00\xFF\x00\xFF\x00\xFF',
        'noname4_signal': b'\xAA\xAA\xAA\xAA\xAA\xAA\xAA',
        'noname5_signal': b'\xAA\x55\xAA\x55\xAA\x55\xAA'
    }
    starting_freq = 18500
    jumps = 200
    bits = 8
    pulse_duration = 100
    silence_duration = 100
    protocol = IdentityProtocol()
    params = {
        'starting_freq': starting_freq,
        'jumps': jumps,
        'pulse_duration': pulse_duration,
        'silence_duration': silence_duration,
        'protocol': protocol,
        'bits': bits,
        'magnitude_percentage': 0.7,
        'time_threshold': 0.4,
        'center_error': 0.14,
        'name': '',
        'signal': '',
        'melody_time': 0
    }
    result_file_name = 'results.csv'
    header = list(params.keys()) + ['retrieved_signal','True Positive', 'False Positive', 'False Negative', 'True Negative']
    header.remove('protocol')
    with open(result_file_name, 'a', newline='') as result_file:
        writer = csv.DictWriter(result_file, fieldnames=header)
        writer.writeheader()

    result_file = open(result_file_name, 'a')
    result_file.write(''.join(header) + '\n')
    result_file.close()
    for name, signal in signals.items():
        params['name'] = name
        params['signal'] = signal
        params['both'] = False
        pulse_duration_s = pulse_duration / 1000
        if params['both']:
            info_retrieved = sending_and_retrieval(params)
            conf_matrix = confusion_matrix(signal, info_retrieved)
            results = params.copy()
            results.update(conf_matrix)
            results['retrieved_signal'] = info_retrieved.hex()
            results['signal'] = results['signal'].hex()
            results.pop('both', None)
            results.pop('listen_time', None)
            results.pop('protocol', None)
            with open(result_file_name, 'a', newline='') as result_file:
                writer = csv.DictWriter(result_file, fieldnames=header)
                writer.writerow(results)
        else:
            percentages = np.linspace(0.3, 1, num=15)[:-1]
            center_errors = np.linspace(pulse_duration_s/100, 1.5*pulse_duration_s, num=30)
            time_thresholds = np.linspace(pulse_duration_s/100, 10*pulse_duration_s, num=30)
            for center_error in center_errors:
                params['center_error'] = center_error
                for time_threshold in time_thresholds:
                    params['time_threshold'] = time_threshold
                    for magnitude_percentage in percentages:
                        params['magnitude_percentage'] = magnitude_percentage
                        info_retrieved = sending_and_retrieval(params)
                        conf_matrix = confusion_matrix(signal, info_retrieved)
                        results = params.copy()
                        results.update(conf_matrix)
                        results['retrieved_signal'] = info_retrieved.hex()
                        results['signal'] = results['signal'].hex()
                        results.pop('both', None)
                        results.pop('protocol', None)
                        results.pop('listen_time', None)
                        with open(result_file_name, 'a', newline='') as result_file:
                            writer = csv.DictWriter(result_file, fieldnames=header)
                            writer.writerow(results)