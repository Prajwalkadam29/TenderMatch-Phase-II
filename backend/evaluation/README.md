# TenderMatch — RAGAS Evaluation Suite

## Purpose
Evaluates the quality of the AI explanation pipeline using the RAGAS framework.
These metrics are used in the research paper to validate the system's explainability claims.

## Setup
```bash
pip install ragas datasets sentence-transformers langchain-groq --break-system-packages
```

## Running the Evaluation

### Step 1 — Build the dataset
```bash
python backend/evaluation/ragas_dataset_builder.py
```

### Step 2 — Run RAGAS evaluation  
```bash
python backend/evaluation/run_ragas_evaluation.py
```

### Step 3 — Generate figures
```bash
python backend/evaluation/generate_visualizations.py
```

## Output Files
| File | Description |
|---|---|
| ragas_dataset.json | Ground truth dataset built from match history |
| ragas_results.json | Raw per-sample and aggregate scores |
| latency_results.json | Pipeline stage latency benchmarks |
| figures/fig1_*.pdf | Summary bar chart — use in paper abstract |
| figures/fig2_*.pdf | Violin distributions — use in methodology |
| figures/fig3_*.pdf | Faithfulness vs score scatter — use in results |
| figures/fig4_*.pdf | Metric correlation heatmap — use in results |
| figures/fig5_*.pdf | Score by feedback boxplot — use in results |

## Interpretation Guide
- **Strong performance (Mean >= 0.90):** Suitable for production use
- **Good performance (Mean 0.75-0.89):** Minor improvements recommended
- **Moderate performance (Mean 0.60-0.74):** Retrieval or prompt engineering improvements needed
- **Weak performance (Mean < 0.60):** Significant pipeline changes required before deployment

## Limitations
- Ground truth is derived from human feedback signals, not expert annotation. In this specific run, synthetic signals were derived from `final_score` where no feedback existed.
- Evaluation LLM is the same model used for inference (Groq LLaMA 3.1) — potential self-evaluation bias.
- Dataset size is limited to available matches; expand feedback collection to improve evaluation quality.
- Rate limits on the inference endpoint may require running evaluation on a smaller subset.
