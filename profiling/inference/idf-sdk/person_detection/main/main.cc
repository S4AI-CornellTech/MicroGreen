#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "../../common/tflite_common/tflite_inference_runner.h"

extern "C" void app_main(void)
{
    // Create the TensorFlow Lite task with a reasonable stack size
    // You may need to adjust the stack size based on your model's requirements
    xTaskCreate(tflite_model_task, "tflite_task", 8192, NULL, 5, NULL);
}
