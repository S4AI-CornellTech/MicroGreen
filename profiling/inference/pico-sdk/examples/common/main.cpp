#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "pico/stdlib.h"
#include "pico/sleep.h"
#include "pico/bootrom.h"
#include "hardware/clocks.h"


// TensorFlow Lite Micro includes
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_log.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "model_config.h"

#define MARKER_PIN 15

// Safe runtime CPU-frequency range for the optimizer to sweep over
#define MIN_SYS_CLOCK_KHZ 48000u
#define MAX_SYS_CLOCK_KHZ 150000u

// Sleep callback function - does nothing, just for wakeup
void sleep_callback(uint alarm_num) {
    // Empty callback used to wake up
}

inline float DequantizeInt8ToFloat(int8_t value, float scale, int zero_point)
{
    return static_cast<float>(value - zero_point) * scale;
}

void Error_Handler(void)
{
    while (1) {
        sleep_ms(100);
    }
}

bool is_serial_connected(void)
{
    // Check if USB is connected and configured for both RP2040 and RP2350
    return stdio_usb_connected();
}

// Report the live system clock and check if the requested frequency took effect
void report_clock(void)
{
    printf("CLK sys=%lu Hz\r\n", (unsigned long)clock_get_hz(clk_sys));
}

// A requested system clock (in kHz) at runtime. Returns true if CPU frequency 
// is sucessfully set. 
// USB stdio runs off PLL_USB, so the serial link survives the clk_sys change and
// stays reachable for the next command. time_us_64() is driven by the always-on
// timer tick, so reported inference times remain valid across frequency changes.
bool set_cpu_freq_khz(uint32_t khz)
{
    if (khz < MIN_SYS_CLOCK_KHZ || khz > MAX_SYS_CLOCK_KHZ)
    {
        printf("ERR freq %lu kHz out of range [%u,%u]\r\n",
               (unsigned long)khz, MIN_SYS_CLOCK_KHZ, MAX_SYS_CLOCK_KHZ);
        return false;
    }
    stdio_flush();
    // false: return failure if no PLL/divider can produce the requested khz
    if (!set_sys_clock_khz(khz, false))
    {
        printf("ERR could not configure %lu kHz (no valid PLL/divider)\r\n",
               (unsigned long)khz);
        return false;
    }
    return true;
}

// Non-blocking serial command processor on this board's USB serial port.
// Commands (one per line, terminated by CR/LF):
//   b           reboot into BOOTSEL/USB-flash mode (re-enumerate as mass storage
//               so a new UF2 can be flashed without pressing the BOOTSEL button)
//   f<khz>      set the CPU frequency, e.g. "f100000" for 100 MHz; replies "ACK f"
//   ?           report the current system clock
// A bare 'b' (no newline) is still honored immediately to preserve the existing
// flash flow that sends a single character.
void process_serial_commands(void)
{
    static char buf[16];
    static uint8_t len = 0;
    int c;
    while ((c = getchar_timeout_us(0)) != PICO_ERROR_TIMEOUT) // drain all waiting bytes
    {
        if ((c == 'b' || c == 'B') && len == 0) // only want to reboot if buffer is empty
        {
            printf("Rebooting into BOOTSEL mode for flashing...\r\n");
            stdio_flush();
            reset_usb_boot(0, 0);
        }

        if (c == '\r' || c == '\n') // checks for the end of a command
        {
            if (len == 0)
            {
                continue;
            }
w
                case 'f':
                case 'F':
                char *freq_str = buf + 1; // skip the 'f' character
                uint32_t freq = (uint32_t)strtoul(freq_str, NULL, 10);
                if (set_cpu_freq_khz(freq))
                {
                    printf("ACK f ");
                    report_clock();
                }
                break;
                case '?':
                    report_clock();
                    break;
                default:
                    printf("ERR unknown cmd '%s'\r\n", buf);
                    break;
            }
            len = 0;
        }
        else if (len < sizeof(buf) - 1)
        {
            buf[len++] = (char)c;
        }
        else
        {
            len = 0; // overflow: drop the malformed line
        }
    }
}

void enter_sleep_cycle(void)
{
    printf("Preparing to sleep for 2 seconds...\r\n");

    // Light sleep for BOTH the RP2040 and RP2350 that keeps the clocks and USB alive
    // so the board stays enumerated and reachable for automated flashing.
    // This is NOT a true low-power sleep
    stdio_flush();
    sleep_ms(2000);
    printf("Woke up from light sleep\r\n");
}

