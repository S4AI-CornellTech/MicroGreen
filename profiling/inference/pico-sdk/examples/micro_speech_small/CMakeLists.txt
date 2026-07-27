cmake_minimum_required(VERSION 3.12)

project(micro_speech C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

add_executable(micro_speech_small "")

target_include_directories(micro_speech_small
  PRIVATE
  ${CMAKE_CURRENT_LIST_DIR}/.
)

set_target_properties(
  micro_speech_small
  PROPERTIES
  COMPILE_FLAGS -fno-rtti
  COMPILE_FLAGS -fno-exceptions
  COMPILE_FLAGS -fno-threadsafe-statics
  COMPILE_FLAGS -nostdlib
)

target_sources(micro_speech_small
  PRIVATE
  ${CMAKE_CURRENT_LIST_DIR}/../common/main.cpp
  ${CMAKE_CURRENT_LIST_DIR}/kws_model_data.cc
  ${CMAKE_CURRENT_LIST_DIR}/kws_model_settings.cc
)

target_link_libraries(
  micro_speech_small
  pico-tflmicro
  pico_stdlib
)

pico_enable_stdio_usb(micro_speech_small 1)
pico_enable_stdio_uart(micro_speech_small 0)

pico_add_extra_outputs(micro_speech_small)
