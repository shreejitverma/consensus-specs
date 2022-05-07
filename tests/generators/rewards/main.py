from eth2spec.gen_helpers.gen_from_tests.gen import run_state_test_generators
from eth2spec.test.helpers.constants import PHASE0, ALTAIR, BELLATRIX


if __name__ == "__main__":
    phase_0_mods = {
        key: f'eth2spec.test.phase0.rewards.test_{key}'
        for key in [
            'basic',
            'leak',
            'random',
        ]
    }

    # No additional Altair specific rewards tests, yet.
    altair_mods = phase_0_mods

    # No additional Bellatrix specific rewards tests, yet.
    # Note: Block rewards are non-epoch rewards and are tested as part of block processing tests.
    # Transaction fees are part of the execution-layer.
    bellatrix_mods = altair_mods

    all_mods = {
        PHASE0: phase_0_mods,
        ALTAIR: altair_mods,
        BELLATRIX: bellatrix_mods,
    }

    run_state_test_generators(runner_name="rewards", all_mods=all_mods)
