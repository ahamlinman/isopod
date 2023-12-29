from setuptools import Extension, setup
from Cython.Build import cythonize


setup(
    ext_modules=cythonize(
        [
            Extension(
                name="isopod.cdrom.constants",
                sources=["isopod/cdrom/constants.pyx"],
            )
        ]
    )
)
