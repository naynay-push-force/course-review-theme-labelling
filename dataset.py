"""The EduRABSA course reviews, the list of themes, and how the dataset's labels map onto it."""
import json
from pathlib import Path

RAW = Path("data/raw/2_annotated_dataset_files/Annotation_raw_output")
FILES = ["Train_validation_Merged_ASQE_N4000.json", "DEV_TEST_Merged_ASQE_N2500.json"]

CATEGORIES = [
    "Content", "Assessment", "Difficulty", "Workload", "Learning activity",
    "Course materials", "Teaching", "Overall", "Unclear",
]
THEMES = [c for c in CATEGORIES if c != "Unclear"]
DEFINITIONS = {
    "Content": "what is taught: topics, concepts, material (e.g. 'the topics were interesting')",
    "Assessment": "exams, assignments, grading",
    "Difficulty": "how hard it is",
    "Workload": "amount of work",
    "Learning activity": "lectures, tutorials, labs",
    "Course materials": "textbooks, notes, slides",
    "Teaching": "the instructor or TAs",
    "Overall": "a verdict on the course as a whole rather than on one part of it (e.g. 'great course', 'interesting class', 'avoid this course')",
    "Unclear": "the review doesn't clearly say",
}
MULTI_RULE = (
    "List every category the review says something about: a judgement, complaint, "
    "praise or description, not just a word in passing. Give each category once, with "
    "the exact consecutive words from the review that show it. If no category clearly "
    "applies, return Unclear on its own."
)


def load_course_reviews():
    """Every course review, with its text and the dataset's own category labels."""
    missing = [f for f in FILES if not (RAW / f).exists()]
    if missing:
        raise SystemExit(
            f"Couldn't find {', '.join(missing)} in {RAW}. These files come with the repository: "
            "run the command from the repository's main folder, or download the repository again."
        )
    records = []
    for name in FILES:
        records += json.loads((RAW / name).read_text(encoding="utf-8")).values()
    reviews = [
        {
            "id": r["id"],
            "text": r["text"].strip(),
            "categories": sorted({q["category"] for q in r["Quadruplets"]}),
        }
        for r in records
        if r["type"] == "course review"
    ]
    return sorted(reviews, key=lambda r: int(r["id"]))


def to_our_categories(dataset_categories):
    """Map the dataset's labels (e.g. 'Course - Assessment') onto our nine categories."""
    ours = set()
    for label in dataset_categories:
        entity, attribute = label.split(" - ", 1)
        if entity == "Staff":
            ours.add("Teaching")  # any comment on the instructor is about teaching
        elif attribute == "Technology & tools":
            ours.add("Course materials")
        elif entity == "Course":
            ours.add(attribute)
    return ours or {"Unclear"}
