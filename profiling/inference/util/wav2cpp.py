import os
import struct
import wave
import sys


def wav_to_cpp(wav_file, output_name=None):

    if output_name is None:
        base_name = os.path.splitext(os.path.basename(wav_file))[0]
        output_name = f"{base_name}_audio_data"
    
    # Read WAV
    with wave.open(wav_file, 'r') as w:
        frames = w.readframes(w.getnframes())
        samples = struct.unpack(f'<{w.getnframes() * w.getnchannels()}h', frames)
    
    # Generate header
    header_content = f"""#pragma once
#include <cstdint>

constexpr unsigned int {output_name}_len = {len(samples)};
extern const int16_t {output_name}[];
"""
    
    # Generate source file
    samples_str = ',\n    '.join(str(s) for s in samples)
    source_content = f"""#include "{output_name}.h"

alignas(16) const int16_t {output_name}[] = {{
    {samples_str}
}};
"""
    

    with open(f"{output_name}.h", 'w') as f:
        f.write(header_content)
    
    with open(f"{output_name}.cc", 'w') as f:
        f.write(source_content)
    
    print(f"Generated: {output_name}.h and {output_name}.cc")
    print(f"Array size: {len(samples)} samples")


def main():
    if len(sys.argv) < 2:
        print("Usage: python wav_to_cpp.py <input.wav> [output_name]")
        sys.exit(1)
    
    wav_file = sys.argv[1]
    output_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not wav_file.endswith('.wav'):
        print("Error: Input must be a .wav file")
        sys.exit(1)
    
    if not os.path.exists(wav_file):
        print(f"Error: File {wav_file} not found")
        sys.exit(1)
    
    wav_to_cpp(wav_file, output_name)


if __name__ == '__main__':
    main()