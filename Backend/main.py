from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pipeline import run_pipeline
from models import InputSchema, RunArtifact
from database import save_run, get_all_runs, get_run_by_id

app = FastAPI(
    title="AI Agent Educational Content Pipeline API",
    description="API for the Generator, Reviewer, and Refiner educational content AI agents",
    version="2.0"
)

# Enable CORS since the React frontend runs in the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate", response_model=RunArtifact)
def generate_content(payload: InputSchema):
    """
    Endpoint to trigger the full governed AI content pipeline.
    Expects grade (int) and topic (str) inside the JSON payload.
    Automatically provisions, executes, and saves the RunArtifact to the SQLite persistence index.
    """
    try:
        # Pass the validated Pydantic model directly to the orchestrator
        artifact = run_pipeline(payload)
        
        # Save the finalized immutable deterministic record to the local SQLite DB
        save_run(artifact)
            
        return artifact
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history", response_model=List[RunArtifact])
def fetch_history():
    """Fetches all historically recorded RunArtifacts from the SQLite database."""
    try:
        runs = get_all_runs()
        return runs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Retrieval Error: {str(e)}")


@app.get("/history/{run_id}", response_model=RunArtifact)
def fetch_run(run_id: str):
    """Fetches a solitary specific target run."""
    try:
        run = get_run_by_id(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"RunArtifact '{run_id}' not found in database.")
        return run
    except HTTPException:
        # Re-raise standard HTTP exceptions safely
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Retrieval Error: {str(e)}")


@app.get("/")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "Governed App API is running. Ready to receive requests."}
