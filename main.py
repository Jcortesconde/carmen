from reproducer import Reproducer
import subprocess
from protocol import IdentityProtocol
from os import listdir
from os.path import isfile, join
import csv
import numpy as np
import math


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

    listener_string = 'python listener.py ' + same_section + listen_time + ' --filename ' + file_name
    listener_string += ' --magnitude_percentage ' + str(params['magnitude_percentage']) + ' --time_threshold ' + str(
        params['time_threshold']) + ' --center_error ' + str(params['center_error'])
    if params['both']:

        console_string = reproducer_string + ' & ' + listener_string
    else:
        listener_string += ' --extract'
        console_string = listener_string
    return console_string


def sending_and_retrieval(params):
    encoded_signal = protocol.encode(params['signal'])

    reproducer = Reproducer(params['starting_freq'], params['jumps'], params['bits'], params['pulse_duration'],
                            params['silence_duration'])
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

def acum_list(files, params):
    amount = 0

    file_pos = 0
    last_file = 'Afull_signal_bits:32_jump:130_pd:50_sd:70.wav'
    for file in files:
        set_params(file, params, signals)
        if not skip(params):
            amount += 1
            if file == last_file:
                file_pos = amount

    print('amount of files to run', amount, 'file pos', file_pos, 'amount total', len(files))
    return amount

def optimize_listener(files, result_file_name, params, signals):
    files_to_run = acum_list(files, params)
    files_runned = 0
    for file in files:
        set_params(file, params, signals)
        percentages = np.linspace(0.1, 0.5, num=5)
        min_t = 0.0022675736961451243
        pulse_duration_s = params['pulse_duration'] / 1000
        time = min(min_t, pulse_duration_s / 100)
        center_errors = np.linspace(0.03, 1, num=50)
        time_threshold = 0.1009
        print(file, skip(params))
        params['time_threshold'] = time_threshold

        if not skip(params):
            for center_error in center_errors:
                params['center_error'] = center_error
                for magnitude_percentage in percentages:
                    print(files_runned, '/', files_to_run*len(center_errors)*len(percentages))
                    files_runned += 1
                    params['magnitude_percentage'] = magnitude_percentage
                    info_retrieved = sending_and_retrieval(params)
                    conf_matrix = confusion_matrix(params['signal'], info_retrieved)
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
            print('')

def set_params(file, params, signals):
    params['name'] = file
    param_spilt = file.split('_')
    param_list = list(filter(lambda elem: ':' in elem, param_spilt))
    param_list = list(map(lambda elem: elem.split(':'), param_list))
    params['bits'] = int(param_list[0][1])
    params['jumps'] = int(param_list[1][1])
    params['pulse_duration'] = int(param_list[2][1])
    params['silence_duration'] = int(param_list[3][1][:-4])
    params['starting_freq'] = params['starting_freq'] = 20000 - params['jumps'] * (params['bits'] - 1)
    params['signal'] = signals[param_spilt[0] + '_' + param_spilt[1]]
    set_one_sec_signal(params)


def skip(params):
    aux = 10 >= params['pulse_duration'] or params['pulse_duration'] > 70
    aux = aux or 10 >= params['silence_duration'] or params['silence_duration'] > 70
    aux = aux or params['bits'] == 64 or params['bits'] == 8
    aux = aux or params['jumps'] != 130
    return aux


def get_files():
    mypath = 'sound_files/'
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    filter_files = list(filter(lambda elem: ':' in elem, onlyfiles))
    return filter_files


def set_one_sec_signal(params):
    time = params['pulse_duration'] + params['silence_duration']
    tones_per_second = math.ceil(1000 / time)  # want at least one second of recording
    bytes_per_tone = params['bits'] // 8
    bytes_per_second = tones_per_second * bytes_per_tone
    bytes_in_signal = len(params['signal'])
    repeat_signal = math.ceil(bytes_per_second / bytes_in_signal)
    params['signal'] = params['signal'] * repeat_signal


if __name__ == '__main__':
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
        'magnitude_percentage': 0.3,
        'time_threshold': 0.035,
        'center_error': 0.06,
        'name': '',
        'signal': '',
        'melody_time': 0
    }

    result_file_name = 'results_130.csv'
    header = list(params.keys()) + ['retrieved_signal', 'True Positive', 'False Positive', 'False Negative',
                                    'True Negative']
    header.remove('protocol')
    with open(result_file_name, 'a', newline='') as result_file:
        writer = csv.DictWriter(result_file, fieldnames=header)
        writer.writeheader()

    result_file = open(result_file_name, 'a')
    result_file.write(''.join(header) + '\n')
    result_file.close()
    params['both'] = False
    signals = {  # TODO rename tests
        'full_signal': b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF',
        'decreasing_signal': b'\xFF\x7F\x3F\x1F\x0F\x07\x03',
        'alternating_signal': b'\xFF\x00\xFF\x00\xFF\x00\xFF',
        'noname4_signal': b'\xAA\xAA\xAA\xAA\xAA\xAA\xAA',
        'noname5_signal': b'\xAA\x55\xAA\x55\xAA\x55\xAA'
    }
    if params['both']:

        for name, signal in signals.items():
            params['name'] = name
            params['signal'] = signal
            pulse_duration_s = pulse_duration / 1000
            durations = [10 + 20 * i for i in range(5)]
            bits = [8, 16, 32, 64]
            jumps = [50 + 20 * i for i in range(8)]
            for bit in bits:
                for jump in jumps:
                    for pulse_dur in durations:
                        for sil_dur in durations:
                            specific_name = name + '_bits:' + str(bit) + '_jump:' + str(jump) + '_pd:' + str(
                                pulse_dur) + '_sd:' + str(sil_dur) + '.wav'

                            params['name'] = specific_name
                            params['jumps'] = jump
                            params['pulse_duration'] = pulse_dur
                            params['silence_duration'] = sil_dur
                            params['bits'] = bit
                            params['starting_freq'] = 20000 - jump * (bit - 1)
                            set_one_sec_signal(params)
                            info_retrieved = sending_and_retrieval(params)
                            conf_matrix = confusion_matrix(params['signal'], info_retrieved)
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
        files = get_files()
        optimize_listener(files, result_file_name, params, signals)
