#!/usr/bin/env python3.8
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
"""Amazon Lex CloudFormation Custom Resource Bot Manager Module"""

from datetime import datetime
import logging
from time import sleep
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import boto3

from .shared.constants import (
    CUSTOM_ATTRIBUTES,
    DEFAULT_POLL_SLEEP_TIME_IN_SECS,
    DRAFT_VERSION,
)

from .locale import Locale
from .shared.api import get_api_parameters, wait_for_operation

if TYPE_CHECKING:
    from mypy_boto3_lexv2_models import LexModelsV2Client
    from mypy_boto3_lexv2_models.type_defs import (
        CreateBotLocaleResponseTypeDef,
        CreateIntentResponseTypeDef,
        CreateSlotResponseTypeDef,
        CreateSlotTypeResponseTypeDef,
        DeleteBotLocaleResponseTypeDef,
        UpdateBotLocaleResponseTypeDef,
        UpdateIntentResponseTypeDef,
        UpdateSlotResponseTypeDef,
        UpdateSlotTypeResponseTypeDef,
    )
else:
    LexModelsV2Client = object
    CreateBotLocaleResponseTypeDef = object
    CreateIntentResponseTypeDef = object
    CreateSlotResponseTypeDef = object
    CreateSlotTypeResponseTypeDef = object
    DeleteBotLocaleResponseTypeDef = object
    UpdateBotLocaleResponseTypeDef = object
    UpdateIntentResponseTypeDef = object
    UpdateSlotResponseTypeDef = object
    UpdateSlotTypeResponseTypeDef = object


