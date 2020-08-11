import time
from datetime import datetime

import pytest
from helpers import _assert_result_outcomes


def test_help_text_contains_plugin_options(testdir):
    result = testdir.runpytest("--help")
    result.stdout.fnmatch_lines(
        [
            "dynamicrerun:",
            "*--dynamic-rerun-attempts=DYNAMIC_RERUN_ATTEMPTS",
            "*--dynamic-rerun-triggers=DYNAMIC_RERUN_TRIGGERS",
            "*--dynamic-rerun-schedule=DYNAMIC_RERUN_SCHEDULE",
            "*dynamic_rerun_attempts (string):",
            "*dynamic_rerun_triggers (linelist):",
            "*dynamic_rerun_schedule (string):",
        ]
    )
    assert result.ret == 0


def test_plugin_flags_are_recognized(testdir):
    testdir.makepyfile(
        """
        def test_prints_foo():
            print("foo")

        def test_prints_bar():
            print("bar")
        """
    )

    dynamic_rerun_attempts = 3
    failed_amount = 1
    passed_amount = 1

    result = testdir.runpytest(
        "-v",
        "--dynamic-rerun-attempts={}".format(dynamic_rerun_attempts),
        "--dynamic-rerun-schedule='* * * * * *'",
        "--dynamic-rerun-triggers=foo",
    )

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(
        result,
        dynamic_rerun=dynamic_rerun_attempts,
        failed=failed_amount,
        passed=passed_amount,
    )


@pytest.mark.parametrize(
    "ini_key_name,ini_key_set_value,ini_key_fetch_value",
    [
        ("dynamic_rerun_attempts", "213", "'213'"),
        ("dynamic_rerun_triggers", "ValueError", "['ValueError']"),
        (
            "dynamic_rerun_triggers",
            "ValueError\n\tAssertionError",
            "['ValueError', 'AssertionError']",
        ),
        ("dynamic_rerun_schedule", "* * * * * *", "'* * * * * *'"),
    ],
)
def test_plugin_options_are_ini_configurable(
    testdir, ini_key_name, ini_key_set_value, ini_key_fetch_value
):
    testdir.makeini(
        """
[pytest]
{} = {}
    """.format(
            ini_key_name, ini_key_set_value
        )
    )

    testdir.makepyfile(
        """
        import pytest

        @pytest.fixture
        def fetch_ini_key(request):
            return request.config.getini('{}')

        def test_ini_key_fetch(fetch_ini_key):
            assert fetch_ini_key == {}
    """.format(
            ini_key_name, ini_key_fetch_value
        )
    )

    result = testdir.runpytest("-v")
    result.stdout.fnmatch_lines(["*::test_ini_key_fetch PASSED*"])
    assert result.ret == 0
    _assert_result_outcomes(result, passed=1)


