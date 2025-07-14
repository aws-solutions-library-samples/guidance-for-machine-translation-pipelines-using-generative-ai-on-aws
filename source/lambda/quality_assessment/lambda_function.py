import logging
import json
import boto3
import os
import re

MODEL_ID = os.getenv('MODEL_ID')
BATCH_ROLE_ARN = os.environ.get('BATCH_ROLE_ARN',)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client(service_name="bedrock")
s3 = boto3.client('s3')
ssm = boto3.client('ssm')
sfn = boto3.client('stepfunctions')

# Load prompt template
with open('task_prompt_template.txt', 'r') as file: # nosemgrep
    PROMPT_TEMPLATE = file.read()

with open('system_prompt_template.txt', 'r') as file: # nosemgrep
        SYSTEM_PROMPT_TEMPLATE = file.read()

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Check if this is a batch inference request
    if 'inferenceMethod' in event and event['inferenceMethod'] == 'batch':
        return handle_batch_inference(event, context)
    else:
        # Handle on-demand processing
        return handle_on_demand_processing(event, context)

def handle_on_demand_processing(event, context):
    translation_items = []
    try:
        for item_element in event['Items']:
            item = item_element['item']
            assessed_translation_item = assess_translation_item(item)
            translation_items.append(assessed_translation_item)
        return translation_items
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error processing request: {str(e)}'
            })
        }

def handle_batch_inference(event, context):
    try:
        execution_id = event.get('executionId')
        bucket = event.get('input_bucket')
        input_key = event.get('input_file')
        if bucket in input_key:
            input_key = input_key.split(f"{bucket}/")[1]
            logger.info(f"input_key: {input_key}")
            
        prefix = input_key.split("pipeline")[0]
        task_token = event.get('taskToken', '')
        
        
        if not BATCH_ROLE_ARN:
            raise ValueError("BATCH_ROLE_ARN environment variable is not set")
        
        # Download and process batch output file
        prompts_file_key = prepare_assessment_prompts(bucket, input_key, prefix, execution_id)
        
        # Start Bedrock batch inference job
        job_name = f"assessment-job-{execution_id}"
        
        response = bedrock.create_model_invocation_job(
            jobName=job_name,
            roleArn=BATCH_ROLE_ARN,
            modelId=MODEL_ID,
            inputDataConfig={
                "s3InputDataConfig": {
                    "s3Uri": f"s3://{bucket}/{prompts_file_key}"
                }
            },
            outputDataConfig={
                "s3OutputDataConfig": {
                    "s3Uri": f"s3://{bucket}/{prefix}pipeline/quality_control/{execution_id}/"
                }
            }
        )
        
        job_arn = response['jobArn']
        logger.info(f"Started Bedrock batch job: {job_arn}")
        
        # Store task token in Parameter Store
        param_name = f"/bedrock/batch-jobs/{execution_id}/assessment-task-token"
        ssm.put_parameter(
            Name=param_name,
            Value=task_token,
            Type='SecureString',
            Overwrite=True
        )
        
        return {
            'statusCode': 200,
            'jobArn': job_arn,
            'jobName': job_name,
            'outputLocation': f"s3://{os.path.join(bucket,prefix,"pipeline/quality_control/")}",
            'taskTokenParameter': param_name
        }
        
    except Exception as e:
        logger.error(f"Error starting batch assessment job: {str(e)}", exc_info=True)
        if task_token:
            try:
                sfn.send_task_failure(
                    taskToken=task_token,
                    error='BatchAssessmentJobStartError',
                    cause=str(e)
                )
            except Exception as token_error:
                logger.error(f"Error sending task failure: {str(token_error)}")
        
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Error starting Bedrock batch assessment job'
        }

def prepare_assessment_prompts(bucket, input_key, prefix, execution_id):
    """Download batch output, create assessment prompts, and upload to S3"""
    try:
        # Download the batch output file
        response = s3.get_object(Bucket=bucket, Key=input_key)
        batch_content = response['Body'].read().decode('utf-8')
        
        # Process each line and create assessment prompts
        assessment_prompts = []
        for line in batch_content.strip().split('\n'):
            if line.strip():
                record = json.loads(line)
                modelInput = create_assessment_prompt(record)
                recordId = record['recordId']
                if modelInput:
                    assessment_prompts.append({'modelInput':modelInput,'recordId':recordId})
        
        # Upload prompts file to S3
        prompts_content = '\n'.join([json.dumps(prompt) for prompt in assessment_prompts])
        prompts_file_key = os.path.join(prefix,f"pipeline/assessment_prompts/prompts.jsonl")
        
        s3.put_object(
            Bucket=bucket,
            Key=prompts_file_key,
            Body=prompts_content,
            ContentType='application/jsonl'
        )
        
        logger.info(f"Created assessment prompts file: s3://{bucket}/{prompts_file_key}")
        return prompts_file_key
        
    except Exception as e:
        logger.error(f"Error preparing assessment prompts: {str(e)}", exc_info=True)
        raise

