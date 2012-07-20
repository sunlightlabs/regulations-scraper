from multiprocessing import RLock
import multiprocessing.sharedctypes
import ctypes

class SynchronizedCounter(multiprocessing.sharedctypes.Synchronized):
    def increment(self, amount=1):
        self.acquire()
        try:
            self._obj.value += amount
        finally:
            self.release()

def Counter():
    value = multiprocessing.sharedctypes.RawValue(ctypes.c_uint)
    return SynchronizedCounter(value, RLock())