# Course review theme labelling

This labels public student course reviews with themes from a fixed list: Content, Assessment, Difficulty, Workload, Learning activity, Course materials, Teaching, Overall and Unclear. Each theme must come with the exact words from the review that show it, and a check confirms those words really appear. Every answer is saved, so running it again gives the same table, and the labels are then compared with labels that researchers gave by hand.

Why not just ask a chatbot for "the main themes"? Because you get a different answer every time, with themes it made up and no way to check them. A fixed list, quoted evidence and saved answers make the result consistent and checkable.

There are two ways to try it: **Path A** needs nothing installed, **Path B** runs the full version.

## Path A: no installs (Copilot Chat or any chatbot)

1. Open a **new** chat.
2. Paste this prompt:

   ```
   Classify each review into exactly one of these categories:
   Content (what the course covers), Assessment (exams, assignments, grading), Difficulty (how hard it is), Workload (amount of work), Learning activity (lectures, tutorials, labs), Course materials (textbooks, notes, slides), Teaching (the instructor or TAs), Overall (general verdict only), Unclear (the review doesn't clearly say).
   If a review covers several, choose the one it says most about. If it doesn't clearly fit, use Unclear. Do not invent new categories.
   Return a table with: review number | category | the exact words you relied on. Then give a count per category.
   ```

3. Below it, paste the 40 reviews from [data/copilot_test_40.txt](data/copilot_test_40.txt) and send.
4. Copy the table into Excel and **count the categories yourself**. Don't trust the chatbot's own count: it was wrong in all five test runs.
5. To see how consistent it is, repeat in a new chat each time and compare.

In five fresh chats, 36 of the 40 reviews got the same label every time. The 4 that changed were each about two things.

## Path B: run the pipeline (needs Python)

The commands below are typed into a terminal: **Terminal** on macOS, **PowerShell** on Windows.

1. **Install Python** 3.10 or newer from [python.org](https://www.python.org/downloads/). On Windows, tick *"Add python.exe to PATH"* in the installer.
2. **Download this repository**: the green **Code** button at the top of this page, then **Download ZIP**. Unzip it.
3. **Open a terminal in the unzipped folder.** Windows: open the folder in File Explorer, right-click an empty space, *Open in Terminal*. macOS: open Terminal, type `cd ` (with a space), drag the folder into the window, press Enter.
4. **Create a virtual environment** (a private folder for this project's packages) and switch to it:

   | Windows | macOS |
   |---|---|
   | `py -m venv .venv` | `python3 -m venv .venv` |
   | `.venv\Scripts\activate` | `source .venv/bin/activate` |

   Your prompt now starts with `(.venv)`. If Windows says running scripts is disabled, run `Set-ExecutionPolicy -Scope Process Bypass` (it lasts until you close the window) and try again.
5. **Install the packages:**

   ```
   pip install -r requirements.txt
   ```

6. **Run the keyword rules** first. They use no AI and need no account: each theme is found by searching for words like "exam" or "textbook".

   ```
   python pipeline.py --model rules
   ```

   This labels a sample of 200 reviews and saves them to `results/labels_rules.csv`, which opens in Excel. The `quotes` column shows the words behind each theme, and `problems` lists anything the checks caught.
7. **Score it** against the researchers' labels:

   ```
   python score.py --model rules
   ```

   This prints how often the two agree exactly, the average overlap, and how many reviews each side gave each theme.

The results from the talk's two AI models are already in `results/`, so you can score them without an account:

```
python score.py --model grok-4.7
python score.py --model gpt-5-mini
```

## Connecting a model

Any service that speaks the OpenAI API and supports *structured outputs* (forcing the answer into a set format) works: Azure AI Foundry, OpenAI, or a model running on your own computer with [Ollama](https://ollama.com). The talk used gpt-5-mini and grok-4.7 on Azure AI Foundry.

With Azure AI Foundry:

1. **Set a budget alert first**, so you hear about costs before they surprise you: [create a budget](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets).
2. [Create a Foundry resource](https://learn.microsoft.com/en-us/azure/foundry-classic/openai/how-to/create-resource) and [deploy a model](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/deploy-foundry-models), for example gpt-5-mini.
3. Copy `.env.example` to a new file called `.env` and fill in the three lines. The comments in it say where each value is in the Azure portal.
4. Try 10 reviews, then score them:

   ```
   python pipeline.py --limit 10
   python score.py --model <your MODEL value>
   ```

   Run the first command again without `--limit` to do the rest. Reviews already saved are never sent again, so stopping and restarting is safe.

If something goes wrong, the error message says what to fix.

## Public data only

Never put real student or staff data through a personal account or subscription. Use your organisation's approved tools.

## Data source and licence

The reviews come from **EduRABSA**, a set of 6,500 public student reviews (University of Waterloo course reviews, plus teacher and university reviews from other sources), each labelled by hand by researchers. This project uses the course reviews only.

> Yan Cathy Hua, Paul Denny, Jörg Wicker and Katerina Taskova. *EduRABSA: An Education Review Dataset for Aspect-based Sentiment Analysis Tasks.* 2025. [arXiv:2508.17008](https://arxiv.org/abs/2508.17008). Dataset: [github.com/yhua219/edurabsa_dataset_and_annotation_tool](https://github.com/yhua219/edurabsa_dataset_and_annotation_tool), [doi:10.5281/zenodo.16935017](https://doi.org/10.5281/zenodo.16935017).

- **Data:** everything in `data/`, and the review quotes in `results/`, is under the dataset's licence, [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) ([data/raw/LICENSE.txt](data/raw/LICENSE.txt)): you may share and adapt it for non-commercial purposes, with credit, under the same licence. The two JSON files in `data/raw/` are unmodified. `data/label_200_dataset_labels.json` (the 200-review sample and its labels) and `data/copilot_test_40.txt` (40 review texts) are extracts from them.
- **Code:** MIT, see [LICENSE](LICENSE).
