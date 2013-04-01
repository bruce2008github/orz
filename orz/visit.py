class Environment(object):
    FIELDS = None

    def __init__(self, **kwargs):
        self.__data = kwargs

    def __getattr__(self, name):
        if name in self.FIELDS:
            return self.__data.get(name, None)

        raise AttributeError

    def __call__(self, **kwargs):
        data = self.__data.copy()
        data.update(kwargs)
        return self.__class__(**data)



class Visitor(object):

    def __init__(self):
        self._visitors = {}


    def match(self, type):
        def decorator(func):
            self._visitors[type] = func
            return self
        return decorator

    def __call__(self, env, node):
        return self._visitors[type(node)](env, node)
