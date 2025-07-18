import json
import boto3
import base64
import logging
import os
# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
sfn = boto3.client('stepfunctions')
s3 = boto3.client('s3')
bedrock = boto3.client('bedrock')
ssm = boto3.client('ssm')

def get_task_token_from_job_id(job_id,task_token_def):
    """Get task token from Parameter Store using job ID"""
    try:
        # Get task token from Parameter Store
        param_name = f"/bedrock/batch-jobs/{job_id}/{task_token_def}"
        response = ssm.get_parameter(
            Name=param_name,
            WithDecryption=True
        )
        
        task_token = response['Parameter']['Value']
        logger.info(f"Retrieved task token from Parameter Store: {task_token[:20]}...")
        return task_token
    except ssm.exceptions.ParameterNotFound:
        logger.warning(f"No parameter found for job ID: {job_id}")
        return None
    except Exception as e:
        logger.error(f"Error getting task token from Parameter Store: {str(e)}", exc_info=True)
        return None

def extract_task_token(custom_attributes):
    """Extract Step Functions Task Token from request headers"""
    try:
        logger.info(f"Received custom attributes: {custom_attributes}")
        
        # Parse the custom attributes
        attributes = {}
        for attr in custom_attributes.split(';'):
            if '=' in attr:
                key, value = attr.split('=', 1)
                attributes[key.strip()] = value.strip()
        
        # Extract and decode the task token
        if 'TaskToken' in attributes:
            encoded_token = attributes['TaskToken']
            task_token = base64.b64decode(encoded_token.encode()).decode()
            logger.info(f"Extracted Task Token: {task_token[:20]}...")
            return task_token
        
        return None
    except Exception as e:
        logger.error(f"Error extracting task token: {str(e)}", exc_info=True)
        return None

def handle_sagemaker_notification(sns_message):
    """Handle SageMaker asynchronous endpoint notifications"""
    try:
        
        task_token = extract_task_token(sns_message['requestParameters']['customAttributes'])
        if not task_token:
            logger.error("No task token found in SageMaker notification")
            return {
                'statusCode': 400,
                'message': 'No task token found in SageMaker notification'
            }
        
        # Get the S3 output path from the SNS message
        output_path = sns_message.get('responseParameters', {}).get('outputLocation')
        if not output_path:
            raise ValueError("Output path not found in SNS message")
        
        # Check if the job was successful
        if sns_message.get('invocationStatus') == 'Completed':
            # Send success signal to Step Functions
            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps({
                    'status': 'SUCCESS',
                    'outputPath': output_path
                })
            )
            logger.info(f"Sent task success for SageMaker job")
        else:
            # Job failed
            error = sns_message.get('failureReason', 'Unknown error')
            sfn.send_task_failure(
                taskToken=task_token,
                error='SageMakerJobFailed',
                cause=error
            )
            logger.info(f"Sent task failure with token: {task_token}")
        
        return {
            'statusCode': 200,
            'message': 'Successfully processed SageMaker notification'
        }
    except Exception as e:
        logger.error(f"Error processing SageMaker notification: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Error processing SageMaker notification'
        }
    
    

def handle_bedrock_notification(sns_message):
    """Handle Bedrock batch job notifications"""
    try:
        detail = sns_message.get('detail', {})
        job_status = detail.get('status')
        job_arn = detail.get('batchJobArn')
        job_name = detail.get('batchJobName')
        job_id = job_name.split('translation-job-')[-1] if 'translation-job-' in job_name else job_name.split('assessment-job-')[-1]
        task_token_def,output_file = ('task-token','SUCCEEDED_0') if 'translation-job-' in job_name else ('assessment-task-token','prompts')
        
        task_token = get_task_token_from_job_id(job_id,task_token_def)
        if not task_token:
            logger.error(f"No task token found for Bedrock job: {job_id}")
            return {
                'statusCode': 400,
                'message': 'No task token found for job'
            }
        
        if job_status == 'Completed':
            # Get output location from Bedrock API if not in SNS event
            output_location = detail.get('outputLocation')
            if not output_location:
                try:
                    job_response = bedrock.get_model_invocation_job(jobIdentifier=job_arn)
                    output_location = job_response.get('outputDataConfig', {}).get('s3OutputDataConfig', {}).get('s3Uri')
                    id = job_arn.split('/')[-1]
                    output_location = os.path.join(output_location, id, f'{output_file}.jsonl.out')
                    logger.info(f"Retrieved output location from Bedrock API: {output_location}")
                except Exception as e:
                    logger.error(f"Error getting job details from Bedrock API: {str(e)}")
                    output_location = None
            
            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps({
                        'status': 'SUCCESS',
                        'outputLocation': output_location,
                        'jobId': job_id,
                    }
                )
            )
            logger.info(f"Sent task success for Bedrock job {job_id}")
        elif job_status in ['Submitted','Validating','Scheduled','InProgress']:
            sfn.send_task_heartbeat(taskToken=task_token)
            logger.info(f"Sent heartbeat for Bedrock job {job_id}")
        else:
            error_reason = detail.get('failureReason', f"Job {job_status}")
            sfn.send_task_failure(
                taskToken=task_token,
                error='BedrockJobFailed',
                cause=error_reason
            )
            logger.info(f"Sent task failure for Bedrock job {job_id}: {error_reason}")
        
        return {
            'statusCode': 200,
            'message': f'Successfully processed Bedrock job notification for job {job_id}'
        }
    except Exception as e:
        logger.error(f"Error processing Bedrock notification: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Error processing Bedrock notification'
        }    
def lambda_handler(event, context):
    """
    Processes notifications from SageMaker async endpoint or Bedrock batch jobs
    and sends task tokens back to Step Functions to resume execution.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        # Extract the SNS message
        sns_message = json.loads(event['Records'][0]['Sns']['Message'])
        logger.info(f"SNS message: {sns_message}")
        
        # Check if this is a Bedrock event
        if sns_message.get('source') == 'aws.bedrock':
            return handle_bedrock_notification(sns_message)
        
        # Handle SNS notification from SageMaker async endpoint
        elif sns_message.get('eventSource') == 'aws:sagemaker':
            return handle_sagemaker_notification(sns_message)
        
        else:
            logger.error("Unsupported event type")
            return {
                'statusCode': 400,
                'message': 'Unsupported event type'
            }
        
    except Exception as e:
        logger.error(f"Error processing notification: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Error processing notification'
        }
