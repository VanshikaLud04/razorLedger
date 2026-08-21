import ast
import pathlib
import re
import pytest

def test_matcher_cannot_import_truth_module():
    app_dir = pathlib.Path('/Users/vanshikaludhani/Desktop/razorpay/razorLedger/app')
    if not app_dir.exists():
        return
    violations = []
    for py_file in app_dir.rglob('*.py'):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if 'generator.truth' in alias.name or 'truth' in alias.name:
                        violations.append((str(py_file), alias.name))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if 'generator' in module and 'truth' in module:
                    violations.append((str(py_file), module))
                if module == 'generator' and any(a.name == 'truth' for a in node.names):
                    violations.append((str(py_file), 'from generator import truth'))
    assert violations == [], f'Matcher imports truth module: {violations}'

def test_ground_truth_group_id_not_in_source_records_schema():
    sql_path = pathlib.Path('/Users/vanshikaludhani/Desktop/razorpay/razorLedger/migrations/001_initial.sql')
    if not sql_path.exists():
        return
    sql = sql_path.read_text()
    table_match = re.search(r'CREATE TABLE source_records.*?;\n?', sql, re.DOTALL)
    assert table_match, 'source_records table not found in migration'
    table_def = table_match.group(0)
    assert 'ground_truth_group_id' not in table_def
