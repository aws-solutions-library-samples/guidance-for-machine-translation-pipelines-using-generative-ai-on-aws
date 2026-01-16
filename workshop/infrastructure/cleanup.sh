#!/bin/bash

# Cleanup script for Translation Agent Workshop resources
# This script deletes all AWS resources created during the workshop

set -e

echo "=========================================="
echo "Translation Agent Workshop - Cleanup"
echo "=========================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Prompt for confirmation
read -p "⚠️  This will delete ALL workshop resources. Are you sure? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# Delete CloudFormation stack
echo "1. Deleting CloudFormation stack..."
if aws cloudformation describe-stacks --stack-name chunking-lambda-stack &> /dev/null; then
    aws cloudformation delete-stack --stack-name chunking-lambda-stack
    echo "   Waiting for stack deletion..."
    aws cloudformation wait stack-delete-complete --stack-name chunking-lambda-stack 2>/dev/null || true
    echo "   ✅ CloudFormation stack deleted"
else
    echo "   ℹ️  Stack not found, skipping"
fi

# Get resource names from notebook variables (if available)
# Otherwise, prompt user or use pattern matching
echo ""
echo "2. Cleaning up Knowledge Base resources..."

# List and delete Knowledge Bases
KB_IDS=$(aws bedrock-agent list-knowledge-bases --query 'knowledgeBaseSummaries[?contains(name, `s3-vectors-kb`)].knowledgeBaseId' --output text 2>/dev/null || echo "")

if [ -n "$KB_IDS" ]; then
    for KB_ID in $KB_IDS; do
        echo "   Deleting Knowledge Base: $KB_ID"
        
        # Delete data sources first
        DS_IDS=$(aws bedrock-agent list-data-sources --knowledge-base-id "$KB_ID" --query 'dataSourceSummaries[].dataSourceId' --output text 2>/dev/null || echo "")
        for DS_ID in $DS_IDS; do
            echo "   - Deleting data source: $DS_ID"
            aws bedrock-agent delete-data-source --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID" 2>/dev/null || true
        done
        
        # Delete the Knowledge Base
        aws bedrock-agent delete-knowledge-base --knowledge-base-id "$KB_ID" 2>/dev/null || true
        echo "   ✅ Knowledge Base deleted: $KB_ID"
    done
else
    echo "   ℹ️  No Knowledge Bases found"
fi

echo ""
echo "3. Cleaning up S3 Vectors resources..."

# Delete S3 Vector indexes and buckets
VECTOR_BUCKETS=$(aws s3vectors list-vector-buckets --query 'vectorBuckets[?contains(vectorBucketName, `s3-vectors-embeddings`)].vectorBucketName' --output text 2>/dev/null || echo "")

if [ -n "$VECTOR_BUCKETS" ]; then
    for BUCKET in $VECTOR_BUCKETS; do
        echo "   Deleting vector bucket: $BUCKET"
        
        # Delete indexes first
        INDEXES=$(aws s3vectors list-indexes --vector-bucket-name "$BUCKET" --query 'indexes[].indexName' --output text 2>/dev/null || echo "")
        for INDEX in $INDEXES; do
            echo "   - Deleting index: $INDEX"
            aws s3vectors delete-index --vector-bucket-name "$BUCKET" --index-name "$INDEX" 2>/dev/null || true
        done
        
        # Delete the vector bucket
        aws s3vectors delete-vector-bucket --vector-bucket-name "$BUCKET" 2>/dev/null || true
        echo "   ✅ Vector bucket deleted: $BUCKET"
    done
else
    echo "   ℹ️  No vector buckets found"
fi

echo ""
echo "4. Cleaning up S3 buckets..."

# Delete S3 buckets (empty them first)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")

S3_BUCKETS=$(aws s3 ls | grep -E "s3-translation-memory-${ACCOUNT_ID}|s3-vectors-embeddings" | awk '{print $3}' || echo "")

if [ -n "$S3_BUCKETS" ]; then
    for BUCKET in $S3_BUCKETS; do
        echo "   Emptying and deleting S3 bucket: $BUCKET"
        aws s3 rm "s3://$BUCKET" --recursive 2>/dev/null || true
        aws s3 rb "s3://$BUCKET" 2>/dev/null || true
        echo "   ✅ S3 bucket deleted: $BUCKET"
    done
else
    echo "   ℹ️  No S3 buckets found"
fi

echo ""
echo "5. Cleaning up IAM roles..."

# Delete IAM roles
ROLES=$(aws iam list-roles --query 'Roles[?contains(RoleName, `s3-vectors-kb-role`)].RoleName' --output text 2>/dev/null || echo "")

if [ -n "$ROLES" ]; then
    for ROLE in $ROLES; do
        echo "   Deleting IAM role: $ROLE"
        
        # Delete inline policies
        POLICIES=$(aws iam list-role-policies --role-name "$ROLE" --query 'PolicyNames' --output text 2>/dev/null || echo "")
        for POLICY in $POLICIES; do
            aws iam delete-role-policy --role-name "$ROLE" --policy-name "$POLICY" 2>/dev/null || true
        done
        
        # Detach managed policies
        ATTACHED=$(aws iam list-attached-role-policies --role-name "$ROLE" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null || echo "")
        for ARN in $ATTACHED; do
            aws iam detach-role-policy --role-name "$ROLE" --policy-arn "$ARN" 2>/dev/null || true
        done
        
        # Delete the role
        aws iam delete-role --role-name "$ROLE" 2>/dev/null || true
        echo "   ✅ IAM role deleted: $ROLE"
    done
else
    echo "   ℹ️  No IAM roles found"
fi

echo ""
echo "=========================================="
echo "✅ Cleanup complete!"
echo "=========================================="
echo ""
echo "All workshop resources have been deleted."
