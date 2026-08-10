"""
Simple entry point for reproducing the three-megacity workflow.

Examples
--------
  python run_demo.py check      # show paths / EnergyPlus detection
  python run_demo.py scaleup    # no EnergyPlus required
  python run_demo.py simulate   # needs EnergyPlus 23.1
  python run_demo.py idf        # needs EnergyPlus 23.1 + GIS libs
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def _run_script(name: str) -> int:
    script = REPO_ROOT / name
    print(f">>> python {script.name}")
    return subprocess.call([sys.executable, str(script)], cwd=str(REPO_ROOT))


def cmd_check(_: argparse.Namespace) -> int:
    from config import print_environment_report

    print_environment_report()
    return 0


def cmd_scaleup(_: argparse.Namespace) -> int:
    return _run_script("3_ScaleUp.py")


def cmd_simulate(_: argparse.Namespace) -> int:
    return _run_script("2_BatchSimulation.py")


def cmd_idf(_: argparse.Namespace) -> int:
    return _run_script("1_GIS2IDF.py")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce the Urban Heating Electrification demo workflow."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Print repo paths and EnergyPlus detection")
    p_check.set_defaults(func=cmd_check)

    p_scale = sub.add_parser(
        "scaleup",
        help="Run archetype-to-stock scale-up (pandas only; no EnergyPlus)",
    )
    p_scale.set_defaults(func=cmd_scaleup)

    p_sim = sub.add_parser(
        "simulate",
        help="Re-run Nanjing demo EnergyPlus cases (needs EnergyPlus 23.1)",
    )
    p_sim.set_defaults(func=cmd_simulate)

    p_idf = sub.add_parser(
        "idf",
        help="Regenerate Nanjing prototype IDFs from Prototype GIS (needs EnergyPlus 23.1)",
    )
    p_idf.set_defaults(func=cmd_idf)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
