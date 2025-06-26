import boto3
import os
import base64
import logging
from botocore.exceptions import ClientError
from quality_estimator_base import QualityEstimatorBase

logger = logging.getLogger()

class AsyncEndpointEstimator(QualityEstimatorBase):
    """Implementation for self-hosted asynchronous SageMaker endpoint"""
    
    def __init__(self):
        self.sagemaker_runtime = boto3.client('sagemaker-runtime')
        self.endpoint_name = os.environ.get('SAGEMAKER_ENDPOINT_NAME')
        if not self.endpoint_name:
            raise ValueError("Missing required environment variable: SAGEMAKER_ENDPOINT_NAME")
    
    def invoke_endpoint(self, input_bucket, input_file, task_token):
        """
        Invokes the asynchronous SageMaker endpoint
        
        Args:
            input_bucket (str): S3 bucket containing input data
            input_file (str): S3 key for input file
            task_token (str): Step Functions task token
            
        Returns:
            dict: Response from the endpoint invocation
        """
        try:
            # Encode task token for custom attributes
            encoded_token = base64.b64encode(task_token.encode()).decode()
            custom_attributes = f"TaskToken={encoded_token}"
            
            # Invoke the SageMaker endpoint asynchronously
            response = self.sagemaker_runtime.invoke_endpoint_async(
                EndpointName=self.endpoint_name,
                InputLocation=f"s3://{input_bucket}/{input_file}",
                ContentType='application/jsonl',
                InvocationTimeoutSeconds=900,  # 15 minutes timeout
                RequestTTLSeconds=3600,  # Request will be valid for 1 hour
                CustomAttributes=custom_attributes
            )
            
            logger.info(f"Successfully invoked async SageMaker endpoint: {self.endpoint_name}")
            
            return {
                'statusCode': 200,
                'requestId': response.get('InferenceId'),
                'outputLocation': response.get('OutputLocation'),
                'message': 'Successfully initiated asynchronous inference',
                'requestToken': task_token
            }
            
        except ClientError as e:
            logger.error(f"AWS service error: {e}") # nosemgrep
            raise