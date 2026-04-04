import logging
import uuid
from datetime import datetime, timezone

from models import InputSchema, RunArtifact, AttemptRecord, RunArtifactFinal, RunArtifactTimestamps
from agents import generator, reviewer, refiner, tagger

logger = logging.getLogger(__name__)

def run_pipeline(input_data: InputSchema) -> RunArtifact:
    """
    Executes the governed educational content pipeline.
    Produces a completely auditable RunArtifact.
    Enforces a strict deterministic flow with a maximum of 2 refinement attempts.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())
    attempts = []
    
    logger.info(f"[{run_id}] Step 1: Generation for Grade {input_data.grade}")
    
    # 1. Initial Generation Draft
    current_content = generator(input_data.grade, input_data.topic)
    
    final_status = "rejected"
    final_content = None
    
    # Deterministic Loop: Attempt 1 is Initial, Attempts 2 & 3 are Refinements.
    for attempt_num in range(1, 4):
        logger.info(f"[{run_id}] Step 2: Reviewing attempt {attempt_num}...")
        review_result = reviewer(current_content, input_data.grade)
        
        # Create immutable snapshot of the current state
        record = AttemptRecord(
            attempt=attempt_num,
            draft=current_content,
            review=review_result,
            refined=None
        )
        
        if review_result.is_pass:
            logger.info(f"[{run_id}] Content explicitly PASSED review on attempt {attempt_num}.")
            final_status = "approved"
            final_content = current_content
            attempts.append(record)
            break
            
        else:
            logger.info(f"[{run_id}] Review FAILED on attempt {attempt_num}.")
            if attempt_num < 3: 
                # We haven't hit the cap of 2 max refinements (attempt 3). Run the refiner.
                logger.info(f"[{run_id}] Step 3: Triggering Refiner for attempt {attempt_num+1}...")
                refined_content = refiner(current_content, review_result.feedback, input_data.grade, input_data.topic)
                
                # Attach the outcome to the record to complete the snapshot
                record.refined = refined_content
                attempts.append(record)
                
                # Overwrite 'current_content' moving into the next loop iteration for review
                current_content = refined_content
            else:
                # We have failed 3 times (Initial + Refine 1 + Refine 2)
                logger.warning(f"[{run_id}] Hard stop: Reached absolute max refinement limit (Attempt {attempt_num}). Rejecting artifact run.")
                final_status = "rejected"
                final_content = None
                attempts.append(record)
                break
                
    # 4. Apply Tagger if successful
    if final_status == "approved" and final_content is not None:
        logger.info(f"[{run_id}] Step 4: Generating operational tags via Tagger Agent...")
        tags_dict = tagger(final_content, input_data.grade, input_data.topic)
    else:
        tags_dict = None

    finished_at = datetime.now(timezone.utc).isoformat()
    
    # 5. Construct Governed Audit Record
    return RunArtifact(
        run_id=run_id,
        input=input_data,
        attempts=attempts,
        final=RunArtifactFinal(
            status=final_status,
            content=final_content
        ),
        tags=tags_dict,
        timestamps=RunArtifactTimestamps(
            started_at=started_at,
            finished_at=finished_at
        )
    )
