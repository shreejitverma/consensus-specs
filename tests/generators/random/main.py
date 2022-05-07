from eth2spec.test.helpers.constants import PHASE0, ALTAIR
from eth2spec.gen_helpers.gen_from_tests.gen import run_state_test_generators


if __name__ == "__main__":
    phase_0_mods = {
        key: f'eth2spec.test.phase0.random.test_{key}'
        for key in [
            'random',
        ]
    }

    altair_mods = {
        key: f'eth2spec.test.altair.random.test_{key}'
        for key in [
            'random',
        ]
    }


    all_mods = {
        PHASE0: phase_0_mods,
        ALTAIR: altair_mods,
    }

    run_state_test_generators(runner_name="random", all_mods=all_mods)
