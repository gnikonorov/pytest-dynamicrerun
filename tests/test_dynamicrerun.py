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


# TODO: Add check to make sure dynamic_rerun_triggers flag respected
def test_plugin_flags_are_recognized(testdir):
    testdir.makepyfile("def test_assert_false(): assert False")

    dynamic_rerun_attempts = 3
    failed_amount = 1
    result = testdir.runpytest(
        "-v",
        "--dynamic-rerun-attempts={}".format(dynamic_rerun_attempts),
        "--dynamic-rerun-schedule=* * * * * *",
    )

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(
        result, dynamic_rerun=dynamic_rerun_attempts, failed=failed_amount,
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
        "--dynamic-rerun-schedule=* * * * *",
        "--dynamic-rerun-triggers=blah",
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

    testdir.makepyfile("def test_assert_false(): print('foo')")

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

    result = testdir.runpytest(
        "-v",
        "--dynamic-rerun-attempts={}".format(attempts),
        "--dynamic-rerun-schedule={}".format(rerun_schedule),
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
