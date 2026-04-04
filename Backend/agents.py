import json
import logging
from typing import Optional

from groq import Groq
from pydantic import ValidationError

from config import client
from models import GeneratorOutput, ReviewerOutput, FeedbackItem, ReviewerScores

# Setup logger for basic error logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _construct_generator_prompt(grade: int, topic: str, feedback: Optional[list[str]] = None) -> str:
    """
    Constructs the prompt for the generator agent based on inputs and optional feedback.
    """
    prompt = f"""You are an expert AI tutor generating educational content for a Grade {grade} student.
Topic: {topic}

Your task is to provide a simple, easy-to-understand explanation of the topic appropriate for the student's grade level.
After the explanation, generate 2 to 3 multiple-choice questions (MCQs) to test their understanding.
You must also include teacher notes detailing to the educator the main learning objective and common misconceptions the student might have.

Requirements for MCQs:
- Exactly 4 options per question.
- Exactly 1 correct answer indicated by its 0-indexed 'correct_index' (0, 1, 2, or 3).
- The concepts must be strictly correct and relevant to the topic.
"""
    if feedback and len(feedback) > 0:
        feedback_str = "\n".join(f"- {item}" for item in feedback)
        prompt += f"""
PREVIOUS REVIEWER FEEDBACK:
You previously generated content for this topic, but the reviewer found issues. Please improve your generation based on the following feedback:
{feedback_str}

Ensure you fix any issues related to complexity, clarity, or incorrect questions.
"""

    prompt += f"""
CRITICAL INSTRUCTION:
You must return the output STRICTLY in valid JSON format matching the schema exactly.
Do not include any extra text, greetings, code blocks like ```json, or explanations outside the JSON object.

The JSON object must follow this exact schema structure:
{{
  "explanation": {{
    "text": "string (the educational content)",
    "grade": {grade}
  }},
  "mcqs": [
    {{
      "question": "string",
      "options": ["string", "string", "string", "string"],
      "correct_index": integer (0, 1, 2, or 3)
    }}
  ],
  "teacher_notes": {{
    "learning_objective": "string",
    "common_misconceptions": ["string", "string"]
  }}
}}
"""
    return prompt


def generator(grade: int, topic: str, feedback: Optional[list[str]] = None) -> GeneratorOutput:
    """
    Generator Agent: Calls Groq LLM to generate educational content (explanation + MCQs).
    Strictly validates the output against the GeneratorOutput Pydantic schema.
    Includes a 1-time retry loop for Pydantic validation errors.
    """
    prompt = _construct_generator_prompt(grade, topic, feedback)
    
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise educational AI restricted to only output raw valid JSON based on the requested schema."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            
            raw_output = response.choices[0].message.content
            if not raw_output:
                raise ValueError("Received an empty response from the LLM.")
                
            json_output = json.loads(raw_output)
            
            # Validate safely into the Pydantic model
            validated_data = GeneratorOutput.model_validate(json_output)
            return validated_data
            
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Generator attempt {attempt+1} failed validation: {e}")
            if attempt == 1:
                logger.error("Generator failed twice. Aborting.")
                raise ValueError(f"Generation failed after 2 attempts due to validation errors. Final error: {e}")
        except Exception as e:
            logger.error(f"Generation Error: An unexpected error occurred: {e}")
            raise


def _run_rule_based_checks(content: GeneratorOutput) -> list[FeedbackItem]:
    """
    Performs basic, fast rule-based checks before calling the LLM.
    Returns a list of FeedbackItems mapping field paths to issues.
    """
    feedback = []
    
    if not content.explanation or not content.explanation.text or len(content.explanation.text.strip()) < 10:
        feedback.append(FeedbackItem(field="explanation.text", issue="The explanation is too short or virtually empty."))
        
    if not content.mcqs or len(content.mcqs) < 2:
        feedback.append(FeedbackItem(field="mcqs", issue="Provide at least 2 MCQs."))
        
    for idx, mcq in enumerate(content.mcqs):
        if len(mcq.options) != 4:
            feedback.append(FeedbackItem(field=f"mcqs[{idx}].options", issue=f"MCQ must have exactly 4 options. Found {len(mcq.options)}."))
        if mcq.correct_index < 0 or mcq.correct_index >= len(mcq.options):
            feedback.append(FeedbackItem(field=f"mcqs[{idx}].correct_index", issue="Correct index is significantly invalid and misaligned with options array."))
            
    return feedback


