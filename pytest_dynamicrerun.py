# TODO: Dont count dynamic_rerun resulting runs to the pytest progress report
# TODO: Allow option to dynamically rerun on certain marks
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
DEFAULT_RERUN_SCHEDULE = "* * * * * *"
MARKER_NAME = "dynamicrerun"
PLUGIN_NAME = "dynamicrerun"

DYNAMIC_RERUN_ATTEMPTS_DEST_VAR_NAME = "dynamic_rerun_attempts"
DYNAMIC_RERUN_SCHEDULE_DEST_VAR_NAME = "dynamic_rerun_schedule"
DYNMAIC_RERUN_TRIGGERS_DEST_VAR_NAME = "dynamic_rerun_triggers"


def _add_dynamic_rerun_attempts_flag(parser):
    group = parser.getgroup(PLUGIN_NAME)
    group.addoption(
        "--dynamic-rerun-attempts",
        action="store",
        dest=DYNAMIC_RERUN_ATTEMPTS_DEST_VAR_NAME,
        default=None,
        help="Set the amount of times reruns should be attempted ( defaults to 1 )",
    )

    parser.addini(
        DYNAMIC_RERUN_ATTEMPTS_DEST_VAR_NAME,
        "default value for --dynamic-rerun-attempts",
    )


def _add_dynamic_rerun_schedule_flag(parser):
    group = parser.getgroup(PLUGIN_NAME)
    group.addoption(
        "--dynamic-rerun-schedule",
        action="store",
        dest=DYNAMIC_RERUN_SCHEDULE_DEST_VAR_NAME,
        default=None,
        help="Set the time to attempt a rerun in using a cron like format ( e.g.: '* * * * *' )",
    )

    parser.addini(
        DYNAMIC_RERUN_SCHEDULE_DEST_VAR_NAME,
        "default value for --dyamic-rerun-schedule",
    )


# TODO: As a follow up we can let each error define its own rerun amount here. But that should not be
#       part of the initial pass
def _add_dynamic_rerun_triggers_flag(parser):
    group = parser.getgroup(PLUGIN_NAME)
    group.addoption(
        "--dynamic-rerun-triggers",
        action="append",
        dest=DYNMAIC_RERUN_TRIGGERS_DEST_VAR_NAME,
        default=None,
        help="Set pytest output that will trigger dynamic reruns. By default all failing tests are dynamically rerun",
    )

    parser.addini(
        DYNMAIC_RERUN_TRIGGERS_DEST_VAR_NAME,
        "default value for --dyamic-rerun-triggers",
        type="linelist",
    )


def _can_item_be_potentially_dynamically_rerun(item):
    # this is a previously failing test that now passes
    if item._dynamic_rerun_terminated:
        return False

    # this item has been run as many times as allowed
    if item.num_dynamic_reruns_kicked_off >= item.max_allowed_dynamic_rerun_attempts:
        return False

    return True


def _get_dynamic_rerun_schedule_arg(item):
    marker = item.get_closest_marker(MARKER_NAME)
    marker_param_name = "schedule"

    # The priority followed is: marker, then command line switch, then config INI file
    if marker and marker_param_name in marker.kwargs.keys():
        dynamic_rerun_arg = marker.kwargs[marker_param_name]
    elif item.session.config.option.dynamic_rerun_schedule:
        dynamic_rerun_arg = str(item.session.config.option.dynamic_rerun_schedule)
    else:
        dynamic_rerun_arg = item.session.config.getini(
            DYNAMIC_RERUN_SCHEDULE_DEST_VAR_NAME
        )

    if dynamic_rerun_arg and not croniter.is_valid(dynamic_rerun_arg):
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
        rerun_attempts = item.session.config.getini(
            DYNAMIC_RERUN_ATTEMPTS_DEST_VAR_NAME
        )

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
        dynamic_rerun_triggers = item.session.config.getini(
            DYNMAIC_RERUN_TRIGGERS_DEST_VAR_NAME
        )

    if not isinstance(dynamic_rerun_triggers, list):
        return [dynamic_rerun_triggers]
    return dynamic_rerun_triggers


def _get_next_rerunnable_time(items_to_rerun, current_time):
    soonest_possible_run_time = None

    for item in items_to_rerun:
        if not _can_item_be_potentially_dynamically_rerun(item):
            continue

        time_iterator = croniter(item.dynamic_rerun_schedule, current_time)
        next_run_time = time_iterator.get_next(datetime)

        if soonest_possible_run_time is None:
            soonest_possible_run_time = next_run_time
        elif soonest_possible_run_time > next_run_time:
            soonest_possible_run_time = next_run_time

    return soonest_possible_run_time


