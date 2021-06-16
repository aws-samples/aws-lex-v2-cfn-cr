#!/usr/bin/env python3.8
"""Amazon Lex CloudFormation Custom Resource Bot Alias Manager"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

import boto3

from .shared.api import get_api_parameters, wait_for_operation
from .shared.constants import DEFAULT_POLL_SLEEP_TIME_IN_SECS

if TYPE_CHECKING:
    from mypy_boto3_lexv2_models import LexModelsV2Client
    from mypy_boto3_lexv2_models.type_defs import (
        CreateBotAliasResponseTypeDef,
        DeleteBotAliasResponseTypeDef,
        UpdateBotAliasResponseTypeDef,
    )
else:
    LexModelsV2Client = object
    CreateBotAliasResponseTypeDef = object
    DeleteBotAliasResponseTypeDef = object
    UpdateBotAliasResponseTypeDef = object


class BotAlias:
    """Lex V2 CloudFormation Custom Resource Bot Alias"""

    def __init__(
        self,
        client: Optional[LexModelsV2Client] = None,
        logger: Optional[logging.Logger] = None,
        poll_sleep_time_in_secs: int = DEFAULT_POLL_SLEEP_TIME_IN_SECS,
    ):
        self._client = client or boto3.client("lexv2-models")
        self._logger = logger or logging.getLogger(__name__)
        self._poll_sleep_time_in_secs = poll_sleep_time_in_secs

    def _wait_for_bot_alias(
        self,
        operation_args: Dict[str, Any],
    ) -> None:
        wait_for_operation(
            operation="describe_bot_alias",
            operation_args=operation_args,
            status_key="botAliasStatus",
            wait_status=["Creating"],
            target_status=["Available"],
            client=self._client,
            logger=self._logger,
            poll_sleep_time_in_secs=self._poll_sleep_time_in_secs,
        )

    def create_bot_alias(
        self,
        resource_properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create Bot Alias"""
        operation = "CreateBotAlias"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=resource_properties,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.create_bot_alias(**operation_parameters)
        self._logger.debug(response)

        bot_id = response["botId"]
        bot_alias_id = response["botAliasId"]
        self._wait_for_bot_alias(operation_args=dict(botId=bot_id, botAliasId=bot_alias_id))

        return dict(
            botId=bot_id,
            botAliasId=response["botAliasId"],
            botAliasName=response["botAliasName"],
            botVersion=response["botVersion"],
        )

    def delete_bot_alias(self, bot_id: str, bot_alias_id: str) -> DeleteBotAliasResponseTypeDef:
        """Delete Bot Alias"""
        operation = "DeleteBotAlias"
        input_parameters = dict(
            botId=bot_id,
            botAliasId=bot_alias_id,
            skipResourceInUseCheck=True,
        )
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        return self._client.delete_bot_alias(**operation_parameters)

    def update_bot_alias(
        self,
        bot_alias_id: str,
        resource_properties: Dict[str, Any],
        old_resource_properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update Bot Alias"""
        operation = "UpdateBotAlias"
        input_parameters = {"botAliasId": bot_alias_id, **resource_properties}
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )
        if resource_properties != old_resource_properties:
            self._logger.warning("resource_properties and old_resource_properties are identical")

        response = self._client.update_bot_alias(**operation_parameters)
        self._logger.debug(response)

        bot_id = response["botId"]
        bot_alias_id = response["botAliasId"]
        self._wait_for_bot_alias(operation_args=dict(botId=bot_id, botAliasId=bot_alias_id))

        return dict(
            botId=bot_id,
            botAliasId=response["botAliasId"],
            botAliasName=response["botAliasName"],
            botVersion=response["botVersion"],
        )

    def wait_for_delete_bot_alias(
        self,
        bot_id: str,
        bot_alias_id: str,
    ) -> None:
        """Waits for bot alias to be deleted"""
        try:
            operation_args = dict(botId=bot_id, botAliasId=bot_alias_id)
            wait_for_operation(
                operation="describe_bot_alias",
                operation_args=operation_args,
                status_key="botAliasStatus",
                wait_status=["Deleting"],
                # No target status - handle NotFound exception
                target_status=[""],
                client=self._client,
                logger=self._logger,
                poll_sleep_time_in_secs=self._poll_sleep_time_in_secs,
            )
        except self._client.exceptions.ResourceNotFoundException:
            self._logger.info(
                "Bot alias does not exist - bot_id: %s - bot_alias_id: %s",
                bot_id,
                bot_alias_id,
            )
        except Exception as exception:
            self._logger.error(exception)
            raise RuntimeError from exception

        self._logger.info(
            "Successfully deleted Bot alias with bot_id: %s - bot_alias_id: %s",
            bot_id,
            bot_alias_id,
        )
