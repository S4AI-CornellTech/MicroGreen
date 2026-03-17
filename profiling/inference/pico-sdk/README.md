## Setup

[build_picos.sh](./build_picos.sh) will build all the examples for the pico w and pico 2w in
`build_pico1|2/examples`

you can flash them to your board using [picotool](https://github.com/raspberrypi/picotool)

`picotool load micro_speech_large.uf2 --force`

`picotool load micro_speech_small.uf2 --force`

you can view the results on the serial monitor, i use the one that comes with platformio
just check the port with `pio device list`
`pio device monitor --port /dev/PORT --baud 115200`