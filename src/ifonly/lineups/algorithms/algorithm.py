import pandas as pd
from ifonly import Contest
from typing import Any


class Algorithm:
    def __init__(self, name: str):
        self.name = name
        """
        Cache is meant to be used to reduce duplicate computations on similar competitions

        Cache might check to see if a draft_group_id has already been solved for and then pull the relevant results
        instead of calculating them again. Here's a non-exhaustive list of properties to check for cache matches
            1. draft_group_id
            2. max_entries
            3. payouts
        """
        self.cache = self.initialize_cache()

    def initialize_cache(self) -> Any:
        raise NotImplementedError()

    def clear_cache(self) -> None:
        del self.cache
        self.cache = self.initialize_cache()

    def generate_lineups(self, contest: Contest) -> pd.DataFrame:
        raise NotImplementedError()
