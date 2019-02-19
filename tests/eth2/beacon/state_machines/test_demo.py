
import json
import pytest

import ssz

from eth2.beacon.db.chain import BeaconChainDB
from eth2.beacon.state_machines.forks.serenity.blocks import (
    SerenityBeaconBlock,
)
from eth2.beacon.tools.builder.initializer import (
    create_mock_genesis,
)
from eth2.beacon.tools.builder.proposer import (
    create_mock_block,
)
from eth2.beacon.tools.builder.validator import (
    create_mock_signed_attestations_at_slot,
)


@pytest.mark.parametrize(
    (
        'num_validators,'
        'epoch_length,'
        'min_attestation_inclusion_delay,'
        'target_committee_size,'
        'shard_count'
    ),
    [
        (100, 4, 2, 20, 2)
    ]
)
def test_demo(base_db,
              num_validators,
              config,
              keymap,
              fixture_sm_class):
    chaindb = BeaconChainDB(base_db)

    genesis_state, genesis_block = create_mock_genesis(
        num_validators=num_validators,
        config=config,
        keymap=keymap,
        genesis_block_class=SerenityBeaconBlock,
    )
    for i in range(num_validators):
        assert genesis_state.validator_registry[i].is_active(0)

    chaindb.persist_block(genesis_block, SerenityBeaconBlock)
    chaindb.persist_state(genesis_state)

    state = genesis_state
    block = genesis_block

    serialzed_validator = ssz.encode(state.validator_registry)

    with open('demo_validator.json', 'wb') as outfile:
        outfile.write(serialzed_validator)
        # json.dump(serialzed_validator, outfile)

    current_slot = 1
    chain_length = 3 * config.EPOCH_LENGTH
    attestations = ()
    blocks = (block,)
    states = (state,)

    for current_slot in range(1, chain_length):
        # two epochs
        block = create_mock_block(
            state=state,
            config=config,
            state_machine=fixture_sm_class(
                chaindb,
                blocks[-1],
            ),
            block_class=SerenityBeaconBlock,
            parent_block=block,
            keymap=keymap,
            slot=current_slot,
            attestations=attestations,
        )
        block = block.copy(
            body=block.body.copy(
                attestations=attestations,
            )
        )

        # Get state machine instance
        sm = fixture_sm_class(
            chaindb,
            blocks[-1],
        )
        state, _ = sm.import_block(block)

        chaindb.persist_state(state)
        chaindb.persist_block(block, SerenityBeaconBlock)

        blocks += (block,)
        states += (state,)
        if current_slot > config.MIN_ATTESTATION_INCLUSION_DELAY:
            attestation_slot = current_slot - config.MIN_ATTESTATION_INCLUSION_DELAY
            attestations = create_mock_signed_attestations_at_slot(
                state,
                config,
                attestation_slot,
                keymap,
                1.0,
            )
        else:
            attestations = ()

    assert state.slot == chain_length - 1
    assert isinstance(sm.block, SerenityBeaconBlock)

    serialzed_blocks = [
        ssz.encode(block).hex()
        for block in blocks
    ]

    serialzed_states = [
        ssz.encode(state).hex()
        for state in states
    ]

    with open('demo_blocks.json', 'w') as outfile:
        json.dump(serialzed_blocks, outfile)

    with open('demo_states.json', 'w') as outfile:
        json.dump(serialzed_states, outfile)
