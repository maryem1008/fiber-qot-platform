#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
PREFIX=/usr/local
SOURCE_DIR="$ROOT/.cache/native/oopt-gnpy-libyang"
BINDING_COMMIT=26a9f5a559c44bf9c07f8917e5b724ec2780db49

if [ "$(uname -m)" != "aarch64" ]; then
  echo "This helper is only for Linux ARM64. On platforms with a compatible wheel, use the README install command." >&2
  exit 2
fi
if [ ! -x "$PYTHON" ]; then
  echo "Python environment not found at $PYTHON. Create .venv first or set PYTHON." >&2
  exit 2
fi

PY_MINOR="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
sudo apt-get update
sudo apt-get install -y build-essential cmake ninja-build pkg-config libpcre2-dev libcmocka-dev doctest-dev "python${PY_MINOR}-dev"

"$PYTHON" -m pip install 'pybind11[global]>=2.9.1,<3'

if [ ! -d "$SOURCE_DIR/.git" ]; then
  mkdir -p "$(dirname "$SOURCE_DIR")"
  git clone https://github.com/Telecominfraproject/oopt-gnpy-libyang.git "$SOURCE_DIR"
fi
git -C "$SOURCE_DIR" fetch origin
git -C "$SOURCE_DIR" checkout --detach "$BINDING_COMMIT"
git -C "$SOURCE_DIR" submodule sync --recursive
git -C "$SOURCE_DIR" submodule update --init --recursive

rm -rf "$ROOT/.cache/native/build-libyang" "$ROOT/.cache/native/build-libyang-cpp"
cmake -S "$SOURCE_DIR/libyang" -B "$ROOT/.cache/native/build-libyang" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DENABLE_TESTS=OFF
cmake --build "$ROOT/.cache/native/build-libyang" --parallel 4
sudo cmake --install "$ROOT/.cache/native/build-libyang"

cmake -S "$SOURCE_DIR/libyang-cpp" -B "$ROOT/.cache/native/build-libyang-cpp" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$PREFIX" \
  -DCMAKE_INSTALL_PREFIX="$PREFIX"
cmake --build "$ROOT/.cache/native/build-libyang-cpp" --parallel 4
sudo cmake --install "$ROOT/.cache/native/build-libyang-cpp"
sudo ldconfig

PYBIND11_CMAKE_DIR="$("$PYTHON" -m pybind11 --cmakedir)"
PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig" \
CMAKE_PREFIX_PATH="$PREFIX:$PYBIND11_CMAKE_DIR" \
LD_LIBRARY_PATH="$PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
  "$PYTHON" -m pip install -e "$ROOT[dev]" --extra-index-url https://download.pytorch.org/whl/cpu
