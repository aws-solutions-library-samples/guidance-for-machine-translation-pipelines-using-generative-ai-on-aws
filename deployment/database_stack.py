from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
    RemovalPolicy,
)
from constructs import Construct

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

        # Create credentials secret
        db_credentials = secretsmanager.Secret(
            self, "AuroraCredentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "mt_engine"}',
                generate_string_key="password",
                exclude_punctuation=True
            )
        )

        # Create Aurora Serverless v2 cluster
        db_cluster = rds.DatabaseCluster(
            self, "AuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_6
            ),
            credentials=rds.Credentials.from_secret(db_credentials),
            instance_props=rds.InstanceProps(
                vpc=self.vpc,
                vpc_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ),
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.BURSTABLE3,
                    ec2.InstanceSize.MEDIUM,
                )
            ),
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=1.0,
            instances=1,
            removal_policy=RemovalPolicy.DESTROY,  # For development only - change for production
            default_database_name="mt-engine-tm-database"
        )

        # Add outputs
        CfnOutput(self, "SecretName", value=db_credentials.secret_name)
        CfnOutput(self, "SecretArn", value=db_credentials.secret_arn)
        CfnOutput(self, "ClusterEndpoint", value=db_cluster.cluster_endpoint.hostname)
        CfnOutput(self, "ClusterPort", value=str(db_cluster.cluster_endpoint.port))
        #CfnOutput(self, "DatabaseName", value=db_cluster.default_database_name or "")
