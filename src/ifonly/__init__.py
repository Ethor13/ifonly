import pandas as pd
from dataclasses import dataclass


@dataclass
class Contest:
    details: pd.Series
    draftables: pd.DataFrame
    draft_group: pd.Series
    lineup_reqs: pd.Series
    max_entries: int
    payouts: pd.DataFrame
    projections: pd.Series
    standings: pd.DataFrame  # TODO: hide standings so lineup generator can't see
    box_scores: pd.DataFrame  # TODO: hide box scores so lineup generator can't see
