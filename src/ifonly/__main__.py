from ifonly.history.contests import get_contests
from ifonly.lineups.generate import run_generation_algorithms
from ifonly.judge import get_contest_payouts
from ifonly.summarize import summarize_contest, summarize_runs
from ifonly.lineups import algorithms
import datetime as dt
import pandas as pd
import tomllib
import os

with open("ifonly.toml", "rb") as f:
    parameters = tomllib.load(f)


run_id = int(dt.datetime.now().timestamp())
dates = pd.date_range(parameters["start_date"], parameters["end_date"])
algorithms = {name: algorithm for name, algorithm in algorithms.items() if parameters["algorithms"][name]["run"]}


def backtest_date(date: dt.datetime):
    contests_summaries_lst = []
    for contest in get_contests(date):
        lineups = run_generation_algorithms(contest, algorithms, parameters)
        payouts = get_contest_payouts(lineups, contest)
        contests_summaries_lst.append(summarize_contest(payouts, contest, run_id))

    if contests_summaries_lst:
        contest_summaries = pd.concat(contests_summaries_lst, ignore_index=True)

        results_file = f"results/detailed/{date.strftime(r"%Y-%m-%d")}.csv"

        contest_summaries.to_csv(
            results_file,
            mode="a",
            index=False,
            header=not os.path.exists(results_file),
        )

        summarize_runs(contest_summaries, date)

    (algorithm.clear_cache() for _, algorithm in algorithms)


for date in dates:
    backtest_date(date)
