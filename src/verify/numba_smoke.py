import numpy as np, numba, sys
from numba import njit, prange
@njit(parallel=True, cache=False)
def f(n):
    s = 0.0
    for i in prange(n):
        s += np.sqrt(i)
    return s
r = f(1_000_000)
print("py", sys.version.split()[0], "numba", numba.__version__, "result", round(r, 1), "OK" if abs(r-666666166.5)<1e3 else "CHECK")
