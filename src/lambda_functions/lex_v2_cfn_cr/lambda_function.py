################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.          #
#                                                                              #
#  Licensed under the Apache License, Version 2.0 (the "License").             #
#  You may not use this file except in compliance with the License.            #
#  A copy of the License is located at                                         #
#                                                                              #
#      http://www.apache.org/licenses/LICENSE-2.0                              #
#                                                                              #
#  or in the 'license' file accompanying this file. This file is distributed   #
#  on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express  #
#  or implied. See the License for the specific language governing             #
#  permissions and limitations under the License.                              #
################################################################################
""" Lex V2 CloudFormation Custom Resource Lambda Handler"""

from os import getenv

from crhelper import CfnResource

# our own modules
# pylint: disable=import-error
from shared.client import get_client  # type: ignore
from shared.logger import get_logger, get_log_level  # type: ignore
from lex_v2_cfn_cr import LexV2CustomResource  # type: ignore # pylint: disable=no-name-in-module

# pylint: enable=import-error

LOGGER = get_logger(__name__)
HELPER = CfnResource(json_logging=True, log_level=get_log_level())

# global init code goes here so that it can pass failure in case
# of an exception
try:
    # boto3 client
    CLIENT = get_client("lexv2-models")

    # how long to wait between resource polling
    POLL_SLEEP_TIME_IN_SECS = int(getenv("POLL_SLEEP_TIME_IN_SECS", "5"))

    LEX_CUSTOM_RESOURCE = LexV2CustomResource(
        client=CLIENT,
        logger=LOGGER,
        poll_sleep_time_in_secs=POLL_SLEEP_TIME_IN_SECS,
    )
except Exception as exception:  # pylint: disable=broad-except
    HELPER.init_failure(exception)


def wait_for_bot_locales_build(bot_id, bot_locale_ids):
    """Waits for bot locales build"""
    # NOTE: not using the cr helper poller functionality since there's a 8K limit
    # in the CloudWatch Event input that it uses and medium size bots may trigger
    # it during updates as the payload includes JSON encoded current and old
    # resource properties
    try:
        LEX_CUSTOM_RESOURCE.build_bot_locales(
            bot_id=bot_id,
            bot_locale_ids=bot_locale_ids,
        )
    except Exception as exception:  # pylint: disable=broad-except
        HELPER.Status = "FAILED"
        HELPER.Reason = str(exception)
        HELPER.PhysicalResourceId = bot_id


@HELPER.create
def create_resource(event, _):
    """Create Resource"""
    resource_type = event["ResourceType"]
    resource_properties = event["ResourceProperties"]

    if resource_type == "Custom::LexBot":
        response = LEX_CUSTOM_RESOURCE.create_bot(resource_properties=resource_properties)
        HELPER.Data = response

        bot_id = response.get("botId")
        bot_locale_ids = response.get("botLocaleIds")
        _exception = response.get("_exception")
        if bot_id and _exception:
            # This allows to delete the bot if an exception was raised after
            # the bot was created. E.g. while creating the locale, intents, slot, etc.
            HELPER.Status = "FAILED"
            HELPER.Reason = _exception
            HELPER.PhysicalResourceId = bot_id
        else:
            wait_for_bot_locales_build(bot_id=bot_id, bot_locale_ids=bot_locale_ids)

        return bot_id

    if resource_type == "Custom::LexBotVersion":
        response = LEX_CUSTOM_RESOURCE.create_bot_version(resource_properties=resource_properties)
        HELPER.Data = response
        bot_version = response["botVersion"]

        return bot_version

    if resource_type == "Custom::LexBotAlias":
        response = LEX_CUSTOM_RESOURCE.create_bot_alias(resource_properties=resource_properties)
        HELPER.Data = response
        bot_alias_id = response["botAliasId"]

        return bot_alias_id

    raise RuntimeError(f"Invalid resource type: {resource_type}")


@HELPER.poll_delete
def poll_delete(event, _):
    """Poll Delete"""
    resource_type = event["ResourceType"]
    helper_data = event["CrHelperData"]

    if resource_type == "Custom::LexBot":
        bot_id = helper_data.get("botId")
        if bot_id:
            LEX_CUSTOM_RESOURCE.wait_for_delete_bot(bot_id=bot_id)

        return True

    if resource_type == "Custom::LexBotVersion":
        return True

    if resource_type == "Custom::LexBotAlias":
        bot_id = helper_data.get("botId")
        bot_alias_id = helper_data.get("botAliasId")
        if bot_id and bot_alias_id:
            LEX_CUSTOM_RESOURCE.wait_for_delete_bot_alias(bot_id=bot_id, bot_alias_id=bot_alias_id)
        return True

    raise RuntimeError(f"Invalid resource type: {resource_type}")


