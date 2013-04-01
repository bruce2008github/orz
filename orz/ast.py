class BaseField(object):

    def set_name(self, name):
        self._name = name

    def __get__(self, instance, owner):
        if instance is not None:
            return instance._data[self._name]
        return self

    def __set__(self, instance, value):
        instance._data[self._name] = value


class ValueField(BaseField):

    def __init__(self, type):
        self._type = type

    def __set__(self, instance, value):
        assert isinstance(value, self._type), self._name
        super(ValueField, self).__set__(instance, value)


class NodeField(ValueField):
    _instance_counter = 0

    def __init__(self, type):
        super(NodeField, self).__init__(type)
        NodeField._instance_counter += 1
        self._instance_id = NodeField._instance_counter


class NodeListField(NodeField):

    def __set__(self, instance, value):
        assert all(isinstance(v, self._type) for v in value), self._name
        super(ValueField, self).__set__(instance, value)


class NodeBase(type):
    def __new__(cls, name, bases, attrs):
        all_fields = []
        fields = []

        for k,v in attrs.items():
            if isinstance(v, BaseField):
                v.set_name(k)
                all_fields.append(k)
                if isinstance(v, NodeField):
                    fields.append(v)

        fields.sort(key=lambda f: f._instance_id)
        attrs['_node_fields'] = tuple(f._name for f in fields)
        attrs['_all_fields'] = tuple(all_fields)

        attrs['__visit_name__'] = attrs.get('__visit_name__', name)
        return type.__new__(cls, name, bases, attrs)


class Node(object):
    __metaclass__ = NodeBase

    def __init__(self, lineno, col_offset, **kwargs):
        self._data = {}
        self.lineno = lineno
        self.col_offset = col_offset

        assert all(k in self._all_fields for k in kwargs)
        assert all(k in kwargs for k in self._all_fields)

        for k,v in kwargs.items():
            setattr(self, k, v)
