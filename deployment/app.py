#!/usr/bin/env python3
import aws_cdk as cdk
from database_stack import DatabaseStack

app = cdk.App()
DatabaseStack(app, "DatabaseStack", vpc_id=app.node.try_get_context('vpc_id'))
app.synth()