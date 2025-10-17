import json
import logging
import boto3
import uuid
import os
import time
# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_runtime = boto3.client(service_name="bedrock-runtime")
secrets_client = boto3.client('secretsmanager')

# Get database configuration from Secrets Manager
def get_database_config():
    return {
        'secret_arn': os.environ['DATABASE_SECRET_ARN'],
        'cluster_arn': os.environ['CLUSTER_ARN'],
        'database_name': os.environ['DATABASE_NAME']
    }

db_config = get_database_config()

def lambda_handler(event, context):
    """
    Lambda function that generates a translation prompt for Amazon Bedrock's model.
    
    Parameters:
    - event (dict): Contains the input items following the schema below:
        - source_text (str): The text to be translated
        - source_lang (str): The source language code
        - target_lang (str): The target language code
    - context (LambdaContext): Lambda runtime information
    
    Returns:
    - dict: A JSON object containing Bedrock batch inference JSON
    """
    try:
        print(event)
        prompts = []
        for item_element in event['Items']:
            item = item_element['item']

            # Extract input parameters
            source_text = item.get('source_text')

            if 'source_lang' in item:
                source_lang = item['source_lang']
            else:
                source_lang = os.environ['DEFAULT_SOURCE_LANG']

            if 'target_lang' in item:
                target_lang = item['target_lang']
            else:
                target_lang = os.environ['DEFAULT_TARGET_LANG']

            if 'segment_id' in item:
                unique_id = item['segment_id']
            else:
                unique_id = uuid.uuid4().hex

            # Validate input parameters
            if not all([source_text, source_lang, target_lang]):
                logger.error("Missing required parameters. Skipping item")
                #return {
                #    'statusCode': 400,
                #    'body': json.dumps({
                #       'error': 'Missing required parameters. Please provide source_text, source_lang, and target_lang.'
                #    })
                #}
                continue
            
            # Generate translation prompt for Nova Pro
            body = generate_request_body(source_text, source_lang, target_lang)
            logger.info(f"Generated request body: {json.dumps(body, indent=2)}")
            # Prepare response
            prompt = {
                'recordId': unique_id,
                'modelInput': body,
            }
            #prompts = prompts + json.dumps(prompt) + "\n"
            prompts.append(prompt)
        #Turn response into JSONL format
        #return {"Payload": prompts}
        return prompts
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error processing request: {str(e)}'
            })
        }

def generate_translation_prompt(source_text, source_lang, target_lang):
    """
    Generate a translation prompt for Amazon Bedrock's models.
    
    Parameters:
    - source_text (str): The text to be translated
    - source_lang (str): The source language code
    - target_lang (str): The target language code
    
    Returns:
    - str: The generated translation prompt
    """
    # Create a prompt that instructs the model to translate the text
    system = f"""You are a professional translator with expertise in {source_lang} and {target_lang}."""

    terminology = None
    translation_memory = None

    if 'ENABLE_TRANSLATION_MEMORY' in os.environ and os.environ['ENABLE_TRANSLATION_MEMORY'] == 'true':
        logger.info(f"Translation memory enabled - fetching customization for: {source_text[:50]}...")
        terminology, translation_memory = get_translation_customization(source_text, source_lang, target_lang)
        logger.info(f"Retrieved translation memory: {translation_memory}")
        logger.info(f"Retrieved terminology: {terminology}")
    else:
        logger.info("Translation memory disabled or not configured")

    # Load prompt template
    try:
        logger.info("Loading prompt template from prompt_template.txt...")
        with open('prompt_template.txt', 'r') as file: # nosemgrep
            user_template = file.read()
    except Exception as e:
        logger.error(f"Error loading prompt template: {str(e)}")
        raise
    
    # Fill in the template
    user = user_template.replace('{{source_lang}}', source_lang)
    user = user.replace('{{target_lang}}', target_lang)
    user = user.replace('{{source_text}}', source_text)
    user = user.replace('{{translation_memory}}', str(translation_memory))
    user = user.replace('{{terminology}}', str(terminology))
    
    return system, user

