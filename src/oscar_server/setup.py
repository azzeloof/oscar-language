import os

# Create the build directory if it doesn't exist
if not os.path.exists('build'):
    os.makedirs('build')

# setup.py

import sys
from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

__version__ = "0.0.2"

# Platform-specific linker arguments
extra_link_args = []
include_dirs = []
library_dirs = []
if sys.platform == 'darwin':
    # On macOS, PortAudio might depend on CoreAudio services
    extra_link_args.extend([
        "-framework", "CoreAudio",
        "-framework", "AudioToolbox",
        "-framework", "CoreFoundation"
    ])
    include_dirs.append("/opt/homebrew/include")
    library_dirs.append("/opt/homebrew/lib")

ext_modules = [
    Pybind11Extension(
        "oscar_server",
        ["main.cpp"],
        include_dirs=include_dirs,
        library_dirs=library_dirs,
        libraries=["portaudio"],
        define_macros=[("VERSION_INFO", __version__)],
        extra_link_args=extra_link_args,
        cxx_std=17
    ),
]

setup(
    name="oscar_server",
    version=__version__,
    author="Adam Zeloof",
    author_email="adam@zeloof.xyz",
    description="A PortAudio-based audio server for Python",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.7",
    options={'build': {'build_lib': 'build/lib'}, 'egg_info': {'egg_base': 'build'}},
)