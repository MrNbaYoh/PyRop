class Chain:

    def __init__(self):
        self.chain = []

        self.stack_pointer = 0x0
        self.loaded = False
        self.built = False

    def __repr__(self):
        return self.chain

    def __str__(self):
        """
        String conversion
        :return: string conversion of self.chain
        """
        return str(self.chain)

    def append(self, other):
        """
        Add a list of bytes at the end of the chain.
        :param other: bytes list
        :return: None
        """
        if self.loaded:
            self.chain += other
        self.stack_pointer += len(other)
        return self

    def __len__(self):
        """
        Override "len" operator.
        :return: chain length
        """
        return len(self.chain)

    def get_sp(self):
        """
        Get current stack_pointer.
        :return: stack_pointer value
        """
        return self.stack_pointer

    def set_sp(self, addr):
        """
        Set current stack_pointer.
        :param addr: new SP
        :return: None
        """
        self.stack_pointer = addr

    def add_sp(self, val):
        """
        Add value to the current stack_pointer.
        :param val: value to add
        :return: None
        """
        self.stack_pointer += val

    def is_built(self):
        return self.built

    def __bytes__(self):
        return bytes(self.chain)
