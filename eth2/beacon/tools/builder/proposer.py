from typing import (
    Dict,
    Sequence,
    Type,
)
from eth_typing import (
    BLSPubkey,
    BLSSignature,
)

from eth_typing import Hash32

from eth2.beacon.enums import (
    SignatureDomain,
)
from eth2.beacon.committee_helpers import (
    get_beacon_proposer_index,
)
from eth2.beacon.configs import (
    BeaconConfig,
    CommitteeConfig,
)
from eth2.beacon.exceptions import (
    ProposerIndexError,
)
from eth2.beacon.helpers import (
    slot_to_epoch,
)
from eth2.beacon.state_machines.base import (
    BaseBeaconStateMachine,
)

from eth2.beacon.types.attestations import Attestation
from eth2.beacon.types.blocks import (
    BaseBeaconBlock,
    BeaconBlockBody,
)
from eth2.beacon.types.eth1_data import Eth1Data
from eth2.beacon.types.forks import Fork
from eth2.beacon.types.proposal import Proposal
from eth2.beacon.types.states import BeaconState
from eth2.beacon.typing import (
    FromBlockParams,
    Slot,
    ValidatorIndex,
)

from eth2.beacon.tools.builder.validator import (
    sign_transaction,
)


def _generate_randao_reveal(privkey: int,
                            slot: Slot,
                            fork: Fork,
                            config: BeaconConfig) -> BLSSignature:
    """
    Return the RANDAO reveal for the validator represented by ``privkey``.
    The current implementation requires a validator to provide the BLS signature
    over the SSZ-serialized epoch in which they are proposing a block.
    """
    epoch = slot_to_epoch(slot, config.SLOTS_PER_EPOCH)

    message_hash = Hash32(epoch.to_bytes(32, byteorder='little'))

    randao_reveal = sign_transaction(
        message_hash=message_hash,
        privkey=privkey,
        fork=fork,
        slot=slot,
        signature_domain=SignatureDomain.DOMAIN_RANDAO,
        slots_per_epoch=config.SLOTS_PER_EPOCH,
    )
    return randao_reveal


def validate_proposer_index(state: BeaconState,
                            config: BeaconConfig,
                            slot: Slot,
                            validator_index: ValidatorIndex) -> None:
    beacon_proposer_index = get_beacon_proposer_index(
        state.copy(
            slot=slot,
        ),
        slot,
        CommitteeConfig(config),
    )

    if validator_index != beacon_proposer_index:
        raise ProposerIndexError


def create_block_on_state(
        *,
        state: BeaconState,
        config: BeaconConfig,
        state_machine: BaseBeaconStateMachine,
        block_class: Type[BaseBeaconBlock],
        parent_block: BaseBeaconBlock,
        slot: Slot,
        validator_index: ValidatorIndex,
        privkey: int,
        attestations: Sequence[Attestation],
        check_proposer_index: bool=True) -> BaseBeaconBlock:
    """
    Create a beacon block with the given parameters.
    """
    # Check proposer
    if check_proposer_index:
        validate_proposer_index(state, config, slot, validator_index)

    # Prepare block: slot and parent_root
    block = block_class.from_parent(
        parent_block=parent_block,
        block_params=FromBlockParams(slot=slot),
    )

    # TODO: Add more operations
    randao_reveal = _generate_randao_reveal(privkey, slot, state.fork, config)
    eth1_data = Eth1Data.create_empty_data()
    body = BeaconBlockBody.create_empty_body().copy(
        attestations=attestations,
    )

    block = block.copy(
        randao_reveal=randao_reveal,
        eth1_data=eth1_data,
        body=body,
    )

    # Apply state transition to get state root
    state, block = state_machine.import_block(block, check_proposer_signature=False)

    # Sign
    empty_signature_block_root = block.block_without_signature_root
    proposal_root = Proposal(
        slot,
        config.BEACON_CHAIN_SHARD_NUMBER,
        empty_signature_block_root,
    ).root

    signature = sign_transaction(
        message_hash=proposal_root,
        privkey=privkey,
        fork=state.fork,
        slot=slot,
        signature_domain=SignatureDomain.DOMAIN_BEACON_BLOCK,
        slots_per_epoch=config.SLOTS_PER_EPOCH,
    )

    block = block.copy(
        signature=signature,
    )

    return block


def _get_proposer_index(state_machine: BaseBeaconStateMachine,
                        state: BeaconState,
                        slot: Slot,
                        previous_block_root: Hash32,
                        config: BeaconConfig) -> ValidatorIndex:
    # advance the state to the ``slot``.
    state_transition = state_machine.state_transition
    state = state_transition.apply_state_transition_without_block(state, slot, previous_block_root)

    proposer_index = get_beacon_proposer_index(
        state,
        slot,
        CommitteeConfig(config),
    )
    return proposer_index


def create_mock_block(*,
                      state: BeaconState,
                      config: BeaconConfig,
                      state_machine: BaseBeaconStateMachine,
                      block_class: Type[BaseBeaconBlock],
                      parent_block: BaseBeaconBlock,
                      keymap: Dict[BLSPubkey, int],
                      slot: Slot=None,
                      attestations: Sequence[Attestation]=()) -> BaseBeaconBlock:
    """
    Create a mocking block at ``slot`` with the given block parameters and ``keymap``.

    Note that it doesn't return the correct ``state_root``.
    """
    proposer_index = _get_proposer_index(state_machine, state, slot, parent_block.root, config)
    proposer_pubkey = state.validator_registry[proposer_index].pubkey
    proposer_privkey = keymap[proposer_pubkey]

    result_block = create_block_on_state(
        state=state,
        config=config,
        state_machine=state_machine,
        block_class=block_class,
        parent_block=parent_block,
        slot=slot,
        validator_index=proposer_index,
        privkey=proposer_privkey,
        attestations=attestations,
        check_proposer_index=False,
    )

    return result_block
