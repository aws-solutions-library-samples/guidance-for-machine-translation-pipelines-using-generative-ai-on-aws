# Instructions guided solution deployment with Amazon Q CLI
If the user asks you to deploy the solution in guided mode ensure you follow the guidelines listed below:
- DO NOT forget to create a virtual Python environment before proceeding
- ENSURE you install package dependancies listed in the requirements.txt file located under deployment/
- Before deploying the stacks MAKE SURE that all the context parameters in the deployment/cdk.json, that not marked as optional in the README or without a default value, are populated with the appropriate value. Ask the user if you are missing some. You should be able to at least retrieve the quality_estimation_sgm_image_uri from the output of the sagemaker/build_and_push.sh script
- Before deploying the stacks ask the user whether they want you to use automatic approval. If the answer yes or y, add the proper options to the cdk deploy command so that deployment doesn't wait for user's approval to create resources
- While deploying the stacks ENSURE that the Python environment is always activated when running cdk commands
- Create a Stack deployment summary at the end of the deployment in markdown format
- If the stack fails carefully analyze the errors and generate a clear explanation. Include the explanation into the summary
