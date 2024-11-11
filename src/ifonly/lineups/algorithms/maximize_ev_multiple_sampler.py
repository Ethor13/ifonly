import pandas as pd
import numpy as np
from ifonly import Contest
from ifonly.lineups.algorithms.algorithm import Algorithm
import pyomo.environ as pyo
from pyomo.core.expr.numeric_expr import LinearExpression
from pyomo.core.base.PyomoModel import ConcreteModel
from pyomo.opt.base.solvers import OptSolver
from collections import defaultdict
from typing import Tuple, List

USE_PERSISTENT_SOLVER = False
PROJECTION_CUTOFF = 5
SALARY = 50_000


class MaximizeEVMultipleSamplerAlgorithm(Algorithm):
    name = "maximize_ev_multiple_sampler"

    def __init__(self):
        super().__init__(MaximizeEVMultipleSamplerAlgorithm.name)

    def initialize_cache(self) -> defaultdict[int, List[pd.DataFrame]]:
        return defaultdict(list)

    def initialize_problem(
        self,
        contest: Contest,
        salary: int,
        projection_cutoff: float,
        solver: dict,
    ) -> Tuple[ConcreteModel, OptSolver]:
        num_to_draft = contest.lineup_reqs.sum()
        num_draftables = len(contest.draftables)
        num_players = contest.draftables.player_id.nunique()
        num_positions = len(contest.lineup_reqs)
        num_competitions = contest.draft_group.games_count
        projections = contest.projections.values
        salaries = contest.draftables.salary.astype("int64")
        # NOTE: I think dividing by gcd will make things run faster, but haven't tested this
        salary_gcd = np.gcd.reduce(salaries)

        model = pyo.ConcreteModel(name=MaximizeEVMultipleSamplerAlgorithm.name)

        # Pyomo Variables
        model.drafted = pyo.Var(range(num_draftables), domain=pyo.Boolean)
        drafted_vars_list = [model.drafted[i] for i in range(num_draftables)]

        # Set Variables to 0 if projected value is < a certain threshold
        for idx, projection in enumerate(projections):
            if projection < projection_cutoff:
                model.drafted[idx].fix(0)  # type: ignore

        # Pyomo Objectives
        drafted_ev = LinearExpression(linear_coefs=projections, linear_vars=drafted_vars_list)
        model.obj = pyo.Objective(expr=drafted_ev, sense=pyo.maximize)

        # Pyomo Constraints
        model.constraints = pyo.ConstraintList()

        # Salary Constraint
        drafted_salaries = LinearExpression(linear_coefs=salaries // salary_gcd, linear_vars=drafted_vars_list)
        model.constraints.add(drafted_salaries <= salary // salary_gcd)

        # Player Constraint
        player_ids = contest.draftables.player_id.astype("category")
        player_matrix = np.zeros((num_draftables, num_players), dtype="int8")
        player_matrix[np.arange(num_draftables), player_ids.cat.codes] = 1
        for col in range(num_players):
            # TODO: test if LinearExpression is faster or just the inequality, since there's only one non-zero entry
            model.constraints.add(
                LinearExpression(linear_coefs=player_matrix[:, col], linear_vars=drafted_vars_list) <= 1
            )

        # Positional Constraint
        roster_slots = contest.draftables.roster_slot_id.astype("category")
        position_matrix = np.zeros((num_draftables, num_positions), dtype="int8")
        position_matrix[np.arange(num_draftables), roster_slots.cat.codes] = 1
        for roster_slot_id in contest.lineup_reqs.index:
            same_position = position_matrix[:, roster_slots.cat.categories.get_loc(roster_slot_id)]
            drafted_positions = LinearExpression(linear_coefs=same_position, linear_vars=drafted_vars_list)
            model.constraints.add(drafted_positions == contest.lineup_reqs.loc[roster_slot_id])

        # Game Constraint
        competition_ids = contest.draftables.competition_id.astype("category")
        competition_matrix = np.zeros((num_draftables, num_competitions), dtype="int8")
        competition_matrix[np.arange(num_draftables), competition_ids.cat.codes] = 1
        for col in range(num_competitions):
            drafted_competitions = LinearExpression(
                linear_coefs=competition_matrix[:, col], linear_vars=drafted_vars_list
            )
            must_choose_from_multiple_games = int(
                (contest.draft_group.contest_type_id not in {81, 93}) and (num_competitions > 1)
            )
            model.constraints.add(drafted_competitions <= num_to_draft - must_choose_from_multiple_games)

        # Initialize Pyomo Solver
        opt = pyo.SolverFactory(solver["name"], executable=solver["executable"])

        # TODO: use this when we solve for multiple lineups
        # if USE_PERSISTENT_SOLVER:
        #     opt = pyo.SolverFactory("cplex_persistent")
        #     opt.set_instance(model)
        # else:
        #     opt = pyo.SolverFactory("cbc", executable="solvers/cbc.exe")

        return model, opt

    @classmethod
    def get_drafted_indices(cls, model: ConcreteModel) -> pd.Series:
        return pd.Series([key for key, value in model.drafted.get_values().items() if value > 0.5])  # type: ignore

    def generate_lineups(self, contest: Contest, **kwargs) -> pd.DataFrame:
        """Single Lineup Solver"""

        try:
            USE_PERSISTENT_SOLVER = kwargs["solver"]["persistent"]
        except:
            raise TypeError("persistent must be specified in configuration file for each solver")

        try:
            SALARY = kwargs["salary"]
        except:
            raise TypeError("salary must be specified in configuration file")

        try:
            PROJECTION_CUTOFF = kwargs["projection_cutoff"]
        except:
            raise TypeError("projection_cutoff must be specified in configuration file")

        try:
            SAMPLE_SIZE = kwargs["sample_size"]
        except:
            raise TypeError("sample_size must be specified in configuration file")

        try:
            DESIRED_LINEUPS = kwargs["desired_lineups"]
        except:
            raise TypeError("desired_lineups must be specified in configuration file")

        if SAMPLE_SIZE < DESIRED_LINEUPS:
            raise Exception("The Sample Size must be greater than the desired number of lineups")

        try:
            SOLVER = kwargs["solver"]
        except:
            raise TypeError("solver must be specified in configuration file")

        if contest.details.draft_group_id not in self.cache:
            model, opt = self.initialize_problem(contest, SALARY, PROJECTION_CUTOFF, SOLVER)

            for lineup_num in range(SAMPLE_SIZE):
                sol = opt.solve() if USE_PERSISTENT_SOLVER else opt.solve(model)

                if (cond := sol.solver.termination_condition) != "optimal":
                    breakpoint()
                    raise Exception(f"Solver terminated with condition {cond}")

                drafted_indices = MaximizeEVMultipleSamplerAlgorithm.get_drafted_indices(model)

                lineup = (
                    contest.draftables.iloc[drafted_indices]
                    .assign(lineup_num=lineup_num, projected=lambda df: contest.projections.loc[df.index])
                    .set_index("lineup_num", append=True)
                    .swaplevel()
                )

                self.cache[contest.details.draft_group_id].append(lineup)

                # Prevent this exact lineup from being drafted again
                drafted_player_ids = contest.draftables.iloc[drafted_indices].player_id

                lineup_overlap_constraint = LinearExpression(
                    linear_coefs=contest.draftables.player_id.isin(drafted_player_ids).astype(int).tolist(),
                    linear_vars=[model.drafted[i] for i in range(len(contest.draftables))],  # type: ignore
                ) <= (len(drafted_indices) - 1)

                if USE_PERSISTENT_SOLVER:
                    constraint = pyo.Constraint(expr=lineup_overlap_constraint)
                    constraint_name = f"duplicate_constraint_{lineup_num}"
                    setattr(model, constraint_name, constraint)
                    opt.add_constraint(getattr(model, constraint_name))  # type: ignore
                else:
                    model.constraints.add(lineup_overlap_constraint)  # type: ignore

        lineups_to_submit = min(DESIRED_LINEUPS, contest.max_entries)
        selected_lineup_indices = np.random.choice(SAMPLE_SIZE, lineups_to_submit, replace=False)
        selected_lineups = pd.concat(
            [self.cache[contest.details.draft_group_id][idx] for idx in selected_lineup_indices]
        )
        return selected_lineups

        # TODO: add covariance in another algorithm
        # player_ids = classic_draftables.loc[drafted].player_id
        # draftable_ids_to_exclude = classic_draftables.index[classic_draftables.player_id.isin(player_ids)]

        # # add covariance constraints
        # covariance_expr = (
        #     LinearExpression(
        #         linear_coefs=[1] * len(draftable_ids_to_exclude),
        #         linear_vars=[model.drafted[i] for i in draftable_ids_to_exclude],
        #     )
        #     <= 4
        # )

        # if USE_PERSISTENT_SOLVER:
        #     constraint = pyo.Constraint(expr=covariance_expr)
        #     constraint_name = f"covariance_constraint_{lineup_num}"
        #     setattr(model, constraint_name, constraint)
        #     opt.add_constraint(getattr(model, constraint_name))
        # else:
        #     model.constraints.add(covariance_expr)
        # TODO: End
