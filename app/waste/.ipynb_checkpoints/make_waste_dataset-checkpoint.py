import os
import numpy as np
import pandas as pd


# =======================
# CONFIG
# =======================
FACILITIES_PATH_CANDIDATES = [
    "data/processed/facil.csv",      # your commuting facilities (100,200) if you saved it there
    "data/facil.csv",
    "data/processed/facilities.csv", # ASHRAE facilities (0..1448)
]

PRODUCTION_PATH_CANDIDATES = [
    "data/processed/production.csv",
]

OUT_WASTE_PATH = "data/processed/waste.csv"
OUT_SUMMARY_PATH = "data/processed/waste_summary.csv"

RANDOM_SEED = 42

# If False: we drop recycled/reused from the final waste.csv (as your supervisor suggested "no need to go through")
KEEP_RECYCLED = True

# Materials you want to track
MATERIAL_TYPES = ["silk", "cotton", "polyester", "paper", "plastic", "metal"]

# Treatment types (what happens to waste)
TREATMENTS = ["landfill", "incineration", "recycled", "reused"]

# Probabilities must sum to 1
TREATMENT_PROBS = [0.45, 0.25, 0.20, 0.10]

# If production dates exist, we use them; otherwise we generate the last N days.
FALLBACK_N_DAYS = 30

# Expected waste rate bounds (as a fraction of production quantity, if production exists)
WASTE_RATE_MIN = 0.01   # 1%
WASTE_RATE_MAX = 0.08   # 8%


# =======================
# HELPERS
# =======================
def first_existing_path(candidates: list[str]) -> str | None:
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


# =======================
# MAIN
# =======================
def main():
    np.random.seed(RANDOM_SEED)

    facilities_path = first_existing_path(FACILITIES_PATH_CANDIDATES)
    if facilities_path is None:
        raise FileNotFoundError(
            f"Could not find facilities file. Tried: {FACILITIES_PATH_CANDIDATES}"
        )

    facilities = pd.read_csv(facilities_path)
    facilities.columns = facilities.columns.str.strip()

    if "facility_id" not in facilities.columns:
        raise ValueError(f"'facility_id' column not found in {facilities_path}. Found: {list(facilities.columns)}")

    facilities["facility_id"] = pd.to_numeric(facilities["facility_id"], errors="coerce")
    facilities = facilities.dropna(subset=["facility_id"]).copy()
    facilities["facility_id"] = facilities["facility_id"].astype(int)

    production_path = first_existing_path(PRODUCTION_PATH_CANDIDATES)
    production = None
    production_dates = None

    if production_path is not None:
        production = pd.read_csv(production_path)
        production.columns = production.columns.str.strip()

        # production_date in your processed production.csv (we created it earlier)
        if "production_date" in production.columns:
            production["production_date"] = pd.to_datetime(production["production_date"], errors="coerce").dt.date
            production_dates = production["production_date"].dropna().unique()

    # Decide the date set
    if production_dates is not None and len(production_dates) > 0:
        dates = sorted(production_dates)
    else:
        today = pd.Timestamp.today().normalize().date()
        dates = [(today - pd.Timedelta(days=i)).date() for i in range(FALLBACK_N_DAYS)]
        dates = sorted(dates)

    # Build waste rows
    rows = []
    waste_id = 1

    facility_ids = facilities["facility_id"].unique().tolist()

    # If production exists but has no facility_id, we assign jobs randomly to facilities (synthetic link)
    # and then generate waste per job proportional to quantity_produced.
    if production is not None and "quantity_produced" in production.columns and "production_date" in production.columns:
        # Create a synthetic facility link if missing
        if "facility_id" not in production.columns:
            production = production.copy()
            production["facility_id"] = np.random.choice(facility_ids, size=len(production), replace=True)

        production["production_date"] = pd.to_datetime(production["production_date"], errors="coerce").dt.date
        production = production.dropna(subset=["facility_id", "production_date", "quantity_produced"]).copy()

        for _, job in production.iterrows():
            facility_id = int(job["facility_id"])
            date = job["production_date"]

            # choose 1 material per job (simplified)
            material = np.random.choice(MATERIAL_TYPES)

            # waste quantity proportional to production quantity (bounded by waste rate)
            qty_prod = float(job["quantity_produced"])
            waste_rate = np.random.uniform(WASTE_RATE_MIN, WASTE_RATE_MAX)
            qty_waste = max(0.0, qty_prod * waste_rate)

            treatment = np.random.choice(TREATMENTS, p=TREATMENT_PROBS)
            is_recycled = treatment in ("recycled", "reused")

            rows.append({
                "waste_id": waste_id,
                "facility_id": facility_id,
                "date": date,
                "material_type": material,
                "quantity_kg": round(qty_waste, 3),
                "treatment": treatment,
                "is_recycled": is_recycled,
                "source": "production_job"
            })
            waste_id += 1

    else:
        # No production linkage: generate daily waste events per facility
        for facility_id in facility_ids:
            for date in dates:
                # some days may have no waste events
                if np.random.rand() < 0.35:
                    continue

                # number of waste lines for that day
                n_lines = np.random.randint(1, 4)

                for _ in range(n_lines):
                    material = np.random.choice(MATERIAL_TYPES)
                    treatment = np.random.choice(TREATMENTS, p=TREATMENT_PROBS)
                    is_recycled = treatment in ("recycled", "reused")

                    # random quantity in kg (small/medium)
                    qty_waste = float(np.random.lognormal(mean=1.2, sigma=0.5))  # ~ 2kg..20kg typical

                    rows.append({
                        "waste_id": waste_id,
                        "facility_id": int(facility_id),
                        "date": date,
                        "material_type": material,
                        "quantity_kg": round(qty_waste, 3),
                        "treatment": treatment,
                        "is_recycled": is_recycled,
                        "source": "daily_estimate"
                    })
                    waste_id += 1

    waste_df = pd.DataFrame(rows)

    if waste_df.empty:
        raise RuntimeError("Generated waste_df is empty. Check inputs / config.")

    # Optionally drop recycled/reused
    if not KEEP_RECYCLED:
        waste_df = waste_df[~waste_df["is_recycled"]].copy()

    # Final typing/format
    waste_df["date"] = pd.to_datetime(waste_df["date"], errors="coerce").dt.date
    waste_df = waste_df.dropna(subset=["date"]).copy()

    # Save
    ensure_dir(OUT_WASTE_PATH)
    waste_df.to_csv(OUT_WASTE_PATH, index=False)

    # Quick summary for validation
    summary = (waste_df
               .groupby(["facility_id", "date", "treatment"], as_index=False)
               .agg(total_waste_kg=("quantity_kg", "sum"),
                    n_records=("waste_id", "count")))

    summary.to_csv(OUT_SUMMARY_PATH, index=False)

    print("✅ Generated:", OUT_WASTE_PATH, "rows=", len(waste_df))
    print("✅ Generated:", OUT_SUMMARY_PATH, "rows=", len(summary))
    print("Facilities used from:", facilities_path)
    if production_path:
        print("Production used from:", production_path)
    else:
        print("No production file found; generated daily waste estimates.")


if __name__ == "__main__":
    main()