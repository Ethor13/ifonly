from ifonly.lineups.algorithms import Algorithm
import sys
import glob
import os
import inspect
import importlib


def import_all_from_directory(directory):
    # Add directory to sys.path so it can be imported
    sys.path.insert(0, directory)

    # Import all modules in the directory
    algorithms: set[Algorithm] = set()
    for filepath in glob.glob(os.path.join(directory, "*.py")):
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        if module_name == "__init__":
            continue

        module = importlib.import_module(module_name)

        algorithm = [
            algo_cls
            for _, algo_cls in inspect.getmembers(module, inspect.isclass)
            if (algo_cls.__module__ == module_name) and issubclass(algo_cls, Algorithm)
        ]

        if len(algorithm) != 1:
            raise RuntimeError("Expected exactly one Algorithm to be defined in each file")

        algorithms.add(algorithm[0])  # type: ignore

    # Remove directory from sys.path to avoid side effects
    sys.path.pop(0)

    return algorithms


algorithms = import_all_from_directory("src/ifonly/lineups/algorithms")
