# TODO: When different rerun schedules for items are supported, figure out how to batch runs.
#       After this is done, publush to PyPI
# NOTE: Warning support is broken ATM and may be broken until some pytest patches are made upstream
#       For now, this does NOT support warnings but here are 2 possible solutions:
#           We could use a combination of a global variable and `pytest_warning_captured`. This has issues
#           as it looks like warnings are not always processed with every run but only once upfront, and needs an
#           upstream patch.
#           Alternatively the warnings should be populated on the 'item' object which would be preferred.
#           This would need an upstream patch though the benefit of this approach is that we can neatly access
#           the warnings without checking pytest warning recorded
import re
import time
import warnings
from datetime import datetime
from datetime import timedelta

from _pytest.runner import runtestprotocol
from croniter import croniter

DEFAULT_RERUN_ATTEMPTS = 1
DEFAULT_RERUN_SCHEDULE = "* * * * * *"
MARKER_NAME = "dynamicrerun"
PLUGIN_NAME = "dynamicrerun"


def _add_dynamic_rerun_attempts_flag(parser):
    group = parser.getgroup(PLUGIN_NAME)
    group.addoption(
        "--dynamic-rerun-attempts",
        action="store",
        dest="dynamic_rerun_attempts",
        default=None,
        help="Set the amount of times reruns should be attempted ( defaults to 1 )",
    )

    parser.addini(
        "dynamic_rerun_attempts", "default value for --dynamic-rerun-attempts"
    )


def _add_dynamic_rerun_schedule_flag(parser):
    group = parser.getgroup(PLUGIN_NAME)
    group.addoption(
        "--dynamic-rerun-schedule",
        action="store",
        dest="dynamic_rerun_schedule",
        default=None,
        help="Set the time to attempt a rerun in using a cron like format ( e.g.: '* * * * *' )",
    )

    parser.addini("dynamic_rerun_schedule", "default value for --dyamic-rerun-schedule")


# TODO: As a follow up we can let each error define its own rerun amount here. But that should not be
#       part of the initial pass
def _add_dynamic_rerun_triggers_flag(parser):
    group = parser.getgroup(PLUGIN_NAME)
    group.addoption(
        "--dynamic-rerun-triggers",
        action="append",
        dest="dynamic_rerun_triggers",
        default=None,
        help="Set pytest output that will trigger dynamic reruns. By default all failing tests are dynamically rerun",
    )

    parser.addini(
        "dynamic_rerun_triggers",
        "default value for --dyamic-rerun-triggers",
        type="linelist",
    )


def _get_dynamic_rerun_schedule_arg(item):
    marker = item.get_closest_marker(MARKER_NAME)
    marker_param_name = "schedule"

    # The priority followed is: marker, then command line switch, then config INI file
    if marker and marker_param_name in marker.kwargs.keys():
        dynamic_rerun_arg = marker.kwargs[marker_param_name]
    elif item.session.config.option.dynamic_rerun_schedule:
        dynamic_rerun_arg = str(item.session.config.option.dynamic_rerun_schedule)
    else:
        dynamic_rerun_arg = item.session.config.getini("dynamic_rerun_schedule")

    if dynamic_rerun_arg is not None and not croniter.is_valid(dynamic_rerun_arg):
        warnings.warn(
            "Can't parse invalid dynamic rerun schedule '{}'. "
            "Ignoring dynamic rerun schedule and using default '{}'".format(
                dynamic_rerun_arg, DEFAULT_RERUN_SCHEDULE
            )
        )
        dynamic_rerun_arg = DEFAULT_RERUN_SCHEDULE

    return dynamic_rerun_arg


def _get_dynamic_rerun_attempts_arg(item):
    marker = item.get_closest_marker(MARKER_NAME)
    marker_param_name = "attempts"
    warnings_text = "Rerun attempts must be a positive integer. Using default value {}".format(
        DEFAULT_RERUN_ATTEMPTS
    )

    # The priority followed is: marker, then command line switch, then config INI file
    if marker and marker_param_name in marker.kwargs.keys():
        rerun_attempts = marker.kwargs[marker_param_name]
    elif item.session.config.option.dynamic_rerun_attempts:
        rerun_attempts = item.session.config.option.dynamic_rerun_attempts
    else:
        rerun_attempts = item.session.config.getini("dynamic_rerun_attempts")

    try:
        rerun_attempts = int(rerun_attempts)
    except ValueError:
        warnings.warn(warnings_text)
        rerun_attempts = DEFAULT_RERUN_ATTEMPTS

    if rerun_attempts <= 0:
        warnings.warn(warnings_text)
        rerun_attempts = DEFAULT_RERUN_ATTEMPTS

    return rerun_attempts


def _get_dynamic_rerun_triggers_arg(item):
    marker = item.get_closest_marker(MARKER_NAME)
    marker_param_name = "triggers"

    # The priority followed is: marker, then command line switch, then config INI file
    if marker and marker_param_name in marker.kwargs.keys():
        dynamic_rerun_triggers = marker.kwargs[marker_param_name]
    elif item.session.config.option.dynamic_rerun_triggers:
        dynamic_rerun_triggers = item.session.config.option.dynamic_rerun_triggers
    else:
        dynamic_rerun_triggers = item.session.config.getini("dynamic_rerun_triggers")

    if not isinstance(dynamic_rerun_triggers, list):
        return [dynamic_rerun_triggers]
    return dynamic_rerun_triggers


