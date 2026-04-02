import json
import logging
from typing import Optional

from groq import Groq
from pydantic import ValidationError

from config import client
from models import GeneratorOutput, ReviewerOutput

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

Requirements for MCQs:
- Exactly 4 options per question.
- Exactly 1 correct answer which must exactly match one of the options provided.
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

    prompt += """
CRITICAL INSTRUCTION:
You must return the output STRICTLY in JSON format. Do not include any extra text, greetings, code blocks like ```json, or explanations outside the JSON object.

The JSON object must follow this exact schema:
{
  "explanation": "string (the educational content)",
  "mcqs": [
    {
      "question": "string",
      "options": ["string", "string", "string", "string"],
      "answer": "string"
    }
  ]
}
"""
    return prompt


def generator(grade: int, topic: str, feedback: Optional[list[str]] = None) -> GeneratorOutput:
    """
    Generator Agent: Calls Groq LLM to generate educational content (explanation + MCQs).
    Strictly validates the output against the GeneratorOutput Pydantic schema.
    """
    prompt = _construct_generator_prompt(grade, topic, feedback)
    
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

    except json.JSONDecodeError as e:
        logger.error(f"JSON Parsing Error: Failed to parse LLM response into JSON. Raw output: {raw_output}. Error: {e}")
        raise ValueError("Invalid JSON format received from LLM.") from e
        
    except ValidationError as e:
        logger.error(f"Schema Validation Error: LLM output did not match GeneratorOutput schema. Error: {e}")
        raise ValueError("LLM output structure is invalid or missing required fields.") from e
        
    except Exception as e:
        logger.error(f"Generation Error: An unexpected error occurred: {e}")
        raise


def _run_rule_based_checks(content: GeneratorOutput) -> list[str]:
    """
    Performs basic, fast rule-based checks before calling the LLM.
    Returns a list of feedback comments. If empty, all rules passed.
    """
    feedback = []
    
    if not content.explanation or len(content.explanation.strip()) < 10:
        feedback.append("The explanation is too short or virtually empty.")
        
    if not content.mcqs or len(content.mcqs) < 2:
        feedback.append("Provide at least 2 MCQs.")
        
    for idx, mcq in enumerate(content.mcqs):
        if len(mcq.options) != 4:
            feedback.append(f"MCQ {idx+1} must have exactly 4 options. Found {len(mcq.options)}.")
        if mcq.answer not in mcq.options:
            feedback.append(f"MCQ {idx+1}'s answer is not among the options.")
            
    return feedback


def _construct_reviewer_prompt(content: GeneratorOutput, grade: int) -> str:
    content_json = content.model_dump_json(indent=2)
    return f"""You are an expert AI quality reviewer for educational content.
You must evaluate the following generated content designed for a Grade {grade} student.

CONTENT TO REVIEW:
{content_json}

EVALUATION CRITERIA:
1. Age Appropriateness:
   - Does the language strictly match a Grade {grade} comprehension level?
   - Are sentences too complex, or vocabulary too advanced for this grade?
2. Conceptual Correctness:
   - Is the explanation factually correct?
   - Are the MCQs logically sound, relevant to the topic, and correct?
3. Clarity:
   - Is the explanation straightforward and not confusing?
   - Are the questions clearly worded?

FEEDBACK RULES:
- Evaluate the content fairly and practically. Do NOT be overly pedantic or hyper-critical of standard vocabulary.
- If the content generally meets the grade level and is factually correct, you must PASS it and leave feedback empty.
- You should ONLY FAIL the content if there are blatant factual errors, explicitly confusing language that the grade cannot understand, or logically broken MCQs. If you fail, provide specific, actionable points referencing exactly what is wrong.

CRITICAL INSTRUCTION:
Do not provide any explanatory text, greetings, code blocks, etc.
You must output STRICTLY raw JSON matching this schema exactly:
{{
  "status": "fail",
  "feedback": ["list of strings (specific actionable points)", "..."]
}}
or
{{
  "status": "pass",
  "feedback": []
}}
"""


def reviewer(content: GeneratorOutput, grade: int) -> ReviewerOutput:
    """
    Reviewer Agent: Checks the GeneratorOutput using basic rule-based checks
    combined with a Groq LLM evaluation. Returns strict ReviewerOutput.
    """
    # 1. Faster rule-based checks first
    rule_feedback = _run_rule_based_checks(content)
    
    if rule_feedback:
        return ReviewerOutput(status="fail", feedback=rule_feedback)

    # 2. Deeper LLM-based evaluation
    prompt = _construct_reviewer_prompt(content, grade)
    
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
        
        validated_data = ReviewerOutput.model_validate(json_output)
        
        if validated_data.status == "fail" and not validated_data.feedback:
            validated_data.feedback.append("The reviewer failed the content but did not provide specific reasons.")
            
        if validated_data.status == "pass":
            validated_data.feedback = []
            
        return validated_data

    except json.JSONDecodeError as e:
        logger.error(f"JSON Parsing Error in Reviewer: {e}. Raw output: {{raw_output}}")
        raise ValueError("Invalid JSON format received from Reviewer LLM.") from e
        
    except ValidationError as e:
        logger.error(f"Schema Validation Error in Reviewer: {e}")
        raise ValueError("Reviewer LLM output structure is invalid or missing required fields.") from e
        
    except Exception as e:
        logger.error(f"Reviewer Generation Error: An unexpected error occurred: {e}")
        raise

