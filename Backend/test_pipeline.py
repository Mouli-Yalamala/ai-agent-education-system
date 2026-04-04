import pytest
from unittest.mock import patch, MagicMock

from models import InputSchema, GeneratorOutput, ReviewerOutput, Explanation, MCQ, TeacherNotes
from agents import generator
from pipeline import run_pipeline


# --- DUMMY DATA HELPERS --- #

def get_dummy_generator_output():
    """Generates a perfectly valid Pydantic dummy structure for the Generator Output"""
    return GeneratorOutput(
        explanation=Explanation(text="Dummy explanation text", grade=5),
        mcqs=[
            MCQ(question="Dummy Q1", options=["1", "2", "3", "4"], correct_index=0),
            MCQ(question="Dummy Q2", options=["A", "B", "C", "D"], correct_index=1)
        ],
        teacher_notes=TeacherNotes(learning_objective="Learn dummy things", common_misconceptions=["Misconception"])
    )

def get_dummy_reviewer_output(is_pass: bool):
    """Generates a dummy Reviewer Output based on requested pass/fail status."""
    if is_pass:
        return ReviewerOutput.model_validate({
            "scores": {"age_appropriateness": 5, "correctness": 5, "clarity": 5, "coverage": 5},
            "pass": True,
            "feedback": []
        })
    else:
        return ReviewerOutput.model_validate({
            "scores": {"age_appropriateness": 1, "correctness": 1, "clarity": 1, "coverage": 1},
            "pass": False,
            "feedback": [{"field": "explanation.text", "issue": "Simulated failure issue"}]
        })


# --- TEST CASES --- #

@patch('agents.client.chat.completions.create')
def test_schema_validation_failure_handling(mock_create_llm):
    """
    Test Case 1: Schema Validation Failure Handling
    Simulates the LLM outright hallucinating string/bad JSON data instead of the requested Pydantic schema structure.
    Ensures that the generator catches ValidationError and triggers exactly 1 retry loop before gracefully raising ValueError.
    """
    
    # Create a mock response object that returns bad text payload
    bad_response = MagicMock()
    bad_response.choices = [MagicMock(message=MagicMock(content='{"completely": "invalid_schema"}'))]
    
    # We assign this to always return bad data
    mock_create_llm.return_value = bad_response
    
    with pytest.raises(ValueError, match="Generation failed after 2 attempts due to validation errors"):
        # The generator will attempt once, fail natively mapping to Pydantic, catch it, and attempt a 2nd time before crashing purposefully
        generator(grade=5, topic="Volcanoes")
        
    # Crucial Assertion: Prove that the LLM was actually redundantly summoned 2 times, verifying the internal loop
    assert mock_create_llm.call_count == 2


@patch('pipeline.generator')
@patch('pipeline.reviewer')
@patch('pipeline.refiner')
def test_fail_refine_pass_flow(mock_refiner, mock_reviewer, mock_generator):
    """
    Test Case 2: Fail -> Refine -> Pass
    Simulates the complete optimal bounded logic where attempt 1 fails mathematically, but attempt 2 successfully clears the hurdles.
    """
    mock_generator.return_value = get_dummy_generator_output()
    mock_refiner.return_value = get_dummy_generator_output()
    
    # Reviewer behavior: Fail the initial review (Attempt 1), Pass the refined review (Attempt 2)
    mock_reviewer.side_effect = [
        get_dummy_reviewer_output(is_pass=False),  
        get_dummy_reviewer_output(is_pass=True)
    ]
    
    input_data = InputSchema(grade=5, topic="Fractions")
    artifact = run_pipeline(input_data)
    
    # Validations mapping to architectural state boundaries
    assert artifact.run_id is not None
    assert artifact.timestamps.started_at is not None
    
    # Ensures it passed properly and terminated at step 2 automatically
    assert artifact.final.status == "approved"
    assert artifact.final.content is not None
    
    # Verifies execution boundaries
    assert len(artifact.attempts) == 2      # Loop broke optimally right exactly at attempt 2
    assert mock_reviewer.call_count == 2    # Reviewed the Draft + 1st Refinement
    assert mock_refiner.call_count == 1     # Refined exactly once to bridge the gap


@patch('pipeline.generator')
@patch('pipeline.reviewer')
@patch('pipeline.refiner')
def test_fail_refine_fail_reject_flow(mock_refiner, mock_reviewer, mock_generator):
    """
    Test Case 3: Fail -> Refine -> Fail -> Reject 
    Simulates total system refusal where the refiner cannot save the output structure within explicit mathematical boundaries.
    """
    mock_generator.return_value = get_dummy_generator_output()
    mock_refiner.return_value = get_dummy_generator_output()
    
    # Infinite strict LLM refusal (Always mathematically evaluating below passing threshold)
    mock_reviewer.return_value = get_dummy_reviewer_output(is_pass=False)
    
    input_data = InputSchema(grade=5, topic="Geometry")
    artifact = run_pipeline(input_data)
    
    # Final state assertions verifying pipeline hard-stop abortion protocol
    assert artifact.final.status == "rejected"
    assert artifact.final.content is None     # Safety constraint: unreviewed elements are nullified
    
    # Execution counts bounds checks (Cannot arbitrarily overflow logic bounds into infinite loops)
    assert len(artifact.attempts) == 3        # Ran across absolute max depth
    assert mock_reviewer.call_count == 3      # Initial Review + Refine(1) Review + Refine(2) Review
    assert mock_refiner.call_count == 2       # Reached explicit 2 max refinement limit bounds
