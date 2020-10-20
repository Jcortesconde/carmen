class IdentityProtocol:
    def __init__(self):
        """
        This class is a template of what a Protocol should have. Its is the identity Protocol
        """

    def encode(self, bits):
        """

        :param bits: the raw bits of information
        :return: the encoded bits
        """
        return bits

    def decode(self, bits):
        """

        :param bits: array of encoded bits
        :return: the raw bits of information
        """
        j = 0
        num = 0
        decoded_bits = []
        for i in range(len(bits)):
            if j == 8:  # We make a byte at a time
                # TODO chequear que pasa si la cantidad de bits no es multiplo de 8
                decoded_bits.append(num)
                j = 0
                num = 0
            num += bits[i] * 2 ** (7 - j)
            j += 1
        decoded_bits.append(num)
        return bytes(decoded_bits)
