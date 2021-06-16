# Amazon Lex V2 CloudFormation Custom Resource

> An Amazon Lex V2 CloudFormation [Custom Resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html)

## Quick Start

### Deploy Your Own Stack
There are two ways to deploy this project:

1. Using the [AWS Serverless Application Repository (SAR)](https://aws.amazon.com/serverless/serverlessrepo/)
  to deploy a pre-built version from the AWS Console.
  **TBD**: link to SAR project
  **INTERNAL NOTE (REMOVE):** The current template uses an IAM Service Linked Role.
  Currently, this resource type is not in the
  [list of supported resources](https://docs.aws.amazon.com/serverlessrepo/latest/devguide/list-supported-resources.html).
  There is a [request](https://t.corp.amazon.com/V381564301/overview)
  to allow-list this resource type which is in progress. We may temporarily
  change it to a regular IAM role if needed.

2. Using the [AWS Serverless Application Model Command Line Interface (SAM CLI)](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html)
to build and deploy from an Unix like shell:

```bash
sam build --use-container
sam deploy --guided
```

### Usage

There are three Custom Resources that work together:

1. **LexBot:** Deploys a Lex bot incuding associated locales, slot types,
   intents and slots. Updates are done to the DRAFT version.  It builds all
   locales after creation/updates
2. **LexBotVersion:** Creates immutable bot versions from the DRAFT version
3. **LexBotAlias:** Provisions and manages a bot alias that is pointed to a
   version

The snippett below shows an example of how to use this Custom Resource
in your CloudFormation templates after your deploy this application.

Generally, the Custom Resource proxies the requests to the corresponding
Create/Update/Delete operations of the Lex V2 Models API using boto3.
For details, see the [boto3 Lex V2 Models reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lexv2-models.html)

Note that the attributes with the prefix `CR.` are used as a marker for
subresources and for cases where the underlying API requires an ID that needs
to be dynamically resolved.

```yaml
Parameters:
  LexV2CfnCrStackName:
    Description: >-
      Lex V2 Custom Resource Stack Name. This is used to import the Lambda
      function and IAM role provisioned by the Custom Resource stack
    Type: String
    Default: lex-v2-cfn-cr

Resources:
  # LexBot resource contains bot definition including locales, slot types,
  # intents and slots. This is deployed to the DRAFT version of the bot
  # and all locales are built
  LexBot:
    Type: Custom::LexBot
    Properties:
      ServiceToken:
        # Points to the Custom Resource Lambda function
        !ImportValue
          Fn::Sub: "${LexV2CfnCrStackName}-LexV2CfnCrFunctionArn"
      # Bot level attributes
      # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lexv2-models.html#LexModelsV2.Client.create_bot
      botName:
        ZipCodeUpdateBot
      dataPrivacy:
        childDirected: True
      description: Test bot deployed using CloudFormation Custom Resource
      idleSessionTTLInSeconds: 300
      roleArn:
        # Points to the Custom Resource IAM Service Linked role
        !ImportValue
          Fn::Sub: "${LexV2CfnCrStackName}-LexServiceLinkedRole"
      # List of Bot Locale definitions. Requires one or more locales
      CR.botLocales:
        # Locale level attributes
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lexv2-models.html#LexModelsV2.Client.create_bot_locale
        - localeId: en_US
          nluIntentConfidenceThreshold: 0.40
          voiceSettings:
            voiceId: Salli
          # List of optional Slot Type definitions
          CR.slotTypes:
            # Slot Type level attributes
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lexv2-models.html#LexModelsV2.Client.create_slot_type
            - slotTypeName: ZipCodeType
              parentSlotTypeSignature: AMAZON.AlphaNumeric
              valueSelectionSetting:
                resolutionStrategy: OriginalValue
                regexFilter:
                  pattern: '[0-9]{8}'
          # List of Intent definitions. Requires one or more Intents
          CR.intents:
              # Intent level attributes
              # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lexv2-models.html#LexModelsV2.Client.create_intent
            - intentName: UpdateZipCode
              sampleUtterances:
                - utterance: i want to change my zip code
                - utterance: i have a new zip code
                - utterance: my new zip code is {ZipCode}
               # List of optional Slot definitions. Defined in order of slot priority
              CR.slots:
                # Slot level attributes
                # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lexv2-models.html#LexModelsV2.Client.create_slot
                - slotName: ZipCode
                  # Slot Type Name is used to dyanmically resolve the ID of the
                  # associated Slot Type defined above
                  CR.slotTypeName: ZipCodeType
                  valueElicitationSetting:
                    slotConstraint: Required
                    promptSpecification:
                      messageGroups:
                        - message:
                            plainTextMessage:
                              value: What is your zipcode?
                      maxRetries: 2
                      allowInterrupt: true

  # Creates an immutable Bot Version
  LexBotVersion:
    # Version changes between updates which cause a CloudFormation delete event
    # The following policies prevent deletions
    DeletionPolicy: Retain
    UpdateReplacePolicy: Retain
    Type: Custom::LexBotVersion
    Properties:
      ServiceToken:
        !ImportValue
          Fn::Sub: "${LexV2CfnCrStackName}-LexV2CfnCrFunctionArn"
      # Bot Version level attributes
      # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lexv2-models.html#LexModelsV2.Client.create_bot_version
      botId: !Ref LexBot
      botLocaleIds: !GetAtt LexBot.botLocaleIds
      # lastUpdatedDateTime is used to detect changes in the bot
      lastUpdatedDateTime: !GetAtt LexBot.lastUpdatedDateTime

  # Provisions a Bot Alias that points to a version
  LexBotAlias:
    Type: Custom::LexBotAlias
    Properties:
      ServiceToken:
        !ImportValue
          Fn::Sub: "${LexV2CfnCrStackName}-LexV2CfnCrFunctionArn"
      # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lexv2-models.html#LexModelsV2.Client.create_bot_alias
      botId: !Ref LexBot
      botAliasName: live
      # points to the latest version of the resource above
      botVersion: !Ref LexBotVersion

Outputs:
  LexBotId:
    Description: Lex Bot ID
    Value: !Ref LexBot

  LexBotLocaleIds:
    Description: Lex Bot Locale IDs
    Value: !Join [",", !GetAtt LexBot.botLocaleIds]

  LexBotLatestVersion:
    Description: Latest Lex Bot Version ID
    Value: !Ref LexBotVersion

  LexBotAliasId:
    Description: Lex Bot Alias ID
    Value: !Ref LexBotAlias
```

## Caveats
- If a bot fails to build during a deployment, it may not be able to
  automatically roll back the DRAFT version. In that case, you may need to
  restore the DRAFT version manually or from an existing working version (using
  export/import).
- Lex Bot Resource Policies are not implemented
- Creation and update of the default fallback intent is not supported

## Development

### Deploy Using SAM

The deployment of this project uses the [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html).

The SAM CLI is an extension of the AWS CLI that adds functionality for
building and testing Lambda applications. It uses Docker to run your functions
in an Amazon Linux environment that matches Lambda.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

To build and deploy your application for the first time, run the following in your shell:

```bash
sam build --use-container
sam deploy --guided
```

The first command will build the source of your application. The second command will package and deploy your application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
* **AWS Region**: The AWS region you want to deploy your app to.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modifies IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.

## Development
This project is developed and tested on Amazon Linux 2 using AWS Cloud9:
- Bash 4.2
- Python 3.8
- Python requirements listed in the
  [requirements/requirements-build.txt](requiremetns/requirements-build.txt) and
  [requirements/requirements-dev.txt](requiremetns/requirements-dev.txt) files
- AWS SAM CLI ~= 1.24.0
- Docker >= 20
- GNU make >= 3.82

This project contains a [Makefile](Makefiles) that can be optionally used to
falicilitate tasks such as:

1. Create a python virtual environment and install the required dependencies:

    ```bash
    make install
    ```

2. Build the project

    ```bash
    make build
    ```

3. Deploy the stack:

   Before deploying for the first time, you may need to configure your deployment
   settings using:

   ```
   sam deploy --guided
   ```

   Alternatively, you can edit the [samconfig.toml](samconfig.toml) file to
   configure your deployment values.

   After that initial setup, you can deploy using:

    ```bash
    make deploy
    ```

4. Run linters on the source code:

    ```bash
    make lint
    ```

### SAM Local Invoke

To invoke local functions with an event file:

```bash
make test-local-invoke
EVENT_FILE=tests/events/lex_v2_cfn_cr/create-bot.json make local-invoke-lex_v2_cfn_cr
```

#### SAM Local Invoke Debug Lambda Functions

 To debug inside the container running a Lambda function put `debugpy` as a
 dependency in the function `requirements.txt` under the funtion directory.

 To debug using Visual Studio Code, cretate a launch task to attach to the
 debugger (example found in the [launch.json](.vscode/launch.json) file under the
 .vscode directory):
 ```json
      {
          "name": "Debug SAM Lambda debugpy attach",
          "type": "python",
          "request": "attach",
          "port": 5678,
          "host": "localhost",
          "pathMappings": [
              {
                  "localRoot": "${workspaceFolder}/${relativeFileDirname}",
                  "remoteRoot": "/var/task"
              }
          ],
      }
  ```

 Set the `DEBUGGER` environmental variable. For example, to debug the
 `incoming_process` function, run the following command:

```shell
DEBUGGER=true EVENT_FILE=tests/events/lex_v2_cfn_cr/create-bot.json make local-invoke-lex_v2_cfn_cr
```

## Cleanup

To delete this application, use the AWS CLI.

  ```bash
  aws cloudformation delete-stack --stack-name '<cloudformation-stack-name>'
  ```

 Or [delete the stack using the AWS CloudFormation Console](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-delete-stack.html)

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.
