from ifonly import Contest
from ifonly.lineups.validate import is_valid_lineup
from ifonly.lineups.algorithms import Algorithm
import pandas as pd
from typing import Optional


class RandomAlgorithm(Algorithm):
    name = "random_sampler"
    cache_type = Optional[None]

    def __init__(self):
        super().__init__(RandomAlgorithm.name)

    @classmethod
    def get_empty_cache(cls) -> "RandomAlgorithm.cache_type":
        return None

    @classmethod
    def generate_lineups(cls, contest: Contest, cache: "RandomAlgorithm.cache_type", **kwargs) -> pd.DataFrame:
        # take a super naive approach at first just to get the ball rolling
        while True:
            lineup_by_roster_slot = []
            for roster_slot_id, count in contest.lineup_reqs.items():
                roster_slot_mask = contest.draftables.roster_slot_id.eq(roster_slot_id)  # type: ignore
                draftables = contest.draftables.loc[roster_slot_mask]
                drafted = draftables.sample(count)
                lineup_by_roster_slot.append(drafted)

            lineup = (
                pd.concat(lineup_by_roster_slot).assign(lineup_num=0).set_index("lineup_num", append=True).swaplevel()
            )

            if is_valid_lineup(lineup, contest):
                return lineup
