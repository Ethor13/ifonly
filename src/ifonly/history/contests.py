import pandas as pd
import datetime as dt
from pathlib import Path
from tqdm import tqdm
from typing import List, Generator
from dataclasses import dataclass

DATA_DIR = Path("data")
CONTESTS_DIR = DATA_DIR / "contests"
STANDINGS_DIR = DATA_DIR / "standings"
DRAFTABLES_DIR = DATA_DIR / "draftables"
DRAFT_GROUPS_DIR = DATA_DIR / "draft-groups"
LINEUP_REQS_DIR = DATA_DIR / "lineup-requirements"
MAX_ENTRIES_DIR = DATA_DIR / "max-entries"
PAYOUTS_DIR = DATA_DIR / "payouts"


@dataclass
class Contest:
    details: pd.DataFrame
    draftables: pd.DataFrame
    lineup_reqs: pd.DataFrame
    max_entries: pd.DataFrame
    payouts: pd.DataFrame
    standings: pd.DataFrame


def get_standings(date: dt.datetime) -> pd.DataFrame:
    # Access historical standings
    standings_date_dir = date.strftime(r"%m-%d-%Y")

    all_standings: List[pd.DataFrame] = []
    for standings_file in (STANDINGS_DIR / standings_date_dir).iterdir():
        contest_id = int(standings_file.stem)
        standings = pd.read_csv(standings_file, index_col="EntryId")
        all_standings.append(standings.assign(contest_id=contest_id))

    return pd.concat(all_standings).set_index("contest_id", append=True).swaplevel()


def get_contests_generator(
    date: dt.datetime,
) -> Generator[pd.DataFrame | pd.Series, int, None]:
    # Access historical contests
    contests_file = date.strftime(r"%m-%d-%Y") + ".csv"
    contests = pd.read_csv(CONTESTS_DIR / contests_file, index_col="contest_id")

    contest_id = yield contests
    while True:
        contest_id = yield contests.loc[contest_id]


def get_draftables_generator(
    date: dt.datetime,
) -> Generator[pd.DataFrame, int, None]:
    # Access historical contests
    draftables_file = date.strftime(r"%m-%d-%Y") + ".csv"
    draftables = pd.read_csv(
        DRAFTABLES_DIR / draftables_file,
        index_col=["draft_group_id", "draftable_id"],
    )

    # At first, yield all the draftables
    draft_group_id = yield draftables
    while True:
        # Then for each following call, yield the draftables pertaining to the specific
        # draft_group_id
        draft_group_id = yield draftables.loc[[draft_group_id]]


def get_lineup_reqs_generator(
    date: dt.datetime,
) -> Generator[pd.Series, int, None]:
    dated_file = date.strftime(r"%m-%d-%Y") + ".csv"

    draft_groups = pd.read_csv(
        DRAFT_GROUPS_DIR / dated_file,
        index_col="draft_group_id",
    )

    lineup_reqs = pd.read_csv(
        LINEUP_REQS_DIR / dated_file,
        index_col=["contest_type_id", "roster_slot_id"],
    )["count"]

    draft_group_id = yield lineup_reqs
    while True:
        contest_type_id = draft_groups.loc[draft_group_id].contest_type_id
        draft_group_id = yield lineup_reqs.loc[contest_type_id]


def get_max_entries_generator(
    date: dt.datetime,
) -> Generator[pd.Series | int, int, None]:
    max_entries_file = date.strftime(r"%m-%d-%Y") + ".csv"
    max_entries = (
        pd.read_csv(MAX_ENTRIES_DIR / max_entries_file, index_col=0)
        .rename(index={0: "contest_id"})
        .entry_max_per_user
    )

    contest_id = yield max_entries
    while True:
        contest_id = yield max_entries.loc[contest_id]


def get_payouts_generator(date: dt.datetime) -> Generator[pd.Series, int, None]:
    payouts_file = date.strftime(r"%m-%d-%Y") + ".csv"
    payouts = pd.read_csv(
        PAYOUTS_DIR / payouts_file,
        index_col=["contest_id", "minPosition", "maxPosition"],
    ).payout

    contest_id = yield payouts
    while True:
        contest_id = yield payouts.loc[contest_id]


def get_contests(date: dt.datetime):
    contests_generator = get_contests_generator(date)
    draftables_generator = get_draftables_generator(date)
    lineup_reqs_generator = get_lineup_reqs_generator(date)
    max_entries_generator = get_max_entries_generator(date)
    payouts_generator = get_payouts_generator(date)

    # ignore the full dataframes yielded by the generators on the first yield
    _ = next(contests_generator)
    _ = next(draftables_generator)
    _ = next(lineup_reqs_generator)
    _ = next(max_entries_generator)
    _ = next(payouts_generator)

    standings = get_standings(date)
    for contest_id, contest_standings in tqdm(standings.groupby(level="contest_id")):
        try:
            contest_details: pd.Series = contests_generator.send(contest_id)  # type: ignore
            yield Contest(
                details=contest_details,
                draftables=draftables_generator.send(contest_details.draft_group_id),
                lineup_reqs=lineup_reqs_generator.send(contest_details.draft_group_id),
                max_entries=max_entries_generator.send(contest_id),  # type: ignore
                payouts=payouts_generator.send(contest_id),  # type: ignore
                standings=contest_standings.dropna(axis=1, how="all"),
            )
        except KeyError:
            # KeyError occurs when we have a contest in the standings, but no
            # information about it
            print(f"Skipping Contest #{contest_id}")