def _get_immediately_rerunnable_items(items_to_rerun, current_time, last_run_time):
    rerunnable_items = []
    for item in items_to_rerun:
        if not _can_item_be_potentially_dynamically_rerun(item):
            continue

        time_iterator = croniter(item.dynamic_rerun_schedule, last_run_time)
        if time_iterator.get_next(datetime) <= current_time:
            rerunnable_items.append(item)

    return rerunnable_items


def _get_all_rerunnable_items(items_to_rerun):
    rerunnable_items = []
    for item in items_to_rerun:
        if not _can_item_be_potentially_dynamically_rerun(item):
            continue

        rerunnable_items.append(item)

    return rerunnable_items


def _initialize_plugin_item_level_fields(item):
    item.dynamic_rerun_schedule = _get_dynamic_rerun_schedule_arg(item)
    item.dynamic_rerun_triggers = _get_dynamic_rerun_triggers_arg(item)
    item.max_allowed_dynamic_rerun_attempts = _get_dynamic_rerun_attempts_arg(item)

    if not hasattr(item, "dynamic_rerun_run_times"):
        item.dynamic_rerun_run_times = []
    item.dynamic_rerun_run_times.append(datetime.now())

    if not hasattr(item, "dynamic_rerun_sleep_times"):
        item.dynamic_rerun_sleep_times = []

    if not hasattr(item, "num_dynamic_reruns_kicked_off"):
        item.num_dynamic_reruns_kicked_off = 0

    if not hasattr(item, "_dynamic_rerun_terminated"):
        item._dynamic_rerun_terminated = False

    # The amount of sections seen last run. This works since sections is a globally passed item that is not stage aware
    # so, sections for 'teardown' has all of the sections of 'call' + new teardown sections
    if not hasattr(item, "_amount_previously_seen_sections"):
        item._amount_previously_seen_sections = 0


def _is_rerun_triggering_report(item, report):
    if not item.dynamic_rerun_triggers:
        return report.failed

    new_output_sections_found = (
        len(report.sections) != item._amount_previously_seen_sections
    )
    item._amount_previously_seen_sections = len(report.sections)

    for rerun_regex in item.dynamic_rerun_triggers:
        # NOTE: Checking for both report.longrepr and reprcrash on report.longrepr is intentional
        report_has_reprcrash = report.longrepr and hasattr(report.longrepr, "reprcrash")
        if report_has_reprcrash and re.search(
            rerun_regex, report.longrepr.reprcrash.message
        ):
            return True

        if new_output_sections_found:
            for section in report.sections:
                section_title = section[0]
                section_text = section[1]
                if section_title in [
                    "Captured stdout call",
                    "Captured stderr call",
                ] and re.search(rerun_regex, section_text):
                    return True

    return False


def _rerun_dynamically_failing_items(session):
    last_rerun_attempt_time = None
    while _get_all_rerunnable_items(session.dynamic_rerun_items):
        current_time = datetime.now()
        if last_rerun_attempt_time is None:
            last_rerun_attempt_time = current_time

        rerun_items = _get_immediately_rerunnable_items(
            session.dynamic_rerun_items, current_time, last_rerun_attempt_time
        )
        for i, item in enumerate(rerun_items):
            last_rerun_attempt_time = current_time

            item.num_dynamic_reruns_kicked_off += 1

            last_run_time = item.dynamic_rerun_run_times[-1]
            sleep_time = current_time - last_run_time
            item.dynamic_rerun_sleep_times.append(sleep_time)

            next_item = rerun_items[i + 1] if i + 1 < len(rerun_items) else None
            pytest_runtest_protocol(item, next_item)
        else:
            next_run_time = _get_next_rerunnable_time(
                session.dynamic_rerun_items, last_rerun_attempt_time
            )
            if next_run_time is not None:
                sleep_delta = next_run_time - current_time
                total_sleep_time = sleep_delta.total_seconds()
                if total_sleep_time > 0:
                    time.sleep(total_sleep_time)

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
    _initialize_plugin_item_level_fields(item)

    # don't apply the plugin if required arguments are missing
    should_run_plugin = (
        item.dynamic_rerun_schedule and item.max_allowed_dynamic_rerun_attempts
    )

    if should_run_plugin:
        item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
        reports = runtestprotocol(item, nextitem=nextitem, log=False)

        will_run_again = (
            item.num_dynamic_reruns_kicked_off < item.max_allowed_dynamic_rerun_attempts
        )

        for report in reports:
            if _is_rerun_triggering_report(item, report):
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
        _rerun_dynamically_failing_items(item.session)

    # NOTE: This was done this way to conform to the pytest runtest api and there is no logic beyond that
    if should_run_plugin:
        return True
    else:
        return


def pytest_sessionstart(session):
    session.dynamic_rerun_items = []


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_sep("=", "Dynamically rerun tests")
    for report in terminalreporter.stats.get("dynamicrerun", []):
        terminalreporter.write_line(report.nodeid)
