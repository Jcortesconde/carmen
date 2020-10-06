from pydub.generators import Sine
from pydub.playback import play
from pydub import AudioSegment
from bitstring import BitArray
from pydub.utils import audioop
import time
import functools
import wave


class Translator:
    def __init__(self, starting_freq, bandwitdth, bits):
        self.bands = [starting_freq + i * bandwitdth for i in range(bits)]

    def translate(self, data):
        bits = BitArray(data)
        i = 0
        while i < len(bits):
            freqs = {}
            for b in self.bands:
                freqs[b] = bits[i]
                i += 1
                if i == len(bits):
                    break
            yield freqs


if __name__ == '__main__':

    
    start_signal = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
    signal = b'\xFF\x7F\x3F\x1F\x07\x03\x01'
    starting_freq = 18500
    saltos = 200
    cantidad_bits = 8
    pulse_duration = 100
    silence_duration = 100
    silence = AudioSegment.silent(silence_duration)
    translator = Translator(starting_freq, saltos, cantidad_bits)
    melody = [silence]
    for translation in translator.translate(start_signal):
        tones = []
        for freq, bit in translation.items():
            if not bit:
                continue
            print(freq)
            tones.append(Sine(freq).to_audio_segment(duration=pulse_duration, volume=-20))
        sound = functools.reduce(lambda a, b: b*a, tones)
        melody.append(sound+silence)
    print(tones)
    play(functools.reduce(lambda a, b: a+b, melody))#*suma frecuencias sobrecaca rara

