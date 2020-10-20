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

class Reproducer:
    def __init__(self, starting_freq, delta_freq, bits, pulse_duration, silence_duration):
        """

        :param starting_freq: The starting frequency where the information is going to be store
        :param delta_freq: space between the frequencies that hold information
        :param bits: amount of information that is going to be send
        :param pulse_duration: the amount of time in miliseconds that a tone is going to sound
        :param silence_duration: the time in miliseconds between tones
        """
        self.translator = Translator(starting_freq, delta_freq, bits)
        self.pulse_duration = pulse_duration
        self.silence_duration = silence_duration

    def get_time(self, info):
        """

        :param info: message to send
        :return: the time that the melody will take
        """
        melody = self.generate_melody(info)
        return melody.duration_seconds

    def generate_melody(self, info, volume=-20):
        # TODO see to incorporate other sounds in the background to hide the message
        silence = AudioSegment.silent(self.silence_duration)
        melody = [silence]
        for translation in self.translator.translate(info):
            tones = []
            for freq, bit in translation.items():
                if not bit:
                    continue
                tones.append(Sine(freq).to_audio_segment(duration=self.pulse_duration, volume=volume))
            sound = functools.reduce(lambda a, b: b * a, tones)
            melody.append(sound + silence)
        return functools.reduce(lambda a, b: a + b, melody)

    def send_info(self, info, volume=-20):
        """
        :param info: an arrray of bytes to send
        :param volume: the volume at which to reproduce de sound
        :return:
        """
        melody = self.generate_melody(info, volume)
        play(melody)


if __name__ == '__main__':
    start_signal = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
    signal = b'\xFF\x7F\x3F\x1F\x07\x03\x01'
    starting_freq = 18500
    jumps = 200
    bits = 8
    pulse_duration = 100
    silence_duration = 100

    reproducer = Reproducer(starting_freq, jumps, bits, pulse_duration, silence_duration)
    reproducer.send_info(signal)