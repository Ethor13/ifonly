from ifonly.lineups.algorithms import CachedAlgorithm
from ifonly import Contest
import pandas as pd


def run_generation_algorithms(
    contest: Contest,
    cached_algorithms: set[CachedAlgorithm],
    parameters: dict,
) -> pd.DataFrame:
    algorithm_lineups = []
    for cached_algorithm in cached_algorithms:
        algorithm_specific_parameters = parameters["algorithms"][cached_algorithm.algorithm.name]

        algorithm_parameters = {
            **algorithm_specific_parameters,
            "solver": parameters["solvers"].get(algorithm_specific_parameters.get("solver", None), None),
        }

        lineups = cached_algorithm.algorithm.generate_lineups(contest, cached_algorithm.cache, **algorithm_parameters)
        algorithm_lineups.append(lineups)

    return pd.concat(algorithm_lineups, keys=cached_algorithms, names=["algorithm"])
