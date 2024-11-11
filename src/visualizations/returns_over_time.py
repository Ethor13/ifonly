import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
from pathlib import Path

ENTRY_MAX = float("inf")
ENTRY_FEE_MAX = 5
# ENTRY_FEE_MAX = float("inf")


def thousands_formatter(x, pos):
    return f"${int(x / 1000):,}K"


detailed_results_files = list(Path("results/detailed").iterdir())

detailed_results = (
    pd.concat(
        [pd.read_csv(f, index_col=["run_id", "contest_id"]) for f in detailed_results_files],
        keys=map(lambda f: pd.to_datetime(f.stem), detailed_results_files),
        names=["date"],
    )
    .swaplevel(0, 1)
    .sort_index()
)

RUN_ID = detailed_results.index.get_level_values("run_id").max()
run_results = detailed_results.loc[RUN_ID]

small_entry_fee_results = run_results.loc[lambda df: df.entry_fee.le(ENTRY_FEE_MAX)]
small_entry_fee_results = small_entry_fee_results.loc[lambda df: df.entries.le(ENTRY_MAX)]

results_by_date = small_entry_fee_results.groupby(level="date").sum()


def payouts_vs_entry_fees():
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(results_by_date.index, results_by_date.payout.cumsum(), c="green", label="Payouts")
    ax.plot(results_by_date.index, results_by_date.entry_fee.cumsum(), c="red", label="Entry Fees")

    ax.set_xlabel("Date")

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(thousands_formatter))
    ax.set_ylabel("Dollars")

    ax.set_title(f"Entry Fees and Payouts over Time (Run ID: {RUN_ID})")
    ax.legend()

    plt.tight_layout()
    plt.show()


def profit():
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(results_by_date.index, results_by_date.payout.cumsum() - results_by_date.entry_fee.cumsum(), label="Profit")

    ax.set_xlabel("Date")

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(thousands_formatter))
    ax.set_ylabel("Dollars")
    ax.hlines([0], [results_by_date.index.min()], [results_by_date.index.max()], colors=["black"])

    ax.set_title(f"Profit over Time (Run ID: {RUN_ID})")
    ax.legend()

    plt.tight_layout()
    plt.show()


payouts_vs_entry_fees()
profit()
