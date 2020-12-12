import pyaudio
import wave
from scipy.io import wavfile
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
import protocol
import argparse


class Frequency:
    def __init__(self, freq, band, start_t, delta_t, percentage=0.7):
        """
        This Object is designed to make it easier to query a given frequency of a sound sample
        :param freq: The frequency this Object is defined by
        :param band: An array with the magnitudes/amplitudes of the frequency in a sound sample
        :param start_t: starting time of the band
        :param delta_t: time incremental between array elements
        :param percentage: The percentage that a frequency must pass to determine if it was in, default is 0.7
        """
        self.freq = freq
        self._set_band(band, start_t, delta_t)
        min_elem = min(band)
        max_elem = max(band)
        threshold = percentage*(max_elem - min_elem) + min_elem
        self.set_intervals(threshold)

    def _set_band(self, band, start_t, delta_t):
        """
        Sets the band and the info that comes along with the band.
        :param band: an array with the amplitude of the frequency for each time. Taken from a spectogram
        :param start_t: starting time of the band
        :param delta_t: time incremental between array elements
        :return: None
        """
        self.banda = band
        self.start_t = start_t
        self.delta_t = delta_t

    def get_time(self, indx):
        """
        :param indx: index of an element of a band
        :return: the time that element was reproduced
        """
        return self.start_t + self.delta_t * indx

    def set_intervals(self, threshold):
        """
        set the intervals internal variable with an array with intervals of times when the frequency was active
        :param threshold: Minimum amplitude to determined if the frequency was active.
        :return: None
        """
        times_index = []
        for j in range(len(self.banda)):
            if self.banda[j] > threshold:
                times_index.append(j)

        self.intervals = []
        if len(times_index) != 0:
            prev = times_index[0]
            mid = prev

            for i in range(1, len(times_index)):
                if mid + 1 != times_index[i]:  # When the indexes are not contiguous then we found an interval.
                    self.intervals.append((self.get_time(prev), self.get_time(mid)))
                    prev = times_index[i]
                mid = times_index[i]
            self.intervals.append((self.get_time(prev), self.get_time(mid)))

    def filter_intervals(self, tone_time, threshold):
        """
        Filter the intervals such as the difference between the tone time and the time of the interval
        is less than the threshold
        :param tone_time: the theoretical time a tone should ne active
        :param threshold: The threshold to decide where a time interval is actually a signal
        :return: None
        """
        self.intervals = list(filter(lambda tup: abs(tone_time - (tup[1] - tup[0])) < threshold, self.intervals))


