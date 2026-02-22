#!/usr/bin/env python3
"""
BigLaw Bench Evaluation Script

Evaluates Claude's performance on the BigLaw Bench benchmark across three components:
1. BLB-Core: Complex legal tasks with custom rubrics
2. BLB-Workflows: SPA deal point extraction
3. BLB-Retrieval: Document retrieval and question answering

Uses Claude as both the test subject and the rubric-based evaluator (LLM-as-judge).
"""

import anthropic
import base64
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime

# Configuration
MODEL_UNDER_TEST = "claude-sonnet-4-20250514"
JUDGE_MODEL = "claude-sonnet-4-20250514"
BIGLAW_BENCH_DIR = Path("/tmp/biglaw-bench")
OUTPUT_DIR = Path(__file__).resolve().parent / "results"
MAX_TOKENS_RESPONSE = 4096
MAX_TOKENS_JUDGE = 2048

client = anthropic.Anthropic()


def encode_pdf_base64(pdf_path: str) -> str:
    """Read a PDF file and return its base64-encoded content."""
    with open(pdf_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def read_pdf_text(pdf_path: str) -> str:
    """Extract text from a PDF file using PyPDF2 as fallback."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except (FileNotFoundError, PermissionError) as e:
        return f"[Error reading PDF: {e}]"
    except ImportError:
        return "[Error reading PDF: PyPDF2 not installed]"


def call_claude_with_pdfs(prompt: str, pdf_paths: list[str], model: str = MODEL_UNDER_TEST) -> str:
    """Call Claude with a prompt and optional PDF documents."""
    content = []

    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            pdf_b64 = encode_pdf_base64(pdf_path)
            content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_b64,
                },
            })

    content.append({"type": "text", "text": prompt})

    try:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS_RESPONSE,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text
    except anthropic.APIError as e:
        return f"[API Error: {e}]"


def call_claude_text(prompt: str, model: str = MODEL_UNDER_TEST) -> str:
    """Call Claude with a text-only prompt."""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS_RESPONSE,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except anthropic.APIError as e:
        return f"[API Error: {e}]"


def judge_response(response: str, rubric: str, task_description: str) -> dict:
    """Use Claude as a judge to score a response against a rubric."""
    judge_prompt = f"""You are an expert legal evaluator. Score the following AI response against the provided rubric.

## Task Description
{task_description}

## AI Response to Evaluate
{response}

## Scoring Rubric
{rubric}

## Instructions
1. Go through each rubric item systematically.
2. For each affirmative point, determine if the response satisfies it (award points) or not (0 points).
3. For negative points, identify any hallucinations or extraneous information.
4. Provide your evaluation in the following JSON format:

```json
{{
    "rubric_items": [
        {{
            "item": "description of rubric item",
            "max_points": <number>,
            "awarded_points": <number>,
            "reasoning": "brief explanation"
        }}
    ],
    "negative_points": [
        {{
            "type": "hallucination or extraneous",
            "description": "what was wrong",
            "points_deducted": <number>
        }}
    ],
    "total_positive_points": <number>,
    "max_possible_points": <number>,
    "total_negative_points": <number>,
    "final_score": <number>,
    "final_percentage": <number>,
    "summary": "brief overall assessment"
}}
```

Be strict but fair. Only award points when the criterion is clearly met."""

    try:
        response_obj = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=MAX_TOKENS_JUDGE,
            messages=[{"role": "user", "content": judge_prompt}],
        )
        judge_text = response_obj.content[0].text

        # Extract JSON from the response
        json_match = re.search(r'```json\s*(.*?)\s*```', judge_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        # Try parsing the whole response as JSON
        return json.loads(judge_text)
    except json.JSONDecodeError:
        return {"error": "Failed to parse judge response", "raw": judge_text}
    except anthropic.APIError as e:
        return {"error": f"Judge API error: {e}"}


def parse_core_csv(csv_path: str) -> list[dict]:
    """Parse the BLB-Core samples CSV file."""
    tasks = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            documents = []
            if row.get('Document(s)') and row['Document(s)'].strip() and row['Document(s)'].strip() != 'N/A':
                doc_names = [d.strip() for d in row['Document(s)'].split('\n') if d.strip()]
                for doc_name in doc_names:
                    doc_path = BIGLAW_BENCH_DIR / "blb-core" / "documents" / doc_name
                    if doc_path.exists():
                        documents.append(str(doc_path))

            tasks.append({
                "number": row.get('Number', ''),
                "category": row.get('Category', ''),
                "task_type": row.get('Task Type', ''),
                "task": row.get('Task', ''),
                "prompt": row.get('Prompt', ''),
                "documents": documents,
                "rubric": row.get('Rubric', ''),
            })
    return tasks


def evaluate_core(tasks: list[dict]) -> list[dict]:
    """Evaluate BLB-Core tasks."""
    results = []
    for i, task in enumerate(tasks):
        print(f"\n  [Core Task {i+1}/{len(tasks)}] #{task['number']}: {task['task'][:80]}...")

        # Generate response
        if task['documents']:
            print(f"    Sending prompt with {len(task['documents'])} PDF document(s)...")
            response = call_claude_with_pdfs(task['prompt'], task['documents'])
        else:
            print(f"    Sending text-only prompt...")
            response = call_claude_text(task['prompt'])

        if response.startswith("[API Error") or response.startswith("[Error"):
            print(f"    ERROR: {response[:100]}")
            results.append({
                "task": task,
                "response": response,
                "evaluation": {"error": response},
            })
            continue

        print(f"    Response received ({len(response)} chars). Evaluating against rubric...")

        # Judge the response
        evaluation = judge_response(response, task['rubric'], task['task'])

        result = {
            "task_number": task['number'],
            "category": task['category'],
            "task_type": task['task_type'],
            "task_description": task['task'],
            "prompt": task['prompt'],
            "num_documents": len(task['documents']),
            "response": response,
            "evaluation": evaluation,
        }
        results.append(result)

        if 'error' not in evaluation:
            pct = evaluation.get('final_percentage', 0)
            print(f"    Score: {evaluation.get('final_score', 'N/A')}/{evaluation.get('max_possible_points', 'N/A')} ({pct:.1f}%)")
        else:
            print(f"    Evaluation error: {evaluation.get('error', 'unknown')}")

        # Small delay to respect rate limits
        time.sleep(1)

    return results


def parse_retrieval_csv(csv_path: str) -> list[dict]:
    """Parse the BLB-Retrieval samples CSV file."""
    queries = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            queries.append({
                "query": row.get('Query', ''),
                "source": row.get('Source', ''),
            })
    return queries


def get_retrieval_documents(source: str) -> list[str]:
    """Get document paths for a given retrieval source type."""
    base = BIGLAW_BENCH_DIR / "blb-retrieval"
    if source == "discovery_emails":
        doc_dir = base / "discovery_emails"
    elif source == "spa":
        doc_dir = base / "spa"
    elif source == "merger_agreements":
        doc_dir = base / "merger_agreements"
    else:
        return []

    if doc_dir.exists():
        return sorted([str(p) for p in list(doc_dir.glob("*.pdf")) + list(doc_dir.glob("*.Pdf")) + list(doc_dir.glob("*.PDF"))])
    return []


def evaluate_retrieval(queries: list[dict]) -> list[dict]:
    """Evaluate BLB-Retrieval tasks."""
    results = []
    for i, query_info in enumerate(queries):
        print(f"\n  [Retrieval {i+1}/{len(queries)}] Source: {query_info['source']}")
        print(f"    Query: {query_info['query'][:80]}...")

        doc_paths = get_retrieval_documents(query_info['source'])
        if not doc_paths:
            print(f"    No documents found for source: {query_info['source']}")
            results.append({
                "query": query_info['query'],
                "source": query_info['source'],
                "response": "[No documents available]",
                "evaluation": {"error": "No documents found"},
            })
            continue

        prompt = f"""You are a legal research assistant. Answer the following query based on the provided documents.
Be thorough, accurate, and cite specific provisions, sections, or pages when possible.

Query: {query_info['query']}"""

        print(f"    Sending query with {len(doc_paths)} document(s)...")
        response = call_claude_with_pdfs(prompt, doc_paths)

        if response.startswith("[API Error") or response.startswith("[Error"):
            print(f"    ERROR: {response[:100]}")
            results.append({
                "query": query_info['query'],
                "source": query_info['source'],
                "response": response,
                "evaluation": {"error": response},
            })
            continue

        print(f"    Response received ({len(response)} chars)")

        # For retrieval, we evaluate based on general quality criteria
        retrieval_rubric = f"""Evaluate the response to the legal research query: "{query_info['query']}"

Affirmative Points:
1. Does the response directly address the query? (2 points)
2. Does the response cite specific documents, sections, or provisions? (2 points)
3. Is the response comprehensive and thorough? (2 points)
4. Is the response well-structured and clearly organized? (1 point)
5. Does the response demonstrate accurate understanding of the legal concepts? (2 points)
6. Does the response avoid speculation and stick to what's in the documents? (1 point)

Negative Points:
1. -1 point for every hallucination or fabricated citation
2. -0.5 point for every statement of accurate but extraneous information"""

        evaluation = judge_response(response, retrieval_rubric, query_info['query'])

        result = {
            "query": query_info['query'],
            "source": query_info['source'],
            "num_documents": len(doc_paths),
            "response": response,
            "evaluation": evaluation,
        }
        results.append(result)

        if 'error' not in evaluation:
            pct = evaluation.get('final_percentage', 0)
            print(f"    Score: {pct:.1f}%")

        time.sleep(1)

    return results


def parse_spa_samples(csv_path: str) -> dict:
    """Parse the BLB-Workflows SPA samples CSV and return ground truth."""
    ground_truth = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            doc_name = row.get('Documents', '')
            if doc_name:
                ground_truth[doc_name] = {k: v for k, v in row.items() if k != 'Documents'}
    return ground_truth


def evaluate_workflows(schema: dict, ground_truth: dict) -> list[dict]:
    """Evaluate BLB-Workflows SPA deal point extraction."""
    results = []
    doc_dir = BIGLAW_BENCH_DIR / "blb-workflows" / "spa" / "documents"

    if not doc_dir.exists():
        print("  SPA documents directory not found")
        return results

    pdf_files = sorted(doc_dir.glob("*.pdf")) + sorted(doc_dir.glob("*.PDF"))

    for i, pdf_path in enumerate(pdf_files):
        doc_name = pdf_path.name
        print(f"\n  [SPA {i+1}/{len(pdf_files)}] {doc_name[:60]}...")

        schema_str = json.dumps(schema, indent=2)
        prompt = f"""You are a legal analyst specializing in M&A transactions. Extract the following deal points from this Stock Purchase Agreement (SPA) document.

Return your answer as a JSON object following this exact schema:

{schema_str}

Extract all fields as accurately as possible from the document. If a field is not found or not applicable, use "N/A" or an empty array as appropriate. Be precise and cite specific sections where possible."""

        print(f"    Extracting deal points...")
        response = call_claude_with_pdfs(prompt, [str(pdf_path)])

        if response.startswith("[API Error") or response.startswith("[Error"):
            print(f"    ERROR: {response[:100]}")
            results.append({
                "document": doc_name,
                "response": response,
                "evaluation": {"error": response},
            })
            continue

        print(f"    Response received ({len(response)} chars)")

        # Try to parse the extracted JSON
        extracted = None
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                extracted = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        if not extracted:
            try:
                extracted = json.loads(response)
            except json.JSONDecodeError:
                pass

        # Compare with ground truth if available
        gt = ground_truth.get(doc_name, {})
        if gt:
            eval_prompt = f"""Compare the extracted deal points against the ground truth for the document "{doc_name}".

## Extracted Deal Points (by AI)
{json.dumps(extracted, indent=2) if extracted else response}

## Ground Truth
{json.dumps(gt, indent=2)}

## Schema Fields
{json.dumps(list(schema.keys()), indent=2)}

Evaluate accuracy for each field. Return JSON:
```json
{{
    "field_scores": [
        {{
            "field": "field_name",
            "correct": true/false,
            "partially_correct": true/false,
            "reasoning": "explanation"
        }}
    ],
    "total_fields": <number>,
    "correct_fields": <number>,
    "partially_correct_fields": <number>,
    "accuracy_percentage": <number>,
    "summary": "brief assessment"
}}
```"""
            evaluation = judge_response(response, eval_prompt, f"SPA deal point extraction for {doc_name}")
        else:
            evaluation = {"note": "No ground truth available for comparison"}

        result = {
            "document": doc_name,
            "response": response,
            "extracted_json": extracted,
            "has_ground_truth": bool(gt),
            "evaluation": evaluation,
        }
        results.append(result)

        if 'error' not in evaluation and 'accuracy_percentage' in evaluation:
            print(f"    Accuracy: {evaluation['accuracy_percentage']:.1f}%")
        elif 'error' not in evaluation:
            print(f"    Evaluation completed")

        time.sleep(1)

    return results


def generate_report(core_results: list, retrieval_results: list, workflow_results: list) -> str:
    """Generate a comprehensive evaluation report."""
    report = []
    report.append("=" * 80)
    report.append("BIGLAW BENCH EVALUATION REPORT")
    report.append(f"Model Under Test: {MODEL_UNDER_TEST}")
    report.append(f"Judge Model: {JUDGE_MODEL}")
    report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)

    # BLB-Core Summary
    report.append("\n" + "=" * 80)
    report.append("1. BLB-CORE RESULTS")
    report.append("=" * 80)

    core_scores = []
    for r in core_results:
        eval_data = r.get('evaluation', {})
        if 'error' not in eval_data:
            pct = eval_data.get('final_percentage', 0)
            core_scores.append(pct)
            report.append(f"\nTask #{r['task_number']} ({r['category']} - {r['task_type']})")
            report.append(f"  Description: {r['task_description'][:100]}")
            report.append(f"  Documents: {r['num_documents']}")
            report.append(f"  Score: {eval_data.get('final_score', 'N/A')}/{eval_data.get('max_possible_points', 'N/A')} ({pct:.1f}%)")
            report.append(f"  Positive Points: {eval_data.get('total_positive_points', 'N/A')}")
            report.append(f"  Negative Points: {eval_data.get('total_negative_points', 0)}")
            if eval_data.get('summary'):
                report.append(f"  Summary: {eval_data['summary']}")
        else:
            report.append(f"\nTask #{r.get('task_number', '?')}: ERROR - {eval_data.get('error', 'unknown')}")

    if core_scores:
        avg = sum(core_scores) / len(core_scores)
        report.append(f"\n--- BLB-Core Summary ---")
        report.append(f"Tasks Evaluated: {len(core_scores)}/{len(core_results)}")
        report.append(f"Average Score: {avg:.1f}%")
        report.append(f"Min Score: {min(core_scores):.1f}%")
        report.append(f"Max Score: {max(core_scores):.1f}%")

    # BLB-Retrieval Summary
    report.append("\n" + "=" * 80)
    report.append("2. BLB-RETRIEVAL RESULTS")
    report.append("=" * 80)

    retrieval_scores = []
    by_source = {}
    for r in retrieval_results:
        eval_data = r.get('evaluation', {})
        source = r.get('source', 'unknown')
        if 'error' not in eval_data:
            pct = eval_data.get('final_percentage', 0)
            retrieval_scores.append(pct)
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(pct)
            report.append(f"\nQuery [{source}]: {r['query'][:80]}...")
            report.append(f"  Documents: {r.get('num_documents', 'N/A')}")
            report.append(f"  Score: {pct:.1f}%")
        else:
            report.append(f"\nQuery [{source}]: ERROR - {r['query'][:60]}...")

    if retrieval_scores:
        avg = sum(retrieval_scores) / len(retrieval_scores)
        report.append(f"\n--- BLB-Retrieval Summary ---")
        report.append(f"Queries Evaluated: {len(retrieval_scores)}/{len(retrieval_results)}")
        report.append(f"Average Score: {avg:.1f}%")
        for source, scores in by_source.items():
            src_avg = sum(scores) / len(scores)
            report.append(f"  {source}: {src_avg:.1f}% avg ({len(scores)} queries)")

    # BLB-Workflows Summary
    report.append("\n" + "=" * 80)
    report.append("3. BLB-WORKFLOWS (SPA) RESULTS")
    report.append("=" * 80)

    workflow_scores = []
    for r in workflow_results:
        eval_data = r.get('evaluation', {})
        if 'error' not in eval_data and 'accuracy_percentage' in eval_data:
            pct = eval_data['accuracy_percentage']
            workflow_scores.append(pct)
            report.append(f"\nDocument: {r['document'][:60]}")
            report.append(f"  JSON Extracted: {'Yes' if r.get('extracted_json') else 'No'}")
            report.append(f"  Accuracy: {pct:.1f}%")
            report.append(f"  Correct Fields: {eval_data.get('correct_fields', 'N/A')}/{eval_data.get('total_fields', 'N/A')}")
        elif 'error' not in eval_data:
            report.append(f"\nDocument: {r['document'][:60]}")
            report.append(f"  JSON Extracted: {'Yes' if r.get('extracted_json') else 'No'}")
            report.append(f"  Note: {eval_data.get('note', eval_data.get('summary', 'Evaluation completed'))}")
        else:
            report.append(f"\nDocument: {r.get('document', '?')}: ERROR")

    if workflow_scores:
        avg = sum(workflow_scores) / len(workflow_scores)
        report.append(f"\n--- BLB-Workflows Summary ---")
        report.append(f"Documents Evaluated: {len(workflow_scores)}/{len(workflow_results)}")
        report.append(f"Average Accuracy: {avg:.1f}%")

    # Overall Summary
    report.append("\n" + "=" * 80)
    report.append("OVERALL SUMMARY")
    report.append("=" * 80)

    all_scores = {
        "BLB-Core": core_scores,
        "BLB-Retrieval": retrieval_scores,
        "BLB-Workflows": workflow_scores,
    }

    for name, scores in all_scores.items():
        if scores:
            avg = sum(scores) / len(scores)
            report.append(f"  {name}: {avg:.1f}% average ({len(scores)} tasks)")
        else:
            report.append(f"  {name}: No scores available")

    combined = core_scores + retrieval_scores + workflow_scores
    if combined:
        overall_avg = sum(combined) / len(combined)
        report.append(f"\n  OVERALL AVERAGE: {overall_avg:.1f}% across {len(combined)} tasks")

    report.append("\n" + "=" * 80)
    return "\n".join(report)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("BigLaw Bench Evaluation")
    print(f"Model: {MODEL_UNDER_TEST}")
    print(f"Judge: {JUDGE_MODEL}")
    print("=" * 60)

    # ==========================================
    # 1. BLB-Core Evaluation
    # ==========================================
    print("\n[PHASE 1] BLB-Core Evaluation")
    print("-" * 40)

    core_csv = BIGLAW_BENCH_DIR / "blb-core" / "core-samples.csv"
    core_tasks = parse_core_csv(str(core_csv))
    print(f"Found {len(core_tasks)} core tasks")

    core_results = evaluate_core(core_tasks)

    with open(OUTPUT_DIR / "core_results.json", 'w', encoding='utf-8') as f:
        json.dump(core_results, f, indent=2, default=str)
    print(f"\nCore results saved to {OUTPUT_DIR / 'core_results.json'}")

    # ==========================================
    # 2. BLB-Retrieval Evaluation
    # ==========================================
    print("\n[PHASE 2] BLB-Retrieval Evaluation")
    print("-" * 40)

    retrieval_csv = BIGLAW_BENCH_DIR / "blb-retrieval" / "samples.csv"
    retrieval_queries = parse_retrieval_csv(str(retrieval_csv))
    print(f"Found {len(retrieval_queries)} retrieval queries")

    retrieval_results = evaluate_retrieval(retrieval_queries)

    with open(OUTPUT_DIR / "retrieval_results.json", 'w', encoding='utf-8') as f:
        json.dump(retrieval_results, f, indent=2, default=str)
    print(f"\nRetrieval results saved to {OUTPUT_DIR / 'retrieval_results.json'}")

    # ==========================================
    # 3. BLB-Workflows Evaluation
    # ==========================================
    print("\n[PHASE 3] BLB-Workflows (SPA) Evaluation")
    print("-" * 40)

    schema_path = BIGLAW_BENCH_DIR / "blb-workflows" / "spa" / "schema.json"
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    spa_csv = BIGLAW_BENCH_DIR / "blb-workflows" / "spa" / "spa-samples.csv"
    ground_truth = parse_spa_samples(str(spa_csv))
    print(f"Found {len(ground_truth)} SPA ground truth entries")

    workflow_results = evaluate_workflows(schema, ground_truth)

    with open(OUTPUT_DIR / "workflow_results.json", 'w', encoding='utf-8') as f:
        json.dump(workflow_results, f, indent=2, default=str)
    print(f"\nWorkflow results saved to {OUTPUT_DIR / 'workflow_results.json'}")

    # ==========================================
    # Generate Report
    # ==========================================
    print("\n[PHASE 4] Generating Report")
    print("-" * 40)

    report = generate_report(core_results, retrieval_results, workflow_results)
    report_path = OUTPUT_DIR / "evaluation_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(report)
    print(f"\nFull report saved to {report_path}")

    # Save structured summary
    summary = {
        "model": MODEL_UNDER_TEST,
        "judge_model": JUDGE_MODEL,
        "date": datetime.now().isoformat(),
        "core": {
            "num_tasks": len(core_results),
            "scores": [r['evaluation'].get('final_percentage', None) for r in core_results if 'error' not in r.get('evaluation', {})],
        },
        "retrieval": {
            "num_queries": len(retrieval_results),
            "scores": [r['evaluation'].get('final_percentage', None) for r in retrieval_results if 'error' not in r.get('evaluation', {})],
        },
        "workflows": {
            "num_documents": len(workflow_results),
            "scores": [r['evaluation'].get('accuracy_percentage', None) for r in workflow_results if 'error' not in r.get('evaluation', {}) and 'accuracy_percentage' in r.get('evaluation', {})],
        },
    }

    with open(OUTPUT_DIR / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary saved to {OUTPUT_DIR / 'summary.json'}")
    print("\nEvaluation complete!")


if __name__ == "__main__":
    main()
