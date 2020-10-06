import pyaudio
import wave
from scipy.io import wavfile
import scipy as sp
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal


class Frequency:
    def __init__(self, freq, banda, start_t, delta_t, threshold=1e2):
        self.freq = freq
        self._set_banda(banda, start_t, delta_t)
        self.set_intervals(threshold)

    def _set_banda(self, banda, start_t, delta_t):
        """Setea la banda.

        Keyword arguments:
        banda -- un arreglo con la amplitud de la frecuencia. Sacada del espectograma
        start_t -- el tiempo inicial de la banda
        delta_t -- cuanto incremente el tiempo entre posiciones del arreglo
        """
        self.banda = banda
        self.start_t = start_t
        self.delta_t = delta_t

    def get_time(self, indx):
        """Da el tiempo del i_esimo elemento de la banda
        """
        return self.start_t + self.delta_t * indx

    def set_intervals(self, threshold):
        """Duevuelve un arreglo con tuplas de intervalos de tiempos

        Keyword arguments:
        threshold -- la amplitud minima 
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
                if mid + 1 != times_index[i]:  # Si no son indices contiguos encontre un intervalo.
                    self.intervals.append((self.get_time(prev), self.get_time(mid)))
                    prev = times_index[i]
                mid = times_index[i]
            self.intervals.append((self.get_time(prev), self.get_time(mid)))

    def filter_intervals(self, tone_time, threshold):

        self.intervals = list(filter(lambda tup: abs(tone_time - (tup[1] - tup[0])) < threshold, self.intervals))


class Listener:
    def __init__(self, chunk, fmat, channels, rate, starting_freq, bandwitdth, bits):
        self.chunk = chunk
        self.format = fmat
        self.channels = channels
        self.rate = rate
        self.bands = [starting_freq + i * bandwitdth for i in range(bits)]  # should always be lower to higher
        self.tone_time = 0.1  # sec
        self.silence_time = 0.1  # sec
        assert (all(self.bands[i] <= self.bands[i + 1] for i in range(len(self.bands) - 1)))
        self.listener = pyaudio.PyAudio()

    # returns a list where each element is a sample of the size of format*channels*chunks
    # the length of the list is (rate/chunk)*seconds
    def listen(self, seconds):

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

    def filter(self, times_intervals):
        for freq in times_intervals:
            freq.filter_intervals(self.tone_time, 35 * self.delta_t)

    def extract_info(self, filename):
        frequencies = self.find_freqs(filename)
        self.filter(frequencies)
        # TODO ver la distribucion del tiempo de silencio, media 0 o positiva/negativa(caso ultimo arreglar ideas)
        start_interval = None
        end_interval = None
        for freq in frequencies:
            interval = freq.intervals[0]
            if start_interval is None or interval[0] < start_interval[0]:
                start_interval = interval

            interval = freq.intervals[-1]
            if end_interval is None or end_interval[1] < interval[1]:
                end_interval = interval
        # TODO Testear este hyper parametro sacado bien del culo
        error = 0.12
        matrix_bit = []
        max_bits = 0
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
                    # current_interval = interval
                current_interval = (
                current_interval[1] + self.silence_time, current_interval[1] + self.silence_time + self.tone_time)
            matrix_bit.append(aux)
            print(aux)

        aux = []
        for col in range(len(matrix_bit[0])):
            for row in range(len(matrix_bit)):
                aux.append(matrix_bit[row][col])

        return aux

    def save(self, frames, filename):
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.listener.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()

    # Devuelve un diccionario de frecuencias:lista de tuplas de intervalos de tiempo (t_inicial, t_final) en segundos
    def find_freqs(self, filename, threshold=1e2):
        rate, audio = wavfile.read(filename)
        M = 1024
        freqs, times_bucket, Sx = signal.spectrogram(audio, fs=rate, window='hanning',
                                                     nperseg=1024, noverlap=M - 100,
                                                     detrend=False, scaling='spectrum')
        # 1e4 para 500
        # 1e2 para 8500?
        # se pueden filtrar los intervalos de tiempo por un estimado 0.1 segundos +- 0.03.
        # TODO terminar calibrate asi tenemos mejores estimadores
        bucket_size = freqs[1] - freqs[0]
        self.delta_t = times_bucket[1] - times_bucket[0]
        self.start_t = times_bucket[0]
        self.amount_t = len(times_bucket)
        indexes = {freq: int(freq / bucket_size) for freq in self.bands}
        values = [Frequency(freq, Sx[indx_freq], self.start_t, self.delta_t, threshold) for freq, indx_freq in
                  indexes.items()]

        return values


def plot_amp(audio, rate):
    n = audio.shape[0]
    l = n / rate
    print('Audio length:', l, 'seconds')
    f, ax = plt.subplots()
    ax.plot(np.arange(n) / rate, audio)
    ax.set_xlabel('Time [s]')
    ax.set_ylabel('Amplitude [unknown]')
    plt.show()


def plot_spectogram(freqs, times, Sx):
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
    listener = Listener(chunk, fmat, channels, rate, starting_freq, jumps, bits)
    record_seconds = 5
    filename = "output1.wav"
    calib_file = "calib.wav"

    # frames = listener.listen(record_seconds)
    # listener.save(frames, filename)

    # rate, audio = wavfile.read(filename)
    # M = 1024
    # freqs, times, Sx = signal.spectrogram(audio, fs=rate, window='hanning',
    #                                      nperseg=1024, noverlap=M - 100,
    #                                      detrend=False, scaling='spectrum')
    #
    # plot_spectogram(freqs, times, Sx)
    listener.extract_info(filename)
    # time_intervals = listener.find_freq(freqs, times, Sx)
# print(time_intervals)
