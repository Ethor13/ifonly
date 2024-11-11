from ifonly import Contest
import pandas as pd
import datetime as dt
import os

# TODO: add projected pts
# contest.projections.loc[lineup.index.get_level_values("draftable_id")].sum()


def summarize_contest(payouts: pd.DataFrame, contest: Contest, run_id: int) -> pd.DataFrame:
    algorithm_entries = payouts.groupby(level="algorithm").transform("size") + len(contest.standings)
    return (
        payouts.reset_index()
        .assign(
            run_id=run_id,
            contest_id=contest.details.name,
            contest_type_id=contest.draft_group.contest_type_id,
            entries=algorithm_entries.values,
            entry_fee=contest.details.entry_fee,
            prize_pool=contest.payouts.payout.sum(),
        )
        .filter(
            [
                "run_id",
                "contest_id",
                "contest_type_id",
                "entries",
                "entry_fee",
                "prize_pool",
                "algorithm",
                "lineup_num",
                "fpts",
                "place",
                "payout",
            ]
        )
    )


def summarize_runs(contest_summaries: pd.DataFrame, date: dt.datetime) -> None:

    run_summary = (
        contest_summaries.assign(percentile=lambda df: (df.entries - df.place) / (df.entries - 1))
        .groupby(["run_id", "algorithm", "contest_type_id"])
        .agg(
            contests=("contest_id", "nunique"),
            lineups=("contest_id", "count"),
            entry_fees=("entry_fee", "sum"),
            payouts=("payout", "sum"),
            percentile=("percentile", "mean"),
        )
    )

    run_summary.insert(0, "date", date)

    summary_file = "results/summary.csv"

    run_summary.to_csv(
        summary_file,
        mode="a",
        header=not os.path.exists(summary_file),
        float_format="%.4f",
    )
