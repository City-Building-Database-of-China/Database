"""
Batch EnergyPlus runs.

Default: demo/ready_idf -> demo/result (Nanjing weather).
EnergyPlus location: set ENERGYPLUS_DIR, or use the default install path
resolved in config.py.
"""
from __future__ import annotations

import os
import time

from eppy.modeleditor import IDF
from eppy.runner.run_functions import runIDFs

from config import (
    DEMO_READY_IDF_DIR,
    DEMO_RESULT_DIR,
    NANJING_EPW,
    energyplus_idd,
    require_energyplus_root,
    resolved_energyplus_version,
)


def collect_all_idf_files(root_folder):
    idf_files = []

    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(".idf"):
                idf_files.append(os.path.join(root, file))

    return idf_files


def make_eplaunch_options(idf, output_root, ep_version: str):
    idf_name = os.path.splitext(
        os.path.basename(idf.idfname)
    )[0]

    output_folder = os.path.join(
        output_root,
        idf_name
    )

    os.makedirs(output_folder, exist_ok=True)

    return {
        "ep_version": ep_version,
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
    num_parallel=1,
    ep_version: str | None = None,
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

    if ep_version is None:
        ep_version = resolved_energyplus_version(Path(iddfile).parent)

    print(f"Found {len(idf_files)} IDF files")
    print(f"Using ep_version={ep_version}")

    runs = []

    for idf_file in idf_files:
        print(f"Preparing: {idf_file}")

        idf = IDF(idf_file, epwfile)

        runs.append([
            idf,
            make_eplaunch_options(idf, output_root, ep_version)
        ])

    start_time = time.time()

    runIDFs(runs, num_parallel)

    elapsed = time.time() - start_time

    print("Simulation completed")
    print(f"Total time: {elapsed:.2f} s")


if __name__ == "__main__":
    from pathlib import Path

    ep_root = require_energyplus_root()
    ep_version = resolved_energyplus_version(ep_root)
    iddfile = str(energyplus_idd(ep_root))
    epwfile = str(NANJING_EPW)
    idf_root = str(DEMO_READY_IDF_DIR)
    output_root = str(DEMO_RESULT_DIR)

    print(f"EnergyPlus: {ep_root}")
    print(f"IDD:        {iddfile}")
    print(f"EPW:        {epwfile}")
    print(f"IDF root:   {idf_root}")
    print(f"Output:     {output_root}")

    run_energyplus_batch(
        iddfile=iddfile,
        epwfile=epwfile,
        idf_root=idf_root,
        output_root=output_root,
        num_parallel=1,
        ep_version=ep_version,
    )
