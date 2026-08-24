import itertools
import logging
from typing import List, Dict, Set, Tuple

logger = logging.getLogger(__name__)

class ComponentRejection(Exception):
    pass

class OneToNAllocator:
    def __init__(self, config: dict):
        self.config = config
        self.threshold = config.get('matching', {}).get('auto_match_threshold', 0.80)
        self.max_component_size = 10

    def group_and_validate(self, scored_records: Dict[str, Tuple[Dict, List[Dict]]]) -> List[List[Dict]]:
        """
        Takes scored_records: {sid: (source_rec, ranked_candidates)}
        Returns valid components (list of records).
        """
        # 1. Build Edge Graph
        edges = {}
        nodes = {}
        for sid, (rec, ranked) in scored_records.items():
            nodes[sid] = rec
            for cand in ranked:
                conf = cand.get('probabilistic_confidence', cand.get('confidence_score', 0.0))
                cand_sid = cand['candidate_source_record_id']
                nodes[cand_sid] = cand.get('_cand_record', cand.get('candidate_record'))
                # Store the max confidence for the undirected edge
                edge_pair = tuple(sorted([sid, cand_sid]))
                edges[edge_pair] = max(edges.get(edge_pair, 0.0), conf)

        # Build adjacency list for edges >= threshold
        adj = {sid: set() for sid in nodes}
        for (u, v), conf in edges.items():
            if conf >= self.threshold:
                adj[u].add(v)
                adj[v].add(u)

        # 2. Extract Components
        visited = set()
        components = []
        for sid in adj:
            if sid not in visited:
                comp = set()
                queue = [sid]
                while queue:
                    curr = queue.pop(0)
                    if curr not in visited:
                        visited.add(curr)
                        comp.add(curr)
                        queue.extend(adj[curr])
                if len(comp) > 1:
                    components.append(comp)

        # 3. Validate Components
        valid_components = []
        for comp in components:
            try:
                comp_recs = [nodes[s] for s in comp]
                self._validate_component(comp_recs, edges)
                valid_components.append(comp_recs)
            except ComponentRejection as e:
                logger.info(f"Rejected component {comp}: {e}")
                
        return valid_components

    def _validate_component(self, comp: List[Dict], edges: Dict[Tuple[str, str], float]):
        # 1. Size constraint
        if len(comp) > self.max_component_size:
            raise ComponentRejection("Component too large")

        # 2. Duplicate Check
        sids = [r['source_record_id'] for r in comp]
        if len(sids) != len(set(sids)):
            raise ComponentRejection("Duplicate entity IDs in component")

        # 3. Currency Check
        currencies = set(r.get('currency') for r in comp if r.get('currency'))
        if len(currencies) > 1:
            raise ComponentRejection("Mixed currencies")

        # 4. Cardinality / Source Type Validation
        banks = [r for r in comp if r['source'] == 'BANK']
        gateways = [r for r in comp if r['source'] == 'GATEWAY']
        invoices = [r for r in comp if r['source'] == 'INVOICE']

        is_3way = (len(banks) == 1 and len(gateways) == 1 and len(invoices) == 1)
        is_bank_to_invoices = (len(banks) == 1 and len(invoices) >= 1 and len(gateways) == 0)
        is_banks_to_invoice = (len(banks) >= 1 and len(invoices) == 1 and len(gateways) == 0)
        is_bank_to_gateway = (len(banks) == 1 and len(gateways) == 1 and len(invoices) == 0)
        is_gateway_to_invoices = (len(gateways) == 1 and len(invoices) >= 1 and len(banks) == 0)

        if not any([is_3way, is_bank_to_invoices, is_banks_to_invoice, is_bank_to_gateway, is_gateway_to_invoices]):
            raise ComponentRejection(f"Invalid cardinality: B={len(banks)}, G={len(gateways)}, I={len(invoices)}")

        # 5. Amount Conservation
        if is_bank_to_invoices:
            b_amt = banks[0].get('amount_minor_units', 0)
            i_amt = sum(i.get('amount_minor_units', 0) for i in invoices)
            if b_amt != i_amt:
                raise ComponentRejection("Amount conservation failed")
        elif is_banks_to_invoice:
            b_amt = sum(b.get('amount_minor_units', 0) for b in banks)
            i_amt = invoices[0].get('amount_minor_units', 0)
            if b_amt != i_amt:
                raise ComponentRejection("Amount conservation failed")

        # 6. Direct Edge Confidence Check
        # Applied consistently at self.threshold (the canonical auto-match bar)
        # across EVERY supported edge type. Previously the 3-way Bank-Invoice
        # edge used a special-cased 0.50 -- lower than the 0.80 bar every other
        # pairwise match in the system must clear -- which meant a 3-way group
        # could auto-resolve even though its direct Bank-Invoice relationship,
        # evaluated alone, would never individually clear auto-match. Fixed
        # 2026-08-24 per audit: no edge type gets a weaker bar than any other.
        if is_3way:
            b_id = banks[0]['source_record_id']
            g_id = gateways[0]['source_record_id']
            i_id = invoices[0]['source_record_id']
            bg = edges.get(tuple(sorted([b_id, g_id])), 0.0)
            bi = edges.get(tuple(sorted([b_id, i_id])), 0.0)
            gi = edges.get(tuple(sorted([g_id, i_id])), 0.0)
            if bg < self.threshold:
                raise ComponentRejection(f"Weak edge: Bank-Gateway is {bg} < {self.threshold}")
            if gi < self.threshold:
                raise ComponentRejection(f"Weak edge: Gateway-Invoice is {gi} < {self.threshold}")
            if bi < self.threshold:
                raise ComponentRejection(f"Weak edge: Bank-Invoice is {bi} < {self.threshold}")
        elif is_bank_to_invoices:
            b_id = banks[0]['source_record_id']
            for inv in invoices:
                i_id = inv['source_record_id']
                conf = edges.get(tuple(sorted([b_id, i_id])), 0.0)
                if conf < self.threshold:
                    raise ComponentRejection(f"Weak edge: Bank-{i_id} is {conf} < {self.threshold}")
        elif is_banks_to_invoice:
            i_id = invoices[0]['source_record_id']
            for bank in banks:
                b_id = bank['source_record_id']
                conf = edges.get(tuple(sorted([b_id, i_id])), 0.0)
                if conf < self.threshold:
                    raise ComponentRejection(f"Weak edge: Invoice-{b_id} is {conf} < {self.threshold}")
        elif is_bank_to_gateway:
            b_id = banks[0]['source_record_id']
            g_id = gateways[0]['source_record_id']
            conf = edges.get(tuple(sorted([b_id, g_id])), 0.0)
            if conf < self.threshold:
                raise ComponentRejection(f"Weak edge: Bank-Gateway is {conf} < {self.threshold}")
        elif is_gateway_to_invoices:
            g_id = gateways[0]['source_record_id']
            for inv in invoices:
                i_id = inv['source_record_id']
                conf = edges.get(tuple(sorted([g_id, i_id])), 0.0)
                if conf < self.threshold:
                    raise ComponentRejection(f"Weak edge: Gateway-{i_id} is {conf} < {self.threshold}")
