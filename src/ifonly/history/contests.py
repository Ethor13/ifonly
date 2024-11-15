import pandas as pd
import datetime as dt
from pathlib import Path
from typing import Generator
from ifonly import Contest
from ifonly.utils.matcher import approximate_match
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(filename="ifonly.log", level=logging.INFO)

DATA_DIR = Path("D:/draft-kings-db")
COMPETITIONS_DIR = DATA_DIR / "competitions"
CONTESTS_DIR = DATA_DIR / "contests"
STANDINGS_DIR = DATA_DIR / "standings"
BOX_SCORES_DIR = DATA_DIR / "box-scores"
DRAFTABLES_DIR = DATA_DIR / "draftables"
DRAFT_GROUPS_DIR = DATA_DIR / "draft-groups"
DRAFT_GROUP_GAMES_DIR = DATA_DIR / "draft-group-games"
LINEUP_REQS_DIR = DATA_DIR / "lineup-requirements"
MAX_ENTRIES_DIR = DATA_DIR / "max-entries"
PAYOUTS_DIR = DATA_DIR / "payouts"
PROJECTIONS_DIR = DATA_DIR / "projections"

TEAM_MAPPINGS = {
    "BRK": "BKN",
    "PHO": "PHX",
    "SA": "SAS",
    "CHO": "CHA",
    "NO": "NOP",
    "NY": "NYK",
    "GS": "GSW",
}


def read_standings(date: dt.datetime) -> pd.DataFrame:
    # Access historical standings
    # standings_date_dir = date.strftime(r"%m-%d-%Y")

    # all_standings: List[pd.DataFrame] = []
    # for standings_file in (STANDINGS_DIR / standings_date_dir).iterdir():
    #     contest_id = int(standings_file.stem)
    #     standings = pd.read_csv(standings_file, index_col="EntryId")
    #     all_standings.append(standings.assign(contest_id=contest_id))

    # return pd.concat(all_standings).set_index("contest_id", append=True).swaplevel()
    standings_file = date.strftime(r"%m-%d-%Y") + ".csv"
    standings = pd.read_csv(STANDINGS_DIR / standings_file, index_col=["contest_id", "EntryId"])
    return standings


def read_contests_details(date: dt.datetime) -> pd.DataFrame:
    # Access historical contests
    contest_details_file = date.strftime(r"%m-%d-%Y") + ".csv"

    return pd.read_csv(CONTESTS_DIR / contest_details_file, index_col="contest_id", parse_dates=["starts_at"])


def read_draftables(date: dt.datetime) -> pd.DataFrame:
    # Access historical contests
    draftables_file = date.strftime(r"%m-%d-%Y") + ".csv"

    return pd.read_csv(
        DRAFTABLES_DIR / draftables_file,
        index_col=["draft_group_id", "draftable_id"],
    )


def read_competitions(date: dt.datetime) -> pd.DataFrame:
    competitions_file = date.strftime(r"%m-%d-%Y") + ".csv"

    return pd.read_csv(
        COMPETITIONS_DIR / competitions_file,
        index_col="competition_id",
        parse_dates=["starts_at"],
    )


def read_draft_groups(date: dt.datetime) -> pd.DataFrame:
    draft_groups_file = date.strftime(r"%m-%d-%Y") + ".csv"

    return pd.read_csv(
        DRAFT_GROUPS_DIR / draft_groups_file,
        index_col="draft_group_id",
    )


def read_draft_group_games(date: dt.datetime) -> pd.DataFrame:
    draft_group_games_file = date.strftime(r"%m-%d-%Y") + ".csv"

    return pd.read_csv(
        DRAFT_GROUP_GAMES_DIR / draft_group_games_file,
        index_col="draft_group_id",
    )


def read_lineup_reqs(date: dt.datetime) -> pd.Series:
    dated_file = date.strftime(r"%m-%d-%Y") + ".csv"

    return pd.read_csv(
        LINEUP_REQS_DIR / dated_file,
        index_col=["contest_type_id", "roster_slot_id"],
    )["count"]


def read_max_entries(date: dt.datetime) -> pd.Series:
    max_entries_file = date.strftime(r"%m-%d-%Y") + ".csv"

    return (
        pd.read_csv(MAX_ENTRIES_DIR / max_entries_file, index_col=0).rename(index={0: "contest_id"}).entry_max_per_user
    )


def read_payouts(date: dt.datetime) -> pd.DataFrame:
    payouts_file = date.strftime(r"%m-%d-%Y") + ".csv"

    return pd.read_csv(
        PAYOUTS_DIR / payouts_file,
        index_col=["contest_id", "minPosition"],
    )


