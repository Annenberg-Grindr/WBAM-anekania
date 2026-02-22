#!/usr/bin/env python3
"""
Generate the final BigLaw Bench evaluation report from individual component results.
"""

import json
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path("/home/user/WBAM-anekania/biglaw-bench-eval/results")
MODEL = "claude-sonnet-4-20250514"


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


def generate_report():
    core = load_json(RESULTS_DIR / "core_evaluation.json")
    workflow = load_json(RESULTS_DIR / "workflow_evaluation.json")
    retrieval = load_json(RESULTS_DIR / "retrieval_evaluation.json")

    lines = []
    lines.append("=" * 80)
    lines.append("BIGLAW BENCH EVALUATION REPORT")
    lines.append(f"Model Under Test: {MODEL}")
    lines.append(f"Evaluation Method: LLM-as-Judge (self-evaluation with rubric analysis)")
    lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)

    # ==========================================
    # BLB-Core
    # ==========================================
    lines.append("\n" + "=" * 80)
    lines.append("1. BLB-CORE RESULTS")
    lines.append("   Complex legal tasks with custom rubrics (6 sample tasks)")
    lines.append("=" * 80)

    core_scores = []
    if isinstance(core, list):
        for task in core:
            pct = task.get("final_score_pct", 0)
            core_scores.append(pct)
            lines.append(f"\n  Task #{task.get('task_number', '?')} ({task.get('category', '?')} - {task.get('task_type', '?')})")
            lines.append(f"    {task.get('task_description', 'N/A')[:100]}")
            lines.append(f"    Max Points: {task.get('max_possible_points', 'N/A')}")
            lines.append(f"    Estimated Points: {task.get('estimated_points_earned', 'N/A')}")
            lines.append(f"    Negative Points: {task.get('estimated_negative_points', 0)}")
            lines.append(f"    Score: {pct:.1f}%")
            if task.get("notes"):
                lines.append(f"    Notes: {task['notes']}")
    elif isinstance(core, dict) and "error" not in core:
        lines.append(f"  [Unexpected format: {list(core.keys())[:5]}]")
    else:
        lines.append(f"  [Error loading core results: {core.get('error', 'unknown')}]")

    if core_scores:
        avg = sum(core_scores) / len(core_scores)
        lines.append(f"\n  --- BLB-Core Summary ---")
        lines.append(f"  Tasks Evaluated: {len(core_scores)}")
        lines.append(f"  Average Score: {avg:.1f}%")
        lines.append(f"  Min Score: {min(core_scores):.1f}%")
        lines.append(f"  Max Score: {max(core_scores):.1f}%")

    # ==========================================
    # BLB-Retrieval
    # ==========================================
    lines.append("\n" + "=" * 80)
    lines.append("2. BLB-RETRIEVAL RESULTS")
    lines.append("   Legal document retrieval and question answering (30 queries)")
    lines.append("=" * 80)

    retrieval_scores = []
    if isinstance(retrieval, dict) and "queries" in retrieval:
        by_source = retrieval.get("by_source", {})
        for source, data in by_source.items():
            lines.append(f"\n  {source}:")
            lines.append(f"    Queries: {data.get('count', 'N/A')}")
            lines.append(f"    Average Score: {data.get('avg_pct', 0):.1f}%")

        if retrieval.get("overall_avg_pct"):
            retrieval_scores.append(retrieval["overall_avg_pct"])
            lines.append(f"\n  --- BLB-Retrieval Summary ---")
            lines.append(f"  Total Queries: {len(retrieval.get('queries', []))}")
            lines.append(f"  Overall Average: {retrieval['overall_avg_pct']:.1f}%")

        if retrieval.get("summary"):
            lines.append(f"  Summary: {retrieval['summary']}")
    else:
        lines.append(f"  [Error loading retrieval results]")

    # ==========================================
    # BLB-Workflows
    # ==========================================
    lines.append("\n" + "=" * 80)
    lines.append("3. BLB-WORKFLOWS (SPA Deal Point Extraction) RESULTS")
    lines.append("   Structured extraction from Stock Purchase Agreements (10 documents)")
    lines.append("=" * 80)

    workflow_scores = []
    if isinstance(workflow, dict) and "documents" in workflow:
        for doc in workflow["documents"]:
            pct = doc.get("accuracy_pct", 0)
            workflow_scores.append(pct)
            lines.append(f"\n  {doc.get('name', 'Unknown')[:60]}")
            lines.append(f"    Fields: {doc.get('correct_fields', 0)} correct, "
                        f"{doc.get('partially_correct', 0)} partial, "
                        f"{doc.get('incorrect_fields', 0)} incorrect "
                        f"/ {doc.get('total_fields', 'N/A')} total")
            lines.append(f"    Accuracy: {pct:.1f}%")

        if workflow.get("overall_accuracy_pct") is not None:
            lines.append(f"\n  --- BLB-Workflows Summary ---")
            lines.append(f"  Documents Evaluated: {len(workflow['documents'])}")
            lines.append(f"  Overall Accuracy: {workflow['overall_accuracy_pct']:.1f}%")

        if workflow.get("summary"):
            lines.append(f"  Summary: {workflow['summary']}")
    else:
        lines.append(f"  [Error loading workflow results]")

    # ==========================================
    # Overall Summary
    # ==========================================
    lines.append("\n" + "=" * 80)
    lines.append("OVERALL SUMMARY")
    lines.append("=" * 80)

    sections = {
        "BLB-Core (Legal Tasks)": core_scores,
        "BLB-Retrieval (Document QA)": [retrieval.get("overall_avg_pct", 0)] if isinstance(retrieval, dict) and retrieval.get("overall_avg_pct") else [],
        "BLB-Workflows (SPA Extraction)": workflow_scores,
    }

    overall_scores = []
    for name, scores in sections.items():
        if scores:
            avg = sum(scores) / len(scores)
            overall_scores.append(avg)
            lines.append(f"  {name}: {avg:.1f}%")
        else:
            lines.append(f"  {name}: No data")

    if overall_scores:
        overall = sum(overall_scores) / len(overall_scores)
        lines.append(f"\n  COMPOSITE SCORE: {overall:.1f}%")
        lines.append(f"  (Average across {len(overall_scores)} benchmark components)")

    lines.append("\n" + "=" * 80)
    lines.append("METHODOLOGY NOTES")
    lines.append("=" * 80)
    lines.append("""
  - Model evaluated: Claude Sonnet 4 (claude-sonnet-4-20250514)
  - Evaluation method: Rubric-based assessment using BigLaw Bench scoring criteria
  - BLB-Core: Custom rubrics with affirmative/negative points per Harvey AI methodology
  - BLB-Workflows: Field-by-field comparison against ground truth deal point data
  - BLB-Retrieval: Quality scoring (addressal, citations, comprehensiveness, structure,
    legal accuracy, avoiding speculation) across 3 document types
  - Scores represent estimated percentage of lawyer-quality work product
  - PDF text extraction used PyPDF2; some scanned documents had degraded extraction
  - Full benchmark requires Harvey AI's complete dataset (samples only evaluated here)
""")

    lines.append("=" * 80)

    report = "\n".join(lines)

    # Write report
    with open(RESULTS_DIR / "evaluation_report.txt", "w") as f:
        f.write(report)

    # Write structured summary
    summary = {
        "model": MODEL,
        "date": datetime.now().isoformat(),
        "blb_core": {
            "avg_score_pct": sum(core_scores) / len(core_scores) if core_scores else None,
            "num_tasks": len(core_scores),
            "task_scores": core_scores,
        },
        "blb_retrieval": {
            "avg_score_pct": retrieval.get("overall_avg_pct") if isinstance(retrieval, dict) else None,
            "num_queries": len(retrieval.get("queries", [])) if isinstance(retrieval, dict) else 0,
            "by_source": retrieval.get("by_source", {}) if isinstance(retrieval, dict) else {},
        },
        "blb_workflows": {
            "avg_accuracy_pct": sum(workflow_scores) / len(workflow_scores) if workflow_scores else None,
            "num_documents": len(workflow_scores),
            "document_scores": workflow_scores,
        },
        "composite_score_pct": sum(overall_scores) / len(overall_scores) if overall_scores else None,
    }

    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(report)
    return report


if __name__ == "__main__":
    generate_report()
