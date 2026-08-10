"""
Shared repository paths and EnergyPlus discovery.

Machine-specific EnergyPlus install is resolved in this order:
  1) environment variable ENERGYPLUS_DIR (recommended)
  2) common default install locations for EnergyPlus 23.1

Repository data paths are always relative to this file's directory.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

ENERGYPLUS_VERSION = os.environ.get("ENERGYPLUS_VERSION", "23-1-0")
ENERGYPLUS_VERSION_DOT = ENERGYPLUS_VERSION.replace("-", ".")


def _infer_version_from_root(root: Path) -> str | None:
    name = root.name
    # EnergyPlusV23-2-0 / EnergyPlus-23-2-0
    for prefix in ("EnergyPlusV", "EnergyPlus-"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return None


def resolved_energyplus_version(root: Path | None = None) -> str:
    if os.environ.get("ENERGYPLUS_VERSION"):
        return os.environ["ENERGYPLUS_VERSION"]
    if root is not None:
        inferred = _infer_version_from_root(root)
        if inferred:
            return inferred
    return ENERGYPLUS_VERSION

INPUT_DIR = REPO_ROOT / "input"
DEMO_DIR = REPO_ROOT / "demo"
READY_IDF_DIR = REPO_ROOT / "ready_idf"

GIS_DIR = INPUT_DIR / "GIS"
PROTOTYPE_DIR = GIS_DIR / "Prototype"
CITYBUILDING_DIR = GIS_DIR / "CityBuilding"
ARCHETYPE_DIR = GIS_DIR / "Archetype2stock"
EPW_DIR = INPUT_DIR / "EPW"
SETTING_DIR = INPUT_DIR / "Setting"

DEMO_READY_IDF_DIR = DEMO_DIR / "ready_idf"
DEMO_RESULT_DIR = DEMO_DIR / "result"
DEMO_SCALEUP_DIR = DEMO_DIR / "scaleup"

NANJING_EPW = EPW_DIR / "NANJING" / "Nanjing_2020.epw"
NANJING_PROTOTYPE_SHP = PROTOTYPE_DIR / "320100NANJINGSHI.shp"
NANJING_CITY_ZIP = CITYBUILDING_DIR / "320100_Nanjing.zip"
NANJING_ARCHETYPE_CSV = ARCHETYPE_DIR / "320100_Nanjing.csv"
NON_GEOMETRY_XLSX = SETTING_DIR / "non_geomtry_data_all.xlsx"
AGE_DATA_DIR = SETTING_DIR / "age_de"


def _candidate_energyplus_roots() -> list[Path]:
    roots: list[Path] = []
    env = os.environ.get("ENERGYPLUS_DIR") or os.environ.get("ENERGYPLUS_ROOT")
    if env:
        roots.append(Path(env))

    # Prefer explicitly configured version, then common nearby installs.
    versions = []
    if os.environ.get("ENERGYPLUS_VERSION"):
        versions.append(os.environ["ENERGYPLUS_VERSION"])
    versions.extend(["23-1-0", "23-2-0", "24-1-0", "24-2-0", "22-2-0"])

    for ver in versions:
        roots.extend(
            [
                Path(rf"C:\EnergyPlusV{ver}"),
                Path(f"/usr/local/EnergyPlus-{ver}"),
                Path.home() / f"EnergyPlusV{ver}",
            ]
        )

    # Any EnergyPlusV* on C:\ (Windows)
    try:
        for p in Path("C:/").glob("EnergyPlusV*"):
            if p.is_dir():
                roots.append(p)
    except OSError:
        pass

    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        key = str(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def find_energyplus_root() -> Path | None:
    for root in _candidate_energyplus_roots():
        if (root / "Energy+.idd").is_file():
            return root
    return None


def require_energyplus_root() -> Path:
    root = find_energyplus_root()
    if root is None:
        raise FileNotFoundError(
            "EnergyPlus 23.1 was not found.\n"
            "Install EnergyPlus 23.1, then either:\n"
            "  - set ENERGYPLUS_DIR to the install folder, e.g.\n"
            "      Windows:  set ENERGYPLUS_DIR=C:\\EnergyPlusV23-1-0\n"
            "      Linux:    export ENERGYPLUS_DIR=/usr/local/EnergyPlus-23-1-0\n"
            "  - or place the install at the default path C:\\EnergyPlusV23-1-0\n"
        )
    return root


def energyplus_idd(root: Path | None = None) -> Path:
    root = root or require_energyplus_root()
    path = root / "Energy+.idd"
    if not path.is_file():
        raise FileNotFoundError(f"Energy+.idd not found under {root}")
    return path


def energyplus_minimal_idf(root: Path | None = None) -> Path:
    root = root or require_energyplus_root()
    path = root / "ExampleFiles" / "Minimal.idf"
    if not path.is_file():
        raise FileNotFoundError(f"ExampleFiles/Minimal.idf not found under {root}")
    return path


def energyplus_version_updater_idd(root: Path | None = None) -> Path:
    """IDD used by geomeppy IDF bootstrap in 1_GIS2IDF.py."""
    root = root or require_energyplus_root()
    ver = resolved_energyplus_version(root)
    path = (
        root
        / "PreProcess"
        / "IDFVersionUpdater"
        / f"V{ver}-Energy+.idd"
    )
    if path.is_file():
        return path
    # Fallback to main IDD if VersionUpdater copy is absent
    return energyplus_idd(root)


def print_environment_report() -> None:
    print(f"REPO_ROOT: {REPO_ROOT}")
    ep = find_energyplus_root()
    if ep is None:
        print("EnergyPlus: NOT FOUND (set ENERGYPLUS_DIR if you need re-simulation)")
    else:
        ver = resolved_energyplus_version(ep)
        print(f"EnergyPlus: {ep}")
        print(f"  version tag: {ver}")
        print(f"  IDD: {energyplus_idd(ep)}")
    print(f"Demo IDFs: {DEMO_READY_IDF_DIR} (exists={DEMO_READY_IDF_DIR.is_dir()})")
    print(f"Demo results: {DEMO_RESULT_DIR} (exists={DEMO_RESULT_DIR.is_dir()})")
    print(f"Nanjing EPW: {NANJING_EPW} (exists={NANJING_EPW.is_file()})")
