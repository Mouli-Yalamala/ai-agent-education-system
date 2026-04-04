from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

class InputSchema(BaseModel):
    grade: int
    topic: str

class Explanation(BaseModel):
    text: str = Field(..., min_length=1, description="Explanation should not be empty")
    grade: int

class MCQ(BaseModel):
    question: str
    options: List[str] = Field(..., min_length=4, max_length=4, description="List of exactly 4 options")
    correct_index: int = Field(..., ge=0, le=3, description="Must be a valid index between 0 and 3")

class TeacherNotes(BaseModel):
    learning_objective: str
    common_misconceptions: List[str]

class GeneratorOutput(BaseModel):
    explanation: Explanation
    mcqs: List[MCQ]
    teacher_notes: TeacherNotes

class ReviewerScores(BaseModel):
    age_appropriateness: int = Field(..., ge=1, le=5)
    correctness: int = Field(..., ge=1, le=5)
    clarity: int = Field(..., ge=1, le=5)
    coverage: int = Field(..., ge=1, le=5)

class FeedbackItem(BaseModel):
    field: str
    issue: str

class ReviewerOutput(BaseModel):
    scores: ReviewerScores
    is_pass: bool = Field(..., alias="pass")
    feedback: List[FeedbackItem]

class AttemptRecord(BaseModel):
    attempt: int
    draft: GeneratorOutput
    review: ReviewerOutput
    refined: Optional[GeneratorOutput] = None

class RunArtifactFinal(BaseModel):
    status: Literal["approved", "rejected"]
    content: Optional[GeneratorOutput] = None

class RunArtifactTimestamps(BaseModel):
    started_at: str
    finished_at: str

class RunArtifact(BaseModel):
    run_id: str
    input: InputSchema
    attempts: List[AttemptRecord]
    final: RunArtifactFinal
    tags: Optional[Dict[str, Any]] = None
    timestamps: RunArtifactTimestamps
