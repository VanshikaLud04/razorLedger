from dataclasses import dataclass

@dataclass
class GeneratorConfig:
    seed: str
    partition: str
    num_events: int = 150
    corruption_rate: float = 0.30
    partial_payment_rate: float = 0.05
    refund_rate: float = 0.05
    duplicate_delivery_rate: float = 0.03

PARTITION_SEEDS = {
    'DEV': 'razorledger-dev-v1',
    'VALIDATION': 'razorledger-val-v1',
    'TEST_ADVERSARIAL': 'razorledger-adv-v1',
    'FROZEN_UNSEEN': 'razorledger-unseen-v1',
}
