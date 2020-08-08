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

from _pytest.runner import runtestprotocol
from croniter import croniter

DEFAULT_RERUN_ATTEMPTS = 1
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


# TODO: Add tests for this flag and finish implementing it
#       By default all failures should force a rerun
#       If we pass in a value to this flag, any output emitted by pytest
#       that matches the text should trigger a rerun and all other failures should be hard failures
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


# NOTE: See how we can refactor the _get methods into one method
#       Or if we even need them, since they're not really doing anything
#       Also need to check what happens to plugin if installed and nothing is passed
def _get_dynamic_rerun_schedule_arg(item):
    dynamic_rerun_arg = None
    if item.session.config.option.dynamic_rerun_schedule:
        dynamic_rerun_arg = str(item.session.config.option.dynamic_rerun_schedule)
    else:
        # fall back to ini config if no command line switch provided
        dynamic_rerun_arg = item.session.config.getini("dynamic_rerun_schedule")

    if dynamic_rerun_arg is not None and not croniter.is_valid(dynamic_rerun_arg):
        warnings.warn(
            "Can't parse invalid dynamic rerun schedule '{}'. Ignoring dynamic rerun schedule.".format(
                dynamic_rerun_arg
            )
        )
        dynamic_rerun_arg = None

    return dynamic_rerun_arg


def _get_dynamic_rerun_attempts_arg(item):
    warnings_text = "Rerun attempts must be a positive integer. Using default value {}".format(
        DEFAULT_RERUN_ATTEMPTS
    )

    if item.session.config.option.dynamic_rerun_attempts:
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
    dynamic_rerun_triggers = None
    if item.session.config.option.dynamic_rerun_triggers:
        dynamic_rerun_triggers = item.session.config.option.dynamic_rerun_triggers
    else:
        dynamic_rerun_triggers = item.session.config.getini("dynamic_rerun_triggers")

    return dynamic_rerun_triggers


def _is_rerun_triggering_report(item, report):
    dynamic_rerun_triggers = _get_dynamic_rerun_triggers_arg(item)
    if not dynamic_rerun_triggers:
        return report.failed

    for rerun_regex in dynamic_rerun_triggers:
        if report.longrepr and re.search(
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
    session, max_allowed_rerun_attempts, dynamic_rerun_schedule
):
    session.num_dynamic_reruns_kicked_off += 1
    if session.num_dynamic_reruns_kicked_off > max_allowed_rerun_attempts:
        return True

    now_time = datetime.now()
    time_iterator = croniter(dynamic_rerun_schedule, now_time)

    time_delta = time_iterator.get_next(datetime) - now_time
    time.sleep(time_delta.seconds)

    rerun_items = session.dynamic_rerun_items
    for i, item in enumerate(rerun_items):
        # TODO: Add tests for sleep times
        if not hasattr(item, "sleep_times"):
            item.sleep_times = []
        item.sleep_times.append(time_delta.seconds)

        next_item = rerun_items[i + 1] if i + 1 < len(rerun_items) else None
        pytest_runtest_protocol(item, next_item)

    return True


def pytest_addoption(parser):
    _add_dynamic_rerun_attempts_flag(parser)
    _add_dynamic_rerun_triggers_flag(parser)
    _add_dynamic_rerun_schedule_flag(parser)


def pytest_report_teststatus(report):
    if report.outcome == "dynamically_rerun":
        return "dynamicrerun", "DR", ("DYNAMIC_RERUN", {"yellow": True})


def pytest_runtest_protocol(item, nextitem):
    # bail early if a falsey value was given for required args
    dynamic_rerun_schedule = _get_dynamic_rerun_schedule_arg(item)
    if dynamic_rerun_schedule is None:
        return

    max_allowed_rerun_attempts = _get_dynamic_rerun_attempts_arg(item)
    if max_allowed_rerun_attempts is None:
        return

    item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
    reports = runtestprotocol(item, nextitem=nextitem, log=False)

    will_run_again = (
        item.session.num_dynamic_reruns_kicked_off < max_allowed_rerun_attempts
    )

    should_queue_for_rerun = False
    for report in reports:
        rerun_triggering = _is_rerun_triggering_report(item, report)
        if rerun_triggering:
            if will_run_again:
                should_queue_for_rerun = True

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

        item.ihook.pytest_runtest_logreport(report=report)
    item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)

    if not should_queue_for_rerun:
        if item in item.session.dynamic_rerun_items:
            item.session.dynamic_rerun_items.remove(item)
        return True

    # if nextitem is None, we have finished running tests. Dynamically rerun any tests that failed
    if nextitem is None:
        return _rerun_dynamically_failing_items(
            item.session, max_allowed_rerun_attempts, dynamic_rerun_schedule
        )

    return True


def pytest_sessionstart(session):
    session.dynamic_rerun_items = []

    # NOTE: start count at 1 instead of 0 since we are on the first run
    #       so, if we say we want 2 dynamic run attempts, that means we want 2 test runs
    session.num_dynamic_reruns_kicked_off = 1


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_sep("=", "Dynamically rerun tests")
    for report in terminalreporter.stats.get("dynamicrerun", []):
        terminalreporter.write_line(report.nodeid)


# @pytest.fixture
# def bar(request):
#    return request.config.option.dest_foo
