"""Label each course review with every theme it raises, check the answer, and store it.

    python pipeline.py --model rules        # keyword rules; needs no AI and no account
    python pipeline.py --limit 10           # the model named by MODEL in .env

Results go to results/labels_<model>.csv. A review that already has a stored label is
never sent again, so re-running continues where the last run stopped and gives the same table.

Connection settings come from .env (see .env.example):
    OPENAI_BASE_URL   the service's address, ending in /v1/
    OPENAI_API_KEY    the service's key
    MODEL             the model (on Azure: the deployment name)
"""
import argparse
import csv
import json
import os
import re
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from dataset import CATEGORIES, DEFINITIONS, MULTI_RULE, load_course_reviews

load_dotenv()

RESULTS = Path("results")
SAMPLE = Path("data/label_200_dataset_labels.json")
FIELDS = [
    "review_id", "themes", "quotes", "problems", "model", "labelled_on",
    "input_tokens", "output_tokens", "seconds",
]

# The fixed instructions every review is sent with.
INSTRUCTIONS = (
    "Label the student course review with the categories it raises.\n"
    + "\n".join(f"- {c}: {DEFINITIONS[c]}" for c in CATEGORIES)
    + f"\n{MULTI_RULE} Do not invent new categories."
)

# The only answer shape the model is allowed to return.
SCHEMA = {
    "type": "object",
    "properties": {
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CATEGORIES},
                    "quote": {"type": "string"},
                },
                "required": ["category", "quote"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["themes"],
    "additionalProperties": False,
}

# Keyword rules: each pattern that matches adds its theme. No AI involved.
RULES = [
    ("Assessment", r"\b(exams?|midterms?|finals?|quiz(?:zes)?|assignments?|grad(?:e|es|ing)|marks?|tests?)\b"),
    ("Difficulty", r"\b(hard|difficult|easy|tough|challenging|brutal|bird)\b"),
    ("Workload", r"\b(workload|time[- ]consuming|hours|lots of work|too much work)\b"),
    ("Learning activity", r"\b(lectures?|tutorials?|labs?|seminars?)\b"),
    ("Course materials", r"\b(textbooks?|notes|slides|readings?)\b"),
    ("Teaching", r"\b(prof|professors?|instructors?|TAs?|teach(?:er|ing))\b"),
    ("Content", r"\b(content|material|topics?|concepts?|learn(?:ed|t)?)\b"),
    ("Overall", r"\b(great|good|bad|worst|best|favou?rite|useless|boring|fun|interesting) (course|class)\b"),
]


def rules_model(text):
    themes = []
    for category, pattern in RULES:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            themes.append({"category": category, "quote": match.group(0)})
    return {"themes": themes or [{"category": "Unclear", "quote": ""}]}


def ai_model(name):
    """A model behind any OpenAI-compatible service, with the answer shape enforced."""
    import openai

    base_url, key = os.getenv("OPENAI_BASE_URL", "").strip(), os.getenv("OPENAI_API_KEY", "").strip()
    if not base_url or not key:
        raise SystemExit("OPENAI_BASE_URL or OPENAI_API_KEY is empty. Copy .env.example to .env and fill it in.")
    client = openai.OpenAI(base_url=base_url, api_key=key, max_retries=5, timeout=120)

    def call(text):
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=name,
                messages=[{"role": "system", "content": INSTRUCTIONS}, {"role": "user", "content": text}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "labels", "schema": SCHEMA, "strict": True},
                },
            )
        except openai.APIConnectionError:
            raise SystemExit(f"Couldn't reach {base_url}. Check the internet connection and OPENAI_BASE_URL in .env.")
        except openai.AuthenticationError:
            raise SystemExit("The service rejected the key. Copy OPENAI_API_KEY into .env again.")
        except openai.NotFoundError:
            raise SystemExit(
                f"No model called '{name}' at {base_url}. Check MODEL in .env "
                "(on Azure, use the deployment name, not the model's name)."
            )
        except (openai.BadRequestError, openai.UnprocessableEntityError) as e:
            detail = f"{e} {e.body}"
            if "response_format" in detail or "json_schema" in detail:
                raise SystemExit(
                    f"'{name}' can't guarantee the answer format. "
                    "Choose a model that supports structured outputs."
                )
            return {"refused": f"the model refused this review: {detail[:200]}"}
        usage = response.usage
        try:
            themes = json.loads(response.choices[0].message.content)["themes"]
        except (TypeError, KeyError, json.JSONDecodeError):
            themes = []  # check() reports an empty answer
        return {
            "themes": themes,
            "input_tokens": usage.prompt_tokens if usage else "",
            "output_tokens": usage.completion_tokens if usage else "",
            "seconds": round(time.perf_counter() - started, 2),
        }
    return call


def _normalise(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def check(themes, text):
    """Return a list of plain-English problems with an answer; empty means it passed."""
    problems = []
    if not themes:
        problems.append("no themes returned (expected at least Unclear)")
    categories = [t["category"] for t in themes]
    for category in sorted({c for c in categories if categories.count(c) > 1}):
        problems.append(f"'{category}' listed more than once")
    if "Unclear" in categories and len(categories) > 1:
        problems.append("Unclear given alongside other themes")
    for t in themes:
        if t["category"] not in CATEGORIES:
            problems.append(f"category '{t['category']}' is not on the list")
        elif t["category"] != "Unclear" and not _normalise(t["quote"]):
            problems.append(f"{t['category']}: no quoted words given")
        elif t["category"] != "Unclear" and _normalise(t["quote"]) not in _normalise(text):
            problems.append(f"{t['category']}: quoted words '{t['quote']}' do not appear in the review")
    return problems


def run(name, model, limit=None):
    reviews = {r["id"]: r["text"] for r in load_course_reviews()}
    sample = [d["id"] for d in json.loads(SAMPLE.read_text(encoding="utf-8"))]
    out = RESULTS / f"labels_{re.sub(r'[^\w.-]', '-', name)}.csv"
    out.parent.mkdir(exist_ok=True)
    done = set()
    if out.exists():
        with out.open(encoding="utf-8", newline="") as f:
            done = {row["review_id"] for row in csv.DictReader(f)}
    todo = [i for i in sample if i not in done][:limit]

    f = writer = None
    for n, review_id in enumerate(todo, 1):
        answer = model(reviews[review_id])
        if "refused" in answer:
            print(f"  {n}/{len(todo)}  {review_id}: not stored, {answer['refused']}. Run again to retry.")
            continue
        if writer is None:  # the file is opened only once there is an answer to save
            f = out.open("a", encoding="utf-8", newline="")
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            if f.tell() == 0:
                writer.writeheader()
        themes = answer.pop("themes")
        writer.writerow({
            **answer,
            "review_id": review_id,
            "themes": "; ".join(str(t["category"]) for t in themes),
            "quotes": json.dumps(themes, ensure_ascii=False),
            "problems": "; ".join(check(themes, reviews[review_id])),
            "model": name,
            "labelled_on": date.today().isoformat(),
        })
        f.flush()  # each label is saved the moment it arrives
        print(f"  {n}/{len(todo)}  {review_id}: {'; '.join(str(t['category']) for t in themes)}")
    if f:
        f.close()
    print(f"{len(todo)} new reviews processed, {len(done)} already stored -> {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.getenv("MODEL", "").strip() or "rules",
                        help="'rules', or a model name (default: MODEL in .env)")
    parser.add_argument("--limit", type=int, help="label at most this many new reviews")
    args = parser.parse_args()
    run(args.model, rules_model if args.model == "rules" else ai_model(args.model), args.limit)
