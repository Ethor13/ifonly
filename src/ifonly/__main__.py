from ifonly.backtest import backtest_parallelize, backtest_sequential
import datetime as dt
import pandas as pd
import tomllib
import multiprocessing

with open("ifonly.toml", "rb") as f:
    parameters = tomllib.load(f)

parameters["run_id"] = int(dt.datetime.now().timestamp())
parameters["dates"] = pd.date_range(parameters["start_date"], parameters["end_date"])

if __name__ == "__main__":
    with multiprocessing.Manager() as manager:
        backtest_func = backtest_parallelize if parameters["parallelize"] else backtest_sequential
        backtest_func(manager.Queue(), manager.Queue(), parameters)
