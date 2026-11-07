"""Release the next DeskTrace version as a version license, from installer/changelog.json.

    python installer\\release.py              # build the license of the newest release in the changelog
    python installer\\release.py --check      # only check the version numbers against the levels

Every change has a level:
    5  New feature        an entirely new capability
    4  Major improvement
    3  Improvement
    2  Polish
    1  Fix
A release's number follows from the one before it: with a level-5 change the second digit goes up and the
third goes back to 0 (after x.9 the first digit goes up and the second goes back to 0, so 1.9.x -> 2.0.0);
otherwise only the third digit goes up. Write "version": "next" for a new release and its number is filled
in. Build each release's license right after making its changes: the license packs the program as it is
now (src), together with the changelog up to that release (shown when choosing what to install).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_license as ml  # noqa: E402

CHANGELOG = HERE / 'changelog.json'
OUT = HERE.parent / 'dist' / 'licenses'


def parse(v):
    p = [int(x) for x in v.split('.')] + [0, 0]
    return tuple(p[:3])


def fmt(t):
    return '.'.join(map(str, t))


def bump(prev, level):
    major, minor, patch = prev
    if level >= 5:
        minor, patch = minor + 1, 0
        if minor > 9:
            major, minor = major + 1, 0
    else:
        patch += 1
    return major, minor, patch


def check(releases):
    """Fill in "next" numbers and make sure every number follows from its levels."""
    for i, rel in enumerate(releases):
        if i == 0 or rel.get('legacy'):
            continue  # the base version, and releases from before the levels were introduced
        levels = [c['level'] for c in rel.get('changes', [])]
        if not levels or not all(c in (1, 2, 3, 4, 5) for c in levels):
            sys.exit(f"release {rel.get('version')}: every change needs a level 1-5")
        want = fmt(bump(parse(releases[i - 1]['version']), max(levels)))
        if rel['version'] == 'next':
            rel['version'] = want
        elif fmt(parse(rel['version'])) != want:
            sys.exit(f"release {rel['version']} should be {want} (after {releases[i - 1]['version']}, highest level {max(levels)})")
        for c in rel['changes']:
            if not all(c.get(k) for k in ('en', 'zh')):
                sys.exit(f"release {rel['version']}: every change needs en / zh text")
    return releases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = json.loads(CHANGELOG.read_text('utf-8'))
    releases = check(data['releases'])
    CHANGELOG.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    for r in releases:
        print(f"  {r['version']:8} " + (f"levels {sorted({c['level'] for c in r.get('changes', [])}, reverse=True)}" if r.get('changes') else '(base / legacy)'))
    if a.check:
        return
    rel = releases[-1]
    key = ml.load_key()
    if key['n'] != ml.updates.PUBLIC_KEY['n']:
        sys.exit('updates.py holds a different public key than installer\\keys\\release-key.json')
    upto = [{k: r[k] for k in ('version', 'date', 'changes', 'notes') if k in r}
            for r in releases[1:] if parse(r['version']) <= parse(rel['version'])]
    gone = {f: v for f, v in (data.get('removed_features') or {}).items() if parse(v) <= parse(rel['version'])}
    for r_ in upto:  # changes to a feature removed by this version are not worth reading about any more (2.6.0)
        if 'changes' in r_:
            r_['changes'] = [c for c in r_['changes'] if not (c.get('feature') in gone and parse(gone[c['feature']]) > parse(r_['version']))]
    upto = [r_ for r_ in upto if r_.get('changes') or r_.get('notes') or 'changes' not in r_]  # nothing left: not listed
    out = ml.make_license(rel['version'], data.get('min_version', '1.6'), rel.get('notes') or {}, key,
                          OUT / f"DeskTrace {rel['version']}{ml.updates.EXT}", changelog=upto, removed=gone)
    print(f'built {out}  ({out.stat().st_size / 1024:.0f} KB)')


if __name__ == '__main__':
    main()
