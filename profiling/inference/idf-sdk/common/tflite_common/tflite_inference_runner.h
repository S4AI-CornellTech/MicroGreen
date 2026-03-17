#ifndef TFLITE_INFERENCE_RUNNER_H_
#define TFLITE_INFERENCE_RUNNER_H_

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_sleep.h"

// TensorFlow Lite Micro includes
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_log.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

// Utility functions
inline float DequantizeInt8ToFloat(int8_t value, float scale, int zero_point);
void FillInputPattern(int8_t *buffer, size_t size);
void Error_Handler(void);

// Main inference task function
void tflite_model_task(void *pvParameters);

#endif // TFLITE_INFERENCE_RUNNER_H_
