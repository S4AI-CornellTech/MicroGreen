import matplotlib.pyplot as plt

##########################################################################################
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman"]

##########################################################################################
GENERATE_PLOTS = False  

##########################################################################################
# monetary cost constants 

# source: https://www.homedepot.com/p/HDX-AA-Alkaline-Battery-60-Pack-7151-60QP/320744454?source=shoppingads&locale=en-US
AA_battery_cost = 0.33  # $ per AA battery

# source: https://www.amazon.com/Rechargeable-Battery-9900mAh-Capacity-Flashlights/dp/B0DZXHQY9M?th=1
battery_18650_cost = 1.6  # $ per 18650 battery

# source: https://www.questcomp.com/part/4/adg819brtz-reel7/103964854?utm_source=google&utm_medium=merchantcenter&utm_term=adg819brtz-reel7&srsltid=afmboor3r_2hnruc6kkxpqdpcms0nd-iwyerclyvdqcakfw4s0-ubble2gi
capacitor_switches_cost = 1.83 # $ per capacitor switch

# IoT solar panel monetary cost source: 
# https://www.adafruit.com/product/5369
# https://store.rakwireless.com/products/solar-panel?srsltid=AfmBOopn8zdl3SbvALAkTu9hFt5cpNAsv2VeRrQb49Qy2UJOx8qrKg8l
# https://www.homedepot.com/p/Yichuhaoxi-6-Watt-10-67-ft-Solar-Panel-with-IP67-Waterproof-Monocrystalline-Module-PET-Material-for-Smart-Phone-Fans-Monitor-1-06827FPH005/334761389?source=shoppingads&locale=en-US&srsltid=AfmBOopnl9WkIkbYA9bbMpPqp9nI3pbV0TU1d1eDn-NXJSN57ykQrl5wNTE
# large solar panel monetary cost sources: 
#https://us.ecoflow.com/products/110w-portable-solar-panel?srsltid=AfmBOorcj7qrZebsb2BQUfJTR0DzkHoryszizYO8FjRed8pG8I3akquj--M&variant=39998109941833
solar_panel_per_cm2_cost = 0.1  # $ per cm² of solar panel
per_capacitor_cost = 1  # $ per capacitor

##########################################################################################
# embodied carbon constant
microphone_carbon = 0.018
image_sensor_carbon = 0.0423
solar_panel_emission_per_cm2 = 0.0168  # kg CO2e per cm² of solar panel
coral_flash_and_dram_carbon = 0.019722  # kg CO2e for flash and dram on coral board
# source: https://www.mouser.com/ProductDetail/Analog-Devices/ADG819BRTZ-REEL7?qs=BpaRKvA4VqHIb%252BZWdVZ1eQ%3D%3D&srsltid=AfmBOorXY9cbpMW-vqXb-9ixTDjEO3OlKgK-unFVEqg1BV0ckpsB2NYU
capacitor_switches_CO2e = 0.004356  # kgCO₂e per capacitor switch
AA_carbon = 0.107  # kgCO₂e per AA battery
battery_18650_carbon = 2  # kgCO2e per 18650 battery
EDLC_carbon_per_F = 0.0506  # kgCO2e per Farad of EDLC capacitor

# NXP series: https://www.nxp.com/products/processors-and-microcontrollers/arm-microcontrollers/i-mx-rt-crossover-mcus:IMX-RT-SERIES
# NXP RT1176: M4@400 + M7@800, 2 MB SRAM, 14mm x 14mm: https://www.nxp.com/part/MIMXRT1176DVMAA
# NXP RT1050: M7@600MHz, 512KB RAM, 10mm x 10mm: https://www.nxp.com/docs/en/data-sheet/IMXRT1050CEC.pdf

RT1126 = 0.236451 #kg CO2e, 1.8mm x 1.8mm
RT1050 = RT1126 / (14*14) * (10*10)  # scale down to 10mm x 10mm

