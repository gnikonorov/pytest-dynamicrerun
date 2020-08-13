# This file contains tests specific to the dynamic_rerun_disabled option
import pytest
from helpers import _assert_result_outcomes


def test_dynamic_rerun_disabled_false_by_default(testdir):
    dynamic_rerun_attempts = 3

    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_attempts = {}
        dynamic_rerun_schedule = * * * * * *
    """.format(
            dynamic_rerun_attempts
        )
    )

    testdir.makepyfile("def test_always_false(): assert False")

    result = testdir.runpytest("-v")

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(result, dynamic_rerun=dynamic_rerun_attempts, failed=1)


@pytest.mark.parametrize(
    "dynamic_rerun_disabled",
    ["TRUE", "True", "TrUe", "true", "y", "yes", "t", "true", "on", "1"],
)
def test_dynamic_rerun_disabled_works_for_true_values(testdir, dynamic_rerun_disabled):
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_attempts = 3
        dynamic_rerun_disabled = {}
        dynamic_rerun_schedule = * * * * * *
    """.format(
            dynamic_rerun_disabled
        )
    )

    testdir.makepyfile("def test_always_false(): assert False")

    result = testdir.runpytest("-v")

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(result, dynamic_rerun=0, failed=1)


@pytest.mark.parametrize(
    "dynamic_rerun_disabled",
    [
        "doit",
        "ok",
        "fine",
        "n",
        "NO",
        "FaLsE",
        "OFF",
        "noway",
        "",
        "stopit",
        "123",
        "0",
    ],
)
def test_dynamic_rerun_disabled_works_for_false_values(testdir, dynamic_rerun_disabled):
    dynamic_rerun_attempts = 3

    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_attempts = {}
        dynamic_rerun_disabled = {}
        dynamic_rerun_schedule = * * * * * *
    """.format(
            dynamic_rerun_attempts, dynamic_rerun_disabled
        )
    )

    testdir.makepyfile("def test_always_false(): assert False")

    result = testdir.runpytest("-v")

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(result, dynamic_rerun=dynamic_rerun_attempts, failed=1)
