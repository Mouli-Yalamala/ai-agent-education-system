from typing import List, Literal
from pydantic import BaseModel, Field, model_validator

class InputSchema(BaseModel):
    grade: int
    topic: str

class MCQ(BaseModel):
    question: str
    options: List[str] = Field(..., min_length=4, max_length=4, description="List of exactly 4 options")
    answer: str

    @model_validator(mode="after")
    def check_answer_in_options(self) -> "MCQ":
        if self.answer not in self.options:
            raise ValueError("answer must be one of the options")
        return self

class GeneratorOutput(BaseModel):
    explanation: str = Field(..., min_length=1, description="Explanation should not be empty")
    mcqs: List[MCQ]

class ReviewerOutput(BaseModel):
    status: Literal["pass", "fail"]
    feedback: List[str] = Field(default_factory=list)
