"""Stage 2 factorial analysis for the revised Frequency × ISI design.

Inputs are run-level threshold data with columns:
- frequency_hz
- isi_ms
- replication
- threshold_db

Outputs:
- effects summary
- ANOVA table
- coded regression coefficients
- diagnostic plots
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import levene, shapiro, t


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"frequency_hz", "isi_ms", "replication", "threshold_db"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df


def compute_effects(df: pd.DataFrame) -> pd.DataFrame:
    freq_low_mean = df[df["frequency_hz"] == 250]["threshold_db"].mean()
    freq_high_mean = df[df["frequency_hz"] == 1000]["threshold_db"].mean()
    isi_low_mean = df[df["isi_ms"] == 200]["threshold_db"].mean()
    isi_high_mean = df[df["isi_ms"] == 1000]["threshold_db"].mean()

    cell_means = df.groupby(["frequency_hz", "isi_ms"])["threshold_db"].mean().unstack()
    y_11 = cell_means.loc[250, 200]
    y_12 = cell_means.loc[250, 1000]
    y_21 = cell_means.loc[1000, 200]
    y_22 = cell_means.loc[1000, 1000]

    effect_a = freq_high_mean - freq_low_mean
    effect_b = isi_high_mean - isi_low_mean
    effect_ab = 0.5 * ((y_11 + y_22) - (y_12 + y_21))

    n = len(df)
    df_error = n - 4
    mse = (
        (df["threshold_db"] - df.groupby(["frequency_hz", "isi_ms"])["threshold_db"].transform("mean"))
        ** 2
    ).sum() / df_error
    n_per_level = n / 2
    se_effect = 2 * np.sqrt(mse / (2 * n_per_level))
    t_crit = t.ppf(0.975, df_error)
    half_width = t_crit * se_effect

    return pd.DataFrame(
        {
            "effect": ["frequency", "isi", "interaction"],
            "estimate": [effect_a, effect_b, effect_ab],
            "se": [se_effect, se_effect, se_effect],
            "ci_lower": [effect_a - half_width, effect_b - half_width, effect_ab - half_width],
            "ci_upper": [effect_a + half_width, effect_b + half_width, effect_ab + half_width],
        }
    )


def compute_anova(df: pd.DataFrame) -> pd.DataFrame:
    a = df["frequency_hz"].nunique()
    b = df["isi_ms"].nunique()
    r = len(df) // (a * b)
    grand_mean = df["threshold_db"].mean()
    mean_a = df.groupby("frequency_hz")["threshold_db"].mean()
    mean_b = df.groupby("isi_ms")["threshold_db"].mean()
    mean_ab = df.groupby(["frequency_hz", "isi_ms"])["threshold_db"].mean()

    ss_total = ((df["threshold_db"] - grand_mean) ** 2).sum()
    ss_a = b * r * ((mean_a - grand_mean) ** 2).sum()
    ss_b = a * r * ((mean_b - grand_mean) ** 2).sum()
    ss_ab = r * sum(
        (mean_ab.loc[freq, isi] - mean_a[freq] - mean_b[isi] + grand_mean) ** 2
        for freq in sorted(df["frequency_hz"].unique())
        for isi in sorted(df["isi_ms"].unique())
    )
    ss_error = ss_total - ss_a - ss_b - ss_ab

    df_a = a - 1
    df_b = b - 1
    df_ab = (a - 1) * (b - 1)
    df_error = a * b * (r - 1)
    df_total = len(df) - 1

    ms_a = ss_a / df_a
    ms_b = ss_b / df_b
    ms_ab = ss_ab / df_ab
    ms_error = ss_error / df_error

    f_a = ms_a / ms_error
    f_b = ms_b / ms_error
    f_ab = ms_ab / ms_error

    p_a = 1 - stats.f.cdf(f_a, df_a, df_error)
    p_b = 1 - stats.f.cdf(f_b, df_b, df_error)
    p_ab = 1 - stats.f.cdf(f_ab, df_ab, df_error)

    return pd.DataFrame(
        {
            "source": ["frequency", "isi", "interaction", "error", "total"],
            "df": [df_a, df_b, df_ab, df_error, df_total],
            "ss": [ss_a, ss_b, ss_ab, ss_error, ss_total],
            "ms": [ms_a, ms_b, ms_ab, ms_error, np.nan],
            "f": [f_a, f_b, f_ab, np.nan, np.nan],
            "p_value": [p_a, p_b, p_ab, np.nan, np.nan],
        }
    )


def fit_coded_regression(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    work = df.copy()
    work["A"] = np.where(work["frequency_hz"] == 250, -1, 1)
    work["B"] = np.where(work["isi_ms"] == 200, -1, 1)
    work["AB"] = work["A"] * work["B"]

    x = np.column_stack([np.ones(len(work)), work["A"], work["B"], work["AB"]])
    y = work["threshold_db"].to_numpy()
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    fitted = x @ beta
    residuals = y - fitted
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    adj_r2 = 1 - (1 - r2) * (len(y) - 1) / (len(y) - x.shape[1])
    return beta, fitted, residuals, r2, adj_r2


def save_plots(df: pd.DataFrame, fitted: np.ndarray, residuals: np.ndarray, outdir: Path) -> None:
    grand_mean = df["threshold_db"].mean()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    freq_stats = df.groupby("frequency_hz")["threshold_db"].agg(["mean", "std", "count"])
    axes[0, 0].errorbar(
        freq_stats.index.astype(str),
        freq_stats["mean"],
        yerr=1.96 * freq_stats["std"] / np.sqrt(freq_stats["count"]),
        fmt="o-",
        linewidth=2,
        capsize=6,
    )
    axes[0, 0].axhline(grand_mean, linestyle="--", color="gray")
    axes[0, 0].set_title("Main Effect: Frequency")
    axes[0, 0].set_xlabel("Frequency (Hz)")
    axes[0, 0].set_ylabel("JND (dB)")

    isi_stats = df.groupby("isi_ms")["threshold_db"].agg(["mean", "std", "count"])
    axes[0, 1].errorbar(
        isi_stats.index.astype(str),
        isi_stats["mean"],
        yerr=1.96 * isi_stats["std"] / np.sqrt(isi_stats["count"]),
        fmt="s-",
        linewidth=2,
        capsize=6,
        color="orange",
    )
    axes[0, 1].axhline(grand_mean, linestyle="--", color="gray")
    axes[0, 1].set_title("Main Effect: ISI")
    axes[0, 1].set_xlabel("ISI (ms)")
    axes[0, 1].set_ylabel("JND (dB)")

    for freq in sorted(df["frequency_hz"].unique()):
        subset = df[df["frequency_hz"] == freq].groupby("isi_ms")["threshold_db"].mean()
        axes[1, 0].plot(subset.index.astype(str), subset.values, "o-", linewidth=2, label=f"{freq} Hz")
    axes[1, 0].legend()
    axes[1, 0].set_title("Interaction Plot")
    axes[1, 0].set_xlabel("ISI (ms)")
    axes[1, 0].set_ylabel("Mean JND (dB)")

    axes[1, 1].scatter(fitted, residuals, s=60)
    axes[1, 1].axhline(0, linestyle="--", color="black")
    axes[1, 1].set_title("Residual vs Fitted")
    axes[1, 1].set_xlabel("Fitted")
    axes[1, 1].set_ylabel("Residual")

    plt.tight_layout()
    plt.savefig(outdir / "factorial_plots.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    stats.probplot(residuals, dist="norm", plot=ax)
    ax.set_title("Normal Q-Q Plot")
    plt.tight_layout()
    plt.savefig(outdir / "qq_plot.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze revised Stage 2 factorial data")
    parser.add_argument("input_csv", help="Path to cleaned threshold CSV")
    parser.add_argument("--outdir", default="outputs", help="Output directory")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_data(Path(args.input_csv))
    effects = compute_effects(df)
    anova = compute_anova(df)
    beta, fitted, residuals, r2, adj_r2 = fit_coded_regression(df)
    save_plots(df, fitted, residuals, outdir)

    shapiro_p = shapiro(residuals).pvalue
    groups = [g["threshold_db"].to_numpy() for _, g in df.groupby(["frequency_hz", "isi_ms"])]
    levene_p = levene(*groups).pvalue

    coeffs = pd.DataFrame(
        {
            "term": ["b0", "bA", "bB", "bAB"],
            "estimate": beta,
        }
    )
    diagnostics = pd.DataFrame(
        {
            "metric": ["r_squared", "adjusted_r_squared", "shapiro_p", "levene_p"],
            "value": [r2, adj_r2, shapiro_p, levene_p],
        }
    )

    effects.to_csv(outdir / "effects_summary.csv", index=False)
    anova.to_csv(outdir / "anova_table.csv", index=False)
    coeffs.to_csv(outdir / "coded_regression_coefficients.csv", index=False)
    diagnostics.to_csv(outdir / "model_diagnostics.csv", index=False)

    print("Factorial analysis complete")
    print("Effects")
    print(effects.round(4).to_string(index=False))
    print("\nANOVA")
    print(anova.round(4).to_string(index=False))
    print("\nCoded regression coefficients")
    print(coeffs.round(4).to_string(index=False))
    print("\nDiagnostics")
    print(diagnostics.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
