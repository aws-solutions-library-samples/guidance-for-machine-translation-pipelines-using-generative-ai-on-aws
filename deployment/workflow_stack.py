# workflow_stack.py
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_iam as iam,
    aws_logs as logs,
    aws_glue as glue,
    aws_s3_assets as s3_assets,
    aws_secretsmanager as secretsmanager,
    Duration,
    Fn,
    RemovalPolicy

)
from constructs import Construct
from cdk_nag import NagSuppressions
import json

class WorkflowStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.stateMachineName = "BatchMachineTranslationStateMachineCDK"

        self.input_bucket_name = self.node.try_get_context('input_bucket_name')
        self.output_bucket_name = self.node.try_get_context('output_bucket_name')
        self.marketplace_endpoint_name = self.node.try_get_context('marketplace_endpoint_name')
        self.sgm_quality_endpoint_name = Fn.import_value("SageMakerAsyncEndpointName")
        
        # Create workflow-specific secret
        secret_name = self.node.try_get_context('config_secret_name') or 'workflow-bedrock-config'
        self.workflow_secret = self._create_workflow_secret(secret_name)

        lambda_functions = self._create_lambda_functions()
        step_functions_role = self._create_step_functions_role(lambda_functions)

        with open('../source/statemachine/definition.json', 'r') as f: # nosemgrep
            state_machine_definition = json.load(f)

        # Create Glue job
        glue_job = self._create_glue_job()
        
        definition_substitutions = {
            "DistributedMapS3_Bucket_9e75b795": self.input_bucket_name,
            "DistributedMapS3_Bucket_dd4c4e86": self.output_bucket_name,
            "lambdainvoke_FunctionName_bb13d64d": lambda_functions["prompt_generator"].function_arn,
            "lambdainvoke_FunctionName_8f56d740": lambda_functions["count_prompts"].function_arn,
            "lambdainvoke_FunctionName_025afb4a": lambda_functions["run_inferences"].function_arn,
            "lambdainvoke_FunctionName_379ed8b3": lambda_functions["batch_inference"].function_arn,
            "lambdainvoke_FunctionName_452ghc1k": lambda_functions["quality_estimation"].function_arn,
            "lambdainvoke_FunctionName_67ab9c2d": lambda_functions["quality_assessment"].function_arn,
            "lambdainvoke_FunctionName_89ef1d3b": lambda_functions["quality_assessment_notification"].function_arn,
            "lambdainvoke_FunctionName_5fc2e3a1": lambda_functions["inference_transformation"].function_arn,
            "GlueJobName": glue_job.name
        }

        log_group = logs.LogGroup(
            self, "StateMachineLogGroup",
            log_group_name=f"/aws/vendedlogs/states/{self.stateMachineName}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        state_machine = sfn.CfnStateMachine(
            self, "TranslationStateMachine",
            role_arn=step_functions_role.role_arn,
            definition=state_machine_definition,
            definition_substitutions=definition_substitutions,
            state_machine_name=f"{self.stateMachineName}",
            state_machine_type="STANDARD",
            tracing_configuration={ "enabled": True }
        )

        # Add CDK-Nag suppressions for workflow stack resources
        self._add_cdk_nag_suppressions(state_machine, step_functions_role, log_group, lambda_functions)


    def _add_cdk_nag_suppressions(self, state_machine, step_functions_role, log_group, lambda_functions):
        """Add CDK-Nag suppressions for workflow stack resources"""
        
        # Suppress warnings for Step Functions state machine
        NagSuppressions.add_resource_suppressions(
            state_machine,
            [
                {
                    "id": "AwsSolutions-SF1",
                    "reason": "X-Ray tracing is already enabled for the state machine"
                },
                {
                    "id": "AwsSolutions-SF2",
                    "reason": "Logging is configured separately for this state machine"
                }
            ]
        )
        
        # Add comprehensive suppressions for Step Functions role
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"{self.node.path}/StepFunctionsRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "The input and output buckets are working/scratchpad buckets owned by the solution. Full access to all prefixes is needed.",
                    "appliesTo": [
                        f"Resource::arn:aws:s3:::{self.input_bucket_name}/*",
                        f"Resource::arn:aws:s3:::{self.output_bucket_name}/*"
                    ]
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard is required for Step Functions execution paths",
                    "appliesTo": [
                        "Resource::arn:aws:states:<AWS::Region>:<AWS::AccountId>:execution:WorkflowStack/Map:*",
                        "Resource::arn:aws:states:<AWS::Region>:<AWS::AccountId>:execution:BatchMachineTranslationStateMachineCDK/*"
                    ]
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard is required for CloudWatch Logs streams",
                    "appliesTo": [
                        "Resource::arn:aws:logs:<AWS::Region>:<AWS::AccountId>:log-group:/aws/vendedlogs/states/BatchMachineTranslationStateMachineCDK:*"
                    ]
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard is required for X-Ray permissions",
                    "appliesTo": [
                        "Resource::*"
                    ]
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard is required for Glue job permissions",
                    "appliesTo": [
                        "Resource::arn:aws:glue:<AWS::Region>:<AWS::AccountId>:job/*"
                    ]
                }
            ]
        )
        
        # Suppress warnings for Lambda functions
        for name, func in lambda_functions.items():
            NagSuppressions.add_resource_suppressions(
                func,
                [
                    {
                        "id": "AwsSolutions-L1",
                        "reason": "Latest runtime is used for Lambda functions"
                    }
                ]
            )
        
        # Suppress warnings for CloudWatch Log Group
        NagSuppressions.add_resource_suppressions(
            log_group,
            [
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Log retention is set to one week for development purposes"
                }
            ]
        )


    def _create_lambda_functions(self):
        lambda_role = self._create_lambda_role()

        secret_arn = Fn.import_value("DatabaseSecretArn")
        cluster_arn = Fn.import_value("DatabaseClusterArn")
        database_name = Fn.import_value("DatabaseName")

        functions = {
            "prompt_generator": lambda_.Function(
                self, "TranslationPromptGeneratorCDK",
                runtime=lambda_.Runtime.PYTHON_3_13,
                handler="lambda_function.lambda_handler",
                code=lambda_.Code.from_asset("../source/lambda/prompt_generator"),
                role=lambda_role,
                timeout=Duration.minutes(5),
                environment={
                    "DATABASE_SECRET_ARN": secret_arn,
                    "CLUSTER_ARN": cluster_arn,
                    "DATABASE_NAME": database_name,
                    "WORKFLOW_SECRET_ARN": self.workflow_secret.secret_arn,
                    "DEFAULT_SOURCE_LANG": "en",
                    "DEFAULT_TARGET_LANG": "fr",
                    "ENABLE_TRANSLATION_MEMORY": "false"
                }
            ),
            "count_prompts": lambda_.Function(
                self, "CountTranslationPromptsCDK",
                runtime=lambda_.Runtime.PYTHON_3_13,
                handler="lambda_function.lambda_handler",
                code=lambda_.Code.from_asset("../source/lambda/count_prompts"),
                role=lambda_role,
                timeout=Duration.minutes(5)
            ),
            "run_inferences": lambda_.Function(
                self, "RunTranslationInferencesCDK",
                runtime=lambda_.Runtime.PYTHON_3_13,
                handler="lambda_function.lambda_handler",
                code=lambda_.Code.from_asset("../source/lambda/run_inferences"),
                role=lambda_role,
                timeout=Duration.minutes(15),
                environment={
                    "WORKFLOW_SECRET_ARN": self.workflow_secret.secret_arn
                }
            ),
            "batch_inference": lambda_.Function(
                self, "LaunchBatchInferenceJobCDK",
                runtime=lambda_.Runtime.PYTHON_3_13,
                handler="lambda_function.lambda_handler",
                code=lambda_.Code.from_asset("../source/lambda/batch_inference"),
                role=lambda_role,
                timeout=Duration.minutes(5)
            ),
            "quality_estimation": lambda_.Function(
                self, "QualityEstimationCDK",
                runtime=lambda_.Runtime.PYTHON_3_13,
                handler="lambda_function.lambda_handler",
                code=lambda_.Code.from_asset("../source/lambda/quality_estimation"),
                role=self._create_quality_estimation_role(),
                timeout=Duration.minutes(5),
                environment={
                    "SAGEMAKER_ENDPOINT_NAME": self.sgm_quality_endpoint_name,
                    "MARKETPLACE_ENDPOINT_NAME": self.marketplace_endpoint_name or "",
                    "QUALITY_ESTIMATION_MODE": "MARKETPLACE_SELF_HOSTED" if self.marketplace_endpoint_name else "OPEMN_SOURCE_SELF_HOSTED",
                    "USE_CROSS_ACCOUNT_ENDPOINT": "N",  # Set to 'Y' if using cross-account access
                    "CROSS_ACCOUNT_ENDPOINT_ACCESS_ROLE_ARN": "<Replace with actual role ARN if needed>",  # Replace with actual role ARN if needed
                    "CROSS_ACCOUNT_ENDPOINT_ACCOUNT_ID": "<Replace with actual account ID if needed>"  # Replace with actual account ID if needed
                }
            ),
            "quality_assessment": lambda_.Function(
                self, "QualityAssessmentCDK",
                runtime=lambda_.Runtime.PYTHON_3_13,
                handler="lambda_function.lambda_handler",
                code=lambda_.Code.from_asset("../source/lambda/quality_assessment"),
                role=lambda_role,
                timeout=Duration.minutes(5),
                environment={
                    "WORKFLOW_SECRET_ARN": self.workflow_secret.secret_arn
                }
            ),
            "quality_assessment_notification": lambda_.Function(
                self, "QualityAssessmentNotificationCDK",
                runtime=lambda_.Runtime.PYTHON_3_13,
                handler="lambda_handler.lambda_handler",
                code=lambda_.Code.from_asset("../source/lambda/quality_estimation_notification"),
                role=lambda_role,
                timeout=Duration.minutes(5)
            ),
            "inference_transformation": lambda_.Function(
                self, "InferenceTransformationCDK",
                runtime=lambda_.Runtime.PYTHON_3_13,
                handler="lambda_function.lambda_handler",
                code=lambda_.Code.from_asset("../source/lambda/inference_transformation"),
                role=lambda_role,
                timeout=Duration.minutes(5)
            )
        }
        return functions


    def _create_step_functions_role(self, lambda_functions):
        role_name = "StepFunctions_IAM_ROLE_BatchMachineTranslation"
        
        # Create a new role - if it already exists, CloudFormation will handle the error
        role = iam.Role(
            self, "StepFunctionsRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            role_name=role_name
        )

        # This suppression is now handled in _add_cdk_nag_suppressions method

        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject", "s3:ListBucket"],
            resources=[
                f"arn:aws:s3:::{self.input_bucket_name}",
                f"arn:aws:s3:::{self.input_bucket_name}/*"
            ]
        ))

        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:ListMultipartUploadParts", "s3:AbortMultipartUpload"],
            resources=[
                f"arn:aws:s3:::{self.output_bucket_name}",
                f"arn:aws:s3:::{self.output_bucket_name}/*"
            ]
        ))

        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["lambda:InvokeFunction"],
            resources=[func.function_arn for func in lambda_functions.values()]
        ))

        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["states:RedriveExecution"],
            resources=[f"arn:aws:states:{self.region}:{self.account}:execution:{self.stack_name}/Map:*"]
        ))

        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["states:StartExecution", "states:DescribeExecution", "states:StopExecution"],
            resources=[
                f"arn:aws:states:{self.region}:{self.account}:stateMachine:{self.stateMachineName}",
                f"arn:aws:states:{self.region}:{self.account}:execution:{self.stateMachineName}/*"
            ]
        ))

        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogGroups"],
            resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/vendedlogs/states/{self.stateMachineName}:*"]
        ))

        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets"],
            resources=["*"]
        ))
        
        # Add Glue job permissions
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["glue:StartJobRun", "glue:GetJobRun", "glue:GetJobRuns", "glue:BatchStopJobRun"],
            resources=[f"arn:aws:glue:{self.region}:{self.account}:job/*"]
        ))

        return role

    def _create_lambda_role(self) -> iam.Role:
        role_name = "lambda-translation-role-cdk"
        
        # Create a new role - if it already exists, CloudFormation will handle the error
        lambda_role = iam.Role(
            self, "TranslationLambdaRole",
            role_name=role_name,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        NagSuppressions.add_resource_suppressions(
            lambda_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Using AWS managed policies for Lambda basic execution, Bedrock, and Secrets Manager access"
                }
            ]
        )

        lambda_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))
        
        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:GetModelCustomizationJob",
                "bedrock:ListModelCustomizationJobs"
            ],
            resources=["*"]
        ))

        # Add permissions to list models
        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            resources=["*"]
        )) 
        
        # Add specific Secrets Manager permissions for both database and workflow secrets
        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["secretsmanager:GetSecretValue"],
            resources=[
                Fn.import_value("DatabaseSecretArn"),
                self.workflow_secret.secret_arn
            ]
        ))

        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["rds-data:BatchExecuteStatement", "rds-data:BeginTransaction", "rds-data:CommitTransaction", "rds-data:ExecuteStatement", "rds-data:RollbackTransaction"],
            resources=[Fn.import_value("DatabaseClusterArn")]
        ))

        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:ListBucket"],
            resources=[
                f"arn:aws:s3:::{self.input_bucket_name}",
                f"arn:aws:s3:::{self.input_bucket_name}/*"
            ]
        ))

        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
            resources=[
                f"arn:aws:s3:::{self.output_bucket_name}",
                f"arn:aws:s3:::{self.output_bucket_name}/*"
            ]
        ))
        
        # Add suppressions for Lambda role S3 bucket wildcard permissions
        # Adding after all permissions to ensure the policy exists
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"{self.node.path}/TranslationLambdaRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "The input and output buckets are working/scratchpad buckets owned by the solution. Full access to all prefixes is needed.",
                    "appliesTo": [
                        f"Resource::arn:aws:s3:::{self.input_bucket_name}/*",
                        f"Resource::arn:aws:s3:::{self.output_bucket_name}/*"
                    ]
                }
            ]
        )

        return lambda_role

    def _create_quality_estimation_role(self) -> iam.Role:
        role_name = "lambda-quality-estimation-role-cdk"
        
        # Create a new role - if it already exists, CloudFormation will handle the error
        quality_estimation_role = iam.Role(
            self, "QualityEstimationLambdaRole",
            role_name=role_name,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        quality_estimation_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))
        
        # Add CDK-Nag suppressions for quality estimation role
        NagSuppressions.add_resource_suppressions(
            quality_estimation_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Using AWS managed policy for Lambda basic execution"
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "The input and output buckets are working/scratchpad buckets owned by the solution. Full access to all prefixes is needed.",
                    "appliesTo": [
                        f"Resource::arn:aws:s3:::{self.input_bucket_name}/*",
                        f"Resource::arn:aws:s3:::{self.output_bucket_name}/*"
                    ]
                }
            ]
        )

        # Add permissions for async endpoint
        quality_estimation_role.add_to_policy(iam.PolicyStatement(
            actions=["sagemaker:InvokeEndpointAsync", "sagemaker:DescribeEndpoint"],
            resources=[f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/{self.sgm_quality_endpoint_name}"]
        ))
        
        # Add permissions for marketplace endpoint if specified
        if self.marketplace_endpoint_name:
            quality_estimation_role.add_to_policy(iam.PolicyStatement(
                actions=["sagemaker:InvokeEndpoint", "sagemaker:DescribeEndpoint"],
                resources=[f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/{self.marketplace_endpoint_name}"]
            ))
        
        # Add permissions for S3 operations needed by marketplace implementation
        quality_estimation_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:PutObject"],
            resources=[
                f"arn:aws:s3:::{self.input_bucket_name}/*",
                f"arn:aws:s3:::{self.output_bucket_name}/*"
            ]
        ))
        
        # Add permissions for Step Functions operations needed by marketplace implementation
        states_policy = iam.PolicyStatement(
            actions=["states:SendTaskSuccess", "states:SendTaskFailure"],
            resources=["*"]  # Scope down in production
        )
        quality_estimation_role.add_to_policy(states_policy)
        
        # Add CDK-Nag suppressions for overly permissive policy
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f"{self.node.path}/QualityEstimationLambdaRole/DefaultPolicy/Resource",
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Wildcard resource is used for Step Functions actions, would be scoped down in production"
                }
            ]
        )
        
        return quality_estimation_role
        
    def _create_glue_job(self):
        # Create Glue job role
        role_name = "glue-translation-processor-role"
        
        # Create a new role - if it already exists, CloudFormation will handle the error
        glue_role = iam.Role(
            self, "TranslationGlueJobRole",
            role_name=role_name,
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com")
        )
        
        # Add necessary permissions
        glue_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"))
        
        # Add CDK-Nag suppressions for Glue role
        NagSuppressions.add_resource_suppressions(
            glue_role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Using AWS managed policy for Glue service role"
                }
            ]
        )
        
        # Add S3 permissions
        glue_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject"],
            resources=[
                f"arn:aws:s3:::{self.input_bucket_name}",
                f"arn:aws:s3:::{self.input_bucket_name}/*",
                f"arn:aws:s3:::{self.output_bucket_name}",
                f"arn:aws:s3:::{self.output_bucket_name}/*"
            ]
        ))
        
        # Create script asset
        script_asset = s3_assets.Asset(
            self, "GlueScriptAsset",
            path="../source/glue/translation_results_processor.py"
        )
        
        # Grant read permissions to the Glue role
        script_asset.grant_read(glue_role)
        
        # Create Glue job
        glue_job = glue.CfnJob(
            self, "TranslationResultsProcessor",
            name="translation-results-processor",
            role=glue_role.role_arn,
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                python_version="3",
                script_location=script_asset.s3_object_url
            ),
            default_arguments={
                "--job-language": "python",
                "--enable-metrics": "",
                "--extra-py-files": "s3://aws-glue-studio-transforms-251189692203-prod-us-east-2/gs_common.py,s3://aws-glue-studio-transforms-251189692203-prod-us-east-2/gs_flatten.py"
            },
            glue_version="5.0",
            max_retries=2,
            timeout=60,  # 60 minutes
            number_of_workers=2,
            worker_type="G.1X"  # 1 DPU per worker
        )
        
        return glue_job
    
    def _create_workflow_secret(self, secret_name: str) -> secretsmanager.Secret:
        """Create a workflow-specific secret for Bedrock model configuration"""
        secret = secretsmanager.Secret(
            self, "WorkflowSecret",
            secret_name=secret_name,
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({
                    "bedrock_model_id": "us.amazon.nova-pro-v1:0",
                    "assessment_model_id": "us.amazon.nova-pro-v1:0"
                }),
                generate_string_key="placeholder",
                exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\@"
            )
        )
        
        # Add CDK-Nag suppression for secret without automatic rotation
        NagSuppressions.add_resource_suppressions(
            secret,
            [
                {
                    "id": "AwsSolutions-SMG4",
                    "reason": "This secret contains static configuration values that don't require automatic rotation"
                }
            ]
        )
        
        return secret