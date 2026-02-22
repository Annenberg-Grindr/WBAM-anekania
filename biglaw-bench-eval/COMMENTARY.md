# BigLaw Bench: A Design Commentary

**Author:** WBAM Evaluation Team
**Date:** February 22, 2026
**Context:** Commentary written after running the BigLaw Bench evaluation suite against Claude Sonnet 4 (claude-sonnet-4-20250514), producing a composite score of 55.0% across BLB-Core (70.5%), BLB-Retrieval (55.7%), and BLB-Workflows (38.9%).

---

## 1. What BigLaw Bench Gets Right

BigLaw Bench (BLB) represents a genuine advance over prior legal AI benchmarks. Where earlier efforts like LegalBench and the bar exam multiple-choice tests evaluate pattern-matching on structured, closed-ended questions, BLB grounds its tasks in the kind of open-ended, document-intensive work that associates at large law firms actually bill for. Three design choices deserve credit:

**Grounding in time entries.** By mapping tasks to the billing taxonomy that organizes real legal work -- drafting, document review, negotiation analysis, trial preparation -- BLB measures something closer to economic value than academic aptitude. A model that scores well on BLB is, in principle, a model that could displace billable hours.

**Rubric-based scoring with affirmative and negative points.** Rather than binary correct/incorrect, BLB assigns partial credit for incomplete but useful work and deducts points for hallucinations and extraneous information. This mirrors how a supervising partner evaluates an associate's draft: good structure and partial coverage still has value, but fabricated citations destroy trust disproportionately.

**Use of real, publicly-sourced documents.** The benchmark draws on actual court filings, merger agreements, stock purchase agreements, and discovery materials. This forces models to grapple with the messiness of real legal prose -- defined terms, cross-references, exhibits, boilerplate variation -- rather than sanitized textbook excerpts.

## 2. The Self-Evaluation Problem

The most fundamental design issue with BLB is structural: Harvey AI created the benchmark, designed the rubrics, selected the tasks, and then published results showing its own fine-tuned models outperforming public foundation models. This is the equivalent of a test-prep company writing the SAT and then advertising that its students score highest.

Harvey has been transparent about this tension and has taken steps to mitigate it (publishing the methodology, releasing sample tasks on GitHub, introducing BLB: Arena with blind head-to-head comparisons). But the core conflict remains. The rubrics themselves embed judgment calls -- how many points a particular sub-task is worth, what counts as "extraneous" information, where the line falls between partial and full credit -- and these calls inevitably reflect the design priorities of the rubric author. A rubric written by Harvey's legal team will, even unconsciously, reward the kinds of outputs Harvey's models are trained to produce.

The legal AI ecosystem needs an independent benchmarking body, analogous to how NIST operates for cybersecurity standards or how LSAC administers the LSAT. Until then, BLB scores should be interpreted as one data point among many, not as a definitive ranking.

## 3. LLM-as-Judge: Grading Your Own Exam

Our evaluation used Claude Sonnet 4 as both the test-taker and the judge -- the same model in both roles. This is a known weakness of the LLM-as-judge paradigm, and it surfaces three specific biases:

**Self-enhancement bias.** Models tend to rate their own outputs more favorably than human evaluators would. When Claude judges Claude's legal memo, it is evaluating prose that shares its own distributional patterns, vocabulary choices, and reasoning style. Research has documented that this bias is statistically significant across model families.

**Verbosity bias.** LLM judges consistently prefer longer, more detailed responses even when conciseness would be more appropriate. In legal practice, a 10-page memo where a 3-page memo was called for is not better work -- it is worse work that wastes the client's time and money. BLB's rubrics do not penalize unnecessary length, and an LLM judge is unlikely to do so spontaneously.

**Positional and anchoring effects.** The order in which rubric items are presented, and the framing of the evaluation prompt, can shift scores by meaningful margins. Our evaluation pipeline presents the rubric after the response, which may anchor the judge toward finding alignment rather than gaps.

A more robust design would use a different (stronger) model as judge, or better yet, combine LLM evaluation with structured human review on a calibration subset. Harvey's BLB: Arena partially addresses this by using pairwise preference judgments rather than absolute rubric scoring, but the core evaluation still relies on automated grading.

