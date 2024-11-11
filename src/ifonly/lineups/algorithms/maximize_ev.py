import pandas as pd
import numpy as np
from ifonly import Contest
from ifonly.lineups.algorithms.algorithm import Algorithm
import pyomo.environ as pyo
from pyomo.core.expr.numeric_expr import LinearExpression
from pyomo.core.base.PyomoModel import ConcreteModel
from pyomo.opt.base.solvers import OptSolver
from typing import Tuple, Dict


class MaximizeEVAlgorithm(Algorithm):
    name = "maximize_ev"

    def __init__(self):
        super().__init__(MaximizeEVAlgorithm.name)

    def initialize_cache(self) -> Dict[int, pd.DataFrame]:
        return dict()

    def initialize_problem(self, contest: Contest, salary: int, solver: dict) -> Tuple[ConcreteModel, OptSolver]:
        num_to_draft = contest.lineup_reqs.sum()
        num_draftables = len(contest.draftables)
        num_players = contest.draftables.player_id.nunique()
        num_positions = len(contest.lineup_reqs)
        num_competitions = contest.draft_group.games_count
        projections = contest.projections.values
        salaries = contest.draftables.salary.astype("int64")
        # NOTE: I think dividing by gcd will make things run faster, but haven't tested this
        salary_gcd = np.gcd.reduce(salaries)

        model = pyo.ConcreteModel(name=MaximizeEVAlgorithm.name)

        # Pyomo Variables
        model.drafted = pyo.Var(range(num_draftables), domain=pyo.Boolean)
        drafted_vars_list = [model.drafted[i] for i in range(num_draftables)]

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
            SOLVER = kwargs["solver"]
        except:
            raise TypeError("solver must be specified in configuration file")

        if contest.details.draft_group_id in self.cache:
            return self.cache[contest.details.draft_group_id]

        model, opt = self.initialize_problem(contest, SALARY, SOLVER)

        sol = opt.solve() if USE_PERSISTENT_SOLVER else opt.solve(model)

        if (cond := sol.solver.termination_condition) != "optimal":
            breakpoint()
            raise Exception(f"Solver terminated with condition {cond}")

        drafted_indices = MaximizeEVAlgorithm.get_drafted_indices(model)

        lineup = (
            contest.draftables.iloc[drafted_indices]
            .assign(lineup_num=0)
            .set_index("lineup_num", append=True)
            .swaplevel()
        )

        self.cache[contest.details.draft_group_id] = lineup

        return lineup

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
