import pytest


# TODO: Determine if we want all the ini keys to be of type string or not
def test_help_text_contains_plugin_options(testdir):
    result = testdir.runpytest("--help")
    result.stdout.fnmatch_lines(
        [
            "dynamicrerun:",
            "*--dynamic-rerun-attempts=DYNAMIC_RERUN_ATTEMPTS",
            "*--dynamic-rerun-errors=DYNAMIC_RERUN_ERRORS",
            "*--dynamic-rerun-schedule=DYNAMIC_RERUN_SCHEDULE",
            "*dynamic_rerun_attempts (string):",
            "*dynamic_rerun_errors (string):",
            "*dynamic_rerun_schedule (string):",
        ]
    )
    assert result.ret == 0


@pytest.mark.parametrize(
    "ini_key_name,ini_key_value",
    [
        ("dynamic_rerun_attempts", "213"),
        ("dynamic_rerun_errors", "ValueError"),
        ("dynamic_rerun_schedule", "* * * * *"),
    ],
)
def test_plugin_options_are_ini_configurable(testdir, ini_key_name, ini_key_value):
    testdir.makeini(
        """
        [pytest]
        {} = {}
    """.format(
            ini_key_name, ini_key_value
        )
    )

    testdir.makepyfile(
        """
        import pytest

        @pytest.fixture
        def fetch_ini_key(request):
            return request.config.getini('{}')

        def test_ini_key_fetch(fetch_ini_key):
            assert fetch_ini_key == '{}'
    """.format(
            ini_key_name, ini_key_value
        )
    )

    result = testdir.runpytest("-v")
    result.stdout.fnmatch_lines(["*::test_ini_key_fetch PASSED*"])
    assert result.ret == 0
