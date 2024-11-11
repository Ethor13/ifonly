# Generate lineups given information about a contest and an algorithm
from ifonly.lineups.algorithms.algorithm import Algorithm
from ifonly import Contest
import pandas as pd


def run_generation_algorithms(contest: Contest, algorithms: dict[str, Algorithm], parameters: dict) -> pd.DataFrame:
    algorithm_lineups = []
    for name, algorithm in algorithms.items():
        algorithm_parameters = {
            **parameters["algorithms"][name],
            "solver": parameters["solvers"][parameters["algorithms"][name]["solver"]],
        }
        lineups = algorithm.generate_lineups(contest, **algorithm_parameters)
        algorithm_lineups.append(lineups)

    return pd.concat(algorithm_lineups, keys=algorithms, names=["algorithm"])
