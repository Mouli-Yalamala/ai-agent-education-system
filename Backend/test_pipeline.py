import logging
from unittest.mock import patch
from models import GeneratorOutput, MCQ
from pipeline import run_pipeline

# Ensure clear output without interfering logger spam during tests
logging.basicConfig(level=logging.WARNING)

def test_normal_case():
    print("\n--- Running Test Case 1: Normal Case (Should Pass) ---")
    grade = 4
    topic = "Types of angles"
    
    result = run_pipeline(grade, topic)
    
    # Validation
    assert result.get("error") is None, f"Pipeline threw an error: {result.get('error')}"
    
    initial = result.get("initial_content")
    review = result.get("review")
    refined = result.get("refined_content")
    
    print(f"Reviewer Status: {review.status.upper()}")
    
    if review.status == "pass":
        assert refined is None, "Refined content should be None if review passed."
        print("Test 1 Passed: Agent passed smoothly, no retry triggered.")
    else:
        assert refined is not None, "Pipeline must generate refined content if it fails."
        print("Test 1 Note: Organic failure occurred. LLMs can be strict. Retry logic handled it successfully.")

def test_forced_fail_case():
    print("\n--- Running Test Case 2: Forced Fail Case ---")
    # We use patch to simulate the generator throwing a bad output deliberately on the very first try.
    grade = 2
    topic = "Addition"
    
    original_generator = __import__('agents').generator
    state = {"called": False}
    
    def fake_generator(grd, tpc, feedback=None):
        if not state["called"]:
            state["called"] = True
            # Intentionally bad output for a 2nd grader
            return GeneratorOutput(
                explanation="The concept of addition is intrinsically tied to establishing a bijective function combining cardinalities of disjoint sets, mapped strictly to integer progression.",
                mcqs=[
                    MCQ(question="What is 1+1?", options=["2", "3", "4", "5"], answer="2"),
                    MCQ(question="What is 2+2?", options=["4", "5", "6", "7"], answer="4")
                ]
            )
        else:
            # Second call (retry) runs the real generative logic to "fix" it.
            return original_generator(grd, tpc, feedback)

    with patch('pipeline.generator', side_effect=fake_generator):
        result = run_pipeline(grade, topic)
        review = result.get("review")
        
        print(f"Reviewer Status: {review.status.upper()}")
        print(f"Reviewer Feedback Provided:")
        for fb in review.feedback:
            print(f"  - {fb}")
            
        assert review.status == "fail", "Reviewer failed to catch the overly complex text."
        assert result.get("refined_content") is not None, "Pipeline did not trigger a retry after failure."
        
        print("Test 2 Passed: Reviewer successfully failed bad content and triggered a retry.")

def test_structure_validation():
    print("\n--- Running Test Case 3: Structure Validation ---")
    grade = 5
    topic = "The Solar System"
    
    result = run_pipeline(grade, topic)
    
    assert "initial_content" in result, "Key 'initial_content' is missing."
    assert "review" in result, "Key 'review' is missing."
    assert "refined_content" in result, "Key 'refined_content' is missing."
    assert result.get("error") is None, "Pipeline generated an internal error."
    
    initial = result["initial_content"]
    assert hasattr(initial, "explanation") and len(initial.explanation.strip()) > 0, "Explanation is missing or empty."
    assert hasattr(initial, "mcqs") and len(initial.mcqs) >= 2, "Less than 2 MCQs generated."
    
    for mcq in initial.mcqs:
        assert len(mcq.options) == 4, f"MCQ requires 4 options, got {len(mcq.options)}."
        assert mcq.answer in mcq.options, f"MCQ answer '{mcq.answer}' is not in options list."
        
    print(" Test 3 Passed: Structure conforms perfectly to requirements.")

if __name__ == "__main__":
    try:
        test_normal_case()
        test_forced_fail_case()
        test_structure_validation()
        print("\n All tests completed successfully.")
    except AssertionError as e:
        print(f"\nTest Failed: {e}")
