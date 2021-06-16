#!/usr/bin/env python3.8
"""Amazon Lex CloudFormation Custom Resource Bot Version Manager"""

import logging
from time import sleep
from typing import Any, Dict, Optional, TYPE_CHECKING

import boto3

from .shared.api import get_api_parameters, wait_for_operation
from .shared.constants import DEFAULT_POLL_SLEEP_TIME_IN_SECS, DRAFT_VERSION

if TYPE_CHECKING:
    from mypy_boto3_lexv2_models import LexModelsV2Client
    from mypy_boto3_lexv2_models.type_defs import (
        CreateBotVersionResponseTypeDef,
        DeleteBotVersionResponseTypeDef,
    )
else:
    LexModelsV2Client = object
    CreateBotVersionResponseTypeDef = object
    DeleteBotVersionResponseTypeDef = object


class BotVersion:
    """Lex V2 CloudFormation Custom Resource Bot Version"""

    def __init__(
        self,
        client: Optional[LexModelsV2Client] = None,
        logger: Optional[logging.Logger] = None,
        poll_sleep_time_in_secs: int = DEFAULT_POLL_SLEEP_TIME_IN_SECS,
    ):
        self._client = client or boto3.client("lexv2-models")
        self._logger = logger or logging.getLogger(__name__)
        self._poll_sleep_time_in_secs = poll_sleep_time_in_secs

    def _wait_for_create_bot_version(
        self,
        operation_args: Dict[str, Any],
        max_tries: int = 5,
    ) -> None:
        try_count = 0
        while try_count < max_tries:
            try:
                wait_for_operation(
                    operation="describe_bot_version",
                    operation_args=operation_args,
                    status_key="botStatus",
                    wait_status=["Creating", "Versioning"],
                    target_status=["Available"],
                    client=self._client,
                    logger=self._logger,
                    poll_sleep_time_in_secs=self._poll_sleep_time_in_secs,
                )
                try_count = max_tries
            # operation may initially raise ResourceNotFoundException
            except self._client.exceptions.ResourceNotFoundException:
                self._logger.debug("bot version not found try count: %i", try_count)
                sleep(self._poll_sleep_time_in_secs)

            try_count = try_count + 1

    def _create_bot_version(
        self,
        input_parameters: Dict[str, Any],
    ) -> CreateBotVersionResponseTypeDef:
        operation = "CreateBotVersion"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.create_bot_version(**operation_parameters)
        self._logger.debug(response)

        return response

    def create_bot_version(
        self,
        resource_properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create Bot Version"""
        bot_id = resource_properties["botId"]
        bot_locale_ids = resource_properties["botLocaleIds"]
        last_updated_date_time = resource_properties["lastUpdatedDateTime"]

        bot_version_locale_specification = {
            locale_id: dict(sourceBotVersion=DRAFT_VERSION) for locale_id in bot_locale_ids
        }
        input_parameters = dict(
            botId=bot_id,
            description=f"Created by CloudFormation Custom Resource: {last_updated_date_time}",
            botVersionLocaleSpecification=bot_version_locale_specification,
        )

        response = self._create_bot_version(input_parameters=input_parameters)
        bot_id = response["botId"]
        bot_version = response["botVersion"]
        self._wait_for_create_bot_version(operation_args=dict(botId=bot_id, botVersion=bot_version))

        return dict(
            botId=bot_id,
            botVersion=bot_version,
        )

    def delete_bot_version(self, bot_id: str, bot_version: str) -> DeleteBotVersionResponseTypeDef:
        """Delete Bot Version"""
        operation = "DeleteBotVersion"
        input_parameters = dict(
            botId=bot_id,
            botVersion=bot_version,
            skipResourceInUseCheck=True,
        )
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        return self._client.delete_bot_version(**operation_parameters)

    def wait_for_delete_bot_alias(
        self,
        bot_id: str,
        bot_version: str,
    ) -> None:
        """Waits for bot version to be deleted"""
        try:
            operation_args = dict(botId=bot_id, botVersion=bot_version)
            wait_for_operation(
                operation="describe_bot_version",
                operation_args=operation_args,
                status_key="botStatus",
                wait_status=["Deleting"],
                # No target status - handle NotFound exception
                target_status=[""],
                client=self._client,
                logger=self._logger,
                poll_sleep_time_in_secs=self._poll_sleep_time_in_secs,
            )
        except self._client.exceptions.ResourceNotFoundException:
            self._logger.info(
                "Bot version does not exist - bot_id: %s - bot_version: %s",
                bot_id,
                bot_version,
            )
        except Exception as exception:
            self._logger.error(exception)
            raise RuntimeError from exception

        self._logger.info(
            "Successfully deleted Bot version with bot_id: %s - bot_version: %s",
            bot_id,
            bot_version,
        )
