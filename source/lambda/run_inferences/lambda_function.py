import json
import boto3
import time
import os
from botocore.exceptions import ClientError

# Initialize the Bedrock Runtime client
bedrock_runtime = boto3.client('bedrock-runtime')
s3 = boto3.resource('s3')

model_id = os.getenv('MODEL_ID', 'us.amazon.nova-pro-v1:0')

def get_required_env_var(var_name):
    """Retrieve an environment variable that is required for the application."""
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Required environment variable '{var_name}' is not set")
    return value

def lambda_handler(event, context):
    """
    Sample event payload
    {
        "recordId": "eaf2e019697c4e2185bc5151360e7ea0",
        "modelInput": {
            "schemaVersion": "messages-v1",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": "\n    Task: Translate the following text from french to german.\n\n    Context information:\n        Examples:\n        None\n\n        Terminology:\n        None\n    Model Instructions and Guidelines:\n    1. Maintain the original meaning, tone, and nuance\n    2. Preserve formatting, including paragraph breaks and bullet points\n    3. Keep any proper nouns, technical terms, or brand names as they appear in the original text unless there's a standard translation\n    4. Use the examples provided in Examples section to influence the translation output's tone and vocabulary.\n    5. Use the custom terms in the Terminology section as strict translation guidelines.\n    6. For ambiguous terms, choose the most appropriate translation based on context\n    7. Ensure cultural appropriateness and localization where necessary\n    8. Return only the translated text without explanations or notes\n\n    Text to translate (french):\n    Reprise de la session\n\n    Translation (german):\n    "
                        }
                    ]
                }
            ],
            "system": [
                "You are a professional translator with expertise in french and german."
            ],
            "inferenceConfig": {
                "maxTokens": 500,
                "topP": 0.9,
                "topK": 20,
                "temperature": 0.7
            }
        }
    }
    """
    # Copy event object
    #record = event.copy()
    outputs = []
    for item_element in event['Items']:
        item = item_element['item']
        output = process_record(item)
        record = item.copy()
        record['modelOutput'] = output['text']
        record['inferenceStatus'] = output['status']
        outputs.append(record)
    return outputs

def process_record(record):
    
    # Read and process the input file
    processed_records = []
    try:
        # Define your system prompt(s).
        system_list = [
            {"text": record['modelInput']['system'][0]}
        ]

        # Define one or more messages using the "user" and "assistant" roles.
        message_list = record['modelInput']['messages']

        # Configure the inference parameters.
        inf_params = {
            "max_new_tokens": record['modelInput']['inferenceConfig']['maxTokens'], 
            "top_p": record['modelInput']['inferenceConfig']['topP'], 
            "top_k": record['modelInput']['inferenceConfig']['topK'], 
            "temperature": record['modelInput']['inferenceConfig']['temperature']
        }

        request_body = {
            "messages": message_list,
            "system": system_list,
            "inferenceConfig": inf_params,
        }
        
        # Invoke the model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
    
        # Add the model output to the record
        model_output = response_body["output"]["message"]["content"][0]["text"]
        return {"status": "SUCCESS", "text": model_output}
    
    except Exception as e:
        print(f"Error processing record {record['recordId']}: {str(e)}")
        # Add the record with error information
        return {"status": "ERROR", "text": f"Error: {str(e)}"}