def generate_request_body(source_text, source_lang, target_lang):
    
    # Define one or more messages using the "user" and "assistant" roles.
    system_text, user_text = generate_translation_prompt(source_text, source_lang, target_lang)
    message_list = [{"role": "user", "content": [{"text": user_text}]}]
    # system_list = [system_text]
    system_list = [{"text":system_text}]
    # Configure the inference parameters.
    inf_params = {"maxTokens": 500, "topP": 0.9, "temperature": 0.5}

    request_body = {
        # "schemaVersion": "messages-v1",
        "messages": message_list,
        "system": system_list,
        "inferenceConfig": inf_params,
    }
    return request_body

def get_translation_customization(source_text, source_lang, target_lang):
    """Lookup similar text segments from the translation_memory table via similarity search. It uses the RDS Data API to run the query"""
    logger.info(f"Starting translation customization lookup for: {source_text[:50]}...")
    similarities = call_rds_data_api(source_lang, target_lang, source_text)
    logger.info(f"RDS query returned {len(similarities)} results")
    translation_memory = ""
    for record in similarities:
        translation_memory = translation_memory+ f"{source_lang}:{record['source_text']} ==> {target_lang}:{record['target_text']}\n"
    logger.info(f"Final translation memory: {translation_memory}")
    return None, translation_memory

def generate_embeddings(query):
    
    payLoad = json.dumps({'inputText': query })
    response = bedrock_runtime.invoke_model(
        body=payLoad, 
        modelId='amazon.titan-embed-text-v2:0',
        accept="application/json", 
        contentType="application/json" )
    response_body = json.loads(response.get("body").read())
    return(response_body.get("embedding"))

def call_rds_data_api(source_lang, target_lang, source_text):

    def extract_records(response):
        """
        Extracts records from the AWS response and returns them in a more usable format.
        
        Args:
            response (dict): The AWS response containing the records
            
        Returns:
            list: A list of dictionaries containing id, source_text, and target_text
        """
        formatted_records = []
        
        for record in response['records']:
            # Each record is a list of 3 items: [id, source_text, target_text]
            record_dict = {
                'id': record[0]['longValue'],
                'source_text': record[1]['stringValue'],
                'target_text': record[2]['stringValue']
            }
            formatted_records.append(record_dict)
        
        return formatted_records

    logger.info("Starting RDS Data API call...")
    rds_data = boto3.client('rds-data')
    logger.info("Generating embeddings for source text...")
    embedding_str = generate_embeddings(source_text)
    logger.info(f"Generated embedding of length: {len(embedding_str) if embedding_str else 0}")
    
    sql_text = f"SELECT unique_id, source_text, target_text FROM translation_memory ORDER BY source_text_embedding <=> CAST('{embedding_str}' AS VECTOR) limit 1;" # nosec B608
    logger.info(f"Executing SQL: {sql_text[:100]}...")

    
    max_retries = 5
    base_delay = 1  # Initial delay in seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"RDS attempt {attempt + 1}/{max_retries}")
            response = rds_data.execute_statement(
                resourceArn = db_config['cluster_arn'], 
                secretArn = db_config['secret_arn'], 
                database = db_config['database_name'],
                sql = sql_text
            )
            logger.info(f"RDS response received: {len(response.get('records', []))} records")
            records = extract_records(response)
            logger.info(f"Extracted {len(records)} formatted records")
            return records
            
        except rds_data.exceptions.BadRequestException as e:
            logger.exception(f"RDS BadRequestException on attempt {attempt + 1}: {str(e)}")
            if "Communications link failure" in str(e) and attempt < max_retries - 1:
                delay = (2 ** attempt) * base_delay  # Exponential backoff
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            raise
        except Exception as e:
            logger.error(f"Unexpected RDS error on attempt {attempt + 1}: {str(e)}")
            raise
            
    logger.warning("All RDS retry attempts failed, returning empty list")
    return []  # Return empty list if all retries failed
