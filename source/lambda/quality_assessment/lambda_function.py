import logging
import json
import boto3
import os
import re

model_id = os.getenv('MODEL_ID', 'us.amazon.nova-pro-v1:0')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    translation_items = []
    try:
        logger.info(f"Received event: {json.dumps(event)}")
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
    
    # Load prompt template
    try:
        with open('prompt_template.txt', 'r') as file: # nosemgrep
            prompt_template = file.read()
    except Exception as e:
        logger.error(f"Error loading prompt template: {str(e)}")
        # Fallback to a basic template if file can't be loaded
        prompt_template = """
        Task: Your task is to carefully read a source text and a translation from {{source_lang}} to {{target_lang}}, and then give constructive criticism and helpful recommendations to improve the translation.

        <SOURCE_TEXT>
        {{source_text}}
        </SOURCE_TEXT>

        <TRANSLATION>
        {{translated_text}}
        </TRANSLATION>
        
        Provide assessment in JSON format with overall_status and dimensions (accuracy, fluency, style, terminology).
        """
    
    # Fill in the template
    prompt = prompt_template.replace('{{source_lang}}', source_lang)
    prompt = prompt.replace('{{target_lang}}', target_lang)
    prompt = prompt.replace('{{source_text}}', source_text)
    prompt = prompt.replace('{{translated_text}}', translated_text)
    
    # Invoke Amazon Nova Pro via Bedrock
    bedrock_runtime = boto3.client('bedrock-runtime')
    
    # Define your system prompt(s).
    system_list = [
        {"text": f"You are an expert in language translation from {source_lang} to {target_lang} quality assessment."}
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
            modelId=model_id,
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
