#!/usr/bin/env python3.8
"""AWS API Helpers for CloudFormation Custom Resources"""

import logging
from time import sleep

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .constants import CUSTOM_ATTRIBUTE_PREFIX, DEFAULT_POLL_SLEEP_TIME_IN_SECS

if TYPE_CHECKING:
    from mypy_boto3_lexv2_models import LexModelsV2Client
else:
    LexModelsV2Client = object


def get_and_validate_api_input_parameters(
    input_parameters: Dict[str, Any],
    input_shape: Any,
    parameter_prefix_to_ignore: str = CUSTOM_ATTRIBUTE_PREFIX,
    extra_parameter_to_ignore: Optional[List[str]] = None,
    should_raise_on_extra_parameter: bool = False,
) -> Dict[str, Any]:
    # pylint: disable=too-many-branches
    """Transforms Lex API input parameters to the expected boto3 types

    This function casts the input_parameters to the expected boto3 type
    based on the input_shape definition. It recursively traverses the input
    parameter to cast nested properties to the right type.

    This is needed because CloudFormation converts the resource properties
    payload to strings which causes typing issues with boto3:
    https://forums.aws.amazon.com/message.jspa?messageID=922600


    Additionally, this function validates that the input parameter contains
    all required properties and optionally that no extraneous properties exists.
    """
    params: Dict[str, Any] = {}
    _extra_parameter_to_ignore = extra_parameter_to_ignore or []

    for key in input_shape.required_members:
        if key not in input_parameters:
            raise ValueError(f"missing required key: {key}")

    for key, value in input_parameters.items():
        if key not in input_shape.members:
            # special prefix for nested custom properties
            # that are not proxied to the API
            if (
                key.startswith(parameter_prefix_to_ignore)
                or key == "ServiceToken"
                or key in _extra_parameter_to_ignore
            ):
                continue
            if should_raise_on_extra_parameter:
                raise ValueError(f"invalid parameter {key}")

        input_shape_member = input_shape.members[key]
        type_name = input_shape_member.type_name
        # types from:
        # https://github.com/boto/botocore/blob/928d202aac381e7f7f2f41d61a601f3014186057/botocore/model.py#L723
        if type_name == "structure":
            params[key] = get_and_validate_api_input_parameters(
                value,
                input_shape_member,
            )
        elif type_name == "list":
            params[key] = [
                get_and_validate_api_input_parameters(
                    i,
                    input_shape_member.member,
                )
                for i in value
            ]
        elif type_name == "map":
            params[key] = dict(value)
        elif type_name in ["string", "char"]:
            params[key] = str(value)
        elif type_name == "boolean":
            params[key] = bool(value.lower() == "true" if isinstance(value, str) else value)
        elif type_name in ["integer", "long"]:
            params[key] = int(value)
        elif type_name in ["float", "double"]:
            params[key] = float(value)
        else:
            raise ValueError(f"invalid type name {type_name}")

    return params


def get_api_parameters(
    operation: str,
    input_parameters: Dict[str, Any],
    client: LexModelsV2Client,
    logger: logging.Logger,
    parameter_prefix_to_ignore: str = CUSTOM_ATTRIBUTE_PREFIX,
    extra_parameter_to_ignore: Optional[List[str]] = None,
    should_raise_on_extra_parameter: bool = False,
) -> Dict[str, Any]:
    """Build API parameters from model definition"""
    input_shape = client.meta.service_model.operation_model(operation).input_shape
    operation_parameters = get_and_validate_api_input_parameters(
        input_parameters=input_parameters,
        input_shape=input_shape,
        parameter_prefix_to_ignore=parameter_prefix_to_ignore,
        extra_parameter_to_ignore=extra_parameter_to_ignore,
        should_raise_on_extra_parameter=should_raise_on_extra_parameter,
    )

    logger.debug(dict(operation=operation, parameters=operation_parameters))

    return operation_parameters


def wait_for_operation(
    operation: str,
    operation_args: Dict[str, Any],
    status_key: str,
    wait_status: List[str],
    target_status: List[str],
    client: LexModelsV2Client,
    logger: logging.Logger,
    poll_sleep_time_in_secs=DEFAULT_POLL_SLEEP_TIME_IN_SECS,
    max_tries: int = 60,
):
    """Wait for API Operation"""
    # pylint: disable=too-many-arguments
    tries = 0
    while True:
        operation_function = getattr(client, operation)
        logger.debug(operation_args)
        response = operation_function(**operation_args)
        logger.debug(response)
        status = response[status_key]
        if status not in wait_status or tries >= max_tries:
            break
        sleep(poll_sleep_time_in_secs)
        tries = tries + 1
    if status not in target_status:
        logger.error(
            "failed waiting for operation: %s  - response: %s, tries: %s",
            operation,
            response,
            tries,
        )
        raise RuntimeError(f"Failed waiting for operation: {operation}")
