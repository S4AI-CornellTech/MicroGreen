#ifndef MAIN_H
#define MAIN_H
#include "stm32f4xx_hal.h"

// LED Configuration for STM32F411VE Discovery Board
// Using LD4 (Green User LED) connected to PD12
#define LED_PIN                                GPIO_PIN_12
#define LED_GPIO_PORT                          GPIOD
#define LED_GPIO_CLK_ENABLE()                  __HAL_RCC_GPIOD_CLK_ENABLE()

// UART Configuration for STM32F411VE Discovery Board
// Using USART2 connected to ST-LINK Virtual COM Port
// PA2 = USART2_TX, PA3 = USART2_RX
#define UART_TX_PIN                            GPIO_PIN_2
#define UART_RX_PIN                            GPIO_PIN_3
#define UART_GPIO_PORT                         GPIOA
#define UART_GPIO_CLK_ENABLE()                 __HAL_RCC_GPIOA_CLK_ENABLE()
#define UART_CLK_ENABLE()                      __HAL_RCC_USART2_CLK_ENABLE()
#define UART_INSTANCE                          USART2
#define PRINT_BUFFER_SIZE 128 // Buffer for formatted output

// Global UART handle
extern UART_HandleTypeDef huart2;

// Function prototypes
void Error_Handler(void);
void UART_Init(void);
void UART_printf(const char* format, ...);
void enter_sleep_cycle(void);
#endif // MAIN_H
