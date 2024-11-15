from ifonly.lineups.algorithms import CachedAlgorithm
from ifonly.history.contests import get_contests
from ifonly.lineups.generate import run_generation_algorithms
from ifonly.judge import get_contest_payouts
from ifonly.summarize import summarize_contest, summarize_runs
from ifonly.utils.printer import Printer
from ifonly.lineups import algorithms
import multiprocessing
from queue import Queue
import datetime as dt
import pandas as pd
import os


def backtest_date(date: dt.datetime, print_queue: Queue, parameters: dict) -> None:
    cached_algorithms = {
        CachedAlgorithm(algorithm) for algorithm in algorithms if parameters["algorithms"][algorithm.name]["run"]
    }

    contests_summaries_lst = []
    contests = get_contests(date)
    num_contests: int = next(contests)  # type: ignore
    per_contest_progress = 1 / num_contests

    for contest in contests:
        lineups = run_generation_algorithms(contest, cached_algorithms, parameters)
        payouts = get_contest_payouts(lineups, contest)
        contests_summaries_lst.append(summarize_contest(payouts, contest, parameters["run_id"]))
        print_queue.put((date, per_contest_progress))

    print_queue.put((date, "DONE"))

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


def backtest_sequential(print_queue: Queue, result_queue: Queue, parameters: dict):
    with Printer(print_queue, result_queue, parameters):
        for date in parameters["dates"]:
            backtest_date(date, print_queue, parameters)


def backtest_parallelize(print_queue: Queue, result_queue: Queue, parameters: dict):
    with Printer(print_queue, result_queue, parameters):
        processes = {}
        for date in parameters["dates"]:
            process = multiprocessing.Process(target=backtest_date, args=(date, print_queue, parameters))
            process.start()
            processes[date] = process

            if len(processes) >= parameters["concurrent_threads"]:
                finished_date = result_queue.get()
                del processes[finished_date]

        # Wait for all workers to finish
        for process in processes.values():
            process.join()
