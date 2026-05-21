"""
run_ragas_final.py
==================
Definitive single-pass RAGAS re-evaluation for the TenderMatch paper.

Steps performed atomically in one run:
  1. Load ragas_dataset.json (30 samples, fixed)
  2. Re-generate ALL answer strings using the NEW tightened explanation
     prompt (negative constraints, max_tokens=450, temperature=0.1)
     via llama-3.3-70b-versatile (same model as explanation_service.py)
  3. Run RAGAS evaluation on the fresh answers
  4. Save ragas_results.json  (overwrites old stale file)
  5. Immediately regenerate all 5 figures from the same JSON
  6. Print definitive metric table

This guarantees the saved JSON and all figures are from the exact same run.
"""

import json, os, sys, asyncio, numpy as np
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH  = os.path.join(EVAL_DIR, "ragas_dataset.json")
RESULTS_PATH  = os.path.join(EVAL_DIR, "ragas_results.json")
FIGURES_DIR   = os.path.join(EVAL_DIR, "figures")

EXPLANATION_MODEL = "llama-3.3-70b-versatile"
RAGAS_MODEL       = "llama-3.1-8b-instant"   # lighter model for RAGAS judge calls

# ── Tightened system prompt (matches explanation_service.py post-fix) ──────────
_SYSTEM_PROMPT = """You are the TenderMatch Procurement Intelligence Engine — a senior AI analyst
specializing in government and enterprise tender evaluation for the Indian market.

YOUR ROLE:
You evaluate whether a specific vendor is genuinely well-suited for a specific tender opportunity.
You produce tight, evidence-based analysis a procurement officer can act on immediately.

CRITICAL CONSTRAINTS — VIOLATIONS WILL INVALIDATE YOUR RESPONSE:
- Do NOT include general procurement advice or explanations of how tendering works.
- Do NOT explain what the tender is about in general terms.
- Do NOT repeat information already visible in the input tables.
- Do NOT pad responses with filler phrases like "It is worth noting that" or "In conclusion".
- ONLY explain why THIS specific vendor matches or does not match THIS specific tender.
- ALL claims must be directly traceable to a number or field in the input data.
- NEVER hallucinate certifications, project names, or financial figures not in the input.

OUTPUT: Answer in 2-4 concise sentences. State the final score, the dominant strength, and the
primary gap (if any). Do not use JSON — plain prose only for this evaluation task."""


