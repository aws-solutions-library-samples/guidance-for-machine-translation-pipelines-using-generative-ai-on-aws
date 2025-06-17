from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
    aws_iam as iam,
    Duration,
    CfnOutput,
    RemovalPolicy,
)
from constructs import Construct
from cdk_nag import NagSuppressions

class DatabaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc_id: str = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Look up existing VPC if vpc_id is provided, otherwise create a new one
        if vpc_id:
            self.vpc = ec2.Vpc.from_lookup(self, "ExistingVPC", vpc_id=vpc_id)
        else:
            self.vpc = ec2.Vpc(
                self, "DatabaseVPC",
                max_azs=2,
                nat_gateways=1,
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name="Private",
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                        cidr_mask=24
                    ),
                    ec2.SubnetConfiguration(
                        name="Public",
                        subnet_type=ec2.SubnetType.PUBLIC,
                        cidr_mask=24
                    )
                ]
            )
            
            # Create VPC Flow Log
            log_group = logs.LogGroup(
                self, "VPCFlowLogGroup",
                retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=RemovalPolicy.DESTROY
            )
            
            # Create Flow Log Role
            flow_log_role = iam.Role(
                self, "VPCFlowLogRole",
                assumed_by=iam.ServicePrincipal("vpc-flow-logs.amazonaws.com")
            )
            
            # Add Flow Log to VPC
            ec2.FlowLog(
                self, "VPCFlowLog",
                resource_type=ec2.FlowLogResourceType.from_vpc(self.vpc),
                destination=ec2.FlowLogDestination.to_cloud_watch_logs(log_group, flow_log_role)
            )

        # Create credentials secret with rotation
        db_credentials = secretsmanager.Secret(
            self, "AuroraCredentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "mt_engine"}',
                generate_string_key="password",
                exclude_punctuation=True
            )
        )

        # Create Aurora Serverless v2 cluster
        database_name = "MTEngineTranslationMemoryDb"
        db_cluster = rds.DatabaseCluster(
            self, "TranslationMemoryAuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_6
            ),
            credentials=rds.Credentials.from_secret(db_credentials),
            instance_props=rds.InstanceProps(
                vpc=self.vpc,
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ),
                #TODO: Need to configure Reader/Writer instances to make sure serverless v2 is used
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.BURSTABLE3,
                    ec2.InstanceSize.MEDIUM,
                )
            ),
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=1.0,
            removal_policy=RemovalPolicy.DESTROY,  # For development only - change for production
            default_database_name=database_name,
            storage_encrypted=True,  # Enable storage encryption
            iam_authentication=True,  # Enable IAM authentication
            deletion_protection=True  # Enable deletion protection
            #enable_data_api=True
        )

        # Add outputs
        CfnOutput(self, "DatabaseSecretName", value=db_credentials.secret_name, export_name="DatabaseSecretName")
        CfnOutput(self, "DatabaseSecretArn", value=db_credentials.secret_arn, export_name="DatabaseSecretArn")
        CfnOutput(self, "DatabaseClusterEndpoint", value=db_cluster.cluster_endpoint.hostname, export_name="DatabaseClusterEndpoint")
        CfnOutput(self, "DatabaseClusterPort", value=str(db_cluster.cluster_endpoint.port), export_name="DatabaseClusterPort")
        CfnOutput(self, "DatabaseName", value=database_name, export_name="DatabaseName")
        CfnOutput(self, "DatabaseClusterArn",value=self.format_arn(service="rds",resource="cluster",resource_name=db_cluster.cluster_resource_identifier),export_name="DatabaseClusterArn")
        
        # Setup secret rotation
        db_credentials.add_rotation_schedule(
            "Rotation",
            automatically_after=Duration.days(30),
            hosted_rotation=secretsmanager.HostedRotation.postgre_sql_single_user()
        )
        
        # Add stack-specific CDK-Nag suppressions
        NagSuppressions.add_resource_suppressions(
            db_cluster,
            [
                {
                    "id": "AwsSolutions-RDS3",
                    "reason": "Removal policy set to DESTROY for development purposes only. Should be changed for production."
                }
                # RDS2, RDS6, and RDS10 issues have been fixed
            ]
        )
        
        # Add suppression for log group retention
        if not vpc_id:  # Only if we created a new VPC
            NagSuppressions.add_resource_suppressions_by_path(
                self,
                f"{self.node.path}/VPCFlowLogGroup/Resource",
                [
                    {
                        "id": "AwsSolutions-IAM4",
                        "reason": "Flow log role uses AWS managed policy"
                    }
                ]
            )