@HELPER.delete
def delete_resource(event, _):
    """Delete Resource"""
    resource_type = event["ResourceType"]
    resource_properties = event["ResourceProperties"]

    if resource_type == "Custom::LexBot":
        physical_resource_id = event.get("PhysicalResourceId", "")
        # Handle resource cancellation deletes during creation and cases where CloudFormation
        # passes a system generated PhysicalResourceId which is not a botId.
        # Valid Bot IDs are a fixed lenght of 10 alphanumeric characters:
        # https://docs.aws.amazon.com/lexv2/latest/dg/API_CreateBot.html#lexv2-CreateBot-response-botId
        if (
            not physical_resource_id
            or not physical_resource_id.isalnum()
            or len(physical_resource_id) != 10
        ):
            bot_name = resource_properties.get("botName", "")
            LOGGER.warning(
                "unable to find a valid Physical Resource ID - "
                "trying to obtain it from the resource properties botName: %s",
                bot_name,
            )
            bot_id = LEX_CUSTOM_RESOURCE.get_bot_id(bot_name=bot_name)
        else:
            bot_id = physical_resource_id

        HELPER.Data["botId"] = bot_id

        if bot_id:
            try:
                LEX_CUSTOM_RESOURCE.delete_bot(bot_id=bot_id)
            except CLIENT.exceptions.PreconditionFailedException:
                LOGGER.info("Bot does not exist - bot_id: %s", bot_id)

        return

    if resource_type == "Custom::LexBotVersion":
        # to be implemented - for now keeping versions
        # Use a deletion policy on the resource to avoid attempted deletions
        # on updates: DeletionPolicy: Retain
        return

    if resource_type == "Custom::LexBotAlias":
        bot_alias_id = event["PhysicalResourceId"]
        bot_id = resource_properties["botId"]
        HELPER.Data["botId"] = bot_id
        HELPER.Data["botAliasId"] = bot_alias_id

        if bot_alias_id and bot_id:
            try:
                LEX_CUSTOM_RESOURCE.delete_bot_alias(bot_id=bot_id, bot_alias_id=bot_alias_id)
            except CLIENT.exceptions.PreconditionFailedException:
                LOGGER.info(
                    "Bot alias does not exist - bot_id: %s - bot_alias_id: %s",
                    bot_id,
                    bot_alias_id,
                )

        return

    raise RuntimeError(f"Invalid resource type: {resource_type}")


@HELPER.update
def update_resource(event, _):
    """Update Resource"""
    resource_type = event["ResourceType"]
    resource_properties = event["ResourceProperties"]
    old_resource_properties = event["OldResourceProperties"]

    if resource_type == "Custom::LexBot":
        bot_id = event["PhysicalResourceId"]
        response = LEX_CUSTOM_RESOURCE.update_bot(
            bot_id=bot_id,
            resource_properties=resource_properties,
            old_resource_properties=old_resource_properties,
        )
        HELPER.Data = response

        bot_id = response.get("botId")
        bot_locale_ids = response.get("botLocaleIds")
        _exception = response.get("_exception")
        if bot_id and _exception:
            # This allows to delete the bot if an exception was raised after
            # the bot was created. E.g. while creating the locale, intents, slot, etc.
            HELPER.Status = "FAILED"
            HELPER.Reason = _exception
            HELPER.PhysicalResourceId = bot_id
        else:
            wait_for_bot_locales_build(bot_id=bot_id, bot_locale_ids=bot_locale_ids)

        return bot_id

    if resource_type == "Custom::LexBotVersion":
        # versions are immutable - a new one is created
        response = LEX_CUSTOM_RESOURCE.create_bot_version(resource_properties=resource_properties)
        HELPER.Data = response
        bot_version = response["botVersion"]

        return bot_version

    if resource_type == "Custom::LexBotAlias":
        bot_alias_id = event["PhysicalResourceId"]
        response = LEX_CUSTOM_RESOURCE.update_bot_alias(
            bot_alias_id=bot_alias_id,
            resource_properties=resource_properties,
            old_resource_properties=old_resource_properties,
        )
        HELPER.Data = response

        return response["botAliasId"]

    raise RuntimeError(f"Invalid resource type: {resource_type}")


def handler(event, context):
    """Lambda Handler"""
    HELPER(event, context)