def create_assessment_prompt(record):
    """Create assessment prompt from batch output record"""
    try:
        model_input = record['modelInput']
        model_output = record['modelOutput']
        
        # Extract source text from model input
        input_text = model_input['messages'][0]['content'][0]['text']
        
        # Parse source and target languages
        source_lang_match = re.search(r'from\s+(\w+)\s+to', input_text)
        target_lang_match = re.search(r'to\s+(\w+)', input_text)
        
        source_lang = source_lang_match.group(1) if source_lang_match else "unknown"
        target_lang = target_lang_match.group(1) if target_lang_match else "unknown"
        
        # Extract source text
        source_text_match = re.search(r'Source text \(.*?\):(.*?)(?:Context information:|$)', input_text, re.DOTALL)
        source_text = source_text_match.group(1).strip() if source_text_match else ""
        
        # Extract translated text from model output
        translated_text = model_output['output']['message']['content'][0]['text'].strip()
        
        # Fill in the template
        prompt = PROMPT_TEMPLATE.replace('{{source_lang}}', source_lang)
        prompt = prompt.replace('{{target_lang}}', target_lang)
        prompt = prompt.replace('{{source_text}}', source_text)
        prompt = prompt.replace('{{translated_text}}', translated_text)

        system_prompt = SYSTEM_PROMPT_TEMPLATE.replace('{{source_lang}}', source_lang)
        system_prompt = system_prompt.replace('{{target_lang}}', target_lang)
        return {
            "messages": [
                {"role": "user", "content": [{"text": prompt}]}
            ],
            "system": [
                {"text": system_prompt}
            ],
            "inferenceConfig": {
                "maxTokens": int(os.getenv('MAX_NEW_TOKEN', 512)),
                "topP": float(os.getenv('TOP_P', 0.9)),
                "temperature": float(os.getenv('TEMPERATURE', 0.1))
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating assessment prompt for record {record.get('recordId', 'unknown')}: {str(e)}")
        return None

def assess_translation_item(item):
    """
    Lambda function to assess translation quality using Amazon Nova Pro.
    
    This function:
    1. Parses the input event to extract source language, target language, source text, and translated text
    2. Creates a prompt for Amazon Nova Pro using a template
    3. Invokes Nova Pro via Bedrock SDK
    4. Parses the response and returns a quality assessment
    
    Expected input event structure:
    {
        "modelInput": {
            "inputText": "Task: Translate the following text from [source_lang] to [target_lang]..."
        },
        "modelOutput": {
            "results": [
                {
                    "outputText": "Translated text...",
                    "completionReason": "FINISH"
                }
            ]
        },
        "recordId": "unique-record-id"
    }
    
    Expected output structure:
    {
        "assessment": {
            "overall_status": "MEETS_REQUIREMENTS|NEEDS_ATTENTION",
            "dimensions": {
                "accuracy": {
                    "status": "MEETS_REQUIREMENTS|NEEDS_ATTENTION",
                    "comment": "Recommendations if needed"
                },
                "fluency": {
                    "status": "MEETS_REQUIREMENTS|NEEDS_ATTENTION",
                    "comment": "Recommendations if needed"
                },
                "style": {
                    "status": "MEETS_REQUIREMENTS|NEEDS_ATTENTION",
                    "comment": "Recommendations if needed"
                },
                "terminology": {
                    "status": "MEETS_REQUIREMENTS|NEEDS_ATTENTION",
                    "comment": "Recommendations if needed"
                }
            }
        },
        "recordId": "unique-record-id"
    }
    """
    logger.info(f"Received item. Running assessment... {json.dumps(item)}")
    
    # Extract source language, target language, source text, and translated text
    input_text = item['modelInput']['inputText']
    output_text = item['modelOutput']['results'][0]['outputText']
    reason = item['modelOutput']['results'][0]['completionReason']
    record_id = item['recordId']
    
    if reason == "ERROR":
        assessment = {
            "overall_status": "ERROR",
            "dimensions": {
                "accuracy": {"status": "NOT_ASSESSED", "comment": ""},
                "fluency": {"status": "NOT_ASSESSED", "comment": ""},
                "style": {"status": "NOT_ASSESSED", "comment": ""},
                "terminology": {"status": "NOT_ASSESSED", "comment": ""}
            }
        }
        return {"assessment": assessment, "recordId": record_id}

    # Parse source and target languages from input text
    source_lang_match = re.search(r'from\s+(\w+)\s+to', input_text)
    target_lang_match = re.search(r'to\s+(\w+)', input_text)
    
    source_lang = source_lang_match.group(1) if source_lang_match else "unknown"
    target_lang = target_lang_match.group(1) if target_lang_match else "unknown"
    
    # Extract source text to translate
    source_text_match = re.search(r'Source text \(.*?\):(.*?)(?:Context information:|Translation \()', input_text, re.DOTALL)
    source_text = source_text_match.group(1).strip() if source_text_match else ""
    
    # Extract translated text from output
    translated_text = output_text.strip()
    
    
    # Fill in the template
    prompt = PROMPT_TEMPLATE.replace('{{source_lang}}', source_lang)
    prompt = prompt.replace('{{target_lang}}', target_lang)
    prompt = prompt.replace('{{source_text}}', source_text)
    prompt = prompt.replace('{{translated_text}}', translated_text)
    
    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace('{{source_lang}}', source_lang)
    system_prompt = system_prompt.replace('{{target_lang}}', target_lang)
    
    
    # Invoke Amazon Nova Pro via Bedrock
    bedrock_runtime = boto3.client('bedrock-runtime')
    
    # Define your system prompt(s).
    system_list = [
        {"text": system_prompt}
    ]

    # Define one or more messages using the "user" and "assistant" roles.
    message_list = [
                       {"role":"user","content":[{"text":prompt}]}
                   ]

    # Configure the inference parameters.
    inf_params = {
        "max_new_tokens": int(os.getenv('MAX_NEW_TOKEN', 512)), 
        "top_p": float(os.getenv('TOP_P', 0.9)), 
        "temperature": float(os.getenv('TEMPERATURE', 0.1))
    }

    request_body = {
        "messages": message_list,
        "system": system_list,
        "inferenceConfig": inf_params,
    }
    
    logger.info(f"Sending request to Bedrock: {json.dumps(request_body)}")
    assessment = None

    # Invoke the model
    try:
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read().decode())
        #logger.info(f"Received response from Bedrock: {json.dumps(response_body)}")
        model_output = response_body["output"]["message"]
        logger.info(f"Received response from Bedrock: {json.dumps(model_output)}")
        
        # Check if 'content' key exists in the response
        if 'content' in model_output:
            assessment_text = model_output['content'][0]['text']
        else:
            # Handle different response format
            logger.warning(f"Unexpected response format: {json.dumps(response_body)}")
            assessment_text = json.dumps(response_body)
    except Exception as e:
        logger.error(f"Error invoking Bedrock: {str(e)}")
        # Create a default assessment for error case
        assessment = {
            "overall_status": "NEEDS_ATTENTION",
            "dimensions": {
                "accuracy": {
                    "status": "NEEDS_ATTENTION",
                    "comment": f"Error invoking Bedrock: {str(e)}"
                },
                "fluency": {"status": "MEETS_REQUIREMENTS", "comment": ""},
                "style": {"status": "MEETS_REQUIREMENTS", "comment": ""},
                "terminology": {"status": "MEETS_REQUIREMENTS", "comment": ""}
            }
        }
        #return {"assessment": assessment, "recordId": record_id}
    
    # Parse the assessment JSON from the response
    if assessment is None:
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', assessment_text, re.DOTALL)
            if json_match:
                assessment = json.loads(json_match.group(0))
            else:
                # Fallback if no JSON is found - create a default assessment structure
                assessment = {
                    "overall_status": "NEEDS_ATTENTION",
                    "dimensions": {
                        "accuracy": {
                            "status": "NEEDS_ATTENTION",
                            "comment": "Failed to parse model response properly. Raw response: " + assessment_text
                        },
                        "fluency": {
                            "status": "MEETS_REQUIREMENTS",
                            "comment": ""
                        },
                        "style": {
                            "status": "MEETS_REQUIREMENTS",
                            "comment": ""
                        },
                        "terminology": {
                            "status": "MEETS_REQUIREMENTS",
                            "comment": ""
                        }
                    }
                }
        except Exception as e:
            logger.error(f"Error parsing assessment: {str(e)}")
            assessment = {
                "overall_status": "NEEDS_ATTENTION",
                "dimensions": {
                    "accuracy": {
                        "status": "NEEDS_ATTENTION",
                        "comment": f"Error parsing assessment: {str(e)}. Raw response: {assessment_text}"
                    },
                    "fluency": {
                        "status": "MEETS_REQUIREMENTS",
                        "comment": ""
                    },
                    "style": {
                        "status": "MEETS_REQUIREMENTS",
                        "comment": ""
                    },
                    "terminology": {
                        "status": "MEETS_REQUIREMENTS",
                        "comment": ""
                    }
                }
            }
    
    # Prepare the output
    result = {
        "source_language":  source_lang,
        "target_language": target_lang,
        "source_text": source_text,
        "translated_text": translated_text,
        "assessment": assessment,
        "recordId": record_id
    }
    return result
