import boto3
import os
import json
import logging
from botocore.exceptions import ClientError
from quality_estimator_base import QualityEstimatorBase

logger = logging.getLogger()

def convert_json_array_to_jsonl(data):
    json_string=""
    for item in data:
        json_dumps = json.dumps(item)
        json_string = json_string + '\n' + json_dumps
    return json_string.strip()

def to_comet_input_payload(item):
    print("Preparing: "+repr(item))
    if 'source_text' in item:
        data = {
            'src': item['source_text'],
            'mt': item['translated_text']
        }
        return data
    return None

class MarketplaceEndpointEstimator(QualityEstimatorBase):
    """Implementation for Marketplace real-time SageMaker endpoint"""
    
    def __init__(self):
        cross_account = os.environ.get('USE_CROSS_ACCOUNT_ENDPOINT')

        if cross_account == 'Y':
            cross_account_role_arn = os.environ.get('CROSS_ACCOUNT_ENDPOINT_ACCESS_ROLE_ARN')
            cross_account_account_id = os.environ.get('CROSS_ACCOUNT_ENDPOINT_ACCOUNT_ID')
            sts_client = boto3.client('sts')
            assumed_role = sts_client.assume_role(
                RoleArn=cross_account_role_arn,  # add parent id here
                RoleSessionName='SageMakerInvokeSession',
                ExternalId=cross_account_account_id, # add parent id here
            )
            
            # Create a new session using the assumed role credentials
            credentials = assumed_role['Credentials']
            self.sagemaker_runtime = boto3.client(
                'sagemaker-runtime',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
            )
        else:
            self.sagemaker_runtime = boto3.client('sagemaker-runtime')

        self.s3 = boto3.client('s3')
        self.sfn = boto3.client('stepfunctions')
        self.endpoint_name = os.environ.get('MARKETPLACE_ENDPOINT_NAME')
        if not self.endpoint_name:
            raise ValueError("Missing required environment variable: MARKETPLACE_ENDPOINT_NAME")

    def invoke_endpoint(self, input_bucket, input_file, task_token):
        """
        Invokes the real-time Marketplace SageMaker endpoint
        
        Args:
            input_bucket (str): S3 bucket containing input data
            input_file (str): S3 key for input file
            task_token (str): Step Functions task token
            
        Returns:
            dict: Response from the endpoint invocation
        """
        try:
            # Get the input data from S3
            response = self.s3.get_object(Bucket=input_bucket, Key=input_file)
            input_data = response['Body'].read().decode('utf-8')
            
            # Process the input data - assuming JSONL format
            results = []
            data = []
            valid_items = []
            for line in input_data.strip().split('\n'):
                # Invoke the endpoint for each line
                line = json.loads(line)
                item = to_comet_input_payload(line)
                if item is not None:
                    data.append(item)
                    valid_items.append(line)
            
            endpoint_response = self.sagemaker_runtime.invoke_endpoint(
                    EndpointName=self.endpoint_name,
                    ContentType='application/json',
                    Body=json.dumps({"data": data})
                )
            # Parse the response
            results = json.loads(endpoint_response['Body'].read().decode())
            #results.append(result)
            scores = results['scores']
            for i, score in enumerate(scores):
                valid_items[i]['score'] = score

            # Store the results back to S3
            output_key = f"{input_file.rsplit('/', 1)[0]}/SCORED-{input_file.rsplit('/', 1)[1]}"
            self.s3.put_object(
                Bucket=input_bucket,
                Key=output_key,
                Body=convert_json_array_to_jsonl(valid_items),
                ContentType='application/jsonl'
            )
            
            # Send success signal to Step Functions directly
            self.sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps({
                    'status': 'SUCCESS',
                    'outputPath': f"s3://{input_bucket}/{output_key}"
                })
            )
            logger.info(f"Successfully invoked real-time Marketplace endpoint: {self.endpoint_name}")
            
            return {
                'statusCode': 200,
                'message': 'Successfully completed real-time inference',
                'outputLocation': f"s3://{input_bucket}/{output_key}",
                'requestToken': task_token
            }
            
        except ClientError as e:
            logger.error(f"AWS service error: {e}") # nosemgrep
            # Send failure signal to Step Functions
            try:
                self.sfn.send_task_failure(
                    taskToken=task_token,
                    error='EndpointInvocationError',
                    cause=str(e)
                )
            except Exception as sfn_error:
                logger.error(f"Error sending task failure: {sfn_error}")
            raise