class Listener:
    def __init__(self, chunk, fmat, channels, rate, starting_freq, delta_freq, bits, pulse_duration, silence_time):
        """

        :param chunk:
        :param fmat: The format of the Wav we are going to read/write/listen
        :param channels: the amount of channels of the Wav
        :param rate: The rate of the sound sample
        :param starting_freq: The starting frequency where the information is going to be store
        :param delta_freq: space between the frequencies that hold information
        :param bits: amount of information that is going to be send
        :param pulse_duration: the amount of time in milliseconds that a tone is going to sound
        :param silence_time: the time in milliseconds between tones
        """
        self.chunk = chunk
        self.format = fmat
        self.channels = channels
        self.rate = rate
        self.bands = [starting_freq + i * delta_freq for i in range(bits)]  # should always be lower to higher
        self.pulse_duration = pulse_duration / 1000  # we work with seconds here
        # TODO work with  same unit of time between all project
        self.silence_time = silence_time / 1000  # we work with seconds here
        # This will be modified once we start analyzing one audio sample
        self.delta_t = 0
        self.start_t = 0
        self.amount_t = 0
        assert (all(self.bands[i] <= self.bands[i + 1] for i in range(len(self.bands) - 1)))
        self.listener = pyaudio.PyAudio()

    def listen(self, seconds):
        """

        :param seconds: amount of time to listen
        :return: list where each element is a sample of the size of format*channels*chunks
        """
        stream = self.listener.open(format=self.format,
                                    channels=self.channels,
                                    rate=self.rate,
                                    input=True,
                                    frames_per_buffer=self.chunk)

        frames = []

        for i in range(0, int(self.rate / self.chunk * seconds)):
            data = stream.read(self.chunk)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        self.listener.terminate()
        return frames

    def filter(self, frequencies, threshold):
        """
        filter the frequencies times interval given some magic number that worked out
        :param frequencies: list of frequencies
        :param threshold: The threshold to decide where a time interval is actually a signal
        :return:
        """
        # TODO test magic numbers parameterize
        for freq in frequencies:
            freq.filter_intervals(self.pulse_duration, threshold)

    def extract_info(self, filename, magnitude_percentage, time_threshold, center_error):
        """

        :param filename: The file to read the sound sample
        :param magnitude_percentage: The percentage that a frequency must pass to determine if it was in, default is 0.7
        :param time_threshold: The threshold to decide where a time interval is actually a signal
        :param center_error: The error we are willing to accept to se if two intervals are the same
        :return: a stream of bits that the sample had as information
        """
        frequencies = self.find_frequencies(filename, magnitude_percentage)

        self.filter(frequencies, time_threshold)
        # TODO ver la distribucion del tiempo de silencio, media 0 o positiva/negativa(caso ultimo arreglar ideas)
        start_interval = None
        end_interval = None
        for freq in frequencies:
            #print(freq.freq, freq.intervals)
            if len(freq.intervals) != 0:
                interval = freq.intervals[0]
                if start_interval is None or interval[0] < start_interval[0]:
                    start_interval = interval

                interval = freq.intervals[-1]
                if end_interval is None or end_interval[1] < interval[1]:
                    end_interval = interval
        if start_interval is None:
            return []
        matrix_bit = []
        for freq in frequencies:
            aux = []
            current_interval = start_interval
            index = 0
            while current_interval[0] < end_interval[1]:
                same_center = False
                if index < len(freq.intervals):
                    interval = freq.intervals[index]
                    interval_center = (interval[1] + interval[0]) / 2
                    current_center = (current_interval[0] + current_interval[1]) / 2
                    diff = abs(interval_center - current_center)
                    same_center = diff < center_error
                aux.append(same_center)
                if same_center and index < len(freq.intervals) - 1:
                    index += 1
                current_interval = (
                    current_interval[1] + self.silence_time,
                    current_interval[1] + self.silence_time + self.pulse_duration)
            matrix_bit.append(aux)

        aux = []
        for col in range(len(matrix_bit[0])):
            for row in range(len(matrix_bit)):
                aux.append(matrix_bit[row][col])

        return aux

    def save(self, frames, filename):
        """

        :param frames: an array of info?
        :param filename: the filename to save the wav
        :return: None
        """
        # TODO learn how to skipp saving the wav files this is costy in time
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.listener.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()

    def find_frequencies(self, filename, percentage=0.7):
        """

        :param filename: The file name from where to read a wav file
        :param percentage: The percentage that a frequency must pass to determine if it was in
        :return: A list of Frequency Objects,corresponding to the frequencies that hold information
        """
        rate, audio = wavfile.read(filename)
        M = 1024
        freqs, times_bucket, Sx = signal.spectrogram(audio, fs=rate, window='hanning',
                                                     nperseg=1024, noverlap=M - 100,
                                                     detrend=False, scaling='spectrum')
        # threshold 1e4 for 500Hz
        # threshold 1e2 for 8500Hz
        # TODO test threshold hyperparameter
        # TODO if we calibrate given a known sound we should be able to use better estimators, maybe needed
        bucket_size = freqs[1] - freqs[0]
        self.delta_t = times_bucket[1] - times_bucket[0]
        #print(bucket_size, self.delta_t)
        self.start_t = times_bucket[0]
        self.amount_t = len(times_bucket)
        indexes = {freq: int(freq / bucket_size) for freq in self.bands}
        values = [Frequency(freq, Sx[indx_freq], self.start_t, self.delta_t, percentage) for freq, indx_freq in
                  indexes.items()]
        return values

    def listen_and_extract(self, duration, filename, magnitude_threshold, time_threshold, center_error):
        frames = self.listen(duration)
        self.save(frames, filename)
        info = self.extract_info(filename, magnitude_threshold, time_threshold, center_error)

        return info


