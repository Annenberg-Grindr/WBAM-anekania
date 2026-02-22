# BigLaw Bench: Improvement Proposal

**Author:** WBAM Evaluation Team
**Date:** February 22, 2026
**Status:** Draft for discussion

---

## Purpose

This document proposes specific, implementable improvements to (A) the BigLaw Bench benchmark itself and (B) our evaluation pipeline. Each proposal is grounded in problems observed during our evaluation of Claude Sonnet 4, which scored 55.0% composite (Core 70.5%, Retrieval 55.7%, Workflows 38.9%). Where relevant, we estimate the impact each change would have on score accuracy and interpretability.

---

## Part A: Proposals for the BigLaw Bench Benchmark

### A1. Separate Document Pipeline Scores from Legal Reasoning Scores

**Problem.** Our evaluation showed that the single largest driver of score variance was document availability, not model capability. Task #5 scored 0% because all five source PDFs were scanned images with no extractable text. BLB-Workflows averaged 38.9%, but extracted text was truncated to the first 18-27 pages of 60-120 page agreements. When we isolate fields where text was actually available, accuracy rises to approximately 79.6%.

The benchmark conflates two distinct capabilities: (1) can the model handle a PDF-to-text pipeline, and (2) can the model reason about legal content once it has the text.

**Proposal.** For every document-dependent task, BLB should provide two input variants:

| Variant | Input | What it measures |
|---------|-------|------------------|
| **Raw** | Original PDF files as-is | Full pipeline: OCR + extraction + reasoning |
| **Clean** | Pre-extracted, verified plain text | Legal reasoning in isolation |

BLB should then report two scores per task:
- **Pipeline Score** = performance on the raw variant
- **Reasoning Score** = performance on the clean variant

The gap between the two directly quantifies how much a model's score depends on infrastructure rather than intelligence.

**Implementation.** This requires Harvey AI to produce clean-text versions of each source document, verified by a human reviewer for completeness and fidelity. For the 6 BLB-Core sample tasks and 30 BLB-Retrieval queries, this is approximately 50-60 documents -- a one-time effort of roughly 40 hours.

**Impact on our scores.** We estimate our BLB-Core Reasoning Score would be 84.6% (up from 70.5%) because Task #5 would no longer score 0%. Our Workflows Reasoning Score would be approximately 79.6% (up from 38.9%).

---

### A2. Normalize Rubric Scores by Task Complexity

**Problem.** BLB's rubrics have wildly inconsistent granularity:

| Task | Max Points | Points per Rubric Item | Impact of 1 Missed Point |
|------|-----------|----------------------|-------------------------|
| #49 (Board Consent) | 9 | ~1.3 | 11.1% |
| #19 (Merger Memo) | 23 | ~1.0 | 4.3% |
| #96 (Subpoena Analysis) | 12 | ~1.0 | 8.3% |

The composite score treats all tasks equally (simple average of percentages), but the underlying measurement precision varies by a factor of nearly 3x. Missing one rubric item on the 9-point drafting task costs 2.6x more than missing one item on the 23-point analytical task.

**Proposal.** Introduce complexity-weighted composite scoring:

```
Weighted_Score = Sum(task_score_pct * task_weight) / Sum(task_weight)

where task_weight = max_points * document_count * estimated_hours
```

Alternatively, a simpler fix: report the composite as a weighted average where each task's weight is its maximum points. Under this method, a point on Task #19 (23 max) contributes the same as a point on Task #49 (9 max), rather than being worth 2.5x less.

**Impact.** Under point-weighted averaging, our BLB-Core score shifts from 70.5% to approximately 72.8%, better reflecting the strong performance on complex analytical tasks.

---

### A3. Tiered Hallucination Penalties

**Problem.** BLB deducts -1 point per hallucination and -0.5 per extraneous item, regardless of severity. On a 9-point task, one hallucination costs 11.1%; on a 23-point task, 4.3%. More fundamentally, the benchmark treats a fabricated case citation (potential malpractice) identically to a minor factual embellishment (harmless but sloppy).

