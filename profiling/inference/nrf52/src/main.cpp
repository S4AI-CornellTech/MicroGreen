#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <Arduino.h>
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif
#ifdef round
#undef round
#endif

// TensorFlow Lite Micro includes
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_log.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "model_config.h"

inline float DequantizeInt8ToFloat(int8_t value, float scale, int zero_point)
{
    return static_cast<float>(value - zero_point) * scale;
}

void FillInputPattern(int8_t *buffer, size_t size)
{
    const int8_t pattern[] = {42, -42, 85, -85}; // 01010101, 10101010 patterns
    for (size_t i = 0; i < size; i++)
    {
        buffer[i] = pattern[i % 4];
    }
}

void Error_Handler(void)
{
    while (1)
    {
        delay(100);
    }
}

// Alternative implementation using simple delay (if ArduinoLowPower not available)
void enter_simple_sleep_cycle(void)
{
    Serial.println("Preparing to sleep for 3 seconds...");
    Serial.flush();

    delay(3000);
}

// Global variables for TensorFlow Lite
namespace
{
    const tflite::Model *model = nullptr;
    tflite::MicroInterpreter *interpreter = nullptr;
    TfLiteTensor *input = nullptr;
    TfLiteTensor *output = nullptr;
    uint8_t *tensor_arena = nullptr;
}

void setup(void)
{
    Serial.begin(115200);

    // Wait for Serial connection (optional, useful for debugging)
    while (!Serial && millis() < 5000)
    {
        delay(10);
    }

    // Brief delay to allow serial to stabilize
    delay(1000);

    Serial.print("\r\n=== Starting ");
    Serial.print(ModelConfig::GetModelName());
    Serial.println(" Model Test ===\r\n");

    if (tensor_arena == nullptr)
    {
        tensor_arena = (uint8_t *)malloc(ModelConfig::kTensorArenaSize);
        if (tensor_arena == nullptr)
        {
            Serial.println("Failed to allocate tensor arena!");
            Error_Handler();
        }
        Serial.print("Allocated ");
        Serial.print(ModelConfig::kTensorArenaSize);
        Serial.println(" bytes for tensor arena on heap");
    }

    unsigned long program_start_time = micros();

    // Get model from configuration
    model = tflite::GetModel(ModelConfig::GetModelData());
    if (model->version() != TFLITE_SCHEMA_VERSION)
    {
        Serial.print("The model version of ");
        Serial.print(model->version());
        Serial.print(" does not match the version of the schema of version ");
        Serial.println(TFLITE_SCHEMA_VERSION);
        Error_Handler();
    }

    Serial.print("Program start time: ");
    Serial.print(program_start_time);
    Serial.println(" microseconds");

    // Create op resolver with model-specific operations
    static tflite::MicroMutableOpResolver<ModelConfig::kOpResolverSize> resolver;
    ModelConfig::InitializeOpResolver(resolver);

    // Create interpreter
    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, ModelConfig::kTensorArenaSize);
    interpreter = &static_interpreter;

    // Allocate tensors
    TfLiteStatus allocate_status = interpreter->AllocateTensors();
    if (allocate_status != kTfLiteOk)
    {
        Serial.println("AllocateTensors() failed");
        Error_Handler();
    }

    // Get input and output tensors
    input = interpreter->input(0);
    output = interpreter->output(0);

    // Print model info
    Serial.print("Model loaded successfully: ");
    Serial.println(ModelConfig::GetModelName());
    Serial.print("Input size: ");
    Serial.print(ModelConfig::GetInputSize());
    Serial.println(" bytes");
    Serial.print("Expected categories: ");
    Serial.println(ModelConfig::GetCategoryCount());

    if (input->bytes != ModelConfig::GetInputSize())
    {
        Serial.print("Input tensor size mismatch! Expected: ");
        Serial.print(ModelConfig::GetInputSize());
        Serial.print(", got: ");
        Serial.println(input->bytes);
    }

    // Display tensor information
    Serial.print("Input tensor type: ");
    Serial.println(input->type);
    Serial.print("Input tensor scale: ");
    Serial.println(input->params.scale, 6);
    Serial.print("Input tensor zero point: ");
    Serial.println(input->params.zero_point);

    Serial.print("Output tensor type: ");
    Serial.println(output->type);
    Serial.print("Output tensor scale: ");
    Serial.println(output->params.scale, 6);
    Serial.print("Output tensor zero point: ");
    Serial.println(output->params.zero_point);

    // Report arena memory usage
    Serial.print("Tensor arena memory used: ");
    Serial.print(interpreter->arena_used_bytes());
    Serial.println(" bytes");
    Serial.print("Tensor arena memory available: ");
    Serial.print(ModelConfig::kTensorArenaSize);
    Serial.println(" bytes");

    Serial.println("Initialization complete");
    unsigned long current_time = micros();
    Serial.print("Setup() end time: ");
    Serial.println(current_time);
    unsigned long setup_time = current_time - program_start_time;
    Serial.print("Setup takes: ");
    Serial.print(setup_time);
    Serial.println(" microseconds");
}

