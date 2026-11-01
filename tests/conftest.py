"""One BLAS / OpenMP thread for the test session, set before numpy loads (as the fullopt scripts do): the tests' small
matrices gain nothing from threads, which only contend (R027b: 4 min user + 4 min system for 23 s of wall time)."""

import os
import sys

if "numpy" not in sys.modules:
    os.environ.update({k: "1" for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")})