**Proposal.** Replace the flat penalty with a three-tier system:

| Tier | Definition | Example | Penalty |
|------|-----------|---------|---------|
| **Critical** | Fabricated legal authorities or materially incorrect legal conclusions | Citing a nonexistent case; stating the wrong standard of review | -3 points |
| **Serious** | Incorrect factual claims derived from the source documents | Misstating a dollar amount from a contract; wrong date from a filing | -1.5 points |
| **Minor** | Embellishments, speculative hedging, or extraneous but non-harmful content | Adding context not in the documents; over-qualifying a conclusion | -0.5 points |

**Rationale.** This mirrors real-world consequences. A partner who finds a fabricated citation in an associate's memo will question everything the associate has ever produced. A partner who finds an incorrect dollar amount will correct it and move on. A partner who finds unnecessary hedging will red-line it and bill for the time. The penalties should scale accordingly.

---

### A4. Multi-Turn Evaluation Tasks

**Problem.** Every BLB task is a single prompt-response pair. Real legal work is iterative: a partner reviews a draft, provides feedback, the associate revises, new facts surface. BLB cannot measure a model's ability to incorporate feedback, correct errors when prompted, or maintain analytical consistency across a conversation.

**Proposal.** Add a BLB-Iterative component with 5-10 tasks structured as multi-turn conversations:

```
Turn 1: Initial task (e.g., "Draft a memo analyzing the indemnification
        provisions in this SPA.")
Turn 2: Partner feedback ("The analysis of basket mechanisms is incomplete.
        Also, you missed the anti-sandbagging clause in Section 8.4.
        Please revise.")
Turn 3: New facts ("The client just told us the target company had an
        undisclosed environmental liability. How does this affect the
        indemnification analysis?")
Turn 4: Final deliverable request ("Prepare a final version incorporating
        all revisions and flag any open issues for the partner meeting
        tomorrow.")
```

**Scoring.** Each turn would have its own rubric, but the final turn's score would also assess consistency with prior turns (e.g., did the model retain correct analysis from Turn 1 while incorporating Turn 2 corrections, or did it introduce regressions?).

**Why this matters.** In our evaluation, Claude scored 100% on Task #49 (pure drafting) but only 73.9% on Task #19 (complex analysis). A multi-turn format would reveal whether the Task #19 gaps (missing Residual Shares provision, potential calculation errors) could be corrected through interactive feedback -- which is how real legal work actually functions.

---

### A5. Adversarial Robustness Tasks

**Problem.** BLB tasks are presented in good faith: the documents are authentic, the prompts are straightforward, and the correct answers exist. Real legal practice is not always cooperative. Opposing counsel embeds misleading language in contracts. Clients present incomplete or inaccurate facts. Witnesses contradict themselves.

**Proposal.** Add a BLB-Adversarial component with 5-10 tasks testing robustness:

1. **False premise detection.** Prompt contains an incorrect legal assumption (e.g., "Under Delaware law, the business judgment rule does not apply to conflicted transactions"). Model should identify and correct the false premise rather than build on it.

2. **Planted errors in source documents.** A modified contract contains an internally inconsistent provision (e.g., a governing law clause that says "New York" in one section and "Delaware" in another). Model should flag the inconsistency.

3. **Missing document detection.** Task references five source documents but only provides four. Model should identify the gap rather than fabricate content to fill it.

4. **Misleading context.** Prompt includes a parenthetical that subtly misdirects (e.g., "the non-compete provision (Section 4.2)" when the non-compete is actually in Section 7.1). Model should use the document text, not the prompt's section reference.

**Scoring.** Binary per item: did the model identify the adversarial element (1 point) or did it proceed without flagging it (0 points). Negative points for incorporating the adversarial element into the analysis without qualification.

---

### A6. Expand Practice Area Coverage

**Problem.** Of the 6 sample BLB-Core tasks, 3 are transactional (corporate/M&A) and 2 are litigation. Major BigLaw practice areas are absent.

