# Validate lineup submissions

from ifonly.history.contests import Contest
import pandas as pd

MAX_SALARY = 50_000


def is_valid_lineup(lineup: pd.DataFrame, contest: Contest) -> bool:
    # check salary is under the limit
    if lineup.salary.sum() > MAX_SALARY:
        return False

    # check position requirements are met
    if lineup.groupby("roster_slot_id").size().ne(contest.lineup_reqs).any():
        return False

    # check team requirements are met
    if lineup.team.nunique() < 2:
        return False

    # check draftable_ids are as they appear in the contest
    if lineup.index.droplevel().difference(contest.draftables.index).size > 0:
        return False

    # check for unique player IDs
    if not lineup.player_id.is_unique:
        return False

    return True
