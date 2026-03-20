import pandas as pd
import numpy as np
import os, math

from helper import *
from constants import *

# -----------------------
# device parameters
Vl = 4.5  # V
Vh = 5.5  # V

solar_panel_efficiency = 0.2

# Workloads 
image_capturing_latency_ms = 38.917
image_capturing_energy_mJ = 30.54
image_capturing_min_cap_size_mF = 2*image_capturing_energy_mJ / (Vh**2 - Vl**2) 

PPD_inference_latency_ms = 4.473
PPD_inference_energy_mJ = 10.45
PPD_min_cap_size_mF = 2*PPD_inference_energy_mJ / (Vh**2 - Vl**2)

YOLOv8_latency_ms = 286.402 - image_capturing_latency_ms
YOLOv8_energy_mJ = 245.07 - image_capturing_energy_mJ
YOLOv8_min_cap_size_mF = 2*YOLOv8_energy_mJ / (Vh**2 - Vl**2)

inference_per_second = 6

seconds_per_day = 24 * 60 * 60
# -----------------------
# solar traces import
file_dir = os.path.dirname(os.path.abspath(__file__))
solar_5000 = pd.read_pickle(file_dir + "/synthetic_traces/solar_pkl/synthetic_irradiance_day_0_5000_1s_sinwave.pkl")
solar_10000 = pd.read_pickle(file_dir + "/synthetic_traces/solar_pkl/synthetic_irradiance_day_0_10000_1s_sinwave.pkl")
solar_50000 = pd.read_pickle(file_dir + "/synthetic_traces/solar_pkl/synthetic_irradiance_day_0_50000_1s_sinwave.pkl")

# -----------------------
# visitor flow trace import
large_Columbus_Circle = pd.read_pickle(file_dir + "/synthetic_traces/visitorFlow_pkl/large_Columbus_Circle.pkl")
mid_E_72nd = pd.read_pickle(file_dir + "/synthetic_traces/visitorFlow_pkl/mid_E_72nd.pkl")
small_Central_Park_North = pd.read_pickle(file_dir + "/synthetic_traces/visitorFlow_pkl/small_Central_Park_North.pkl")

# -----------------------
solar_traces = {"solar_50000": solar_50000, "solar_10000": solar_10000, "solar_5000": solar_5000}
visitor_traces = {"large_Columbus_Circle": large_Columbus_Circle, "mid_E_72nd": mid_E_72nd, "small_Central_Park_North": small_Central_Park_North}
solar_panel_sizes_cm2 = [0, 74.58, 304.0, 611.0, math.inf]  # cm^2

# -----------------------

