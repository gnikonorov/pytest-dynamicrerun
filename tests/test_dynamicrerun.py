import pytest


def test_help_text_contains_plugin_options(testdir):
    result = testdir.runpytest("--help")
    result.stdout.fnmatch_lines(
        [
            "dynamicrerun:",
            "*--dynamic-rerun-attempts=DYNAMIC_RERUN_ATTEMPTS",
            "*--dynamic-rerun-errors=DYNAMIC_RERUN_ERRORS",
            "*--dynamic-rerun-schedule=DYNAMIC_RERUN_SCHEDULE",
            "*dynamic_rerun_attempts (string):",
            "*dynamic_rerun_errors (linelist):",
            "*dynamic_rerun_schedule (string):",
        ]
    )
    assert result.ret == 0


# TODO: Add similar test but for flags
@pytest.mark.parametrize(
    "ini_key_name,ini_key_set_value,ini_key_fetch_value",
    [
        ("dynamic_rerun_attempts", "213", "'213'"),
        ("dynamic_rerun_errors", "ValueError", "['ValueError']"),
        ("dynamic_rerun_schedule", "* * * * *", "'* * * * *'"),
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


# TODO: test to make sure default value is actually selected
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

    testdir.makepyfile("def test_always_true(): assert True")
    result = testdir.runpytest("-v")
    result.stdout.fnmatch_lines(
        ["*Rerun attempts must be a positive integer. Using default value 1*"]
    )


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

    testdir.makepyfile("def test_always_true(): assert True")
    result = testdir.runpytest("-v")
    result.stdout.fnmatch_lines(
        [
            "*Can't parse invalid dynamic rerun schedule '{}'. Ignoring dynamic rerun schedule.*".format(
                rerun_schedule
            )
        ]
    )
