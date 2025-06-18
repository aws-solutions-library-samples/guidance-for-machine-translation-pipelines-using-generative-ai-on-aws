'use strict';

const AWS = require('aws-sdk');
const lambda = new AWS.Lambda();

exports.handler = async (event, context) => {
  console.log('PreTraffic Hook started');
  console.log(JSON.stringify(event));
  
  // Get the deployed Lambda function
  const functionToTest = event.DeploymentId.replace('d-', 'f-');
  
  // Run basic validation test
  try {
    const params = {
      FunctionName: functionToTest,
      InvocationType: 'RequestResponse',
      Payload: JSON.stringify({ test: true })
    };
    
    const result = await lambda.invoke(params).promise();
    console.log('Validation test result:', result);
    
    // Return success if the function executed without errors
    await sendResult(event, context, 'Succeeded');
    return 'PreTraffic validation succeeded';
  } catch (error) {
    console.error('Validation test failed:', error);
    await sendResult(event, context, 'Failed');
    return 'PreTraffic validation failed';
  }
};

async function sendResult(event, context, status) {
  const codedeploy = new AWS.CodeDeploy();
  const params = {
    deploymentId: event.DeploymentId,
    lifecycleEventHookExecutionId: event.LifecycleEventHookExecutionId,
    status: status
  };
  
  return await codedeploy.putLifecycleEventHookExecutionStatus(params).promise();
}
