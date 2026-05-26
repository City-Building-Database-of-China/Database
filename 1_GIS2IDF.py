import os
import re
import json
import warnings
os.environ["USE_PYGEOS"] = "0"
import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import Polygon
from pyproj import Transformer

import geomeppy
from geomeppy import IDF

from eppy.modeleditor import IDF as epIDF
import eppy.json_functions as json_functions

warnings.filterwarnings("ignore")

base_dir = os.path.dirname(os.path.abspath(__file__))

schedule_sheetname = [
    "SCHEDULETYPELIMITS",
    "SCHEDULE_DAY_HOURLY",
    "SCHEDULE_WEEK_DAILY",
    "SCHEDULE_YEAR"
]

mat_sheetname = [
    "MATERIAL_NOMASS",
    "WINDOWMATERIAL"
]

con_sheetname = [
    "CONSTRUCTION"
]

hvac_sheetname = [
    "THERMOSTATSETPOINT_DUALSETPOINT",
    "DESIGNSPECIFICATION_OUTDOORAIR",
    "HVACTEMPLATE_THERMOSTAT"
]

sheet_name_simulation = [
    "SITE_LOCATION",
    "SIZINGPERIOD_DESIGNDAY",
    "SIMULATIONCONTROL",
    "TIMESTEP",
    "BUILDING",
    "RUNPERIOD",
    "SHADOWCALCULATION",
    "GLOBALGEOMETRYRULES",
    "OUTPUT_VARIABLEDICTIONARY"
]

zone_listset_sheetname = [
    "PEOPLE",
    "LIGHTS",
    "ELECTRICEQUIPMENT",
    "ZONEINFILTRATION_DESIGNFLOWRATE"
]


def initialize_idf_environment(version, epw_path):
    # EnergyPlus install path is machine-specific (not relative to this repo). Edit if needed.
    IDF.setiddname(
        f"C:\\EnergyPlusV{version}\\PreProcess\\IDFVersionUpdater\\V{version}-Energy+.idd"
    )
    idf = IDF(f"C:\\EnergyPlusV{version}\\ExampleFiles\\Minimal.idf")
    idf.epw = epw_path
    return idf


