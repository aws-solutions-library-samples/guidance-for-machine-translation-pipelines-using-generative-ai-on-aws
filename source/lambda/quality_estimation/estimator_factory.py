import os
import logging
from async_endpoint_estimator import AsyncEndpointEstimator
from marketplace_endpoint_estimator import MarketplaceEndpointEstimator

logger = logging.getLogger()

def get_estimator():
    """
    Factory method to get the appropriate quality estimator based on environment variables
    
    Returns:
        QualityEstimatorBase: An instance of the appropriate quality estimator
    """
    mode = os.environ.get('QUALITY_ESTIMATION_MODE', 'OPEN_SOURCE_SELF_HOSTED')
    
    if mode.upper() == 'MARKETPLACE_SELF_HOSTED':
        logger.info("Using Marketplace endpoint estimator")
        return MarketplaceEndpointEstimator()
    else:
        logger.info("Using async endpoint estimator")
        return AsyncEndpointEstimator()