int main(void)
{
    stdio_init_all();
    
    gpio_init(MARKER_PIN);
    gpio_set_dir(MARKER_PIN, GPIO_OUT);
    gpio_put(MARKER_PIN, 0);

    printf("\r\n=== Starting %s Model Test with Sleep Cycles ===\r\n", ModelConfig::GetModelName());
    report_clock();  // baseline operating point for the energy log

    uint64_t program_start_time = time_us_64();

    // Get model from configuration
    const tflite::Model *model = tflite::GetModel(ModelConfig::GetModelData());
    if (model->version() != TFLITE_SCHEMA_VERSION)
    {
        printf("The model version of %d does not match the version of the schema of %d\r\n",
                    model->version(), TFLITE_SCHEMA_VERSION);
        Error_Handler();
    }

    printf("Program start time: %llu microseconds\r\n", program_start_time);

    // Create op resolver with model-specific operations
    tflite::MicroMutableOpResolver<ModelConfig::kOpResolverSize> resolver;
    ModelConfig::InitializeOpResolver(resolver);

    // Create interpreter
    tflite::MicroInterpreter interpreter(
        model, resolver, tensor_arena, ModelConfig::kTensorArenaSize);

    // Allocate tensors
    TfLiteStatus allocate_status = interpreter.AllocateTensors();
    if (allocate_status != kTfLiteOk)
    {
        printf("AllocateTensors() failed\r\n");
        Error_Handler();
    }

    // Get input and output tensors
    TfLiteTensor *input = interpreter.input(0);
    TfLiteTensor *output = interpreter.output(0);

    // Print model info
    printf("Model loaded successfully: %s\r\n", ModelConfig::GetModelName());
    printf("Input size: %d bytes\r\n", ModelConfig::GetInputSize());
    printf("Expected categories: %d\r\n", ModelConfig::GetCategoryCount());

    if (input->bytes != ModelConfig::GetInputSize())
    {
        printf("Input tensor size mismatch! Expected: %d, got: %d\r\n",
                    ModelConfig::GetInputSize(), input->bytes);
    }

    // Display tensor information
    printf("Input tensor type: %d, scale: %f, zero point: %d\r\n", 
           input->type, input->params.scale, input->params.zero_point);
    printf("Output tensor type: %d, scale: %f, zero point: %d\r\n", 
           output->type, output->params.scale, output->params.zero_point);

    // Report arena memory usage
    printf("Tensor arena memory used: %lu bytes\r\n", (unsigned long)interpreter.arena_used_bytes());
    printf("Tensor arena memory available: %d bytes\r\n", ModelConfig::kTensorArenaSize);

    printf("Initialization complete\r\n");
    uint64_t current_time = time_us_64();
    printf("Setup() end time: %llu\r\n", current_time);
    uint64_t setup_time = current_time - program_start_time;
    printf("Setup takes: %llu microseconds\r\n", setup_time);

    // Continuous inference loop with sleep cycles
    int inference_count = 0;
    uint64_t total_memcpy_time = 0;
    uint64_t total_inference_time = 0;
    uint64_t total_postprocess_time = 0;

    while (1)
    {
        // Handle host serial commands: 'b' (BOOTSEL flash), 'f<khz>' (CPU freq), '?'.
        process_serial_commands();

        // Check if we need to sleep after every 10 inferences
        if (inference_count > 0 && inference_count % 10 == 0)
        {
            printf("\r\n--- Completed %d inferences, entering sleep cycle ---\r\n", inference_count);
            printf("Model: %s\r\n", ModelConfig::GetModelName());
            printf("Average memcpy time: %.2f microseconds\r\n", (float)total_memcpy_time / 10);
            printf("Average inference time: %.2f microseconds\r\n", (float)total_inference_time / 10);
            printf("Average post-processing time: %.2f microseconds\r\n", (float)total_postprocess_time / 10);
            uint64_t total_avg_time = (total_memcpy_time + total_inference_time + total_postprocess_time) / 10;
            printf("Average total loop time: %llu microseconds\r\n", total_avg_time);
            
            // Reset timing counters
            total_memcpy_time = 0;
            total_inference_time = 0;
            total_postprocess_time = 0;
            
            enter_sleep_cycle();
        }

        uint64_t loop_start_time = time_us_64();
        printf("\r\nInference %d starts at: %llu\r\n", inference_count + 1, loop_start_time);

        uint64_t memcpy_start_time = time_us_64();
        // Using all zeros for input data
        memset(input->data.int8, 0, input->bytes);
        uint64_t memcpy_end_time = time_us_64();
        uint64_t memcpy_time = memcpy_end_time - memcpy_start_time;
        total_memcpy_time += memcpy_time;
        printf("memcpy took: %llu microseconds\r\n", memcpy_time);

        uint64_t inference_start_time = time_us_64();
        gpio_put(MARKER_PIN, 1);                       // marker HIGH: inference begins
        TfLiteStatus invoke_status = interpreter.Invoke();
        gpio_put(MARKER_PIN, 0);                        // marker LOW: inference done
        if (invoke_status != kTfLiteOk)
        {
            printf("Invoke failed\r\n");
            continue;
        }
        uint64_t inference_end_time = time_us_64();
        uint64_t inference_time = inference_end_time - inference_start_time;
        total_inference_time += inference_time;
        printf("Inference took: %llu microseconds\r\n", inference_time);

        uint64_t postprocess_start_time = time_us_64();

        printf("Results: [");
        for (int j = 0; j < output->dims->data[1]; j++)
        {
            float converted = DequantizeInt8ToFloat(
                output->data.int8[j],
                output->params.scale,
                output->params.zero_point);

            printf("%.3f", converted);
            if (j < output->dims->data[1] - 1)
            {
                printf(", ");
            }
        }
        printf("]\r\n");

        int max_idx = 0;
        float max_val = DequantizeInt8ToFloat(
            output->data.int8[0],
            output->params.scale,
            output->params.zero_point);

        for (int j = 1; j < output->dims->data[1]; j++)
        {
            float val = DequantizeInt8ToFloat(
                output->data.int8[j],
                output->params.scale,
                output->params.zero_point);

            if (val > max_val)
            {
                max_val = val;
                max_idx = j;
            }
        }

        // Use the category labels from the model configuration
        const char **labels = ModelConfig::GetCategoryLabels();
        printf("Detected: %s (%.3f)\r\n", labels[max_idx], max_val);

        uint64_t postprocess_end_time = time_us_64();
        uint64_t postprocess_time = postprocess_end_time - postprocess_start_time;
        total_postprocess_time += postprocess_time;
        printf("Post-processing took: %llu microseconds\r\n", postprocess_time);

        inference_count++;
    }

    return 0;
}