def process_polygon_coordinates(coordinates):
    def calculate_polygon_area(coords):
        n = len(coords)
        area = 0.0
        for i in range(n - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            area += x1 * y2 - x2 * y1
        return area / 2.0

    list_x_y = []

    if isinstance(coordinates[0], list):
        for point in coordinates:
            if isinstance(point[0], list):
                list_x_y.extend(point)
            else:
                list_x_y.append(point)
    else:
        list_x_y.append(coordinates)

    xy_coords = [
        (x, y)
        for point in list_x_y
        if len(point) >= 2
        for x, y in [point[:2]]
    ]

    area = calculate_polygon_area(xy_coords)

    if area < 0:
        list_x_y.reverse()

    if list_x_y and list_x_y[0] == list_x_y[-1]:
        list_x_y.pop()

    return list_x_y


def calculate_centroid_coordinates(list_x_y):
    ref_polygon = Polygon(list_x_y)
    P_c = ref_polygon.centroid.wkt
    P_coo = re.split(r"\(|\)| |,", P_c)
    P_coo = [coord for coord in P_coo if coord]
    return P_coo


def classify_surfaces(listsurface):
    floor_surfaces = [sf for sf in listsurface if sf.Surface_Type == "floor"]
    ceiling_surfaces = [sf for sf in listsurface if sf.Surface_Type == "ceiling"]
    roof_surfaces = [sf for sf in listsurface if sf.Surface_Type == "roof"]
    wall_surfaces = [sf for sf in listsurface if sf.Surface_Type == "wall"]

    all_empty = all(
        sf.Outside_Boundary_Condition in [None, ""]
        for sf in listsurface
    )

    if all_empty:
        for sf in floor_surfaces:
            if sf.Zone_Name == "Storey 0":
                sf.Outside_Boundary_Condition = "Ground"
                break

        for sf in wall_surfaces:
            sf.Outside_Boundary_Condition = "Outdoors"

        for sf in roof_surfaces:
            sf.Outside_Boundary_Condition = "Outdoors"

        for sf in ceiling_surfaces:
            sf.Outside_Boundary_Condition = "Surface"

        for sf in floor_surfaces:
            if sf.Outside_Boundary_Condition == "Ground":
                continue
            sf.Outside_Boundary_Condition = "Surface"

    exterior_walls = [
        sf for sf in wall_surfaces
        if sf.Outside_Boundary_Condition == "Outdoors"
    ]

    interior_walls = [
        sf for sf in wall_surfaces
        if sf.Outside_Boundary_Condition != "Outdoors"
    ]

    notground_floor_surfaces = [
        sf for sf in floor_surfaces
        if sf.Outside_Boundary_Condition != "Ground"
    ]

    notground_floor_surfaces.extend(ceiling_surfaces)

    dict_construction = {
        "interior_wall": interior_walls,
        "exterior_wall": exterior_walls,
        "floor": notground_floor_surfaces,
        "ground": [
            sf for sf in floor_surfaces
            if sf.Outside_Boundary_Condition == "Ground"
        ],
        "roof": roof_surfaces
    }

    return dict_construction


def add_windows_to_walls(dict_construction, function_list, data_wwr, idf):
    exterior_walls = dict_construction.get("exterior_wall", [])

    def create_window(wall, direction, function_name, wwr):
        pt = geomeppy.recipes.window_vertices_given_wall(wall, wwr)

        idf.newidfobject(
            "FENESTRATIONSURFACE:DETAILED",
            Name=f"{wall.Name}window",
            Surface_Type="Window",
            Building_Surface_Name=wall.Name,
            Construction_Name=f"{function_name}_{direction}_window_construction",
            Vertex_1_Xcoordinate=str(pt[0][0]),
            Vertex_1_Ycoordinate=str(pt[0][1]),
            Vertex_1_Zcoordinate=str(pt[0][2]),
            Vertex_2_Xcoordinate=str(pt[1][0]),
            Vertex_2_Ycoordinate=str(pt[1][1]),
            Vertex_2_Zcoordinate=str(pt[1][2]),
            Vertex_3_Xcoordinate=str(pt[2][0]),
            Vertex_3_Ycoordinate=str(pt[2][1]),
            Vertex_3_Zcoordinate=str(pt[2][2]),
            Vertex_4_Xcoordinate=str(pt[3][0]),
            Vertex_4_Ycoordinate=str(pt[3][1]),
            Vertex_4_Zcoordinate=str(pt[3][2])
        )

    for wall in exterior_walls:
        for function_name in function_list:
            if function_name in wall.Name:
                wall.Construction_Name = f"{function_name}_exterior_wall_construction"

                if 315 < wall.azimuth <= 360 or 0 <= wall.azimuth <= 45:
                    create_window(
                        wall,
                        "north",
                        function_name,
                        data_wwr.loc[str(function_name), "north"]
                    )
                elif 45 < wall.azimuth <= 135:
                    create_window(
                        wall,
                        "east",
                        function_name,
                        data_wwr.loc[str(function_name), "east"]
                    )
                elif 135 < wall.azimuth <= 225:
                    create_window(
                        wall,
                        "south",
                        function_name,
                        data_wwr.loc[str(function_name), "south"]
                    )
                elif 225 < wall.azimuth <= 315:
                    create_window(
                        wall,
                        "west",
                        function_name,
                        data_wwr.loc[str(function_name), "west"]
                    )


def assign_construction_name(dict_construction, function_list, surface_type):
    surfaces = dict_construction.get(surface_type, [])

    for surface in surfaces:
        for function_name in function_list:
            if function_name in surface.Name:
                surface.Construction_Name = f"{function_name}_{surface_type}_construction"


def print_surface_counts(dict_construction):
    for category, surfaces in dict_construction.items():
        print(f"{category.replace('_', ' ').title()} Count: {len(surfaces)}")


def convert_latlon_to_utm(latlon_coords, zone_number):
    transformer = Transformer.from_proj(
        proj_from="epsg:4326",
        proj_to=f"+proj=utm +zone={zone_number} +datum=WGS84"
    )

    utm_coords = []

    for lon, lat, _ in latlon_coords:
        easting, northing = transformer.transform(lat, lon)
        utm_coords.append([easting, northing])

    return utm_coords


def check_external_wall_conditions(listsurface, idf, bh, land_use, floor, start_index):
    newlistsurface = listsurface[start_index:]

    list_floornum = []

    for m in range(floor):
        wallname = f"Block {bh} {land_use} Storey {m} Wall"
        list_onezonewall = []
        zone_condition = 0

        for surface in newlistsurface:
            if wallname in surface.Name:
                list_onezonewall.append(surface)

        for q in list_onezonewall:
            if q.Outside_Boundary_Condition != "surface":
                zone_condition = 1

        if zone_condition == 1:
            list_floornum.append(f"Block {bh} {land_use} Storey {m}")

    final_index = len(listsurface)

    return list_floornum, final_index


def set_daylighting_controls(
    idf,
    list_floornum,
    P_coo,
    floor_change,
    land_use,
    setpoint_commercial="500",
    setpoint_residential="300"
):
    x_coord = float(P_coo[1])
    y_coord = float(P_coo[2])

    for k in list_floornum:
        num_floor = re.findall(r"\d+", k)
        storey_number = int(num_floor[-1])

        daylightpoint = idf.newidfobject(
            "DAYLIGHTING:REFERENCEPOINT",
            Name="Rpoint_" + str(k)
        )

        daylightpoint.Zone_or_Space_Name = str(k)
        daylightpoint.XCoordinate_of_Reference_Point = x_coord
        daylightpoint.YCoordinate_of_Reference_Point = y_coord
        daylightpoint.ZCoordinate_of_Reference_Point = (
            storey_number * float(floor_change) + 0.8
        )

        Daylight = epIDF.newidfobject(
            self=idf,
            key="DAYLIGHTING:CONTROLS",
            Name="Dlight_" + str(k),
            defaultvalues=False
        )

        Daylight.Zone_or_Space_Name = str(k)
        Daylight.Daylighting_Reference_Point_1_Name = daylightpoint.Name
        Daylight.Glare_Calculation_Daylighting_Reference_Point_Name = daylightpoint.Name

        if land_use in ["Commercial", "Hospital", "Industrial"]:
            Daylight.Illuminance_Setpoint_at_Reference_Point_1 = setpoint_commercial
        else:
            Daylight.Illuminance_Setpoint_at_Reference_Point_1 = setpoint_residential


def create_space_lists(idf, list_all_building, function_list):
    space_list_allname = []

    dict_fuctionforinfilteration = {
        func: []
        for func in function_list
    }

    for func in function_list:
        if func in list_all_building:
            space_list = idf.newidfobject("SPACELIST", str(func))
            space_list_for_infilteration = idf.newidfobject(
                "SPACELIST",
                str(func) + "_infilteration"
            )

            for idx, zone_name in enumerate(list_all_building[func]):
                space_one = idf.newidfobject("SPACE", zone_name + "_space")
                space_one["Zone_Name"] = zone_name
                space_one["Space_Type"] = func
                space_list[f"Space_{idx + 1}_Name"] = zone_name + "_space"

            for idx, infilteration_space in enumerate(
                dict_fuctionforinfilteration.get(func, [])
            ):
                space_list_for_infilteration[
                    f"Space_{idx + 1}_Name"
                ] = infilteration_space + "_space"

            space_list_allname.extend([
                space_list.Name,
                space_list_for_infilteration.Name
            ])

    return space_list_allname


def process_device_data(
    excel_path,
    zone_listset_sheetname,
    space_list_allname,
    idf,
    list_all_building
):
    dict_sub_1 = {}

    for sheet_name in zone_listset_sheetname:
        data_toimport_2 = pd.read_excel(
            excel_path,
            sheet_name=sheet_name,
            keep_default_na=False
        )

        for device_name in data_toimport_2["Name"]:
            for function_type in list_all_building.keys():
                if function_type in device_name:
                    idf.newidfobject(
                        data_toimport_2.columns[1],
                        Name=device_name
                    )

        for attribute in data_toimport_2.columns[3:]:
            for idx in range(len(data_toimport_2)):
                if data_toimport_2.iloc[idx, 3] in space_list_allname:
                    if len(str(data_toimport_2[attribute][idx])) != 0:
                        key = (
                            f"{'.'.join(data_toimport_2.columns[:2])}."
                            f"{data_toimport_2['Name'][idx]}."
                            f"{attribute}"
                        )
                        dict_sub_1[key] = str(data_toimport_2[attribute][idx])

    return dict_sub_1


def extract_simulation_data(non_geomdata_path, sheet_names):
    dict_sub_simulation = {}

    for sheet_name in sheet_names:
        data_simulation = pd.read_excel(
            non_geomdata_path,
            sheet_name=sheet_name,
            keep_default_na=False
        )

        if "Name" in data_simulation:
            for k in data_simulation.columns[3:]:
                for q in range(len(data_simulation)):
                    value = str(data_simulation.at[q, k])
                    if value:
                        key = ".".join(data_simulation.columns[0:2]) + ".Name"
                        dict_sub_simulation[key] = str(
                            data_simulation.at[q, "Name"]
                        )

                        key = (
                            ".".join(data_simulation.columns[0:2])
                            + "."
                            + str(data_simulation.at[q, "Name"])
                            + "."
                            + str(k)
                        )
                        dict_sub_simulation[key] = value
        else:
            for m in data_simulation.columns[2:]:
                for n in range(len(data_simulation)):
                    value = str(data_simulation.at[n, m])
                    if value:
                        key = ".".join(data_simulation.columns[0:2]) + "." + str(m)
                        dict_sub_simulation[key] = value

    return dict_sub_simulation


def set_output_table_style(idf, style_name):
    idf.newidfobject(
        "OutputControl:Table:Style",
        Style=style_name
    )


def process_excel_to_idf(input_sheetname, non_geomdata_Path, idf):
    dict_sub = {}

    for sheet_name in input_sheetname:
        data_toimport_1 = pd.read_excel(
            non_geomdata_Path,
            sheet_name=sheet_name,
            keep_default_na=False
        )

        for j in range(len(data_toimport_1["Name"])):
            idf.newidfobject(
                data_toimport_1.columns[1],
                Name=data_toimport_1["Name"][j]
            )

        for k in data_toimport_1.columns[3:]:
            for q in range(len(data_toimport_1.iloc[:, 3])):
                if len(str(data_toimport_1[str(k)][q])) != 0:
                    key = (
                        ".".join(data_toimport_1.columns[0:2])
                        + "."
                        + str(data_toimport_1["Name"][q])
                        + "."
                        + str(k)
                    )
                    dict_sub[key] = str(data_toimport_1[str(k)][q])

    return dict_sub


def remove_idf_objects(idf, object_type):
    num_objects = len(idf.idfobjects[object_type])

    for _ in range(num_objects):
        idf.popidfobject(object_type, 0)


def run_idf_generation(
    shpfile_path,
    epw_path,
    non_geometry_data_path,
    age_data_folder,
    save_folder,
    version="23-1-0",
    floor_height=3
):
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    function_list = list(
        pd.read_excel(
            non_geometry_data_path,
            sheet_name="Functions",
            keep_default_na=False
        )["Functions"]
    )

    file_name = os.path.basename(shpfile_path)
    print(f"Processing SHP file: {file_name}")

    data = gpd.read_file(shpfile_path)

    data["useLandTyp"] = data["landUseTyp"]
    data["useLandTyp"] = data["useLandTyp"].replace("Commerial", "Commercial")
    data["useLandTyp"] = data["useLandTyp"].replace("Industry", "Industrial")

    part_buildings_jsonstr = data.to_json()
    part_buildings_json = json.loads(part_buildings_jsonstr)

    sequence_dict = {
        item["properties"]["bh"]: item
        for item in part_buildings_json["features"]
    }

    for index, row in data.iterrows():
        feature = sequence_dict.get(row["bh"], None)
        num_1 = 0

        if feature is not None:
            bh = str(int(row["bh"]))
            print(f"Processing building: {bh}")

            idf = initialize_idf_environment(version, epw_path)

            remove_idf_objects(idf, "OUTPUT:VARIABLE")
            remove_idf_objects(idf, "OUTPUTCONTROL:TABLE:STYLE")
            remove_idf_objects(idf, "SIZINGPERIOD:DESIGNDAY")
            remove_idf_objects(idf, "OUTPUT:TABLE:SUMMARYREPORTS")

            land_use = feature["properties"].get("useLandTyp", "Unknown")

            elevation = round(feature["properties"].get("Height", 0))
            floor = int(elevation / floor_height) + (elevation % floor_height > 0)

            coordinates = feature["geometry"]["coordinates"]
            processed_coords = process_polygon_coordinates(coordinates)
            centroid_coords = calculate_centroid_coordinates(processed_coords)

            building_name = f"{bh} {land_use}"

            idf.add_block(
                name=building_name,
                coordinates=processed_coords,
                height=elevation,
                num_stories=floor,
                zoning="by_storey"
            )

            zone_lists = idf.idfobjects["ZONE"]
            surfaces = idf.idfobjects["BUILDINGSURFACE:DETAILED"]

            dict_construction = classify_surfaces(surfaces)

            age = feature["properties"].get("Age_Data")
            age_path = os.path.join(
                age_data_folder,
                f"{age}.xlsx"
            )

            data_wwr = pd.read_excel(
                age_path,
                sheet_name="WWR",
                index_col=0,
                keep_default_na=False
            )

            add_windows_to_walls(
                dict_construction,
                function_list,
                data_wwr,
                idf
            )

            listsurface = idf.idfobjects["BUILDINGSURFACE:DETAILED"]

            list_floornum, num_1 = check_external_wall_conditions(
                listsurface,
                idf,
                bh,
                land_use,
                floor,
                num_1
            )

            set_daylighting_controls(
                idf,
                list_floornum,
                centroid_coords,
                floor_height,
                land_use,
                "500",
                "300"
            )

            idf.set_default_constructions()

            list_all_building = {
                i: [
                    j.Name for j in zone_lists
                    if i in j.Name
                ]
                for i in function_list
            }

            space_list_allname = create_space_lists(
                idf,
                list_all_building,
                function_list
            )

            device_data_dict = process_device_data(
                non_geometry_data_path,
                zone_listset_sheetname,
                space_list_allname,
                idf,
                list_all_building
            )

            json_functions.updateidf(idf, device_data_dict)

            dict_sub_schedule = process_excel_to_idf(
                schedule_sheetname,
                non_geometry_data_path,
                idf
            )

            json_functions.updateidf(idf, dict_sub_schedule)

            dict_sub_mat = process_excel_to_idf(
                mat_sheetname,
                age_path,
                idf
            )

            json_functions.updateidf(idf, dict_sub_mat)

            dict_sub_con = process_excel_to_idf(
                con_sheetname,
                non_geometry_data_path,
                idf
            )

            json_functions.updateidf(idf, dict_sub_con)

            idf.match()

            dict_sub_hvac = process_excel_to_idf(
                hvac_sheetname,
                non_geometry_data_path,
                idf
            )

            json_functions.updateidf(idf, dict_sub_hvac)

            for function_name in list_all_building.keys():
                for zone_name in list_all_building[function_name]:
                    hvac = idf.newidfobject(
                        "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM"
                    )

                    hvac.Zone_Name = str(zone_name)
                    hvac.Template_Thermostat_Name = (
                        "Thermostat_for_" + str.lower(function_name)
                    )
                    hvac.Outdoor_Air_Method = "DetailedSpecification"
                    hvac.Design_Specification_Outdoor_Air_Object_Name = (
                        "Ventilation_for_" + str.lower(function_name)
                    )

            simulation_data = extract_simulation_data(
                non_geometry_data_path,
                sheet_name_simulation
            )

            json_functions.updateidf(idf, simulation_data)

            idf.newidfobject(
                "OUTPUT:TABLE:SUMMARYREPORTS",
                Report_1_Name="AllSummary"
            )

            idf.newidfobject(
                "OUTPUTCONTROL:TABLE:STYLE",
                Column_Separator="HTML",
                Unit_Conversion="JtoKWH"
            )

            sql = idf.newidfobject("OUTPUT:SQLITE")
            sql["Option_Type"] = "SimpleAndTabular"

            save_path = os.path.join(
                save_folder,
                f"{os.path.splitext(file_name)[0]}_{bh}.idf"
            )

            idf.save(save_path, encoding="utf-8")

            print(f"Saved: {save_path}")


if __name__ == "__main__":
    # All paths below are relative to this repository (base_dir = folder containing this script).
    # Use Prototype GIS for replication (not CityBuilding full-city zips under input/GIS/CityBuilding/)
    shpfile_path = os.path.join(
        base_dir,
        "input",
        "GIS",
        "Prototype",
        "320100NANJINGSHI.shp"
    )

    epw_path = os.path.join(
        base_dir,
        "input",
        "EPW",
        "NANJING",
        "Nanjing_2020.epw"
    )

    non_geometry_data_path = os.path.join(
        base_dir,
        "input",
        "Setting",
        "non_geomtry_data_all.xlsx"
    )

    age_data_folder = os.path.join(
        base_dir,
        "input",
        "Setting",
        "age_de"
    )

    save_folder = os.path.join(
        base_dir,
        "ready_idf",
        "320100NANJINGSHI"
    )

    version = "23-1-0"
    floor_height = 3

    print("Starting IDF generation.")

    run_idf_generation(
        shpfile_path=shpfile_path,
        epw_path=epw_path,
        non_geometry_data_path=non_geometry_data_path,
        age_data_folder=age_data_folder,
        save_folder=save_folder,
        version=version,
        floor_height=floor_height
    )

    print("IDF generation completed.")
