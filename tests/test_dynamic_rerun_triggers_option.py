# This file contains tests specific to the dynamic_rerun_triggers option
import pytest
from helpers import _assert_result_outcomes


def test_errors_no_longer_rerun_by_default_when_dynamic_rerun_triggers_provided(
    testdir,
):
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_schedule = * * * * * *
        dynamic_rerun_attempts = 99
        dynamic_rerun_triggers = this will trigger a rerun
    """
    )

    testdir.makepyfile("def test_always_false(): assert False")
    result = testdir.runpytest("-v")
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(result, failed=1)


@pytest.mark.parametrize(
    "rerun_trigger_text", ["ValueError", "A value error", "A value"]
)
def test_exceptions_output_checked_by_dynamic_rerun_triggers(
    testdir, rerun_trigger_text
):
    rerun_amount = 3
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_schedule = * * * * * *
        dynamic_rerun_attempts = {}
        dynamic_rerun_triggers = {}
    """.format(
            rerun_amount, rerun_trigger_text
        )
    )

    testdir.makepyfile("def test_value_error(): raise ValueError('A value error')")
    result = testdir.runpytest("-v")
    assert result.ret == pytest.ExitCode.TESTS_FAILED

    failed_amount = 1
    _assert_result_outcomes(result, dynamic_rerun=rerun_amount, failed=failed_amount)


@pytest.mark.parametrize(
    "rerun_trigger_text", ["Please rerun me", "rerun", "Please", "me"]
)
def test_stdout_checked_by_dynamic_rerun_triggers(testdir, rerun_trigger_text):
    rerun_amount = 3
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_schedule = * * * * * *
        dynamic_rerun_attempts = {}
        dynamic_rerun_triggers = {}
    """.format(
            rerun_amount, rerun_trigger_text
        )
    )

    testdir.makepyfile("def test_all_seems_well_but(): print('Please rerun me')")
    result = testdir.runpytest("-v")
    assert result.ret == pytest.ExitCode.TESTS_FAILED

    failed_amount = 1
    _assert_result_outcomes(result, dynamic_rerun=rerun_amount, failed=failed_amount)


@pytest.mark.parametrize(
    "rerun_trigger_text", ["Please rerun me", "rerun", "Please", "me"]
)
def test_stderr_checked_by_dynamic_rerun_triggers(testdir, rerun_trigger_text):
    rerun_amount = 3
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_schedule = * * * * * *
        dynamic_rerun_attempts = {}
        dynamic_rerun_triggers = {}
    """.format(
            rerun_amount, rerun_trigger_text
        )
    )

    testdir.makepyfile(
        """
        import sys

        def test_all_seems_well_but():
            print('Please rerun me', file=sys.stderr)
    """
    )
    result = testdir.runpytest("-v")
    assert result.ret == pytest.ExitCode.TESTS_FAILED

    failed_amount = 1
    _assert_result_outcomes(result, dynamic_rerun=rerun_amount, failed=failed_amount)


@pytest.mark.parametrize(
    "print_output,should_rerun",
    [
        ("Rerun on this text", True),
        ("Also rerun on this one", True),
        ("But not on this one", False),
    ],
)
def test_can_handle_multiple_dynamic_rerun_triggers(
    testdir, print_output, should_rerun
):
    rerun_amount = 3
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_attempts = {}
        dynamic_rerun_schedule = * * * * * *
        dynamic_rerun_triggers = Rerun on this text
            Also rerun on this one
            Finally also check this one
    """.format(
            rerun_amount
        )
    )

    testdir.makepyfile(
        "def test_all_seems_well_but(): print('{}')".format(print_output)
    )
    result = testdir.runpytest("-v")

    if should_rerun:
        failed_amount = 1
        dynamic_rerun_amount = rerun_amount
        passed_amount = 0

        assert result.ret == pytest.ExitCode.TESTS_FAILED
    else:
        failed_amount = 0
        dynamic_rerun_amount = 0
        passed_amount = 1

        assert result.ret == pytest.ExitCode.OK

    _assert_result_outcomes(
        result,
        dynamic_rerun=dynamic_rerun_amount,
        failed=failed_amount,
        passed=passed_amount,
    )


@pytest.mark.parametrize(
    "rerun_regex,should_rerun",
    [
        ("My", True),
        ("print", True),
        ("^print", False),
        ("^My", True),
        ("output$", True),
        ("^output$", False),
        ("My.*output", True),
        ("^My.*output$", True),
        ("^My output$", False),
    ],
)
def test_dynamic_rerun_triggers_can_handle_regexes(testdir, rerun_regex, should_rerun):
    rerun_amount = 2
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_attempts = {}
        dynamic_rerun_schedule = * * * * * *
        dynamic_rerun_triggers = {}
    """.format(
            rerun_amount, rerun_regex
        )
    )

    testdir.makepyfile("def test_all_seems_well_but(): print('My print output')")
    result = testdir.runpytest("-v")

    if should_rerun:
        failed_amount = 1
        dynamic_rerun_amount = rerun_amount
        passed_amount = 0

        assert result.ret == pytest.ExitCode.TESTS_FAILED
    else:
        failed_amount = 0
        dynamic_rerun_amount = 0
        passed_amount = 1

        assert result.ret == pytest.ExitCode.OK

    _assert_result_outcomes(
        result,
        dynamic_rerun=dynamic_rerun_amount,
        failed=failed_amount,
        passed=passed_amount,
    )
