# This file contains tests specific to the dynamic_rerun_attempts option
import pytest
from helpers import _assert_result_outcomes


@pytest.mark.parametrize("rerun_amount", [0, -1, 2.23, "foobar"])
def test_non_positive_integer_rerun_attempts_rejected(testdir, rerun_amount):
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_schedule = * * * * * *
        dynamic_rerun_attempts = {}
    """.format(
            rerun_amount
        )
    )

    testdir.makepyfile("def test_always_false(): assert False")
    result = testdir.runpytest("-v")
    result.stdout.fnmatch_lines(
        ["*Rerun attempts must be a positive integer. Using default value '1'*"]
    )
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(result, dynamic_rerun=1, failed=1)


@pytest.mark.parametrize("rerun_amount", [1, 2, 3])
def test_positive_integer_dynamic_rerun_attempts_accepted(testdir, rerun_amount):
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_schedule = * * * * * *
        dynamic_rerun_attempts = {}
    """.format(
            rerun_amount
        )
    )

    testdir.makepyfile("def test_always_false(): assert False")
    result = testdir.runpytest("-v")
    assert result.ret == pytest.ExitCode.TESTS_FAILED

    failed_amount = 1
    _assert_result_outcomes(result, dynamic_rerun=rerun_amount, failed=failed_amount)


@pytest.mark.parametrize(
    "pytest_file,expected_reruns",
    [
        (
            """
foo = 0
def test_foo():
    global foo
    foo += 1
    assert foo == 2""",
            "1",
        ),
        (
            """
foo = 0
def test_foo():
    global foo
    assert foo == 0""",
            "0",
        ),
        (
            """
foo = 0
def test_foo():
    global foo
    foo += 1
    assert foo == 5""",
            "4",
        ),
    ],
)
def test_success_stops_dynamic_rerun_attempts(testdir, pytest_file, expected_reruns):
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_schedule = * * * * * *
        dynamic_rerun_attempts = 99
    """
    )

    testdir.makepyfile(pytest_file)
    result = testdir.runpytest("-v")
    assert result.ret == pytest.ExitCode.OK

    _assert_result_outcomes(result, dynamic_rerun=expected_reruns, passed=1)


def test_one_dynamic_rerun_attempt_by_default(testdir):
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_schedule = * * * * * *
    """
    )

    testdir.makepyfile("def test_always_false(): assert False")
    result = testdir.runpytest("-v")
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(result, dynamic_rerun=1, failed=1)
