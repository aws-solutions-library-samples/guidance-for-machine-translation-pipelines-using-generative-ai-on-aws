import json
import boto3
import time
import os
from botocore.exceptions import ClientError

# Initialize the Bedrock Runtime client
bedrock_runtime = boto3.client('bedrock-runtime')
s3 = boto3.resource('s3')
secretsmanager = boto3.client('secretsmanager')

# Get model_id from workflow secret
def get_model_id():
    secret_arn = os.getenv('WORKFLOW_SECRET_ARN')
    if not secret_arn:
        return 'us.amazon.nova-pro-v1:0'  # fallback
    
    try:
        response = secretsmanager.get_secret_value(SecretId=secret_arn)
        secret_data = json.loads(response['SecretString'])
        return secret_data.get('bedrock_model_id', 'us.amazon.nova-pro-v1:0')
    except Exception as e:
        print(f"Error retrieving model_id from secret: {e}")
        return 'us.amazon.nova-pro-v1:0'  # fallback

model_id = get_model_id()

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
    
    print(f"Record: {record}")
    try:
        
        # Invoke the model
        response = bedrock_runtime.converse(
            modelId=model_id,
            **record['modelInput']
        )
        
        # Add the model output to the record
        model_output = response["output"]["message"]["content"][0]["text"]
        return {"status": "SUCCESS", "text": model_output}
    
    except Exception as e:
        print(f"Error processing record {record['recordId']}: {str(e)}")
        # Add the record with error information
        return {"status": "ERROR", "text": f"Error: {str(e)}"}
