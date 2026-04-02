import logging
from typing import Optional, Dict, Any

from models import GeneratorOutput, ReviewerOutput
from agents import generator, reviewer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_pipeline(grade: int, topic: str) -> Dict[str, Any]:
    """
    Executes the content generation pipeline.
    Calls the generator, then reviewer. If reviewer fails, retries the generator ONCE.
    """
    result = {
        "initial_content": None,
        "review": None,
        "refined_content": None
    }
    
    try:
        # Step 1: Initial Content Generation
        logger.info(f"Generating initial content for Grade {grade}, Topic: '{topic}'")
        initial_content = generator(grade, topic)
        result["initial_content"] = initial_content
        
        # Step 2: Content Review
        logger.info("Reviewing initial content...")
        review = reviewer(initial_content, grade)
        result["review"] = review
        
        # Step 3: Conditional Single Retry (no loops, no recursion)
        if review.status == "fail":
            logger.info("Review failed. Running generator one more time with feedback.")
            refined_content = generator(grade, topic, feedback=review.feedback)
            result["refined_content"] = refined_content
        elif review.status == "pass":
            logger.info("Review passed. No retry needed.")
            # refined_content remains None

    except Exception as e:
        logger.error(f"Pipeline execution encountered an error: {e}")
        # Attach error to the result for graceful handling by the caller
        result["error"] = str(e)
        
    return result
