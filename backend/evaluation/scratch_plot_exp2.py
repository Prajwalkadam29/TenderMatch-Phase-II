import asyncio
import os
import sys
import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import get_db, connect_to_mongo, close_mongo_connection

async def main():
    data_dir = os.path.join(os.path.dirname(__file__), "results")
    figs_dir = os.path.join(os.path.dirname(__file__), "figures")
    os.makedirs(figs_dir, exist_ok=True)
    
    with open(os.path.join(data_dir, "exp2_matching_results.json"), "r") as f:
        data = json.load(f)
        
    vendors = data["vendors"]
    
    # --- Figure 1: Hard Filter Breakdown ---
    plt.figure(figsize=(10, 6))
    vendor_names = [v["vendor_id"] for v in vendors]
    passed = [v["hard_filter_pass"] for v in vendors]
    failed = [v["hard_filter_fail"] for v in vendors]
    
    x = np.arange(len(vendors))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(12, 6))
    rects1 = ax.bar(x - width/2, passed, width, label='Passed', color='#2ca02c')
    rects2 = ax.bar(x + width/2, failed, width, label='Failed', color='#d62728')
    
    ax.set_ylabel('Number of Tenders')
    ax.set_title('Hard Filter Results by Vendor')
    ax.set_xticks(x)
    ax.set_xticklabels(vendor_names, rotation=45, ha="right")
    ax.legend()
    
    fig.tight_layout()
    plt.savefig(os.path.join(figs_dir, "fig_matching_hard_filter_breakdown.pdf"))
    plt.close()
    
    # --- Figure 2: Precision at K ---
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(vendors))
    width = 0.25
    
    p3, p5, p10 = [], [], []
    has_matches = []
    
    for v in vendors:
        pass_count = v["hard_filter_pass"]
        if pass_count == 0:
            p3.append(0); p5.append(0); p10.append(0)
            has_matches.append(False)
        else:
            has_matches.append(True)
            p3.append(min(pass_count, 3) / 3.0)
            p5.append(min(pass_count, 5) / 5.0)
            p10.append(min(pass_count, 10) / 10.0)
            
    rects1 = ax.bar(x - width, p3, width, label='P@3', color='#1f77b4')
    rects2 = ax.bar(x, p5, width, label='P@5', color='#ff7f0e')
    rects3 = ax.bar(x + width, p10, width, label='P@10', color='#2ca02c')
    
    for i, has_match in enumerate(has_matches):
        if not has_match:
            ax.bar(x[i] - width, 1.0, width, color='lightgray', hatch='//', edgecolor='gray')
            ax.bar(x[i], 1.0, width, color='lightgray', hatch='//', edgecolor='gray')
            ax.bar(x[i] + width, 1.0, width, color='lightgray', hatch='//', edgecolor='gray')
            ax.text(x[i], 0.5, 'No passed\nmatches', ha='center', va='center', rotation=90, fontsize=8, color='black')
            
    ax.set_ylabel('Precision')
    ax.set_title('Precision at K by Vendor')
    ax.set_xticks(x)
    ax.set_xticklabels(vendor_names, rotation=45, ha="right")
    ax.set_ylim(0, 1.1)
    ax.legend(loc='upper right')
    
    fig.tight_layout()
    plt.savefig(os.path.join(figs_dir, "fig_matching_precision_at_k.pdf"))
    plt.close()
    
    # --- Figure 3: Score Distribution ---
    await connect_to_mongo()
    db = get_db()
    
    all_scores = []
    passed_scores = []
    
    matches_cursor = db.match_results.find({})
    matches = await matches_cursor.to_list(length=2000)
    
    for doc in matches:
        mr = doc.get("match_result", {})
        hfr = mr.get("hard_filter_results", {})
        ws = mr.get("weighted_score", {})
        
        score = ws.get("final_score", 0)
        passed = hfr.get("overall_pass", False)
        
        if passed:
            all_scores.append(score)
            passed_scores.append(score)
        else:
            all_scores.append(0)
            
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Left Panel: All 500 pairs
    sns.histplot(all_scores, bins=20, ax=ax1, color='#1f77b4', kde=False)
    ax1.set_title(f'Score Distribution (All {len(all_scores)} Pairs)')
    ax1.set_xlabel('Match Score')
    ax1.set_ylabel('Frequency')
    
    # Right Panel: Only Passed Pairs
    sns.histplot(passed_scores, bins=15, ax=ax2, color='#2ca02c', kde=True)
    ax2.set_title(f'Score Distribution (Passed {len(passed_scores)} Pairs)')
    ax2.set_xlabel('Match Score')
    ax2.set_ylabel('Frequency')
    
    fig.tight_layout()
    plt.savefig(os.path.join(figs_dir, "fig_matching_score_distribution.pdf"))
    plt.close()
    
    await close_mongo_connection()
    print("Generated all 3 figures.")

if __name__ == "__main__":
    asyncio.run(main())
