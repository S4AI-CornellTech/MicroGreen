I cannot for the life of me get this to work with the STM32's FPU. I noticed it was running slower than I expected a 100MHz chip to run. I am pretty sure it has to do with [this issue](https://github.com/platformio/platform-ststm32/issues/591).

All of this might be pointless if we go with the better optimized [stm32CUBE.AI runtime?](https://community.st.com/t5/edge-ai/how-to-use-tflite-micro-runtime-with-optimized-kernel-from-cmsis/td-p/230051)

All timing and power tests are using the unoptimized kernels for now.