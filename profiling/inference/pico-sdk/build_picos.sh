#!/bin/bash

set -e 

echo "Building for Pico W..."
mkdir -p build_pico1
cd build_pico1
cmake -DPICO_BOARD=pico_w ..
make person_detection micro_speech_small micro_speech_large vww -j8
cd ..

echo "Building for Pico 2..."
mkdir -p build_pico2
cd build_pico2
cmake -DPICO_BOARD=pico2 ..
make person_detection micro_speech_small micro_speech_large vww -j8
cd ..

echo "Build complete!"
echo "Pico W build: build_pico1/"
echo "Pico 2 build: build_pico2/"