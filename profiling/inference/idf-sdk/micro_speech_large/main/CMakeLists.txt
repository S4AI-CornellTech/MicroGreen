
#
# Main component of TF Micro project 'micro_speech'.
#

idf_component_register(
    SRCS main.cc kws_model_data.cc kws_model_settings.cc
    PRIV_REQUIRES esp_timer tflite_common
    INCLUDE_DIRS ""
    PRIV_INCLUDE_DIRS "../../common/tflite_common")

# Expose model_config.h as an interface include directory
target_include_directories(${COMPONENT_LIB} INTERFACE ".")

target_compile_options(${COMPONENT_LIB} PRIVATE
    -Wno-maybe-uninitialized
    -Wno-missing-field-initializers
    -Wno-error=sign-compare
    -Wno-error=double-promotion
    -Wno-type-limits)
