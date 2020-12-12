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


if __name__ == '__main__':

    la idea es ver cuantos caracteres necesito para hacerlo un palindromo
    asd -> 2 sa
    si todas las letras son distintas entonces requiero length(s) - 1 si es impar y length(s) si es par

    assd -> adssda
    tenia un subpalindromo, me convenia mantenerlo?

    1AsAp -> pAsAp -> 1AsAp1 -> 2
    empiezo desde el palindromo mas chico, puedo poner o lo que va a la izquierda, o lo que va a la dercha, pero tengo que matchear su coso
    poner dos letras iguales no sirve de nada, mantengo el problema a futuro, que me conviene poner derecha o izquierda?

    aaadfaaa ->f -> dfd -> aaadfdaaa aca me conviene poner un caracter nuevo a izquierda. por que tengo caracteres que puedo usar despues?

    manzanf -> z -> aza 1 -> nazan -> anazana 2 -> manazanam 3 -> fmanazanamf 4
    manzabf -> z -> aza 1 -> bazab 2 ->nbzabn 3 -> abazaba 4 -> mabazabam 5 -> fmabazabamf 6
    manzabf -> z -> nzn 1 -> anzna ->


    haces un bucket sort si es par tiene que tener dos elementos el medio si es impar tiene que tener uno
    si el medio va a ser 0, tenes que insertar  lentgh(s) -1 o length(s) -2 dependiendo si s[0] == s[1]
    si el medio va a ser 1, tenes que insertar length(s) - 1 (si s[0] != s[1]) len(s) -2 si no y len(s) -3 aaansd -> dsnaaansd
    si el medio va a ser i y es impar entonces tengo dos subcadenas s1 y s2
    s[i] = d
    basabendtobasab
    s1 = basabent
    d
    s2 = tnobasab
    busco la subcadena mas grande que este en s2 y la saco de los dos
    ent
    d
    nto
    busco la subcadena mas grande de s1 que este en s2 y la saco de los dos
    e
    d
    o
    cuando no hay mas subcadenas me dice cuantos elementos tengo que agregar a izquierda y a derecha 2
    basabentdotnbasab -> odo 1 -> tnodont 1 -> etnodonte 2 -> basabetnodontebasab


    veo si es palindromo o(n)
    emnumero todas las subcadenas -> 0(n²)
    puestas en un arreglo de arreglos, A[i][j] empieza en i, termina en j

    elijo un medio
    mientras sacar(A[:m][:m], s2, s1):
     pass
    return len(s2)+len(s1)?

