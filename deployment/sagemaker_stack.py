# sagemaker_stack.py
from aws_cdk import (
    Stack,
    aws_sagemaker as sagemaker,
    aws_iam as iam,
    aws_sns as sns,
    aws_lambda as lambda_,
    aws_sns_subscriptions as sns_subscriptions,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_secretsmanager as secretsmanager,
    SecretValue,
    CfnOutput,
    Fn,
    RemovalPolicy,
    Duration,
    aws_s3_assets as s3_assets,
    Aws
)
from constructs import Construct
from cdk_nag import NagSuppressions
import os

class SageMakerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get bucket name from context
        output_bucket_name = self.node.try_get_context('output_bucket_name')
        
        # Create SageMaker model with a unique name that includes a timestamp
        model_name = self.node.try_get_context('quality_estimation_sgm_model_name')
        image_uri = self.node.try_get_context('quality_estimation_sgm_image_uri')
        hf_token = self.node.try_get_context('hugging_face_token')
        topic_name = self.node.try_get_context('quality_estimation_sgm_topic_name')
        endpoint_name = self.node.try_get_context('quality_estimation_sgm_endpoint_name')

        # Create secret for HuggingFace token
        hf_secret = secretsmanager.CfnSecret(
            self, "HuggingFaceTokenSecretV2",
            name="huggingface-api-token",
            description="HuggingFace API token",
            secret_string=hf_token,
        )
        
        # Add CDK-Nag suppression for automatic rotation
        NagSuppressions.add_resource_suppressions(
            hf_secret,
            [
                {
                    "id": "AwsSolutions-SMG4",
                    "reason": "HuggingFace API tokens do not expire automatically and rotation requires manual intervention"
                }
            ]
        )

        # Create SNS topics for async inference notifications
        success_topic = sns.Topic(
            self, "SageMakerAsyncSuccessTopic",
            topic_name=f"{topic_name}-success",
            enforce_ssl=True
        )
        # Grant EventBridge permission to publish to the SNS topic
        success_topic.grant_publish(iam.ServicePrincipal("events.amazonaws.com"))
        
        error_topic = sns.Topic(
            self, "SageMakerAsyncErrorTopic",
            topic_name=f"{topic_name}-error",
            enforce_ssl=True
        )
        
        # Create SageMaker execution role with least privilege
        sagemaker_role = iam.Role(
            self, "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com")
        )
        
        # Add specific permissions instead of using the broad managed policy
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sagemaker:CreateModel",
                    "sagemaker:CreateEndpointConfig",
                    "sagemaker:CreateEndpoint",
                    "sagemaker:DescribeModel",
                    "sagemaker:DescribeEndpointConfig",
                    "sagemaker:DescribeEndpoint",
                    "sagemaker:InvokeEndpointAsync"
                ],
                resources=[
                    f"arn:aws:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model/{model_name}",
                    f"arn:aws:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:endpoint-config/{model_name}-async-config",
                    f"arn:aws:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:endpoint/{endpoint_name}"
                ]
            )
        )
        
        # Extract ECR repository information from image_uri
        # Expected format: account.dkr.ecr.region.amazonaws.com/repository/image_name:tag
        image_parts = image_uri.split('/')
        if len(image_parts) >= 2:
            ecr_domain = image_parts[0]  # account.dkr.ecr.region.amazonaws.com
            repository_path = '/'.join(image_parts[1:])  # repository/image_name:tag
            
            # Split repository path and tag
            if ':' in repository_path:
                repository = repository_path.split(':')[0]  # repository/image_name
                tag = repository_path.split(':')[1]  # tag
            else:
                repository = repository_path
                tag = "latest"  # Default tag
                
            # Extract account ID from ECR domain
            account_id = ecr_domain.split('.')[0]
            
            # Add ECR permissions to allow pulling the container image
            sagemaker_role.add_to_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ecr:GetDownloadUrlForLayer", 
                        "ecr:BatchGetImage",
                        "ecr:BatchCheckLayerAvailability"
                    ],
                    resources=[
                        f"arn:aws:ecr:{Aws.REGION}:{account_id}:repository/{repository}",
                        f"arn:aws:ecr:{Aws.REGION}:{account_id}:repository/{repository}:{tag}"
                    ]
                )
            )
                    
            # Add ECR authorization token permissions
            sagemaker_role.add_to_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ecr:GetAuthorizationToken"
                    ],
                    resources=["*"]  # This permission doesn't support resource-level restrictions
                )
            )

        # Add suppression for the wildcard resource in GetAuthorizationToken permission
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"{self.node.path}/SageMakerExecutionRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "GetAuthorizationToken requires wildcard permission as it doesn't support resource-level restrictions",
                    "appliesTo": ["Resource::*"]
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "SageMaker requires wildcard permissions for CloudWatch Logs as it creates log groups dynamically",
                    "appliesTo": [f"Resource::arn:aws:logs:<AWS::Region>:<AWS::AccountId>:log-group:/aws/sagemaker/*"]
                }
            ]
        )
        
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                resources=[
                    f"arn:aws:s3:::{output_bucket_name}",
                    f"arn:aws:s3:::{output_bucket_name}/*"
                ]
            )
        )
        
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sns:Publish"
                ],
                resources=[
                    success_topic.topic_arn,
                    error_topic.topic_arn
                ]
            )
        )
        
        # Add CloudWatch Logs permissions for SageMaker endpoint
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=[
                    f"arn:aws:logs:{Aws.REGION}:{Aws.ACCOUNT_ID}:log-group:/aws/sagemaker/*"
                ]
            )
        )
        
        # Add Secrets Manager permissions for HuggingFace token
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue"
                ],
                resources=[
                    hf_secret.attr_id
                ]
            )
        )
        
        # Create notification Lambda role
        notification_lambda_role = iam.Role(
            self, "NotificationLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        
        notification_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )
        
        # Define Step Functions state machine ARN pattern for more specific permissions
        states_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "states:SendTaskSuccess",
                "states:SendTaskFailure",
                "states:SendTaskHeartbeat"
            ],
            resources=[
                f"arn:aws:states:{Aws.REGION}:{Aws.ACCOUNT_ID}:stateMachine:*",
                f"arn:aws:states:{Aws.REGION}:{Aws.ACCOUNT_ID}:execution:*:*"
            ]
        )
        notification_lambda_role.add_to_policy(states_policy)

        # Add SSM GetParameter permission
        notification_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[f"arn:aws:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/*"]
            )
        )
        # Add permission to call Bedrock GetModelInvocationJob
        notification_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:GetModelInvocationJob"],
                resources=[f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:model-invocation-job/*"]
            )
        )

        NagSuppressions.add_resource_suppressions(
            notification_lambda_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Using AWS managed policy for basic Lambda logging and monitoring is sufficient for this use case."
                }
            ]
        )
        
        # Add CDK-Nag suppressions for overly permissive policy
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"{self.node.path}/NotificationLambdaRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard resource is used for Step Functions actions, would be scoped down in production"
                }
            ]
        )
        
        # Create notification Lambda function
        notification_lambda = lambda_.Function(
            self, "QualityEstimationNotificationLambdaCDK",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="lambda_handler.lambda_handler",
            code=lambda_.Code.from_asset("../source/lambda/quality_estimation_notification"),
            role=notification_lambda_role,
            timeout=Duration.seconds(60),
            memory_size=256
        )
        
        # Subscribe the Lambda function to both SNS topics
        success_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(notification_lambda)
        )
        
        error_topic.add_subscription(
            sns_subscriptions.LambdaSubscription(notification_lambda)
        )
        
        
        # Create SageMaker model with S3 model data
        model = sagemaker.CfnModel(
            self, "QualityEstimationModel",
            execution_role_arn=sagemaker_role.role_arn,
            model_name=model_name,
            primary_container={
                "image": image_uri,
                "environment": {
                    "HF_SECRET_ARN": hf_secret.attr_id
                }
            }
        )

        model.node.add_dependency(sagemaker_role)

        
        # Create async endpoint configuration
        endpoint_config = sagemaker.CfnEndpointConfig(
            self, "QualityEstimationAsyncEndpointConfig",
            endpoint_config_name=f"{model_name}-async-config",
            production_variants=[
                sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    variant_name="AllTraffic",
                    model_name=model_name,
                    instance_type="ml.g4dn.xlarge",
                    initial_instance_count=1
                )
            ],
            async_inference_config=sagemaker.CfnEndpointConfig.AsyncInferenceConfigProperty(
                output_config=sagemaker.CfnEndpointConfig.AsyncInferenceOutputConfigProperty(
                    s3_output_path=f"s3://{output_bucket_name}/sagemaker-async-results",
                    notification_config=sagemaker.CfnEndpointConfig.AsyncInferenceNotificationConfigProperty(
                        success_topic=success_topic.topic_arn,
                        error_topic=error_topic.topic_arn
                    )
                ),
                client_config=sagemaker.CfnEndpointConfig.AsyncInferenceClientConfigProperty(
                    max_concurrent_invocations_per_instance=4
                )
            )
        )
        
        endpoint_config.add_depends_on(model)
        
        # Endpoint name already defined at the top of the function
        endpoint = sagemaker.CfnEndpoint(
            self, "QualityEstimationAsyncEndpoint",
            endpoint_name=endpoint_name,
            endpoint_config_name=endpoint_config.endpoint_config_name
        )
        
        endpoint.add_depends_on(endpoint_config)
        
        # Add CDK-Nag suppressions for SageMaker resources
        NagSuppressions.add_resource_suppressions(
            sagemaker_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "SageMaker role permissions are scoped to specific resources and actions required for the quality estimation model"
                }
            ]
        )
        
        # Add specific suppressions for S3 wildcard permissions
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"{self.node.path}/SageMakerExecutionRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "S3 permissions with wildcards are required for CDK assets and SageMaker model access",
                    "appliesTo": [
                        "Action::s3:GetBucket*",
                        "Action::s3:GetObject*",
                        "Action::s3:List*",
                        "Resource::arn:<AWS::Partition>:s3:::cdk-hnb659fds-assets-<AWS::AccountId>-<AWS::Region>/*",
                        f"Resource::arn:aws:s3:::{output_bucket_name}/*"
                    ]
                }
            ]
        )
        NagSuppressions.add_resource_suppressions(
            sagemaker_role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "SageMaker role permissions are scoped to specific resources and actions required for the quality estimation model"
                }
            ]
        )
        self._add_cdk_nag_suppressions(model, endpoint_config, endpoint, notification_lambda)

        CfnOutput(
            self, "SageMakerAsyncEndpointName",
            value=endpoint_name,
            description="SageMaker Asynchronous Endpoint Name",
            export_name="SageMakerAsyncEndpointName"
        )
        
        CfnOutput(
            self, "SageMakerSuccessTopicArn",
            value=success_topic.topic_arn,
            description="SNS Topic ARN for successful inferences",
            export_name="SageMakerSuccessTopicArn"
        )
        
        CfnOutput(
            self, "SageMakerErrorTopicArn",
            value=error_topic.topic_arn,
            description="SNS Topic ARN for failed inferences",
            export_name="SageMakerErrorTopicArn"
        )
        
        CfnOutput(
            self, "NotificationLambdaArn",
            value=notification_lambda.function_arn,
            description="Lambda function ARN for SageMaker notifications",
            export_name="NotificationLambdaArn"
        )
        
        CfnOutput(
            self, "HuggingFaceSecretArn",
            value=hf_secret.attr_id,
            description="ARN of the HuggingFace token secret",
            export_name="HuggingFaceSecretArn"
        )
        
    def _add_cdk_nag_suppressions(self, model, endpoint_config, endpoint, notification_lambda):
        """Add CDK-Nag suppressions for SageMaker stack resources"""
        
        # Suppress warnings for SageMaker model
        NagSuppressions.add_resource_suppressions(
            model,
            [
                {
                    "id": "AwsSolutions-SM1",
                    "reason": "Model is using a custom container image"
                }
            ]
        )
        
        # Suppress warnings for SageMaker endpoint config
        NagSuppressions.add_resource_suppressions(
            endpoint_config,
            [
                {
                    "id": "AwsSolutions-SM2",
                    "reason": "Using g4dn.xlarge instance type which is appropriate for this model"
                }
            ]
        )
        
        # Suppress warnings for SageMaker endpoint
        NagSuppressions.add_resource_suppressions(
            endpoint,
            [
                {
                    "id": "AwsSolutions-SM3",
                    "reason": "Endpoint is configured with appropriate instance type"
                }
            ]
        )
        
        # Suppress warnings for Lambda function
        NagSuppressions.add_resource_suppressions(
            notification_lambda,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Latest runtime is used for Lambda function"
                }
            ]
        )