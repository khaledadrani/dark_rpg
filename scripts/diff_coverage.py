"""Diff coverage: how much of the code a branch CHANGED is exercised by the tests, for lines and for branches (if/else paths).

    make coverage-gate        # = the three steps below
    uv run coverage run -m pytest
    uv run coverage json -o coverage.json
    uv run python scripts/diff_coverage.py --base master --min-lines 80 --min-branches 80

Ported 2026-10-04 from agentnet/scripts/diff_coverage.py (itself from zonepals): branch coverage over every product
file, [tool.coverage.*] in pyproject.toml. The gate is on the changed code only, not on the
whole codebase, so a branch is judged on what it touches. Changed lines come from `git diff` against the merge-base
(committed, staged and unstaged changes; untracked .py files count entirely); tests, scripts, docs and non-Python files
are ignored. Exit status 1 when a threshold is missed (and the uncovered changed lines are listed), 0 otherwise."""
import argparse
import json
import re
import subprocess
import sys

IGNORED_PARTS = ('/tests/', '/scripts/', '/docs/', '/misc/', '/_tickets/', '/notebooks/', '/.venv/')
IGNORED_NAMES = ('conftest.py',)
HUNK = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')


def is_measured(path):
    p = f'/{path}'
    name = path.rsplit('/', 1)[-1]
    return (path.endswith('.py') and not any(part in p for part in IGNORED_PARTS)
            and name not in IGNORED_NAMES and not name.startswith('test_') and not name.endswith('_tests.py') and name != 'tests.py')


def parse_diff(diff_text):
    """{path: set(changed line numbers in the new file)} from `git diff -U0` output."""
    changed, path = {}, None
    for line in diff_text.splitlines():
        if line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') else None
        elif path and (match := HUNK.match(line)):
            start, count = int(match.group(1)), int(match.group(2) if match.group(2) is not None else 1)
            if count:
                changed.setdefault(path, set()).update(range(start, start + count))
    return {p: lines for p, lines in changed.items() if is_measured(p)}


def measure(changed, coverage):
    """Per file: changed statements (covered/uncovered lines) and changed branch points (covered/missed) from a `coverage json` report."""
    result = {}
    for path, lines in sorted(changed.items()):
        data = coverage['files'].get(path)
        if data is None:                                   # never imported by the tests: every changed statement counts as uncovered
            result[path] = {'covered': set(), 'uncovered': set(lines), 'branches_hit': 0, 'branches_missed': 0, 'unmeasured': True}
            continue
        executed, missing = set(data['executed_lines']), set(data['missing_lines'])
        hit = sum(1 for src, _ in data.get('executed_branches', []) if src in lines)
        missed = [(src, dst) for src, dst in data.get('missing_branches', []) if src in lines]
        result[path] = {'covered': lines & executed, 'uncovered': lines & missing, 'branches_hit': hit, 'branches_missed': len(missed),
                        'missed_branches': missed, 'unmeasured': False}
    return result


def percent(part, whole):
    return 100.0 if whole == 0 else 100.0 * part / whole


def summarize(result):
    covered = sum(len(r['covered']) for r in result.values())
    uncovered = sum(len(r['uncovered']) for r in result.values())
    hit = sum(r['branches_hit'] for r in result.values())
    missed = sum(r['branches_missed'] for r in result.values())
    return {'lines': percent(covered, covered + uncovered), 'branches': percent(hit, hit + missed),
            'statements': covered + uncovered, 'branch_points': hit + missed}


def git(*args):
    return subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout


def changed_lines(base):
    merge_base = git('merge-base', base, 'HEAD').strip()
    changed = parse_diff(git('diff', '-U0', '--no-color', merge_base, '--', '*.py'))
    for path in git('ls-files', '--others', '--exclude-standard', '--', '*.py').split():
        if is_measured(path):
            with open(path, encoding='utf-8') as handle:
                changed[path] = set(range(1, len(handle.readlines()) + 1))
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--base', default='master')
    parser.add_argument('--coverage-json', default='coverage.json')
    parser.add_argument('--min-lines', type=float, default=80.0)
    parser.add_argument('--min-branches', type=float, default=80.0)
    args = parser.parse_args(argv)

    with open(args.coverage_json, encoding='utf-8') as handle:
        coverage = json.load(handle)
    result = measure(changed_lines(args.base), coverage)
    totals = summarize(result)

    for path, r in result.items():
        note = ' (not imported by any test)' if r['unmeasured'] else ''
        print(f"{path}: {len(r['covered'])}/{len(r['covered']) + len(r['uncovered'])} changed lines, "
              f"{r['branches_hit']}/{r['branches_hit'] + r['branches_missed']} branches{note}")
        if r['uncovered']:
            print(f"    uncovered lines: {', '.join(map(str, sorted(r['uncovered'])))}")
        for src, dst in r.get('missed_branches', []):
            print(f"    branch not taken: line {src} -> {dst if dst > 0 else 'exit'}")
    print(f"\nChanged code: lines {totals['lines']:.1f}% of {totals['statements']} (min {args.min_lines:.0f}), "
          f"branches {totals['branches']:.1f}% of {totals['branch_points']} (min {args.min_branches:.0f})")
    failed = totals['lines'] < args.min_lines or totals['branches'] < args.min_branches
    print('FAILED: the changed code is under-tested.' if failed else 'OK')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
