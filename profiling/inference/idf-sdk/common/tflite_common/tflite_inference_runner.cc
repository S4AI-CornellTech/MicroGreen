#include "tflite_inference_runner.h"
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
    printf("ERROR: Fatal error occurred!\n");
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void enter_sleep_cycle(void)
{
    printf("Entering light sleep for 2 seconds...\n");
    fflush(stdout); // Ensure output is sent before sleep
    
    // Configure light sleep for 2 seconds
    esp_sleep_enable_timer_wakeup(2000000); // 2 seconds in microseconds
    esp_light_sleep_start();
    
    printf("Woke up from light sleep\n");
}

// Global variables for TensorFlow Lite
namespace {
    const tflite::Model* model = nullptr;
    tflite::MicroInterpreter* interpreter = nullptr;
    TfLiteTensor* input = nullptr;
    TfLiteTensor* output = nullptr;
}

void tflite_model_task(void *pvParameters)
{
    printf("\n=== Starting %s Model Test with Sleep Cycles ===\n\n", ModelConfig::GetModelName());

    int64_t program_start_time = esp_timer_get_time();

    // Get model from configuration
    model = tflite::GetModel(ModelConfig::GetModelData());
    if (model->version() != TFLITE_SCHEMA_VERSION)
    {
        printf("ERROR: The model version of %ld does not match the version of the schema of version %d\n",
               model->version(), TFLITE_SCHEMA_VERSION);
        Error_Handler();
    }

    printf("Program start time: %lld microseconds\n", program_start_time);

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
        printf("ERROR: AllocateTensors() failed\n");
        Error_Handler();
    }

    // Get input and output tensors
    input = interpreter->input(0);
    output = interpreter->output(0);

    // Print model info
    printf("Model loaded successfully: %s\n", ModelConfig::GetModelName());
    printf("Input size: %d bytes\n", ModelConfig::GetInputSize());
    printf("Expected categories: %d\n", ModelConfig::GetCategoryCount());

    if (input->bytes != ModelConfig::GetInputSize())
    {
        printf("WARNING: Input tensor size mismatch! Expected: %d, got: %zu\n",
               ModelConfig::GetInputSize(), input->bytes);
    }

    // Display tensor information
    printf("Input tensor type: %d, scale: %f, zero point: %ld\n", 
           input->type, input->params.scale, (long)input->params.zero_point);
    printf("Output tensor type: %d, scale: %f, zero point: %ld\n", 
           output->type, output->params.scale, (long)output->params.zero_point);

    // Report arena memory usage
    printf("Tensor arena memory used: %zu bytes\n", interpreter->arena_used_bytes());
    printf("Tensor arena memory available: %d bytes\n", ModelConfig::kTensorArenaSize);

    printf("Initialization complete\n");
    int64_t current_time = esp_timer_get_time();
    printf("Setup end time: %lld\n", current_time);
    int64_t setup_time = current_time - program_start_time;
    printf("Setup takes: %lld microseconds\n", setup_time);

    // Continuous inference loop with sleep cycles
    int inference_count = 0;
    int64_t total_memcpy_time = 0;
    int64_t total_inference_time = 0;
    int64_t total_postprocess_time = 0;

    while (1) {
        // Check if we need to sleep after every 10 inferences
        if (inference_count > 0 && inference_count % 10 == 0)
        {
            printf("\n--- Completed %d inferences, entering sleep cycle ---\n", inference_count);
            printf("Average memcpy time: %.2f microseconds\n", (float)total_memcpy_time / 10);
            printf("Average inference time: %.2f microseconds\n", (float)total_inference_time / 10);
            printf("Average post-processing time: %.2f microseconds\n", (float)total_postprocess_time / 10);
            int64_t total_avg_time = (total_memcpy_time + total_inference_time + total_postprocess_time) / 10;
            printf("Average total loop time: %lld microseconds\n", total_avg_time);
            
            // Reset timing counters
            total_memcpy_time = 0;
            total_inference_time = 0;
            total_postprocess_time = 0;
            
            enter_sleep_cycle();
        }

        int64_t loop_start_time = esp_timer_get_time();
        printf("\nInference %d starts at: %lld\n", inference_count + 1, loop_start_time);

        int64_t memcpy_start_time = esp_timer_get_time();
        // Using all zeros for input data
        memset(input->data.int8, 0, input->bytes);
        int64_t memcpy_end_time = esp_timer_get_time();
        int64_t memcpy_time = memcpy_end_time - memcpy_start_time;
        total_memcpy_time += memcpy_time;
        printf("memcpy took: %lld microseconds\n", memcpy_time);

        int64_t inference_start_time = esp_timer_get_time();
        TfLiteStatus invoke_status = interpreter->Invoke();
        if (invoke_status != kTfLiteOk)
        {
            printf("ERROR: Invoke failed\n");
            vTaskDelay(pdMS_TO_TICKS(1000));
            inference_count++;
            continue;
        }
        int64_t inference_end_time = esp_timer_get_time();
        int64_t inference_time = inference_end_time - inference_start_time;
        total_inference_time += inference_time;
        printf("Inference took: %lld microseconds\n", inference_time);

        int64_t postprocess_start_time = esp_timer_get_time();

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
        printf("]\n");

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
        printf("Detected: %s (%.3f)\n", labels[max_idx], max_val);

        int64_t postprocess_end_time = esp_timer_get_time();
        int64_t postprocess_time = postprocess_end_time - postprocess_start_time;
        total_postprocess_time += postprocess_time;
        printf("Post-processing took: %lld microseconds\n", postprocess_time);

        inference_count++;
        
        // Small delay between inferences
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}