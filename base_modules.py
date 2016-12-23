from builder_base import BaseBuilder
from builder_module import user_function


class AreaModule(BaseBuilder):
    def __init__(self):
        super().__init__()
        self.areas = []

    @user_function
    def append(self, bytes_l):
        super().append(bytes_l)
        self.check_areas()

    @user_function
    def begin_area(self, size):
        if not self.chain.loaded:
            return
        self.areas.append((len(self.chain), size))

    @user_function
    def end_area(self):
        if not self.chain.loaded:
            return
        self.areas.pop()

    def check_areas(self):
        for area in self.areas:
            if len(self.chain)-area[0] > area[1]:
                raise OverflowError("Area overflowed!")


class LabelContext:
    def __init__(self, parent, l_locals):
        self.locals = l_locals
        self.parent = parent

    def setdefault(self, key, value):
        self.locals.setdefault(key, value)

    def __getitem__(self, item):
        """
        Return the value associated to the label name in the nearest context that contains it.
        (search in context then context's parent and then parents of context's parent...)
        :param item: label name
        :return: address associated to the label
        """
        current = self
        while current is not None:
            if item in current.locals:
                return current.locals[item]
            current = current.parent

    def __contains__(self, item):
        """
        Override 'in' operator, search the label in the local dict and all the parents dicts.
        :param item: label to search
        :return: True if label is found, False otherwise
        """
        current = self
        while current is not None:
            if item in current.locals:
                return True
            current = current.parent
        return False


class Macro:

    def __init__(self):
        self.total_count = 0
        self.current_instance = 0
        self.instance_contexts = []

    def add_instance(self, context):
        """
        Add a new instance.
        :param context: instance label context
        :return: None
        """
        self.instance_contexts.append(context)
        self.total_count += 1

    def reset_current_instance(self):
        """
        Reset the current_instance counter.
        :return: None
        """
        self.current_instance = 0

    def get_last_instance(self):
        """
        Get the last instance added.
        :return: macro's last instance
        """
        return self.instance_contexts[-1]

    def get_next_instance(self):
        """
        Get the current instance, then increment the current_instance value.
        :return: current instance label context
        """
        self.current_instance += 1
        return self.instance_contexts[self.current_instance - 1]

from ast import *
from inspect import *

class LabelModule(BaseBuilder):
    def __init__(self):
        super().__init__()

        self.context_stack = []

        self.global_context = dict()
        self.current_context = self.global_context

        self.macros = dict()

    def load(self, file):
        tree = parse(open(file).read(), "<ast>", 'exec')
        for node in walk(tree):
            if isinstance(node, Call) and node.func.id == "put_label" and node.args and isinstance(node.args[0], Str):
                name = node.args[0].s
                if name in self.global_context:
                    raise NameError("Label name already used!")
                self.global_context.setdefault(name, 0)
        self.user_functions.update(self.global_context)
        super().load(file)
        self.user_functions.update(self.global_context)

    def __setitem__(self, name: str, address: int):
        """
        Add a label to the current context.
        Override [] assignment.
        :param name: label name
        :param address: label address
        :return: None
        """
        if self.chain.loaded:
            return

        if address is None:
            address = self.chain.get_sp()
        elif address.bit_length() > 32:
            raise ValueError("Label address should be 32 bits long!")

        self.current_context[name] = address

    def __getitem__(self, name):
        """
        Get address associated to the label name in current_context.
        :param name: label name
        :return: address associated to label
        """
        if name not in self.current_context:
            raise KeyError("Trying to use an undefined label!")
        return self.current_context[name]

    def __contains__(self, item):
        """
        Override 'in' operator.
        :param item: label name
        :return: True if current_context contains the label, False otherwise
        """
        return item in self.current_context

    def get_current_context(self):
        return self.current_context

    def register_macro(self, name: str):
        """
        Register a new macro in the macros dict.
        :param name: macro's name
        :return: None
        """
        self.macros.setdefault(name, Macro())

    def add_macro_context(self, name: str, context: dict = None):
        """
        Add a new instance/context to a Macro object
        :param name: macro's name
        :param context: macro's label context, default = dict()
        :return: None
        """
        if context is None:
            context = dict()
        self.macros[name].add_instance(dict())

    def switch_context(self, context):
        """
        Switch the current context.
        :param context: the new context
        :return: None
        """
        self.context_stack.append(self.current_context)
        self.current_context = context

    def restore_context(self):
        """
        Restore the previous context.
        :return: None
        """
        self.current_context = self.context_stack.pop()

    @user_function
    def put_label(self, name: str, address: int = None):
        if type(name) is not str:
            raise ValueError("Label name expected, " + type(name).__name__ + " was given!")
        self[name] = address

    @user_function
    def get_label(self, name: str):
        return self[name]

    @user_function
    def macro(self, func):
        """
        The macro function decorator.
        :param func: macro function
        :return: the wrapped function
        """
        self.register_macro(func.__name__)

        def wrapper(*args, **kwargs):
            if not self.chain.loaded:
                self.add_macro_context(func.__name__)
                self.switch_context(self.macros[func.__name__].get_last_instance())
                tree = parse(getsource(func), "<ast>", 'exec')
                for node in walk(tree):
                    if isinstance(node, Call) and node.func.id == "put_label" and node.args and isinstance(node.args[0],
                                                                                                           Str):
                        name = node.args[0].s
                        if name in self.current_context:
                            raise NameError("Label name already used!")
                        self.current_context.setdefault(name, 0)

            else:
                self.switch_context(self.macros[func.__name__].get_next_instance())

            old = func.__globals__.copy()
            func.__globals__.update(self.current_context)
            func(*args, **kwargs)
            func.__globals__.clear()
            func.__globals__.update(old)

            self.restore_context()

        return wrapper


class PopModule(BaseBuilder):
    def __init__(self):
        super().__init__()
        self.pop_macros = dict()

    @user_function
    def pop_macro(self, func):
        args = func.__code__.co_varnames
        if set(args) - {"r"+str(i) for i in range(16)}:
            raise Exception("Non register argument found in pop_macro!")
        self.pop_macros[func.__name__] = (func, set(args))
        return func

    @user_function
    def pop(self, **registers):
        reg_set = set(registers.keys())
        if reg_set - {"r"+str(i) for i in range(16)}:
            raise Exception("Trying to pass non register argument to a pop_macro!")
        candidates = {name: infos for name, infos in self.pop_macros.items() if infos[1] & reg_set}
        pop_stack = []
        while reg_set:
            pop_stack.append(self.find_best(candidates, reg_set))
            if pop_stack[-1] is None:
                raise Exception("Could not find pop_macro to pop register(s): " + str(reg_set))
            reg_set -= self.pop_macros[pop_stack[-1]][1]
        for func in pop_stack:
            candidates[func][0](**{reg: value for reg, value in registers.items() if reg in candidates[func][1]})

    def find_best(self, candidates, regs):
        maxi = 0
        name = None
        for func, infos in candidates.items():
            nb = len(regs & infos[1])
            if nb == 0:
                continue
            if nb > maxi or (nb == maxi and len(candidates[name][1]) > len(candidates[func][1])):
                maxi = nb
                name = func
        return name
