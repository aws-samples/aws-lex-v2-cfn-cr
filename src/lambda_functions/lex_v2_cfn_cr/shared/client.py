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
# pylint: disable=global-statement
"""Boto3 Client"""
from os import getenv
import json
import boto3
from botocore.config import Config
from .logger import get_logger


LOGGER = get_logger(__name__)

CLIENT_CONFIG = Config(
    retries={"mode": "standard"},
    **json.loads(getenv("AWS_SDK_USER_AGENT", "{}")),
)

_HELPERS_SERVICE_CLIENTS = dict()


def get_client(service_name, config=CLIENT_CONFIG):
    """Get Boto3 Client"""
    global _HELPERS_SERVICE_CLIENTS
    if service_name not in _HELPERS_SERVICE_CLIENTS:
        LOGGER.debug("Initializing global boto3 client for %s", service_name)
        _HELPERS_SERVICE_CLIENTS[service_name] = boto3.client(service_name, config=config)
    return _HELPERS_SERVICE_CLIENTS[service_name]


def reset_client():
    """Reset Boto3 Client"""
    global _HELPERS_SERVICE_CLIENTS
    _HELPERS_SERVICE_CLIENTS = dict()
