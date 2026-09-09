"""ctypes bridge to the production C contract.

The bridge is intentionally tiny. Experiments can fail closed if the C library
cannot be built, rather than silently switching implementations.
"""
from __future__ import annotations
import ctypes, os, subprocess
from pathlib import Path
from functools import lru_cache

ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/"build"/"libtiku_utility.so"
SRC=ROOT/"upstream"/"tikuOS"/"kernel"/"utility"/"tiku_utility.c"

class CHint(ctypes.Structure):
    _fields_=[("utility_q16",ctypes.c_uint16),("deadline_tick",ctypes.c_uint32),
              ("cost_cycles",ctypes.c_uint32),("flags",ctypes.c_uint8),
              ("valid",ctypes.c_uint8)]

def build() -> Path:
    LIB.parent.mkdir(exist_ok=True)
    patched=ROOT/"build"/"tikuOS-patched"
    # Always materialize from the checked-in clean snapshot before applying the
    # patch. This prevents a stale build directory from making parity tests
    # silently exercise an already-patched tree.
    import shutil
    if patched.exists(): shutil.rmtree(patched)
    shutil.copytree(ROOT/"upstream"/"tikuOS",patched)
    patch=ROOT/"patches"/"0001-information-utility-scheduler.patch"
    subprocess.run(["patch","-p1","--forward","--input",str(patch)],
                   cwd=patched,check=True,stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE,text=True)
    src=patched/"kernel"/"utility"/"tiku_utility.c"
    cmd=["gcc","-std=c11","-O2","-fPIC",
         "-shared","-Wall","-Wextra","-Werror",
         "-I",str(ROOT/"tests"/"c_host"/"include"),"-I",str(patched),
         str(src),str(ROOT/"tests"/"c_host"/"atomic_stubs.c"),"-o",str(LIB)]
    subprocess.run(cmd,check=True)
    return LIB

@lru_cache(maxsize=1)
def load():
    path=build()
    lib=ctypes.CDLL(str(path))
    lib.tiku_utility_score.argtypes=[ctypes.POINTER(CHint)]
    lib.tiku_utility_score.restype=ctypes.c_uint32
    lib.tiku_utility_deadline_eligible.argtypes=[ctypes.POINTER(CHint),ctypes.c_uint32]
    lib.tiku_utility_deadline_eligible.restype=ctypes.c_int
    return lib

def score_exact(hint) -> int:
    from .contract import UtilityHint
    if not isinstance(hint, UtilityHint): raise TypeError("hint must be UtilityHint")
    lib=load()
    ch=CHint(hint.utility_q16,hint.deadline_tick,hint.cost_cycles,hint.flags,1)
    return int(lib.tiku_utility_score(ctypes.byref(ch)))
