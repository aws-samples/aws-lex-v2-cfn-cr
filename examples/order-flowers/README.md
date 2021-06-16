This example template illustrates how to use the Custom Resource from a
stack deployed in your account. Once you have deployed the Custom Resource stack,
you can use the template in this folder to deploy the sample bot.

The bot can be deployed using the
[AWS Serverless Application Model Command Line Interface (SAM CLI)](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html):

```bash
sam build --use-container
sam deploy --guided
```