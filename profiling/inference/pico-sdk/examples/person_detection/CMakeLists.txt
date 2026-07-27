cmake_minimum_required(VERSION 3.12)

project(micro_speech C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

add_executable(person_detection "")

target_include_directories(person_detection
  PRIVATE
  ${CMAKE_CURRENT_LIST_DIR}/.
)

set_target_properties(
  person_detection
  PROPERTIES
  COMPILE_FLAGS -fno-rtti
  COMPILE_FLAGS -fno-exceptions
  COMPILE_FLAGS -fno-threadsafe-statics
  COMPILE_FLAGS -nostdlib
)

target_sources(person_detection
  PRIVATE
  ${CMAKE_CURRENT_LIST_DIR}/../common/main.cpp
  ${CMAKE_CURRENT_LIST_DIR}/person_detect_model_data.cc
  ${CMAKE_CURRENT_LIST_DIR}/person_detect_model_settings.cpp
)

target_link_libraries(
  person_detection
  pico-tflmicro
  pico_stdlib
)

pico_enable_stdio_usb(person_detection 1)
pico_enable_stdio_uart(person_detection 0)

pico_add_extra_outputs(person_detection)
