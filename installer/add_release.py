"""Append a release to changelog.json and build its license.

    python installer\\add_release.py <release.json>

release.json: {"changes": [{"level": 1-5, "en": "...", "zh": "...", "de": "..."}, ...]}  (its version is
worked out from the levels by release.py)."""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
rel = json.loads(Path(sys.argv[1]).read_text('utf-8'))
data = json.loads((HERE / 'changelog.json').read_text('utf-8'))
data['releases'].append({'version': 'next', 'date': time.strftime('%Y-%m-%d'), 'changes': rel['changes']})
(HERE / 'changelog.json').write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', 'utf-8')
sys.exit(subprocess.run([sys.executable, str(HERE / 'release.py')]).returncode)
