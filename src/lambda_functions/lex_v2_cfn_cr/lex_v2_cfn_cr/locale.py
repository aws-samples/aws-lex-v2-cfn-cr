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
"""Amazon Lex CloudFormation Custom Resource Locale Manager"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import boto3

from .slot_type import SlotType
from .intent import Intent
from .shared.api import get_api_parameters, wait_for_operation
from .shared.constants import (
    CUSTOM_ATTRIBUTES,
    DEFAULT_POLL_SLEEP_TIME_IN_SECS,
    DRAFT_VERSION,
)

if TYPE_CHECKING:
    from mypy_boto3_lexv2_models import LexModelsV2Client
    from mypy_boto3_lexv2_models.type_defs import (
        CreateBotLocaleResponseTypeDef,
        DeleteBotLocaleResponseTypeDef,
        UpdateBotLocaleResponseTypeDef,
    )
else:
    LexModelsV2Client = object
    CreateBotLocaleResponseTypeDef = object
    DeleteBotLocaleResponseTypeDef = object
    UpdateBotLocaleResponseTypeDef = object


class Locale:
    """Lex V2 CloudFormation Custom Resource Locale"""

    def __init__(
        self,
        client: Optional[LexModelsV2Client] = None,
        logger: Optional[logging.Logger] = None,
        poll_sleep_time_in_secs=DEFAULT_POLL_SLEEP_TIME_IN_SECS,
    ):
        self._client = client or boto3.client("lexv2-models")
        self._logger = logger or logging.getLogger(__name__)
        self._poll_sleep_time_in_secs = poll_sleep_time_in_secs

        self._slot_type_manager = SlotType(
            client=self._client,
            logger=self._logger,
        )
        self._intent_manager = Intent(
            client=self._client,
            logger=self._logger,
        )

    def _create_bot_locale(
        self, input_parameters: Dict[str, Any]
    ) -> CreateBotLocaleResponseTypeDef:
        operation = "CreateBotLocale"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.create_bot_locale(**operation_parameters)
        self._logger.debug(response)

        return response

    def _create_intents(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        intents=List[Dict[str, Any]],
    ) -> None:
        # TODO fallback intent  # pylint: disable=fixme
        for intent in intents:
            input_parameters = {
                "botId": bot_id,
                "botVersion": bot_version,
                "localeId": locale_id,
                **intent,
            }
            self._intent_manager.create_intent(input_parameters=input_parameters)

    def _create_or_update_existing_intents(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        intents=List[Dict[str, Any]],
        old_intents=List[Dict[str, Any]],
    ) -> None:
        intents_to_update: List[Dict[str, Any]] = []
        intents_to_create: List[Dict[str, Any]] = []
        for intent in intents:
            intent_name = intent["intentName"]
            intent_id = self._intent_manager.get_intent_id(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intent_name=intent_name,
            )
            if intent_id:
                intents_to_update.append(intent)
            else:
                intents_to_create.append(intent)

        if intents_to_update:
            self._update_existing_intents(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intents_to_update=intents_to_update,
                old_intents=old_intents,
            )
        if intents_to_create:
            self._create_intents(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intents=intents_to_create,
            )

    def _create_or_update_existing_slot_types(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        slot_types=List[Dict[str, Any]],
    ) -> None:
        slot_types_to_update: List[Dict[str, Any]] = []
        slot_types_to_create: List[Dict[str, Any]] = []
        for slot_type in slot_types:
            slot_type_name = slot_type["slotTypeName"]
            slot_type_id = self._slot_type_manager.get_slot_type_id(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                slot_type_name=slot_type_name,
            )
            if slot_type_id:
                slot_types_to_update.append(slot_type)
            else:
                slot_types_to_create.append(slot_type)

        if slot_types_to_update:
            self._update_existing_slot_types(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                slot_types=slot_types_to_update,
            )
        if slot_types_to_create:
            self._create_slot_types(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                slot_types=slot_types_to_create,
            )

    def _create_slot_types(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        slot_types=List[Dict[str, Any]],
    ) -> None:
        for slot_type in slot_types:
            input_parameters = {
                "botId": bot_id,
                "botVersion": bot_version,
                "localeId": locale_id,
                **slot_type,
            }
            self._slot_type_manager.create_slot_type(input_parameters=input_parameters)

    def _delete_intents(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        intents=List[Dict[str, Any]],
    ) -> None:
        for intent in intents:
            intent_name = intent["intentName"]
            intent_id = self._intent_manager.get_intent_id(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intent_name=intent_name,
            )
            input_parameters = {
                "botId": bot_id,
                "botVersion": bot_version,
                "localeId": locale_id,
                "intentId": intent_id,
            }
            if intent_id:
                self._intent_manager.delete_intent(input_parameters=input_parameters)
            else:
                self._logger.warning(
                    "unable to find intent name: %s",
                    intent_name,
                )

    def _delete_slot_types(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        slot_types=List[Dict[str, Any]],
    ) -> None:
        for slot_type in slot_types:
            slot_type_name = slot_type["slotTypeName"]
            slot_type_id = self._slot_type_manager.get_slot_type_id(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                slot_type_name=slot_type_name,
            )
            input_parameters = {
                "botId": bot_id,
                "botVersion": bot_version,
                "localeId": locale_id,
                "skipResourceInUseCheck": True,
                "slotTypeId": slot_type_id,
            }
            if slot_type_id:
                self._slot_type_manager.delete_slot_type(input_parameters=input_parameters)
            else:
                self._logger.warning(
                    "unable to find slot type name: %s",
                    slot_type_name,
                )

    def _update_bot_locale(
        self, input_parameters: Dict[str, Any]
    ) -> UpdateBotLocaleResponseTypeDef:
        operation = "UpdateBotLocale"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.update_bot_locale(**operation_parameters)
        self._logger.debug(response)

        return response

    def _update_existing_intents(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        intents_to_update=List[Dict[str, Any]],
        old_intents=List[Dict[str, Any]],
    ) -> None:
        for intent in intents_to_update:
            intent_name = intent["intentName"]
            old_intent_match = [o_i for o_i in old_intents if o_i["intentName"] == intent_name]
            if old_intent_match:
                old_intent = old_intent_match[0]
            else:
                continue

            if intent == old_intent:
                continue

            intent_id = self._intent_manager.get_intent_id(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intent_name=intent_name,
            )
            if not intent_id:
                raise ValueError(f"intent not found: {intent_name}")

            self._intent_manager.update_intent(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intent_id=intent_id,
                intent=intent,
                old_intent=old_intent,
            )

    def _update_existing_slot_types(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        slot_types=List[Dict[str, Any]],
    ) -> None:
        for slot_type in slot_types:
            slot_type_id = self._slot_type_manager.get_slot_type_id(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                slot_type_name=slot_type["slotTypeName"],
            )
            if not slot_type_id:
                raise ValueError(f"slot type not found: {slot_type['slotTypeName']}")
            input_parameters = {
                "botId": bot_id,
                "botVersion": bot_version,
                "localeId": locale_id,
                "slotTypeId": slot_type_id,
                **slot_type,
            }
            self._slot_type_manager.update_slot_type(input_parameters=input_parameters)

    def _update_intents(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        new_intents: List[Dict[str, Any]],
        old_intents: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        old_intent_names = {s_t["intentName"] for s_t in old_intents}
        new_intent_names = {s_t["intentName"] for s_t in new_intents}

        intents_to_create = [
            s_t for s_t in new_intents if s_t["intentName"] not in old_intent_names
        ]
        intents_to_delete = [
            s_t for s_t in old_intents if s_t["intentName"] not in new_intent_names
        ]

        intent_names_to_update = new_intent_names.intersection(old_intent_names)
        intents_to_update_new = {
            intent["intentName"]: intent
            for intent in new_intents
            if intent["intentName"] in intent_names_to_update
        }
        intents_to_update_old = {
            intent["intentName"]: intent
            for intent in old_intents
            if intent["intentName"] in intent_names_to_update
        }
        intents_to_update = [
            intents_to_update_new[intent_name]
            for intent_name in intent_names_to_update
            if intents_to_update_new[intent_name] != intents_to_update_old[intent_name]
        ]

        if intents_to_create or intents_to_update:
            self._create_or_update_existing_intents(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intents=[*intents_to_create, *intents_to_update],
                old_intents=old_intents,
            )
        if intents_to_delete:
            self._delete_intents(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intents=intents_to_delete,
            )

        return [*intents_to_create, *intents_to_delete, *intents_to_update]

    def _update_slot_types(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        new_slot_types: List[Dict[str, Any]],
        old_slot_types: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        old_slot_type_names = {s_t["slotTypeName"] for s_t in old_slot_types}
        new_slot_type_names = {s_t["slotTypeName"] for s_t in new_slot_types}

        slot_types_to_create = [
            s_t for s_t in new_slot_types if s_t["slotTypeName"] not in old_slot_type_names
        ]
        slot_types_to_delete = [
            s_t for s_t in old_slot_types if s_t["slotTypeName"] not in new_slot_type_names
        ]

        slot_type_names_to_update = new_slot_type_names.intersection(old_slot_type_names)
        slot_types_to_update_new = {
            s_t["slotTypeName"]: s_t
            for s_t in new_slot_types
            if s_t["slotTypeName"] in slot_type_names_to_update
        }
        slot_types_to_update_old = {
            s_t["slotTypeName"]: s_t
            for s_t in old_slot_types
            if s_t["slotTypeName"] in slot_type_names_to_update
        }
        slot_types_to_update = [
            slot_types_to_update_new[slot_type_name]
            for slot_type_name in slot_type_names_to_update
            if slot_types_to_update_new[slot_type_name] != slot_types_to_update_old[slot_type_name]
        ]

        if slot_types_to_create or slot_types_to_update:
            self._create_or_update_existing_slot_types(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                slot_types=[*slot_types_to_create, *slot_types_to_update],
            )
        if slot_types_to_delete:
            self._delete_slot_types(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                slot_types=slot_types_to_delete,
            )
        if slot_types_to_update:
            self._update_existing_slot_types(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                slot_types=slot_types_to_update,
            )

        return [*slot_types_to_create, *slot_types_to_delete, *slot_types_to_update]

    def _wait_for_create_bot_locale(
        self,
        operation_args: Dict[str, Any],
    ) -> None:
        wait_for_operation(
            operation="describe_bot_locale",
            operation_args=operation_args,
            status_key="botLocaleStatus",
            wait_status=["Creating"],
            target_status=["NotBuilt"],
            client=self._client,
            logger=self._logger,
            poll_sleep_time_in_secs=self._poll_sleep_time_in_secs,
        )

    def _wait_for_delete_bot_locale(
        self,
        operation_args: Dict[str, Any],
    ) -> None:
        try:
            wait_for_operation(
                operation="describe_bot_locale",
                operation_args=operation_args,
                status_key="botLocaleStatus",
                wait_status=["Deleting"],
                # No target status - handle NotFound exception
                target_status=[""],
                client=self._client,
                logger=self._logger,
                poll_sleep_time_in_secs=self._poll_sleep_time_in_secs,
            )
        except self._client.exceptions.ResourceNotFoundException:
            pass

    def create_bot_locale(self, input_parameters: Dict[str, Any]) -> CreateBotLocaleResponseTypeDef:
        """Create Locale"""
        response = self._create_bot_locale(input_parameters=input_parameters)
        bot_id = response["botId"]
        locale_id = response["localeId"]
        bot_version = response["botVersion"]
        self._wait_for_create_bot_locale(
            operation_args=dict(
                botId=bot_id,
                botVersion=bot_version,
                localeId=locale_id,
            ),
        )
        if CUSTOM_ATTRIBUTES["slotTypes"] in input_parameters:
            self._create_slot_types(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                slot_types=input_parameters[CUSTOM_ATTRIBUTES["slotTypes"]],
            )

        self._create_intents(
            bot_id=bot_id,
            bot_version=bot_version,
            locale_id=locale_id,
            intents=input_parameters[CUSTOM_ATTRIBUTES["intents"]],
        )

        return response

    def delete_bot_locale(self, input_parameters: Dict[str, Any]) -> DeleteBotLocaleResponseTypeDef:
        """Delete Bot Locale"""
        operation = "DeleteBotLocale"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.delete_bot_locale(**operation_parameters)
        self._logger.debug(response)

        bot_id = response["botId"]
        locale_id = response["localeId"]
        bot_version = response["botVersion"]

        self._wait_for_delete_bot_locale(
            operation_args=dict(
                botId=bot_id,
                botVersion=bot_version,
                localeId=locale_id,
            ),
        )

        return response

    def update_bot_locale(
        self,
        bot_id: str,
        bot_locale: Dict[str, Any],
        old_bot_locale: Dict[str, Any],
    ) -> None:
        """Update Bot Locale"""
        bot_version = DRAFT_VERSION
        locale_id = bot_locale["localeId"]
        input_parameters = {
            "botId": bot_id,
            "botVersion": bot_version,
            **bot_locale,
        }
        new_update_bot_locale_parameters = get_api_parameters(
            operation="UpdateBotLocale",
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )
        old_update_bot_locale_parameters = get_api_parameters(
            operation="UpdateBotLocale",
            input_parameters={**input_parameters, **old_bot_locale},
            client=self._client,
            logger=self._logger,
        )
        if new_update_bot_locale_parameters != old_update_bot_locale_parameters:
            # TODO this fails if the bot is in a failed state  # pylint: disable=fixme
            # need to figure out how to revert on rollbacks
            self._update_bot_locale(input_parameters=input_parameters)

        new_slot_types = (
            bot_locale[CUSTOM_ATTRIBUTES["slotTypes"]]
            if CUSTOM_ATTRIBUTES["slotTypes"] in bot_locale
            else []
        )
        old_slot_types = (
            old_bot_locale[CUSTOM_ATTRIBUTES["slotTypes"]]
            if CUSTOM_ATTRIBUTES["slotTypes"] in old_bot_locale
            else []
        )
        if new_slot_types or old_slot_types:
            self._update_slot_types(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                new_slot_types=new_slot_types,
                old_slot_types=old_slot_types,
            )

        self._update_intents(
            bot_id=bot_id,
            bot_version=bot_version,
            locale_id=locale_id,
            new_intents=bot_locale[CUSTOM_ATTRIBUTES["intents"]],
            old_intents=old_bot_locale[CUSTOM_ATTRIBUTES["intents"]],
        )