**Proposal.** The full benchmark should include at least 2 tasks per major practice area:

| Practice Area | Current Coverage | Proposed Tasks |
|--------------|-----------------|----------------|
| M&A / Corporate | 3 tasks | Sufficient |
| Litigation | 2 tasks | Sufficient |
| Regulatory / Compliance | 1 task (partial) | Add: SEC comment letter response, FCPA internal investigation memo |
| Tax | 0 tasks | Add: Tax opinion letter, structuring memo for cross-border transaction |
| IP | 0 tasks | Add: Freedom-to-operate analysis, patent claim construction memo |
| Employment | 0 tasks | Add: Severance agreement review, wage-and-hour class certification memo |
| Restructuring / Bankruptcy | 0 tasks | Add: First-day declaration analysis, plan confirmation objection |
| Antitrust | 0 tasks | Add: HSR filing analysis, merger clearance risk assessment |

---

## Part B: Proposals for Our Evaluation Pipeline

### B1. Use a Stronger / Different Model as Judge

**Problem.** Our evaluation used Claude Sonnet 4 as both test-taker and judge. Self-evaluation introduces documented biases: self-enhancement (favoring own output style), verbosity preference, and anchoring to rubric framing.

**Proposal.** Implement a three-judge panel:

```python
JUDGE_MODELS = [
    "claude-opus-4-20250514",      # Stronger model, same family
    "gpt-4o-2024-11-20",           # Different model family
    "claude-sonnet-4-20250514",    # Self-evaluation (for comparison)
]

def evaluate_task(response, rubric):
    scores = {}
    for model in JUDGE_MODELS:
        scores[model] = grade_with_rubric(response, rubric, model)

    # Report individual and consensus scores
    consensus = median(scores.values())
    agreement = max(scores.values()) - min(scores.values())
    return {
        "consensus_score": consensus,
        "inter_judge_spread": agreement,
        "individual_scores": scores,
    }
```

**Key metrics to report:**
- **Consensus score** (median of 3 judges) as the primary result
- **Inter-judge spread** as a confidence indicator -- a task where all three judges agree within 5% is a high-confidence score; a task with 20%+ spread signals rubric ambiguity or evaluation difficulty
- **Self-evaluation delta** = self-judge score minus consensus score, quantifying the self-enhancement bias for this specific model

**Implementation cost.** For the 6 BLB-Core tasks, this triples the judge API calls (from 6 to 18). At roughly $0.50 per evaluation call, total cost increases by ~$6.00 -- negligible.

---

### B2. Improve Document Extraction Pipeline