def read_box_scores(date: dt.datetime) -> pd.DataFrame:
    box_scores_file = date.strftime(r"%Y-%m-%d") + ".csv"

    return (
        pd.read_csv(BOX_SCORES_DIR / box_scores_file)
        .assign(team=lambda df: df.team.replace(TEAM_MAPPINGS))
        .set_index(["team", "name"])
    )


def read_projections(date: dt.datetime) -> pd.DataFrame:
    projections_file = date.strftime(r"%Y-%m-%d") + ".csv"

    return (
        pd.read_csv(PROJECTIONS_DIR / projections_file)
        .assign(
            team=lambda df: df.team.replace(TEAM_MAPPINGS),
            opp=lambda df: df.opp.replace(TEAM_MAPPINGS),
        )
        .rename(columns={"player_name": "name"})
        .set_index(["team", "player_id", "name"])
        .sort_index()
    )


def get_contest_projections(draftables: pd.DataFrame, projections: pd.DataFrame, contest_type_id: int) -> pd.Series:
    projection_col = "pts" if contest_type_id == 335 else "fpts"

    contest_projections = pd.merge(
        draftables,
        projections.reset_index(level="player_id"),
        how="left",
        left_on=["team", "name"],
        right_index=True,
        validate="many_to_one",
    ).loc[:, projection_col]

    unmatched_mask = contest_projections.isna()
    unmatched_players = draftables.loc[unmatched_mask]
    contest_projections.loc[unmatched_mask] = approximate_match(
        unmatched_players,
        projections.reset_index(),
        what=projection_col,
        on="name",
        by=["team"],
    ).fillna(0)

    # TODO: double check that "Summer League Showdown Captain Mode" also uses roster_slot_id 476 for CPT or just skip
    # summer league contests

    # add 1.5x multiplier for CPT position in "Showdown Captain Mode" competitions
    cpt_multiplier = 1 + 0.5 * draftables.roster_slot_id.eq(476)
    contest_projections *= cpt_multiplier

    return contest_projections


def get_contests(date: dt.datetime) -> Generator[Contest, None, None]:
    try:
        contests_details = read_contests_details(date)
        competitions = read_competitions(date)
        draftables = read_draftables(date)
        lineup_reqs = read_lineup_reqs(date)
        max_entries = read_max_entries(date)
        payouts = read_payouts(date)
        box_scores = read_box_scores(date)
        draft_groups = read_draft_groups(date)
        draft_group_games = read_draft_group_games(date)
        standings = read_standings(date)
        projections = read_projections(date)
    except FileNotFoundError:
        return logger.info(f"Skipping {date}")

    # first, return number of contests
    yield standings.index.get_level_values("contest_id").nunique()  # type: ignore

    for contest_id, contest_standings in standings.groupby(level="contest_id"):
        try:
            details: pd.Series = contests_details.loc[contest_id]  # type: ignore
            draft_group = draft_groups.loc[details.draft_group_id]
            contest_draftables = draftables.loc[details.draft_group_id]
            contest_type_id = draft_group.contest_type_id

            # don't enter any multi-day competitions because we don't scrape projections for the next day
            contest_competitions = draft_group_games.game_id.loc[[details.draft_group_id]]
            competition_starts = competitions.starts_at.loc[contest_competitions]
            if competition_starts.max().astimezone("EST").date() != date.date():
                continue

            # Manually skip contests that have specific competitions in it
            # 5955158 = UTA vs GSW on 1/17/24 game got postponed
            if contest_competitions.isin({5955158}).any():
                continue

            # TODO: change this to only include contest types 70 and 81 and not WNBA
            if (
                (contest_type_id in {65, 73, 170, 188, 193})  # skip contests that don't have a salary cap
                or (contest_type_id in {112, 113})  # skip the contests that don't run for the entire game
                or (contest_type_id in {137})  # skip the contests that run for an entries series
                or (contest_type_id in {335})  # skip the contests that maximize pts and not fpts
                or ((contest_type_id in {37}) or ("WNBA" in details["name"]))  # skip WNBA games
                or (contest_type_id in {92, 93})  # skip summer league games
                or (contest_type_id in {5})  # classic (old) - for some reason this doesn't work
            ):
                continue

            yield Contest(
                details=details,
                draftables=contest_draftables,
                draft_group=draft_group,
                lineup_reqs=lineup_reqs.loc[draft_group.contest_type_id],
                max_entries=max_entries.loc[contest_id],
                payouts=payouts.loc[contest_id],
                projections=get_contest_projections(contest_draftables, projections, contest_type_id),
                standings=contest_standings,
                box_scores=box_scores,
            )
        except KeyError:
            # KeyError occurs when we have a contest in the standings, but no information about it
            logger.info(f"Skipping Contest #{contest_id}")
