#!/usr/bin/env python3
from aws_cdk import (
    App,
    Aspects
)
from database_stack import DatabaseStack
from workflow_stack import WorkflowStack
from sagemaker_stack import SageMakerStack
from cdk_nag import AwsSolutionsChecks, NagSuppressions

# Initialize the CDK app
app = App()

# Get context parameters
vpc_id = app.node.try_get_context('vpc_id')
marketplace_endpoint_name = app.node.try_get_context('marketplace_endpoint_name')

# Deploy Database Stack
database_stack = DatabaseStack(app, "DatabaseStack", vpc_id=vpc_id)

# Deploy SageMaker Stack
sagemaker_stack = SageMakerStack(app, "SageMakerStack")

# Deploy Workflow Stack with marketplace endpoint if specified
workflow_stack = WorkflowStack(app, "WorkflowStack")

# Add comprehensive suppressions for Glue role
NagSuppressions.add_resource_suppressions_by_path(
    workflow_stack,
    f"{workflow_stack.node.path}/TranslationGlueJobRole/DefaultPolicy/Resource",
    [
        {
            "id": "AwsSolutions-IAM5",
            "reason": "The input and output buckets are working/scratchpad buckets owned by the solution. Full access to all prefixes is needed.",
            "appliesTo": [
                f"Resource::arn:aws:s3:::{workflow_stack.input_bucket_name}/*",
                f"Resource::arn:aws:s3:::{workflow_stack.output_bucket_name}/*"
            ]
        },
        {
            "id": "AwsSolutions-IAM5",
            "reason": "S3 wildcard actions are required for Glue job to access data",
            "appliesTo": [
                "Action::s3:GetBucket*",
                "Action::s3:GetObject*",
                "Action::s3:List*"
            ]
        },
        {
            "id": "AwsSolutions-IAM5",
            "reason": "CDK assets bucket access is required for Glue script",
            "appliesTo": [
                "Resource::arn:<AWS::Partition>:s3:::cdk-hnb659fds-assets-<AWS::AccountId>-<AWS::Region>/*"
            ]
        }
    ]
)

# Add comprehensive suppressions for GlueTranslationLambdaRole role
NagSuppressions.add_resource_suppressions_by_path(
    workflow_stack,
    f"{workflow_stack.node.path}/TranslationLambdaRole/DefaultPolicy/Resource",
    [
        {
            "id": "AwsSolutions-IAM5",
            "reason": "Wildcard is required for Bedrock permissions as solution supports multiple models",
            "appliesTo": [
                "Resource::*"
            ]
        }
    ]
)


# Add dependency to ensure correct deployment order
workflow_stack.add_dependency(database_stack)
workflow_stack.add_dependency(sagemaker_stack)

# Apply CDK-Nag to all stacks in the app
Aspects.of(app).add(AwsSolutionsChecks())

# Add suppressions for specific rules if needed
NagSuppressions.add_stack_suppressions(database_stack, [
    # Example suppression - uncomment and customize as needed
    # {"id": "AwsSolutions-IAM4", "reason": "Default AWS managed policies are used for demo purposes"},
])

# Output the marketplace endpoint configuration if provided
if marketplace_endpoint_name:
    print(f"Using Marketplace endpoint: {marketplace_endpoint_name}")
    print("Quality estimation mode: MARKETPLACE")
else:
    print("Using default async endpoint for quality estimation")
    print("Quality estimation mode: ASYNC")

app.synth()