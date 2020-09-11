from pydub.generators import Sine
from pydub.playback import play
from pydub import AudioSegment
from bitstring import BitArray
from pydub.utils import audioop
import time
import functools


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
    starting_freq = 500
    translator = Translator(starting_freq, 1000, 8)
    for translation in translator.translate(b'\xFF\x7F\x3F\x1F\x07\x03\x01'):
        tones = []
        for freq, bit in translation.items():
            if not bit:
                continue
            tones.append(Sine(freq).to_audio_segment(duration=1000, volume=-15))
        if len(tones) == 0:
            time.sleep(1)
        else:
            play(functools.reduce(lambda a, b: b*a, tones))

