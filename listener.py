import pyaudio
import wave
from scipy.io import wavfile
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal


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

    def calibrate(self, filename):
        rate, audio = wavfile.read(filename)
        M = 1024
        freqs, times, Sx = signal.spectrogram(audio, fs=rate, window='hanning',
                                              nperseg=1024, noverlap=M - 100,
                                              detrend=False, scaling='spectrum')

        plot_spectogram(freqs, times, Sx)
        time_intervals = listener.find_freq(freqs, times, Sx)
        print(time_intervals)
        # La idea es que calibrate sepa la señal que vas a mandar y pueda estimar los tiempos del señal y de silencio,
        # asi despues se puede filtrar los times intervals que da el find_freq a los que realmente importa

    def save(self, frames, filename):
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.listener.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()

    # Devuelve un diccionario de frecuencias:lista de tuplas de intervalos de tiempo (t_inicial, t_final, dif) en segundos
    def find_freq(self, freqs_buckets, times_buckets, matrix, threshold=1e2):
        # 1e4 para 500
        # 1e2 para 8500?
        # se pueden filtrar los intervalos de tiempo por un estimado 0.1 segundos +- 0.03.
        # TODO terminar calibrate asi tenemos mejores estimadores
        bucket_size = freqs_buckets[1]
        indexes = {freq: int(freq / bucket_size) for freq in self.bands}

        bla = [freqs_buckets[indexes[freq]] for freq in self.bands]

        freq_times = {}
        for freq, indx_freq in indexes.items():
            aux = []
            for j in range(len(matrix[indx_freq])):
                if matrix[indx_freq][j] > threshold:
                    aux.append(j)
            freq_times[freq] = aux
        values = {}

        for freq, times in freq_times.items():
            aux = []
            if len(times) == 0:
                values[freq] = aux
                continue
            prev = times[0]
            mid = prev

            for i in range(1, len(times)):
                if mid + 1 != times[i]:
                    aux.append((times_buckets[prev], times_buckets[mid], times_buckets[mid] - times_buckets[prev]))
                    prev = times[i]
                mid = times[i]
            aux.append((times_buckets[prev], times_buckets[mid], times_buckets[mid] - times_buckets[prev]))
            values[freq] = aux
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
    listener = Listener(chunk, fmat, channels, rate, starting_freq, jumps, bits)
    record_seconds = 5
    filename = "output1.wav"
    # listener.calibrate("calib.wav")
    frames = listener.listen(record_seconds)
    listener.save(frames, filename)

    rate, audio = wavfile.read(filename)
    M = 1024
    freqs, times, Sx = signal.spectrogram(audio, fs=rate, window='hanning',
                                          nperseg=1024, noverlap=M - 100,
                                          detrend=False, scaling='spectrum')

    plot_spectogram(freqs, times, Sx)
    time_intervals = listener.find_freq(freqs, times, Sx)

    print(time_intervals)
