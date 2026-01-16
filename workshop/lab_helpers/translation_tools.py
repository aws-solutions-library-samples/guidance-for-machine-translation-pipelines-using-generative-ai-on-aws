"""
Translation tools for the intelligent translation agent workshop.
"""

from strands import tool
from typing import Dict, List
import re


@tool
def evaluate_translation_quality(
    source_text: str,
    translated_text: str,
    target_language: str = "Russian"
) -> str:
    """
    Evaluate the quality of a translation and identify issues.
    
    This tool helps you systematically assess translation quality.
    
    Args:
        source_text: Original text in source language
        translated_text: Translated text to evaluate
        target_language: Target language name
        
    Returns:
        Evaluation guidance prompt for you to assess the translation
    """
    return f"""
Evaluate this {target_language} translation:

Source: {source_text[:200]}...
Translation: {translated_text[:200]}...

Provide your assessment in this format:

Quality Score: [0-100, where 85+ is acceptable]

Issues Found:
1. [Specific issue with example]
2. [Another issue if any]

Needs Refinement: [Yes/No]

Check for:
- Accuracy: Does it convey the same meaning?
- Fluency: Does it sound natural to native speakers?
- Terminology: Are technical terms correct and consistent?
- Tone: Is the formality level appropriate?
"""


@tool
def query_terminology_kb(term: str, kb_id: str = None) -> str:
    """
    Query the AWS terminology Knowledge Base for correct translations.
    
    Args:
        term: Technical term to look up
        kb_id: Knowledge Base ID (optional, will use default if not provided)
        
    Returns:
        Correct translation and definition of the term
    """
    # This tool will be implemented to query Bedrock Knowledge Base
    # For now, it's a placeholder that guides the LLM
    return f"Query Knowledge Base for term: {term}"


@tool
def translate_text(
    text: str,
    source_language: str = "English",
    target_language: str = "Russian"
) -> str:
    """
    Translate text from source language to target language.
    
    Args:
        text: Text to translate
        source_language: Source language name
        target_language: Target language name
        
    Returns:
        Translated text
    """
    # The LLM will perform the actual translation
    # This tool just structures the request
    return f"Translate from {source_language} to {target_language}: {text}"


@tool
def refine_translation_section(
    section_to_refine: str,
    issue_description: str,
    suggested_improvement: str = ""
) -> str:
    """
    Refine a specific section of a translation based on identified issues.
    
    Use this tool to improve problematic parts of your translation.
    
    Args:
        section_to_refine: The specific text that needs improvement
        issue_description: What's wrong with it (e.g., "sounds unnatural", "wrong term")
        suggested_improvement: Your proposed better version
        
    Returns:
        Guidance for refinement
    """
    return f"""
Refining section: "{section_to_refine}"

Issue: {issue_description}

Your suggested improvement: {suggested_improvement if suggested_improvement else "[Provide your improved version]"}

Now provide the refined translation incorporating this improvement.
"""


def extract_technical_terms(text: str) -> List[str]:
    """
    Helper function to extract potential technical terms from text.
    Not exposed as a tool - used internally.
    """
    # Simple heuristic: capitalized words, acronyms, compound technical terms
    terms = []
    
    # Find capitalized words (potential service names)
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    terms.extend(capitalized)
    
    # Find acronyms
    acronyms = re.findall(r'\b[A-Z]{2,}\b', text)
    terms.extend(acronyms)
    
    # Common technical terms
    technical_keywords = [
        'serverless', 'function', 'trigger', 'scaling', 'compute',
        'provisioning', 'microservices', 'backend', 'API', 'runtime'
    ]
    
    for keyword in technical_keywords:
        if keyword.lower() in text.lower():
            terms.append(keyword)
    
    return list(set(terms))  # Remove duplicates


def format_translation_result(
    original_text: str,
    final_translation: str,
    iterations: int,
    issues_found: List[str]
) -> Dict[str, any]:
    """
    Format the final translation result with metadata.
    """
    return {
        "original": original_text,
        "translation": final_translation,
        "iterations": iterations,
        "issues_resolved": issues_found,
        "status": "complete"
    }
