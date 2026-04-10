"""Data preparation and QC utilities for the revised Stage 2 design.

This script is for exported experiment or sheet data using the updated schema:
- Frequency (Hz)
- ISI (ms)
- Threshold (dB)
- Total/usable reversals

It standardizes column names, validates schema, computes run-level QC flags,
and writes cleaned tables that feed the factorial analysis script or notebook.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "frequency_hz",
    "isi_ms",
    "replication",
    "threshold_db",
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for column in df.columns:
        clean = (
            column.strip()
            .lower()
            .replace("(", "")
            .replace(")", "")
            .replace("-", "_")
            .replace(" ", "_")
        )
        renamed[column] = clean

    df = df.rename(columns=renamed)

    alias_map = {
        "frequency_hz": ["frequency_hz", "frequency"],
        "isi_ms": ["isi_ms", "isi"],
        "replication": ["replication"],
        "threshold_db": ["threshold_db", "threshold", "calculated_threshold_db"],
        "total_trials": ["total_trials"],
        "total_reversals": ["total_reversals"],
        "discarded_reversals": ["discarded_reversals"],
        "usable_reversals": ["usable_reversals", "fine_reversals"],
        "participant_id": ["participant_id"],
        "participant_name": ["participant_name"],
        "block_number": ["block_number"],
        "raw_trial_data": ["raw_trial_data", "trialhistory"],
    }

    for target, aliases in alias_map.items():
        for alias in aliases:
            if alias in df.columns and target not in df.columns:
                df = df.rename(columns={alias: target})
                break

    return df


def validate_schema(df: pd.DataFrame) -> list[str]:
    return sorted(REQUIRED_COLUMNS - set(df.columns))


def add_qc_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "usable_reversals" not in df.columns:
        df["usable_reversals"] = np.nan
    if "total_reversals" not in df.columns:
        df["total_reversals"] = np.nan
    if "discarded_reversals" not in df.columns:
        df["discarded_reversals"] = 2
    if "total_trials" not in df.columns:
        df["total_trials"] = np.nan

    df["flag_missing_threshold"] = df["threshold_db"].isna()
    df["flag_invalid_frequency"] = ~df["frequency_hz"].isin([250, 1000])
    df["flag_invalid_isi"] = ~df["isi_ms"].isin([200, 1000])
    df["flag_low_usable_reversals"] = df["usable_reversals"].fillna(0) < 2
    df["flag_threshold_outlier"] = (df["threshold_db"] < 0.5) | (df["threshold_db"] > 6.0)
    df["flag_trial_count_high"] = df["total_trials"].fillna(0) > 40

    qc_cols = [
        "flag_missing_threshold",
        "flag_invalid_frequency",
        "flag_invalid_isi",
        "flag_low_usable_reversals",
        "flag_threshold_outlier",
        "flag_trial_count_high",
    ]
    df["failed_run"] = df[qc_cols].any(axis=1)
    return df


def summarize(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    condition_summary = (
        df.groupby(["frequency_hz", "isi_ms"])["threshold_db"]
        .agg(["count", "mean", "std", "min", "max"])
        .reset_index()
        .rename(columns={"count": "n", "mean": "mean_jnd_db", "std": "sd_jnd_db"})
    )

    qc_summary = pd.DataFrame(
        {
            "metric": [
                "n_runs",
                "failed_runs",
                "missing_threshold",
                "invalid_frequency",
                "invalid_isi",
                "low_usable_reversals",
                "threshold_outlier",
                "trial_count_high",
            ],
            "value": [
                len(df),
                int(df["failed_run"].sum()),
                int(df["flag_missing_threshold"].sum()),
                int(df["flag_invalid_frequency"].sum()),
                int(df["flag_invalid_isi"].sum()),
                int(df["flag_low_usable_reversals"].sum()),
                int(df["flag_threshold_outlier"].sum()),
                int(df["flag_trial_count_high"].sum()),
            ],
        }
    )
    return condition_summary, qc_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare revised Stage 2 JND data")
    parser.add_argument("input_csv", help="Path to raw/exported CSV")
    parser.add_argument("--outdir", default="outputs", help="Directory for cleaned outputs")
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    df = normalize_columns(df)

    missing = validate_schema(df)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = add_qc_flags(df)
    condition_summary, qc_summary = summarize(df)

    cleaned_path = outdir / "cleaned_threshold_data.csv"
    flags_path = outdir / "cleaned_threshold_data_with_qc.csv"
    cond_path = outdir / "condition_summary.csv"
    qc_path = outdir / "qc_summary.csv"

    keep_cols = [
        col
        for col in [
            "participant_id",
            "participant_name",
            "block_number",
            "frequency_hz",
            "isi_ms",
            "replication",
            "threshold_db",
            "total_trials",
            "total_reversals",
            "discarded_reversals",
            "usable_reversals",
            "failed_run",
        ]
        if col in df.columns
    ]

    df[keep_cols].to_csv(cleaned_path, index=False)
    df.to_csv(flags_path, index=False)
    condition_summary.to_csv(cond_path, index=False)
    qc_summary.to_csv(qc_path, index=False)

    print("Prepared data successfully")
    print(f"Input: {input_path}")
    print(f"Cleaned data: {cleaned_path}")
    print(f"Condition summary: {cond_path}")
    print(f"QC summary: {qc_path}")
    print(qc_summary.to_string(index=False))


if __name__ == "__main__":
    main()
