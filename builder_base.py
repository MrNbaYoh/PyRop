import traceback
import os
import sys
from chain import Chain
from builder_module import *


def create_builder(name, *bases):
    def init(self):
        for base in bases:
            base.__init__(self)
    builder = type(name, tuple(bases), {"__init__": init})
    return builder()


class IncludeModule(BuilderModule):
    def __init__(self):
        super().__init__()
        self.current_path = ""

    def set_base_path(self, base_path):
        self.current_path = os.path.dirname(os.path.abspath(base_path))

    @user_function
    def include(self, incfile: str):

        old = self.current_path
        self.current_path = os.path.join(old, os.path.dirname(incfile))

        path = os.path.join(self.current_path, os.path.basename(incfile))

        try:
            exec(compile(open(path, "rb").read(), path, 'exec'), self.user_functions)
        except Exception as err:
            print("An exception occured while building: ", file=sys.stderr)
            lines = traceback.format_exc(None, err).splitlines()
            print("  " + lines[-1], file=sys.stderr)
            for l in lines[3:-1]:
                print(l, file=sys.stderr)
            exit(1)

        self.current_path = old


class BaseBuilder(IncludeModule):
    def __init__(self):
        super().__init__()
        self.chain = Chain()

    def append(self, bytes_l):
        self.chain.append(bytes_l)

    def add_value(self, word: int, byte_size: int = 4):
        if byte_size < 1:
            raise ValueError("Size of word should be greater than zero!")

        bit_size = byte_size * 8
        if word.bit_length() > bit_size:
            raise ValueError("Value does not fit in a " + str(bit_size) + "bits word!")

        self.append(word.to_bytes(byte_size, 'little'))

    @user_function
    def add_word(self, word):
        self.add_value(word, 4)

    @user_function
    def add_halfword(self, word):
        self.add_value(word, 2)

    @user_function
    def add_byte(self, byte):
        self.add_value(byte, 1)

    @user_function
    def incbin(self, incfile: str):
        self.append(open(incfile, 'rb').read())

    @user_function
    def org(self, address: int):
        if address < self.chain.get_sp():
            raise ValueError("Trying to ORG backwards!")

        self.append([0x0 for i in range(address - self.chain.get_sp())])

    @user_function
    def align(self, value: int):
        self.append([0 for i in range(value - (len(self.chain) % value))])

    @user_function
    def fill(self, size: int, value: int, v_byte_size: int = 1):
        if v_byte_size < 1:
            raise ValueError("Size of value should be greater than zero!")

        bit_size = v_byte_size * 8
        if value.bit_length() > bit_size:
            raise ValueError("Value does not fit in a " + str(bit_size) + "bits word!")

        self.append((value.to_bytes(v_byte_size, 'little') * ((size // v_byte_size) + 1))[:size])

    @user_function
    def add_ascii(self, string: str):
        self.add_str(string)

    @user_function
    def add_utf16(self, string: str):
        self.add_str(string, 'utf_16_le')

    @user_function
    def add_str(self, string: str, encoding: str = 'us-ascii'):
        self.append([c for c in string.encode(encoding)])

    def build(self, file):
        if self.chain.built:
            raise PermissionError("You cannot build multiple times!")

        if not self.chain.loaded:
            self.load(file)

        self.include(file)
        self.chain.built = True

    def load(self, file):
        if self.chain.loaded:
            return

        self.include(file)
        self.chain.loaded = True
