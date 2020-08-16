# This file contains tests specific to ArgumentValue class
import pytest

from pytest_dynamicrerun import ArgumentValue


@pytest.mark.parametrize(
    "argument_value_type,should_throw",
    [
        (ArgumentValue.FLAG, False),
        (ArgumentValue.INI, False),
        (ArgumentValue.MARKER, False),
        (123, True),
    ],
)
def test_constructor_accepts_only_valid_types(argument_value_type, should_throw):
    argument_value = "the value"

    if should_throw:
        value_error_text = "Invalid argument type provided."
        with pytest.raises(ValueError, match=value_error_text):
            ArgumentValue(argument_value_type, argument_value)
    else:
        arg_value = ArgumentValue(argument_value_type, argument_value)
        assert arg_value.argument_type == argument_value_type
        assert arg_value.argument_value == argument_value


@pytest.mark.parametrize(
    "argument_value_type", [ArgumentValue.FLAG, ArgumentValue.INI, ArgumentValue.MARKER]
)
def test_class_level_creation_methods_work(argument_value_type):
    argument_value = "the value"

    if argument_value_type == ArgumentValue.FLAG:
        arg_value = ArgumentValue.create_flag_level_argument(argument_value)
    elif argument_value_type == ArgumentValue.INI:
        arg_value = ArgumentValue.create_ini_level_argument(argument_value)
    else:  # ArgumentValue.MARKER
        arg_value = ArgumentValue.create_marker_level_argument(argument_value)

    assert arg_value.argument_type == argument_value_type
    assert arg_value.argument_value == argument_value
