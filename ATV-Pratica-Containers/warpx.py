
Stage0 += baseimage(image='ubuntu:24.04')

Stage0 += apt_get(ospackages=[
    'build-essential',
    'ca-certificates',
    'ccache',
    'cmake',
    'g++',
    'git',
    'wget',
    'unzip',
    'libfftw3-mpi-dev',
    'libfftw3-dev',
    'libhdf5-openmpi-dev',
    'libopenmpi-dev',
    'pkg-config',
    'python3',
    'python3-dev',
    'python3-matplotlib',
    'python3-mpi4py',
    'python3-numpy',
    'python3-pandas',
    'python3-pip',
    'python3-scipy',
    'python3-venv',
])

Stage0 += shell(commands=[
    'set -e',
    'mkdir -p /hpc',
    'cd /hpc',
    'wget -q https://github.com/BLAST-WarpX/warpx/archive/refs/tags/26.10.zip -O 26.10.zip',
    'unzip -q 26.10.zip',
    'mv warpx-26.10 warpx-src',
    'rm 26.10.zip',
    'python3 -m venv --system-site-packages /hpc/warpx-venv',
])

Stage0 += environment(variables={
    'PATH': '/hpc/warpx-venv/bin:/hpc/warpx/bin:$PATH',
})

Stage0 += shell(commands=[
    'set -e',
    '/hpc/warpx-venv/bin/python -m pip install -U pip build packaging "setuptools[core]" wheel cmake',
    '/hpc/warpx-venv/bin/python -m pip install -r /hpc/warpx-src/requirements.txt',
    'cmake -S /hpc/warpx-src -B /hpc/warpx-build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/hpc/warpx -DPython_EXECUTABLE=/hpc/warpx-venv/bin/python -DWarpX_MPI=ON -DWarpX_COMPUTE=OMP -DWarpX_DIMS=3 -DWarpX_PYTHON=ON',
    'cmake --build /hpc/warpx-build --parallel 2',
    'cmake --install /hpc/warpx-build',
    'cmake --build /hpc/warpx-build --target pip_install --parallel 2',
])

Stage0 += runscript(commands=['/bin/bash'])
