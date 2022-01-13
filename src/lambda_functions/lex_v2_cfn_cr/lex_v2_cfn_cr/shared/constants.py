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
"""Common Constants"""

DEFAULT_POLL_SLEEP_TIME_IN_SECS = 5
DRAFT_VERSION = "DRAFT"
CUSTOM_ATTRIBUTE_PREFIX = "CR_"
CUSTOM_ATTRIBUTES = dict(
    slotTypes=f"{CUSTOM_ATTRIBUTE_PREFIX}slotTypes",
    botLocales=f"{CUSTOM_ATTRIBUTE_PREFIX}botLocales",
    intents=f"{CUSTOM_ATTRIBUTE_PREFIX}intents",
    slots=f"{CUSTOM_ATTRIBUTE_PREFIX}slots",
    slotTypeName=f"{CUSTOM_ATTRIBUTE_PREFIX}slotTypeName",
    botLocaleIds=f"{CUSTOM_ATTRIBUTE_PREFIX}botLocaleIds",
    lastUpdatedDateTime=f"{CUSTOM_ATTRIBUTE_PREFIX}lastUpdatedDateTime",
)
