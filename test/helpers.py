import unittest 

def catchAndSkip(signature, message=None):
    def _decorator(f):
        def _wrapper(self):
            try:
                return f(self)
            except signature as err:
                raise unittest.SkipTest(message or err)
        return _wrapper
    return _decorator

