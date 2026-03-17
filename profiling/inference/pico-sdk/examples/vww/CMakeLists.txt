cmake_minimum_required(VERSION 3.12)

project(micro_speech C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

add_executable(vww "")

target_include_directories(vww
  PRIVATE
  ${CMAKE_CURRENT_LIST_DIR}/.
)

set_target_properties(
  vww
  PROPERTIES
  COMPILE_FLAGS -fno-rtti
  COMPILE_FLAGS -fno-exceptions
  COMPILE_FLAGS -fno-threadsafe-statics
  COMPILE_FLAGS -nostdlib
)

target_sources(vww
  PRIVATE
  ${CMAKE_CURRENT_LIST_DIR}/../common/main.cpp
  ${CMAKE_CURRENT_LIST_DIR}/vww_model_data.cc
  ${CMAKE_CURRENT_LIST_DIR}/vww_model_settings.cc
)

target_link_libraries(
  vww
  pico-tflmicro
  pico_stdlib
)

pico_enable_stdio_usb(vww 1)
pico_enable_stdio_uart(vww 0)

pico_add_extra_outputs(vww)
