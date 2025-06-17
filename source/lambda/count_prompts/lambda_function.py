import json
import boto3

def lambda_handler(event, context):
    # print event
    print(repr(event))
    """
    {
        'MapRunArn': 'arn:aws:states:us-east-2:986528949439:mapRun:BatchMachineTranslationStateMachine/ShippingFileAnalysis:181a97e5-8237-4188-86fc-0876e0d0d161', 
        'ResultWriterDetails': {
            'Bucket': 'machine-translation-output-data', 
            'Key': 'prompts/181a97e5-8237-4188-86fc-0876e0d0d161/manifest.json'
            }
    }

    """
    #copy event JSON object into input_payload
    input_payload = event.copy()
    out_details = event['ResultWriterDetails']

    #load Manifest object from S3
    s3 = boto3.resource('s3')
    obj = s3.Object(out_details['Bucket'], out_details['Key'])
    manifest = json.loads(obj.get()['Body'].read().decode('utf-8'))

    prompt_bucket = manifest['DestinationBucket']
    map_run_arn = event['MapRunArn']
    execution_id = map_run_arn.split(':')[-1]

    prompt_prefix_and_key = manifest['ResultFiles']['SUCCEEDED'][0]['Key']
    s3_input_file = f"s3://{prompt_bucket}/{prompt_prefix_and_key}"

    #Load input file
    s3 = boto3.resource('s3')
    obj = s3.Object(prompt_bucket, prompt_prefix_and_key)
    input_file = obj.get()['Body'].read().decode('utf-8')
    

    #Input file is a JSONL file. Let's count how many records there are.
    input_file_lines = input_file.strip().split('\n')
    input_payload['input_file'] = prompt_prefix_and_key
    input_payload['input_bucket'] = prompt_bucket
    input_payload['record_count'] = len(input_file_lines)
    return input_payload
