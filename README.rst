===================
pytest-dynamicrerun
===================

.. image:: https://img.shields.io/pypi/v/pytest-dynamicrerun.svg
    :target: https://pypi.org/project/pytest-dynamicrerun
    :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/pytest-dynamicrerun.svg
    :target: https://pypi.org/project/pytest-dynamicrerun
    :alt: Python versions

.. image:: https://travis-ci.org/gnikonorov/pytest-dynamicrerun.svg?branch=master
    :target: https://travis-ci.org/gnikonorov/pytest-dynamicrerun
    :alt: See Build Status on Travis CI

pytest-dynamicrerun is a `pytest`_ plugin to rerun tests dynamically based off of test outcome and output.

ATTENTION!!
-----------

This plugin is currently under active development. You are encouraged to use it, but all functionality may not work as expected and behavior may change at any time without warning. I have tried to keep documentation as accurate as possible but make no guarantees. This plugin should not be considered stable until the first version is published to  `PyPI`_.

Supported versions
------------------

This plugin is tested against the following Python and pytest versions. Each Python version is tested against all pytest versions. Please `file an issue`_ to request additional targets.

:Python Versions:
    python 3.5,
    python 3.6,
    python 3.7,
    python 3.8,
    pypy3
:Pytest Versions:
    5.4.0,
    5.4.1,
    5.4.2,
    5.4.3,
    6.0.0,
    6.0.1


Installation
------------

This plugin is not yet published to `PyPI`_. You can install it locally by cloning this repo and running::

    $ pip install -e <PATH_TO_DIR>

Note that in the above example, ``<PATH_TO_DIR>`` is the path to the source of ``pytest-dynamicrerun``.


Usage
-----

Specifying how many times to rerun
##################################

By default, one rerun attempt is made ( subject to change in the future ). You can set the amount of times to attempt a rerun by  passing the ``--dynamic-rerun-attempts`` flag when invoking pytest or including the ``dynamic_rerun_attempts`` ini key.

To pass the flag::

    python3 -m pytest --dynamic-rerun-attempts=3

To set the ini key add the following to your config file's `[pytest]` section::

    [pytest]
    dynamic_rerun_attempts = 123

Passing a non positive integer value will set the number of rerun attempts to the default.

Specifying what to rerun on
###########################

By default, all failed tests are rerun. You can change this behavior by either passing the ``--dynamic-rerun-triggers`` flag when invoking ``pytest`` or including the ``dynamic_rerun_triggers`` ini key. Note that regular expressions are allowed.

To pass the flag::

    python3 -m pytest --dynamic-rerun-triggers=a triggering trace

To set the ini key add the following to your config file's ``[pytest]`` section::

    [pytest]
    dynamic_rerun_triggers = a triggering trace

Note that at this time only ``stdout``, ``stderr``, and exceptions are checked.

Specifying a rerun interval
###########################

You can specify an interval to rerun tests on by either passing the ``--dynamic-rerun-schedule`` flag to python when invoking ``pytest`` or including the ``dyanmic_rerun_schedule`` ini key.

Internally, this plugin uses `croniter`_ to schedule wait times. Because of this, we are able to schedule wait times with second level granularity. Visit the croniter repository ``README`` to find out more information on this.

To pass the flag::

    python3 -m pytest --dynamic-rerun-schedule= * * * * * *

To set the ini key add the following to your config file's ``[pytest]`` section::

    [pytest]
    dynamic_rerun_schedule = * * * * * *

Note thay any valid cron schedule is accepted. If this flag is not passed or set in the ini file, this plugin will not take effect. Passing an invalid value will force the interval to default to ``* * * * * *`` ( every second ).

Using markers to rerun tests
############################

We can achieve the above functionality through markers as well. This plugin defines the ``dynamicrerun`` mark, which can be used as follows::

    @pytest.mark.dynamicrerun(attempts=10, triggers="foo", schedule="* * * * * *")
    def test_print_foo():
        print("foo")

Developing against this plugin
------------------------------
This plugin exposes the following attributes on the ``item`` object:

* ``dynamic_rerun_sleep_times (List)``: A list of `timedelta objects`_ representing the time slept in between reruns for the item

This plugin exposes the following attributes on the ``session`` object:

* ``dynamic_rerun_items (List)``: The list of items that are set to be dynamically rerun on the next iteration
* ``num_dynamic_reruns_kicked_off (int)``: The amount of reruns launched at the moment of inspection


Contributing
------------
Contributions are always welcome. Tests can be run with `tox`_.

`pre-commit`_ is used to ensure basic checks pass.

License
-------

Distributed under the terms of the `MIT`_ license, "pytest-dynamicrerun" is free and open source software

Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

.. _`MIT`: http://opensource.org/licenses/MIT
.. _`PyPI`: https://pypi.org/
.. _`croniter`: https://github.com/kiorky/croniter/
.. _`file an issue`: https://github.com/gnikonorov/pytest-dynamicrerun/issues
.. _`pre-commit`: https://pre-commit.com/
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`timedelta objects`: https://docs.python.org/3/library/datetime.html#timedelta-objects
.. _`tox`: https://tox.readthedocs.io/en/latest/
