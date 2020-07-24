# coding=utf-8

import os
import sys
import random
import datetime

from dotenv import load_dotenv

''' This python module describes a custom command line utility that allows the user to easily
encrypt and decrypt files and directories in-place according to the RSA encryption algorithm.

The global variables KEYSIZE and KEYDIR control the default size (in bits) of the RSA keys
generated by this module and the location in which they are stored on the disk.


USAGE:
1) To generate a key pair, execute the following terminal command:
    python [path_to_RSA_Encrypt.py] -keygen [keysize]

    supplying a non-default keysize will generate a key with a length in bits equivalent to the
    largest multiple of two that is less than the supplied keysize.

2) To encrypt a file or directory, execute the following terminal command:
    python [path_to_RSA_Encrypt.py] -encrypt [path_to_encrypt]

    if [path_to_encrypt] points to a file, the utility will encrypt the file using the keys stored
    under KEYDIR/keys.txt.  If it points to a directory, the utility will recursively encrypt the
    contents of the directory

3) To decrypt a file or directory, execute the following terminal command:
    python [path_to_RSA_Encrypt.py] -decrypt [path_to_decrypt]

    if [path_to_decrypt] points to a file, the utility will decrypt the file using the keys stored
    under KEYDIR/keys.txt.  If it points to a directory, the utility will recursively decrypt the
    contents of the directory.

Execution can be greatly simplified by adding the following aliases to ~/.bashrc:
    alias encrypt='python [path_to_RSA_Encrypt.py]/RSA_Encrypt.py -encrypt'
    alias decrypt='python [path_to_RSA_Encrypt.py]/RSA_Encrypt.py -decrypt'
    alias keygen='python [path_to_RSA_Encrypt.py]/RSA_Encrypt.py -keygen'

You can then just call 'encrypt [path]' or 'decrypt [path]' to encrypt/decrypt files and
directories, or 'keygen [size]' to generate a new key pair.
'''

load_dotenv()
KEYDIR = os.getenv('KEYDIR')
KEYSIZE = 2048

def main():
    ''' main executable.  Parses command line arguments and controls functionality of utility

    void method.

    Raises:
        ValueError if utility is run in keygen mode and is supplied a proposed key size that is
            less than 128 bits.
    '''
    if (len(sys.argv) == 3 and sys.argv[1] == "-encrypt"):
        file = os.path.join(os.getcwd(), sys.argv[2])
        if (os.path.isdir(file)):
            encrypt_directory(file)
        else:
            encrypt_file(file)
    elif (len(sys.argv) == 3 and sys.argv[1] == "-decrypt"):
        if (os.path.isdir(sys.argv[2])):
            decrypt_directory(sys.argv[2])
        else:
            decrypt_file(sys.argv[2])
    elif (sys.argv[1] == "-keygen"):
        if (len(sys.argv) == 2):
            generate_key_pair(KEYSIZE / 2)
        elif (len(sys.argv) == 3 and sys.argv[2].isdigit()):
            val = int(sys.argv[2])
            if (val < 128):
                raise ValueError("key size in bits must be >= 128")
            val = 1 << (val.bit_length() - 1)  # round to nearest power of 2:
            generate_key_pair(val / 2)

def is_prime(n, k=128):
    ''' Tests if a number is prime according to iterated Miller-Rabin primality test

    Accepts:
        int n = number to test
        int k = number of Miller-Rabin tests to perform

    Returns:
        True if n is (probably) prime
    '''
    # trivial cases
    if (n == 2 or n == 3):
        return True
    if (n <= 1 or n % 2 == 0):
        return False

    # find r and s by factoring powers of 2 from n - 1
    s = 0
    r = n - 1
    while (r & 1 == 0):
        s += 1
        r //= 2

    # do k tests
    for val in range(k):
        a = random.randint(2, n - 1)
        x = pow(a, r, n)   # Fermat's little theorem: a^r = 1 mod(n)
        if (x != 1 and x != n - 1):
            j = 0
            while (j < s - 1 and x != n - 1):
                x = pow(x, 2, n)
                if (x == 1):
                    return False
                j += 1
            if (x != n - 1):
                return False
    return True

