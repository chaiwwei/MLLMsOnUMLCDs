# MLLMsOnUMLCDs

> **Performance of Multimodal Large Language Models in Understanding Digital UML Class Diagrams**

This repository contains the datasets, evaluation scripts, prompts, and supplementary materials used in the study investigating how well **Multimodal Large Language Models (MLLMs)** can interpret and reason over **digital UML Class Diagrams (UMLCDs)**.

## 📌 Overview

UML Class Diagrams are a cornerstone of software design, encoding structural relationships, attributes, methods, and constraints. As MLLMs (e.g., GPT-4V, LLaVA, Qwen-VL, Gemini) increasingly handle visual inputs, assessing their ability to "read" technical diagrams like UMLCDs becomes critical—for applications in automated documentation, design validation, and AI-assisted software engineering.

This project provides:

- A curated dataset of digital UML class diagrams (standardized formats, varied complexity)
- A benchmark suite with question-answer pairs targeting structural, behavioral, and semantic understanding
- Evaluation methodology and metrics (accuracy, robustness, error taxonomy)
- Prompt templates and few-shot examples used in experiments
- Analysis scripts and visualization tools

## 📂 Repository Structure

├── dataset/
│ ├── UML class diagrams (PNG)
| ├── groundtruth (json)
├── prompt/
│ └── Prompt.txt prompt template
├── programs/
│ ├── mainv2.0.py # a program to calculate metrics with a given prediction and groundtruth
│ └── run_evaluation.bat # a batch-processing program to run mainv2.0.py
├── resutls/
│ ├── average and standard deviation.csv # Taxonomy of common failure modes
│ └── metrics.csv # the resutls of precision, recall, and F1 score

## 🛠️ Getting Started

### Prerequisites

- Python ≥ 3.9
- `pip install -r requirements.txt` (add this file later; recommend including: `pandas`, `matplotlib`, `torch`, `transformers`, `Pillow`, `openai`, etc.)

### Example: Running Evaluation

```bash
cd evaluation
python runner.py --model gpt-4o --data ../data/diagrams/ --questions ../data/questions.json --output results/gpt4o_results.json

@article{chai2025mllms,
  author    = {Chai, Wei and [Co-authors]},
  title     = {Performance of Multimodal Large Language Models in Understanding Digital UML Class Diagrams},
  journal   = {Submitted to [e.g., IEEE TSE / EMSE]},
  year      = {2025},
  note      = {Preprint: \url{https://arxiv.org/...}}
}
```