async def regenerate_answers(samples: list) -> list:
    """Re-generate answers with the tightened prompt."""
    from groq import AsyncGroq
    import os
    client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
    
    new_samples = []
    for i, row in enumerate(samples):
        # Build a concise user message from the question + context
        ctx_text = "\n".join(f"[Context {j+1}] {c}" for j, c in enumerate(row["contexts"]))
        user_msg = f"{row['question']}\n\nRelevant context:\n{ctx_text}"
        
        try:
            resp = await client.chat.completions.create(
                model=EXPLANATION_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.1,
                max_tokens=450,
                timeout=30,
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [!] Sample {i+1} answer generation failed: {e}. Using original.")
            answer = row["answer"]
        
        new_samples.append({
            "question":     row["question"],
            "answer":       answer,
            "contexts":     row["contexts"],
            "ground_truth": row["ground_truth"],
        })
        print(f"  [{i+1:02d}/{len(samples)}] Answer regenerated ({len(answer)} chars)")
    
    return new_samples


def run_ragas(samples: list) -> dict:
    """Run RAGAS evaluation and return the full results dict."""
    from datasets import Dataset
    import ragas
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from langchain_groq import ChatGroq
    from langchain_community.embeddings import HuggingFaceEmbeddings

    mapped = [{
        "user_input":          s["question"],
        "response":            s["answer"],
        "retrieved_contexts":  s["contexts"],
        "reference":           s["ground_truth"],
        "question":            s["question"],
        "answer":              s["answer"],
        "contexts":            s["contexts"],
        "ground_truth":        s["ground_truth"],
    } for s in samples]

    hf_dataset = Dataset.from_list(mapped)

    llm        = ChatGroq(model_name=RAGAS_MODEL, temperature=0)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    answer_relevancy.strictness = 1

    print("\nRunning RAGAS evaluation (30 samples × 4 metrics)...")
    results = ragas.evaluate(
        dataset=hf_dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=False,
    )

    df = results.to_pandas()
    df = df.replace({float("nan"): None})

    metric_keys = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    metrics_stats = {}
    for mk in metric_keys:
        col = next((c for c in df.columns if mk in c.lower()), None)
        vals = df[col].dropna().tolist() if col else []
        if vals:
            metrics_stats[mk] = {
                "mean":   float(np.mean(vals)),
                "std":    float(np.std(vals)),
                "min":    float(np.min(vals)),
                "max":    float(np.max(vals)),
                "median": float(np.median(vals)),
                "n_non_null": len(vals),
            }
        else:
            metrics_stats[mk] = {"mean": 0.0, "std": 0.0, "min": 0.0,
                                  "max": 0.0, "median": 0.0, "n_non_null": 0}

    return {
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_size":         len(samples),
        "model_used":           RAGAS_MODEL,
        "explanation_model":    EXPLANATION_MODEL,
        "prompt_version":       "v2-tightened-negative-constraints",
        "max_tokens":           450,
        "temperature":          0.1,
        "metrics":              metrics_stats,
        "per_sample_scores":    df.to_dict(orient="records"),
        "score_distribution":   {},
    }


def regenerate_figures(results: dict):
    """Regenerate all 5 figures from the results dict. Overwrites stale PNGs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd

    matplotlib.rcParams.update({
        "font.family": "serif", "font.size": 11,
        "axes.titlesize": 13, "axes.labelsize": 11,
        "xtick.labelsize": 10, "ytick.labelsize": 10,
        "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    })
    os.makedirs(FIGURES_DIR, exist_ok=True)

    metrics   = results["metrics"]
    n         = results["dataset_size"]
    per_s     = results["per_sample_scores"]
    mk_keys   = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    mk_labels = ["Faithfulness", "Answer Relevancy", "Context Precision", "Context Recall"]
    colors    = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]

    # ── Fig 1: Summary bar ────────────────────────────────────────────────────
    means = [metrics[k]["mean"] for k in mk_keys]
    stds  = [metrics[k]["std"]  for k in mk_keys]
    n_nonnull = [metrics[k]["n_non_null"] for k in mk_keys]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(mk_labels, means, yerr=stds, capsize=5,
                  color=colors, alpha=0.85, edgecolor="black")

    for bar, mean, n_nn in zip(bars, means, n_nonnull):
        ax.text(bar.get_x() + bar.get_width()/2, mean + 0.03,
                f"{mean:.3f}\n(n={n_nn})", ha="center", va="bottom", fontsize=9)

    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score")
    ax.set_title(f"TenderMatch RAGAS Evaluation — Definitive Run (n={n})\n"
                 f"Prompt: v2 (tightened constraints, max_tokens=450)  |  "
                 f"Explanation: {results['explanation_model']}")
    ax.axhline(0.75, color="grey", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.text(3.5, 0.76, "Target 0.75", fontsize=8, color="grey")

    fig.text(0.5, -0.04,
             f"Error bars = ±1 SD. n values = non-null samples per metric (RAGAS skips some due to context structure).",
             ha="center", fontsize=9, style="italic")
    plt.tight_layout()
    for ext in ("pdf", "png"):
        plt.savefig(os.path.join(FIGURES_DIR, f"fig1_ragas_summary_bar.{ext}"),
                    bbox_inches="tight")
    plt.close()
    print("  ✓ fig1_ragas_summary_bar")

    # ── Fig 2: Violin distributions ───────────────────────────────────────────
    df = pd.DataFrame(per_s)
    fig, ax = plt.subplots(figsize=(10, 6))
    data_to_plot = [df[mk].dropna().tolist() for mk in mk_keys]

    parts = ax.violinplot(data_to_plot, showmeans=False, showmedians=True)
    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(colors[i])
        pc.set_alpha(0.5)
    for i, data in enumerate(data_to_plot):
        x = np.random.normal(i + 1, 0.05, size=len(data))
        ax.scatter(x, data, alpha=0.4, color=colors[i], s=18)

    ax.set_xticks([1, 2, 3, 4])
    ax.set_xticklabels(mk_labels)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Score")
    ax.set_title("Per-Sample Score Distribution per Metric (Definitive Run)")
    plt.tight_layout()
    for ext in ("pdf", "png"):
        plt.savefig(os.path.join(FIGURES_DIR, f"fig2_score_distributions_violin.{ext}"),
                    bbox_inches="tight")
    plt.close()
    print("  ✓ fig2_score_distributions_violin")

    # ── Fig 3: Faithfulness vs final score ────────────────────────────────────
    # Extract final_score from ground_truth string
    import re
    scores_f, faithful_v = [], []
    for row in per_s:
        gt = row.get("ground_truth") or row.get("reference", "")
        m = re.search(r"score of (\d+\.?\d*)", str(gt))
        if m and row.get("faithfulness") is not None:
            scores_f.append(float(m.group(1)))
            faithful_v.append(float(row["faithfulness"]))

    fig, ax = plt.subplots(figsize=(8, 6))
    if scores_f:
        ax.scatter(scores_f, faithful_v, alpha=0.7, color="#4C72B0", s=50)
        try:
            from scipy.stats import pearsonr
            r, p = pearsonr(scores_f, faithful_v)
            ax.text(min(scores_f), 0.95, f"r = {r:.2f}\np = {p:.3f}",
                    bbox=dict(facecolor="white", alpha=0.8, edgecolor="none"), fontsize=9)
        except Exception:
            pass
    ax.set_xlabel("Match Final Score (0–100)")
    ax.set_ylabel("Faithfulness Score")
    ax.set_ylim(-0.05, 1.1)
    ax.set_title("Faithfulness vs. Match Final Score")
    plt.tight_layout()
    for ext in ("pdf", "png"):
        plt.savefig(os.path.join(FIGURES_DIR, f"fig3_faithfulness_vs_final_score.{ext}"),
                    bbox_inches="tight")
    plt.close()
    print("  ✓ fig3_faithfulness_vs_final_score")

    # ── Fig 4: Correlation heatmap ────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 6))
    corr = df[mk_keys].corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm",
                vmin=-1, vmax=1,
                xticklabels=mk_labels, yticklabels=mk_labels, ax=ax)
    ax.set_title("Inter-Metric Correlation Matrix (Definitive Run)")
    plt.tight_layout()
    for ext in ("pdf", "png"):
        plt.savefig(os.path.join(FIGURES_DIR, f"fig4_metric_correlation_heatmap.{ext}"),
                    bbox_inches="tight")
    plt.close()
    print("  ✓ fig4_metric_correlation_heatmap")

    # ── Fig 5: Score by feedback ──────────────────────────────────────────────
    # final_score and feedback_signal not guaranteed in per_sample; build from ground_truth
    fb_data = []
    for row in per_s:
        gt = row.get("ground_truth") or row.get("reference", "")
        m = re.search(r"score of (\d+\.?\d*)", str(gt))
        fs = float(m.group(1)) if m else None
        fb_data.append({"final_score": fs, "feedback_signal": "no_feedback"})

    df_fb = pd.DataFrame(fb_data).dropna()
    if not df_fb.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.boxplot(x="feedback_signal", y="final_score", data=df_fb, ax=ax,
                    palette={"no_feedback": "#4C72B0"})
        ax.set_ylabel("Match Final Score")
        ax.set_xlabel("Feedback Signal")
        ax.set_title("Match Score Distribution (Definitive Run)")
        plt.tight_layout()
        for ext in ("pdf", "png"):
            plt.savefig(os.path.join(FIGURES_DIR, f"fig5_score_by_feedback_boxplot.{ext}"),
                        bbox_inches="tight")
        plt.close()
    print("  ✓ fig5_score_by_feedback_boxplot")


def print_table(results: dict):
    metrics   = results["metrics"]
    mk_keys   = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    mk_labels = ["Faithfulness", "Answer Relevancy", "Context Precision", "Context Recall"]

    print()
    print("=" * 72)
    print("DEFINITIVE RAGAS RESULTS — TenderMatch Phase II")
    print("=" * 72)
    print(f"  Timestamp        : {results['evaluation_timestamp']}")
    print(f"  Explanation model: {results['explanation_model']}  (max_tokens=450, T=0.1)")
    print(f"  Judge model      : {results['model_used']}")
    print(f"  Prompt version   : {results['prompt_version']}")
    print(f"  Dataset          : {results['dataset_size']} samples (fixed ragas_dataset.json)")
    print()
    print(f"  {'Metric':<22} {'Mean':>6}  {'Std':>6}  {'Min':>6}  {'Median':>7}  {'Max':>6}  {'n':>5}")
    print("  " + "-" * 65)
    for mk, label in zip(mk_keys, mk_labels):
        s = metrics[mk]
        print(f"  {label:<22} {s['mean']:>6.3f}  {s['std']:>6.3f}  {s['min']:>6.3f}  "
              f"{s['median']:>7.3f}  {s['max']:>6.3f}  {s['n_non_null']:>5}")
    print()
    overall = np.mean([metrics[k]["mean"] for k in mk_keys])
    print(f"  Overall mean (4 metrics): {overall:.3f}")
    print()
    ar = metrics["answer_relevancy"]["mean"]
    target = 0.75
    if ar >= target:
        print(f"  ✓ Answer Relevancy {ar:.3f} MEETS target ≥{target}")
    else:
        print(f"  ✗ Answer Relevancy {ar:.3f} BELOW target ≥{target}")
    print("=" * 72)


async def main():
    print("Loading dataset...")
    with open(DATASET_PATH) as f:
        samples = json.load(f)
    print(f"  {len(samples)} samples loaded.")

    print(f"\nStep 1/3 — Regenerating answers with tightened prompt ({EXPLANATION_MODEL})...")
    fresh_samples = await regenerate_answers(samples)

    print("\nStep 2/3 — Running RAGAS evaluation...")
    results = run_ragas(fresh_samples)

    print(f"\nStep 3/3 — Saving results and regenerating figures...")
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  ✓ ragas_results.json saved")

    regenerate_figures(results)
    print(f"  ✓ All figures regenerated in {FIGURES_DIR}/")

    print_table(results)


if __name__ == "__main__":
    asyncio.run(main())
