"""
3_ScaleUp.py
------------
Demonstrate city-wide scale-up logic WITHOUT re-running EnergyPlus.

Pipeline:
  1) Parse heating results for the bundled Nanjing demo prototypes (bh=1,2,3)
  2) Map LandNum_Cluster -> bh via input/GIS/Archetype2stock/*.csv
  3) Apply prototype heating EUI (kWh/m2) to CityBuilding stock rows
  4) Write CSV outputs under demo/scaleup/

Entry point: python run_demo.py scaleup
"""
from __future__ import annotations

import zipfile
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

from config import (
    DEMO_RESULT_DIR,
    DEMO_SCALEUP_DIR as OUT_DIR,
    NANJING_ARCHETYPE_CSV,
    NANJING_CITY_ZIP,
    REPO_ROOT,
)

# Demo uses Nanjing prototypes bh 1/2/3 only (bundled EnergyPlus Table.htm).
CITY_CODE = "320100"
CITY_NAME = "Nanjing"
ARCHETYPE_CSV = NANJING_ARCHETYPE_CSV
CITY_ZIP = NANJING_CITY_ZIP
DEMO_BHS = (1, 2, 3)


class _TableHTMLParser(HTMLParser):
    """Minimal HTML table collector (stdlib only; no BeautifulSoup required)."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
            self._in_cell = True

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell and self._row is not None:
            text = "".join(self._cell or []).strip()
            self._row.append(text)
            self._cell = None
            self._in_cell = False
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None

    def handle_data(self, data):
        if self._in_cell and self._cell is not None:
            self._cell.append(data)


def parse_energyplus_table_htm(path: Path) -> dict[str, float]:
    """Extract conditioned floor area and district-heating end-use from Table.htm."""
    parser = _TableHTMLParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))

    conditioned_m2 = None
    heating_district_gj = None

    for table in parser.tables:
        header = table[0]
        # Building area table
        for row in table:
            if row and row[0] == "Net Conditioned Building Area" and len(row) > 1:
                conditioned_m2 = float(row[1].replace(",", ""))
            if row and row[0] == "Total Building Area" and len(row) > 1:
                try:
                    # Prefer conditioned; keep total as fallback
                    if conditioned_m2 is None:
                        conditioned_m2 = float(row[1].replace(",", ""))
                except ValueError:
                    pass

        # End Uses table (Electricity [GJ] ... District Heating [GJ])
        if (
            header
            and header[0] == ""
            and "Electricity [GJ]" in header
            and "District Heating [GJ]" in header
            and "Subcategory" not in header
            and "Space Type" not in header
        ):
            dh_idx = header.index("District Heating [GJ]")
            for row in table:
                if row and row[0] == "Heating":
                    heating_district_gj = float(row[dh_idx].replace(",", ""))
                    break

    if conditioned_m2 is None or heating_district_gj is None:
        raise ValueError(f"Could not parse heating/area from {path}")

    heating_kwh = heating_district_gj * 1e9 / 3.6e6  # GJ -> kWh
    eui_kwh_m2 = heating_kwh / conditioned_m2
    return {
        "conditioned_area_m2": conditioned_m2,
        "heating_district_GJ": heating_district_gj,
        "heating_kWh": heating_kwh,
        "heating_EUI_kWh_m2": eui_kwh_m2,
    }


def load_archetype_mapping(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "archetype_id" not in df.columns:
        df["archetype_id"] = (
            df["LandNum"].astype(int).astype(str)
            + "_"
            + df["Cluster"].astype(float).astype(int).astype(str)
        )
    df["bh"] = df["bh"].astype(int)
    return df


def load_citybuilding_from_zip(zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        # BuildingID can appear in scientific notation if read as float; force Int64.
        df = pd.read_csv(
            zf.open(csv_name),
            dtype={"BuildingID": "string"},
        )
    df["BuildingID"] = (
        pd.to_numeric(df["BuildingID"], errors="coerce").round().astype("Int64")
    )
    df["archetype_id"] = (
        df["LandNum"].astype(int).astype(str)
        + "_"
        + df["Cluster"].astype(float).astype(int).astype(str)
    )
    # Floors: prefer Fnum; if missing/zero, approximate from Height/Fheight.
    fnum = pd.to_numeric(df["Fnum"], errors="coerce").fillna(0)
    fheight = pd.to_numeric(df["Fheight"], errors="coerce").replace(0, pd.NA)
    height = pd.to_numeric(df["Height"], errors="coerce")
    approx = (height / fheight).round()
    floors = fnum.where(fnum > 0, approx)
    floors = pd.to_numeric(floors, errors="coerce").fillna(1).clip(lower=1)
    df["floors"] = floors.astype(int)
    df["floor_area_m2"] = pd.to_numeric(df["Area"], errors="coerce") * df["floors"]
    return df


def collect_demo_prototype_eui(bhs: tuple[int, ...]) -> pd.DataFrame:
    rows = []
    for bh in bhs:
        folder = DEMO_RESULT_DIR / f"320100NANJINGSHI_{bh}"
        table = folder / f"320100NANJINGSHI_{bh}Table.htm"
        metrics = parse_energyplus_table_htm(table)
        rows.append({"bh": bh, "source_table": str(table.relative_to(REPO_ROOT)), **metrics})
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    mapping = load_archetype_mapping(ARCHETYPE_CSV)
    mapping_out = mapping[
        ["bh", "archetype_id", "LandNum", "Cluster", "BuildingID", "Area", "Fnum", "landUseTyp"]
    ].sort_values("bh")
    mapping_path = OUT_DIR / f"{CITY_CODE}_{CITY_NAME}_bh_to_archetype_id.csv"
    mapping_out.to_csv(mapping_path, index=False, encoding="utf-8-sig")

    eui = collect_demo_prototype_eui(DEMO_BHS)
    eui = eui.merge(
        mapping_out[["bh", "archetype_id", "landUseTyp"]],
        on="bh",
        how="left",
    )
    eui_path = OUT_DIR / f"{CITY_CODE}_{CITY_NAME}_demo_prototype_heating_EUI.csv"
    eui.to_csv(eui_path, index=False, encoding="utf-8-sig", float_format="%.6f")

    stock = load_citybuilding_from_zip(CITY_ZIP)
    demo_arch = set(eui["archetype_id"].dropna().astype(str))
    eui_map = eui.set_index("archetype_id")["heating_EUI_kWh_m2"].to_dict()

    scaled = stock[stock["archetype_id"].isin(demo_arch)].copy()
    scaled["bh"] = scaled["archetype_id"].map(
        mapping_out.set_index("archetype_id")["bh"].to_dict()
    )
    scaled["heating_EUI_kWh_m2"] = scaled["archetype_id"].map(eui_map)
    scaled["heating_kWh"] = scaled["heating_EUI_kWh_m2"] * scaled["floor_area_m2"]

    # Building-level sample (first 50 rows) for inspection
    sample_cols = [
        "BuildingID",
        "landUseTyp",
        "Area",
        "floors",
        "floor_area_m2",
        "LandNum",
        "Cluster",
        "archetype_id",
        "bh",
        "heating_EUI_kWh_m2",
        "heating_kWh",
    ]
    sample = scaled[sample_cols].head(50)
    sample_path = OUT_DIR / f"{CITY_CODE}_{CITY_NAME}_scaleup_building_sample.csv"
    sample.to_csv(sample_path, index=False, encoding="utf-8-sig", float_format="%.4f")

    # City aggregate for the demo archetypes only
    agg = (
        scaled.groupby(["archetype_id", "bh", "landUseTyp"], dropna=False)
        .agg(
            n_buildings=("BuildingID", "count"),
            total_floor_area_m2=("floor_area_m2", "sum"),
            total_heating_kWh=("heating_kWh", "sum"),
            mean_EUI_kWh_m2=("heating_EUI_kWh_m2", "mean"),
        )
        .reset_index()
        .sort_values("bh")
    )
    agg_path = OUT_DIR / f"{CITY_CODE}_{CITY_NAME}_scaleup_aggregate_demo_archetypes.csv"
    agg.to_csv(agg_path, index=False, encoding="utf-8-sig", float_format="%.4f")

    print("Scale-up demo complete (Nanjing bh=1,2,3 only).")
    print(f"  Mapping rows:     {len(mapping_out)} -> {mapping_path}")
    print(f"  Prototype EUI:    {len(eui)} -> {eui_path}")
    print(f"  Stock matched:    {len(scaled)} buildings")
    print(f"  Building sample:  {len(sample)} -> {sample_path}")
    print(f"  Aggregate table:  {len(agg)} -> {agg_path}")
    print(
        "Note: demo uses Nanjing bh=1,2,3 only; "
        "full prototype sets for each megacity are under ready_idf/."
    )


if __name__ == "__main__":
    main()
