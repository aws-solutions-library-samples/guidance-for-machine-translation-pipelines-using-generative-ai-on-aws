import json
import boto3
import os
import base64
import logging
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
sagemaker_runtime = boto3.client('sagemaker-runtime')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Invokes a SageMaker asynchronous endpoint and configures it to notify an SNS topic
    when processing is complete.
    
    Expected event format:
    {
        "executionId": "execution-id",
        "input_file": "path/to/input/file.jsonl",
        "input_bucket": "input-bucket-name"
    }
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Get environment variables
        endpoint_name = os.environ.get('SAGEMAKER_ENDPOINT_NAME')
        
        if not endpoint_name:
            raise ValueError("Missing required environment variable: SAGEMAKER_ENDPOINT_NAME")
        
        # Extract parameters from the event
        execution_id = event.get('executionId')
        input_file = event.get('input_file')
        input_bucket = event.get('input_bucket')
        task_token = event.get('taskToken')

        if not all([execution_id, input_file, input_bucket]):
            raise ValueError("Missing required parameters in the event")
        
        encoded_token = base64.b64encode(task_token.encode()).decode()
        custom_attributes = f"TaskToken={encoded_token}"
 
        
        # Invoke the SageMaker endpoint asynchronously
        response = sagemaker_runtime.invoke_endpoint_async(
            EndpointName=endpoint_name,
            InputLocation=f"s3://{input_bucket}/{input_file}",
            ContentType='application/jsonl',
            InvocationTimeoutSeconds=900,  # 15 minutes timeout
            RequestTTLSeconds=3600,  # Request will be valid for 1 hour
            CustomAttributes=custom_attributes
        )
        
        logger.info(f"Successfully invoked SageMaker endpoint: {endpoint_name}")
        logger.info(f"Response: {response}")
        
        # Return the response with additional context
        return {
            'statusCode': 200,
            'executionId': execution_id,
            'requestId': response.get('InferenceId'),
            'outputLocation': response.get('OutputLocation'),
            'message': 'Successfully initiated asynchronous inference',
            'requestToken': task_token
        }
        
    except ClientError as e:
        logger.error(f"AWS service error: {e}")
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Error invoking SageMaker endpoint'
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Unexpected error occurred'
        }
