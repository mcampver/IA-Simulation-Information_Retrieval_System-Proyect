from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import sys
import setuptools

class get_pybind_include:
    """Helper class to determine the pybind11 include path"""
    def __str__(self):
        import pybind11
        return pybind11.get_include()

ext_modules = [
    Extension(
        'sa_solver',
        ['sa_solver.cpp'],
        include_dirs=[
            get_pybind_include(),
        ],
        language='c++',
        extra_compile_args=['-std=c++17'],
    ),
]

setup(
    name='sa_solver',
    version='0.1',
    author='Abel Ponce Gonzalez',
    author_email='abelponce03@gmail.com',
    description='VRP Solver avanzado con AG y mejoras multi-hilo',
    ext_modules=ext_modules,
    cmdclass={'build_ext': build_ext},
    zip_safe=False,
)
