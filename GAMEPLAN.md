If Only is a simulator of past games

Submodules are needed to

1. Read the data in the past
    - get a list of contests for a certain day that I have complete data for
        - contests
        - standings
2. Generate the lineups an algorithm would've made on that day in history
    - to start, only give the algorithm the competiton data
    - in the future, give the algorithm more information that would've been known at
      that point in time
3. Validate the lineups
4. Judge the lineups
5. Calculate returns

TODO:

-   make it so caches are separated by date or something, not sure exactly what the optimization is, but with
    multiprocessing, it's probably best to have them be independent
-   make sure summary shows the correct entry fees when I enter multiple lineups in the same contest
