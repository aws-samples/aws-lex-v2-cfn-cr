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
"""Amazon Lex CloudFormation Custom Resource Slot Type Manager"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

import boto3

from .shared.api import get_api_parameters

if TYPE_CHECKING:
    from mypy_boto3_lexv2_models import LexModelsV2Client
    from mypy_boto3_lexv2_models.type_defs import (
        CreateSlotTypeResponseTypeDef,
        UpdateSlotTypeResponseTypeDef,
    )
else:
    LexModelsV2Client = object
    CreateSlotTypeResponseTypeDef = object
    UpdateSlotTypeResponseTypeDef = object


class SlotType:
    """Lex V2 CloudFormation Custom Resource Slot Type"""

    def __init__(
        self,
        client: Optional[LexModelsV2Client] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._client = client or boto3.client("lexv2-models")
        self._logger = logger or logging.getLogger(__name__)

    def get_slot_type_id(
        self,
        bot_id: str,
        bot_version: str,
        locale_id: str,
        slot_type_name: str,
    ) -> str:
        """Get Slot Type ID from a Slot Name"""
        if slot_type_name.startswith("AMAZON."):
            return slot_type_name

        response = self._client.list_slot_types(
            botId=bot_id,
            botVersion=bot_version,
            localeId=locale_id,
            filters=[
                {
                    "name": "SlotTypeName",
                    "values": [slot_type_name],
                    "operator": "EQ",
                }
            ],
        )
        self._logger.debug(response)

        slot_type_summaries = response["slotTypeSummaries"]
        slot_type_id = slot_type_summaries[0]["slotTypeId"] if slot_type_summaries else ""

        return slot_type_id

    def create_slot_type(self, input_parameters: Dict[str, Any]) -> CreateSlotTypeResponseTypeDef:
        """Create Slot Type"""
        operation = "CreateSlotType"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.create_slot_type(**operation_parameters)
        self._logger.debug(response)

        return response

    def delete_slot_type(self, input_parameters: Dict[str, Any]) -> None:
        """Delete Slot Type"""
        operation = "DeleteSlotType"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        self._client.delete_slot_type(**operation_parameters)

    def update_slot_type(self, input_parameters: Dict[str, Any]) -> UpdateSlotTypeResponseTypeDef:
        """Update Slot Type"""
        operation = "UpdateSlotType"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.update_slot_type(**operation_parameters)
        self._logger.debug(response)

        return response
