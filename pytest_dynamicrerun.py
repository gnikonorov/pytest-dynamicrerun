import time
import warnings
from datetime import datetime

from _pytest.runner import runtestprotocol
from croniter import croniter

PLUGIN_NAME = "dynamicrerun"


def _add_dynamic_rerun_flag(parser):
    help_text = "Set the time to attempt a rerun in using a cron like format ( e.g.: 5 * * * * )"

    group = parser.getgroup(PLUGIN_NAME)
    group.addoption(
        "--dynamic_rerun_schedule",
        action="store",
        dest="dynamic_rerun_schedule",
        default="* * * * *",
        help=help_text,
    )

    parser.addini("dynamic_rerun_schedule", help_text)


def _get_dynamic_rerun_arg(item):
    dynamic_rerun_arg = None
    if item.session.config.option.dynamic_rerun_schedule:
        dynamic_rerun_arg = item.session.config.option.dynamic_rerun_schedule
    return dynamic_rerun_arg


def pytest_addoption(parser):
    _add_dynamic_rerun_flag(parser)


def pytest_runtest_protocol(item, nextitem):
    # bail early if a falsey value was given for required args
    dynamic_rerun_arg = _get_dynamic_rerun_arg(item)
    if dynamic_rerun_arg is None:
        return

    # terminate runs if we've finished all needed runs to prevent inifinite looping
    # NOTE: for now, we assume one 1 rerun is possible
    if item.session.num_dynamic_reruns_kicked_off > 1:
        warnings.warn("Terminating since more dynamic reruns kicked off than requested")
        return True

    item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
    reports = runtestprotocol(item, nextitem=nextitem, log=False)
    for report in reports:
        if report.failed:
            item.session.dynamic_rerun_items.append(item)

        item.ihook.pytest_runtest_logreport(report=report)
    item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)

    # if nextitem is None, we have finished running tests. Dynamically rerun any tests that failed
    if nextitem is None:
        now_time = datetime.now()
        time_iterator = croniter(dynamic_rerun_arg, now_time)

        time_delta = time_iterator.get_next(datetime) - now_time
        time.sleep(time_delta.seconds)

        warnings.warn(
            "Sleeping for {} seconds and reruning failed items".format(time_delta)
        )

        item.session.num_dynamic_reruns_kicked_off += 1

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
