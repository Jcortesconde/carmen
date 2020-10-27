from pydub.generators import Sine
from pydub.playback import play
from pydub import AudioSegment
from bitstring import BitArray
import functools
import argparse
from protocol import IdentityProtocol
import time


class Translator:
    def __init__(self, starting_freq, bandwidth, bits):
        self.bands = [starting_freq + i * bandwidth for i in range(bits)]

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
        :param pulse_duration: the amount of time in milliseconds that a tone is going to sound
        :param silence_duration: the time in milliseconds between tones
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
            sound = AudioSegment.silent(self.pulse_duration)
            if len(tones) != 0:
                sound = functools.reduce(lambda a, b: b * a, tones)
            melody.append(sound + silence)
        return functools.reduce(lambda a, b: a + b, melody)

    def send_info(self, info, volume=-20):
        """
        :param info: an array of bytes to send
        :param volume: the volume at which to reproduce de sound
        :return:
        """
        melody = self.generate_melody(info, volume)
        play(melody)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('starting_freq', help='The starting frequency where the information is going to be store',
                        type=int)
    parser.add_argument('jump', help='The distance between two frequencies of information in Hz', type=int)
    parser.add_argument('bits', help='The amount of bits send in a pulse', type=int)
    parser.add_argument('pulse_duration', help='The amount of time in milliseconds that a tone is going to sound',
                        type=int)
    parser.add_argument('silence_duration', help='The time in milliseconds between tones', type=int)
    parser.add_argument('information', help='The information to send')  # , type=bytes)
    parser.add_argument('--volume', help='The volume of the signal, default is 20', type=int, default=-20)

    args = parser.parse_args()
    protocol = IdentityProtocol()

    byte_info = bytes.fromhex(args.information)
    encoded_information = protocol.encode(byte_info)
    reproducer = Reproducer(args.starting_freq, args.jump, args.bits, args.pulse_duration, args.silence_duration)
    time.sleep(0.7)
    reproducer.send_info(encoded_information, args.volume)
