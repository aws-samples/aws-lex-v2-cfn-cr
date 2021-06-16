#!/usr/bin/env python3.8
"""Amazon Lex CloudFormation Custom Resource Slot Manager"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

import boto3

from .shared.api import get_api_parameters

if TYPE_CHECKING:
    from mypy_boto3_lexv2_models import LexModelsV2Client
    from mypy_boto3_lexv2_models.type_defs import (
        CreateSlotResponseTypeDef,
        UpdateSlotResponseTypeDef,
    )
else:
    LexModelsV2Client = object
    CreateSlotResponseTypeDef = object
    UpdateSlotResponseTypeDef = object


class Slot:
    """Lex V2 CloudFormation Custom Resource Slot"""

    def __init__(
        self,
        client: Optional[LexModelsV2Client] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._client = client or boto3.client("lexv2-models")
        self._logger = logger or logging.getLogger(__name__)

    def get_slot_id(
        self,
        bot_id: str,
        bot_version: str,
        intent_id: str,
        locale_id: str,
        slot_name: str,
    ) -> str:
        """Get Slot ID from Name"""
        response = self._client.list_slots(
            botId=bot_id,
            botVersion=bot_version,
            localeId=locale_id,
            intentId=intent_id,
            filters=[
                {
                    "name": "SlotName",
                    "values": [slot_name],
                    "operator": "EQ",
                }
            ],
        )
        self._logger.debug(response)

        slot_summaries = response["slotSummaries"]
        slot_id = slot_summaries[0]["slotId"] if slot_summaries else ""

        return slot_id

    def create_slot(self, input_parameters: Dict[str, Any]) -> CreateSlotResponseTypeDef:
        """Create Slot"""
        operation = "CreateSlot"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.create_slot(**operation_parameters)
        self._logger.debug(response)

        return response

    def delete_slot(self, input_parameters: Dict[str, Any]) -> None:
        """Delete Slot"""
        operation = "DeleteSlot"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        self._client.delete_slot(**operation_parameters)

    def update_slot(self, input_parameters: Dict[str, Any]) -> UpdateSlotResponseTypeDef:
        """Update Slot"""
        operation = "UpdateSlot"
        operation_parameters = get_api_parameters(
            operation=operation,
            input_parameters=input_parameters,
            client=self._client,
            logger=self._logger,
        )

        response = self._client.update_slot(**operation_parameters)
        self._logger.debug(response)

        return response
