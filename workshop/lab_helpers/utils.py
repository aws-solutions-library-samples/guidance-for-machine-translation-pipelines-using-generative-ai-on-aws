"""
Utility functions for the translation workshop.
"""

import boto3
import json
from typing import Dict, Optional


def get_aws_region() -> str:
    """Get current AWS region from session."""
    session = boto3.Session()
    return session.region_name or 'us-east-1'


def get_account_id() -> str:
    """Get current AWS account ID."""
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']


def check_bedrock_model_access(model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0") -> bool:
    """
    Check if the specified Bedrock model is accessible.
    
    Args:
        model_id: Bedrock model identifier
        
    Returns:
        True if model is accessible, False otherwise
    """
    try:
        bedrock = boto3.client('bedrock')
        response = bedrock.list_foundation_models()
        
        available_models = [model['modelId'] for model in response.get('modelSummaries', [])]
        
        if model_id in available_models:
            print(f"✅ Model {model_id} is available")
            return True
        else:
            print(f"❌ Model {model_id} is not available")
            print(f"Available models: {available_models[:5]}...")  # Show first 5
            return False
    except Exception as e:
        print(f"⚠️ Error checking model access: {str(e)}")
        return False


def create_s3_bucket_for_kb(bucket_name: Optional[str] = None) -> str:
    """
    Create S3 bucket for Knowledge Base data source.
    
    Args:
        bucket_name: Optional bucket name, will generate if not provided
        
    Returns:
        Created bucket name
    """
    if not bucket_name:
        account_id = get_account_id()
        region = get_aws_region()
        bucket_name = f"translation-kb-{account_id}-{region}"
    
    s3 = boto3.client('s3')
    region = get_aws_region()
    
    try:
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"✅ Created S3 bucket: {bucket_name}")
        return bucket_name
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"✅ S3 bucket already exists: {bucket_name}")
        return bucket_name
    except Exception as e:
        print(f"❌ Error creating S3 bucket: {str(e)}")
        raise


def upload_terminology_to_s3(bucket_name: str, file_path: str, s3_key: str = "terminology/aws_terminology.csv") -> str:
    """
    Upload terminology file to S3 for Knowledge Base.
    
    Args:
        bucket_name: S3 bucket name
        file_path: Local path to terminology file
        s3_key: S3 object key
        
    Returns:
        S3 URI of uploaded file
    """
    s3 = boto3.client('s3')
    
    try:
        s3.upload_file(file_path, bucket_name, s3_key)
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        print(f"✅ Uploaded terminology to: {s3_uri}")
        return s3_uri
    except Exception as e:
        print(f"❌ Error uploading to S3: {str(e)}")
        raise


def wait_for_kb_ingestion(kb_id: str, data_source_id: str, max_wait_seconds: int = 300) -> bool:
    """
    Wait for Knowledge Base data source ingestion to complete.
    
    Args:
        kb_id: Knowledge Base ID
        data_source_id: Data source ID
        max_wait_seconds: Maximum time to wait
        
    Returns:
        True if ingestion completed successfully
    """
    import time
    
    bedrock_agent = boto3.client('bedrock-agent')
    start_time = time.time()
    
    print("⏳ Waiting for Knowledge Base ingestion...")
    
    while time.time() - start_time < max_wait_seconds:
        try:
            response = bedrock_agent.get_data_source(
                knowledgeBaseId=kb_id,
                dataSourceId=data_source_id
            )
            
            status = response['dataSource']['status']
            print(f"   Status: {status}")
            
            if status == 'AVAILABLE':
                print("✅ Knowledge Base ingestion complete!")
                return True
            elif status == 'FAILED':
                print("❌ Knowledge Base ingestion failed")
                return False
                
            time.sleep(10)
        except Exception as e:
            print(f"⚠️ Error checking ingestion status: {str(e)}")
            time.sleep(10)
    
    print("⏰ Timeout waiting for ingestion")
    return False


def query_knowledge_base(kb_id: str, query: str, max_results: int = 5) -> Dict:
    """
    Query Bedrock Knowledge Base.
    
    Args:
        kb_id: Knowledge Base ID
        query: Search query
        max_results: Maximum number of results
        
    Returns:
        Query results
    """
    bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
    
    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results
                }
            }
        )
        
        return response
    except Exception as e:
        print(f"❌ Error querying Knowledge Base: {str(e)}")
        raise


def print_section_header(title: str):
    """Print a formatted section header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")


def print_success(message: str):
    """Print a success message."""
    print(f"✅ {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"❌ {message}")


def print_info(message: str):
    """Print an info message."""
    print(f"ℹ️  {message}")