def simulate_daily_operation(SOLAR_PANEL_AREA_CM2):
    # counters
    total_images_captured = 0
    total_PPD_inferences = 0
    total_YOLOv8_inferences = 0

    # energy bookkeeping
    capacitor_energy_mJ = 0  # energy stored in capacitor at the start of the day
    total_capcitor_energy_needed_mJ = 0
    battery_energy_mJ = 0  # total energy drawn from battery
    daily_energy_needed_mJ = 0
    total_energy_mJ_harvested_per_cm2 = 0

    for second in range(seconds_per_day):
        # -----------------------
        # calculate the amount of YOLOv8 I need to run with the visitor flow trace
        visitors_this_second = CHOSEN_VISITOR_TRACE.loc[
            CHOSEN_VISITOR_TRACE["Second"] == second, "daily visits"
        ].values[0]

        if visitors_this_second > 0:
            # assume each visitor requires one YOLOv8 inference
            YOLOv8_inferences_needed = inference_per_second
        else:
            YOLOv8_inferences_needed = 0

        # other inferences and tasks needed at this second
        images_captured = inference_per_second
        PPD_inferences = inference_per_second

        # accumulate totals
        total_images_captured += images_captured
        total_PPD_inferences += PPD_inferences
        total_YOLOv8_inferences += YOLOv8_inferences_needed

        # -----------------------
        # total energy needed at this second
        total_energy_needed_mJ = (
            images_captured * image_capturing_energy_mJ
            + PPD_inferences * PPD_inference_energy_mJ
            + YOLOv8_inferences_needed * YOLOv8_energy_mJ
        )

        daily_energy_needed_mJ += total_energy_needed_mJ
        # calculate harvested energy at this second
        irradiance_microW_per_cm2 = CHOSEN_SOLAR_TRACE.loc[second, "irr,microW/cm^2"]
        irradiance_W_per_cm2 = irradiance_microW_per_cm2 / 1e6  # W/cm^2
        # if the solar panel size is infinite, we calculate the needed size to cover all energy
        irradiance_energy_J_per_s = irradiance_W_per_cm2 * solar_panel_efficiency
        total_energy_mJ_harvested_per_cm2 += irradiance_energy_J_per_s * 1000.0  # mJ per 
        curr_solar_power_W = (
            irradiance_W_per_cm2 * SOLAR_PANEL_AREA_CM2 * solar_panel_efficiency
        )  # W
        curr_solar_energy_J = curr_solar_power_W * 1.0  # J (since time step is 1 second)
        curr_solar_energy_mJ = curr_solar_energy_J * 1000.0  # mJ

        total_capcitor_energy_needed_mJ += curr_solar_energy_mJ

        # energy needed from battery vs capacitor
        if capacitor_energy_mJ + curr_solar_energy_mJ >= total_energy_needed_mJ:
            capacitor_energy_mJ += (curr_solar_energy_mJ - total_energy_needed_mJ)
        else:
            battery_energy_mJ += (total_energy_needed_mJ - curr_solar_energy_mJ)

    # compute wireless carbon footprint
    hourly_packet_size_bytes = 4  # bytes
    total_data_bytes = hourly_packet_size_bytes * 24  # bytes per day
    transmission_time_s = total_data_bytes / transmission_throughput_bytes_per_s  # s
    wireless_energy_J = transmission_current_A * 3.3 * transmission_time_s  # J
    print("wireless energy (J):", wireless_energy_J)

    battery_energy_mJ = max(0, wireless_energy_J * 1000.0 - capacitor_energy_mJ) + battery_energy_mJ
    print("battery energy needed (mJ) daily:", battery_energy_mJ)

    # total_AA_batteries_used = battery_energy_mJ / 1000 / AA_energy
    # battery_carbon_footprint_kg = total_AA_batteries_used * AA_carbon

    total_18650_batteries_used_daily = battery_energy_mJ / 1000 / battery_18650_energy
    print("total 18650 batteries used daily:", total_18650_batteries_used_daily)

    # calculate the number of 18650 batteries needed to support two weeks of operation
    num_batteries_needed = math.ceil(total_18650_batteries_used_daily * 7) if total_18650_batteries_used_daily > 0 else 0

    # TODO: need to add carbon footprint from charging the battery from US grid
    battery_18650_energy_kWh = battery_energy_mJ / 1000 / 3600 / 1000  # kWh
    battery_grid_carbon_kg = battery_18650_energy_kWh * us_grid_carbon / 1000.0
    print("battery grid carbon footprint (kg CO2):", battery_grid_carbon_kg)

    # calculate if all tasks can be completed within the day
    total_execution_time_ms = (
        total_images_captured * image_capturing_latency_ms
        + total_PPD_inferences * PPD_inference_latency_ms
        + total_YOLOv8_inferences * YOLOv8_latency_ms
        + transmission_time_s * 1000.0
    )
    print("total execution time (ms):", total_execution_time_ms)
    if total_execution_time_ms > seconds_per_day * 1000:
        print("Error: total execution time exceeds available time in a day!")
        raise RuntimeError("total execution time exceeds available time in a day!")

    # calculate capacitor number based on design
    print("total capacitor energy needed (mJ):", total_capcitor_energy_needed_mJ)
    number_of_capacitor_recharges = total_capcitor_energy_needed_mJ / (150000 * 5 * 1000)
    # each capacitor can be recharged 150,000 times, 5J of energy in one capacitor
    print("number of capacitor recharges:", number_of_capacitor_recharges)
    if number_of_capacitor_recharges > 12:
        print("Error: two capacitors cannot support the workflow!")
        # if you prefer to actually stop, raise instead of exit in a function
        raise RuntimeError("two capacitors cannot support the workflow!")
    else:
        number_of_capacitors = 2
        number_of_capacitor_switches = number_of_capacitors - 1

    # calculate the total embodied carbon footprint of the system
    print("----- Embodied Carbon Footprint Calculation -----")

    board_CO2 = whole_board_carbon["nxprt1176+TPU"] + coral_flash_and_dram_carbon

    print("board CO2 (kg):", board_CO2)

    solar_panel_carbon = SOLAR_PANEL_AREA_CM2 * solar_panel_emission_per_cm2
    print("solar panel CO2 (kg):", solar_panel_carbon)

    capacitor_carbon = (
        number_of_capacitors * EDLC_carbon_per_F if SOLAR_PANEL_AREA_CM2 > 0 else 0
    )
    print("capacitor CO2 (kg):", capacitor_carbon)

    capacitor_switch_carbon = (
        number_of_capacitor_switches * capacitor_switches_CO2e
        if SOLAR_PANEL_AREA_CM2 > 0
        else 0
    )
    print("capacitor switch CO2 (kg):", capacitor_switch_carbon)

    # calculate if battery is needed
    num_batteries_needed = max(daily_energy_needed_mJ - total_energy_mJ_harvested_per_cm2 * SOLAR_PANEL_AREA_CM2, 0) / (battery_18650_energy * 1000) * 7
    print("daily energy needed (mJ):", daily_energy_needed_mJ)
    print("total energy harvested per cm2 (mJ):", total_energy_mJ_harvested_per_cm2)
    if num_batteries_needed == 0:
        battery_grid_carbon_kg = 0
    print("batteries needed to support two weeks of operation:", num_batteries_needed)


    print(
        "18650 battery carbon footprint (kg CO2):",
        num_batteries_needed * battery_18650_carbon if SOLAR_PANEL_AREA_CM2 != math.inf else 0,
    )  # assume 4x 18650 batteries used

    if SOLAR_PANEL_AREA_CM2 != math.inf:
        total_embodied_carbon_kg = (
            board_CO2
            + solar_panel_carbon
            + capacitor_carbon
            + capacitor_switch_carbon
            + battery_18650_carbon * num_batteries_needed 
        )
    else:
        total_embodied_carbon_kg = (
            board_CO2
            + capacitor_carbon
            + capacitor_switch_carbon
            + (daily_energy_needed_mJ / total_energy_mJ_harvested_per_cm2) * solar_panel_emission_per_cm2
        )
    print("total embodied carbon footprint (kg CO2):", total_embodied_carbon_kg)

    print("----- Operational Carbon Footprint Calculation -----")
    print("daily battery grid carbon footprint (kg CO2):", battery_grid_carbon_kg)

    print("----- End of Simulation -----")

    print("solar panel area used (cm^2):", SOLAR_PANEL_AREA_CM2 if SOLAR_PANEL_AREA_CM2 != math.inf else  (daily_energy_needed_mJ / total_energy_mJ_harvested_per_cm2))

    # return key metrics as a dict for later analysis
    return {
        "total_18650_batteries_used_daily": total_18650_batteries_used_daily if SOLAR_PANEL_AREA_CM2 != math.inf else 0,
        "num_batteries_needed_for_two_weeks": num_batteries_needed if SOLAR_PANEL_AREA_CM2 != math.inf else 0,
        # "battery_18650_carbon_footprint_kg": battery_18650_carbon_footprint_kg,
        "battery_grid_carbon_kg": battery_grid_carbon_kg if SOLAR_PANEL_AREA_CM2 != math.inf else 0,
        "board_carbon": board_CO2,
        "solar_panel_carbon": solar_panel_carbon,
        "capacitor_carbon": capacitor_carbon,
        "capacitor_switch_carbon": capacitor_switch_carbon,
        "battery_18650_carbon_per_2_years": battery_18650_carbon * num_batteries_needed if SOLAR_PANEL_AREA_CM2 != math.inf else 0,
        "total_embodied_carbon_kg": total_embodied_carbon_kg,
        "SOLAR_PANEL_AREA_CM2": SOLAR_PANEL_AREA_CM2 if SOLAR_PANEL_AREA_CM2 != math.inf else (daily_energy_needed_mJ / total_energy_mJ_harvested_per_cm2),
    }

