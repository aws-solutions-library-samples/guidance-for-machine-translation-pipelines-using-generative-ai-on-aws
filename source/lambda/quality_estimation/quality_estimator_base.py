import logging
import json
from abc import ABC, abstractmethod

logger = logging.getLogger()

class QualityEstimatorBase(ABC):
    """Base class for quality estimation implementations"""
    
    @abstractmethod
    def invoke_endpoint(self, input_bucket, input_file, task_token):
        """
        Invokes the quality estimation endpoint
        
        Args:
            input_bucket (str): S3 bucket containing input data
            input_file (str): S3 key for input file
            task_token (str): Step Functions task token
            
        Returns:
            dict: Response from the endpoint invocation
        """
        pass