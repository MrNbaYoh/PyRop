modules_user_functions = dict()


def user_function(func):
    infos = func.__qualname__.rsplit('.', 1)
    modules_user_functions.setdefault(infos[0], dict())
    modules_user_functions[infos[0]][infos[1]] = func
    return func


class BuilderModule:
    def __init__(self):
        self.user_functions = dict()
        for base in reversed(self.__class__.__mro__):
            #print(base)
            base_user_func = modules_user_functions.get(base.__qualname__, dict())
            self.user_functions.update({name: base.__dict__[name].__get__(self, self.__class__)
                                        for name, func in base_user_func.items()})
