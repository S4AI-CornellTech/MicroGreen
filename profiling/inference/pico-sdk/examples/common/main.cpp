#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "pico/stdlib.h"
#include "pico/sleep.h"
#include "pico/bootrom.h"
#include "hardware/clocks.h"
#include "hardware/sync.h"           // __wfe() / __wfi()
#include "hardware/structs/scb.h"    // scb_hw->scr SLEEPDEEP bit (s2/s3 deep sleep)
#include "hardware/timer.h"          // dedicated hardware alarm for the deep-sleep wake
#include "hardware/watchdog.h"       // backstop reset if a deep sleep fails to wake


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
//
//   0/1  keep the CPU running, so USB stays CONTINUOUSLY enumerated.
//   2/3  real processor deep sleep: the CPU halts and stops servicing USB, so
//        the serial port DROPS during the sleep window and RE-ENUMERATES on the
//        timer wake. They are still "recoverable" (self-wake via the always-on
//        timer + clock restore), so software reboot works again in the command
//        window after each wake -- unlike DORMANT, which can only wake from a
//        GPIO edge and so is deliberately NOT exposed. set_sleep_mode() rejects
//        anything outside this enum, so the optimizer can never select dormant.
enum SleepMode
{
    SLEEP_MODE_BASELINE = 0, // sleep_ms(): park on WFE, all clocks running
    SLEEP_MODE_WFE      = 1, // run-idle: arm a timer alarm, park on __wfe()
    SLEEP_MODE_SLEEP_EN = 2, // deep sleep, PLLs left on (clk_sys/freq preserved)
    SLEEP_MODE_XOSC     = 3, // deep sleep, run from XOSC with PLLs off (deepest)
    SLEEP_MODE_COUNT
};
static volatile uint8_t g_sleep_mode = SLEEP_MODE_BASELINE;

// Last CPU frequency requested via 'f<khz>' (0 = never set, use firmware
// default). sleep_power_up() runs clocks_init() which resets clk_sys to the
// default, so after an s3 deep sleep we re-apply this to keep a frequency sweep
// honest across sleep cycles.
static volatile uint32_t g_cur_freq_khz = 0;

// Cortex SLEEPDEEP bit differs by core (M0+ on RP2040, M33 on RP2350-ARM).
#if PICO_RP2040
#define MG_SCR_SLEEPDEEP M0PLUS_SCR_SLEEPDEEP_BITS
#elif !defined(__riscv)
#define MG_SCR_SLEEPDEEP M33_SCR_SLEEPDEEP_BITS
#endif

// Wake flag for every timer-driven wait (run-idle and deep sleep); set from the
// alarm IRQ, which is what brings the core back out of __wfe()/__wfi().
static volatile bool g_timer_woke = false;
static int64_t timer_wake_cb(alarm_id_t id, void *user_data)
{
    (void)id;
    (void)user_data;
    g_timer_woke = true;
    return 0; // do not reschedule
}

// Dedicated hardware alarm for the deep-sleep wake, claimed once and reused for
// every sleep (so it never leaks, unlike a fresh add_alarm per call). This is
// the same low-level path the SDK's sleep_goto_sleep_for() uses to bring the
// core back out of deep sleep; its callback sets the same g_timer_woke flag.
static int g_deep_alarm = -1;
static void deep_alarm_cb(uint alarm_num)
{
    (void)alarm_num;
    g_timer_woke = true;
}

// Run-idle: park the core on __wfe() until a one-shot timer alarm fires. All
// clocks, PLLs and USB stay up, so power is equivalent to sleep_ms(); the
// difference is that the core waits on an explicit wake event instead of
// polling the timer. Falls back to sleep_ms() if no alarm slot is available.
void idle_wfe_for_ms(uint32_t ms)
{
    g_timer_woke = false;
    if (add_alarm_in_ms(ms, timer_wake_cb, NULL, true) < 0)
    {
        sleep_ms(ms);
        return;
    }
    while (!g_timer_woke)
    {
        __wfe();
    }
}

