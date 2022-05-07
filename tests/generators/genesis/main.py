from eth2spec.gen_helpers.gen_from_tests.gen import run_state_test_generators, combine_mods
from eth2spec.test.helpers.constants import PHASE0, ALTAIR, BELLATRIX


if __name__ == "__main__":
    phase_0_mods = {
        key: f'eth2spec.test.phase0.genesis.test_{key}'
        for key in [
            'initialization',
            'validity',
        ]
    }


    # we have new unconditional lines in `initialize_beacon_state_from_eth1` and we want to test it
    altair_mods = phase_0_mods

    _new_bellatrix_mods = {
        key: f'eth2spec.test.bellatrix.genesis.test_{key}'
        for key in [
            'initialization',
        ]
    }

    bellatrix_mods = combine_mods(_new_bellatrix_mods, altair_mods)

    all_mods = {
        PHASE0: phase_0_mods,
        ALTAIR: altair_mods,
        BELLATRIX: bellatrix_mods,
    }

    run_state_test_generators(runner_name="genesis", all_mods=all_mods)