def _construct_reviewer_prompt(content: GeneratorOutput, grade: int) -> str:
    content_json = content.model_dump_json(indent=2)
    return f"""You are an expert AI quality reviewer for educational content.
You must evaluate the following generated content designed for a Grade {grade} student.

CONTENT TO REVIEW:
{content_json}

EVALUATION CRITERIA:
1. age_appropriateness: Is the language strictly suitable for Grade {grade}? Penalize long or complex sentences heavily.
2. correctness: Are the concepts factual and accurate? Are the MCQs logically valid?
3. clarity: Is the explanation easy to understand? Are questions clear?
4. coverage: Does the content cover the topic sufficiently and introduce necessary concepts?

YOUR TASK:
Determine a score from 1 to 5 for each criteria (1 being very poor, 5 being perfect).
If any score is strictly less than 3, or if you spot any explicit issue, you MUST provide an actionable feedback item specifying exactly which JSON field is failing.

CRITICAL INSTRUCTION:
Do not provide any explanatory text, greetings, code blocks, etc.
You must output STRICTLY raw valid JSON matching this schema exactly:
{{
  "scores": {{
    "age_appropriateness": integer,
    "correctness": integer,
    "clarity": integer,
    "coverage": integer
  }},
  "feedback": [
    {{
      "field": "string (e.g. 'explanation.text' or 'mcqs[1].question')",
      "issue": "string (specific actionable issue)"
    }}
  ]
}}
"""


def reviewer(content: GeneratorOutput, grade: int) -> ReviewerOutput:
    """
    Reviewer Agent: Checks the GeneratorOutput using basic rule-based checks
    combined with a Groq LLM evaluation. Returns strict ReviewerOutput.
    Computes pass/fail based on a strict scoring logic rule.
    """
    rule_feedback = _run_rule_based_checks(content)
    
    prompt = _construct_reviewer_prompt(content, grade)
    
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an automated curriculum reviewer constrained to output only valid JSON matching the requested schema."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            
            raw_output = response.choices[0].message.content
            if not raw_output:
                raise ValueError("Received an empty response from the Reviewer LLM.")
                
            json_output = json.loads(raw_output)
            
            scores_data = json_output.get("scores", {})
            feedback_data = json_output.get("feedback", [])
            
            scores = ReviewerScores(**scores_data)
            feedback_items = [FeedbackItem(**f) for f in feedback_data]
            
            # Combine rule-based feedback
            feedback_items.extend(rule_feedback)
            
            # Implement Pass/Fail evaluation rule
            is_pass = (
                scores.age_appropriateness >= 3 and
                scores.correctness >= 3 and
                scores.clarity >= 3 and
                scores.coverage >= 3 and
                len(rule_feedback) == 0  # Automatically fail if explicitly caught by hard rules
            )
            
            output_dict = {
                "scores": scores,
                "pass": is_pass,
                "feedback": feedback_items
            }
            
            validated_data = ReviewerOutput.model_validate(output_dict)
            return validated_data

        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            logger.warning(f"Reviewer attempt {attempt+1} failed schema mapping validation: {e}")
            if attempt == 1:
                logger.error("Reviewer failed twice. Aborting.")
                raise ValueError(f"Reviewer failed after 2 attempts due to validation errors. Final error: {e}")
        except Exception as e:
            logger.error(f"Reviewer Generation Error: An unexpected error occurred: {e}")
            raise