def _is_rerun_triggering_report(item, report):
    dynamic_rerun_triggers = _get_dynamic_rerun_triggers_arg(item)
    if not dynamic_rerun_triggers:
        return report.failed

    item.dynamic_rerun_triggers = dynamic_rerun_triggers

    for rerun_regex in item.dynamic_rerun_triggers:
        # NOTE: Checking for both report.longrepr and reprcrash on report.longrepr is intentional
        report_has_reprcrash = report.longrepr and hasattr(report.longrepr, "reprcrash")
        if report_has_reprcrash and re.search(
            rerun_regex, report.longrepr.reprcrash.message
        ):
            return True

        for section in report.sections:
            section_title = section[0]
            section_text = section[1]
            if section_title in [
                "Captured stdout call",
                "Captured stderr call",
            ] and re.search(rerun_regex, section_text):
                return True

    return False


def _rerun_dynamically_failing_items(
    session, max_allowed_dynamic_rerun_attempts, dynamic_rerun_schedule
):
    # NOTE: We always sleep one second to ensure that we wait for the next interval instead of running
    #       multiple times in the same one
    #       For example, if the cron schedule is every second ( * * * * * * ) and the test takes .1
    #       seconds to run, we could end up rerunning the test in the same second it failed without
    #       this required sleep. The same idea applies to other cron formats
    rerun_items = session.dynamic_rerun_items
    for i, item in enumerate(rerun_items):
        # If this is a previously failing test that now passes, don't run it
        if (
            hasattr(item, "_dynamic_rerun_terminated")
            and item._dynamic_rerun_terminated
        ):
            continue

        item.num_dynamic_reruns_kicked_off += 1
        if item.num_dynamic_reruns_kicked_off > item.max_allowed_dynamic_rerun_attempts:
            continue

        if not hasattr(item, "dynamic_rerun_sleep_times"):
            item.dynamic_rerun_sleep_times = []

        # TODO: This is WRONG. We should only be sleeping the mandatory sleep time once before we begin this loop
        #       I'm leaving it here as a temporary thing while I migrate num_dynamic_rerun_attempts to the item object
        manditory_sleep_time = 1
        time.sleep(manditory_sleep_time)

        post_sleep_time = datetime.now()
        time_iterator = croniter(dynamic_rerun_schedule, post_sleep_time)

        next_allowed_run_time = time_iterator.get_next(datetime) - post_sleep_time
        time.sleep(next_allowed_run_time.total_seconds())

        real_sleep_time = (
            timedelta(seconds=manditory_sleep_time) + next_allowed_run_time
        )
        item.dynamic_rerun_sleep_times.append(real_sleep_time)

        next_item = rerun_items[i + 1] if i + 1 < len(rerun_items) else None
        pytest_runtest_protocol(item, next_item)

    return True


def pytest_addoption(parser):
    _add_dynamic_rerun_attempts_flag(parser)
    _add_dynamic_rerun_triggers_flag(parser)
    _add_dynamic_rerun_schedule_flag(parser)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "{}(attempts=N, triggers=[REGEX], schedule=S): mark test as dynamically re-runnable. "
        "Attempt a rerun up to N times on anything that matches a regex in the list [REGEX], "
        "following cron formatted schedule S".format(MARKER_NAME),
    )


def pytest_report_teststatus(report):
    if report.outcome == "dynamically_rerun":
        return "dynamicrerun", "DR", ("DYNAMIC_RERUN", {"yellow": True})


def pytest_runtest_protocol(item, nextitem):
    # bail early if a falsey value was given for required args
    dynamic_rerun_schedule = _get_dynamic_rerun_schedule_arg(item)
    if dynamic_rerun_schedule is None:
        return

    max_allowed_dynamic_rerun_attempts = _get_dynamic_rerun_attempts_arg(item)
    if max_allowed_dynamic_rerun_attempts is None:
        return

    # TODO: We should refactor the setting of public fields on an item to a method
    item.dynamic_rerun_schedule = dynamic_rerun_schedule
    item.max_allowed_dynamic_rerun_attempts = max_allowed_dynamic_rerun_attempts

    # TODO: num_dynamic_reruns_kicked_off needs to be changed to 0
    #       having it at 1 doesn't make sense
    if not hasattr(item, "num_dynamic_reruns_kicked_off"):
        item.num_dynamic_reruns_kicked_off = 1

    item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
    reports = runtestprotocol(item, nextitem=nextitem, log=False)

    will_run_again = (
        item.num_dynamic_reruns_kicked_off < item.max_allowed_dynamic_rerun_attempts
    )

    for report in reports:
        rerun_triggering = _is_rerun_triggering_report(item, report)
        if rerun_triggering:
            item._dynamic_rerun_terminated = False

            if will_run_again:
                report.outcome = "dynamically_rerun"
                if item not in item.session.dynamic_rerun_items:
                    item.session.dynamic_rerun_items.append(item)

                if not report.failed:
                    item.ihook.pytest_runtest_logreport(report=report)
                    break
            elif report.when == "call" and not report.failed:
                # only mark 'call' as failed to avoid over-reporting errors
                # 'call' was picked over setup or teardown since it makes the most sense
                # to mark the actual execution as bad in passing test cases
                report.outcome = "failed"
        else:
            item._dynamic_rerun_terminated = True

        item.ihook.pytest_runtest_logreport(report=report)
    item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)

    # if nextitem is None, we have finished running tests. Dynamically rerun any tests that failed
    if nextitem is None:
        return _rerun_dynamically_failing_items(
            item.session,
            item.max_allowed_dynamic_rerun_attempts,
            item.dynamic_rerun_schedule,
        )

    return True


def pytest_sessionstart(session):
    # TODO: Will need to revisit how this will look when mutliple items with different rerun schedules
    #       exist
    session.dynamic_rerun_items = []


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_sep("=", "Dynamically rerun tests")
    for report in terminalreporter.stats.get("dynamicrerun", []):
        terminalreporter.write_line(report.nodeid)
