import json
import os
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

matplotlib.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.format': 'pdf'  # vector format for papers
})

def run_visualizations():
    eval_dir = os.path.dirname(__file__)
    results_path = os.path.join(eval_dir, "ragas_results.json")
    dataset_path = os.path.join(eval_dir, "ragas_dataset.json")
    
    if not os.path.exists(results_path):
        print(f"Error: {results_path} not found. Run evaluation first.")
        return
        
    with open(results_path, "r") as f:
        results = json.load(f)
        
    # We also need the final_score and feedback_signal for fig3 and fig5
    # Since they aren't explicitly in ragas_dataset.json as separate flat fields,
    # wait, we can extract them from ground truth or we need to pass them.
    # Let's extract from the dataset or generate mock ones if not found, 
    # but we should get the exact scores from the database via ragas_dataset.
    # Actually, in dataset builder I synthesized feedback signal. Let's re-parse it from ground_truth
    
    with open(dataset_path, "r") as f:
        dataset = json.load(f)
        
    # We will build a dataframe
    records = []
    per_sample_scores = results.get("per_sample_scores", [])
    
    # We need to map metrics correctly as ragas might rename them
    metric_keys = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    
    for i, row in enumerate(dataset):
        if i >= len(per_sample_scores):
            break
            
        score_row = per_sample_scores[i]
        
        question = row["question"]
        gt = row["ground_truth"]
        import re
        m_vendor = re.search(r"vendor (V-EVAL-\d+)", question)
        vendor_id = m_vendor.group(1) if m_vendor else ""
        
        m_score = re.search(r"score of (\d+\.\d)", gt)
        final_score = float(m_score.group(1)) if m_score else 50.0
        
        # Query MongoDB for feedback
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27018/")
        db = client["tendermatch"]
        match_doc = db.match_results.find_one({
            "vendor_profile_id": {"$regex": vendor_id},
            "final_score": {"$gte": final_score - 1, "$lte": final_score + 1}
        })
        
        feedback = "no_feedback"
        if match_doc:
            feedback = match_doc.get("feedback_signal", match_doc.get("match_result", {}).get("feedback_signal", "no_feedback"))
            
        record = {
            "final_score": final_score,
            "feedback_signal": feedback
        }
        
        # add metrics
        for mk in metric_keys:
            # find matching key
            matched_val = 0.0
            for k, v in score_row.items():
                if mk in k.lower() or k.lower().replace("_", "") == mk.replace("_", ""):
                    if v is not None:
                        matched_val = float(v)
                    break
            record[mk] = matched_val
            
        records.append(record)
        
    df = pd.DataFrame(records)
    
    fig_dir = os.path.join(eval_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    
    metrics = results["metrics"]
    dataset_size = len(results.get("results", []))
    
    # Figure 1: Summary Bar Chart
    plt.figure(figsize=(8, 5))
    metric_names = ["Faithfulness", "Answer Relevancy", "Context Precision", "Context Recall"]
    metric_keys = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    
    means = [metrics[k]["mean"] for k in metric_keys]
    stds = [metrics[k]["std"] for k in metric_keys]
    
    colors = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']
    
    bars = plt.bar(metric_names, means, yerr=stds, capsize=5, color=colors, alpha=0.8, edgecolor='black')
    
    plt.ylim(0, 1.05)
    plt.ylabel("Score")
    plt.title(f"TenderMatch RAGAS Evaluation Results (n={dataset_size})")
    
    plt.figtext(0.5, -0.05, f"Error bars represent ±1 standard deviation across {dataset_size} evaluated match pairs.", 
                ha="center", fontsize=10)
    
    plt.savefig(os.path.join(fig_dir, "fig1_ragas_summary_bar.pdf"))
    plt.savefig(os.path.join(fig_dir, "fig1_ragas_summary_bar.png"))
    plt.close()
    
    # Figure 2: Score Distributions Violin
    plt.figure(figsize=(10, 6))
    data_to_plot = [df[mk].dropna() for mk in metric_keys]
    
    parts = plt.violinplot(data_to_plot, showmeans=False, showmedians=True)
    for i, pc in enumerate(parts['bodies']):
        pc.set_facecolor(colors[i])
        pc.set_alpha(0.5)
        
    for i, data in enumerate(data_to_plot):
        x = np.random.normal(i + 1, 0.05, size=len(data))
        plt.scatter(x, data, alpha=0.3, color=colors[i], s=15)
        
    plt.xticks([1, 2, 3, 4], metric_names)
    plt.ylim(0, 1.05)
    plt.ylabel("Score")
    plt.title("Score Distribution per Metric")
    plt.savefig(os.path.join(fig_dir, "fig2_score_distributions_violin.pdf"))
    plt.savefig(os.path.join(fig_dir, "fig2_score_distributions_violin.png"))
    plt.close()
    
    # Figure 3: Faithfulness vs Final Score
    plt.figure(figsize=(8, 6))
    
    feedback_colors = {
        "won": "green",
        "lost": "red",
        "not_relevant": "orange",
        "interested": "blue",
        "submitted": "purple",
        "no_feedback": "gray"
    }
    
    sns.regplot(x="final_score", y="faithfulness", data=df, scatter=False, color="black", line_kws={"alpha":0.5, "linestyle":"--"})
    
    for fb in df['feedback_signal'].unique():
        subset = df[df['feedback_signal'] == fb]
        plt.scatter(subset['final_score'], subset['faithfulness'], 
                   c=feedback_colors.get(fb, "gray"), label=fb, alpha=0.7)
                   
    # Pearson r
    r = df['final_score'].corr(df['faithfulness'])
    from scipy.stats import pearsonr
    try:
        r, p = pearsonr(df['final_score'].dropna(), df['faithfulness'].dropna())
        plt.text(df['final_score'].min(), 0.95, f"r = {r:.2f}\np = {p:.3f}", 
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    except Exception:
        pass
        
    plt.legend(title="Feedback")
    plt.xlabel("Match Final Score (0-100)")
    plt.ylabel("Faithfulness Score")
    plt.title("Faithfulness vs. Match Final Score")
    plt.ylim(-0.05, 1.05)
    plt.savefig(os.path.join(fig_dir, "fig3_faithfulness_vs_final_score.pdf"))
    plt.savefig(os.path.join(fig_dir, "fig3_faithfulness_vs_final_score.png"))
    plt.close()
    
    # Figure 4: Metric Correlation Heatmap
    plt.figure(figsize=(7, 6))
    corr = df[metric_keys].corr()
    
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1,
               xticklabels=metric_names, yticklabels=metric_names)
               
    plt.title("Inter-Metric Correlation Matrix")
    
    # Check if context precision and recall are highly correlated
    try:
        cp_cr_corr = corr.loc['context_precision', 'context_recall']
        if cp_cr_corr > 0.85:
            plt.figtext(0.5, -0.05, "High correlation between Context Precision and Recall may indicate retrieval system consistency.", 
                        ha="center", fontsize=9, style='italic')
    except Exception:
        pass
        
    plt.savefig(os.path.join(fig_dir, "fig4_metric_correlation_heatmap.pdf"))
    plt.savefig(os.path.join(fig_dir, "fig4_metric_correlation_heatmap.png"))
    plt.close()
    
    # Figure 5: Score by Feedback Boxplot
    plt.figure(figsize=(8, 6))
    
    order = ["won", "submitted", "interested", "lost", "not_relevant", "no_feedback"]
    order = [o for o in order if o in df['feedback_signal'].unique()]
    
    sns.boxplot(x="feedback_signal", y="final_score", data=df, order=order, 
               palette=feedback_colors)
    sns.stripplot(x="feedback_signal", y="final_score", data=df, order=order,
                 color="black", alpha=0.3, jitter=True)
                 
    plt.ylabel("Match Final Score")
    plt.xlabel("Feedback Signal")
    plt.title("Match Score Distribution by Outcome Signal")
    
    # Add text annotation if median of won is not meaningfully higher
    try:
        if "won" in df['feedback_signal'].unique() and "not_relevant" in df['feedback_signal'].unique():
            med_won = df[df['feedback_signal'] == 'won']['final_score'].median()
            med_not_rel = df[df['feedback_signal'] == 'not_relevant']['final_score'].median()
            if med_won - med_not_rel < 10:
                plt.figtext(0.5, -0.05, "Note: Score-outcome correlation is weak. Adaptive weight tuning is recommended.", 
                            ha="center", fontsize=10, style='italic', color='red')
    except Exception:
        pass
        
    plt.savefig(os.path.join(fig_dir, "fig5_score_by_feedback_boxplot.pdf"))
    plt.savefig(os.path.join(fig_dir, "fig5_score_by_feedback_boxplot.png"))
    plt.close()
    
    print(f"Figures saved to {fig_dir}/")
    print("  fig1_ragas_summary_bar.pdf")
    print("  fig2_score_distributions_violin.pdf")
    print("  fig3_faithfulness_vs_final_score.pdf")
    print("  fig4_metric_correlation_heatmap.pdf")
    print("  fig5_score_by_feedback_boxplot.pdf")
    print("\nRecommended figure for paper abstract/summary: fig1_ragas_summary_bar.pdf")
    print("Recommended figure for methodology section: fig2_score_distributions_violin.pdf")
    print("Recommended figures for results section: fig3, fig4, fig5")

if __name__ == "__main__":
    run_visualizations()
