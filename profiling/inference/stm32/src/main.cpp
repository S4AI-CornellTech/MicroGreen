#include "main.h"
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

// TensorFlow Lite Micro includes
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_log.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "model_config.h"

// Global UART handle
UART_HandleTypeDef huart2;
char uart_print_buffer[PRINT_BUFFER_SIZE];

// Timing structure to handle overflow properly
typedef struct
{
  uint32_t start_cycles;
  uint32_t start_ms; // HAL_GetTick() backup
} TimingContext;

inline float DequantizeInt8ToFloat(int8_t value, float scale, int zero_point)
{
  return static_cast<float>(value - zero_point) * scale;
}

void UART_printf(const char *format, ...)
{
  va_list args_list;

  va_start(args_list, format);
  vsnprintf(uart_print_buffer, PRINT_BUFFER_SIZE, format, args_list);
  va_end(args_list);

  HAL_UART_Transmit(&huart2, (uint8_t *)uart_print_buffer, strlen(uart_print_buffer), HAL_MAX_DELAY);
}

void FillInputPattern(int8_t *buffer, size_t size)
{
  const int8_t pattern[] = {42, -42, 85, -85}; // 01010101, 10101010 patterns
  for (size_t i = 0; i < size; i++)
  {
    buffer[i] = pattern[i % 4];
  }
}

void enter_sleep_cycle(void)
{
  UART_printf("Entering sleep for 2 seconds...\r\n");
  
  // Small delay to ensure UART transmission completes
  HAL_Delay(10);
  
  // Use __WFI() with SysTick for low power sleep
  // SysTick interrupts fire every 1ms and will wake the CPU
  uint32_t start_tick = HAL_GetTick();
  while ((HAL_GetTick() - start_tick) < 2000) {
    __WFI(); // Wait for interrupt (SysTick will wake us every 1ms)
  }
  
  UART_printf("Woke up from sleep\r\n");
}

// Remove unused functions
void enter_stop_mode(void) { /* Removed - not used */ }
void configure_rtc_wakeup(uint32_t milliseconds) { /* Removed - not used */ }
void disable_rtc_wakeup(void) { /* Removed - not used */ }
void enter_simple_sleep_cycle(void) { /* Removed - not used */ }

void LED_Init()
{
  LED_GPIO_CLK_ENABLE();

  GPIO_InitTypeDef GPIO_InitStruct;

  GPIO_InitStruct.Pin = LED_PIN;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_PULLUP;
  GPIO_InitStruct.Speed = GPIO_SPEED_HIGH;
  HAL_GPIO_Init(LED_GPIO_PORT, &GPIO_InitStruct);
}

void UART_Init(void)
{
  // Enable clocks
  UART_GPIO_CLK_ENABLE();
  UART_CLK_ENABLE();

  // Configure GPIO pins for UART
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  GPIO_InitStruct.Pin = UART_TX_PIN | UART_RX_PIN;
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStruct.Alternate = GPIO_AF7_USART2;
  HAL_GPIO_Init(UART_GPIO_PORT, &GPIO_InitStruct);

  // Configure UART
  huart2.Instance = UART_INSTANCE;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;

  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
}

void DWT_Init(void)
{
  // Enable DWT
  CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;

  // Reset cycle counter
  DWT->CYCCNT = 0;

  // Enable cycle counter
  DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}

// Start timing measurement
TimingContext start_timing(void)
{
  TimingContext ctx;
  ctx.start_cycles = DWT->CYCCNT;
  ctx.start_ms = HAL_GetTick();
  return ctx;
}

// Get elapsed microseconds since start_timing was called
// Handles 32-bit overflow correctly
uint32_t get_elapsed_micros(TimingContext ctx)
{
  uint32_t current_cycles = DWT->CYCCNT;
  uint32_t current_ms = HAL_GetTick();

  // Calculate elapsed milliseconds first
  uint32_t elapsed_ms = current_ms - ctx.start_ms;

  // For very long durations (>10 seconds), use ms timer
  // This prevents issues with cycle counter overflow
  if (elapsed_ms > 10000)
  {
    // Something is wrong if inference takes > 10 seconds
    // But return the value in microseconds
    return elapsed_ms * 1000;
  }

  // Calculate elapsed cycles with overflow handling
  uint32_t elapsed_cycles;
  if (current_cycles >= ctx.start_cycles)
  {
    elapsed_cycles = current_cycles - ctx.start_cycles;
  }
  else
  {
    // Overflow occurred (happens every ~42 seconds at 100MHz)
    elapsed_cycles = (0xFFFFFFFF - ctx.start_cycles) + current_cycles + 1;
  }

  // Convert cycles to microseconds
  // SystemCoreClock is typically 100000000 (100MHz) for STM32F411
  return elapsed_cycles / (SystemCoreClock / 1000000);
}