## 4. Document Pipeline as Confound

Our evaluation revealed that the single largest driver of score variance was not model capability but document pipeline quality. Three examples:

- **Task #5 (Document Review):** Score 0.0% -- not because the model cannot analyze trial transcripts, but because all five source documents were scanned image PDFs with zero extractable text. The benchmark conflates OCR capability with legal reasoning.

- **BLB-Workflows (SPA Extraction):** Average 38.9% -- but extracted text was truncated to the first 18-27 pages of 60-120 page agreements. Fields like indemnification caps, governing law, and dispute resolution provisions appear in the back half of every SPA. The model scored ~80% on fields present in the extracted text.

- **BLB-Retrieval (Discovery Emails):** Average 49.0% -- but 4 of 10 queries referenced topics not present in the available corpus. The model cannot retrieve information from documents it was not given.

These are not failures of legal reasoning. They are failures of document ingestion. A well-designed benchmark should isolate the capability it claims to measure. BLB's design makes it impossible to distinguish "the model cannot do legal analysis" from "the PDF extraction pipeline dropped the relevant pages." This is a serious methodological flaw that inflates apparent performance gaps between models with different document-handling architectures.

**Recommendation:** BLB should report two scores for document-dependent tasks: a raw score (reflecting the full pipeline, including extraction), and an adjusted score (reflecting only tasks where the relevant text was confirmed available to the model). Without this distinction, the benchmark measures infrastructure as much as intelligence.

## 5. Task Coverage: A BigLaw-Shaped Hole

BLB's task taxonomy, while more realistic than prior benchmarks, has significant coverage gaps:

**Overrepresentation of transactional work.** Of the six core sample tasks, three are transactional (corporate strategy, drafting, negotiation) and two are litigation. Regulatory, tax, IP, employment, bankruptcy, and antitrust are absent or underrepresented. BigLaw practice is broader than M&A and securities litigation.

**Absence of multi-turn reasoning.** Every BLB task is a single prompt-response pair. Real legal work is iterative: a partner sends back a draft with comments, the associate revises, new facts emerge, the analysis shifts. The benchmark cannot measure a model's ability to incorporate feedback, update its analysis, or maintain consistency across a conversation.

**No adversarial testing.** BLB does not test whether models can be manipulated into producing incorrect legal advice through adversarial prompting, misleading document excerpts, or subtly incorrect premises embedded in the prompt. In practice, lawyers must spot when a question contains a false assumption. Models that score well on BLB might still be brittle under adversarial conditions.

**No jurisdictional variation (until 2026).** Until the recent BLB: Global expansion, the benchmark was exclusively US-focused. Even now, coverage of civil law jurisdictions, international arbitration, and cross-border transactions remains limited.

## 6. The Rubric Granularity Problem

BLB's rubrics vary significantly in granularity across tasks, creating inconsistent measurement precision:

- Task #49 (Board Consent Drafting): 9 maximum points across a relatively simple drafting exercise. Each rubric item is worth ~11% of the total.
- Task #19 (Merger Equity Memo): 23 maximum points across a complex analytical exercise. Each rubric item is worth ~4% of the total.

This means a single missed point on the drafting task has nearly three times the score impact of a single missed point on the merger memo. The composite score weights all tasks equally, but the rubrics do not have uniform resolution. A model that excels at high-granularity analytical tasks but misses one point on a low-granularity drafting task will appear to underperform relative to a model with the opposite profile.

**Recommendation:** Normalize scores by task complexity (measured by rubric granularity, document volume, or expected completion time) rather than treating all percentage scores as equivalent.

## 7. The Hallucination Asymmetry

BLB's negative scoring for hallucinations is directionally correct but poorly calibrated. The rubrics deduct -1 point per hallucination and -0.5 per piece of extraneous information. But on a task worth 23 positive points, a single hallucination costs 4.3% of the score. On a task worth 9 points, the same hallucination costs 11.1%.

More fundamentally, the benchmark does not distinguish between types of hallucination:

- **Fabricated citations** (citing a case that does not exist) -- catastrophic in practice, potential malpractice.
- **Incorrect legal conclusions** (misapplying a standard of review) -- serious but correctable through review.
- **Factual embellishments** (adding a detail not in the source documents) -- minor, often harmless.