# -----------------------
results_list = []

solar_trace_to_location = {
    "solar_5000": "mid_E_72nd",
    "solar_10000": "small_Central_Park_North",
    "solar_50000": "large_Columbus_Circle"
}

for solar_panel_size in solar_panel_sizes_cm2:
    print("===== Solar Panel Size (cm^2):", solar_panel_size, " =====\n")
    SOLAR_PANEL_AREA_CM2 = solar_panel_size
    for solar_trace_name, location_name in solar_trace_to_location.items():
        print("***** Solar Trace Max Irradiance (microW/cm^2):", solar_trace_name, " *****\n")
        CHOSEN_SOLAR_TRACE = solar_traces[solar_trace_name]
        CHOSEN_VISITOR_TRACE = visitor_traces[location_name]
        print("----- Visitor Trace:", location_name, " -----\n")
        sim_out = simulate_daily_operation(SOLAR_PANEL_AREA_CM2)
        print("\n\n")

        sim_out.update({
            "solar_panel_size_cm2": solar_panel_size if solar_panel_size != math.inf else sim_out["SOLAR_PANEL_AREA_CM2"],
            "visitor_trace_name": location_name,
            "solar_trace_max_irradiance": solar_trace_name,
        }) 

        results_list.append(sim_out)

results_df = pd.DataFrame(results_list)
results_df.to_csv("database/heterogeneous_deployment_simulation_results.csv", index=False)





