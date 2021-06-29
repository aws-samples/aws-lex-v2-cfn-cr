# Amazon Lex V2 CloudFormation Custom Resource

> An Amazon Lex V2 CloudFormation [Custom Resource](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html)

## Quick Start

### Deploy Your Own Stack

Before you can use the Custom Resource, you need to deploy this project in your
AWS account. You can deploy this project using the
[AWS Serverless Application Repository (SAR)](https://aws.amazon.com/serverless/serverlessrepo/)
or using the [AWS Serverless Application Model Command Line Interface (SAM CLI)](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html).
Once you deploy it, you can reference the created Lambda function and IAM
role in your CloudFormation templates. See the [Usage](#usage) section below
for details on how to use the Custom Resources.

Deployment options:

1. Using SAR:

    You can deploy this project with this AWS Console
    [one click link](https://console.aws.amazon.com/lambda/home#/create/app?applicationId=arn:aws:serverlessrepo:us-east-1:777566285978:applications/lex-v2-cfn-cr).

    **Alternatively**, you can directly embed the SAR application as a nested
    stack in your CloudFormation template. See the following snippet or the
    [examples/zip-code](examples/zip-code) directory for a template that uses
    this nested stack approach.

    **NOTE:** Deploying the stack with the one click SAR link above is preferred
    over using the nested stack in cases where you want a single instance of the
    Custom Resource Lambda function to be shared between stacks to avoid
    duplication.

    ```yaml
    Resources:
      # This deploys the Custom Resource as a nested CloudFormation stack
      # The Custom Resource is provisioned with your bot. However, the Custom
      # Resource becomes dedicated and should not be shared with other stacks
      # as it gets deleted when you delete your stack
      LexV2CfnCr:
        Type: AWS::Serverless::Application
        Properties:
          Location:
            ApplicationId: arn:aws:serverlessrepo:us-east-1:777566285978:applications/lex-v2-cfn-cr
            SemanticVersion: 0.2.0
          Parameters:
            # Custom Resource Lambda log level
            LogLevel: 'INFO'

      LexBot:
        Type: Custom::LexBot
        Properties:
          # this references the Lambda function created by the Custom Resource stack above.
          # Note that it uses the Outputs of the nested stack
          ServiceToken: !GetAtt LexV2CfnCr.Outputs.LexV2CfnCrFunctionArn
          botName: My Bot
          # ...
          # See the example in the examples/zip-code directory for a full template
          # that uses this approach
    ```

2. Using the SAM CLI:

   Clone this repo and issue the following commands from a host with the sam cli:

    ```bash
    sam build --use-container
    sam deploy --guided
    ```

   See the [examples/order-flowers](examples/order-flowers) directory for a
   template that illustrates how to use this approach. See the [Development](#development) section below for more details.

### Usage

Once you have deployed the Custom Resource stack as described above, you are
ready to use it in your own CloudFormation templates. There are three Custom
Resources that work together:

1. **LexBot:** Deploys a Lex bot including associated subresources: locales,
   slot types, intents and slots. These subresources are managed as a unit with
   the bot so everything is managed from a single resource. CloudFormation
   changes are done to the `DRAFT` version of the bot. The Custom Resource
   automatically builds all locales after successful CloudFormation deployments
2. **LexBotVersion:** Creates immutable bot versions from the bot `DRAFT`
   version
3. **LexBotAlias:** Provisions and manages a bot alias that is pointed to a
   version

The snippett below shows an example of how to use these Custom Resources
in your CloudFormation templates:

```yaml
Parameters:
  # add a parameter to your bot template to reference the Custom Resource stack
  LexV2CfnCrStackName:
    Description: >-
      Existing Lex V2 Custom Resource Stack Name. This is used to import the
      Lambda function and IAM role provisioned by the Custom Resource stack
    Type: String
    # If you deployed via the SAR Console and used the defaults, your stack
    # will be named serverlessrepo-lex-v2-cfn-cr. If you deployed manually,
    # make it match the name of your Custom Resource stack
    Default: serverlessrepo-lex-v2-cfn-cr

Resources:
  # LexBot resource contains the bot definition and subresources including:
  # locales, slot types, intents and slots. These subresources use custom
  # attributes with a name prefix: CR.<subresource name>
  # The changes are done to the DRAFT version of the bot.
  # All locales are automatically built
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
    # Bot versions are deleted by the Bot on Stack deletions. This deletion
    # policy speeds up deletes
    DeletionPolicy: Retain
    # Version number changes between updates which cause a CloudFormation
    # delete event since the version number is the physical resource ID.
    # The following policies prevents deletion events to retain the bot versions
    # and speed up updates
    UpdateReplacePolicy: Retain
    Type: Custom::LexBotVersion
    Properties:
      ServiceToken:
        !ImportValue
          Fn::Sub: "${LexV2CfnCrStackName}-LexV2CfnCrFunctionArn"
      # Bot Version level attributes
      # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lexv2-models.html#LexModelsV2.Client.create_bot_version
      botId: !Ref LexBot
      # botVersionLocaleSpecification is derived from the bot locales
      # this controls which locales are added to the version
      CR.botLocaleIds: !GetAtt LexBot.botLocaleIds
      # lastUpdatedDateTime is used to detect changes in the bot
      CR.lastUpdatedDateTime: !GetAtt LexBot.lastUpdatedDateTime

  # Provisions a Bot Alias that points to a version
  LexBotAlias:
    # Bot aliases are deleted by the Bot on Stack deletions. This deletion
    # policy speeds up deletes
    DeletionPolicy: Retain
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
      # enable locales under this alias
      botAliasLocaleSettings:
        en_US:
          enabled: True

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

Generally, the Custom Resources proxy the requests to the corresponding
Create/Update/Delete operations of the Lex V2 Models API using boto3.
For details, see the
[boto3 Lex V2 Models reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lexv2-models.html)

Some attributes of the custom resources use the prefix `CR.` as a marker for
subresources (e.g. locales, slot types, intents, slots).
It is also used for cases where the underlying API requires an ID that needs to
be dynamically resolved and for custom attributes that are not part of the
Lex APIS.

## Caveats

- CloudFormation Updates and creation events must complete within the Lambda
  limit of 15 minutes. This also includes building the Bot locales. This is
  enough time for the vast majority of bots. The poller functionality of the
  CrHelper library is not used to extend this time since larger bot definitions
  can trigger a 8KB limit in the CloudWatch Events input payload
- If a bot fails to build during a deployment, it may not be able to
  automatically roll back the `DRAFT` version. In that case, you may need to
  restore the `DRAFT` version manually and rebuild before you can update with
  CloudFormation again. You can also use the Lex export functionality to an get
  an existing working bot version and restore it into the current `DRAFT`
  using the Lex import functionality
- A default fallback intent will be automatically created per locale when you
  initially deploy the bot. This default fallback intent cannot be modified
  with this Custom Resource
- Lex Bot Resource Policies are not implemented

## Development

### Deploy Using SAM

The deployment of this project uses the [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html).

The SAM CLI is an extension of the AWS CLI that adds functionality for
building and testing Lambda applications. It uses Docker to run your functions
in an Amazon Linux environment that matches Lambda.

To use the SAM CLI, you need the following tools.

- SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- [Python 3 installed](https://www.python.org/downloads/)
- Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

To build and deploy your application for the first time, run the following in your shell:

```bash
sam build --use-container
sam deploy --guided
```

The first command will build the source of your application. The second command will package and deploy your application to AWS, with a series of prompts:

- **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
- **AWS Region**: The AWS region you want to deploy your app to.
- **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
- **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modifies IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
- **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.

### Development Environment Setup

This project is developed and tested on Amazon Linux 2 using AWS Cloud9:

- Bash 4.2
- Python 3.8
- Python requirements listed in the
  [requirements/requirements-build.txt](requirements/requirements-build.txt) and
  [requirements/requirements-dev.txt](requirements/requirements-dev.txt) files
- AWS SAM CLI ~= 1.24.0
- Docker >= 20
- GNU make >= 3.82

This project contains a [Makefile](Makefiles) that can be optionally used to
facilitate tasks such as:

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

   ```bash
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

5. Publish to SAR:

    ```bash
    make publish
    ```

6. Delete the stack:

    ```bash
    make delete-stack
    ```

### SAM Local Invoke

To invoke local functions with an event file:

```bash
make test-local-invoke
EVENT_FILE=tests/events/lex_v2_cfn_cr/create-bot.json make local-invoke-lex_v2_cfn_cr
```

#### SAM Local Invoke Debug Lambda Functions

 To interactively debug inside the SAM container running a Lambda function put
 `debugpy` as a dependency in the `requirements.txt` file under the function directory. That allows to attach a Python debugger to the Lambda function.

 To debug using Visual Studio Code, create a launch task to attach to the
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
 `lex_v2_cfn_cr` function, run the following command (requires debugpy in the
 function requirements.txt folder):

```shell
DEBUGGER=true EVENT_FILE=tests/events/lex_v2_cfn_cr/create-bot.json make local-invoke-lex_v2_cfn_cr
```

### Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

## Cleanup

To delete this application, you can use the AWS CLI:

  ```bash
  aws cloudformation delete-stack --stack-name '<cloudformation-stack-name>'
  ```

 Or [delete the stack using the AWS CloudFormation Console](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-delete-stack.html)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