// Simple function for short duration measurements (< 40 seconds)
uint32_t get_elapsed_micros_simple(uint32_t start_cycles)
{
  uint32_t current_cycles = DWT->CYCCNT;
  uint32_t elapsed_cycles;

  if (current_cycles >= start_cycles)
  {
    elapsed_cycles = current_cycles - start_cycles;
  }
  else
  {
    // Overflow occurred
    elapsed_cycles = (0xFFFFFFFF - start_cycles) + current_cycles + 1;
  }

  return elapsed_cycles / (SystemCoreClock / 1000000);
}

// Get current time in microseconds (for compatibility with original code)
// Note: This will overflow after ~71 minutes
uint32_t micros(void)
{
  // For absolute timestamps, we'll use a simpler approach
  // This is mainly for logging "starts at" times
  return HAL_GetTick() * 1000; // Convert ms to us
}

void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  // Configure the main internal regulator output voltage
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

  // Initialize the HSE Oscillator and activate PLL with HSE as source
  // If you have an external crystal, use HSE. Otherwise use HSI
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = 8;             // HSI/8 = 2 MHz
  RCC_OscInitStruct.PLL.PLLN = 100;           // 2 MHz * 100 = 200 MHz
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2; // 200 MHz / 2 = 100 MHz
  RCC_OscInitStruct.PLL.PLLQ = 4;

  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  // Select PLL as system clock source and configure the HCLK, PCLK1 and PCLK2 clocks dividers
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1; // 100 MHz
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;  // 50 MHz
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;  // 100 MHz

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_3) != HAL_OK)
  {
    Error_Handler();
  }

  // Update SystemCoreClock variable
  SystemCoreClockUpdate();
}

