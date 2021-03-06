
class Config(object):
    # Measuration Parameters
    TOTAL_TICKS = 80
    PRECISION = 1
    INITIAL_TIMESTAMP = 1

    # Acceleration Parameters
    MINIMIZE_CHECKING = True
    GENERATE_STATE = False
    LOGGING_NETWORK = False

    # SPEC Parameters
    SLOTS_PER_EPOCH = 8

    # System Parameters
    NUM_VALIDATORS = 8

    # Network Parameters
    LATENCY = 1.5 / PRECISION
    RELIABILITY = 1.0
    NUM_PEERS = 10
    SHARD_NUM_PEERS = 5
    TARGET_TOTAL_TPS = 1
    MEAN_TX_ARRIVAL_TIME = ((1 / TARGET_TOTAL_TPS) * PRECISION) * NUM_VALIDATORS

    # Validator Parameters
    TIME_OFFSET = 1
    PROB_CREATE_BLOCK_SUCCESS = 0.999
    DISCONNECT_THRESHOLD = 5
