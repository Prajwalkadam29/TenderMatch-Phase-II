"""
scratch_audit_ragas.py
Audits ragas_results.json to explain the figure vs table discrepancy.
"""
import json, os, numpy as np

eval_dir = os.path.dirname(os.path.abspath(__file__))
results_path = os.path.join(eval_dir, "ragas_results.json")

with open(results_path) as f:
    data = json.load(f)

print("=" * 60)
print("SOURCE FILE: ragas_results.json")
print("=" * 60)
print(f"  Timestamp : {data['evaluation_timestamp']}")
print(f"  Model     : {data['model_used']}")
print(f"  Dataset   : {data['dataset_size']} rows declared")
print(f"  Per-sample: {len(data['per_sample_scores'])} rows stored")
print()

metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
print(f"{'Metric':<22} {'Stored mean':>12} {'Non-null n':>10} {'Recomputed mean':>16}")
print("-" * 65)

for mk in metrics:
    stored = data["metrics"].get(mk, {})
    stored_mean = stored.get("mean", 0.0)

    vals = [s[mk] for s in data["per_sample_scores"] if s.get(mk) is not None]
    recomputed = float(np.mean(vals)) if vals else 0.0
    print(f"  {mk:<20} {stored_mean:>12.4f} {len(vals):>10}   {recomputed:>14.4f}")

print()
print("DISCREPANCY CHECK:")
print("  Table in report uses stored 'metrics.mean' from this file.")
print("  Figure (fig1) also uses 'metrics.mean' from this file.")
print()
print("  If figure shows DIFFERENT values, the figure was generated")
print("  from a DIFFERENT ragas_results.json than the one now on disk.")
print()

# Check: what does generate_visualizations.py actually render?
print("FIGURE GENERATION DATA (what fig1 bar chart actually plots):")
for mk in metrics:
    stored = data["metrics"].get(mk, {})
    print(f"  {mk:<22}: mean={stored.get('mean',0):.4f}  std={stored.get('std',0):.4f}")

print()
print("CONCLUSION:")
print("  The figure and the table should show IDENTICAL values because")
print("  both read from the same ragas_results.json['metrics'] dict.")
print("  If they differ, one of:")
print("  (a) The figure was generated from an older run's JSON that")
print("      was later overwritten by a second ragas run.")
print("  (b) The figure PNG on disk is stale (pre-dates the current JSON).")
print()

import os.path, datetime
fig_path = os.path.join(eval_dir, "figures", "fig1_ragas_summary_bar.png")
json_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(results_path))
fig_mtime  = datetime.datetime.fromtimestamp(os.path.getmtime(fig_path))
print(f"  ragas_results.json  last modified: {json_mtime.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  fig1_ragas_summary_bar.png last modified: {fig_mtime.strftime('%Y-%m-%d %H:%M:%S')}")
if fig_mtime < json_mtime:
    print()
    print("  >>> CONFIRMED: Figure predates the JSON. Figure is STALE.")
    print("  >>> The JSON was overwritten by a later RAGAS run AFTER the figure was saved.")
else:
    print()
    print("  >>> Figure is NEWER than JSON. Investigate further.")
