from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from pipeline import run_pipeline
from models import InputSchema

app = FastAPI(
    title="AI Agent Educational Content Pipeline API",
    description="API for the Generator and Reviewer educational content AI agents",
    version="1.0"
)

# Enable CORS since the React frontend runs in the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate", response_model=Dict[str, Any])
def generate_content(payload: InputSchema):
    """
    Endpoint to trigger the AI content pipeline.
    Expects grade (int) and topic (str) inside the JSON payload.
    """
    try:
        # Run the agent pipeline
        result = run_pipeline(payload.grade, payload.topic)
        
        # If the pipeline returned an internal error, raise it
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "API is running. Ready to receive requests."}
