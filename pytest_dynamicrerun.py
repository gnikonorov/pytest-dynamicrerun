from _pytest.runner import runtestprotocol

# from croniter import croniter - we'll use this to schedule reruns

PLUGIN_NAME = "dynamicrerun"


def _add_dynamic_rerun_flag(parser):
    help_text = "Set the time to attempt a rerun in using a cron like format ( e.g.: 5 * * * * )"

    group = parser.getgroup(PLUGIN_NAME)
    group.addoption(
        "--rerun_schedule",
        action="store",
        dest="rerun_schedule",
        default="* * * * *",
        help=help_text,
    )

    parser.addini("rerun_schedule", help_text)


def pytest_addoption(parser):
    _add_dynamic_rerun_flag(parser)


def pytest_runtest_protocol(item, nextitem):
    item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
    reports = runtestprotocol(item, nextitem=nextitem, log=False)
    for report in reports:
        if report.failed:
            # failed test, store it and log as pytest would
            # NOTE: we can store the failed items like this. Then in sesisonfinsh we can see if anything has failed
            #       if something has failed then we can schedule a rerun. We can share session state as on line 44
            item.ihook.pytest_runtest_logreport(report=report)
            item.session.dynamicrerun = {"failed_item": None}
            item.session.dynamicrerun["failed_item"] = item

    item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
    return True


# def pytest_sessionfinish(session, exitstatus):
#    raise ValueError(session.dynamicrerun)

# Consider providing a fixture too
# @pytest.fixture
# def bar(request):
#    return request.config.option.dest_foo