def plot_amp(audio, rate):
    """
    shows a plot of the audio
    :param audio: the sound sample
    :param rate: the rate of the sound sample
    :return: None
    """
    n = audio.shape[0]
    l = n / rate
    print('Audio length:', l, 'seconds')
    f, ax = plt.subplots()
    ax.plot(np.arange(n) / rate, audio)
    ax.set_xlabel('Time [s]')
    ax.set_ylabel('Amplitude [unknown]')
    plt.show()


def plot_spectrogram(freqs, times, Sx):
    """
    Shows a plot of the spectrogram of a sound sample
    :param freqs: the frequencies of the audio y axis
    :param times: the time of the sample x axis
    :param Sx: the amplitudes/magnitudes of the frequencies given a time
    :return: None
    """
    f, ax = plt.subplots(figsize=(4.8, 2.4))
    pcm = ax.pcolormesh(times, freqs / 1000, 10 * np.log10(Sx), cmap='viridis', shading='flat')
    ax.set_ylabel('Frequency [kHz]')
    ax.set_xlabel('Time [s]')
    f.colorbar(pcm, ax=ax)
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('starting_freq', help='The starting frequency where the information is going to be store',
                        type=int)
    parser.add_argument('jump', help='The distance between two frequencies of information in Hz', type=int)
    parser.add_argument('bits', help='The amount of bits send in a pulse', type=int)
    parser.add_argument('pulse_duration', help='The amount of time in milliseconds that a tone is going to sound',
                        type=int)
    parser.add_argument('silence_duration', help='The time in milliseconds between tones', type=int)
    parser.add_argument('seconds', help='The seconds to listen', type=int)
    parser.add_argument('-c', '--chunk', help='The size of data in a chunk, default is 1024', type=int, default=1024)
    parser.add_argument('-f', '--format', help='The Format of the audio, default is 16 bits',
                        type=type(pyaudio.paInt16), default=pyaudio.paInt16)
    parser.add_argument('--channels', help='The amount of channels to listen, default is 1', type=int, default=1)
    parser.add_argument('-r', '--rate', help='The rate of the sampling, default is 44100 hz', type=int, default=44100)
    parser.add_argument('--filename', help='The name where to save the file, must end with .wav', type=str,
                        default='output.wav')

    parser.add_argument('--magnitude_percentage',
                        help='The percentage that a frequency must pass to determine if it was in, default is 0.7',
                        type=float, default=0.7)
    parser.add_argument('--time_threshold',
                        help='The threshold to decide where a time interval is actually a signal, default is 0.4',
                        type=float, default=0.4)
    parser.add_argument('--center_error',
                        help='The error we are willing to accept to se if two intervals are the same, default is 0.14',
                        type=float, default=0.14)
    parser.add_argument('--plot', help='It will plot the spectrogram', action='store_true')
    parser.add_argument('--extract', help='When you want to extract', action='store_true')

    args = parser.parse_args()

    listener = Listener(args.chunk, args.format, args.channels, args.rate, args.starting_freq, args.jump, args.bits,
                        args.pulse_duration, args.silence_duration)
    filename = 'sound_files/' + args.filename
    encoded_signal = ''
    if args.extract:
        encoded_signal = listener.extract_info(filename, args.magnitude_percentage, args.time_threshold,
                                               args.center_error)
    else:
        encoded_signal = listener.listen_and_extract(args.seconds, filename, args.magnitude_percentage,
                                                     args.time_threshold, args.center_error)
    protocol = protocol.IdentityProtocol()
    info = protocol.decode(encoded_signal)
    print('listen:', info.hex())
    if args.plot:
        rate, audio = wavfile.read(filename)
        M = 1024
        freqs, times, Sx = signal.spectrogram(audio, fs=args.rate, window='hanning',
                                              nperseg=1024, noverlap=M - 100,
                                              detrend=False, scaling='spectrum')

        plot_spectrogram(freqs, times, Sx)
