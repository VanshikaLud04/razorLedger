class AdversarialHoldoutEvaluator:
    def __init__(self, truth_bundle, decisions, attack_classes):
        self.truth_bundle = truth_bundle
        self.decisions = decisions
        self.attack_classes = attack_classes

    def compute(self) -> dict:
        return {'status': 'NOT_IMPLEMENTED_P1'}
