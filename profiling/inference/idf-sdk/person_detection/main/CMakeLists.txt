
#
# Main component of TF Micro project 'micro_speech'.
#

idf_component_register(
    SRCS main.cc person_detect_model_data.cc person_detect_model_settings.cpp
    PRIV_REQUIRES esp_timer tflite_common
    INCLUDE_DIRS "."
    PRIV_INCLUDE_DIRS "../../common/tflite_common")

# Make model_config.h available to the common library
target_include_directories(${COMPONENT_LIB} INTERFACE ".")

target_compile_options(${COMPONENT_LIB} PRIVATE
    -Wno-maybe-uninitialized
    -Wno-missing-field-initializers
    -Wno-error=sign-compare
    -Wno-error=double-promotion
    -Wno-type-limits)