def test_mark_takes_precedence_over_flags(testdir):
    attempts = 5
    failed_amount = 1

    rerun_triggers = "foo"
    rerun_schedule = "* * * * * *"

    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.dynamicrerun(attempts={}, triggers="{}", schedule="{}")
        def test_assert_false():
            print("foo")
    """.format(
            attempts, rerun_triggers, rerun_schedule
        )
    )

    testdir.makeconftest(
        """
        def pytest_sessionfinish(session, exitstatus):
            # a little hacky, but we know we can only ever have 1 item
            rerun_item = session.dynamic_rerun_items[0]

            # first, check the sleep times
            sleep_times_for_item = rerun_item.dynamic_rerun_sleep_times
            assert len(sleep_times_for_item) == {0}
            for sleep_time in sleep_times_for_item:
                assert sleep_time.days == 0
                assert sleep_time.seconds >= 0
                assert sleep_time.microseconds

            # Then, the triggers, schedule, and rerun attempts
            assert rerun_item.dynamic_rerun_triggers == ["{1}"]
            assert rerun_item.dynamic_rerun_schedule == "{2}"
            assert rerun_item.max_allowed_dynamic_rerun_attempts == {0}
    """.format(
            attempts, rerun_triggers, rerun_schedule
        )
    )

    result = testdir.runpytest(
        "-v",
        "--dynamic-rerun-attempts=2",
        "--dynamic-rerun-schedule='* * * * *'",
        "--dynamic-rerun-triggers='blah'",
    )

    assert result.ret == pytest.ExitCode.TESTS_FAILED

    _assert_result_outcomes(
        result, dynamic_rerun=attempts, failed=failed_amount,
    )


def test_mark_takes_precedence_over_ini_file(testdir):
    attempts = 5
    failed_amount = 1

    rerun_triggers = "foo"
    rerun_schedule = "* * * * * *"

    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.dynamicrerun(attempts={}, triggers="{}", schedule="{}")
        def test_assert_false():
            print("foo")
    """.format(
            attempts, rerun_triggers, rerun_schedule
        )
    )

    testdir.makeconftest(
        """
        def pytest_sessionfinish(session, exitstatus):
            # a little hacky, but we know we can only ever have 1 item
            rerun_item = session.dynamic_rerun_items[0]

            # first, check the sleep times
            sleep_times_for_item = rerun_item.dynamic_rerun_sleep_times
            assert len(sleep_times_for_item) == {0}
            for sleep_time in sleep_times_for_item:
                assert sleep_time.days == 0
                assert sleep_time.seconds >= 0
                assert sleep_time.microseconds

            # Then, the triggers, schedule, and rerun attempts
            assert rerun_item.dynamic_rerun_triggers == ["{1}"]
            assert rerun_item.dynamic_rerun_schedule == "{2}"
            assert rerun_item.max_allowed_dynamic_rerun_attempts == {0}
    """.format(
            attempts, rerun_triggers, rerun_schedule
        )
    )

    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_attempts = 2
        dynamic_rerun_schedule = * * * * *
        dynamic_rerun_triggers = blah
    """
    )

    result = testdir.runpytest("-v")

    assert result.ret == pytest.ExitCode.TESTS_FAILED

    _assert_result_outcomes(
        result, dynamic_rerun=attempts, failed=failed_amount,
    )


def test_flags_take_precedence_over_ini_file(testdir):
    attempts = 5
    failed_amount = 1

    rerun_triggers = "foo"
    rerun_schedule = "* * * * * *"

    testdir.makepyfile("def test_print_foo(): print('foo')")

    testdir.makeconftest(
        """
        def pytest_sessionfinish(session, exitstatus):
            # a little hacky, but we know we can only ever have 1 item
            rerun_item = session.dynamic_rerun_items[0]

            # first, check the sleep times
            sleep_times_for_item = rerun_item.dynamic_rerun_sleep_times
            assert len(sleep_times_for_item) == {0}
            for sleep_time in sleep_times_for_item:
                assert sleep_time.days == 0
                assert sleep_time.seconds >= 0
                assert sleep_time.microseconds

            # Then, the triggers, schedule, and rerun attempts
            assert rerun_item.dynamic_rerun_triggers == ["{1}"]
            assert rerun_item.dynamic_rerun_schedule == "{2}"
            assert rerun_item.max_allowed_dynamic_rerun_attempts == {0}
    """.format(
            attempts, rerun_triggers, rerun_schedule
        )
    )

    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_attempts = 2
        dynamic_rerun_schedule = * * * * *
        dynamic_rerun_triggers = blah
    """
    )

    # NOTE: Intentionally leaving dynamic-rerun-triggers unquoted.
    #       When having it quoted this test fails, but I verified that
    #       failure will not happen, and that the test behaves as expected
    #       when run via command line. Seems to be a testdir bug
    result = testdir.runpytest(
        "-v",
        "--dynamic-rerun-attempts={}".format(attempts),
        "--dynamic-rerun-schedule='{}'".format(rerun_schedule),
        "--dynamic-rerun-triggers={}".format(rerun_triggers),
    )

    assert result.ret == pytest.ExitCode.TESTS_FAILED

    _assert_result_outcomes(
        result, dynamic_rerun=attempts, failed=failed_amount,
    )


@pytest.mark.parametrize(
    "ini_text,test_body,would_normally_pass",
    [
        (
            """
            [pytest]
            dynamic_rerun_schedule = * * * * * *
            dynamic_rerun_attempts = {}
            dynamic_rerun_triggers = I will pass""",
            "print('I will pass')",
            True,
        ),
        (
            """
            [pytest]
            dynamic_rerun_schedule = * * * * * *
            dynamic_rerun_attempts = {}""",
            "assert False",
            False,
        ),
    ],
)
def test_output_properly_shown(testdir, ini_text, test_body, would_normally_pass):
    dynamic_rerun_attempts = 3
    failed_amount = 1

    testdir.makeini(ini_text.format(dynamic_rerun_attempts))

    test_file_name = "test_output_properly_shown.py"
    test_name = "test_output"
    testdir.makepyfile("def {}(): {}".format(test_name, test_body))

    expected_output = []
    expected_output.append("=* test session starts *=")
    for rerun_attempt in range(dynamic_rerun_attempts):
        expected_output.append(
            "*{}::{} DYNAMIC_RERUN*".format(test_file_name, test_name)
        )
    expected_output.append("*{}::{} FAILED*".format(test_file_name, test_name))

    expected_output.append("=* FAILURES *=")
    expected_output.append("_* {} *_".format(test_name))

    expected_output.append("=* Dynamically rerun tests *=")
    for rerun_attempt in range(dynamic_rerun_attempts):
        expected_output.append("*{}::{}".format(test_file_name, test_name))

    expected_output.append("=* short test summary info *=")
    if would_normally_pass:
        expected_output.append("FAILED {}::{}*".format(test_file_name, test_name))
    else:
        expected_output.append(
            "FAILED {}::{} - {}*".format(test_file_name, test_name, test_body)
        )

    expected_output.append(
        "=*{} failed, {} dynamicrerun in *s *=".format(
            failed_amount, dynamic_rerun_attempts
        )
    )

    result = testdir.runpytest("-v")
    result.stdout.fnmatch_lines(expected_output)

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(
        result, dynamic_rerun=dynamic_rerun_attempts, failed=failed_amount,
    )


