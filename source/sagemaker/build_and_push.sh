#!/bin/bash

# =============================================================================
# Docker Image Build and Push to Amazon ECR Script
# =============================================================================

# -----------------------------------------------------------------------------
# ENVIRONMENT VARIABLES TO BE INITIALIZED:
# -----------------------------------------------------------------------------
# AWS_REGION - The AWS region where the ECR repository will be created
# ECR_REPOSITORY_NAME - Name for the ECR repository
# IMAGE_TAG - Tag for the Docker image (default: latest)
# -----------------------------------------------------------------------------

# Set default values for environment variables
AWS_REGION=${AWS_REGION:-"us-east-1"}
ECR_REPOSITORY_NAME=${ECR_REPOSITORY_NAME:-"machine-translation/quality-estimation-model"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}

# Get AWS account ID
echo "Getting AWS account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ $? -ne 0 ]; then
  echo "Error: Failed to get AWS account ID. Make sure you're authenticated with AWS CLI."
  exit 1
fi
echo "AWS Account ID: $AWS_ACCOUNT_ID"

# Create ECR repository if it doesn't exist
echo "Creating ECR repository $ECR_REPOSITORY_NAME (if it doesn't exist)..."
aws ecr create-repository --repository-name $ECR_REPOSITORY_NAME --region $AWS_REGION || echo "Repository already exists or couldn't be created."

# Authenticate Docker to ECR
echo "Authenticating Docker with ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
if [ $? -ne 0 ]; then
  echo "Error: Failed to authenticate Docker with ECR."
  exit 1
fi

# Check if hub directory exists, create if it doesn't
if [ ! -d "hub" ]; then
  echo "Creating hub directory for Hugging Face model files..."
  mkdir -p hub
fi

# Build Docker image
echo "Building Docker image..."
docker build -t $ECR_REPOSITORY_NAME:$IMAGE_TAG .
if [ $? -ne 0 ]; then
  echo "Error: Docker build failed."
  exit 1
fi

# Tag the image for ECR
echo "Tagging image for ECR..."
docker tag $ECR_REPOSITORY_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG

# Push the image to ECR
echo "Pushing image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG
if [ $? -ne 0 ]; then
  echo "Error: Failed to push image to ECR."
  exit 1
fi

echo "==============================================================================="
echo "SUCCESS: Image successfully built and pushed to ECR"
echo "Repository: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG"
echo "==============================================================================="
