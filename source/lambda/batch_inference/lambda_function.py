import json
import boto3

bedrock = boto3.client(service_name="bedrock")

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
    out_details = event['ResultWriterDetails']

    #load Manifest object from S3
    s3 = boto3.resource('s3')
    obj = s3.Object(out_details['Bucket'], out_details['Key'])
    manifest = json.loads(obj.get()['Body'].read().decode('utf-8'))

    prompt_bucket = manifest['DestinationBucket']
    map_run_arn = event['MapRunArn']
    execution_id = map_run_arn.split(':')[-1]

    prompt_prefix_and_key = manifest['ResultFiles']['SUCCEEDED'][0]['Key']
    
    #Start Bedrock batch inference job
    
    inputDataConfig=({
        "s3InputDataConfig": {
            "s3Uri": f"s3://{prompt_bucket}/{prompt_prefix_and_key}"
        }
    })

    outputDataConfig=({
        "s3OutputDataConfig": {
            "s3Uri": f"s3://{prompt_bucket}/inferences/{execution_id}/"
        }
    })

    response=bedrock.create_model_invocation_job(
        roleArn="arn:aws:iam::986528949439:role/service-role/MachineTranslationBatch",
        modelId="us.amazon.nova-pro-v1:0",
        jobName=f"MachineTranslationJob-{execution_id}",
        inputDataConfig=inputDataConfig,
        outputDataConfig=outputDataConfig
    )

    jobArn = response.get('jobArn')
    
    return {
        'statusCode': 200,
        'body': {'batchInferenceJobArn': jobArn}
    }