int main(void)
{
  HAL_Init();
  SystemClock_Config(); // Configure clock to 100 MHz
  UART_Init();
  DWT_Init();

  UART_printf("\r\n=== Starting %s Model Test with Sleep Cycles ===\r\n", ModelConfig::GetModelName());

  // Debug: Print system clock frequency
  UART_printf("System Clock: %lu Hz\r\n", SystemCoreClock);
  UART_printf("HAL_RCC_GetSysClockFreq: %lu Hz\r\n", HAL_RCC_GetSysClockFreq());
  UART_printf("HAL_RCC_GetHCLKFreq: %lu Hz\r\n", HAL_RCC_GetHCLKFreq());
  uint32_t start = DWT->CYCCNT;
  HAL_Delay(1);
  uint32_t end = DWT->CYCCNT;
  UART_printf("DWT test: %lu cycles for 1ms delay\n", end - start);

  TimingContext program_start = start_timing();
  uint32_t program_start_time = micros();

  // Get model from configuration
  const tflite::Model *model = tflite::GetModel(ModelConfig::GetModelData());
  if (model->version() != TFLITE_SCHEMA_VERSION)
  {
    UART_printf("The model version of %d does not match the version of the schema of version %d\r\n",
                model->version(), TFLITE_SCHEMA_VERSION);
    Error_Handler();
  }

  UART_printf("Program start time: %lu microseconds\r\n", program_start_time);

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
    UART_printf("AllocateTensors() failed\r\n");
    return 1;
  }

  // Get input and output tensors
  TfLiteTensor *input = interpreter.input(0);
  TfLiteTensor *output = interpreter.output(0);

  // Print model info
  UART_printf("Model loaded successfully: %s\r\n", ModelConfig::GetModelName());
  UART_printf("Input size: %d bytes\r\n", ModelConfig::GetInputSize());
  UART_printf("Expected categories: %d\r\n", ModelConfig::GetCategoryCount());

  if (input->bytes != ModelConfig::GetInputSize())
  {
    UART_printf("Input tensor size mismatch! Expected: %d, got: %d\r\n",
                ModelConfig::GetInputSize(), input->bytes);
  }

  // Display tensor information
  UART_printf("Input tensor type: %d, scale: %f, zero point: %d\r\n", 
              input->type, input->params.scale, input->params.zero_point);
  UART_printf("Output tensor type: %d, scale: %f, zero point: %d\r\n", 
              output->type, output->params.scale, output->params.zero_point);

  // Report arena memory usage
  UART_printf("Tensor arena memory used: %lu bytes\r\n", (unsigned long)interpreter.arena_used_bytes());
  UART_printf("Tensor arena memory available: %d bytes\r\n", ModelConfig::kTensorArenaSize);

  UART_printf("Initialization complete\r\n");

  uint32_t current_time = micros();
  UART_printf("Setup() end time: %lu\r\n", current_time);

  uint32_t setup_time = get_elapsed_micros(program_start);
  UART_printf("Setup takes: %lu microseconds\r\n", setup_time);

  // Continuous inference loop with sleep cycles
  int inference_count = 0;
  uint32_t total_memcpy_time = 0;
  uint32_t total_inference_time = 0;
  uint32_t total_postprocess_time = 0;

  while (1)
  {
    // Check if we need to sleep after every 10 inferences
    if (inference_count > 0 && inference_count % 10 == 0)
    {
      UART_printf("\r\n--- Completed %d inferences, entering sleep cycle ---\r\n", inference_count);
      UART_printf("Average memcpy time: %.2f microseconds\r\n", (float)total_memcpy_time / 10);
      UART_printf("Average inference time: %.2f microseconds\r\n", (float)total_inference_time / 10);
      UART_printf("Average post-processing time: %.2f microseconds\r\n", (float)total_postprocess_time / 10);
      uint32_t total_avg_time = (total_memcpy_time + total_inference_time + total_postprocess_time) / 10;
      UART_printf("Average total loop time: %lu microseconds\r\n", total_avg_time);
      
      // Reset timing counters
      total_memcpy_time = 0;
      total_inference_time = 0;
      total_postprocess_time = 0;
      
      enter_sleep_cycle();
    }

    uint32_t loop_start_time = micros();
    UART_printf("\r\nInference %d starts at: %lu\r\n", inference_count + 1, loop_start_time);

    // Time memcpy operation
    uint32_t memcpy_start = DWT->CYCCNT;
    memset(input->data.int8, 0, input->bytes);
    uint32_t memcpy_time = get_elapsed_micros_simple(memcpy_start);
    total_memcpy_time += memcpy_time;
    UART_printf("memcpy took: %lu microseconds\r\n", memcpy_time);

    // Time inference
    TimingContext inference_ctx = start_timing();
    TfLiteStatus invoke_status = interpreter.Invoke();
    if (invoke_status != kTfLiteOk)
    {
      UART_printf("Invoke failed\r\n");
      HAL_Delay(500);
      inference_count++;
      continue;
    }
    uint32_t inference_time = get_elapsed_micros(inference_ctx);
    total_inference_time += inference_time;
    UART_printf("Inference took: %lu microseconds\r\n", inference_time);

    // Time post-processing
    uint32_t postprocess_start = DWT->CYCCNT;

    UART_printf("Results: [");
    for (int j = 0; j < output->dims->data[1]; j++)
    {
      float converted = DequantizeInt8ToFloat(
          output->data.int8[j],
          output->params.scale,
          output->params.zero_point);

      UART_printf("%.3f", converted);
      if (j < output->dims->data[1] - 1)
      {
        UART_printf(", ");
      }
    }
    UART_printf("]\r\n");

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
    UART_printf("Detected: %s (%.3f)\r\n", labels[max_idx], max_val);

    uint32_t postprocess_time = get_elapsed_micros_simple(postprocess_start);
    total_postprocess_time += postprocess_time;
    UART_printf("Post-processing took: %lu microseconds\r\n", postprocess_time);

    inference_count++;

    // Add a small delay between inferences to allow for any cleanup
    HAL_Delay(10);
  }
}

// Remove unused RTC code
// RTC Handle removed - not needed for simple sleep

// Interrupt handlers
extern "C" void SysTick_Handler(void)
{
  HAL_IncTick();
}

void NMI_Handler(void)
{
}

void HardFault_Handler(void)
{
  UART_printf("ERROR: HardFault occurred!\r\n");
  while (1)
  {
  }
}

void MemManage_Handler(void)
{
  UART_printf("ERROR: MemManage fault occurred!\r\n");
  while (1)
  {
  }
}

void BusFault_Handler(void)
{
  UART_printf("ERROR: BusFault occurred!\r\n");
  while (1)
  {
  }
}

void UsageFault_Handler(void)
{
  UART_printf("ERROR: UsageFault occurred!\r\n");
  while (1)
  {
  }
}

void SVC_Handler(void)
{
}

void DebugMon_Handler(void)
{
}

void PendSV_Handler(void)
{
}

void Error_Handler(void)
{
  UART_printf("ERROR: Error_Handler called!\r\n");
  while (1)
  {
  }
}