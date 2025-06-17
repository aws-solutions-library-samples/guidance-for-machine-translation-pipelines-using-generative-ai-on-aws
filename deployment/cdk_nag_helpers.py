"""
Helper functions for CDK-Nag suppressions and compliance management.
"""
from typing import List, Dict, Any
from constructs import Construct
from cdk_nag import NagSuppressions

def add_common_suppressions(construct: Construct, resource_id: str, rules: List[Dict[str, Any]]) -> None:
    """
    Add common suppressions to a specific resource.
    
    Args:
        construct: The CDK construct containing the resource
        resource_id: The logical ID of the resource
        rules: List of rules to suppress with reasons
    """
    resource = construct.node.find_child(resource_id)
    if resource:
        NagSuppressions.add_resource_suppressions(resource, rules)

def add_database_common_suppressions(database_stack: Construct) -> None:
    """
    Add common suppressions for database resources.
    
    Args:
        database_stack: The database stack construct
    """
    # Example suppressions for common database issues
    NagSuppressions.add_resource_suppressions_by_path(
        database_stack,
        "/DatabaseStack/TranslationMemoryAuroraCluster/Resource",
        [
            {
                "id": "AwsSolutions-RDS3",
                "reason": "Deletion protection disabled for development purposes"
            },
            {
                "id": "AwsSolutions-RDS2",
                "reason": "Auto minor version upgrade configured separately"
            }
        ]
    )

def add_security_group_suppressions(security_group: Construct, reason: str) -> None:
    """
    Add suppressions for security group resources.
    
    Args:
        security_group: The security group construct
        reason: Reason for the suppression
    """
    NagSuppressions.add_resource_suppressions(
        security_group,
        [
            {
                "id": "AwsSolutions-EC23",
                "reason": reason
            }
        ]
    )