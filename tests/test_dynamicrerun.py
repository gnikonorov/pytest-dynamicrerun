import pytest


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

    dynamic_rerun_attempts = 5
    failed_amount = 1
    result = testdir.runpytest(
        "-v",
        "--dynamic-rerun-attempts={}".format(dynamic_rerun_attempts),
        "--dynamic-rerun-schedule=* * * * * *",
    )

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(
        result,
        dynamic_rerun=dynamic_rerun_attempts - failed_amount,
        failed=failed_amount,
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
    dynamic_rerun_attempts = 5
    failed_amount = 1
    dynamic_rerun_amount = dynamic_rerun_attempts - failed_amount

    testdir.makeini(ini_text.format(dynamic_rerun_attempts))

    test_file_name = "test_output_properly_shown.py"
    test_name = "test_output"
    testdir.makepyfile("def {}(): {}".format(test_name, test_body))

    expected_output = []
    expected_output.append("=* test session starts *=")
    for rerun_attempt in range(dynamic_rerun_amount):
        expected_output.append(
            "*{}::{} DYNAMIC_RERUN*".format(test_file_name, test_name)
        )
    expected_output.append("*{}::{} FAILED*".format(test_file_name, test_name))

    expected_output.append("=* FAILURES *=")
    expected_output.append("_* {} *_".format(test_name))

    expected_output.append("=* Dynamically rerun tests *=")
    for rerun_attempt in range(dynamic_rerun_amount):
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
            failed_amount, dynamic_rerun_amount
        )
    )

    result = testdir.runpytest("-v")
    result.stdout.fnmatch_lines(expected_output)

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(
        result,
        dynamic_rerun=dynamic_rerun_attempts - failed_amount,
        failed=failed_amount,
    )


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
        ["*Rerun attempts must be a positive integer. Using default value 1*"]
    )
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(result, failed=1)


@pytest.mark.parametrize("rerun_amount", [1, 2, 10, 5])
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
    dynamic_rerun_amount = rerun_amount - failed_amount
    _assert_result_outcomes(
        result, dynamic_rerun=dynamic_rerun_amount, failed=failed_amount
    )


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
    assert foo == 20""",
            "19",
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


# TODO: add tests for different valid cron inputs to schedule, right now only default is used
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


def test_no_dynamic_reruns_by_default(testdir):
    testdir.makeini(
        """
        [pytest]
        dynamic_rerun_schedule = * * * * * *
    """
    )

    testdir.makepyfile("def test_always_false(): assert False")
    result = testdir.runpytest("-v")
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    _assert_result_outcomes(result, failed=1)


# TODO: add more tests for dynamic rerun triggers flag
#       - Still need tests for passing multiple triggers
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
def test_exceptions_outut_checked_by_dynamic_rerun_triggers(
    testdir, rerun_trigger_text
):
    rerun_amount = 99
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
    dynamic_rerun_amount = rerun_amount - failed_amount
    _assert_result_outcomes(
        result, dynamic_rerun=dynamic_rerun_amount, failed=failed_amount
    )


@pytest.mark.parametrize(
    "rerun_trigger_text", ["Please rerun me", "rerun", "Please", "me"]
)
def test_stdout_checked_by_dynamic_rerun_triggers(testdir, rerun_trigger_text):
    rerun_amount = 99
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
    dynamic_rerun_amount = rerun_amount - failed_amount
    _assert_result_outcomes(
        result, dynamic_rerun=dynamic_rerun_amount, failed=failed_amount
    )


@pytest.mark.parametrize(
    "rerun_trigger_text", ["Please rerun me", "rerun", "Please", "me"]
)
def test_stderr_checked_by_dynamic_rerun_triggers(testdir, rerun_trigger_text):
    rerun_amount = 99
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
    dynamic_rerun_amount = rerun_amount - failed_amount
    _assert_result_outcomes(
        result, dynamic_rerun=dynamic_rerun_amount, failed=failed_amount
    )


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
    rerun_amount = 99
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
        dynamic_rerun_amount = rerun_amount - failed_amount
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
