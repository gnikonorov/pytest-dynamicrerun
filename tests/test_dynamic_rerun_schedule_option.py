# This file contains tests specific to the dynamic_rerun_schedule option
import pytest
from helpers import _assert_result_outcomes


# TODO: test to make sure default value is actually selected ( use item.sleep_times )
@pytest.mark.parametrize(
    "rerun_schedule", [0, -1, 2.23, "foobar", "12 AM EST", "* * * * C *"]
)
def test_invalid_dynamic_rerun_schedule_ignored(testdir, rerun_schedule):
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_schedule = {}
    """.format(
            rerun_schedule
        )
    )

    testdir.makepyfile("def test_always_false(): assert False")
    result = testdir.runpytest("-v")
    result.stdout.fnmatch_lines(
        [
            "*Can't parse invalid dynamic rerun schedule '{}'. Ignoring dynamic rerun schedule.*".format(
                rerun_schedule
            )
        ]
    )
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(result, failed=1)


@pytest.mark.parametrize(
    "rerun_amount,rerun_regex,rerun_schedule,max_wait_seconds,should_rerun",
    [
        (99, "My", "* * * * * *", 0, True),
        (2, "My", "* * * * * */10", 9, True),
        (3, "My", "* * * * * */5", 4, True),
        (55, "^print", "* * * * * *", 0, False),
    ],
)
def test_dynamic_rerun_properly_adheres_to_schedule(
    testdir, rerun_amount, rerun_regex, rerun_schedule, max_wait_seconds, should_rerun
):
    if should_rerun:
        failed_amount = 1
        dynamic_rerun_amount = rerun_amount - failed_amount
        passed_amount = 0
    else:
        failed_amount = 0
        dynamic_rerun_amount = 0
        passed_amount = 1

    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_attempts = {}
        dynamic_rerun_schedule = {}
        dynamic_rerun_triggers = {}
    """.format(
            rerun_amount, rerun_schedule, rerun_regex
        )
    )

    testdir.makeconftest(
        """
        def pytest_sessionfinish(session, exitstatus):
            if {}:
                # A little hacky, but we know we can only ever have 1 item
                sleep_times_for_item = session.dynamic_rerun_items[0].dynamic_rerun_sleep_times
                assert len(sleep_times_for_item) == {}
                for sleep_time in sleep_times_for_item:
                    assert sleep_time.days == 0
                    assert sleep_time.seconds >= 0 and sleep_time.seconds <= {}
                    assert sleep_time.microseconds
            else:
                assert not session.dynamic_rerun_items
    """.format(
            should_rerun, dynamic_rerun_amount, max_wait_seconds
        )
    )

    testdir.makepyfile("def test_print_message(): print('My print message')")

    result = testdir.runpytest("-v")

    if should_rerun:
        assert result.ret == pytest.ExitCode.TESTS_FAILED
    else:
        assert result.ret == pytest.ExitCode.OK

    _assert_result_outcomes(
        result,
        dynamic_rerun=dynamic_rerun_amount,
        failed=failed_amount,
        passed=passed_amount,
    )
