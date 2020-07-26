import copy
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


# TODO: Check if this is errors or any freeform text
def _add_dynamic_rerun_errors_flag(parser):
    group = parser.getgroup(PLUGIN_NAME)
    group.addoption(
        "--dynamic-rerun-errors",
        action="append",
        dest="dynamic_rerun_errors",
        default=None,
        help="Set the errors that will be dynamically rerun ( by default all errors are dynamically rerun )",
    )

    parser.addini(
        "dynamic_rerun_errors",
        "default value for --dyamic-rerun-errors",
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


def _get_dynamic_rerun_errors_arg(item):
    dynamic_rerun_errors = None
    if item.session.config.option.dynamic_rerun_errors:
        dynamic_rerun_errors = item.session.config.option.dynamic_rerun_errors
    return dynamic_rerun_errors


def _is_rerunnable_error(item, report):
    if not report.failed:
        return False

    dynamic_rerun_errors = _get_dynamic_rerun_errors_arg(item)
    if not dynamic_rerun_errors:
        return True

    for rerun_regex in dynamic_rerun_errors:
        if re.search(rerun_regex, report.longrepr.reprcrash.message):
            return True

    return False


def pytest_addoption(parser):
    _add_dynamic_rerun_attempts_flag(parser)
    _add_dynamic_rerun_errors_flag(parser)
    _add_dynamic_rerun_schedule_flag(parser)


def pytest_report_teststatus(report):
    if report.outcome == "dynamically_rerun":
        return "dynamicrerun", "DR", ("DYNAMIC_RERUN", {"yellow": True})


def pytest_runtest_protocol(item, nextitem):
    # bail early if a falsey value was given for required args
    dynamic_rerun_schedule_arg = _get_dynamic_rerun_schedule_arg(item)
    if dynamic_rerun_schedule_arg is None:
        return

    dynamic_rerun_attempts_arg = _get_dynamic_rerun_attempts_arg(item)
    if dynamic_rerun_attempts_arg is None:
        return

    if item.session.num_dynamic_reruns_kicked_off > dynamic_rerun_attempts_arg:
        return True

    item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
    reports = runtestprotocol(item, nextitem=nextitem, log=False)
    for report in reports:
        will_run_again = (
            item.session.num_dynamic_reruns_kicked_off < dynamic_rerun_attempts_arg
        )
        if report.failed:
            if will_run_again and _is_rerunnable_error(item, report):
                report.outcome = "dynamically_rerun"
                item.ihook.pytest_runtest_logreport(report=report)
                # TODO: Need to properly copy this item object.
                #       If I can't copy it, its duplicated in report.
                #       Pytest issue raised: https://github.com/pytest-dev/pytest/issues/7543
                item.session.dynamic_rerun_items.append(copy.copy(item))
            else:
                report.outcome = "failed"
                item.ihook.pytest_runtest_logreport(report=report)
    item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)

    # if nextitem is None, we have finished running tests. Dynamically rerun any tests that failed
    if nextitem is None:
        item.session.num_dynamic_reruns_kicked_off += 1
        now_time = datetime.now()
        # NOTE: in the readme note that croniter does second repeats
        #       see https://github.com/kiorky/croniter#about-second-repeats
        time_iterator = croniter(dynamic_rerun_schedule_arg, now_time)

        time_delta = time_iterator.get_next(datetime) - now_time
        time.sleep(time_delta.seconds)

        rerun_items = item.session.dynamic_rerun_items
        for i, item in enumerate(rerun_items):
            next_item = rerun_items[i + 1] if i + 1 < len(rerun_items) else None
            pytest_runtest_protocol(item, next_item)

    return True


def pytest_sessionstart(session):
    session.dynamic_rerun_items = []
    session.num_dynamic_reruns_kicked_off = 0


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_sep("=", "Dynamically rerun tests")
    for report in terminalreporter.stats.get("dynamicrerun", []):
        terminalreporter.write_line(report.nodeid)


# @pytest.fixture
# def bar(request):
#    return request.config.option.dest_foo