BLB treats all three identically. A benchmark designed for BigLaw should weight hallucinations by their professional consequences, not apply a flat penalty. Harvey's published data showing hallucination rates of 0.2% (Harvey) to 1.3% (Gemini) is useful but obscures this severity dimension.

## 8. What Would a Better Benchmark Look Like?

Drawing on the limitations identified above, an improved legal AI benchmark would:

1. **Be administered by an independent body** with no commercial interest in model performance.

2. **Separate document handling from legal reasoning** by providing both raw PDFs and pre-extracted clean text, scoring each independently.

3. **Include multi-turn evaluation** where the model must revise work in response to partner feedback, incorporate new facts, and maintain consistency.

4. **Weight hallucinations by severity**, distinguishing fabricated authorities from minor factual embellishments.

5. **Normalize across tasks** so that a point on a 9-point rubric is not implicitly worth more than a point on a 23-point rubric.

6. **Include adversarial and edge-case tasks** testing robustness, not just best-case performance.

7. **Use a panel of human evaluators** for calibration, even if LLM-as-judge handles the bulk of scoring.

8. **Require confidence-calibrated responses**, testing not just accuracy but whether the model knows what it does not know -- a critical skill for lawyers.

9. **Cover the full breadth of BigLaw practice**, including regulatory, tax, IP, employment, restructuring, and cross-border work.

10. **Publish inter-rater reliability metrics** for both human and LLM judges, so users can assess how much scores depend on who (or what) is grading.

## 9. Conclusion

BigLaw Bench is the best publicly available benchmark for evaluating LLMs on realistic legal tasks. That is a low bar. The benchmark's core insight -- that legal AI should be measured against the work lawyers actually do, not against law school exam questions -- is correct and important. But its execution is compromised by the conflict of interest inherent in vendor-administered benchmarks, the well-documented flaws of LLM-as-judge evaluation, a document pipeline that confounds infrastructure with intelligence, inconsistent rubric granularity, and significant gaps in task coverage.

Our evaluation of Claude Sonnet 4 illustrates these limitations clearly. The composite score of 55.0% is misleading in both directions: it understates the model's legal reasoning ability (which is closer to 70-80% when measured only on tasks with clean document input) and overstates the benchmark's ability to measure legal reasoning in the first place (since roughly half the score variance comes from document pipeline artifacts rather than analytical quality).

BigLaw Bench is a useful starting point. It should not be mistaken for a finish line.

---

### Sources

- [Harvey AI: Introducing BigLaw Bench](https://www.harvey.ai/blog/introducing-biglaw-bench)
- [Harvey AI: Expanding BigLaw Bench](https://www.harvey.ai/blog/expanding-big-law-bench)
- [Harvey AI: BigLaw Bench Arena](https://www.harvey.ai/blog/introducing-biglaw-bench-arena)
- [Harvey AI: BigLaw Bench Sources](https://www.harvey.ai/blog/biglaw-bench-sources)
- [GitHub: harveyai/biglaw-bench](https://github.com/harveyai/biglaw-bench)
- [Artificial Lawyer: Harvey Launches Legal GenAI Evaluation System](https://www.artificiallawyer.com/2024/09/03/harvey-launches-legal-genai-evaluation-system-biglaw-bench/)
- [Artificial Lawyer: GPT-5 Tops BigLaw Bench Eval](https://www.artificiallawyer.com/2025/08/08/gpt-5-tops-harveys-biglaw-bench-eval/)
- [Legal IT Insider: The Gen AI LLM Benchmarking War Starts Here](https://legaltechnology.com/2024/09/03/the-gen-ai-llm-benchmarking-war-starts-here-harvey-releases-new-evaluation-framework/)
- [OpenReview: Are We on the Right Way for Assessing LLM](https://openreview.net/pdf/2da121049115d8ad916b671bcf7e28600eaf3679.pdf)
- [Evidently AI: LLM-as-a-Judge Complete Guide](https://www.evidentlyai.com/llm-guide/llm-as-a-judge)
- [LegalBench: Open Science Legal Reasoning Benchmark](https://hazyresearch.stanford.edu/legalbench/)
