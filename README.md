# DigitalFish – The Digital Ichthyologist

> **Evolutionary Code Analyst**: Treats a Git repository as a digital ecosystem,
> tracking the survival, mutation, and extinction of *Digital Fish* (functions and
> classes) through the dimension of time (Git commits).

---

## The Metaphor

| Concept | Meaning |
|---|---|
| **Fish** | A discrete code block (function or class) |
| **DNA** | The source text within that block |
| **The Current** | The progression of Git commits |
| **Survival** | A fish survives if it remains similar enough and large enough |
| **Extinction** | Deletion or refactoring beyond recognition |
| **Speciation** | Copying a fish and modifying it into a distinct function |
| **Lazarus Event** | Code deleted and later reintroduced |

---

## Configuration

| Parameter | Symbol | Default | Description |
|---|---|---|---|
| Size threshold | σ | 5 lines | Minimum meaningful lines; smaller blocks are "plankton" |
| Similarity threshold | λ | 0.7 | Minimum fuzzy-match ratio for identity to be preserved |
| Similarity method | – | levenshtein | Algorithm used to compare fish DNA (see below) |

### Similarity Methods

The `--similarity-method` flag (or `similarity_method` in the Python API) selects the
algorithm used to measure how similar two code blocks are.  All methods return a
value in **[0, 1]** where **1** means identical.

| Method | Description | Best for |
|---|---|---|
| `levenshtein` | Edit-distance similarity via [RapidFuzz](https://github.com/maxbachmann/RapidFuzz). Measures the minimum number of single-character edits needed to transform one string into the other, normalised to [0, 1]. | General-purpose; sensitive to small, localised edits such as variable renames or single-line fixes. |
| `hamming` | Positional character-by-character comparison (shorter string padded with nulls). Counts the number of positions where corresponding characters differ, normalised by total length. | Detecting single-character substitutions in blocks of roughly equal length. |
| `jaccard` | Set-based overlap of whitespace-delimited tokens. Computes `|A ∩ B| / |A ∪ B|` over token sets. | Catching structural rewrites where the same tokens appear but in a different order. |
| `cosine` | Cosine similarity over token-frequency vectors. Measures the cosine of the angle between two token-count vectors. | Comparing blocks that share vocabulary but differ in token frequency (e.g. duplicated logic). |

---

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

Then run the digital ichthyologist:

```bash
digital-ichthyologist /path/to/repo
```

### Dependencies

- **PyDriller** – Git repository traversal
- **RapidFuzz** – High-performance fuzzy string matching
- **pandas** – Longitudinal data storage (optional reporting)

---

## Usage

### Command-line

```bash
# Analyse a local repository (text report)
digital-ichthyologist /path/to/repo

# Analyse a remote repository with custom thresholds
digital-ichthyologist https://github.com/user/repo \
    --similarity-threshold 0.8 \
    --size-threshold 10 \
    --top-n 30

# Use a different similarity method
digital-ichthyologist /path/to/repo --similarity-method jaccard
digital-ichthyologist /path/to/repo --similarity-method cosine --similarity-threshold 0.6

# JSON output to a file
digital-ichthyologist /path/to/repo --output json --out-file report.json

# Interactive HTML dashboard (Vita)
digital-ichthyologist /path/to/repo --output vita
digital-ichthyologist /path/to/repo --output vita --out-file dashboard.html

# Analyse a specific branch and commit range
digital-ichthyologist /path/to/repo \
    --branch main \
    --from-commit abc123 \
    --to-commit def456
```

### Python API

```python
from digital_ichthyologist import Analyzer, Reporter

# Run the analysis
analyzer = Analyzer(
    repo_path="/path/to/repo",
    similarity_threshold=0.7,
    size_threshold=5,
    similarity_method="levenshtein",   # or "hamming", "jaccard", "cosine"
)
population = analyzer.run()

# Generate reports
reporter = Reporter(population, top_n=20)
print(reporter.survival_heatmap())
print(reporter.lazarus_report())
print(reporter.ecosystem_health(total_commits=len(set(
    h for f in population for h in f.commit_hashes
))))

# Export to JSON
with open("population.json", "w") as fh:
    fh.write(reporter.to_json())
```

---

## Output Goals

### 1. Survival Heatmap
A ranked ASCII table showing which code blocks are *ancient* (highly stable)
versus *volatile* (short-lived), with a bar chart of relative age and
cumulative mutation rate.

```
=== Survival Heatmap ===
Fish Name                                  Age  Stability              Mut.Rate  Status
------------------------------------------------------------------------------------------
process_data                                47  [████████████████████]    0.312  alive
parse_config                                39  [████████████████░░░░]    0.089  alive
_legacy_handler                             12  [█████░░░░░░░░░░░░░░░]    1.204  extinct
```

### 2. The Lazarus Report
Identifies code deleted and later reintroduced.

```
=== The Lazarus Report ===
Fish Name                                Resurrections    Age  Status
------------------------------------------------------------------------
validate_token                                       3     28  alive
_compat_shim                                         1      4  extinct
```

### 3. Ecosystem Health
Births-per-100-commits vs extinctions-per-100-commits ratio to measure
overall project stability.

```
=== Ecosystem Health Report ===

  Commits analysed        : 250
  Total fish (ever)        : 84
  Currently alive          : 61
  Extinct                  : 23
  Lazarus events           : 4

  Births per 100 commits   : 33.6
  Extinctions per 100      : 9.2
  Survival ratio           : 72.6%

  Avg age (commits)        : 18.4
  Avg mutation rate        : 0.231
```

### 4. Vita – Interactive HTML Dashboard

A self-contained HTML page with interactive charts and sortable tables
visualising all ecosystem metrics.  Generated with `--output vita`.

The dashboard includes:
- **Ecosystem Health** summary stat cards
- **Population Status** doughnut chart (alive vs extinct)
- **Age Distribution** histogram
- **Mutation Rate vs Age** scatter plot
- **Lazarus Events** horizontal bar chart
- **Survival Heatmap** table with stability bars
- **All Fish** sortable detail table

---

## Project Structure

```
digital_ichthyologist/
├── __init__.py       # Public API
├── fish.py           # DigitalFish model
├── extractor.py      # AST-based code block extractor
├── analyzer.py       # Survival analysis engine
├── reporter.py       # Report generators
├── similarity.py     # Similarity metrics (levenshtein, hamming, jaccard, cosine)
├── vita.py           # Interactive HTML dashboard (Vita)
└── cli.py            # Command-line interface
tests/
├── test_fish.py
├── test_extractor.py
├── test_analyzer.py
├── test_reporter.py
└── test_vita.py
```

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

