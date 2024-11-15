import pandas as pd
import difflib
from typing import List, Callable
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(filename="matcher.log", level=logging.INFO, filemode="w")

MATCH_CUTOFF = 0.7


def get_matcher(name: str) -> Callable[[str], float]:
    def matcher(other: str) -> float:
        return difflib.SequenceMatcher(None, name, other).ratio()

    return matcher


def approximate_match(source: pd.DataFrame, lookup: pd.DataFrame, what: str, on: str, by: List[str]) -> pd.Series:
    """
    For each row in `source`, finds the row in `lookup` that matches the row on all columns listed in `by`, and most
    closely resembles the `on` column in `source`, and returns the value in the `what` column

    Parameters
    ----------
    source: pd.DataFrame
        The source data
    lookup: pd.DataFrame
        The lookup data that doesn't have an exact match for the `on` column in `lookup`
    what: str
        The column we're interested in getting after finding the best match
    on: str
        The column to match approximately between `source` and `lookup`
    by: List[str]
        The columns to match exactly between `source` and `lookup`

    Returns
    -------
    best_guesses: pd.Series
        A series containing the best guesses at the matching rows between `source` and `lookup`
    """
    what_best_guesses = []
    for _, row in source.iterrows():
        # Filter lookup down to only the rows that match each attribute of `row` in `by`
        mask = (lookup.filter(by) == row.filter(by)).all(axis=1)
        lookup_matches = lookup.loc[mask]

        # make a function that scores how similar a str is to the `on` attribute of `row`
        matcher = get_matcher(row.loc[on])
        # score each of the remaining entries in lookups
        match_ratios = lookup_matches.get(on).map(matcher)  # type: ignore

        # get the `what` value of the closest match in `lookup_matches`
        try:
            if match_ratios.max() >= MATCH_CUTOFF:
                what_best_guess = lookup_matches.iloc[match_ratios.argmax()].get(what)
                logger.info(f"Matched {row.get("name")} with {lookup_matches.iloc[match_ratios.argmax()].get("name")}")
            else:
                what_best_guess = None
                logger.info(
                    f"Did not match match {row.get("name")} - Closest was {lookup_matches.iloc[match_ratios.argmax()].get("name")}"
                )
        except:
            breakpoint()
            exit(1)

        what_best_guesses.append(what_best_guess if match_ratios.max() >= MATCH_CUTOFF else None)

    return pd.Series(what_best_guesses, index=source.index, dtype=lookup.dtypes.get(what))  # type: ignore
