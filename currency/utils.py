# -*- coding: utf-8 -*-
from functools import wraps

from django.core.cache import cache


def _memoize_result(owner_obj=None, func=None, memoize_key=None,
                    args=None, kwargs=None):
    if owner_obj:
        try:
            cache_dict = owner_obj._mm
        except AttributeError:
            cache_dict = {}
            owner_obj._mm = cache_dict
        try:
            res = cache_dict[memoize_key]
        except KeyError:
            if args is None:
                args = []
            if kwargs is None:
                kwargs = {}
            res = func(*args, **kwargs)
            cache_dict[memoize_key] = res
    else:
        res = func(*args, **kwargs)

    return res


def memoize_for_object(func):
    '''
    The 'memoize_for_object' decorator runs the wrapped object's method just
    once for each argument set and stores the result in the hidden property of
    the object.

    The remembered result will be returned on subsequent method's calls instead
    of recalculating it.

    The decorator creates separate results cache for each object's instance and
    stores it in the '_mm' property of the object.

    '''
    key = func.__name__

    @wraps(func)
    def inner(self, *args, **kwargs):
        key_args = (
            key + (str(args) if args else '') + (str(kwargs) if kwargs else '')
        )

        return _memoize_result(owner_obj=self,
                               func=func,
                               memoize_key=key_args,
                               args=(self,) + args,
                               kwargs=kwargs)
    return inner


def simple_cache(key_format, kwargs_key_format=None, expire=86400):
    """Build key with key_format.format(*args, **kwargs) and first try to get it
    from cache, then from function call. Default cache expiry time is 1 day.

    kwargs_key_format is optional argument to support building cache key from
    kwargs.

    cached function does not support mixed kwargs/args calling: only one of them
    can be uses.

    """

    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            if args and kwargs:
                raise TypeError("Cached function call only accepts args or kwargs, not both")
            if kwargs and not kwargs_key_format:
                raise TypeError("Cached function without specified `kwargs_key_format` does not support calling with kwargs ")
            if args:
                key = key_format.format(*args)
            elif kwargs:
                key = kwargs_key_format.format(**kwargs)

            result = cache.get(key)
            if not result:
                result = func(*args, **kwargs)
                cache.set(key, result, expire)
            return result
        return inner
    return wrapper
