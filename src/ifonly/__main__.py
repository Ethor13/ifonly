import datetime as dt
from ifonly.history.contests import get_contests


date = dt.datetime(2024, 1, 21)

for contest in get_contests(date):
    ...  # do something
