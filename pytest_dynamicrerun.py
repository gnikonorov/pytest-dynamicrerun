import time
from datetime import datetime

from _pytest.runner import runtestprotocol
from croniter import croniter

DEFAULT_RERUN_ATTEMPTS = 1
PLUGIN_NAME = "dynamicrerun"


def _add_dynamic_rerun_schedule_flag(parser):
    group = parser.getgroup(PLUGIN_NAME)
    group.addoption(
        "--dynamic-rerun-schedule",
        action="store",
        dest="dynamic_rerun_schedule",
        default="* * * * *",
        help="Set the time to attempt a rerun in using a cron like format ( defaults to '* * * * *' )",
    )

    parser.addini("dynamic_rerun_schedule", "default value for --dyamic-rerun-schedule")


def _add_dynamic_rerun_attempts_flag(parser):
    group = parser.getgroup(PLUGIN_NAME)
    group.addoption(
        "--dynamic-rerun-attempts",
        action="store",
        dest="dynamic_rerun_attempts",
        default=1,
        help="Set the amount of times reruns should be attempted ( defaults to 1 )",
    )

    parser.addini(
        "dynamic_rerun_schedule", "default value for --dynamic-rerun-attempts"
    )


# NOTE: See how we can refactor the _get methods into one method
#       Or if we even need them, since they're not really doing anything
#       Also need to check what happens to plugin if installed and nothing is passed
def _get_dynamic_rerun_schedule_arg(item):
    dynamic_rerun_arg = None
    if item.session.config.option.dynamic_rerun_schedule:
        dynamic_rerun_arg = item.session.config.option.dynamic_rerun_schedule
    return dynamic_rerun_arg


def _get_dynamic_rerun_attempts_arg(item):
    if item.session.config.option.dynamic_rerun_schedule:
        return item.session.config.option.dynamic_rerun_attempts
    else:
        return DEFAULT_RERUN_ATTEMPTS


def pytest_addoption(parser):
    _add_dynamic_rerun_schedule_flag(parser)
    _add_dynamic_rerun_attempts_flag(parser)


def pytest_report_teststatus(report):
    if hasattr(report, "dynamically_rerun") and report.dynamically_rerun:
        return "dynamic-rerun", "DR", ("DYNAMIC_RERUN", {"yellow": True})


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
        if report.failed and will_run_again:
            report.dynamically_rerun = True
            item.session.dynamic_rerun_items.append(item)

        item.ihook.pytest_runtest_logreport(report=report)
    item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)

    # if nextitem is None, we have finished running tests. Dynamically rerun any tests that failed
    if nextitem is None:
        item.session.num_dynamic_reruns_kicked_off += 1
        now_time = datetime.now()
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


# Consider providing a fixture too
# @pytest.fixture
# def bar(request):
#    return request.config.option.dest_foo
