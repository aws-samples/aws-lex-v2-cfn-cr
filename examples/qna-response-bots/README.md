This stack deploys 19 [Response Bots from QnABot](https://github.com/aws-samples/aws-ai-qna-bot/blob/master/templates/examples/examples/responsebots.js) in parallel.

The bot can be deployed using the
[AWS Serverless Application Model Command Line Interface (SAM CLI)](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html):

```bash
sam build --use-container
sam deploy --guided
```