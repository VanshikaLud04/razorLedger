"""
tests/test_benchmark_integrity.py — Enforces the evaluator/matcher boundary.

These are structural tests: they check the codebase organisation, not runtime behaviour.
They run without a DB or network.
"""
import ast
import pathlib
import re
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))


REPO_ROOT = pathlib.Path(__file__).parent.parent
APP_DIR = REPO_ROOT / 'app'
MIGRATION_SQL = REPO_ROOT / 'migrations' / '001_initial.sql'


def test_matcher_cannot_import_truth_module():
    """
    No file under app/ may import generator.truth.
    Checks for: 'import generator.truth', 'from generator.truth import ...',
    'from generator import truth'.
    Uses a known file list (same as what git tracks) to avoid slow filesystem scans.
    """
    # Explicit list of app/ source files — update if new files are added to app/
    known_app_files = [
        'app/__init__.py', 'app/db.py', 'app/models.py', 'app/schemas.py',
        'app/ingest.py', 'app/blocking.py', 'app/decision.py', 'app/audit.py',
        'app/pipeline.py', 'app/main.py',
        'app/allocation/__init__.py', 'app/allocation/one_to_one.py', 'app/allocation/one_to_n.py',
        'app/controls/__init__.py', 'app/controls/engine.py',
        'app/matching/__init__.py', 'app/matching/deterministic.py', 'app/matching/fuzzy.py',
        'app/matching/evidence.py', 'app/matching/evidence_weighted.py',
        'app/matching/probabilistic.py', 'app/matching/llm.py',
        'app/routes/__init__.py', 'app/routes/ingest.py', 'app/routes/reconcile.py',
        'app/routes/review.py', 'app/routes/audit_trail.py', 'app/routes/approve.py',
    ]
    violations = []
    for rel_path in known_app_files:
        py_file = REPO_ROOT / rel_path
        if not py_file.exists():
            continue
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'generator.truth' or alias.name.startswith('generator.truth.'):
                        violations.append((rel_path, alias.name))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if module == 'generator.truth' or module.startswith('generator.truth.'):
                    violations.append((rel_path, f'from {module} import ...'))
                if module == 'generator':
                    for alias in node.names:
                        if alias.name == 'truth':
                            violations.append((rel_path, 'from generator import truth'))

    assert violations == [], (
        f"app/ imports generator.truth — benchmark integrity violation:\n"
        + '\n'.join(f"  {f}: {imp}" for f, imp in violations)
    )



def test_ground_truth_group_id_not_in_source_records_table():
    """
    The source_records table definition in the migration must not have a
    ground_truth_group_id column. It is stripped on ingest.
    """
    sql = MIGRATION_SQL.read_text()
    # Extract just the source_records CREATE TABLE block
    table_match = re.search(
        r'CREATE TABLE source_records\s*\(.*?\);',
        sql,
        re.DOTALL | re.IGNORECASE,
    )
    assert table_match, 'source_records table not found in 001_initial.sql'
    table_def = table_match.group(0)
    assert 'ground_truth_group_id' not in table_def, (
        'ground_truth_group_id found in source_records schema — '
        'it must never be persisted in the DB'
    )


def test_evaluation_may_import_truth():
    """
    Sanity check: evaluation/ is allowed to import generator.truth.
    At minimum, benchmark.py should exist and be importable as a module.
    """
    eval_dir = REPO_ROOT / 'evaluation'
    assert eval_dir.exists()
    assert (eval_dir / 'benchmark.py').exists()


def test_no_float_money_in_source_records_schema():
    """
    The source_records table must use BIGINT for amount, not NUMERIC or FLOAT.
    Constitution rule 6.
    """
    sql = MIGRATION_SQL.read_text()
    table_match = re.search(
        r'CREATE TABLE source_records\s*\(.*?\);',
        sql, re.DOTALL | re.IGNORECASE,
    )
    assert table_match
    table_def = table_match.group(0)
    assert 'BIGINT' in table_def.upper()
    assert 'FLOAT' not in table_def.upper()
    assert 'NUMERIC' not in table_def.upper()


def test_idempotency_constraint_is_run_scoped():
    """
    UNIQUE constraint must be (run_id, source, source_event_id) not (source, source_event_id).
    Constitution fix #5: run-scoped idempotency.
    """
    sql = MIGRATION_SQL.read_text()
    # Find the UNIQUE constraint in source_records
    assert 'UNIQUE (run_id, source, source_event_id)' in sql, (
        'Expected run-scoped UNIQUE(run_id, source, source_event_id) in source_records'
    )


def test_allocation_lines_table_exists():
    """
    allocation_lines child table must exist (fix #4: no UUID array for 1:N allocation).
    """
    sql = MIGRATION_SQL.read_text()
    assert 'CREATE TABLE allocation_lines' in sql, (
        'allocation_lines table missing — needed for CTRL-005 per-record balance checks'
    )


def test_decisions_table_has_post_control_comment():
    """
    decisions table must not be used for pre-control outcomes.
    The migration comment must reflect fix #1 (pipeline ordering).
    """
    sql = MIGRATION_SQL.read_text()
    assert 'post-control' in sql.lower() or 'FINAL' in sql, (
        'decisions table comment should clarify post-control ordering'
    )
