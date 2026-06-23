#!/bin/bash

set -e

# PICO_BUILD_TYPE (a CMAKE_BUILD_TYPE: Release=-O3, RelWithDebInfo=-O2,
# MinSizeRel=-Os, Debug=-O0). Defaults to Release (-O3).
BUILD_TYPE="${PICO_BUILD_TYPE:-Release}"
echo "Build type (optimization): ${BUILD_TYPE}"

echo "Building for Pico W..."
mkdir -p build_pico1
cd build_pico1
cmake -DPICO_BOARD=pico_w -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" ..
make person_detection micro_speech_small micro_speech_large vww -j8
cd ..

echo "Building for Pico 2..."
mkdir -p build_pico2
cd build_pico2
cmake -DPICO_BOARD=pico2 -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" ..
make person_detection micro_speech_small micro_speech_large vww -j8
cd ..

echo "Build complete!"
echo "Pico W build: build_pico1/"
echo "Pico 2 build: build_pico2/"