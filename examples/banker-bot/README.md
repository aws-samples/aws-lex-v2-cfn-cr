This example deploys a Banker Bot based on the [Lex V2 Workshop](https://amazonlex.workshop.aws/)
which showcases various Lex V2 capabilities.

The template shows how to attach a [Lambda Fulfillment Code Hook](https://docs.aws.amazon.com/lexv2/latest/dg/lambda.html)
and how to configure [Text Conversation Logs](https://docs.aws.amazon.com/lexv2/latest/dg/conversation-logs-configure.html)

Before you use this example, you should deploy the Custom Resource stack
in your AWS account. The Custom Resource stack name is passed as a parameter
when deploying this example. This stack name parameter is used to import the
values of the Lambda function and the IAM role created by the Custom Resource.

The bot in this example can be deployed using the
[AWS Serverless Application Model Command Line Interface (SAM CLI)](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html):

```bash
sam build --use-container
sam deploy --guided
```
