# TenderWatch / TenderMatch
## Limitations and Mitigation Strategy

---

## 1. Current Limitations

### 1.1 Data and Scraping Limitations

Tender data is dispersed across hundreds of fragmented government and institutional portals, each with unique HTML structures, session management, and update cadences. Many portals employ CAPTCHA challenges and login barriers that obstruct automated retrieval, while others render content via JavaScript, requiring resource-intensive browser automation.

Tender documents frequently span 50 to 1,200+ pages and are delivered as complex PDFs. A significant proportion consist of scanned images rather than machine-readable text, producing OCR-dependent pipelines prone to noise. Inconsistent formatting — multi-column layouts, embedded tables, unnumbered annexures — further complicates reliable section identification prior to AI processing.

---

### 1.2 AI and LLM Limitations

Large language models carry an inherent hallucination risk: they may generate plausible but factually incorrect field values when source text is ambiguous or poorly structured. This is particularly dangerous for legally binding fields such as eligibility thresholds and mandatory certifications. Additionally, current context windows — even at 1M tokens — cannot reliably accommodate the largest tender documents in a single pass.

Chunking strategies introduced to address context limits risk severing logical continuity across clause cross-references and annexures. Precise extraction of eligibility criteria — which are often scattered, conditionally stated, and legally qualified — remains a challenging NLP task. Generating auditable, human-verifiable reasoning from probabilistic model outputs poses a further explainability challenge.

---

### 1.3 Matching and Scoring Limitations

Rule-based matching alone is rigid: it fails when a vendor's capabilities are semantically equivalent to tender requirements but expressed using different terminology. Conversely, pure embedding-based semantic similarity is too permissive and produces false positives by rewarding surface-level domain overlap without enforcing hard qualifications. Mandatory compliance criteria — such as minimum turnover, mandatory certifications, and geographic eligibility — require binary enforcement that neither approach handles reliably in isolation.

---

### 1.4 Notification and Feedback Constraints

The Meta WhatsApp Business API mandates pre-approved message templates for all outbound communications, restricting dynamic content and introducing approval latency of 24–72 hours. API rate limits prevent instantaneous bulk dispatch during high-volume tender publication events. In early deployment, sparse vendor feedback limits the system's ability to learn preference signals and refine match ranking. PoC-stage infrastructure constraints — including absent auto-scaling and simulated notification delivery — further bound real-world validation.

---

## 2. Our Strategy to Overcome These Limitations

### 2.1 Structured Data Ingestion Strategy

Rather than attempting universal portal coverage, the system targets a curated set of stable, high-yield portals in Phase 1. Playwright-based browser automation handles JavaScript-rendered and session-dependent sources; lightweight HTTP scrapers are used for static portals. All retrieved documents pass through a two-track processing pipeline: PyMuPDF for machine-readable PDFs and a Tesseract OCR pipeline — with DPI normalization, deskewing, and binarization — for scanned documents.

Before any LLM call, a rule-based and embedding-assisted section detector identifies and tags key document divisions (Eligibility, Scope, Financial Requirements, Deadlines). Only relevant sections are passed to the extraction model, substantially reducing token consumption and improving extraction precision. All outputs are stored in a normalized relational schema with full-text search indexing.

---

### 2.2 Controlled AI Extraction Strategy

LLM extraction operates on section-level chunks — not full documents — ensuring that each prompt contains contextually coherent input. The model is constrained to output a strict JSON schema with no freeform text; any field absent from the source document is returned as `null` with an explicit `"not_found"` flag. Every extracted value must include an evidence citation referencing the source page and section, enabling immediate human verification.

```json
{
  "eligibility": "Bidder must have completed two similar works of value >= INR 50L in the last 5 years.",
  "mandatory_certifications": ["ISO 9001:2015", "MNRE Empanelment"],
  "financial_threshold": "Average annual turnover >= INR 1 crore (last 3 years)",
  "location": "Pune, Maharashtra",
  "deadline": "2026-03-15T17:00:00+05:30",
  "evidence": { "page": 12, "section": "Section 3 – Eligibility Criteria" }
}
```

A hybrid validation layer cross-checks extracted numeric values against expected ranges and flags low-confidence outputs for human review before they enter the matching pipeline.

---

### 2.3 Hybrid Matching and Scoring Model

The matching engine applies a three-layer cascade to eliminate false positives progressively:

- **Layer 1 – Hard Rule Filter:** Mandatory binary checks (turnover threshold, required certifications, geographic eligibility). A vendor failing any hard filter is categorically excluded regardless of semantic similarity.
- **Layer 2 – Semantic Similarity:** Cosine similarity between vendor profile embeddings and tender requirement embeddings, computed in a shared sentence-transformer vector space.
- **Layer 3 – Keyword Boost:** Domain-specific keyword co-occurrence scoring applied as a precision signal over the semantic similarity result.

**Final Score:**

```
Final Score = 0.4 × Hard Rule Score + 0.4 × Semantic Similarity + 0.2 × Keyword Boost
```

This hybrid design ensures that no semantically similar but legally ineligible vendor receives a high match score. The hard filter enforces compliance as a precondition; semantic and keyword layers then rank eligible candidates by relevance.

---

### 2.4 Smart Notification and Feedback Design

Notifications are dispatched only when a match score exceeds a vendor-configured confidence threshold (default: 0.75), preventing low-quality alerts from reaching vendors. High-confidence matches trigger immediate push notifications; matches between 0.60 and 0.75 are batched into a daily digest, directly mitigating alert fatigue. WhatsApp communications operate on pre-registered templates; Email and SMS serve as high-flexibility fallback channels.

Vendor interactions — opens, clicks, dismissals, and explicit feedback — are captured as structured signals. These signals feed a dynamic weight adjustment mechanism that incrementally recalibrates scoring weights per vendor segment, improving recommendation quality over successive deployment cycles.

---

## Conclusion

The limitations inherent to large-scale tender processing — fragmented data sources, LLM uncertainty, matching imprecision, and notification constraints — are addressed not by avoiding complexity, but by designing explicit control mechanisms at each pipeline stage. Section-aware ingestion, evidence-grounded extraction, cascade filtering, and threshold-gated notifications collectively transform an otherwise brittle AI pipeline into a controlled, explainable, and auditable system. As vendor feedback accumulates and portal coverage expands across phases, the architecture is designed to scale both in data volume and recommendation accuracy, positioning TenderWatch as a production-ready procurement intelligence platform.

---

*TenderWatch / TenderMatch — Phase 1 PoC | February 2026*