whole_board_carbon = {
    "esp32": 0.21434801070444712 + microphone_carbon + image_sensor_carbon,
    "esp32C6": 0.1973969667044471 + microphone_carbon + image_sensor_carbon,
    "esp32S3": 0.2625468867044471 + microphone_carbon + image_sensor_carbon,
    "nf52840": 0.17534202335999998 + microphone_carbon + image_sensor_carbon,
    "rp2040": 0.3236869288521515 + microphone_carbon + image_sensor_carbon,
    "rp2350": 0.3873442915203545 +  microphone_carbon + image_sensor_carbon,
    "stm32f411fe": 0.4527894151677715 + microphone_carbon + image_sensor_carbon, 
    "nxprt1176+TPU": 1.140981586893209 + image_sensor_carbon,
    "nxprt1176": 1.140981586893209 - RT1126 + RT1050 + image_sensor_carbon 
}

monetary_cost = {
    "esp32": 8,
    "esp32C6": 14.95,
    "esp32S3": 17.5,
    "nf52840": 24.95,
    "rp2040": 4,
    "rp2350": 7,
    "stm32f411fe": 16.5,
    "nxprt1176+TPU": 79.99,
    "nxprt1176": 35,
}

# Device name mapping for cleaner legend labels
device_name_mapping = {
    "esp32": "ESP32",
    "esp32C6": "ESP32-C6",
    "esp32S3": "ESP32-S3",
    "nf52840": "nRF52840",
    "rp2040": "RP2040",
    "rp2350": "RP2350",
    "stm32f411fe": "STM32F4",
    "nxprt1176+TPU": "NXP RT1176 + TPU",
    "nxprt1176": "NXP RT1176",
}

# voltage regulator Cost
voltage_regulator_cost = {
    "esp32": 6.75,
    "esp32C6": 6.75,
    "esp32S3": 6.75,
    "nf52840": 0,
    "rp2040": 0,
    "rp2350": 0,
    "stm32f411fe": 6.75,
    "nxprt1176+TPU": 0,
    "nxprt1176": 0
}

# Calculate CO2 emissions of board                                                                                               
voltage_regulator_CO2 = {
    "esp32": 0.008478224763,
    "esp32C6": 0.008478224763,
    "esp32S3": 0.008478224763,
    "nf52840": 0,
    "rp2040": 0,
    "rp2350": 0,
    "stm32f411fe": 0.008478224763,
    "nxprt1176+TPU": 0,
    "nxprt1176": 0
}

##########################################################################################
# other constants
AA_energy = 11250  # J
battery_18650_energy = 131868  # J
single_capacitor_capacity = 0.47  # in mF, this is the capacity of a single capacitor
solar_panel_efficiency = 0.2  # 20% efficiency for solar panel
us_grid_carbon = 380  # g CO2e per kWh

##########################################################################################
# LoRA transmission and receiving parameters
# https://reyax.com/upload/products_download/download_file/RYLR998_EN.pdf
transmission_current_A = 0.14  # A
transmission_throughput_bytes_per_s = 4400  # bytes/s
receiving_current_A = 0.0175  # A

##########################################################################################
#color scheme for different devices
device_colors = {
    "esp32": "slategrey",
    "esp32C6": "darkviolet",
    "esp32S3": "blue",
    "nf52840": "black",
    "rp2040": "darkgreen",
    "rp2350": "yellowgreen",
    "stm32f411fe": "hotpink",
    "nxprt1176+TPU": "coral",
    "nxprt1176": "darkred",
}

component_colors = {
    "capacitor": plt.cm.tab10.colors[0],
    "solar panel": plt.cm.tab10.colors[1],
    "board": plt.cm.tab10.colors[2],
    "voltage regulator": plt.cm.tab10.colors[3],
    "switch": plt.cm.tab10.colors[4],
    "battery": plt.cm.tab10.colors[5],
}