def _construct_refiner_prompt(content: GeneratorOutput, feedback: list[FeedbackItem], grade: int, topic: str) -> str:
    content_json = content.model_dump_json(indent=2)
    feedback_str = "\n".join([f"- Field: '{item.field}' - Issue: '{item.issue}'" for item in feedback])
    
    return f"""You are an expert AI educational content refiner.
Your task is to fix and improve the following educational content according to the specific reviewer feedback items provided.

Grade Level: {grade}
Topic: {topic}

ORIGINAL CONTENT:
{content_json}

REVIEWER FEEDBACK (ISSUES TO FIX):
{feedback_str}

CRITICAL INSTRUCTIONS:
1. Fix the issues mentioned in the feedback. Focus specifically on the fields mentioned.
2. Keep the grade-appropriate language.
3. Do NOT change the overarching structure of the JSON. Make surgical improvements to the text, MCQs, or teacher notes.
4. Return ONLY valid JSON matching exactly the original schema. Do not include extra text, greetings, or markdown code blocks like ```json.

The JSON object must strictly match this schema structure:
{{
  "explanation": {{
    "text": "string (the educational content)",
    "grade": {grade}
  }},
  "mcqs": [
    {{
      "question": "string",
      "options": ["string", "string", "string", "string"],
      "correct_index": integer (0, 1, 2, or 3)
    }}
  ],
  "teacher_notes": {{
    "learning_objective": "string",
    "common_misconceptions": ["string", "string"]
  }}
}}
"""


def refiner(content: GeneratorOutput, feedback: list[FeedbackItem], grade: int, topic: str) -> GeneratorOutput:
    """
    Refiner Agent: Improves the generated content based on structured reviewer feedback.
    Returns a valid GeneratorOutput.
    If it fails after 2 attempts due to validation, it safely returns the original content as a fallback.
    """
    prompt = _construct_refiner_prompt(content, feedback, grade, topic)
    
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise educational AI refiner restricted to only output raw valid JSON based on the requested schema."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            
            raw_output = response.choices[0].message.content
            if not raw_output:
                raise ValueError("Received an empty response from the Refiner LLM.")
                
            json_output = json.loads(raw_output)
            validated_data = GeneratorOutput.model_validate(json_output)
            return validated_data
            
        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            logger.warning(f"Refiner attempt {attempt+1} failed schema mapping validation: {e}")
            if attempt == 1:
                logger.error("Refiner failed twice. Returning original content as fallback.")
                return content  # Fallback gracefully
        except Exception as e:
            logger.error(f"Refiner Error: An unexpected error occurred: {e}")
            return content  # Fallback gracefully


def _construct_tagger_prompt(content: GeneratorOutput, grade: int, topic: str) -> str:
    content_json = content.model_dump_json(indent=2)
    return f"""You are an advanced AI classification agent.
Your task is to classify educational content into specific curriculum tags.

Original Request:
Grade: {grade}
Topic: {topic}

Content to Classify:
{content_json}

INSTRUCTIONS:
Determine the following metadata tags:
- subject: Infer the broad academic subject (e.g., Mathematics, Science, History, Language Arts) from the topic.
- difficulty: Classify the content complexity as either "Easy", "Medium", or "Hard".
- blooms_level: Classify the cognitive level based on Bloom's Taxonomy (e.g., "Recall", "Understanding", "Application", "Analysis").

CRITICAL INSTRUCTION:
Output STRICTLY valid JSON. No explanations, no markdown code blocks.
Schema:
{{
  "subject": "string",
  "topic": "{topic}",
  "grade": {grade},
  "difficulty": "string (Easy, Medium, or Hard)",
  "content_type": ["Explanation", "Quiz"],
  "blooms_level": "string"
}}
"""

def tagger(content: GeneratorOutput, grade: int, topic: str) -> dict:
    """
    Tagger Agent: Assigns metadata classifications natively to passing artifacts.
    Provides a guaranteed valid dictionary wrapper fallback.
    """
    prompt = _construct_tagger_prompt(content, grade, topic)
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a JSON-only tagging AI."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw_output = response.choices[0].message.content
        if not raw_output:
            raise ValueError("Empty response from Tagger.")
        return json.loads(raw_output)
    except Exception as e:
        logger.error(f"Tagger Error: {e}")
        # Mathematical absolute fallback so orchestrator pipelines do not fail at the tags stage
        return {
            "subject": "Unknown",
            "topic": topic,
            "grade": grade,
            "difficulty": "Medium",
            "content_type": ["Explanation", "Quiz"],
            "blooms_level": "Understanding"
        }

