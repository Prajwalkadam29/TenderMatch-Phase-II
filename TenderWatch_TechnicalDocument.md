# TenderWatch / TenderMatch
## Intelligent Vendor–Tender Matching and Notification System Using GenAI and Agentic AI

---

**Document Type:** Technical Project Report  
**Version:** 1.0  
**Status:** Proof of Concept (Phase 1)  
**Date:** February 2026  
**Classification:** Academic / Internal Documentation  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Current Limitations](#3-current-limitations)
   - 3.1 [Data Source Limitations](#31-data-source-limitations)
   - 3.2 [AI and LLM Limitations](#32-ai-and-llm-limitations)
   - 3.3 [Matching Model Limitations](#33-matching-model-limitations)
   - 3.4 [Notification System Constraints](#34-notification-system-constraints)
   - 3.5 [PoC-Level Constraints](#35-poc-level-constraints)
4. [Implementation Strategy (Phase-Wise)](#4-implementation-strategy-phase-wise)
   - 4.1 [Phase 1 – Core System Foundation](#41-phase-1--core-system-foundation)
   - 4.2 [Phase 2 – AI Matching and Scoring Engine](#42-phase-2--ai-matching-and-scoring-engine)
   - 4.3 [Phase 3 – Notification and Alert System](#43-phase-3--notification-and-alert-system)
   - 4.4 [Phase 4 – Agentic AI and Autonomous Workflows](#44-phase-4--agentic-ai-and-autonomous-workflows)
   - 4.5 [Phase 5 – Production Hardening and Scale](#45-phase-5--production-hardening-and-scale)
5. [System Architecture](#5-system-architecture)
   - 5.1 [High-Level Architecture Overview](#51-high-level-architecture-overview)
   - 5.2 [Data Flow Diagram](#52-data-flow-diagram)
   - 5.3 [Technology Stack](#53-technology-stack)
6. [AI and Machine Learning Design](#6-ai-and-machine-learning-design)
   - 6.1 [Tender Extraction Pipeline](#61-tender-extraction-pipeline)
   - 6.2 [Matching Engine Design](#62-matching-engine-design)
   - 6.3 [Agentic AI Design](#63-agentic-ai-design)
7. [Key Features and Modules](#7-key-features-and-modules)
8. [Evaluation and Metrics](#8-evaluation-and-metrics)
9. [Ethical Considerations and Risk Mitigation](#9-ethical-considerations-and-risk-mitigation)
10. [Conclusion and Future Roadmap](#10-conclusion-and-future-roadmap)
11. [References](#11-references)

---

## 1. Executive Summary

### 1.1 Problem Overview

The government and enterprise procurement landscape is governed by a complex ecosystem of tenders, bids, and request-for-proposals (RFPs) dispersed across hundreds of fragmented portals at national, state, and municipal levels. Vendors — particularly small and medium enterprises (SMEs) — face the daunting task of manually monitoring these sources, parsing lengthy documents that often span 50 to 1,200 pages, and determining eligibility through dense legal and technical language. This results in missed opportunities, wasted resources, and systemic inefficiency in public procurement.

### 1.2 Proposed Solution

**TenderWatch / TenderMatch** is an AI-native, agentic system designed to automate the end-to-end process of tender discovery, structured information extraction, intelligent vendor–tender matching, and real-time notification delivery.

The system leverages:

- **Generative AI (GenAI):** For intelligent extraction of structured data from unstructured and semi-structured tender documents, including scanned PDFs.
- **Agentic AI:** For autonomous, multi-step workflows that monitor portals, retrieve documents, extract insights, match vendors, and dispatch alerts with minimal human intervention.
- **Hybrid Matching Models:** Combining semantic embeddings, rule-based hard filters, and weighted scoring to produce ranked, explainable match results.
- **Multi-Channel Notification:** Delivering actionable, context-rich alerts via WhatsApp, Email, and SMS.

### 1.3 Expected Impact

| Stakeholder | Expected Impact |
|---|---|
| SME Vendors | Reduced discovery time; higher bid participation rates |
| Large Enterprises | Automated screening of thousands of tenders per month |
| Procurement Portals | Increased discoverability of published tenders |
| Government Bodies | More competitive and inclusive bidding ecosystems |
| End Platform | Scalable SaaS revenue model through subscription tiers |

The system targets a reduction in tender discovery and screening effort by an estimated **70–85%**, enabling vendors to focus exclusively on tender preparation rather than reconnaissance.

---

## 2. Problem Statement

### 2.1 Fragmented Tender Portals

Government and institutional tenders in India and globally are published across a highly decentralized network of portals. These include the Central Public Procurement Portal (CPPP/GeM), state-level procurement portals, municipal corporation websites, NHAI, Railways, DRDO, and thousands of individual departmental websites. Each portal has its own structure, format, login requirements, and update cadence.

A vendor seeking relevant tenders must monitor 20–50+ distinct sources daily. There is no unified aggregation layer, and cross-portal deduplication remains unsolved at scale.

### 2.2 Document Complexity and Volume

Tender documents are inherently complex artifacts. They may include:

- Eligibility criteria spread across multiple sections and annexures
- Financial qualification thresholds expressed in diverse formats
- Mandatory certifications referenced by obscure regulatory codes
- Terms and conditions embedded within legal schedules
- Cross-referenced clauses that require full document comprehension

A single active tender may consist of 50 to 1,200 pages across multiple attached documents. Manual review is time-intensive, error-prone, and impractical when dealing with hundreds of active tenders simultaneously.

### 2.3 Manual Eligibility Checking

Current practice requires procurement officers or vendor representatives to manually cross-reference their organization's qualifications against each tender's eligibility matrix. This includes:

- Verifying past project experience and value thresholds
- Checking applicable ISO, BIS, or domain-specific certifications
- Validating financial metrics such as average annual turnover or net worth
- Confirming geographic jurisdiction and joint venture eligibility

This manual process is estimated to require 2–6 person-hours per tender, making it economically unviable to screen more than a handful of opportunities per week.

### 2.4 Missed Tender Opportunities

Given the manual nature of discovery and screening, vendors systematically miss relevant tenders due to:

- Portal monitoring gaps during weekends or holidays
- Alerts set up for keywords that do not match tender terminology
- Submission deadlines passing before document review is completed
- Inability to track amendments or corrigenda to previously reviewed tenders

The compounded effect of these gaps results in quantifiably lower bid participation rates, particularly among SMEs with limited dedicated procurement teams.

### 2.5 Need for Intelligent Automation

The convergence of large language models (LLMs), agentic AI frameworks, vector databases, and real-time notification APIs presents a unique opportunity to automate this domain end to end. An intelligent system can:

- Continuously monitor and scrape tender portals
- Extract structured metadata from complex documents using LLMs
- Match vendor capability profiles against extracted tender requirements
- Rank and score matches with explainable confidence weights
- Deliver timely, personalized alerts through preferred communication channels

TenderWatch is designed to translate this opportunity into a practical, deployable system.

---

## 3. Current Limitations

A clear-eyed understanding of current limitations is essential for setting accurate expectations and designing appropriate mitigation strategies. The following limitations are organized by system domain.

---

### 3.1 Data Source Limitations

#### 3.1.1 Fragmented and Siloed Portals

No standardized API exists for accessing tender data across Indian government portals. Each portal requires custom scraping adapters. Portal structure changes frequently without notice, causing scraper failures. The maintenance overhead for supporting more than 5–10 portals simultaneously is significant.

#### 3.1.2 CAPTCHA and Login Barriers

Several portals implement CAPTCHA challenges, OTP-based authentication, or session-cookie-dependent navigation flows. These mechanisms are designed to prevent automated crawling, and they impose hard barriers to scraping without browser automation tools such as Playwright or Selenium. Even with browser automation, CAPTCHAs remain a persistent and evolving barrier.

#### 3.1.3 Dynamic Website Structures

An increasing number of portals are built using JavaScript-heavy single-page application (SPA) frameworks. Traditional HTML-based scrapers fail to retrieve content that is rendered client-side via JavaScript. Browser headless instances consume significantly more compute resources than lightweight HTTP crawlers.

#### 3.1.4 PDF Complexity

Tender documents are delivered primarily in PDF format. However, these PDFs exhibit a wide range of structures:

- Digitally typeset, machine-readable PDFs
- Scanned physical documents embedded as image pages
- Mixed documents combining typewritten and handwritten annotations
- Multi-column layouts and tables without clear semantic markup

Standard PDF text extraction libraries (e.g., PyMuPDF, PDFMiner) perform well on machine-readable PDFs but fail entirely on scanned documents, requiring Optical Character Recognition (OCR) pipelines.

#### 3.1.5 Scanned Documents and OCR Accuracy

OCR-based text extraction introduces a non-trivial error rate, particularly with:

- Low-resolution scans (below 150 DPI)
- Documents containing regional language annotations
- Stamps, watermarks, or handwritten amendments overlaid on printed text
- Tables and structured forms that do not map cleanly to sequential text

OCR errors propagate downstream into the LLM extraction pipeline, potentially causing incorrect or missing field values in the structured output.

---

### 3.2 AI and LLM Limitations

#### 3.2.1 Hallucination Risk

Large language models can generate plausible-sounding but factually incorrect responses, particularly when the source document is ambiguous, poorly formatted, or outside the model's training distribution. In the tender extraction context, a hallucinated eligibility criterion or financial threshold could result in a vendor submitting a non-compliant bid. Mitigation requires evidence grounding, confidence scoring, and human-in-the-loop validation for high-stakes fields.

#### 3.2.2 Context Window Limitations

Current commercially available LLMs (including GPT-4 Turbo, Claude 3, and Gemini 1.5 Pro) support context windows ranging from 32K to 1M tokens. However, a 500-page tender PDF may exceed even the largest available context window when converted to plain text. This necessitates document chunking strategies, which introduce the risk of losing cross-chunk contextual dependencies between clauses and referenced annexures.

#### 3.2.3 Chunking and Boundary Issues

When a tender document is split into chunks for sequential or parallel processing:

- Eligibility criteria that span multiple pages may be split across chunk boundaries
- Cross-references between clauses (e.g., "refer to Annexure B, Clause 4") may not resolve within a single chunk
- Tables and structured lists may be fragmented, losing their relational meaning

Intelligent chunking strategies — such as section-aware splitting based on detected headings — partially mitigate this issue but require robust document structure detection.

#### 3.2.4 Explainability Challenges

LLM-based extraction and matching decisions are inherently opaque. Vendors require clear justification for why a specific tender was matched or rejected. Producing explainable, auditable reasoning from a probabilistic language model is non-trivial and requires careful prompt engineering and output structuring.

---

### 3.3 Matching Model Limitations

#### 3.3.1 Pure Rule-Based Matching Rigidity

A rule-based matching approach — for example, exact keyword matching between vendor capabilities and tender categories — is fragile and low-recall. It fails to capture semantic similarity between vendor experience described in natural language and tender requirements expressed using different terminology (e.g., "civil construction" vs. "infrastructure development").

#### 3.3.2 Pure Embedding-Based Matching Looseness

Semantic embedding-based matching (e.g., cosine similarity of text embeddings) provides high recall but low precision. A vendor with general IT experience may score highly against a specialized cybersecurity tender due to surface-level semantic overlap. Without hard eligibility filters enforced as pre-conditions, this approach generates an unacceptably high rate of false positives.

#### 3.3.3 Mandatory Eligibility Handling Difficulty

Certain eligibility criteria are mandatory go/no-go conditions — a vendor either satisfies them or is categorically disqualified. These include:

- Minimum annual turnover thresholds
- Mandatory ISO certifications
- Mandatory past project experience in a specific domain
- Government registration and enrollment requirements

Hybrid matching systems must enforce these mandatory criteria as hard filters before applying weighted scoring to remaining criteria. Designing and maintaining this two-phase filter-then-score pipeline adds architectural complexity.

---

### 3.4 Notification System Constraints

#### 3.4.1 WhatsApp Template Approval Process

The WhatsApp Business API (accessed via Meta) requires all outbound message templates containing marketing or transactional content to be pre-approved by Meta. The approval process may take 24–72 hours and can be rejected for policy violations. This prevents the system from sending dynamic, ad-hoc messages and constrains notification content to pre-approved template formats.

#### 3.4.2 API Rate Limits

Cloud notification APIs — including WhatsApp Business API, SendGrid (Email), and Twilio (SMS) — impose rate limits on message dispatch. High-velocity notification events (e.g., 200 tenders published simultaneously across multiple portals) cannot be delivered instantaneously and must be queued and rate-limited, potentially delaying time-sensitive alerts.

#### 3.4.3 Alert Fatigue

If the matching system generates a high volume of notifications — particularly low-confidence matches — vendors may disengage from the notification channel over time. Alert fatigue is a well-documented behavioral phenomenon. The system must implement intelligent notification thresholds, vendor-defined frequency preferences, and confidence score minimums to prevent notification overload.

---

### 3.5 PoC-Level Constraints

#### 3.5.1 Limited Tender Source Coverage

The Phase 1 Proof of Concept targets a controlled subset of tender portals — specifically 2–3 known stable sources with predictable HTML structure. Full multi-portal coverage requires significantly higher engineering investment and is deferred to subsequent phases.

#### 3.5.2 No Production Deployment

The Phase 1 system operates in a local or development environment. It has not been hardened for production-grade reliability, security, or compliance requirements. There is no SLA guarantee, auto-scaling, or disaster recovery provision at this stage.

#### 3.5.3 Simulated Notifications

In the PoC phase, end-to-end notification delivery via WhatsApp Business API is simulated using test environments or stub integrations. Real template approval, rate limit handling, and delivery receipts are deferred to the production integration phase.

#### 3.5.4 Vendor Profile Scope

The PoC onboards a manually curated set of vendor profiles for demonstration and evaluation purposes. Automated profile ingestion, enrichment, and maintenance pipelines are not implemented in Phase 1.

---

## 4. Implementation Strategy (Phase-Wise)

The system is designed using an iterative, phase-gated delivery model. Each phase builds upon the previous, with clearly defined scope, deliverables, and validation criteria.

---

### 4.1 Phase 1 – Core System Foundation

**Objective:** Establish the foundational data pipeline and AI extraction engine. Validate the end-to-end workflow on a controlled dataset.

**Duration:** 6–8 weeks

#### 4.1.1 Vendor Profiling and Onboarding

A structured, form-based onboarding interface is implemented to capture vendor capability profiles. The schema captures:

| Field | Description |
|---|---|
| Organization Name | Legal entity name |
| Registration Type | Sole Proprietor / Pvt. Ltd / LLP / Partnership |
| Business Domains | Multi-select from a controlled taxonomy |
| Certifications | ISO, BIS, NSIC, MSME, and domain-specific certifications |
| Annual Turnover | Self-declared financial bracket |
| Past Project Experience | Domain, value, and client type |
| Geographic Presence | State(s) and regions of operation |
| Preferred Tender Categories | CPV codes or free-text domain preferences |
| Notification Preferences | Channel (WhatsApp/Email/SMS), frequency, confidence threshold |

Profiles are stored in a structured relational schema. A JSON representation of a vendor profile is maintained for compatibility with the matching engine.

#### 4.1.2 Tender Scraping and Storage

A modular scraping framework is implemented using headless browser automation (Playwright) for JavaScript-rendered portals and lightweight HTTP requests with BeautifulSoup for static HTML portals. The scraper:

- Polls configured portal sources on a defined schedule (e.g., every 4 hours)
- Detects new or updated tender listings via hash comparison
- Downloads associated tender documents (PDF, DOCX)
- Stores raw documents and extracted metadata in a structured database
- Logs scrape attempts, success rates, and failure reasons

#### 4.1.3 PDF Text Extraction

The document processing pipeline applies a two-track extraction strategy:

- **Track A (Digitally typed PDFs):** PyMuPDF or pdfplumber are used for high-fidelity text and table extraction, preserving structure and page number references.
- **Track B (Scanned PDFs):** Tesseract OCR (or a cloud OCR API such as Google Document AI) is applied after DPI normalization and image preprocessing (deskewing, denoising, binarization).

The extracted text is stored per-page with page number metadata for downstream evidence grounding.

#### 4.1.4 Section Detection Logic

A rule-based and embedding-assisted section detector identifies key document sections, including:

- Scope of Work / Technical Specifications
- Eligibility and Qualification Criteria
- Financial Requirements
- Mandatory Certifications
- Submission Instructions and Deadlines
- Terms and Conditions

Detected sections are tagged and passed as prioritized input to the AI extraction module.

#### 4.1.5 Controlled AI Extraction

A prompted LLM (operating via API, e.g., OpenAI GPT-4 or Google Gemini) extracts structured fields from detected sections. The extraction prompt enforces:

- Field-specific extraction with explicit evidence citation
- Strict JSON output format
- Uncertainty flags for ambiguous or missing information
- Prohibition of inference beyond the document's explicit content

#### 4.1.6 Structured JSON Output with Evidence

The extracted tender data is stored in the following canonical JSON schema:

```json
{
  "tender_id": "TW-2026-00847",
  "source_portal": "cppp.nic.in",
  "scraped_at": "2026-02-25T14:32:00Z",
  "document_hash": "sha256:a3f4c9...",
  "eligibility": "The bidder must have successfully completed at least two similar works of value not less than INR 50 lakhs each during the last five years.",
  "scope_summary": "Supply, installation, testing, and commissioning of solar rooftop panels of 50 kWp capacity at Government Medical College, Pune.",
  "mandatory_certifications": [
    "MNRE Empanelment Certificate",
    "ISO 9001:2015",
    "BIS Certification for Solar PV Modules (IS 14286)"
  ],
  "financial_threshold": {
    "annual_turnover": "INR 1 crore minimum (average of last 3 financial years)",
    "net_worth": "Positive net worth as per last audited balance sheet"
  },
  "location": "Government Medical College, Pune, Maharashtra",
  "deadline": {
    "bid_submission": "2026-03-15T17:00:00+05:30",
    "pre_bid_meeting": "2026-03-05T11:00:00+05:30"
  },
  "tender_value_estimate": "INR 42,00,000",
  "category": "Renewable Energy / Solar",
  "cpv_codes": ["09332000", "45261215"],
  "amendments": [],
  "extraction_confidence": 0.91,
  "extraction_flags": [],
  "evidence": {
    "eligibility": {
      "page": 12,
      "section": "Section 3 – Eligibility Criteria",
      "verbatim_excerpt": "The bidder must have successfully completed at least two similar works..."
    },
    "financial_threshold": {
      "page": 14,
      "section": "Section 4 – Financial Qualifications",
      "verbatim_excerpt": "Average Annual Turnover of at least INR 1 Crore..."
    },
    "mandatory_certifications": {
      "page": 16,
      "section": "Annexure A – Certifications Required",
      "verbatim_excerpt": "MNRE Empanelment, ISO 9001:2015, BIS IS 14286..."
    }
  }
}
```

Each extracted field is traceable to a specific page and section of the source document, enabling human validators to verify the extraction accuracy.

---

### 4.2 Phase 2 – AI Matching and Scoring Engine

**Objective:** Implement the hybrid vendor–tender matching engine capable of producing ranked, explainable match results.

**Duration:** 4–6 weeks

#### 4.2.1 Vendor Profile Embedding

Vendor capability profiles are embedded into a high-dimensional vector space using a domain-adapted sentence transformer model. The embedding captures:

- Business domain descriptions
- Past project summaries
- Certification listings
- Geographic coverage

Embeddings are stored in a vector database (e.g., Pinecone, Chroma, or Qdrant) for efficient approximate nearest-neighbor retrieval.

#### 4.2.2 Tender Requirement Embedding

Extracted tender fields — specifically scope summary, eligibility criteria, and required certifications — are embedded using the same model to ensure semantic compatibility in the shared vector space.

#### 4.2.3 Hard Filter Layer (Mandatory Eligibility)

Before scoring, mandatory eligibility criteria are enforced as binary pass/fail filters:

| Filter | Logic |
|---|---|
| Annual Turnover | Vendor declared turnover >= threshold extracted from tender |
| Geographic Presence | Vendor registered state intersects with tender location state |
| Mandatory Certifications | All mandatory certifications are present in vendor profile |
| Business Domain | Vendor's primary domain intersects with tender category |

Tenders that fail any hard filter are excluded from scoring and flagged as "Ineligible – Reason: [specific criterion]."

#### 4.2.4 Weighted Scoring Layer

Tenders passing the hard filter are scored using a weighted multi-criteria function:

| Criterion | Weight | Scoring Method |
|---|---|---|
| Domain Semantic Similarity | 35% | Cosine similarity of embeddings |
| Certification Match | 25% | Jaccard similarity on certification sets |
| Financial Capacity | 20% | Ratio-based scoring with soft upper threshold |
| Geographic Alignment | 10% | Exact match or proximity scoring |
| Experience Alignment | 10% | LLM-assisted relevance scoring |

The final match score is a weighted linear combination, normalized to a [0, 1] range.

#### 4.2.5 Explainability Output

Each match result includes a human-readable explanation of the contributing factors:

```json
{
  "vendor_id": "V-00234",
  "tender_id": "TW-2026-00847",
  "match_score": 0.87,
  "eligibility_status": "Eligible",
  "score_breakdown": {
    "domain_similarity": 0.91,
    "certification_match": 0.80,
    "financial_capacity": 0.85,
    "geographic_alignment": 1.00,
    "experience_alignment": 0.78
  },
  "recommendation": "High match. The vendor's solar EPC experience and MNRE empanelment align closely with tender requirements.",
  "disqualifying_factors": [],
  "advisory_flags": [
    "Verify ISO 9001:2015 certificate validity before bid submission."
  ]
}
```

---

### 4.3 Phase 3 – Notification and Alert System

**Objective:** Implement a multi-channel notification system with intelligent routing, templating, and delivery management.

**Duration:** 3–4 weeks

#### 4.3.1 Notification Trigger Logic

A notification is dispatched when:

- A new tender is matched to a vendor with a score above the vendor's configured threshold (default: 0.75)
- A corrigendum or amendment is published for a tender previously matched to a vendor
- A submission deadline approaches within the vendor's configured lead-time window (default: 72 hours)

#### 4.3.2 Channel Integration

| Channel | Integration | Template Requirement |
|---|---|---|
| WhatsApp | Meta WhatsApp Business API | Pre-approved template required |
| Email | SendGrid / AWS SES | Dynamic templates supported |
| SMS | Twilio / MSG91 | DLT-registered sender ID required |

#### 4.3.3 Notification Payload

Each notification includes:

- Tender title and reference number
- Publication date and submission deadline
- Match score and primary matching reasons
- Direct link to the tender document
- One-click action links for viewing full details in the TenderWatch dashboard

#### 4.3.4 Alert Fatigue Prevention

- Vendors configure a maximum notification frequency (per day / per week)
- Notifications below a configured confidence threshold are batched into a daily digest
- An unsubscribe and preference management interface is provided

---

### 4.4 Phase 4 – Agentic AI and Autonomous Workflows

**Objective:** Introduce multi-agent, autonomous workflow capabilities to reduce human intervention at every stage of the pipeline.

**Duration:** 5–7 weeks

#### 4.4.1 Agent Architecture

The agentic layer is implemented using a framework such as LangGraph, AutoGen, or CrewAI. The following specialized agents are defined:

| Agent | Responsibility |
|---|---|
| Portal Monitor Agent | Autonomous portal scanning and change detection |
| Document Retrieval Agent | Document download, format detection, and pre-processing |
| Extraction Agent | LLM-driven structured data extraction from documents |
| Eligibility Analyst Agent | Cross-referencing tender criteria against vendor profiles |
| Scoring Agent | Computing weighted match scores and generating explanations |
| Notification Agent | Composing and dispatching alerts via configured channels |
| Feedback Agent | Learning from vendor feedback to improve future recommendations |

#### 4.4.2 Agent Communication Protocol

Agents communicate via a shared message queue (e.g., Redis Streams or Celery). Each agent consumes tasks from its designated queue, processes them, and publishes results to downstream queues. This decoupled architecture enables horizontal scaling of individual agents based on workload.

#### 4.4.3 Human-in-the-Loop Checkpoints

Despite the autonomous design, human-in-the-loop checkpoints are enforced for:

- Tenders flagged with extraction confidence below 0.70
- Matches where mandatory eligibility status is ambiguous
- Any tender above a configurable financial value threshold

---

### 4.5 Phase 5 – Production Hardening and Scale

**Objective:** Prepare the system for production deployment with enterprise-grade reliability, security, and compliance.

**Duration:** 6–10 weeks

#### Key Activities

- Cloud deployment on AWS / GCP / Azure with auto-scaling infrastructure
- Database replication and backup strategies
- API security: OAuth 2.0, rate limiting, and input sanitization
- GDPR and IT Act compliance review for data handling
- Monitoring, alerting, and SLA dashboards (via Grafana / Datadog)
- Multi-tenant onboarding for enterprise clients
- Custom scraper development for additional portal sources

---

## 5. System Architecture

### 5.1 High-Level Architecture Overview

The TenderWatch system is organized into eight functional layers:

```
Layer 1: Data Sources
  |-- Government Portals (GeM, CPPP, State Portals)
  |-- Institutional Portals (NHAI, Railways, DRDO)
  |-- Direct Document Uploads

Layer 2: Ingestion and Scraping Layer
  |-- Portal Monitor Agents (Playwright / BeautifulSoup)
  |-- Document Downloader
  |-- Deduplication Engine (Hash Comparison)

Layer 3: Document Processing Pipeline
  |-- PDF Classifier (Typed vs. Scanned)
  |-- Text Extractor (PyMuPDF / Tesseract OCR)
  |-- Section Detector
  |-- Chunk Generator

Layer 4: AI Extraction Engine
  |-- LLM Extraction API (GPT-4 / Gemini)
  |-- Prompt Management Layer
  |-- Evidence Grounding Module
  |-- Confidence Scorer
  |-- Structured JSON Output Store

Layer 5: Vendor Profile Store
  |-- Structured Profile Database (PostgreSQL)
  |-- Embedding Index (Chroma / Pinecone)
  |-- Profile Evolution Tracker

Layer 6: Matching Engine
  |-- Hard Filter Layer (Rule-Based Eligibility)
  |-- Semantic Scoring Layer (Embedding Similarity)
  |-- Multi-Criteria Weighted Scorer
  |-- Explainability Module

Layer 7: Notification System
  |-- Trigger Engine
  |-- Channel Router (WhatsApp / Email / SMS)
  |-- Template Manager
  |-- Delivery Tracker

Layer 8: Frontend Dashboard (TenderMatch UI)
  |-- Vendor Onboarding Interface
  |-- Tender Discovery Feed
  |-- Match Results View with Explainability
  |-- Notification Preference Management
  |-- Admin Analytics Dashboard
```

### 5.2 Data Flow Diagram

```
[Portal Sources]
      |
      v
[Portal Monitor Agents] ---> [Document Download Queue]
                                       |
                                       v
                             [PDF Processing Pipeline]
                             (Classify --> Extract --> Detect Sections --> Chunk)
                                       |
                                       v
                             [LLM Extraction Engine]
                             (Structured JSON + Evidence)
                                       |
                                       v
                             [Tender Database]   <---  [Vendor Profile Store]
                                       |                        |
                                       v                        v
                             [Matching Engine] ----------> [Match Results]
                                       |
                                       v
                             [Notification Engine]
                                       |
                           ________________________
                           |           |           |
                           v           v           v
                      [WhatsApp]   [Email]      [SMS]
                                       |
                                       v
                             [Vendor Dashboard]
```

### 5.3 Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React (TypeScript), Vite, CSS Modules, Framer Motion |
| Backend API | Python (FastAPI) |
| Scraping | Playwright, BeautifulSoup4, Scrapy |
| PDF Processing | PyMuPDF, pdfplumber, Tesseract OCR, Google Document AI |
| AI / LLM | OpenAI GPT-4 API / Google Gemini API |
| Embedding Model | Sentence Transformers (all-mpnet-base-v2) |
| Vector Database | Chroma DB / Pinecone |
| Relational Database | PostgreSQL |
| Task Queue | Celery + Redis |
| Notification – WhatsApp | Meta WhatsApp Business API |
| Notification – Email | SendGrid |
| Notification – SMS | Twilio |
| Agent Framework | LangGraph / CrewAI |
| Deployment | Docker, Kubernetes, AWS / GCP |
| Monitoring | Grafana, Datadog |

---

## 6. AI and Machine Learning Design

### 6.1 Tender Extraction Pipeline

#### Extraction Prompt Engineering

The extraction prompt is designed using a structured, constrained template. Key directives include:

- Extract only information explicitly stated in the provided document excerpt
- Output must conform strictly to the defined JSON schema
- If a field is not found, return `null` with a flag value of `"not_found"`
- Cite the page number and section header for every extracted field
- Do not infer, extrapolate, or paraphrase beyond the source text

#### Confidence Scoring

Each extracted field receives an individual confidence score based on:

- Clarity and specificity of the source statement
- Whether the extracted value is in an expected format
- Absence of contraindication in other document sections
- OCR quality score (for scanned documents)

### 6.2 Matching Engine Design

The matching engine implements a cascade architecture:

```
Stage 1: Domain Pre-Filter (Keyword / Category Match)
    |
    v
Stage 2: Hard Eligibility Filter (Rule-Based Binary)
    |
    v
Stage 3: Semantic Similarity Scoring (Embedding Cosine)
    |
    v
Stage 4: Multi-Criteria Weighted Scoring
    |
    v
Stage 5: Explainability Generation (LLM Summary)
    |
    v
Stage 6: Ranked Match Output
```

### 6.3 Agentic AI Design

The agentic layer implements a **supervisor-worker** architecture:

- A **Supervisor Agent** receives high-level objectives (e.g., "Process all new tenders published in the last 24 hours") and decomposes them into task queues.
- **Specialist Worker Agents** execute defined subtasks and return structured results to the Supervisor.
- A **Memory Module** (backed by a vector store) enables agents to retain and retrieve context from prior task executions.
- A **Tool Registry** defines the set of permissioned actions each agent may perform, enforcing security and scope boundaries.

---

## 7. Key Features and Modules

| Feature | Description | Phase |
|---|---|---|
| Vendor Onboarding | Structured profile capture with domain taxonomy | Phase 1 |
| Portal Scraper | Multi-portal tender discovery and document retrieval | Phase 1 |
| PDF Processor | Hybrid typed/scanned document extraction | Phase 1 |
| AI Extractor | LLM-based structured field extraction with evidence | Phase 1 |
| Tender Database | Normalized storage with full-text search | Phase 1 |
| Hard Filter Matcher | Mandatory eligibility enforcement | Phase 2 |
| Semantic Matcher | Embedding-based domain similarity scoring | Phase 2 |
| Explainability Engine | Human-readable match justification | Phase 2 |
| WhatsApp Notifier | Real-time tender alerts via WhatsApp Business API | Phase 3 |
| Email / SMS Notifier | Multi-channel fallback notification delivery | Phase 3 |
| Alert Preference Manager | Frequency and threshold controls per vendor | Phase 3 |
| Portal Monitor Agent | Autonomous, scheduled portal surveillance | Phase 4 |
| Extraction Agent | Autonomous document processing pipeline | Phase 4 |
| Feedback Learning Agent | Match improvement via vendor feedback signals | Phase 4 |
| Dashboard Analytics | Tender pipeline, match rates, and conversion metrics | Phase 4 |
| Multi-Tenant SaaS | Enterprise subscription and access tier management | Phase 5 |

---

## 8. Evaluation and Metrics

### 8.1 Extraction Quality Metrics

| Metric | Target (Phase 1 PoC) |
|---|---|
| Field Extraction Accuracy | > 85% (on labeled test set) |
| Evidence Grounding Rate | > 90% of extracted fields have valid citations |
| Hallucination Rate | < 5% of total extracted field values |
| OCR-to-Extraction Success Rate | > 75% on scanned documents |

### 8.2 Matching Performance Metrics

| Metric | Target |
|---|---|
| Precision at K=5 | > 80% (top 5 matches are relevant) |
| Recall of Relevant Tenders | > 70% of truly eligible tenders returned |
| False Positive Rate | < 20% of served matches are ineligible |
| Hard Filter Accuracy | 100% (no ineligible vendor passes a mandatory filter) |

### 8.3 Notification Effectiveness Metrics

| Metric | Target |
|---|---|
| Delivery Success Rate | > 97% (Email) |
| Alert Open Rate | > 40% (WhatsApp) |
| Click-through Rate | > 25% (link to dashboard) |
| Unsubscribe Rate | < 5% per month |

### 8.4 System Performance Metrics

| Metric | Target |
|---|---|
| End-to-End Processing Latency (per tender) | < 90 seconds |
| Notification Dispatch Latency (after match) | < 5 minutes |
| Portal Scrape Success Rate | > 95% |
| System Uptime (Phase 3+) | > 99.5% |

---

## 9. Ethical Considerations and Risk Mitigation

### 9.1 Data Privacy and Vendor Confidentiality

Vendor profiles contain commercially sensitive information including financial thresholds, certification statuses, and past project values. The system must enforce:

- Role-based access controls (RBAC) ensuring vendor data is visible only to the vendor and authorized administrators
- Encryption at rest (AES-256) and in transit (TLS 1.2+) for all vendor profile data
- Data retention policies with explicit vendor consent and deletion rights

### 9.2 AI Fairness and Non-Discrimination

The matching engine must not systematically disadvantage vendors based on characteristics unrelated to tender eligibility, including organization size, region of origin, or ownership type. Regular fairness audits of match score distributions across vendor segments are recommended.

### 9.3 Hallucination and Error Accountability

Given the financial and legal consequences of acting on incorrect tender information, the system implements:

- Mandatory evidence citation for all AI-extracted fields
- Confidence score thresholds below which human review is required
- Clear disclaimers that AI-extracted information must be verified against the original tender document before submission

### 9.4 Portal Terms of Service Compliance

Automated scraping of government portals must be conducted in compliance with the portal's stated terms of service and applicable legal frameworks. Where portals provide official APIs or data feeds, these must be prioritized over web scraping. Scraping must be rate-limited to avoid disruption to portal services.

---

## 10. Conclusion and Future Roadmap

### 10.1 Summary

TenderWatch / TenderMatch represents a substantive application of Generative AI and Agentic AI to a high-value, underserved problem in the public procurement domain. By automating tender discovery, structured extraction, intelligent matching, and real-time notification, the system has the potential to transform how vendors — particularly SMEs — participate in government and institutional procurement. The Phase 1 PoC establishes the technical foundation and validates the core AI pipeline.

### 10.2 Future Enhancements

| Enhancement | Description | Target Phase |
|---|---|---|
| Multi-Language Support | Tender extraction in Hindi, Marathi, Tamil, and other regional languages | Phase 3 |
| Bid Document Preparation Assist | AI-assisted generation of eligibility declarations and bid forms | Phase 4 |
| Tender Analytics Dashboard | Market intelligence on tender trends, winning bid patterns | Phase 4 |
| Blockchain Audit Trail | Immutable logging of extraction and matching decisions for compliance | Phase 5 |
| API Marketplace | Public API for third-party integration with ERP and procurement platforms | Phase 5 |
| Vendor Capability Growth Advisor | AI recommendations on certifications or experience to pursue for higher match rates | Phase 5 |
| Corrigendum Tracker | Automated detection and notification of tender amendments and corrections | Phase 3 |
| Comparative Bid Intelligence | Benchmarking past bid results to inform competitive pricing strategy | Phase 5 |

### 10.3 Strategic Vision

The long-term vision for TenderWatch is to become the definitive AI-native procurement intelligence layer for the Indian public sector, eventually expanding to cover ASEAN and emerging market procurement ecosystems. The system's modular, agent-based architecture positions it for extensibility across verticals including defense, healthcare, infrastructure, and IT services procurement.

---

## 11. References

1. Government of India, Central Public Procurement Portal. *GeM – Government e-Marketplace*. Available at: https://gem.gov.in
2. Government of India, Ministry of Finance. *Central Public Procurement Portal (CPPP)*. Available at: https://eprocure.gov.in
3. OpenAI. *GPT-4 Technical Report*. OpenAI, 2023.
4. Google DeepMind. *Gemini: A Family of Highly Capable Multimodal Models*. Google, 2023.
5. Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. EMNLP 2019.
6. Chase, H. *LangChain: Building Applications with LLMs*. LangChain, 2023. Available at: https://langchain.com
7. Meta. *WhatsApp Business API Documentation*. Meta for Developers, 2024. Available at: https://developers.facebook.com/docs/whatsapp
8. Rajpurkar, P., et al. (2016). *SQuAD: 100,000+ Questions for Machine Comprehension of Text*. EMNLP 2016.
9. Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS 2020.
10. European Commission. *Directive 2014/24/EU on Public Procurement*. Official Journal of the European Union, 2014.

---

*End of Document*

---

**Document Control**

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | February 2026 | TenderWatch Project Team | Initial Draft |
| 1.0 | February 2026 | TenderWatch Project Team | Final PoC Documentation |

---

*This document is intended for academic, evaluation, and internal technical purposes. All AI-extracted information presented in examples is illustrative and does not represent actual tender data.*
