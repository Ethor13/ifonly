# Judge generated lineups against historical results

import pandas as pd
from ifonly import Contest
from ifonly.utils.matcher import approximate_match


def score_lineups(lineups: pd.DataFrame, box_scores: pd.DataFrame, contest_type_id: int) -> pd.Series:
    projection_col = "pts" if contest_type_id == 335 else "fpts"

    player_pts = pd.merge(
        lineups,
        box_scores,
        left_on=["team", "name"],
        right_index=True,
        how="left",
        validate="many_to_one",
    ).loc[:, projection_col]

    unmatched_mask = player_pts.isna()
    unmatched_players = lineups.loc[unmatched_mask]
    player_pts.loc[unmatched_mask] = approximate_match(
        unmatched_players,
        box_scores.reset_index(),
        what=projection_col,
        on="name",
        by=["team"],
    ).fillna(0)

    # TODO: double check that "Summer League Showdown Captain Mode" also uses roster_slot_id 476 for CPT or just skip
    # summer league contests

    # add 1.5x multiplier for CPT position in "Showdown Captain Mode" competitions
    cpt_multiplier = 1 + 0.5 * lineups.roster_slot_id.eq(476)
    player_pts *= cpt_multiplier

    # TODO: remove once i'm sure approximate match works as intended
    if player_pts.isna().any():
        breakpoint()

    return player_pts.groupby(level=["algorithm", "lineup_num"]).sum()


def rank_lineups(lineups: pd.DataFrame, contest: Contest) -> pd.DataFrame:
    lineup_scores = score_lineups(lineups, contest.box_scores, contest.draft_group.contest_type_id)

    standings = contest.standings.Points
    if standings.is_monotonic_decreasing:
        standings = standings.iloc[::-1]
    elif not standings.is_monotonic_increasing:
        standings = standings.sort_values(ascending=True)

    ranks = pd.Series(standings.searchsorted(lineup_scores), index=lineup_scores.index, name="rank")

    places = (standings.size + 1) - ranks

    return lineup_scores.to_frame().assign(place=places)


def get_contest_payouts(lineups: pd.DataFrame, contest: Contest) -> pd.DataFrame:
    places = rank_lineups(lineups, contest)

    # if we got a payout it would be here, if we didn't get a payoff, we need to check
    # that the max_position is less than what we ranked
    potential_payouts = pd.merge_asof(
        places.sort_values("place"),
        contest.payouts.sort_index(),
        left_on="place",
        right_index=True,
    )

    actual_payouts = potential_payouts.payout.where(potential_payouts.place <= potential_payouts.maxPosition, 0)

    return places.assign(payout=actual_payouts)
