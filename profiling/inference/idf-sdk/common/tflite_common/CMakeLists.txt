idf_component_register(SRCS "tflite_inference_runner.cc"
                       INCLUDE_DIRS "."
                       REQUIRES esp_timer freertos espressif__esp-tflite-micro main)

# Add the project's main directory to include paths to find model_config.h
target_include_directories(${COMPONENT_LIB} PRIVATE "${CMAKE_SOURCE_DIR}/main")
