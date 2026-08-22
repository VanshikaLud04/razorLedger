"""
tests/test_matching.py — Tests real matching pipeline components.
No DB required. Pure computation tests.
"""
import sys
import pathlib
from datetime import date, timedelta
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from app.matching.deterministic import DeterministicMatcher
from app.matching.fuzzy import FuzzyMatcher
from app.matching.evidence import EvidenceFeatureBuilder, compute_rarity_frequencies
from app.matching.evidence_weighted import EvidenceWeightedScorer

CONFIG = {
    'matching': {
        'auto_match_threshold': 0.80,
        'review_threshold': 0.40,
        'minimum_confidence_gap': 0.15,
        'amount_tolerance_minor': 50,
        'date_tolerance_days': 3,
        'settlement_window_days': 5,
    },
    'evidence': {
        'min_families_for_auto_match': 2,
        'amount_bins': {'exact': 0, 'near': 50, 'close': 500},
        'date_bins': {'same_day': 0, 'near': 1, 'close': 3},
        'reference_bins': {'exact': 1.0, 'high': 0.85, 'medium': 0.60},
        'counterparty_bins': {'high': 0.85, 'medium': 0.60},
        'description_bins': {'high': 0.80, 'medium': 0.55},
    },
    'llm': {'llm_max_evidence_delta': 0.05},
}

det = DeterministicMatcher(CONFIG)
fuzz = FuzzyMatcher(CONFIG)
evb = EvidenceFeatureBuilder(CONFIG)
scorer = EvidenceWeightedScorer(CONFIG)

TODAY = date(2024, 6, 15)

def make_records(ref_a='INV-2024-001234', ref_b='INV-2024-001234',
                 amt_a=100000, amt_b=100000,
                 date_a=None, date_b=None,
                 src_a='INVOICE', src_b='BANK'):
    return (
        {'source_record_id': 'A', 'source': src_a,
         'reference': ref_a, 'counterparty': 'Acme Corp',
         'amount_minor_units': amt_a,
         'transaction_date': date_a or TODAY,
         'description': 'Payment for services'},
        {'source_record_id': 'B', 'source': src_b,
         'reference': ref_b, 'counterparty': 'Acme Corp',
         'amount_minor_units': amt_b,
         'transaction_date': date_b or TODAY,
         'description': 'Settlement received'},
    )


class TestDeterministicMatcher:
    def test_exact_reference_match(self):
        a, b = make_records()
        result = det.match(a, b)
        assert result['is_exact_reference_match'] is True
        assert result['deterministic_match'] is True

    def test_exact_amount_date_match(self):
        a, b = make_records(ref_a='INV-001', ref_b='DIFFERENT')
        result = det.match(a, b)
        assert result['is_exact_amount_date_match'] is True
        assert result['deterministic_match'] is True

    def test_no_match(self):
        a, b = make_records(ref_a='INV-001', ref_b='INV-999',
                             amt_a=100000, amt_b=200000,
                             date_b=TODAY + timedelta(days=10))
        result = det.match(a, b)
        assert result['deterministic_match'] is False

    def test_reference_normalization(self):
        """Matching strips hyphens and spaces before comparing."""
        a, b = make_records(ref_a='INV 2024 001234', ref_b='INV-2024-001234')
        result = det.match(a, b)
        assert result['is_exact_reference_match'] is True


class TestFuzzyMatcher:
    def test_handles_none_reference(self):
        """No crash when reference is None."""
        a, b = make_records(ref_a=None, ref_b=None)
        result = fuzz.score(a, b)
        assert result['reference_similarity_score'] == 0.0

    def test_exact_reference_scores_high(self):
        a, b = make_records()
        result = fuzz.score(a, b)
        assert result['reference_similarity_score'] >= 0.99

    def test_corrupted_reference_scores_moderate(self):
        # Bank truncates ref by 4 chars — still should score reasonably
        a, b = make_records(ref_a='INV-2024-001234', ref_b='INV-2024-0012')
        result = fuzz.score(a, b)
        assert result['reference_similarity_score'] > 0.70


