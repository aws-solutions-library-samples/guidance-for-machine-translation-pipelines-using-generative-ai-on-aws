"""
Production translation agent for AgentCore deployment.
"""

from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel
import boto3
import os

# Initialize AgentCore app
app = BedrockAgentCoreApp()

# Get Knowledge Base ID from environment
KB_ID = os.environ.get('KNOWLEDGE_BASE_ID', '')

# Define tools
@tool
def evaluate_translation_quality(
    source_text: str,
    translated_text: str,
    target_language: str = "Russian"
) -> dict:
    """Evaluate translation quality and identify issues."""
    return {
        "quality_score": 0,
        "issues": [],
        "needs_refinement": True,
        "evaluation_prompt": f"""
        Evaluate this {target_language} translation:
        Source: {source_text}
        Translation: {translated_text}
        
        Check accuracy, fluency, terminology, and tone.
        Provide quality_score (0-100), issues list, and needs_refinement flag.
        """
    }

@tool
def query_aws_terminology(term: str) -> str:
    """Query AWS terminology Knowledge Base."""
    if not KB_ID:
        return f"Knowledge Base not configured for term: {term}"
    
    try:
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
        query = f"What is the correct Russian translation for '{term}'?"
        
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {'numberOfResults': 1}
            }
        )
        
        if response.get('retrievalResults'):
            content = response['retrievalResults'][0].get('content', {}).get('text', '')
            return f"Terminology for '{term}': {content}"
        return f"No terminology found for '{term}'"
    except Exception as e:
        return f"Error querying terminology: {str(e)}"

@tool
def refine_translation_section(
    original_translation: str,
    section_to_refine: str,
    refinement_instructions: str
) -> str:
    """Refine specific section of translation."""
    return f"Refine: {section_to_refine} - Instructions: {refinement_instructions}"

# Configure model
model = BedrockModel(
    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0"
)

# Create agent
agent = Agent(
    model=model,
    tools=[
        evaluate_translation_quality,
        query_aws_terminology,
        refine_translation_section
    ],
    system_prompt="""
    You are a production-quality translation agent.
    
    Workflow:
    1. Translate English to Russian
    2. Validate technical terms using query_aws_terminology
    3. Evaluate quality using evaluate_translation_quality
    4. Refine if quality_score < 85
    5. Repeat until quality >= 85
    
    Rules:
    - Keep AWS service names in English
    - Use natural, fluent Russian
    - Validate all technical terms
    - Show iteration count and validated terms
    """
)

@app.entrypoint
def invoke(payload, context):
    """AgentCore entrypoint for translation requests."""
    user_message = payload.get(
        "prompt",
        "Please provide text to translate in the 'prompt' field"
    )
    
    result = agent(user_message)
    
    return {
        "result": result.message,
        "iterations": len(agent.messages) // 2,
        "status": "complete"
    }

if __name__ == "__main__":
    app.run()

print("✅ Production agent entrypoint created!")
