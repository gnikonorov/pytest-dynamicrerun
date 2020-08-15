# Test helper functions and classes


class ParameterPassLevel:
    FLAG = 0
    INI_KEY = 1
    MARKER = 2


def _assert_result_outcomes(
    result, passed=0, skipped=0, failed=0, error=0, dynamic_rerun=0
):
    outcomes = result.parseoutcomes()
    _check_outcome_field(outcomes, "passed", passed)
    _check_outcome_field(outcomes, "skipped", skipped)
    _check_outcome_field(outcomes, "failed", failed)
    _check_outcome_field(outcomes, "error", error)
    _check_outcome_field(outcomes, "dynamicrerun", dynamic_rerun)


def _check_outcome_field(outcomes, field_name, expected_value):
    field_value = outcomes.get(field_name, 0)
    expected_value = int(expected_value)
    assert (
        field_value == expected_value
    ), "outcomes.{} has unexpected value. Expected '{}' but got '{}'".format(
        field_name, expected_value, field_value
    )
