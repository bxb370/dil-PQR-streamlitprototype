"""Generate synthetic PQR (Product Quality Report) complaint data.

Outputs to synthetic_data/:
  formulas.csv    - one row per REX formula
  batches.csv     - one row per 10,000 gallon batch produced
  complaints.csv  - one row per complaint ticket

PQR rate is defined as complaints per 10,000 gallons of paint, which equals
complaints divided by the number of batches produced (each batch = 10,000 gal).
"""

from __future__ import annotations

import os
import random
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from reasons import COMMENT_TEMPLATES, REASON_WEIGHTS, REASONS

SEED = 42
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "synthetic_data")

START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)

GALLONS_PER_BATCH = 10_000

PRODUCT_LINES = [
    "Interior Latex",
    "Exterior Latex",
    "Interior Enamel",
    "Exterior Enamel",
    "Primer",
    "Industrial Coating",
    "Stain",
]

SHEENS = ["Flat", "Matte", "Eggshell", "Satin", "Semi-Gloss", "Gloss"]
BASES = ["White", "Deep", "Ultradeep", "Pastel", "Neutral"]
PLANTS = ["CLE", "ATL", "DAL", "PHX", "CHI"]
COLORS = ["Navy", "Barn Red", "Hunter Green", "Charcoal", "Beige", "Sky Blue", "Brick"]
SUBSTRATES = ["drywall", "bare pine trim", "galvanized metal", "cedar siding",
              "concrete block", "previously painted plaster", "MDF trim"]
CHANNELS = ["Company Store", "Dealer", "Big Box", "Direct/Commercial"]
REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]

N_FORMULAS = 40


def make_formulas(rng: random.Random) -> pd.DataFrame:
    rows = []
    for i in range(N_FORMULAS):
        rex = f"REX-{4000 + i * 7}"
        line = rng.choice(PRODUCT_LINES)
        sheen = rng.choice(SHEENS)
        base = rng.choice(BASES)
        rows.append(
            {
                "REX_Number": rex,
                "Product_Name": f"{line} {sheen} {base}",
                "Product_Line": line,
                "Sheen": sheen,
                "Base": base,
                # underlying "true" quality of the formula: complaints per batch
                "TrueRate": round(max(0.05, rng.gauss(0.9, 0.55)), 3),
                "NBatches": rng.randint(25, 400),
            }
        )
    return pd.DataFrame(rows)


def make_batches(formulas: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    rows = []
    span = (END_DATE - START_DATE).days
    for f in formulas.itertuples():
        for b in range(f.NBatches):
            produced = START_DATE + timedelta(days=rng.randint(0, span - 30))
            rows.append(
                {
                    "Batch_Number": f"B{rng.choice(PLANTS)}{produced:%y%m}{rng.randint(1000, 9999)}-{b:03d}",
                    "REX_Number": f.REX_Number,
                    "Plant": rng.choice(PLANTS),
                    "Production_Date": produced,
                    "Gallons": GALLONS_PER_BATCH,
                }
            )
    return pd.DataFrame(rows)


def _reason_distribution(rex_index: int, rng: random.Random) -> np.ndarray:
    """Per-formula reason mix: global weights plus a formula specific skew."""
    base = np.array([REASON_WEIGHTS[r] for r in REASONS], dtype=float)
    noise = np.array([rng.uniform(0.4, 1.8) for _ in REASONS])
    weights = base * noise
    # give each formula one or two "signature" problem categories
    for _ in range(rng.choice([1, 1, 2])):
        weights[rng.randrange(len(REASONS))] *= rng.uniform(3, 8)
    return weights / weights.sum()


def _comment(reason: str, rng: random.Random) -> str:
    template = rng.choice(COMMENT_TEMPLATES[reason])
    return template.format(
        months=rng.randint(2, 18),
        days=rng.randint(2, 21),
        color=rng.choice(COLORS),
        substrate=rng.choice(SUBSTRATES),
        temp=rng.choice([48, 52, 88, 94, 99]),
        sheen=rng.choice(SHEENS),
    )


def make_complaints(formulas: pd.DataFrame, batches: pd.DataFrame,
                    rng: random.Random, np_rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    ticket = 100000
    batches_by_rex = {k: v for k, v in batches.groupby("REX_Number")}

    for idx, f in enumerate(formulas.itertuples()):
        rex_batches = batches_by_rex[f.REX_Number]
        probs = _reason_distribution(idx, rng)
        expected = f.TrueRate * len(rex_batches)
        n_complaints = int(np_rng.poisson(expected))

        # a handful of batches are "bad" and attract a disproportionate share
        bad = set(rex_batches["Batch_Number"].sample(
            max(1, len(rex_batches) // 25), random_state=idx).tolist())

        for _ in range(n_complaints):
            if bad and rng.random() < 0.25:
                batch_no = rng.choice(sorted(bad))
                batch_row = rex_batches.loc[rex_batches["Batch_Number"] == batch_no].iloc[0]
            else:
                batch_row = rex_batches.sample(1, random_state=rng.randrange(1 << 30)).iloc[0]

            produced = batch_row["Production_Date"]
            complaint_date = produced + timedelta(days=int(np_rng.gamma(2.0, 30)) + 5)
            if complaint_date > END_DATE:
                continue

            reason = str(np_rng.choice(REASONS, p=probs))
            hour = int(np.clip(np_rng.normal(13, 3), 6, 20))
            t = datetime(2000, 1, 1, hour, rng.randrange(60), rng.randrange(60)).time()

            ticket += 1
            rows.append(
                {
                    "Ticket_ID": f"PQR-{ticket}",
                    "Date": complaint_date,
                    "Time": t.strftime("%H:%M:%S"),
                    "Comments": _comment(reason, rng),
                    "REX_Number": f.REX_Number,
                    "Batch_Number": batch_row["Batch_Number"],
                    "Reason": reason,
                    "Settlement_Total": round(max(25, rng.lognormvariate(6.1, 0.75)), 2),
                    "Plant": batch_row["Plant"],
                    "Region": rng.choice(REGIONS),
                    "Channel": rng.choice(CHANNELS),
                }
            )

    df = pd.DataFrame(rows).sort_values(["Date", "Time"]).reset_index(drop=True)
    return df


def main() -> None:
    rng = random.Random(SEED)
    np_rng = np.random.default_rng(SEED)

    formulas = make_formulas(rng)
    batches = make_batches(formulas, rng)
    complaints = make_complaints(formulas, batches, rng, np_rng)

    os.makedirs(OUT_DIR, exist_ok=True)
    formulas.drop(columns=["TrueRate", "NBatches"]).to_csv(
        os.path.join(OUT_DIR, "formulas.csv"), index=False)
    batches.to_csv(os.path.join(OUT_DIR, "batches.csv"), index=False)
    complaints.to_csv(os.path.join(OUT_DIR, "complaints.csv"), index=False)

    print(f"formulas:   {len(formulas):>7,}")
    print(f"batches:    {len(batches):>7,}  ({len(batches) * GALLONS_PER_BATCH:,} gallons)")
    print(f"complaints: {len(complaints):>7,}")
    print(f"overall PQR rate: {len(complaints) / len(batches):.3f} per 10,000 gal")
    print(f"written to {OUT_DIR}")


if __name__ == "__main__":
    main()