class TestEvidenceFamilies:
    def _get_evidence(self, rec_a, rec_b):
        dterm = det.match(rec_a, rec_b)
        fscores = fuzz.score(rec_a, rec_b)
        return evb.build(rec_a, rec_b, fscores, dterm)

    def test_numeric_and_temporal_families_present(self):
        """Exact amount + same date → NUMERIC and TEMPORAL families."""
        a, b = make_records(ref_a=None, ref_b=None)  # no reference
        ev = self._get_evidence(a, b)
        assert 'NUMERIC' in ev['evidence_families_present']
        assert 'TEMPORAL' in ev['evidence_families_present']

    def test_identity_family_on_exact_reference(self):
        a, b = make_records()
        ev = self._get_evidence(a, b)
        assert 'IDENTITY' in ev['evidence_families_present']

    def test_source_family_on_compatible_sources(self):
        a, b = make_records(src_a='INVOICE', src_b='BANK')
        ev = self._get_evidence(a, b)
        assert 'SOURCE' in ev['evidence_families_present']

    def test_amount_family_only_not_auto_match_eligible(self):
        """NUMERIC family only (no date, no identity, no source) → not eligible."""
        # Different source types that are incompatible
        a, b = make_records(src_a='BANK', src_b='BANK',
                             ref_a=None, ref_b=None,
                             date_b=TODAY + timedelta(days=10))
        ev = self._get_evidence(a, b)
        eligible, reason = scorer.check_auto_match_eligibility({
            **ev,
            'probabilistic_confidence': 0.85,
            'confidence_gap_to_next': 0.20,
        })
        # SOURCE should fail (BANK-BANK incompatible) so not eligible regardless
        assert not eligible

    def test_two_families_required_for_auto_match(self):
        """Check auto_match_eligibility enforces ≥2 family rule."""
        # Craft evidence with only 1 family
        ev_one_family = {
            'amount_difference_bin': 'EXACT',
            'date_delta_bin': 'FAR',
            'reference_similarity_bin': 'LOW',
            'counterparty_similarity_bin': 'LOW',
            'source_compatibility': True,
            'evidence_rarity_score': 0.0,
            'evidence_families_present': ['NUMERIC'],  # only 1
            'probabilistic_confidence': 0.85,
            'confidence_gap_to_next': 0.20,
        }
        eligible, reason = scorer.check_auto_match_eligibility(ev_one_family)
        assert not eligible
        assert 'INSUFFICIENT_EVIDENCE_FAMILIES' in reason


class TestEvidenceWeightedScorer:
    def setup_method(self):
        self.scorer = EvidenceWeightedScorer(CONFIG)

    def test_scorer_is_deterministic(self):
        """Same inputs → same score every time."""
        ev = {
            'amount_difference_bin': 'EXACT',
            'date_delta_bin': 'SAME_DAY',
            'reference_similarity_bin': 'EXACT',
            'counterparty_similarity_bin': 'HIGH',
            'source_compatibility': True,
            'evidence_rarity_score': 0.5,
        }
        assert scorer.score_candidate(ev) == scorer.score_candidate(ev)

    def test_strong_match_scores_above_threshold(self):
        """Exact ref + exact amount + same day + compatible source → above 0.80."""
        ev = {
            'amount_difference_bin': 'EXACT',
            'date_delta_bin': 'SAME_DAY',
            'reference_similarity_bin': 'EXACT',
            'counterparty_similarity_bin': 'HIGH',
            'source_compatibility': True,
            'evidence_rarity_score': 0.0,
        }
        assert scorer.score_candidate(ev) >= 0.80

    def test_poor_match_scores_below_review_threshold(self):
        """FAR amount + FAR date + LOW ref + incompatible source → below 0.40."""
        ev = {
            'amount_difference_bin': 'FAR',
            'date_delta_bin': 'FAR',
            'reference_similarity_bin': 'LOW',
            'counterparty_similarity_bin': 'LOW',
            'source_compatibility': False,
            'evidence_rarity_score': 0.0,
        }
        assert scorer.score_candidate(ev) < 0.40

    def test_llm_adjustment_is_bounded(self):
        """LLM can move score by at most llm_max_delta in either direction."""
        base = 0.75
        up = scorer.apply_llm_adjustment(base, 'supports')
        down = scorer.apply_llm_adjustment(base, 'contradicts')
        neutral = scorer.apply_llm_adjustment(base, 'neutral')
        assert abs(up - base) <= CONFIG['llm']['llm_max_evidence_delta'] + 1e-9
        assert abs(down - base) <= CONFIG['llm']['llm_max_evidence_delta'] + 1e-9
        assert neutral == base


class TestRarityFrequencies:
    def test_compute_rarity_frequencies(self):
        records = [
            {'reference': 'INV-2024-001'},
            {'reference': 'INV-2024-001'},   # appears twice
            {'reference': 'INV-2024-002'},
            {'reference': None},
        ]
        freqs = compute_rarity_frequencies(records)
        assert freqs['__total__'] == 3
        assert freqs['INV2024001'] == 2
        assert freqs['INV2024002'] == 1

    def test_rarity_score_higher_for_rare_reference(self):
        freqs = {'INV2024COMMON': 100, 'INV2024RARE': 1, '__total__': 200}
        evb_with_rarity = EvidenceFeatureBuilder(CONFIG, rarity_frequencies=freqs)
        rare_score = evb_with_rarity._rarity_score('INV-2024-RARE', 'INV-2024-RARE')
        common_score = evb_with_rarity._rarity_score('INV-2024-COMMON', 'INV-2024-COMMON')
        assert rare_score > common_score
