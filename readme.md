# High-Fidelity 3-Column Merge Workspace

A (Vibe coded, credit to Google Gemini) zero-dependency Python utility that generates a completely standalone, highly interactive 3-column HTML suite to compare, review, and merge text document modifications side-by-side.

![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-none-green)

## ✨ Features

* **3-Column Workspace:** View the original text (left), your active merge space (center), and the modified text (right) concurrently.
* **Intelligent Line Tracking:** Automatically matches modified lines while isolating raw structural additions or deletions.
* **Intra-line Diffing:** Character-level sequence analysis highlights precise internal additions and deletions inline.
* **Live "Undo" Engine:** Misclicked? Revert any merge decision instantly with the `↩` undo button to bring back the pending state.
* **Dynamic Line Numbering:** The center column maps out your output document's actual line count in real-time as decisions are accepted or omitted.
* **Context Collapsing:** Collapses identical matching blocks into neat, expandible accordions to focus only on where the real changes happen.
* **Fully Standalone Output:** Generates a single, lightweight HTML file containing all data and logic. Run it locally or air-gapped without external CDNs or network calls.

---

## 🚀 Quick Start

### Prerequisites
* **Python 3.6+** (Uses standard libraries only —no `pip install` required!)
* Any modern web browser.

### Running the Generator
Clone this repository and run the script against your two target files:

```bash
python diffGen.py path/to/original.txt path/to/modified.txt -o merge_workspace.html

## 🛠️ Argument Layout

| Argument | Long Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `file1` | *Positional* | Path to the base/original document. | *Required* |
| `file2` | *Positional* | Path to the revised/modified document. | *Required* |
| `-o` | `--output` | The output path for the interactive HTML suite. | `docCompare.html` |


## 🖥️ Using the Interactive Workspace

Once the HTML workspace is generated, double-click to open it in your browser:

1. **Review and Filter:** Use the **Context Lines** input at the top to adjust how many unchanged buffer lines display around modifications. Click **Apply Window** to update the layout.
2. **Accept Changes:** Click `➔` from the left panel to take the original line, or `⬅` from the right panel to take the modified line.
3. **Omit Lines:** Click `∅` in the center workspace to explicitly drop an added/removed line from the final document.
4. **Revert Actions:** Click `↩` in the center workspace to undo any merge decision or omission and instantly reset the line back to pending.
5. **Export File:** When all changes are resolved, click **💾 Save Merged File** to download your clean, consolidated text file.

---