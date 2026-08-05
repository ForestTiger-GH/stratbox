from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

from stratbox.macrobanks.cbr_sors_restoration.problem import (
    bridge_profile_problem,
    strict_publication_problem,
)
from stratbox.macrobanks.cbr_sors_restoration.solver import ReusableHighsModel


def main() -> None:
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    with input_path.open('rb') as stream:
        payload = pickle.load(stream)
    problem = payload['problem']
    targets = payload['targets']
    profile_targets = payload.get('profile_targets', targets)
    profile_tolerance = payload['profile_tolerance']
    time_limit = payload['time_limit']
    threads = payload['threads']

    model = ReusableHighsModel(problem, time_limit=time_limit, threads=threads)
    bridge = model.solve_objective(problem.bridge_objective)
    backend = model.backend
    version = model.version
    del model

    strict = {}
    profile = {}
    if bridge.success and bridge.values is not None:
        strict_problem = strict_publication_problem(problem)
        for target in targets:
            model = ReusableHighsModel(strict_problem, time_limit=time_limit, threads=threads)
            lower = model.solve_vector(target.indices, target.coefficients, maximize=False)
            del model
            model = ReusableHighsModel(strict_problem, time_limit=time_limit, threads=threads)
            upper = model.solve_vector(target.indices, target.coefficients, maximize=True)
            del model
            strict[target.target_id] = (lower, upper)

        profile_problems = {}
        for target in profile_targets:
            local_problem = profile_problems.get(target.region_code)
            if local_problem is None:
                local_problem = bridge_profile_problem(
                    problem,
                    bridge.values,
                    tolerance=profile_tolerance,
                    geography_node_id=target.region_code,
                )
                profile_problems[target.region_code] = local_problem
            model = ReusableHighsModel(local_problem, time_limit=time_limit, threads=threads)
            lower = model.solve_vector(target.indices, target.coefficients, maximize=False)
            del model
            model = ReusableHighsModel(local_problem, time_limit=time_limit, threads=threads)
            upper = model.solve_vector(target.indices, target.coefficients, maximize=True)
            del model
            profile[target.target_id] = (lower, upper)

    result = {
        'bridge': bridge,
        'strict': strict,
        'profile': profile,
        'backend': backend,
        'version': version,
    }
    with output_path.open('wb') as stream:
        pickle.dump(result, stream, protocol=pickle.HIGHEST_PROTOCOL)
        stream.flush()
        os.fsync(stream.fileno())
    os._exit(0)


if __name__ == '__main__':
    main()