@pytest.mark.parametrize(
    "test_body",
    [
        """
        import pytest

        def test_will_pass():
            assert True

        @pytest.mark.dynamicrerun(attempts=3, triggers="foo", schedule="* * * * * *")
        def test_will_dynamically_rerun():
            print("foo")

        def test_will_fail():
            assert False
        """,
        """
        import pytest

        def test_will_pass():
            assert True

        def test_will_fail():
            assert False

        @pytest.mark.dynamicrerun(attempts=3, triggers="foo", schedule="* * * * * *")
        def test_will_dynamically_rerun():
            print("foo")
        """,
        """
        import pytest

        def test_will_fail():
            assert False

        def test_will_pass():
            assert True

        @pytest.mark.dynamicrerun(attempts=3, triggers="foo", schedule="* * * * * *")
        def test_will_dynamically_rerun():
            print("foo")
        """,
        """
        import pytest

        def test_will_fail():
            assert False

        @pytest.mark.dynamicrerun(attempts=3, triggers="foo", schedule="* * * * * *")
        def test_will_dynamically_rerun():
            print("foo")

        def test_will_pass():
            assert True
        """,
        """
        import pytest

        @pytest.mark.dynamicrerun(attempts=3, triggers="foo", schedule="* * * * * *")
        def test_will_dynamically_rerun():
            print("foo")

        def test_will_fail():
            assert False

        def test_will_pass():
            assert True
        """,
        """
        import pytest

        @pytest.mark.dynamicrerun(attempts=3, triggers="foo", schedule="* * * * * *")
        def test_will_dynamically_rerun():
            print("foo")

        def test_will_pass():
            assert True

        def test_will_fail():
            assert False
        """,
    ],
)
def test_triggering_passing_and_failing_tests_properly_run_in_same_collection(
    testdir, test_body
):
    testdir.makepyfile(test_body)

    result = testdir.runpytest("-v")
    assert result.ret == pytest.ExitCode.TESTS_FAILED

    _assert_result_outcomes(result, dynamic_rerun=3, failed=2, passed=1)


def test_dynamic_reruns_batched_by_rerun_time(testdir):
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.dynamicrerun(attempts=3, triggers="foo", schedule="* * * * * *")
        def test_dynamically_rerun_every_second_a():
            print("foo")

        @pytest.mark.dynamicrerun(attempts=4, triggers="foo", schedule="* * * * * *")
        def test_dynamically_rerun_every_second_b():
            print("foo")

        @pytest.mark.dynamicrerun(attempts=11, triggers="foo", schedule="* * * * * *")
        def test_dynamically_rerun_every_second_c():
            print("foo")

        @pytest.mark.dynamicrerun(attempts=2, triggers="foo", schedule="* * * * * */5")
        def test_dynamically_rerun_every_five_seconds_a():
            print("foo")

        @pytest.mark.dynamicrerun(attempts=3, triggers="foo", schedule="* * * * * */5")
        def test_dynamically_rerun_every_five_seconds_b():
            print("foo")
        """
    )

    expected_stdout = [
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_a DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_b DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_five_seconds_a DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_five_seconds_b DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_a DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_b DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_a DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_b DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_a FAILED*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_b DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_b FAILED*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_five_seconds_a DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_five_seconds_b DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_five_seconds_a FAILED*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_five_seconds_b DYNAMIC_RERUN*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_second_c FAILED*",
        "*test_dynamic_reruns_batched_by_rerun_time.py::test_dynamically_rerun_every_five_seconds_b FAILED*",
    ]

    # wait until seconds are at a *0 value for consistency ( 00, 10, 20, 30, ..., etc )
    # this isn't exactly perfect since microseconds will be non zero, but it's close enough
    current_time = datetime.now()

    sleep_time_microseconds = 1 - (current_time.microsecond / 1000000)
    sleep_time_seconds = 10 - (current_time.second % 10)
    if sleep_time_microseconds != 0:
        sleep_time_seconds -= 1

    sleep_time = sleep_time_seconds + sleep_time_microseconds
    time.sleep(sleep_time)

    result = testdir.runpytest("-v")

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.stdout.fnmatch_lines(expected_stdout)

    _assert_result_outcomes(result, dynamic_rerun=23, failed=5)


def test_plugin_doesnt_reread_old_sections_on_rerun(testdir):
    # NOTE: We intentionally raise an exception instead of printing something else
    #       since exceptions don't add to the report.sections object
    testdir.makepyfile(
        """
        COUNTER = 0

        def test_usually_prints_foo():
            global COUNTER
            COUNTER = COUNTER + 1

            if COUNTER == 5:
                raise ValueError("bar")
            else:
                print("foo")
        """
    )

    result = testdir.runpytest(
        "-v",
        "--dynamic-rerun-attempts=10",
        "--dynamic-rerun-schedule='* * * * * */5'",
        "--dynamic-rerun-triggers=foo",
    )

    assert result.ret == pytest.ExitCode.TESTS_FAILED

    _assert_result_outcomes(result, dynamic_rerun=4, failed=1)
