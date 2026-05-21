"""
TenderMatch RAGAS Evaluation Runner
====================================
Operationalization of RAGAS metrics for a procurement matching system:

Faithfulness: Measures whether LLM explanation claims are grounded in the 
retrieved tender context and computed scores. Unfaithful = invented strengths 
or risks not supported by actual scores or tender text.

Answer Relevance: Measures whether the executive summary and recommendation 
are relevant to the specific tender-vendor pair. Irrelevant = generic text 
that could apply to any match.

Context Precision: Of the tender chunks passed to the explanation engine, 
what fraction were actually useful for the scoring decision.

Context Recall: Whether the retrieved chunks contained all information 
necessary for a complete and accurate scoring decision.
"""

import json
import os
import sys
from datetime import datetime, timezone
import numpy as np

# Load env before any imports that might need it
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from datasets import Dataset
import ragas
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings

def run_evaluation():
    dataset_path = os.path.join(os.path.dirname(__file__), "ragas_dataset.json")
    if not os.path.exists(dataset_path):
        print(f"Error: {dataset_path} not found. Run dataset builder first.")
        sys.exit(1)
        
    with open(dataset_path, "r") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} samples from dataset.")
    
    mapped_data = []
    for row in data:
        mapped_data.append({
            "user_input": row["question"],
            "response": row["answer"],
            "retrieved_contexts": row["contexts"],
            "reference": row["ground_truth"],
            "question": row["question"],
            "answer": row["answer"],
            "contexts": row["contexts"],
            "ground_truth": row["ground_truth"]
        })
        
    hf_dataset = Dataset.from_list(mapped_data)
    
    # Configure Groq LLM
    # llama3-8b-8192 is decommissioned, use llama-3.1-8b-instant
    model_name = "llama-3.1-8b-instant"
    llm = ChatGroq(model_name=model_name, temperature=0)
    
    # Needs embeddings for some metrics (Answer Relevancy)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Groq does not support n > 1 in Chat completions. 
    # AnswerRelevancy in Ragas uses n=strictness if strictness > 1
    answer_relevancy.strictness = 1
    
    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    ]
    
    print("Running evaluation... This may take a while depending on the dataset size and rate limits.")
    try:
        results = ragas.evaluate(
            dataset=hf_dataset,
            metrics=metrics,
            llm=llm,
            embeddings=embeddings,
            raise_exceptions=False
        )
    except Exception as e:
        print(f"Evaluation failed: {e}")
        sys.exit(1)
        
    results_df = results.to_pandas()
    
    metrics_stats = {}
    metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    
    cols = results_df.columns
    
    for metric in metric_names:
        match_col = None
        for c in cols:
            if metric in c.lower() or c.lower().replace("_", "") == metric.replace("_", ""):
                match_col = c
                break
                
        if match_col and match_col in results_df:
            valid_scores = results_df[match_col].dropna().tolist()
            if valid_scores:
                metrics_stats[metric] = {
                    "mean": float(np.mean(valid_scores)),
                    "std": float(np.std(valid_scores)),
                    "min": float(np.min(valid_scores)),
                    "max": float(np.max(valid_scores)),
                    "median": float(np.median(valid_scores))
                }
            else:
                metrics_stats[metric] = {
                    "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "median": 0.0
                }
        else:
            metrics_stats[metric] = {
                "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "median": 0.0
            }
            
    overall_mean = np.mean([m["mean"] for m in metrics_stats.values()])
    
    results_df = results_df.replace({np.nan: None})
    per_sample = results_df.to_dict(orient="records")
    
    output_data = {
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_size": len(data),
        "model_used": model_name,
        "metrics": metrics_stats,
        "per_sample_scores": per_sample,
        "score_distribution": {} 
    }
    
    out_path = os.path.join(os.path.dirname(__file__), "ragas_results.json")
    with open(out_path, "w") as f:
        json.dump(output_data, f, indent=2)
        
    print("\n=====================================")
    print("TenderMatch RAGAS Evaluation Results")
    print("=====================================")
    print(f"Dataset: {len(data)} samples evaluated")
    print(f"Model: {model_name}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nMetric              Mean    Std     Min     Median  Max")
    print("----------------------------------------------------------")
    for metric in metric_names:
        stats = metrics_stats[metric]
        name = metric.replace("_", " ").title()
        print(f"{name:<20}{stats['mean']:<8.2f}±{stats['std']:<7.2f}{stats['min']:<8.2f}{stats['median']:<8.2f}{stats['max']:<8.2f}")
    print("----------------------------------------------------------")
    print(f"Overall (mean)      {overall_mean:.2f}")
    print("\nInterpretation:")
    
    if overall_mean >= 0.90:
        print("Strong performance — suitable for production use")
    elif overall_mean >= 0.75:
        print("Good performance — minor improvements recommended")
    elif overall_mean >= 0.60:
        print("Moderate performance — retrieval or prompt engineering improvements needed")
    else:
        print("Weak performance — significant pipeline changes required before deployment")

if __name__ == "__main__":
    run_evaluation()