class Bot:
    """Lex V2 CloudFormation Custom Resource Bot"""

    def __init__(
        self,
        client: Optional[LexModelsV2Client] = None,
        logger: Optional[logging.Logger] = None,
        poll_sleep_time_in_secs=DEFAULT_POLL_SLEEP_TIME_IN_SECS,
    ):
        self._client = client or boto3.client("lexv2-models")
        self._logger = logger or logging.getLogger(__name__)
        self._poll_sleep_time_in_secs = poll_sleep_time_in_secs

        self._locale_manager = Locale(
            client=self._client,
            logger=self._logger,
        )

    def _build_bot_locale(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        max_retries: int = 3,
    ) -> None:
        # Note that the boto3 client is configured using "standard" retry mode (see client.py)
        # It provides 3 retries at the client level.
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html#standard-retry-mode
        # The retries in the loop below are in addition to the retries at the client level.
        # The retry loop below is meant to work around concurrent build limits (5)
        retry_count = 0
        sleep_retry = self._poll_sleep_time_in_secs
        while retry_count < max_retries:
            try:
                response = self._client.build_bot_locale(
                    botId=bot_id, botVersion=bot_version, localeId=locale_id
                )
                self._logger.debug(response)
                break
            except self._client.exceptions.ThrottlingException as exception:
                retry_count = retry_count + 1
                if retry_count >= max_retries:
                    raise exception

                self._logger.warning(
                    "build request throttled - sleeping for %i seconds - retry count: %i - "
                    "exception: %s",
                    sleep_retry,
                    retry_count,
                    exception,
                )
                sleep(sleep_retry)
                # exponentially increase sleep time
                sleep_retry = int(sleep_retry ** retry_count)

    def _create_bot(self, resource_properties: Dict[str, Any]) -> str:
        operation = "CreateBot"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=resource_properties,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.create_bot(**operation_parameters)
        self._logger.debug(response)
        bot_id = response["botId"]

        self._wait_for_create_bot(operation_args=dict(botId=bot_id))

        return bot_id

    def _create_bot_locales(self, bot_id: str, bot_locales: List[Dict[str, Any]]) -> None:
        for bot_locale in bot_locales:
            input_parameters = {
                "botId": bot_id,
                "botVersion": DRAFT_VERSION,
                **bot_locale,
            }
            self._locale_manager.create_bot_locale(input_parameters=input_parameters)

    def _create_or_update_existing_bot_locales(
        self,
        bot_id: str,
        bot_locales: List[Dict[str, Any]],
        old_bot_locales: List[Dict[str, Any]],
    ) -> None:
        bot_locales_to_update: List[Dict[str, Any]] = []
        bot_locales_to_create: List[Dict[str, Any]] = []
        existing_bot_locale_ids: List[str] = []

        list_bot_locales_args: Dict[str, Any] = dict(
            botId=bot_id,
            botVersion=DRAFT_VERSION,
        )
        while True:
            response = self._client.list_bot_locales(
                **list_bot_locales_args,
            )
            self._logger.debug(response)

            existing_bot_locale_ids.extend(
                [l_s["localeId"] for l_s in response["botLocaleSummaries"]]
            )
            next_token = response.get("nextToken")

            if next_token:
                list_bot_locales_args["nextToken"] = next_token
            else:
                break

        for bot_locale in bot_locales:
            bot_locale_id = bot_locale["localeId"]
            if bot_locale_id in existing_bot_locale_ids:
                bot_locales_to_update.append(bot_locale)
            else:
                bot_locales_to_create.append(bot_locale)

        if bot_locales_to_update:
            self._update_existing_bot_locales(
                bot_id=bot_id,
                bot_locales=bot_locales_to_update,
                old_bot_locales=old_bot_locales,
            )

        if bot_locales_to_create:
            self._create_bot_locales(bot_id=bot_id, bot_locales=bot_locales_to_create)

    def _delete_bot_locales(self, bot_id: str, bot_locales: List[Dict[str, Any]]) -> None:
        bot_locale_ids = [locale["localeId"] for locale in bot_locales]

        for locale_id in bot_locale_ids:
            input_parameters = {
                "botId": bot_id,
                "botVersion": DRAFT_VERSION,
                "localeId": locale_id,
            }

            try:
                self._locale_manager.delete_bot_locale(input_parameters=input_parameters)
            except self._client.exceptions.PreconditionFailedException:
                self._logger.info(
                    "Bot locale does not exist - bot_id: %s - locale_id: %s",
                    bot_id,
                    locale_id,
                )

    def _update_bot(
        self,
        bot_id: str,
        resource_properties: Dict[str, Any],
        old_resource_properties: Dict[str, Any],
    ) -> str:
        operation = "UpdateBot"

        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters={"botId": bot_id, **resource_properties},
            client=self._client,
            logger=self._logger,
            # bot tags are not a valid parameter in updates
            extra_parameter_to_ignore=["botTags"],
        )
        old_operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters={"botId": bot_id, **old_resource_properties},
            client=self._client,
            logger=self._logger,
            extra_parameter_to_ignore=["botTags"],
        )

        if operation_parameters != old_operation_parameters:
            response = self._client.update_bot(**operation_parameters)
            self._logger.debug(response)

            self._wait_for_create_bot(operation_args=dict(botId=bot_id))

        return bot_id

    def _update_bot_locales(
        self,
        bot_id: str,
        resource_properties: Dict[str, Any],
        old_resource_properties: Dict[str, Any],
    ) -> List[str]:
        new_locales = resource_properties[CUSTOM_ATTRIBUTES["botLocales"]]
        old_locales = old_resource_properties[CUSTOM_ATTRIBUTES["botLocales"]]

        new_locale_ids = {locale["localeId"] for locale in new_locales}
        old_locale_ids = {locale["localeId"] for locale in old_locales}

        locale_ids_to_add = new_locale_ids.difference(old_locale_ids)
        locales_to_add = [
            locale for locale in new_locales if locale["localeId"] in locale_ids_to_add
        ]

        locale_ids_to_delete = old_locale_ids.difference(new_locale_ids)
        locales_to_delete = [
            locale for locale in old_locales if locale["localeId"] in locale_ids_to_delete
        ]

        locale_ids_to_update = new_locale_ids.intersection(old_locale_ids)
        locales_to_update_new = {
            locale["localeId"]: locale
            for locale in new_locales
            if locale["localeId"] in locale_ids_to_update
        }
        locales_to_update_old = {
            locale["localeId"]: locale
            for locale in old_locales
            if locale["localeId"] in locale_ids_to_update
        }
        locales_to_update = [
            locales_to_update_new[locale_id]
            for locale_id in locales_to_update_new
            if locales_to_update_new[locale_id] != locales_to_update_old[locale_id]
        ]

        if locales_to_add or locales_to_update:
            self._create_or_update_existing_bot_locales(
                bot_id=bot_id,
                bot_locales=[*locales_to_add, *locales_to_update],
                old_bot_locales=old_locales,
            )
        if locales_to_delete:
            self._delete_bot_locales(bot_id=bot_id, bot_locales=locales_to_delete)

        return [
            *locale_ids_to_add,
            *locale_ids_to_update,
        ]

    def _update_existing_bot_locales(
        self,
        bot_id: str,
        bot_locales: List[Dict[str, Any]],
        old_bot_locales: List[Dict[str, Any]],
    ) -> None:
        # pylint: disable=too-many-locals
        for bot_locale in bot_locales:
            locale_id = bot_locale["localeId"]
            old_bot_locale_match = [
                o_b_l for o_b_l in old_bot_locales if o_b_l["localeId"] == locale_id
            ]
            if old_bot_locale_match:
                old_bot_locale = old_bot_locale_match[0]
            else:
                continue

            if old_bot_locale != bot_locale:
                self._locale_manager.update_bot_locale(
                    bot_id=bot_id,
                    bot_locale=bot_locale,
                    old_bot_locale=old_bot_locale,
                )

    def _wait_for_build_bot_locale(
        self,
        operation_args: Dict[str, Any],
    ) -> None:
        wait_for_operation(
            operation="describe_bot_locale",
            operation_args=operation_args,
            status_key="botLocaleStatus",
            wait_status=["Building", "ReadyExpressTesting"],
            target_status=["Built"],
            client=self._client,
            logger=self._logger,
            poll_sleep_time_in_secs=self._poll_sleep_time_in_secs,
        )

    def _wait_for_create_bot(
        self,
        operation_args: Dict[str, Any],
    ) -> None:
        wait_for_operation(
            operation="describe_bot",
            operation_args=operation_args,
            status_key="botStatus",
            wait_status=["Creating"],
            target_status=["Available"],
            client=self._client,
            logger=self._logger,
            poll_sleep_time_in_secs=self._poll_sleep_time_in_secs,
        )

    def build_bot_locales(
        self,
        bot_id: str,
        bot_locale_ids: List[str],
        bot_version: str = DRAFT_VERSION,
        max_concurrent_builds: int = 5,
    ):
        """Build the Lex Bot Locales"""
        for i in range(0, len(bot_locale_ids), max_concurrent_builds):
            locale_ids_to_build = bot_locale_ids[i : i + max_concurrent_builds]  # noqa: E203
            for locale_id in locale_ids_to_build:
                self._build_bot_locale(
                    bot_id=bot_id,
                    bot_version=bot_version,
                    locale_id=locale_id,
                )

            for locale_id in locale_ids_to_build:
                self._wait_for_build_bot_locale(
                    operation_args=dict(
                        botId=bot_id,
                        botVersion=bot_version,
                        localeId=locale_id,
                    ),
                )

    def create_bot(self, resource_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create Lex V2 Bot"""
        bot_id = self._create_bot(resource_properties=resource_properties)

        locale_exeption = {"_exception": ""}
        bot_locale_ids = []
        try:
            bot_locales = resource_properties[CUSTOM_ATTRIBUTES["botLocales"]]
            self._create_bot_locales(
                bot_id=bot_id,
                bot_locales=bot_locales,
            )
            bot_locale_ids = [locale["localeId"] for locale in bot_locales]
        except Exception as exception:  # pylint: disable=broad-except
            self._logger.error("failed to create locale: %s", exception)
            locale_exeption["_exception"] = str(exception)

        return {
            "botId": bot_id,
            "botLocaleIds": bot_locale_ids,
            "lastUpdatedDateTime": datetime.now().isoformat(),
            **locale_exeption,
        }

    def delete_bot(self, bot_id: str) -> None:
        """Delete Bot"""
        operation = "DeleteBot"
        input_parameters = dict(
            botId=bot_id,
            skipResourceInUseCheck=True,
        )
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        self._client.delete_bot(**operation_parameters)

    def get_bot_id(
        self,
        bot_name: str,
    ) -> str:
        """Get Bot ID from a Bot Name"""
        list_bots_args: Dict[str, Any] = dict(
            filters=[
                {
                    "name": "BotName",
                    "values": [bot_name],
                    "operator": "EQ",
                }
            ],
            sortBy={
                "attribute": "BotName",
                "order": "Ascending",
            },
        )
        while True:
            response = self._client.list_bots(**list_bots_args)
            self._logger.debug(response)

            bot_summaries = response["botSummaries"]
            bot_id = bot_summaries[0]["botId"] if bot_summaries else ""

            if bot_id:
                break

            next_token = response.get("nextToken")
            if next_token:
                list_bots_args["nextToken"] = next_token
            else:
                break

        if not bot_id:
            self._logger.warning("could not find bot named: %s", bot_name)

        return bot_id

    def update_bot(
        self,
        bot_id: str,
        resource_properties: Dict[str, Any],
        old_resource_properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update Lex V2 Bot"""

        _bot_id = self._update_bot(
            bot_id=bot_id,
            resource_properties=resource_properties,
            old_resource_properties=old_resource_properties,
        )

        locale_exeption = {"_exception": ""}
        bot_locale_ids = []
        try:
            bot_locale_ids = self._update_bot_locales(
                bot_id=_bot_id,
                resource_properties=resource_properties,
                old_resource_properties=old_resource_properties,
            )
        except Exception as exception:  # pylint: disable=broad-except
            self._logger.error("failed to create locale: %s", exception)
            locale_exeption["_exception"] = str(exception)

        return {
            "botId": _bot_id,
            "botLocaleIds": bot_locale_ids,
            "lastUpdatedDateTime": datetime.now().isoformat(),
            **locale_exeption,
        }

    def wait_for_delete_bot(
        self,
        bot_id: str,
    ) -> None:
        """Waits for bot to be deleted"""
        try:
            operation_args = dict(botId=bot_id)
            wait_for_operation(
                operation="describe_bot",
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
            self._logger.info("Bot does not exist - bot_id: %s", bot_id)
        except Exception as exception:
            self._logger.error(exception)
            raise RuntimeError from exception

        self._logger.info("Successfully deleted Bot with bot_id: %s", bot_id)
