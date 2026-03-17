from constants import * 

##########################################################################################
# datafram construction helper functions
def calculate_energy_in_capacitors(number_of_capacitors, Vh, Vl):
    # Energy stored in capacitors (in mJ)
    energy_stored_mJ = (
        number_of_capacitors * single_capacitor_capacity * (Vh**2 - Vl**2) / 2
    )
    return energy_stored_mJ

# def calculate_solar_panel_area(inference_energy_mJ, irradiance=irradiance, inference_per_second=inference_per_second):
def calculate_solar_panel_area(inference_energy_mJ, irradiance, inference_per_second):
    energy_per_second_mJ = inference_energy_mJ * inference_per_second  # in mJ
    power_per_second_uW = energy_per_second_mJ * 1000  # convert mJ to uW (1 mJ = 1000 uW·s)
    area_cm2 = power_per_second_uW / (irradiance * solar_panel_efficiency)  # in cm²
    return area_cm2

# def calculate_charging_time_per_inference(energy_in_capacitors_mJ, solar_panel_area_cm2, irradiance=irradiance):
def calculate_charging_time_per_inference(energy_in_capacitors_mJ, solar_panel_area_cm2, irradiance):
    # Calculate the charging time in seconds
    charging_time_s = energy_in_capacitors_mJ / ((irradiance / 1000) * solar_panel_efficiency * solar_panel_area_cm2) 
    return charging_time_s

##########################################################################################
# component color unifying helper functions

def get_component_color_for_column(column_name: str, component_colors_dict=None):
    """
    Given a full column name like 'kg CO2e (capacitor only)',
    return the matching color from component_colors_dict based on keyword.
    """
    if component_colors_dict is None:
        component_colors_dict = component_colors

    col_lower = column_name.lower()
    for keyword, color in component_colors_dict.items():
        if keyword in col_lower:
            return color

    raise KeyError(f"No matching color keyword found in '{column_name}'.")


def map_components_to_colors(components, component_colors_dict=None):
    """
    Map a list of component column names to a list of colors using
    get_component_color_for_column.
    """
    return [
        get_component_color_for_column(comp, component_colors_dict)
        for comp in components
    ]