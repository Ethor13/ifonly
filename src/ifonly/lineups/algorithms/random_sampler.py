from ifonly import Contest
from ifonly.lineups.validate import is_valid_lineup
from ifonly.lineups.algorithms.algorithm import Algorithm
import pandas as pd


class RandomAlgorithm(Algorithm):
    name = "random_sampler"

    def __init__(self):
        super().__init__(RandomAlgorithm.name)

    def initialize_cache(self) -> None:
        return None

    def generate_lineups(self, contest: Contest, **kwargs) -> pd.DataFrame:
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
