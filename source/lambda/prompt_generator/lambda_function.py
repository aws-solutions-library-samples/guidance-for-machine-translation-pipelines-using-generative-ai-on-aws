import json
import logging
import boto3
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_runtime = boto3.client(service_name="bedrock-runtime")

secret_arn= "arn:aws:secretsmanager:us-east-2:986528949439:secret:AuroraCredentials20EDD625-lm2rx5dUXdeO-OOCrM5"
cluster_arn = "arn:aws:rds:us-east-2:986528949439:cluster:databasestack-translationmemoryauroraclusterfd1dc6-axcfoistdywf"
database_name = 'MTEngineTranslationMemoryDb'

def lambda_handler(event, context):
    """
    Lambda function that generates a translation prompt for Amazon Bedrock's Anthropic Claude (Nova Pro) model.
    
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
            source_lang = item.get('source_lang')
            target_lang = item.get('target_lang')
            
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
            id, body = generate_request_body(source_text, source_lang, target_lang)
            # Prepare response
            prompt = {
                'recordId': id,
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
    Generate a translation prompt for Amazon Bedrock's Nova Pro model.
    
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

    #terminology, translation_memory = get_translation_customization(source_text, source_lang, target_lang)

    user = f"""
    Task: 
    Translate the provided source text from {source_lang} to {target_lang}.
    
    Source text (in {source_lang}): 
    {source_text}

    Context information:
        Examples:
        {translation_memory}

        Terminology:
        {terminology}

    Model Instructions and Guidelines:
    1. Maintain the original meaning, tone, and nuance
    2. Preserve formatting, including paragraph breaks and bullet points
    3. Keep any proper nouns, technical terms, or brand names as they appear in the original text unless there's a standard translation
    4. ONLY translate the source text. DO NOT Translate the context information
    5. Use the examples provided in Examples section to influence the translation output's tone and vocabulary.
    6. Use the custom terms in the Terminology section as strict translation guidelines.
    7. For ambiguous terms, choose the most appropriate translation based on context
    8. Ensure cultural appropriateness and localization where necessary
    9. Return only the translated text without explanations or notes

    Translation ({target_lang}):
    """
    return system, user

def generate_request_body(source_text, source_lang, target_lang):
    
    # Define one or more messages using the "user" and "assistant" roles.
    system_text, user_text = generate_translation_prompt(source_text, source_lang, target_lang)
    message_list = [{"role": "user", "content": [{"text": user_text}]}]
    system_list = [system_text]

    # Configure the inference parameters.
    inf_params = {"maxTokens": 500, "topP": 0.9, "topK": 20, "temperature": 0.7}

    request_body = {
        "schemaVersion": "messages-v1",
        "messages": message_list,
        "system": system_list,
        "inferenceConfig": inf_params,
    }
    unique_id = uuid.uuid4().hex
    return unique_id, request_body

def get_translation_customization(source_text, source_lang, target_lang):
    """Lookup similar text segments from the translation_memory table via similarity search. It uses the RDS Data API to run the query"""
    similarities = call_rds_data_api(source_lang, target_lang, source_text)
    translation_memory = ""
    for record in similarities:
        translation_memory = translation_memory+ f"{source_lang}:{source_text} ==> {target_lang}:{record['target_text']}\n"
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

    rds_data = boto3.client('rds-data')
    embedding_str = generate_embeddings(source_text)
    sql_text = f"SELECT unique_id, source_text, target_text FROM translation_memory ORDER BY source_text_embedding <=> CAST('{embedding_str}' AS VECTOR) limit 3;" # nosec B608

    
    max_retries = 5
    base_delay = 1  # Initial delay in seconds
    
    for attempt in range(max_retries):
        try:
            response = rds_data.execute_statement(
                resourceArn = cluster_arn, 
                secretArn = secret_arn, 
                database = database_name,
                sql = sql_text
            )
            records = extract_records(response)
            return records
            
        except rds_data.exceptions.BadRequestException as e:
            if "Communications link failure" in str(e) and attempt < max_retries - 1:
                delay = (2 ** attempt) * base_delay  # Exponential backoff
                time.sleep(delay)
                continue
            raise
            
    return []  # Return empty list if all retries failed
