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
"""Logger"""
import logging
from os import getenv

DEFAULT_LEVEL = "WARNING"


def get_log_level():
    """
    Get the logging level from the LOG_LEVEL environment variable if it is valid.
    Otherwise set to WARNING
    :return: The logging level to use
    """
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    requested_level = getenv("LOG_LEVEL", DEFAULT_LEVEL)
    if requested_level and requested_level in valid_levels:
        return requested_level
    return DEFAULT_LEVEL


def get_logger(name):
    """
    Get a configured logger.
    Compatible with both the AWS Lambda runtime (root logger) and local execution
    :param name: The name of the logger (most often __name__ of the calling module)
    :return: The logger to use
    """
    logger = None
    # first case: running as a lambda function or in pytest with conftest
    # second case: running a single test or locally under test
    if len(logging.getLogger().handlers) > 0:
        logger = logging.getLogger()
        logger.setLevel(get_log_level())
        # overrides
        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
    else:
        logging.basicConfig(
            format=(
                "%(asctime)s [%(levelname)s] " "%(filename)s:%(lineno)s:%(funcName)s(): %(message)s"
            ),
            level=get_log_level(),
            datefmt="%Y-%m-%d %H:%M:%S",
        )  # NOSONAR logger's config is safe here

        logger = logging.getLogger(name)
    return logger
