import os
import time

from eppy.modeleditor import IDF
from eppy.runner.run_functions import runIDFs


def collect_all_idf_files(root_folder):
    idf_files = []

    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(".idf"):
                idf_files.append(os.path.join(root, file))

    return idf_files


def make_eplaunch_options(idf, output_root):
    idf_name = os.path.splitext(
        os.path.basename(idf.idfname)
    )[0]

    output_folder = os.path.join(
        output_root,
        idf_name
    )

    os.makedirs(output_folder, exist_ok=True)

    return {
        "ep_version": "23-1-0",
        "output_prefix": idf_name,
        "output_suffix": "C",
        "output_directory": output_folder,
        "readvars": True,
        "expandobjects": True,
    }


def run_energyplus_batch(
    iddfile,
    epwfile,
    idf_root,
    output_root,
    num_parallel=1
):
    if not os.path.isfile(iddfile):
        raise FileNotFoundError(f"IDD file not found: {iddfile}")

    if not os.path.isfile(epwfile):
        raise FileNotFoundError(f"EPW file not found: {epwfile}")

    if not os.path.isdir(idf_root):
        raise FileNotFoundError(f"IDF folder not found: {idf_root}")

    os.makedirs(output_root, exist_ok=True)

    IDF.setiddname(iddfile)

    idf_files = collect_all_idf_files(idf_root)

    if not idf_files:
        raise FileNotFoundError(f"No IDF files found in: {idf_root}")

    print(f"Found {len(idf_files)} IDF files")

    runs = []

    for idf_file in idf_files:
        print(f"Preparing: {idf_file}")

        idf = IDF(idf_file, epwfile)

        runs.append([
            idf,
            make_eplaunch_options(idf, output_root)
        ])

    start_time = time.time()

    runIDFs(runs, num_parallel)

    elapsed = time.time() - start_time

    print("Simulation completed")
    print(f"Total time: {elapsed:.2f} s")


if __name__ == "__main__":

    base_dir = os.path.dirname(os.path.abspath(__file__))

    iddfile = r"C:\EnergyPlusV23-1-0\Energy+.idd"

    epwfile = os.path.join(
        base_dir,
        "input",
        "epw",
        "NANJING",
        "Nanjing_2020.epw"
    )

    idf_root = os.path.join(
        base_dir,
        "ready_idf",
        "demo"
    )

    output_root = os.path.join(
        base_dir,
        "result",
        "demo"
    )

    run_energyplus_batch(
        iddfile=iddfile,
        epwfile=epwfile,
        idf_root=idf_root,
        output_root=output_root,
        num_parallel=1
    )