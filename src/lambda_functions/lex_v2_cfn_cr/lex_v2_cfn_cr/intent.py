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
"""Amazon Lex CloudFormation Custom Resource Intent Manager"""

import logging
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

import boto3

from .slot import Slot
from .slot_type import SlotType
from .shared.api import get_api_parameters
from .shared.constants import (
    CUSTOM_ATTRIBUTES,
)

if TYPE_CHECKING:
    from mypy_boto3_lexv2_models import LexModelsV2Client
    from mypy_boto3_lexv2_models.type_defs import (
        CreateIntentResponseTypeDef,
        CreateSlotResponseTypeDef,
        UpdateIntentResponseTypeDef,
    )
else:
    LexModelsV2Client = object
    CreateIntentResponseTypeDef = object
    CreateSlotResponseTypeDef = object
    UpdateIntentResponseTypeDef = object


class Intent:
    """Lex V2 CloudFormation Custom Resource Intent"""

    def __init__(
        self,
        client: Optional[LexModelsV2Client] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._client = client or boto3.client("lexv2-models")
        self._logger = logger or logging.getLogger(__name__)

        self._slot_type_manager = SlotType(
            client=self._client,
            logger=self._logger,
        )

        self._slot_manager = Slot(
            client=self._client,
            logger=self._logger,
        )

    def _create_intent(self, input_parameters: Dict[str, Any]) -> CreateIntentResponseTypeDef:
        operation = "CreateIntent"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.create_intent(**operation_parameters)
        self._logger.debug(response)

        return response

    def _create_or_update_existing_slots(
        self,
        bot_id: str,
        bot_version: str,
        intent_id: str,
        locale_id: str,
        slots=List[Dict[str, Any]],
    ) -> None:
        slots_to_update: List[Dict[str, Any]] = []
        slots_to_create: List[Dict[str, Any]] = []
        for slot in slots:
            slot_name = slot["slotName"]
            slot_id = self._slot_manager.get_slot_id(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intent_id=intent_id,
                slot_name=slot_name,
            )
            if slot_id:
                slots_to_update.append(slot)
            else:
                slots_to_create.append(slot)

        if slots_to_update:
            self._update_existing_slots(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intent_id=intent_id,
                slots=slots_to_update,
            )
        if slots_to_create:
            self._create_slots(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intent_id=intent_id,
                slots=slots_to_create,
            )

    def _create_slots(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        intent_id: str,
        slots=List[Dict[str, Any]],
    ) -> List[CreateSlotResponseTypeDef]:
        create_slot_responses: List[CreateSlotResponseTypeDef] = []
        for slot in slots:
            slot_name = slot["slotName"]
            slot_type_name = (
                slot[CUSTOM_ATTRIBUTES["slotTypeName"]]
                if CUSTOM_ATTRIBUTES["slotTypeName"] in slot
                else ""
            )
            if not slot_type_name:
                raise ValueError("unable to find slot type name attribute")
            slot_type_id = self._slot_type_manager.get_slot_type_id(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                slot_type_name=slot_type_name,
            )
            if not slot_type_id:
                raise ValueError(f"unable to find slot type id for slot name: {slot_name}")

            input_parameters = {
                "botId": bot_id,
                "botVersion": bot_version,
                "intentId": intent_id,
                "localeId": locale_id,
                "slotTypeId": slot_type_id,
                **slot,
            }
            response = self._slot_manager.create_slot(input_parameters=input_parameters)
            create_slot_responses.append(response)

        return create_slot_responses

    def _delete_slots(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        intent_id: str,
        slots=List[Dict[str, Any]],
    ) -> None:
        for slot in slots:
            slot_name = slot["slotName"]
            slot_id = self._slot_manager.get_slot_id(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intent_id=intent_id,
                slot_name=slot_name,
            )
            input_parameters = {
                "botId": bot_id,
                "botVersion": bot_version,
                "localeId": locale_id,
                "intentId": intent_id,
                "slotId": slot_id,
            }
            if slot_id:
                self._slot_manager.delete_slot(input_parameters=input_parameters)
            else:
                self._logger.warning(
                    "unable to find slot with name: %s",
                    slot_name,
                )

    def _update_intent(self, input_parameters: Dict[str, Any]) -> UpdateIntentResponseTypeDef:
        operation = "UpdateIntent"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.update_intent(**operation_parameters)
        self._logger.debug(response)

        return response

    def _update_existing_slots(
        self,
        bot_id: str,
        bot_version: str,
        intent_id: str,
        locale_id: str,
        slots=List[Dict[str, Any]],
    ) -> None:
        for slot in slots:
            slot_name = slot["slotName"]
            slot_id = self._slot_manager.get_slot_id(
                bot_id=bot_id,
                bot_version=bot_version,
                intent_id=intent_id,
                locale_id=locale_id,
                slot_name=slot_name,
            )
            if not slot_id:
                raise ValueError(f"slot not found: {slot_name}")

            slot_type_id = ""
            if CUSTOM_ATTRIBUTES["slotTypeName"] in slot:
                slot_type_name = slot[CUSTOM_ATTRIBUTES["slotTypeName"]]
                slot_type_id = self._slot_type_manager.get_slot_type_id(
                    bot_id=bot_id,
                    bot_version=bot_version,
                    locale_id=locale_id,
                    slot_type_name=slot_type_name,
                )
            elif "slotTypeId" in slot and slot["slotTypeId"].startswith("AMAZON."):
                slot_type_id = slot["slotTypeId"]

            if not slot_type_id:
                raise ValueError(
                    f"missing CR.slotTypeName or slotTypeId attribute for slot name: {slot_name}"
                )

            input_parameters = {
                "botId": bot_id,
                "botVersion": bot_version,
                "localeId": locale_id,
                "intentId": intent_id,
                "slotId": slot_id,
                "slotTypeId": slot_type_id,
                **slot,
            }
            self._slot_manager.update_slot(input_parameters=input_parameters)

    def _update_slots(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        intent_id: str,
        new_slots: List[Dict[str, Any]],
        old_slots: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        old_slot_names = {s_t["slotName"] for s_t in old_slots}
        new_slot_names = {s_t["slotName"] for s_t in new_slots}

        slots_to_create = [s_t for s_t in new_slots if s_t["slotName"] not in old_slot_names]
        slots_to_delete = [s_t for s_t in old_slots if s_t["slotName"] not in new_slot_names]

        slot_names_to_update = new_slot_names.intersection(old_slot_names)
        slots_to_update_new = {
            s_t["slotName"]: s_t for s_t in new_slots if s_t["slotName"] in slot_names_to_update
        }
        slots_to_update_old = {
            s_t["slotName"]: s_t for s_t in old_slots if s_t["slotName"] in slot_names_to_update
        }
        slots_to_update = [
            slots_to_update_new[slot_name]
            for slot_name in slot_names_to_update
            if slots_to_update_new[slot_name] != slots_to_update_old[slot_name]
        ]

        if slots_to_create or slots_to_update:
            self._create_or_update_existing_slots(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intent_id=intent_id,
                slots=[*slots_to_create, *slots_to_update],
            )
        if slots_to_delete:
            self._delete_slots(
                bot_id=bot_id,
                bot_version=bot_version,
                locale_id=locale_id,
                intent_id=intent_id,
                slots=slots_to_delete,
            )

        return [*slots_to_create, *slots_to_delete, *slots_to_update]

    def get_intent_id(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        intent_name: str,
    ) -> str:
        """Get Intent Id from Name"""
        list_intents_args: Dict[str, Any] = dict(
            botId=bot_id,
            botVersion=bot_version,
            localeId=locale_id,
            filters=[
                {
                    "name": "IntentName",
                    "values": [intent_name],
                    "operator": "EQ",
                }
            ],
            sortBy={
                "attribute": "IntentName",
                "order": "Ascending",
            },
        )
        while True:
            response = self._client.list_intents(**list_intents_args)
            self._logger.debug(response)

            intent_summaries = response["intentSummaries"]
            intent_id = intent_summaries[0]["intentId"] if intent_summaries else ""

            if intent_id:
                break

            next_token = response.get("nextToken")
            if next_token:
                list_intents_args["nextToken"] = next_token
            else:
                break

        if not intent_id:
            self._logger.warning("could not find intent named: %s", intent_name)

        return intent_id

    def create_intent(
        self, input_parameters: Dict[str, Any]
    ) -> Union[CreateIntentResponseTypeDef, UpdateIntentResponseTypeDef]:
        """Create Intent"""
        response = self._create_intent(input_parameters=input_parameters)
        bot_id = response["botId"]
        bot_version = response["botVersion"]
        locale_id = response["localeId"]
        intent_id = response["intentId"]

        if CUSTOM_ATTRIBUTES["slots"] in input_parameters:
            slots = self._create_slots(
                bot_id=bot_id,
                bot_version=bot_version,
                intent_id=intent_id,
                locale_id=locale_id,
                slots=input_parameters[CUSTOM_ATTRIBUTES["slots"]],
            )

            slot_priorities = [
                dict(priority=(i + 1), slotId=slot["slotId"]) for i, slot in enumerate(slots)
            ]
            update_intent_input_parameters = {
                "intentId": intent_id,
                "slotPriorities": slot_priorities,
                **input_parameters,
            }
            response = self._update_intent(input_parameters=update_intent_input_parameters)

        return response

    def delete_intent(self, input_parameters: Dict[str, Any]) -> None:
        """Delete Intent"""
        operation = "DeleteIntent"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        self._client.delete_intent(**operation_parameters)

    def update_intent(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        intent_id: str,
        intent: Dict[str, Any],
        old_intent: Dict[str, Any],
    ) -> UpdateIntentResponseTypeDef:
        """Update Intent"""
        input_parameters: Dict[str, Any] = {
            "botId": bot_id,
            "botVersion": bot_version,
            "localeId": locale_id,
            "intentId": intent_id,
            **intent,
        }
        old_slots = (
            old_intent[CUSTOM_ATTRIBUTES["slots"]]
            if CUSTOM_ATTRIBUTES["slots"] in old_intent
            else []
        )
        new_slots = (
            intent[CUSTOM_ATTRIBUTES["slots"]] if CUSTOM_ATTRIBUTES["slots"] in intent else []
        )
        if new_slots or old_slots:
            self._update_slots(
                bot_id=bot_id,
                bot_version=bot_version,
                intent_id=intent_id,
                locale_id=locale_id,
                new_slots=new_slots,
                old_slots=old_slots,
            )

            if new_slots:
                slot_priorities = []
                for i, slot in enumerate(new_slots):
                    slot_name = slot["slotName"]
                    slot_id = self._slot_manager.get_slot_id(
                        bot_id=bot_id,
                        bot_version=bot_version,
                        intent_id=intent_id,
                        locale_id=locale_id,
                        slot_name=slot_name,
                    )
                    if slot_id:
                        slot_priorities.append(dict(priority=(i + 1), slotId=slot_id))
                    else:
                        self._logger.warning("slot id not found for slot name: %s", slot_name)
                if slot_priorities:
                    input_parameters["slotPriorities"] = slot_priorities

        return self._update_intent(input_parameters=input_parameters)
