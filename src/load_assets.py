# src/load_assets.py

from pathlib import Path
import pandas as pd


def get_project_root() -> Path:
    """Return the project root directory (one level above this file)."""
    return Path(__file__).resolve().parents[1]


def load_assets(csv_name: str = "assets.csv") -> pd.DataFrame:
    """
    Load the asset inventory from data/assets.csv (or another filename).

    Returns a DataFrame with at least:
    - asset_id
    - type
    - latitude
    - longitude
    - capacity_kVA
    - age_years
    - criticality
    """
    root = get_project_root()
    path = root / "data" / csv_name
    if not path.exists():
        raise FileNotFoundError(f"Asset file not found: {path}")

    df = pd.read_csv(path)
    return df