def generate_prime_candidate(length):
    ''' generates a prime number candidate of a specified bit length

    Accepts:
        int length = length of desired prime number candidate

    Returns:
        random odd number of the specified length in bits
    '''
    p = random.getrandbits(length)
    p |= (1 << length - 1) | 1    # p = result of bitwise or of p against 100...001
    return p

def get_prime(length=(KEYSIZE / 2)):
    ''' finds a random prime number of the specified length in bits

    Accepts:
        int length = length of prime to return (default = KEYSIZE / 2)

    Returns:
        random prime number with the specified length in bits
    '''
    p = generate_prime_candidate(length)
    while (not is_prime(p)):
        p = generate_prime_candidate(length)
    return p


def xgcd(b, a):
    ''' computes greatest common divisor between two numbers via the extended euclidean algorithm

    Accepts:
        int b, a = numbers between which greatest common divisor is to be found

    Returns:
        triple whose elements correspond to
            1. greatest common divisor between a and b
            2 & 3. coefficients x0 and y0 of Bézout's identity, such that a*x0 + b*y0 = gcd(a, b)
    '''
    x0, x1, y0, y1 = 1, 0, 0, 1
    while (a != 0):
        q = b // a
        b, a = a, b % a
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    return b, x0, y0

def mod_inverse(a, m) :
    ''' evaluates modular multiplicative inverse of a with modulus m

    Accepts:
        int a = base for which inverse is to be calculated
        int m = modulus to use in evaluation of inverse

    Returns:
        modular multiplicative inverse x such that a*x == 1 (mod m)

    Raises:
        ValueError if modular multiplicative inverse does not exist (gcd(a, m) != 1)
    '''
    g, x, y = xgcd(a, m)
    if (g != 1):
        raise ValueError('modular inverse does not exist (gcd(a, m) != 1)')
    else:
        return x % m

def generate_key_pair(length=(KEYSIZE / 2)):
    ''' generates a public/private key pair and saves them to KEYDIR/keys.txt

    Accepts:
        int length = length (in bits) of generated key pair

    Returns:
        void.  Saves keys to KEYDIR/keys.txt
    '''
    print("Generating RSA keys...")
    p = get_prime(length)
    q = get_prime(length)
    while (p == q):
        p = get_prime(length)
        q = get_prime(length)

    n = p * q
    phi = (p - 1) * (q - 1)   # phi = totient function

    e = 65537   #2**16 + 1.  This is standard.  Low e = faster encryption, slower decryption
    publicKey = (e, n)

    d = mod_inverse(e, phi)
    privateKey = (d, n)

    dir = os.path.join(KEYDIR, '')
    if (not os.path.isdir(dir)):
        try:
            os.mkdir(dir)
        except OSError:
            raise OSError("Could not create key directory " + dir)

    keyPath = os.path.join(KEYDIR, "keys.txt")
    file = open(keyPath, "w+")
    file.write("[" + str(datetime.datetime.now()) + "]\n")
    file.write("public key:\n")
    file.write(str(e) + ", " + str(n) + "\n")
    file.write("private key:\n")
    file.write(str(d) + ", " + str(n) + "\n")
    file.close()
    print("key generation successful (length: " + str(n.bit_length()) + " bits)")

def get_private_key():
    ''' retrieves private key from KEYDIR/keys.txt

    Returns:
        private key as tuple (e, n) where e is private exponent and n is modulus

    Raises:
        IOError if KEYDIR/keys.txt could not be opened
    '''
    keyPath = os.path.join(KEYDIR, "keys.txt")
    try:
        file = open(keyPath, "r")
    except IOError:
        raise IOError("Could not open " + keyPath)
    else:
        specifier = "private key:"
        for line in file:
            if specifier in line:
                keyParts = next(file).split(", ")
                e = int(keyParts[0])
                n = int(keyParts[1])
                privateKey = (e, n)
                file.close()
                return privateKey

