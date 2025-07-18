
import logging
import json
import boto3
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        bucket = event.get('input_bucket')
        input_file = event.get('input_key')
        if bucket in input_file:
            input_file = input_file.split(f"{bucket}/")[1]
            logger.info(f"input_file: {input_file}")
        
        # Process batch inference results
        assessment_results = process_batch_assessment_results(bucket, input_file)
        
        # Write results to JSONL file
        output_file = write_assessment_results(bucket, input_file, assessment_results)
        
        return {
            'statusCode': 200,
            'input_bucket': bucket,
            'input_file': output_file,
            'totalProcessed': len(assessment_results)
        }
        
    except Exception as e:
        logger.error(f"Error processing batch assessment results: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'error': str(e)
        }

def process_batch_assessment_results(bucket, input_file):
    """Process batch inference JSONL results and extract assessments"""
    try:
        # Download the batch output file
        response = s3.get_object(Bucket=bucket, Key=input_file)
        batch_content = response['Body'].read().decode('utf-8')
        
        assessment_results = []
        
        # Process each line in the JSONL file
        for line in batch_content.strip().split('\n'):
            if line.strip():
                record = json.loads(line)
                assessment_result = extract_assessment_from_record(record)
                if assessment_result:
                    assessment_results.append(assessment_result)
        
        return assessment_results
        
    except Exception as e:
        logger.error(f"Error processing batch assessment results: {str(e)}", exc_info=True)
        raise

def write_assessment_results(bucket, input_file, assessment_results):
    """Write assessment results to JSONL file"""
    try:
        # Create output file name with _final suffix
        file_parts = input_file.split('.')
        output_file = f"{file_parts[0]}_final.jsonl"
        
        # Create JSONL content
        jsonl_content = '\n'.join([json.dumps(result) for result in assessment_results])
        
        # Upload to S3
        s3.put_object(
            Bucket=bucket,
            Key=output_file,
            Body=jsonl_content,
            ContentType='application/jsonl'
        )
        
        logger.info(f"Written {len(assessment_results)} results to s3://{bucket}/{output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error writing assessment results: {str(e)}", exc_info=True)
        raise

def extract_assessment_from_record(record):
    """Extract assessment data from a batch inference record"""
    try:
        model_input = record.get('modelInput', {})
        model_output = record.get('modelOutput', {})
        record_id = record.get('recordId')
        
        # Extract languages and texts from modelInput
        messages = model_input.get('messages', [])
        if not messages:
            return None
            
        content = messages[0].get('content', [])
        if not content:
            return None
            
        prompt_text = content[0].get('text', '')
        
        # Parse source and target languages from system prompt
        system_prompts = model_input.get('system', [])
        system_text = system_prompts[0].get('text', '') if system_prompts else ''
        
        source_lang_match = re.search(r'from\s+(\w+)\s+to', system_text)
        target_lang_match = re.search(r'to\s+(\w+)', system_text)
        
        source_lang = source_lang_match.group(1) if source_lang_match else "unknown"
        target_lang = target_lang_match.group(1) if target_lang_match else "unknown"
        
        # Extract source text
        source_text_match = re.search(r'<SOURCE_TEXT>\n(.*?)\n</SOURCE_TEXT>', prompt_text, re.DOTALL)
        source_text = source_text_match.group(1).strip() if source_text_match else ""
        
        # Extract translated text
        translation_match = re.search(r'<TRANSLATION>\n(.*?)\n</TRANSLATION>', prompt_text, re.DOTALL)
        translated_text = translation_match.group(1).strip() if translation_match else ""

        # Parse assessment from model output
        output_message = model_output.get('output', {}).get('message', {})
        output_content = output_message.get('content', [])
        
        if not output_content:
            return None
            
        assessment_text = output_content[0].get('text', '')
        
        # Parse JSON assessment
        assessment = parse_assessment_json(assessment_text)
        
        return {
            'source_language': source_lang,
            'target_language': target_lang,
            'source_text': source_text,
            'translated_text': translated_text,
            'assessment': assessment,
            'recordId': record_id
        }
        
    except Exception as e:
        logger.error(f"Error extracting assessment from record {record.get('recordId', 'unknown')}: {str(e)}")
        return None

def parse_assessment_json(assessment_text):
    """Parse assessment JSON from model output text"""
    try:
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', assessment_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        else:
            # Fallback assessment structure
            return {
                "overall_status": "NEEDS_ATTENTION",
                "dimensions": {
                    "accuracy": {
                        "status": "NEEDS_ATTENTION",
                        "comment": "Failed to parse assessment response"
                    },
                    "fluency": {"status": "MEETS_REQUIREMENTS", "comment": ""},
                    "style": {"status": "MEETS_REQUIREMENTS", "comment": ""},
                    "terminology": {"status": "MEETS_REQUIREMENTS", "comment": ""}
                }
            }
    except Exception as e:
        logger.error(f"Error parsing assessment JSON: {str(e)}")
        return {
            "overall_status": "NEEDS_ATTENTION",
            "dimensions": {
                "accuracy": {
                    "status": "NEEDS_ATTENTION",
                    "comment": f"Error parsing assessment: {str(e)}"
                },
                "fluency": {"status": "MEETS_REQUIREMENTS", "comment": ""},
                "style": {"status": "MEETS_REQUIREMENTS", "comment": ""},
                "terminology": {"status": "MEETS_REQUIREMENTS", "comment": ""}
            }
        }