void loop(void)
{
    static int inference_count = 0;
    static unsigned long total_memcpy_time = 0;
    static unsigned long total_inference_time = 0;
    static unsigned long total_postprocess_time = 0;

    // Check if we need to sleep after every 10 inferences
    if (inference_count > 0 && inference_count % 10 == 0)
    {
        Serial.print("\r\n--- Completed ");
        Serial.print(inference_count);
        Serial.print(' ');
        Serial.print(ModelConfig::GetModelName());
        Serial.println(" inferences");
        Serial.print("Average memcpy time: ");
        Serial.print((float)total_memcpy_time / 10);
        Serial.println(" microseconds");
        Serial.print("Average inference time: ");
        Serial.print((float)total_inference_time / 10);
        Serial.println(" microseconds");
        Serial.print("Average post-processing time: ");
        Serial.print((float)total_postprocess_time / 10);
        Serial.println(" microseconds");
        unsigned long total_avg_time = (total_memcpy_time + total_inference_time + total_postprocess_time) / 10;
        Serial.print("Average total loop time: ");
        Serial.print(total_avg_time);
        Serial.println(" microseconds");

        // Reset timing counters
        total_memcpy_time = 0;
        total_inference_time = 0;
        total_postprocess_time = 0;

        enter_simple_sleep_cycle();
    }

    unsigned long loop_start_time = micros();
    Serial.print("\r\nInference ");
    Serial.print(inference_count + 1);
    Serial.print(" starts at: ");
    Serial.println(loop_start_time);

    unsigned long memcpy_start_time = micros();
    // using all zeros for input data
    memset(input->data.int8, 0, input->bytes);
    unsigned long memcpy_end_time = micros();
    unsigned long memcpy_time = memcpy_end_time - memcpy_start_time;
    total_memcpy_time += memcpy_time;
    Serial.print("memcpy took: ");
    Serial.print(memcpy_time);
    Serial.println(" microseconds");

    unsigned long inference_start_time = micros();
    TfLiteStatus invoke_status = interpreter->Invoke();
    if (invoke_status != kTfLiteOk)
    {
        Serial.println("Invoke failed");
        delay(1000);
        inference_count++;
        return;
    }
    unsigned long inference_end_time = micros();
    unsigned long inference_time = inference_end_time - inference_start_time;
    total_inference_time += inference_time;
    Serial.print("Inference took: ");
    Serial.print(inference_time);
    Serial.println(" microseconds");

    unsigned long postprocess_start_time = micros();

    Serial.print("Results: [");
    for (int j = 0; j < output->dims->data[1]; j++)
    {
        float converted = DequantizeInt8ToFloat(
            output->data.int8[j],
            output->params.scale,
            output->params.zero_point);

        Serial.print(converted, 3);
        if (j < output->dims->data[1] - 1)
        {
            Serial.print(", ");
        }
    }
    Serial.println("]");

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
    Serial.print("Detected: ");
    Serial.print(labels[max_idx]);
    Serial.print(" (");
    Serial.print(max_val, 3);
    Serial.println(")");

    unsigned long postprocess_end_time = micros();
    unsigned long postprocess_time = postprocess_end_time - postprocess_start_time;
    total_postprocess_time += postprocess_time;
    Serial.print("Post-processing took: ");
    Serial.print(postprocess_time);
    Serial.println(" microseconds");

    inference_count++;

    // Small delay between inferences
    delay(100);
}