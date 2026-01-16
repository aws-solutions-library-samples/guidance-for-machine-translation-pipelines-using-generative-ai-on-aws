"""
OpsBuddy Agent - Simplified Strands Agent for Operations Assistance
Designed for notebook usage with explicit knowledge base configuration.
"""
import boto3
import json
import logging
from typing import Dict, List, Any, Optional
from strands import Agent, tool
from strands_tools import use_aws

# Configure logging
logging.getLogger("strands").setLevel(logging.INFO)


class OpsBuddyAgent:
    """
    Simplified Strands AI Agent for operations assistance.
    
    Features:
    - Single knowledge base integration (explicit KB ID)
    - AWS service operations via use_aws tool
    - CloudWatch monitoring capabilities
    - Direct Bedrock model queries
    """
    
    def __init__(
        self, 
        kb_id: str,
        model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0",
        region: str = "us-east-1"
    ):
        """
        Initialize OpsBuddy Agent.
        
        Args:
            kb_id: Amazon Bedrock Knowledge Base ID
            model_id: Bedrock model ID to use
            region: AWS region
        """
        self.kb_id = kb_id
        self.model_id = model_id
        self.region = region
        
        # Initialize AWS clients
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        
        # Create system prompt
        self.system_prompt = self._create_system_prompt()
        
        # Initialize tools and agent
        self.tools = self._create_tools()
        self.agent = self._create_agent()
        
        print(f"✅ OpsBuddy Agent initialized")
        print(f"📚 Knowledge Base: {kb_id}")
        print(f"🤖 Model: {model_id}")
        print(f"🌍 Region: {region}")
    
    def _create_system_prompt(self) -> str:
        """Create the agent's system prompt"""
        return f"""You are OpsBuddy, an intelligent operations assistant for AWS infrastructure.

Your role is to:
1. Monitor AWS resources and CloudWatch alarms
2. Search operations runbooks in the Knowledge Base (ID: {self.kb_id})
3. Diagnose issues and recommend remediation steps
4. Execute approved AWS operations to resolve incidents

Available capabilities:
- retrieve_from_knowledge_base: Search runbooks and documentation
- get_cloudwatch_alarms: Check active CloudWatch alarms
- query_bedrock_model: Direct model queries for general assistance
- use_aws: Execute AWS CLI commands and manage resources

When investigating an issue:
1. Check CloudWatch alarms to identify active problems
2. Search the Knowledge Base for relevant runbooks
3. Analyze the situation and propose remediation steps
4. Ask for approval before executing any changes
5. Execute approved remediation actions
6. Verify the issue is resolved

Always explain your reasoning and provide clear, actionable recommendations.
Be concise but thorough in your responses.
"""
    
    def _create_tools(self) -> List:
        """Create tools for the agent"""
        
        @tool
        def retrieve_from_knowledge_base(query: str, num_results: int = 3) -> str:
            """
            Retrieve relevant information from the operations runbook Knowledge Base.
            
            Args:
                query: The search query
                num_results: Number of results to return (default: 3)
            
            Returns:
                Formatted string with retrieved documents
            """
            try:
                response = self.bedrock_agent_runtime.retrieve(
                    knowledgeBaseId=self.kb_id,
                    retrievalQuery={'text': query},
                    retrievalConfiguration={
                        'vectorSearchConfiguration': {
                            'numberOfResults': num_results
                        }
                    }
                )
                
                # Format results
                results = []
                for i, result in enumerate(response['retrievalResults'], 1):
                    score = result['score']
                    content = result['content']['text']
                    source = result['location'].get('s3Location', {}).get('uri', 'Unknown')
                    results.append(
                        f"Document {i} (Relevance: {score:.3f}):\n{content}\n\nSource: {source}"
                    )
                
                return "\n\n---\n\n".join(results) if results else "No relevant documents found."
                
            except Exception as e:
                return f"Error retrieving from knowledge base: {str(e)}"
        
        @tool
        def get_cloudwatch_alarms(state_value: str = "ALARM") -> str:
            """
            Get CloudWatch alarms filtered by state.
            
            Args:
                state_value: Alarm state to filter by (ALARM, OK, INSUFFICIENT_DATA)
            
            Returns:
                Formatted string with alarm details
            """
            try:
                response = self.cloudwatch.describe_alarms(
                    StateValue=state_value,
                    MaxRecords=10
                )
                
                if not response['MetricAlarms']:
                    return f"No alarms in {state_value} state found."
                
                alarms = []
                for alarm in response['MetricAlarms']:
                    alarm_info = f"""Alarm Name: {alarm['AlarmName']}
State: {alarm['StateValue']}
Reason: {alarm.get('StateReason', 'N/A')}
Metric: {alarm.get('MetricName', 'N/A')}
Namespace: {alarm.get('Namespace', 'N/A')}
Threshold: {alarm.get('Threshold', 'N/A')}
Comparison: {alarm.get('ComparisonOperator', 'N/A')}"""
                    
                    # Add dimension info if available
                    if alarm.get('Dimensions'):
                        dims = ', '.join([f"{d['Name']}={d['Value']}" for d in alarm['Dimensions']])
                        alarm_info += f"\nDimensions: {dims}"
                    
                    alarms.append(alarm_info)
                
                return "\n\n---\n\n".join(alarms)
                
            except Exception as e:
                return f"Error getting CloudWatch alarms: {str(e)}"
        
        @tool
        def query_bedrock_model(prompt: str) -> str:
            """
            Query the Bedrock foundation model directly for general assistance.
            
            Args:
                prompt: The question or prompt
            
            Returns:
                Model's response
            """
            try:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                }
                
                response = self.bedrock_runtime.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body),
                    contentType='application/json'
                )
                
                response_body = json.loads(response['body'].read())
                return response_body['content'][0]['text']
                
            except Exception as e:
                return f"Error querying Bedrock model: {str(e)}"
        
        # Return all tools including use_aws from strands_tools
        return [
            retrieve_from_knowledge_base,
            get_cloudwatch_alarms,
            query_bedrock_model,
            use_aws
        ]
    
    def _create_agent(self) -> Agent:
        """Create the Strands Agent"""
        return Agent(
            model=self.model_id,
            system_prompt=self.system_prompt,
            tools=self.tools
        )
    
    def invoke(self, query: str) -> str:
        """
        Invoke the agent with a query.
        
        Args:
            query: User's question or request
        
        Returns:
            Agent's response as a string
        """
        try:
            # Try different methods to invoke the Strands Agent
            if hasattr(self.agent, 'invoke'):
                result = self.agent.invoke(query)
            elif hasattr(self.agent, 'run'):
                result = self.agent.run(query)
            elif hasattr(self.agent, 'chat'):
                result = self.agent.chat(query)
            elif hasattr(self.agent, '__call__'):
                result = self.agent(query)
            else:
                return f"Error: Agent has no invoke/run/chat/__call__ method"
            
            # Extract content from result
            if hasattr(result, 'content'):
                return result.content
            elif hasattr(result, 'text'):
                return result.text
            elif hasattr(result, 'message'):
                return result.message
            else:
                return str(result)
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"Error processing query: {str(e)}\n\nDetails:\n{error_details}"
    
    def chat(self, message: str) -> str:
        """
        Alias for invoke() - more intuitive for chat interactions.
        
        Args:
            message: User's message
        
        Returns:
            Agent's response
        """
        return self.invoke(message)
    
    def get_agent_methods(self) -> list:
        """
        Get available methods on the agent object for debugging.
        
        Returns:
            List of method names
        """
        return [method for method in dir(self.agent) if not method.startswith('_')]


def create_ops_buddy(
    kb_id: str,
    model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0",
    region: str = "us-east-1"
) -> OpsBuddyAgent:
    """
    Convenience function to create an OpsBuddy agent.
    
    Args:
        kb_id: Amazon Bedrock Knowledge Base ID
        model_id: Bedrock model ID (default: Claude 4 Sonnet)
        region: AWS region (default: us-east-1)
    
    Returns:
        Configured OpsBuddyAgent instance
    
    Example:
        >>> agent = create_ops_buddy(kb_id="ABCD1234")
        >>> response = agent.invoke("What tools do you have?")
        >>> print(response)
    """
    return OpsBuddyAgent(kb_id=kb_id, model_id=model_id, region=region)
