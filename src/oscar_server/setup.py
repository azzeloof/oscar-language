import os

# Create the build directory if it doesn't exist
if not os.path.exists('build'):
    os.makedirs('build')


import sys
import urllib.request
import zipfile
import subprocess
import glob
from pybind11.setup_helpers import Pybind11Extension, build_ext as _build_ext
from setuptools import setup

class build_ext(_build_ext):
    def run(self):
        if sys.platform == 'win32':
            pa_dir = os.path.abspath("build/portaudio")
            build_dir = os.path.join(pa_dir, "cmake_build")
            
            # Find the compiled library
            lib_files = glob.glob(os.path.join(build_dir, "**", "*portaudio*.*"), recursive=True)
            lib_files = [f for f in lib_files if f.endswith('.a') or f.endswith('.lib')]
            
            if not lib_files:
                print("Downloading and building PortAudio for Windows...")
                os.makedirs(pa_dir, exist_ok=True)
                zip_path = os.path.join(pa_dir, "portaudio.zip")
                if not os.path.exists(zip_path):
                    urllib.request.urlretrieve(
                        "https://github.com/PortAudio/portaudio/archive/refs/tags/v19.7.0.zip", 
                        zip_path
                    )
                
                src_dir = os.path.join(pa_dir, "src")
                if not os.path.exists(src_dir):
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(pa_dir)
                    os.rename(os.path.join(pa_dir, "portaudio-19.7.0"), src_dir)
                
                os.makedirs(build_dir, exist_ok=True)
                
                subprocess.check_call(
                    ["cmake", "../src", "-G", "Visual Studio 17 2022", "-A", "x64", "-DCMAKE_BUILD_TYPE=Release", "-DPA_BUILD_SHARED=OFF", "-DPA_BUILD_STATIC=ON"],
                    cwd=build_dir
                )
                subprocess.check_call(
                    ["cmake", "--build", ".", "--config", "Release"],
                    cwd=build_dir
                )
                
                lib_files = glob.glob(os.path.join(build_dir, "**", "*portaudio*.*"), recursive=True)
                lib_files = [f for f in lib_files if f.endswith('.a') or f.endswith('.lib')]

            if lib_files:
                lib_path = lib_files[0]
                lib_dir = os.path.dirname(lib_path)
                lib_name = os.path.basename(lib_path)
                if lib_name.startswith('lib') and lib_name.endswith('.a'):
                    lib_name = lib_name[3:-2]
                elif lib_name.endswith('.lib'):
                    lib_name = lib_name[:-4]
                elif lib_name.endswith('.a'):
                    lib_name = lib_name[:-2]

                for ext in self.extensions:
                    ext.include_dirs.append(os.path.join(pa_dir, "src", "include"))
                    ext.library_dirs.append(lib_dir)
                    if "portaudio" in ext.libraries:
                        ext.libraries.remove("portaudio")
                    ext.libraries.append(lib_name)
                    # PortAudio static requires these system libraries on Windows
                    ext.libraries.extend(["winmm", "dsound", "ksuser", "advapi32", "ole32", "setupapi", "user32", "ws2_32"])

        super().run()

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