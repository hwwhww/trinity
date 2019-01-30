
class Config(object):
    # Measuration Parameters
    TOTAL_TICKS = 500
    PRECISION = 0.5
    INITIAL_TIMESTAMP = 1

    # Acceleration Parameters
    MINIMIZE_CHECKING = True

    # System Parameters
    NUM_VALIDATORS = 100

    # Network Parameters
    LATENCY = 1.5 / PRECISION
    RELIABILITY = 0.9
    NUM_PEERS = 5
    SHARD_NUM_PEERS = 5
    TARGET_TOTAL_TPS = 1
    MEAN_TX_ARRIVAL_TIME = ((1 / TARGET_TOTAL_TPS) * PRECISION) * NUM_VALIDATORS

    # Validator Parameters
    TIME_OFFSET = 1
    PROB_CREATE_BLOCK_SUCCESS = 0.999
    TARGET_BLOCK_TIME = 14
    MEAN_MINING_TIME = (TARGET_BLOCK_TIME - LATENCY * PRECISION) * NUM_VALIDATORS
    DISCONNECT_THRESHOLD = 5