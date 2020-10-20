import pyaudio
import wave
from scipy.io import wavfile
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal


class Frequency:
    def __init__(self, freq, band, start_t, delta_t, threshold=1e2):
        """
        This Object is designed to make it easier to query a given frequency of a sound sample
        :param freq: The frequency this Object is defined by
        :param band: An array with the magnitudes/amplitudes of the frequency in a sound sample
        :param start_t: starting time of the band
        :param delta_t: time incremental between array elements
        :param threshold:  Minimum amplitude to determined if the frequency was active.
        """
        self.freq = freq
        self._set_band(band, start_t, delta_t)
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
        :param threshold:
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
        :param pulse_duration: the amount of time in miliseconds that a tone is going to sound
        :param silence_time: the time in miliseconds between tones
        """
        self.chunk = chunk
        self.format = fmat
        self.channels = channels
        self.rate = rate
        self.bands = [starting_freq + i * delta_freq for i in range(bits)]  # should always be lower to higher
        self.pulse_duration = pulse_duration / 1000 # we work with seconds here # TODO work with  same unit of time between all project
        self.silence_time = silence_time/1000 #we work with seconds here
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

    def filter(self, frequencies):
        """
        filter the frequencies times interval given some magic number that worked out
        :param frequencies: list of frequencies
        :return:
        """
        # TODO test magic numbers parameterize
        for freq in frequencies:
            freq.filter_intervals(self.pulse_duration, 35 * self.delta_t)

    def extract_info(self, filename):
        """

        :param filename: the file to read the sound sample
        :return: a stream of bits that the asmple had as information
        """
        frequencies = self.find_frequencies(filename)
        self.filter(frequencies)
        # TODO ver la distribucion del tiempo de silencio, media 0 o positiva/negativa(caso ultimo arreglar ideas)
        start_interval = None
        end_interval = None
        for freq in frequencies:
            print(freq.freq, freq.intervals)
            interval = freq.intervals[0]
            if start_interval is None or interval[0] < start_interval[0]:
                start_interval = interval

            interval = freq.intervals[-1]
            if end_interval is None or end_interval[1] < interval[1]:
                end_interval = interval
        # TODO Testear este hyper parametro sacado bien del culo
        error = 0.12
        matrix_bit = []
        for freq in frequencies:
            aux = []
            current_interval = start_interval
            index = 0
            while current_interval[0] < end_interval[1]:
                interval = freq.intervals[index]
                interval_center = (interval[1] + interval[0]) / 2
                current_center = (current_interval[0] + current_interval[1]) / 2
                diff = abs(interval_center - current_center)
                overlapping = diff < error
                aux.append(overlapping)
                if overlapping and index < len(freq.intervals) - 1:
                    index += 1
                current_interval = (
                current_interval[1] + self.silence_time, current_interval[1] + self.silence_time + self.pulse_duration)
            matrix_bit.append(aux)
            print(aux)

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
        #TODO learn how to skipp saving the wav files this is costy in time
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.listener.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()


    def find_frequencies(self, filename, threshold=1e2):
        """

        :param filename: th file name from where to read a wav file
        :param threshold: the threshold to determine whether or not a frequency was active or not
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
        self.start_t = times_bucket[0]
        self.amount_t = len(times_bucket)
        indexes = {freq: int(freq / bucket_size) for freq in self.bands}
        values = [Frequency(freq, Sx[indx_freq], self.start_t, self.delta_t, threshold) for freq, indx_freq in
                  indexes.items()]
        return values

    def listen_and_extract(self, duration, filename):
        frames = self.listen(duration)
        self.save(frames, filename)
        info = self.extract_info(filename)

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


def plot_spectogram(freqs, times, Sx):
    """
    Shows a plot of the spectogram of a sound sample
    :param freqs: the frequencies of the audio y axis
    :param times: the time of the sample x axis
    :param Sx: the apmlitudes/magnitudes of the frecuencies given a time
    :return: None
    """
    f, ax = plt.subplots(figsize=(4.8, 2.4))
    ax.pcolormesh(times, freqs / 1000, 10 * np.log10(Sx), cmap='viridis', shading='flat')
    ax.set_ylabel('Frequency [kHz]')
    ax.set_xlabel('Time [s]')
    plt.show()


if __name__ == '__main__':
    chunk = 1024
    fmat = pyaudio.paInt16
    channels = 1
    rate = 44100
    starting_freq = 18500
    jumps = 200
    bits = 8
    pulse_duration = 100
    silence_duration = 100
    listener = Listener(chunk, fmat, channels, rate, starting_freq, jumps, bits, pulse_duration, silence_duration)
    record_seconds = 10
    filename = "output1.wav"
    filename = 'test_futures1.wav'
    calib_file = "calib.wav"

    # frames = listener.listen(record_seconds)
    # listener.save(frames, filename)

    rate, audio = wavfile.read(filename)
    M = 1024
    freqs, times, Sx = signal.spectrogram(audio, fs=rate, window='hanning',
                                         nperseg=1024, noverlap=M - 100,
                                         detrend=False, scaling='spectrum')

    plot_spectogram(freqs, times, Sx)
    info = listener.extract_info(filename)
    print(info)
    # time_intervals = listener.find_freq(freqs, times, Sx)
