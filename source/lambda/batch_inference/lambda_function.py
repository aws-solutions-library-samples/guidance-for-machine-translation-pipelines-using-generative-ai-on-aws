import json
import boto3
import os
import logging
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client(service_name="bedrock")
sfn = boto3.client('stepfunctions')
ssm = boto3.client('ssm')

def lambda_handler(event, context):
    logger.info(repr(event))
    """
    {
        'MapRunArn': 'arn:aws:states:us-east-2:986528949439:mapRun:BatchMachineTranslationStateMachine/ShippingFileAnalysis:181a97e5-8237-4188-86fc-0876e0d0d161', 
        'ResultWriterDetails': {
            'Bucket': 'machine-translation-output-data', 
            'Key': 'prompts/181a97e5-8237-4188-86fc-0876e0d0d161/manifest.json'
            }
    }
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
            
        # Extract parameters from the event
        execution_id = event.get('executionId')
        bucket = event.get('input_bucket')
        input_key = event.get('input_file')
        prefix = input_key.split("pipeline")[0]
        task_token = event.get('taskToken', '')
        # Get model ID from environment variable or use default
        model_id = os.environ.get('MODEL_ID')
        # Get the role ARN from environment variable
        batch_role_arn = os.environ.get('BATCH_ROLE_ARN')
        if not batch_role_arn:
            raise ValueError("BATCH_ROLE_ARN environment variable is not set")


        #Start Bedrock batch inference job
        job_name = f"translation-job-{execution_id}"
        inputDataConfig=({
            "s3InputDataConfig": {
                "s3Uri": f"s3://{bucket}/{input_key}"
            }
        })

        logger.info(f"inputDataConfig:{inputDataConfig}")

        outputDataConfig=({
            "s3OutputDataConfig": {
                "s3Uri": f"s3://{os.path.join(bucket,prefix,'pipeline/inferences/')}"
            }
        })

        logger.info(f"outputDataConfig:{outputDataConfig}")

        response=bedrock.create_model_invocation_job(
            jobName=job_name,
            roleArn=batch_role_arn,
            modelId=model_id,
            inputDataConfig=inputDataConfig,
            outputDataConfig=outputDataConfig
        )
        job_arn = response['jobArn']

        logger.info(f"Started Bedrock batch job: {job_arn}")

        # jobId = job_arn.split('/')[-1]
        
        # Store task token and job ARN in Parameter Store
        param_name = f"/bedrock/batch-jobs/{execution_id}/task-token"
        ssm.put_parameter(
            Name=param_name,
            Value=task_token,
            Type='SecureString',
            Overwrite=True
        )
        
        logger.info(f"Stored task token in Parameter Store: {param_name}")
        
        return {
            'statusCode': 200,
            'jobArn': job_arn,
            'jobName': job_name,
            'outputLocation': outputDataConfig['s3OutputDataConfig']['s3Uri'],
            'taskTokenParameter': param_name
        }
        
    except Exception as e:
        logger.error(f"Error starting batch job: {str(e)}", exc_info=True)
        # If there's an error, we need to send a task failure to Step Functions
        # so the workflow can continue or handle the error
        if 'task_token' in locals() and task_token:
            try:
                sfn.send_task_failure(
                    taskToken=task_token,
                    error='BatchJobStartError',
                    cause=str(e)
                )
                logger.info(f"Sent task failure with token: {task_token}")
            except Exception as token_error:
                logger.error(f"Error sending task failure: {str(token_error)}")
        
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Error starting Bedrock batch job'
        }