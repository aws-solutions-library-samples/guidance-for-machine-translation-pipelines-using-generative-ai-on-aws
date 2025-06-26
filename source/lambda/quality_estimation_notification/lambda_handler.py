import json
import boto3
import base64
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
sfn = boto3.client('stepfunctions')


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

def lambda_handler(event, context):
    """
    Processes SNS notifications from SageMaker async endpoint and sends task tokens
    back to Step Functions to resume execution.
    
    The task token is stored in the output file in the metadata.TaskToken field.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract the SNS message
        sns_message = json.loads(event['Records'][0]['Sns']['Message'])
        logger.info(f"SNS message: {sns_message}")

        task_token = extract_task_token(sns_message['requestParameters']['customAttributes'])
        if task_token:
            logger.info("Found Step Functions Task Token in request")
        
        # Get the S3 output path from the SNS message
        output_path = sns_message.get('responseParameters', {}).get('outputLocation')
        if not output_path:
            raise ValueError("Output path not found in SNS message")
        
        
        # Check if the job was successful
        if sns_message.get('invocationStatus') == 'Completed':
            # Get the results from S3
            try:

                # Send success signal to Step Functions
                sfn.send_task_success(
                    taskToken=task_token,
                    output=json.dumps({
                        'status': 'SUCCESS',
                        'outputPath': output_path
                    })
                )
                
            except Exception as e:
                logger.error(f"Error processing results: {e}")
                
                # Try to get the task token even if processing the results failed
                try:
                     
                    # Send failure signal to Step Functions
                    sfn.send_task_failure(
                        taskToken=task_token,
                        error='ResultProcessingError',
                        cause=str(e)
                    )
                    logger.info(f"Sent task failure with token: {task_token}")
                    # else:
                    #     logger.error("Could not extract task token from result metadata")
                except Exception as token_error:
                    logger.error(f"Error extracting task token: {token_error}")
        else:
            # Job failed, try to get the task token from the output file
            try:
                error = sns_message.get('failureReason', 'Unknown error')
                sfn.send_task_failure(
                    taskToken=task_token,
                    error='SageMakerJobFailed',
                    cause=error
                )
                logger.info(f"Sent task failure with token: {task_token}")
                # else:
                #     logger.error("Could not extract task token from result metadata")
            except Exception as token_error:
                logger.error(f"Error extracting task token: {token_error}")
                logger.error(f"SageMaker job failed: {sns_message.get('failureReason', 'Unknown error')}")
        
        return {
            'statusCode': 200,
            'message': 'Successfully processed SNS notification'
        }
        
    except Exception as e:
        logger.error(f"Error processing SNS notification: {e}")
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Error processing SNS notification'
        }
