#!/usr/bin/env python3.8
"""Common Constants"""

DEFAULT_POLL_SLEEP_TIME_IN_SECS = 5
DRAFT_VERSION = "DRAFT"
CUSTOM_ATTRIBUTE_PREFIX = "CR."
CUSTOM_ATTRIBUTES = dict(
    slotTypes=f"{CUSTOM_ATTRIBUTE_PREFIX}slotTypes",
    botLocales=f"{CUSTOM_ATTRIBUTE_PREFIX}botLocales",
    intents=f"{CUSTOM_ATTRIBUTE_PREFIX}intents",
    slots=f"{CUSTOM_ATTRIBUTE_PREFIX}slots",
    slotTypeName=f"{CUSTOM_ATTRIBUTE_PREFIX}slotTypeName",
    botLocaleIds=f"{CUSTOM_ATTRIBUTE_PREFIX}botLocaleIds",
    lastUpdatedDateTime=f"{CUSTOM_ATTRIBUTE_PREFIX}lastUpdatedDateTime",
)
