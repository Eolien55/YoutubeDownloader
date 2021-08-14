from typing import Iterable


def Frontend(callback, target):
    """Ultra generic frontend for generators"""

    def frontend(*args, **kwargs):
        for i in target(*args, **kwargs):
            if i:
                if isinstance(i, Iterable):
                    callback(*i)
                else:
                    callback(i)

    return frontend
