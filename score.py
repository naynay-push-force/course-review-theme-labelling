"""Compare a model's stored labels with the labels the dataset's researchers gave by hand.

    python score.py --model rules
    python score.py --model grok-4.7

A review's labels are a set of themes (Unclear counts as no themes).
- exact match: the two sets are identical
- overlap: themes both named / themes either named (100% when both say Unclear)
"""
import argparse
import csv
import json
import re
from pathlib import Path

from dataset import THEMES, to_our_categories

parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True, help="e.g. rules, gpt-5-mini, grok-4.7")
args = parser.parse_args()

path = Path("results") / f"labels_{re.sub(r'[^\w.-]', '-', args.model)}.csv"
if not path.exists():
    raise SystemExit(f"No stored labels at {path}. Run first: python pipeline.py --model {args.model}")
with path.open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))
# Only themes on the list count; anything else was already flagged by the checks.
model = {r["review_id"]: {t.strip() for t in r["themes"].split(";")} & set(THEMES) for r in rows}

sample = json.loads(Path("data/label_200_dataset_labels.json").read_text(encoding="utf-8"))
humans = {d["id"]: to_our_categories(d["categories"]) - {"Unclear"} for d in sample}

ids = [i for i in model if i in humans]
n = len(ids)
if n == 0:
    raise SystemExit(f"{path} has no labelled reviews yet.")
exact = sum(model[i] == humans[i] for i in ids)
overlap = sum(len(model[i] & humans[i]) / len(model[i] | humans[i]) if model[i] | humans[i] else 1 for i in ids)

print(f"{args.model}: {n} reviews, {sum(1 for r in rows if r['problems'])} flagged by the checks")
print(f"  exact match:     {exact}/{n} = {100 * exact / n:.0f}%")
print(f"  average overlap: {100 * overlap / n:.0f}%")
print(f"\n  {'theme':<18}{'model':>7}{'humans':>8}{'both':>6}")
for t in THEMES:
    a = sum(t in model[i] for i in ids)
    b = sum(t in humans[i] for i in ids)
    both = sum(t in model[i] and t in humans[i] for i in ids)
    print(f"  {t:<18}{a:>7}{b:>8}{both:>6}")
