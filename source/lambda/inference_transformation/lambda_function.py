import json
import boto3
import os


def convert_json_array_to_jsonl(data):
    json_string=""
    for item in data:
        json_dumps = json.dumps(item)
        json_string = json_string + '\n' + json_dumps
    return json_string.strip()

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

    #input_file_lines = input_file.strip().split('\n')
    input_file_lines = json.loads(input_file)
    results = []
    for inference in input_file_lines:
        #inference = json.loads(inference)
        print(inference)
        #model_input = line['Input']
        model_output = inference['modelOutput']
        output_text = {'results': [{'outputText': model_output, 'completionReason': inference['inferenceStatus']}]}
        input_text = {'inputText':inference['modelInput']['messages'][0]['content'][0]['text']}
        record_id = inference['recordId']
        results.append({'modelInput': input_text, 'modelOutput': output_text, 'recordId': record_id})

    #remove extension from prompt_prefix_and_key
    file_name_without_extension = os.path.splitext(prompt_prefix_and_key)[0]
    result_file_key = file_name_without_extension + ".final.jsonl"

    #Store results in S3
    print("Storing data into:"+ result_file_key)
    obj = s3.Object(prompt_bucket, result_file_key)
    jsonl_data = convert_json_array_to_jsonl(results)
    obj.put(Body=jsonl_data)
    #obj.put(Body=json.dumps(results))

    output_payload = {}
    output_payload['resultFile'] = result_file_key
    output_payload['resultBucket'] = prompt_bucket
    output_payload['recordCount'] = len(results)
    return output_payload
