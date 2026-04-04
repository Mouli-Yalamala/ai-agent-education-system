# AI Agent Educational Content Pipeline

This repository contains a modular AI agent pipeline that automatically generates, reviews, and refines educational content. The system uses a FastAPI backend to orchestrate interactions with the Groq API, and a React frontend for the user interface.

## Live Demo
**https://ai-agent-education-system.vercel.app/**

**CRITICAL NOTE FOR REVIEWERS:** 
The API backend is hosted on a free-tier cloud service which automatically spins down after periods of inactivity. **The very first time you click "Generate," it may take up to 60 seconds for the backend server to wake up.** Please be patient during the first generation! Subsequent requests will be instantaneous.

## Agent Roles
1. **Generator Agent**: The primary drafting agent. Receives parameters (grade, topic) to create educational artifacts (Explanation, MCQs, Teacher notes). Restricts output to strict JSON Pydantic schemas. Includes a built-in 1-time fallback retry for JSON malformations.
2. **Reviewer Agent (Gatekeeper)**: Quantitatively evaluates the Generator's draft across 4 distinct criteria (Age Appropriateness, Correctness, Clarity, Coverage) on a strict 1-5 scale. Outputs targeted, actionable feedback mapping specific JSON fields.
3. **Refiner Agent**: Takes the reviewer's targeted feedback and executes surgical improvements. Hard-capped to a maximum of 2 refinement attempts to prevent infinite hallucination loops.
4. **Tagger Agent**: A robust analytical agent executed only on approved artifacts. Classifies the finalized content against taxonomies (subject, difficulty classification, Bloom's Taxonomy level).

## Pass/Fail Criteria
The pipeline evaluates quality strictly. A draft is only "passed" if:
* Evaluated quantitative scores for Age Appropriateness, Correctness, Clarity, and Coverage are **ALL >= 3 (out of 5)**.
* **0 rule-based issues** exist (e.g. fewer than 2 MCQs generated, structurally broken answer indices, or missing explanation blocks). 
If any criteria fails, the Reviewer outputs specific field-level references to allow the Refiner precise context to fix the structure.

## Orchestration Decisions
* **Deterministic Flow & Bounded Retries**: The system explicitly hard-stops loops using a `for attempt_num in range(1, 4)` threshold. It strictly limits attempts to Initial Generation + Max 2 refinements. Unchecked loops cause extreme API cost hemorrhage.
* **Single Run Artifact Record**: The orchestration architecture does not store isolated DB fields; it maps the entire lifecycle (Inputs, Drafts, Reviews, Refinements, Tags, Timestamps) into an immutable JSON representation called a `RunArtifact` to provide a true audit trail.
* **Database Target**: Handled via simple robust SQLite table (`runs.db`) containing deeply nested JSON representation blocks to ease the evaluator setup process while simulating structured persistence databases like PostgreSQL.

## Trade-offs
1. **Latency vs. High Reliability**: Utilizing a rigid Multi-Agent structure (Generate → Review → Refine) causes significant execution latency but astronomically improves content structural compliance and factual trust compared to zero-shot conversational bots. 
2. **SQLite vs. PostgreSQL**: The setup natively leverages SQLite for simplicity and frictionless execution for reviewers, at the tradeoff of complex concurrency and horizontal scalability standard SQL configurations provide natively.
3. **Creative Autonomy vs. Auditability**: By mandating output mapped directly into Pydantic models with constrained variables, we sacrifice the wide-ranging creative flair of the LLM for rigorous enterprise-level stability and auditability.

---

## Local Setup Instructions

If you prefer to run this application locally on your own machine instead of the live demo, follow these steps.

### 1. Backend Setup

Open a terminal and navigate to the backend directory:
```bash
cd Backend
```

Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

Install the required python packages:
```bash
pip install -r requirements.txt
```

Create a .env file in the Backend directory with your Groq API key:
```text
GROQ_API_KEY=your_key_here
```

Start the FastAPI server:
```bash
uvicorn main:app --reload
```
The backend API will run on http://127.0.0.1:8000. 

### 2. Testing (For Reviewers)

To execute the 3 mandatory assessment tests (mocked LLM schema failure, pass loop, and reject loop), ensure your virtual environment is active and run:
```bash
pytest test_pipeline.py -v
```

### 3. Frontend Setup

Open a separate terminal and navigate to the frontend directory:
```bash
cd Frontend
```

Install the node modules for the React application:
```bash
npm install
```

Start the local development server:
```bash
npm run dev
```

Open your browser and navigate to the link provided in the terminal (usually http://localhost:5173). The React application is now connected to the FastAPI backend.
