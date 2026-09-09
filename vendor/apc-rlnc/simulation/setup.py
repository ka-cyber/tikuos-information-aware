"""
Build the Cython-accelerated GF(256) extension:
    python setup.py build_ext --inplace
"""
from setuptools import setup, Extension

try:
    from Cython.Build import cythonize
    import numpy as np

    extensions = [
        Extension(
            "coding.gf256_accel",
            ["coding/gf256_accel.pyx"],
            include_dirs=[np.get_include()],
        )
    ]
    ext_modules = cythonize(extensions, language_level=3)
except ImportError:
    print("Cython/NumPy not available at build time -- skipping accelerated "
          "extension. The pure-Python coding/gf256.py path still works.")
    ext_modules = []

setup(
    name="apc-rlnc-simulation",
    version="0.1.0",
    description="APC-RLNC discrete-event simulator",
    ext_modules=ext_modules,
)
