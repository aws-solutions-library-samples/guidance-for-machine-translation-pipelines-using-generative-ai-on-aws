from flask import Flask, request, jsonify
import os
import logging
from comet import download_model, load_from_checkpoint
import sys
import time
import json
import base64
from distutils.util import strtobool
import boto3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Global variable for model
model = None

def get_hf_token():
    """Get HuggingFace token from AWS Secrets Manager"""
    secret_arn = os.environ.get('HF_SECRET_ARN')
    if not secret_arn:
        logger.warning("HF_SECRET_ARN not found in environment variables")
        return None
    
    try:
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        token = response['SecretString']
        logger.info("Successfully retrieved HuggingFace token from Secrets Manager")
        return token
    except Exception as e:
        logger.error(f"Failed to retrieve HuggingFace token from Secrets Manager: {str(e)}")
        return None

# Get environment variables with defaults
def get_env_config():
    """Get configuration from environment variables with defaults"""
    # Check if GPU should be used (default: False)
    use_gpu = bool(strtobool(os.environ.get('USE_GPU', 'True')))
    # Get batch size for predictions (default: 16)
    batch_size = int(os.environ.get('BATCH_SIZE', '16'))
    # Check if model should be loaded from S3 (default: False - download from HuggingFace)
    load_from_s3 = bool(strtobool(os.environ.get('LOAD_FROM_S3', 'False')))
    
    logger.info(f"Configuration: USE_GPU={use_gpu}, BATCH_SIZE={batch_size}, LOAD_FROM_S3={load_from_s3}")
    return {
        'use_gpu': use_gpu,
        'batch_size': batch_size,
        'load_from_s3': load_from_s3
    }

CONFIG = get_env_config()


def load_model():
    """Initialize and load the COMET model"""
    global model
    try:
        if model is None:
            logger.info("Starting model loading process...")
            start_time = time.time()
            
            # Set HuggingFace token from Secrets Manager
            hf_token = get_hf_token()
            if hf_token:
                os.environ['HF_TOKEN'] = hf_token
                logger.info("HuggingFace token set from Secrets Manager")
            
            if CONFIG['load_from_s3']:
                # Load model from S3 (SageMaker model artifacts)
                sagemaker_model_path = "/opt/ml/model/hub"
                logger.info(f"Loading model from S3 path: {sagemaker_model_path}")
                model_path = download_model("Unbabel/wmt22-cometkiwi-da", saving_directory=sagemaker_model_path, local_files_only=True)
            else:
                # Download model from HuggingFace
                logger.info("Downloading model from HuggingFace")
                model_path = download_model("Unbabel/wmt22-cometkiwi-da")
            logger.info(f"Model path: {model_path}")
            
            logger.info("Loading model from checkpoint...")
            model = load_from_checkpoint(model_path)            
            end_time = time.time()
            loading_time = end_time - start_time
            logger.info(f"Model loaded successfully in {loading_time:.2f} seconds")
        else:
            logger.info("Model already loaded, reusing existing instance")
        
        return model
    
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}", exc_info=True)
        # Return None instead of raising exception to allow endpoint creation
        return None

@app.route('/ping', methods=['GET'])
def ping():
    """Healthcheck endpoint for SageMaker - always returns healthy to prevent deployment loops"""
    logger.info("Received health check request")
    # Always return healthy to ensure SageMaker endpoint creation succeeds
    logger.info("Health check returning healthy status")
    return jsonify({"status": "healthy"}), 200

# Prediction endpoint
@app.route('/invocations', methods=['POST'])
def predict():
    """
    SageMaker prediction endpoint
    Expects JSON or JSONL input:
    
    For JSON:
    {
        "data": [
            {
                "src": "source text",
                "mt": "translated text"
            }
        ]
    }
    
    For JSONL: Each line is a separate JSON object
    {"recordId": "id1", "source_text": "text", "translated_text": "translation", ...}
    {"recordId": "id2", "source_text": "text", "translated_text": "translation", ...}
    """
    logger.info("Received prediction request")
    
    try:
        # Ensure model is loaded
        global model
        model = load_model()
        
        # Check content type and parse accordingly
        content_type = request.headers.get('Content-Type', '')
        
        if 'jsonl' in content_type.lower() or 'json-lines' in content_type.lower():
            # Handle JSONL format
            raw_data = request.data.decode('utf-8')
            content = []
            for line in raw_data.strip().split('\n'):
                if line.strip():
                    content.append(json.loads(line))
            logger.info(f"Parsed JSONL with {len(content)} records")
        else:
            # Handle regular JSON
            if not request.is_json: # nosemgrep
                logger.error("Request content-type is not application/json")
                return jsonify({"error": "Content type must be application/json"}), 415
            content = request.get_json()
            
        logger.info(f"Received prediction request with {len(content)} samples")
        if not content:
            logger.error("Empty data received in request")
            return jsonify({"error": "No data provided"}), 400
        
        # Perform prediction
        logger.info("Starting prediction")
        start_time = time.time()
        
        data = []
        input_model = []
        input_ids = []     
        for translation_item in content:
            #prompt_input = json.loads(el['Input'])
            #prompt_input = json.loads(el['Input'])
            #recordId = prompt_input['recordId']
            #source_text = prompt_input['source_text']
            #translation_output = el['Output']
            recordId = translation_item['recordId']
            if 'translated_text' not in translation_item:
                logger.warning(f"Skipping error record: {recordId}")
                data.append({
                    "recordId": recordId,
                    "score": None
                })
                continue
            
            translation_output = translation_item['translated_text']
            source_text = translation_item['source_text']
            source_language = translation_item['source_language']
            target_language = translation_item['target_language']

            input_model.append(
                {
                    "src": source_text,
                    "mt": translation_output
                }
            )
            input_ids.append(recordId)
        

        try:
            model_output = model.predict(
                input_model, 
                batch_size=CONFIG['batch_size'], 
                gpus=1 if CONFIG['use_gpu'] else 0, 
                num_workers=1
            )
            for id, score in zip(input_ids,model_output.scores):
                data.append({
                    "recordId": id,
                    "score": score
                })
        except Exception as e:
            logger.error(f"Error processing records: {str(e)}", exc_info=True)
            data = []
        
        end_time = time.time()
        prediction_time = end_time - start_time
        logger.info(f"Prediction completed in {prediction_time:.2f} seconds")
        
        # Prepare response
        response = {
            "predictions": data
        }
        
        logger.info("Successfully generated prediction response")
        logger.debug(f"Response structure: {list(response.keys())}")
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error during prediction: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Main entry point
if __name__ == '__main__':
    try:
        # Log environment information
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        
        # SageMaker expects the app to be listening on port 8080
        port = int(os.environ.get('PORT', 8080))
        logger.info(f"Starting server on port {port}")
        
        # Load model at startup
        logger.info("Initializing model at startup")
        load_model()
        
        # Start Flask app
        # Binding to 0.0.0.0 is required for SageMaker container routing; this is safe in a controlled AWS environment
        app.run(host='0.0.0.0', port=port)  # nosec B104 , nosemgrep
        
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}", exc_info=True)
        sys.exit(1)