def get_public_key():
    ''' retrieves public key from KEYDIR/keys.txt

    Returns:
        public key as tuple (d, n) where d is public exponent and n is modulus

    Raises:
        IOError if KEYDIR/keys.txt could not be opened
    '''
    keyPath = os.path.join(KEYDIR, "keys.txt")
    try:
        file = open(keyPath, "r")
    except IOError:
        raise IOError("Could not open " + keyPath)
    else:
        specifier = "public key:"
        for line in file:
            if specifier in line:
                keyParts = next(file).split(", ")
                d = int(keyParts[0])
                n = int(keyParts[1])
                publicKey = (d, n)
                file.close()
                return publicKey

def encrypt(plaintext, e, n):
    ''' encrypts a plaintext string using the supplied key

    Accepts:
        tuple *key = public key as found by get_public_key
        string plaintext = text to encrypt

    Returns:
        string of ciphertext where each encrypted character is separated by a space
    '''
    cipher = ''
    for char in plaintext:
        val = pow(ord(char), e, n)
        cipher += str(val) + ' '
    return cipher

def decrypt(ciphertext, d, n):
    ''' decrypts a cipher using the supplied key

    Accepts:
        tuple *key = private key as found by get_private_key
        string ciphertext = string of integers representing an encrypted message

    Returns:
        string of plaintext corresponding to decrypted message
    '''
    plaintext = ''
    for cipherChar in ciphertext.split(' ')[:-2]:
        plaintext += chr(pow(int(cipherChar), d, n))
    return plaintext

def encrypt_file(filename):
    ''' encrypts the contents of a plaintext .txt file

    Accepts:
        string filename = the name of the file to encrypt, including .txt extension

    Returns:
        void.  Replaces contents of file with encrypted cipher text and adds .enc extension

    Raises:
        OSError if file is already encrypted (already has .enc extension)
    '''
    if (filename[-4:] == ".enc"):
        raise OSError(filename + " already encrypted")

    (e, n) = get_public_key()
    with open(filename, "r") as readFile:
        contents = []
        for line in readFile:
            contents.append(encrypt(line, e, n))

    with open(filename, "w") as writeFile:
        writeFile.writelines(contents)
    os.rename(filename, filename + ".enc")

def decrypt_file(filename):
    ''' decrypts the contents of an encrypted file

    Accepts:
        string filename = the name of the file to decrypt (including extension)

    Returns:
        void.  Replaces contents of file with decrypted plaintext and removes .enc extension

    Raises:
        OSError if file is not encrypted (does not have .enc extension)
    '''
    if (filename[-4:] != ".enc"):
        raise OSError(filename + " not encrypted")

    (d, n) = get_private_key()
    with open(filename, "r") as readFile:
        contents = []
        for line in readFile:
            contents.append(decrypt(line, d, n))


    with open(filename, "w") as writeFile:
        writeFile.writelines(contents)
    os.rename(filename, filename[:-4])

def encrypt_directory(path):
    ''' recursively encrypts the contents of a directory

    Accepts:
        string path = the directory to encrypt.

    Returns:
        void.  Encrypts each file stored under the supplied directory in-place.  Skips files that
            have already been encrypted.
    '''
    path = os.path.join(os.getcwd(), path)
    if (os.path.isfile(path)):
        try:
            encrypt_file(path)
        except OSError:
            print(path + " is already encrypted")
    else:
        children = os.listdir(path)
        for child in children:
            childPath = os.path.join(path, child)
            encrypt_directory(childPath)

def decrypt_directory(path):
    ''' recursively decrypts the contents of a directory

    Accepts:
        string path = the directory to decrypt

    Returns:
        void.  Decrypts each file stored under the supplied directory in-place.  Skips files that
            are not encrypted.
    '''
    path = os.path.join(os.getcwd(), path)
    if (os.path.isfile(path)):
        try:
            decrypt_file(path)
        except OSError:
            print(path + " is not encrypted")
    else:
        children = os.listdir(path)
        for child in children:
            childPath = os.path.join(path, child)
            decrypt_directory(childPath)

if __name__ == "__main__":
    main()
