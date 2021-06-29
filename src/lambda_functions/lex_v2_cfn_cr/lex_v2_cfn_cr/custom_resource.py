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
"""Amazon Lex CloudFormation Custom Resource Module"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import boto3

from .bot import Bot
from .bot_version import BotVersion
from .bot_alias import BotAlias
from .shared.constants import (
    DEFAULT_POLL_SLEEP_TIME_IN_SECS,
    DRAFT_VERSION,
)

if TYPE_CHECKING:
    from mypy_boto3_lexv2_models import LexModelsV2Client
else:
    LexModelsV2Client = object


class LexV2CustomResource:
    """Lex V2 CloudFormation Custom Resource"""

    def __init__(
        self,
        client: Optional[LexModelsV2Client] = None,
        logger: Optional[logging.Logger] = None,
        poll_sleep_time_in_secs=DEFAULT_POLL_SLEEP_TIME_IN_SECS,
    ):
        self._client = client or boto3.client("lexv2-models")
        self._logger = logger or logging.getLogger(__name__)
        self._poll_sleep_time_in_secs = poll_sleep_time_in_secs

        self._bot_manager = Bot(
            client=self._client,
            logger=self._logger,
            poll_sleep_time_in_secs=self._poll_sleep_time_in_secs,
        )
        self._bot_version_manager = BotVersion(
            client=self._client,
            logger=self._logger,
            poll_sleep_time_in_secs=self._poll_sleep_time_in_secs,
        )
        self._bot_alias_manager = BotAlias(
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
    ) -> None:
        """Build the Lex Bot Locales"""
        self._bot_manager.build_bot_locales(
            bot_id=bot_id,
            bot_locale_ids=bot_locale_ids,
            bot_version=bot_version,
            max_concurrent_builds=max_concurrent_builds,
        )

    def create_bot(self, resource_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create Lex V2 Bot"""
        return self._bot_manager.create_bot(resource_properties=resource_properties)

    def create_bot_alias(self, resource_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create Lex V2 Bot Alias"""
        return self._bot_alias_manager.create_bot_alias(resource_properties=resource_properties)

    def create_bot_version(self, resource_properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create Lex V2 Bot Version"""
        return self._bot_version_manager.create_bot_version(resource_properties=resource_properties)

    def update_bot(
        self,
        bot_id: str,
        resource_properties: Dict[str, Any],
        old_resource_properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update Lex V2 Bot"""
        return self._bot_manager.update_bot(
            bot_id=bot_id,
            resource_properties=resource_properties,
            old_resource_properties=old_resource_properties,
        )

    def update_bot_alias(
        self,
        bot_alias_id: str,
        resource_properties: Dict[str, Any],
        old_resource_properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update Lex V2 Bot Alias"""
        return self._bot_alias_manager.update_bot_alias(
            bot_alias_id=bot_alias_id,
            resource_properties=resource_properties,
            old_resource_properties=old_resource_properties,
        )

    def delete_bot(self, bot_id: str) -> None:
        """Delete Bot"""
        self._bot_manager.delete_bot(bot_id=bot_id)

    def delete_bot_alias(self, bot_id: str, bot_alias_id: str) -> None:
        """Delete Bot Alias"""
        self._bot_alias_manager.delete_bot_alias(bot_id=bot_id, bot_alias_id=bot_alias_id)

    def get_bot_id(
        self,
        bot_name: str,
    ) -> str:
        """Get Bot ID from a Bot Name"""
        return self._bot_manager.get_bot_id(bot_name=bot_name)

    def wait_for_delete_bot(
        self,
        bot_id: str,
    ) -> None:
        """Waits for bot to be deleted"""
        self._bot_manager.wait_for_delete_bot(bot_id=bot_id)

    def wait_for_delete_bot_alias(
        self,
        bot_id: str,
        bot_alias_id: str,
    ) -> None:
        """Waits for bot alias to be deleted"""
        self._bot_alias_manager.wait_for_delete_bot_alias(bot_id=bot_id, bot_alias_id=bot_alias_id)