**Problem.** Our PyPDF2-based extraction failed on scanned PDFs (Task #5) and severely truncated long documents (Workflows SPAs). This is the single largest source of score depression.

**Proposal.** Replace the extraction pipeline with a tiered approach:

```
Step 1: PyMuPDF (fitz) extraction -- handles most text-based PDFs
        ↓ if extracted text < 100 chars per page
Step 2: Tesseract OCR on page images -- handles scanned PDFs
        ↓ if OCR confidence < 0.7
Step 3: Claude Vision (multimodal) -- handles degraded scans
        ↓ always
Step 4: Extraction quality report -- log chars/page, confidence,
        method used, pages extracted vs. total pages
```

**Critical addition: extraction completeness check.**

```python
def validate_extraction(pdf_path, extracted_text):
    """Flag truncated or incomplete extractions before evaluation."""
    total_pages = get_page_count(pdf_path)
    extracted_pages = estimate_extracted_pages(extracted_text)

    completeness = extracted_pages / total_pages

    if completeness < 0.5:
        return {
            "status": "INCOMPLETE",
            "completeness": completeness,
            "recommendation": "Re-extract with OCR or multimodal fallback",
            "impact": f"Fields in pages {extracted_pages+1}-{total_pages} "
                      f"will be unanswerable"
        }
    return {"status": "OK", "completeness": completeness}
```

**Impact.** We estimate this would raise:
- Task #5 from 0.0% to approximately 50-70% (OCR quality dependent)
- BLB-Workflows from 38.9% to approximately 60-75% (full document access)
- BLB-Retrieval from 55.7% to approximately 60-65% (marginal, since most retrieval docs were well-extracted)

---

### B3. Add Confidence Calibration to Model Responses

**Problem.** BLB measures accuracy but not calibration -- whether the model knows what it knows and what it doesn't. In legal practice, an associate who says "I'm 90% confident" when they should say "I'm uncertain, let me verify" is more dangerous than one who simply gets the answer wrong, because the false confidence prevents the partner from catching the error.

**Proposal.** Add a confidence elicitation step to each task:

```python
CONFIDENCE_PROMPT = """
After completing the task, rate your confidence on each major
component of your response:

For each section/conclusion, provide:
- HIGH: I am confident this is correct based on the source materials
- MEDIUM: I believe this is likely correct but some elements are
  uncertain or the source materials are ambiguous
- LOW: I am uncertain about this and it should be verified by a
  senior attorney
- UNABLE: The source materials do not contain sufficient information
  to address this point

Do not inflate your confidence to appear more useful.
Accurate self-assessment is more valuable than false certainty.
"""
```

**Scoring.** Compare stated confidence against actual accuracy:

| Scenario | Calibration |
|----------|------------|
| HIGH confidence + correct answer | Well calibrated (+1) |
| HIGH confidence + wrong answer | Overconfident, dangerous (-2) |
| LOW confidence + correct answer | Underconfident, inefficient (+0.5) |
| LOW confidence + wrong answer | Well calibrated (+1) |
| UNABLE + missing from documents | Well calibrated (+1) |
| UNABLE + present in documents | Over-cautious (-0.5) |

Report a **calibration score** alongside the accuracy score. A model with 70% accuracy and excellent calibration may be more useful in practice than a model with 80% accuracy and poor calibration.

---

### B4. Implement Pairwise Comparison Evaluation

**Problem.** Absolute rubric scoring is sensitive to judge biases and rubric interpretation. Two judges can read the same rubric and reach different conclusions about whether a response "sufficiently" addresses a point.

**Proposal.** Supplement rubric scoring with pairwise preference evaluation (inspired by Harvey's BLB: Arena):

```python
def pairwise_evaluate(task, response_a, response_b, judge_model):
    """
    Present two responses side-by-side and ask the judge
    which is better, without revealing which model produced which.
    """
    prompt = f"""
    You are evaluating two responses to the following legal task.

    Task: {task.description}
    Source Documents: {task.documents}

    Response A:
    {response_a}

    Response B:
    {response_b}

    Which response better serves the needs of a supervising partner?
    Consider: accuracy, completeness, clarity, professional tone,
    appropriate caveats, and absence of fabricated information.

    Output: A_MUCH_BETTER | A_SLIGHTLY_BETTER | TIE |
            B_SLIGHTLY_BETTER | B_MUCH_BETTER

    Then explain your reasoning in 2-3 sentences.
    """
    return judge_model.evaluate(prompt)
```

**Use case.** Run each BLB task against 2-3 different models, then use pairwise comparison to produce an Elo-style ranking. This is more robust than comparing absolute scores across models (which are sensitive to rubric interpretation) and captures quality dimensions that rubrics may miss.

---

### B5. Track Score Variance Across Runs

**Problem.** We ran each task once. LLM outputs are stochastic -- the same model on the same task can produce meaningfully different responses across runs. A single score is a point estimate with unknown variance.

**Proposal.** Run each evaluation task 3-5 times and report distributional statistics:

```python
def evaluate_with_variance(task, model, n_runs=5):
    scores = []
    for i in range(n_runs):
        response = model.generate(task.prompt, temperature=0.7)
        score = judge.grade(response, task.rubric)
        scores.append(score)

    return {
        "mean": statistics.mean(scores),
        "median": statistics.median(scores),
        "std_dev": statistics.stdev(scores),
        "min": min(scores),
        "max": max(scores),
        "coefficient_of_variation": statistics.stdev(scores) / statistics.mean(scores),
    }
```

**Why this matters.** If Task #19 scores [73.9%, 80.4%, 69.6%, 78.3%, 75.0%] across 5 runs, the mean (75.4%) and standard deviation (4.1%) tell a different story than a single run of 73.9%. High-variance tasks indicate either rubric ambiguity or model inconsistency -- both important to understand.

**Cost.** 5 runs x 6 Core tasks = 30 API calls for the test-taker, plus 30 for the judge. At current API pricing, approximately $15-20 total -- a small price for statistical rigor.

---

## Part C: Implementation Priorities

Ranked by impact-to-effort ratio:

| Priority | Proposal | Effort | Impact on Score Accuracy | Impact on Interpretability |
|----------|----------|--------|--------------------------|---------------------------|
| 1 | B2: Better extraction pipeline | Medium (2-3 days) | Very High | High |
| 2 | B1: Multi-model judge panel | Low (1 day) | Medium | Very High |
| 3 | A1: Separate pipeline vs. reasoning scores | Low (reporting change) | None (changes interpretation) | Very High |
| 4 | B5: Multi-run variance tracking | Low (1 day) | Medium | High |
| 5 | A2: Normalize rubric scores | Low (formula change) | Low | High |
| 6 | B3: Confidence calibration | Medium (2 days) | Low | Very High |
| 7 | A3: Tiered hallucination penalties | Medium (rubric redesign) | Medium | High |
| 8 | B4: Pairwise comparison | Medium (2-3 days) | Medium | High |
| 9 | A4: Multi-turn tasks | High (task design) | N/A (new capability) | Very High |
| 10 | A5: Adversarial tasks | High (task design) | N/A (new capability) | High |
| 11 | A6: Practice area expansion | High (content creation) | N/A (new coverage) | High |

**Immediate next steps (this week):**
1. Implement the tiered extraction pipeline (B2) and re-run BLB-Workflows and Task #5
2. Add Claude Opus as a second judge (B1) and compare scores
3. Re-report all scores with pipeline vs. reasoning separation (A1)

**Short-term (next 2 weeks):**
4. Implement multi-run evaluation (B5) for statistical confidence
5. Add confidence calibration prompts (B3) to all tasks
6. Normalize existing rubric scores (A2) and publish both raw and normalized

**Medium-term (proposal to Harvey AI / community):**
7. Draft a public proposal for tiered hallucination penalties (A3)
8. Design 2-3 prototype multi-turn tasks (A4) and pilot them
9. Build adversarial test cases (A5) starting with false premise detection

---

## Appendix: Expected Score Impact

If proposals B1, B2, and A1 were implemented, we estimate the following revised scores:

| Component | Current Score | Estimated Reasoning Score | Delta |
|-----------|--------------|--------------------------|-------|
| BLB-Core | 70.5% | 84.6% | +14.1 |
| BLB-Retrieval | 55.7% | 62.0% | +6.3 |
| BLB-Workflows | 38.9% | 79.6% | +40.7 |
| **Composite** | **55.0%** | **75.4%** | **+20.4** |

The 20-point composite gap between the current score and the estimated reasoning score represents the benchmark's infrastructure tax -- score depression attributable to document pipeline limitations rather than legal reasoning deficits. This gap is the single most important finding of our evaluation and the strongest argument for proposal A1.

---

### References

- Evaluation results: `results/summary.json`, `results/evaluation_report.txt`
- Design commentary: `COMMENTARY.md`
- BigLaw Bench methodology: [harvey.ai/blog/introducing-biglaw-bench](https://www.harvey.ai/blog/introducing-biglaw-bench)
- BLB: Arena: [harvey.ai/blog/introducing-biglaw-bench-arena](https://www.harvey.ai/blog/introducing-biglaw-bench-arena)
- LLM-as-Judge biases: [openreview.net](https://openreview.net/pdf/2da121049115d8ad916b671bcf7e28600eaf3679.pdf)
