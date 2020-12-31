from lazy_object_proxy import Proxy


def lazy_class(cls):
    class Lazy():
        def __new__(cls, *args, **kwargs):
            orig_cls = type(cls.__name__, (cls,), {})
            orig_cls.__new__ = lambda cl_, *args, **kwargs: object.__new__(cl_)
            return Proxy(lambda: orig_cls(*args, **kwargs))
    lazy_class = type(cls.__name__, (cls, Lazy), {})
    return lazy_class
