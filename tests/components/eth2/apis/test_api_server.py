import asyncio
import json
import pytest

from aiohttp.test_utils import (
    RawTestServer,
    TestClient,
)
from ssz.tools import to_formatted_dict

from eth2.beacon.types.attestations import Attestation
from eth2.beacon.types.blocks import BeaconBlock
from eth2.beacon.tools.factories import (
    BeaconChainFactory,
)
from libp2p.crypto.secp256k1 import create_new_key_pair

from trinity.protocol.bcc_libp2p.node import Node
from trinity.http.handlers.api_handler import APIHandler


GET_METHOD = 'GET'
POST_METHOD = 'POST'


@pytest.fixture()
def chain(num_validators, base_db):
    chain = BeaconChainFactory(num_validators=num_validators, base_db=base_db)
    state_machine = chain.get_state_machine()
    state = chain.get_head_state()
    slot = 4
    post_state = state_machine.state_transition.apply_state_transition(
        state,
        future_slot=slot,
    )
    chain.chaindb.persist_state(post_state)
    return chain


@pytest.fixture()
async def libp2p_node(chain, event_bus):
    key_pair = create_new_key_pair()
    libp2p_node = Node(
        key_pair=key_pair,
        listen_ip="0.0.0.0",
        listen_port=30303,
        preferred_nodes=(),
        chain=chain,
        subnets=(),
        event_bus=event_bus,
    )
    asyncio.ensure_future(libp2p_node.run())
    await asyncio.sleep(0.01)
    return libp2p_node


@pytest.fixture
async def http_server(chain, event_bus):
    server = RawTestServer(APIHandler.handle(chain)(event_bus))
    return server


@pytest.fixture
async def http_client(http_server):
    client = TestClient(http_server)
    asyncio.ensure_future(client.start_server())
    await asyncio.sleep(0.01)
    return client


sample_block = BeaconBlock.create()
sample_attestation = Attestation.create()


@pytest.mark.parametrize(
    'num_validators',
    (2,),
)
@pytest.mark.parametrize(
    'method, resource, object, json_data, status_code',
    (
        (GET_METHOD, 'beacon', 'head', '', 200),
        (GET_METHOD, 'beacon', 'block?slot=0', '', 200),
        (GET_METHOD, 'beacon', 'state?slot=4', '', 200),
        (GET_METHOD, 'network', 'peers', '', 200),
        (GET_METHOD, 'network', 'peer_id', '', 200),
        (GET_METHOD, 'validator', '0x8a82fe1e16fd56fb4937ea90f071e0c1775f439bf7812428a773f8d55b506ef45e59fe5bf974a959c49224ce226296c7', '', 200),  # noqa: E501
        (GET_METHOD, 'validator', 'duties?validator_pubkeys=0x8a82fe1e16fd56fb4937ea90f071e0c1775f439bf7812428a773f8d55b506ef45e59fe5bf974a959c49224ce226296c7&validator_pubkeys=0x90b17b958ffd55c1a7e0ff585cdc578f3cfeddd0bc76b07e825b0f5af297d442eb22560394a6a40cf42dbd0bae2a268b', '', 200),  # noqa: E501
        (POST_METHOD, 'validator', 'block', json.dumps(to_formatted_dict(sample_block)), 200),
        (POST_METHOD, 'validator', 'attestation', json.dumps(to_formatted_dict(sample_attestation)), 200),  # noqa: E501
    )
)
@pytest.mark.asyncio
async def test_restful_http_server(
    http_client,
    event_loop,
    event_bus,
    base_db,
    method,
    resource,
    object,
    json_data,
    status_code,
    num_validators,
    chain,
    libp2p_node,
):
    request_path = resource + '/' + object
    response = await http_client.request(method, request_path, json=json_data)

    try:
        assert response.status == status_code
    except Exception:
        print('[ERROR]:', response.reason)
        raise

    if str(status_code).startswith('2'):
        response_data = await response.json()
        print(f'[SUCCESS]: {request_path}: \t {response_data}\n')

    await http_client.close()