// Real processor deep sleep for `ms`, self-waking from the always-on system
// timer. Mirrors the SDK's sleep_goto_sleep_for() but uses the default alarm
// pool (add_alarm_in_ms) so it does NOT leak a hardware alarm per call -- the
// SDK helper claims one each time and never frees it, which would panic after a
// few sleep cycles. With from_xosc=false (s2) the PLLs stay up and clk_sys/freq
// is preserved; with from_xosc=true (s3) we drop to XOSC with the PLLs off for
// the lowest power, then sleep_power_up() restores clocks and we re-apply the
// requested frequency. USB drops during the sleep and re-enumerates after.
void deep_sleep_for_ms(uint32_t ms, bool from_xosc)
{
#if defined(MG_SCR_SLEEPDEEP)
    // Claim the dedicated wake alarm once. If none is free, never deep-sleep
    // (we'd have no way back) -- fall back to a plain delay.
    if (g_deep_alarm < 0)
    {
        g_deep_alarm = hardware_alarm_claim_unused(false);
        if (g_deep_alarm >= 0)
        {
            hardware_alarm_set_callback((uint)g_deep_alarm, deep_alarm_cb);
        }
    }
    if (g_deep_alarm < 0)
    {
        sleep_ms(ms);
        return;
    }

    if (from_xosc)
    {
        sleep_run_from_xosc(); // clk_sys -> XOSC (12 MHz), PLLs deinit'd
    }

    // Arm the timer wake. set_target() returns true if the deadline already
    // passed, in which case don't sleep -- just restore and return.
    g_timer_woke = false;
    if (hardware_alarm_set_target((uint)g_deep_alarm, make_timeout_time_ms(ms)))
    {
        if (from_xosc)
        {
            sleep_power_up();
            if (g_cur_freq_khz)
            {
                set_sys_clock_khz(g_cur_freq_khz, false);
            }
        }
        return;
    }

    // Backstop: if this deep sleep ever fails to wake, the watchdog resets the
    // board (which reboots into s0 with USB alive) instead of wedging forever.
    // The margin is comfortably longer than the sleep; we disable it the instant
    // we wake cleanly, so it never fires during normal operation.
    watchdog_enable(ms + 1000, true);

    // Gate every clock except the system timer (our wake source); save the
    // current masks so s2 (which keeps the PLLs) can restore them verbatim.
    uint32_t save_en0 = clocks_hw->sleep_en0;
    uint32_t save_en1 = clocks_hw->sleep_en1;
    clocks_hw->sleep_en0 = 0x0;
#if PICO_RP2040
    clocks_hw->sleep_en1 = CLOCKS_SLEEP_EN1_CLK_SYS_TIMER_BITS;
#else
    clocks_hw->sleep_en1 = CLOCKS_SLEEP_EN1_CLK_REF_TICKS_BITS |
                           CLOCKS_SLEEP_EN1_CLK_SYS_TIMER0_BITS;
#endif

    scb_hw->scr |= MG_SCR_SLEEPDEEP;        // deepen the next __wfi()
    while (!g_timer_woke)
    {
        __wfi();                            // halt until the timer IRQ fires
    }
    scb_hw->scr &= ~MG_SCR_SLEEPDEEP;       // back to normal sleep depth

    watchdog_disable();                     // woke cleanly -> cancel the backstop

    if (from_xosc)
    {
        sleep_power_up();                   // restore PLLs/clocks (also resets sleep_en)
        if (g_cur_freq_khz)
        {
            set_sys_clock_khz(g_cur_freq_khz, false); // re-apply the f-knob freq
        }
    }
    else
    {
        clocks_hw->sleep_en0 = save_en0;    // s2: PLLs untouched, just restore masks
        clocks_hw->sleep_en1 = save_en1;
    }
#else
    // RISC-V (RP2350) builds: SLEEPDEEP bit handling not wired up here; fall back
    // to a plain delay so these modes still behave safely.
    (void)from_xosc;
    sleep_ms(ms);
#endif
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
    g_cur_freq_khz = khz; // remembered so s3 can re-apply it after sleep_power_up()
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
//   s<n>        select sleep mode (0=baseline sleep_ms, 1=run-idle __wfe,
//               2=deep sleep PLLs-on, 3=deep sleep XOSC). 2/3 drop USB during
//               the sleep and re-enumerate after.
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

    // Modes 0/1 keep the clocks and USB alive; modes 2/3 are real deep sleep
    // that drops USB during the window and re-enumerates on the timer wake.
    // Either way the board self-wakes and returns to the command loop, so
    // software reboot ('b') works again in the next command window.
    stdio_flush();
    switch (g_sleep_mode)
    {
        case SLEEP_MODE_WFE:
            idle_wfe_for_ms(2000);
            break;
        case SLEEP_MODE_SLEEP_EN:
            deep_sleep_for_ms(2000, false); // PLLs stay on, freq preserved
            break;
        case SLEEP_MODE_XOSC:
            deep_sleep_for_ms(2000, true);  // drop to XOSC, PLLs off (deepest)
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