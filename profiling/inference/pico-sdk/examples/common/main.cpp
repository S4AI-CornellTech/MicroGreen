#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "pico/stdlib.h"
#include "pico/sleep.h"
#include "pico/bootrom.h"
#include "hardware/clocks.h"
#include "hardware/sync.h"   // __wfe()


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
#define MAX_SYS_CLOCK_KHZ 250000u // 48 MHz to 250 MHz

// Sleep-mode knob, selectable at runtime via the 's<n>' serial command.
// Every exposed mode keeps the system clocks and USB alive, so the host control
// channel and software reboot survive a sleep cycle. DORMANT is deliberately
// NOT exposed here: it stops the oscillators and drops USB, which would strand
// the board. set_sleep_mode() rejects any value outside this enum, so the
// optimizer cannot select dormant over the USB loop.
enum SleepMode
{
    SLEEP_MODE_BASELINE = 0, // sleep_ms(): park on WFE, all clocks running
    SLEEP_MODE_WFE      = 1, // run-idle: arm a timer alarm, park on __wfe()
    SLEEP_MODE_COUNT
};
static volatile uint8_t g_sleep_mode = SLEEP_MODE_BASELINE;

// Wake flag for the run-idle (__wfe) path; set from the alarm IRQ.
static volatile bool g_wfe_woke = false;
static int64_t wfe_wake_cb(alarm_id_t id, void *user_data)
{
    (void)id;
    (void)user_data;
    g_wfe_woke = true;
    return 0; // do not reschedule
}

// Run-idle: park the core on __wfe() until a one-shot timer alarm fires. All
// clocks, PLLs and USB stay up, so power is equivalent to sleep_ms(); the
// difference is that the core waits on an explicit wake event instead of
// polling the timer. Falls back to sleep_ms() if no alarm slot is available.
void idle_wfe_for_ms(uint32_t ms)
{
    g_wfe_woke = false;
    if (add_alarm_in_ms(ms, wfe_wake_cb, NULL, true) < 0)
    {
        sleep_ms(ms);
        return;
    }
    while (!g_wfe_woke)
    {
        __wfe();
    }
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

// Select the sleep mode used by enter_sleep_cycle(). Rejects anything outside
// the SleepMode enum (this is what keeps dormant off-limits to the optimizer).
bool set_sleep_mode(uint32_t mode)
{
    if (mode >= SLEEP_MODE_COUNT)
    {
        printf("ERR sleep mode %lu out of range [0,%d]\r\n",
               (unsigned long)mode, SLEEP_MODE_COUNT - 1);
        return false;
    }
    g_sleep_mode = (uint8_t)mode;
    return true;
}

// Non-blocking serial command processor on this board's USB serial port.
// Commands (one per line, terminated by CR/LF):
//   b           reboot into BOOTSEL/USB-flash mode
//   f<khz>      set the CPU frequency
//   s<n>        select sleep mode (0=baseline sleep_ms, 1=run-idle __wfe)
//   ?           report the current system clock
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
            buf[len] = '\0';
            switch (buf[0])
            {
                case 'f':
                case 'F':
                {
                    char *freq_str = buf + 1; // skip the 'f' character
                    uint32_t freq = (uint32_t)strtoul(freq_str, NULL, 10);
                    if (set_cpu_freq_khz(freq))
                    {
                        printf("ACK f ");
                        report_clock();
                    }
                    break;
                }
                case 's':
                case 'S':
                {
                    uint32_t mode = (uint32_t)strtoul(buf + 1, NULL, 10);
                    if (set_sleep_mode(mode))
                    {
                        printf("ACK s mode=%u\r\n", (unsigned)g_sleep_mode);
                    }
                    break;
                }
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
    printf("Preparing to sleep for 2 seconds (mode %u)...\r\n", (unsigned)g_sleep_mode);

    // Every mode below keeps the clocks and USB alive for BOTH the RP2040 and
    // RP2350, so the board stays enumerated and reachable for automated
    // flashing. These are NOT true low-power sleeps.
    stdio_flush();
    switch (g_sleep_mode)
    {
        case SLEEP_MODE_WFE:
            idle_wfe_for_ms(2000);
            break;
        case SLEEP_MODE_BASELINE:
        default:
            sleep_ms(2000);
            break;
    }
    printf("Woke up from sleep (mode %u)\r\n", (unsigned)g_sleep_mode);
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