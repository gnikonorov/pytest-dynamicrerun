===================
pytest-dynamicrerun
===================

.. image:: https://img.shields.io/pypi/v/pytest-dynamicrerun.svg
    :target: https://pypi.org/project/pytest-dynamicrerun
    :alt: PyPI version

.. image:: https://travis-ci.org/gnikonorov/pytest-dynamicrerun.svg?branch=master
    :target: https://travis-ci.org/gnikonorov/pytest-dynamicrerun
    :alt: See Build Status on Travis CI

pytest-dynamicrerun is a `pytest`_ plugin to rerun tests dynamically based off of test outcome and output.

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

Install this plugin from `PyPI`_ by running the following::

    $ pip install pytest-dynamicrerun


Usage
-----

Specifying how many times to rerun
##################################

By default, one rerun attempt is made. You can set the amount of times to attempt a rerun by passing the ``--dynamic-rerun-attempts`` flag when invoking pytest or including the ``dynamic_rerun_attempts`` INI key.

To pass the flag::

    python3 -m pytest --dynamic-rerun-attempts=3

To set the INI key add the following to your config file's ``[pytest]`` section::

    [pytest]
    dynamic_rerun_attempts = 123

Passing a non positive integer value will set the number of rerun attempts to the default.

Specifying what to rerun on
###########################

By default, all failed tests are rerun. You can change this behavior by either passing the ``--dynamic-rerun-triggers`` flag when invoking ``pytest`` or including the ``dynamic_rerun_triggers`` INI key. Note that regular expressions are allowed.

To pass the flag::

    python3 -m pytest --dynamic-rerun-triggers="a triggering trace"

To set the INI key add the following to your config file's ``[pytest]`` section::

    [pytest]
    dynamic_rerun_triggers = a triggering trace

You can accumulate values by either providing the flag multiple times or appending to the INI key. For example, the below two snippets would cause this plugin to trigger on both ``foo`` and ``bar``::

    python3 -m pytest --dynamic-rerun-triggers="foo" --dynamic-rerun-triggers="bar"

    [pytest]
    dynamic_rerun_triggers = foo
        bar

Note that at this time only ``stdout``, ``stderr``, and exceptions are checked.

Specifying a rerun interval
###########################

You can specify an interval to rerun tests on by either passing the ``--dynamic-rerun-schedule`` flag to python when invoking ``pytest`` or including the ``dyanmic_rerun_schedule`` INI key.

Internally, this plugin uses `croniter`_ to schedule wait times. Because of this, we are able to schedule wait times with second level granularity. Visit the croniter repository ``README`` to find out more information on this.

To pass the flag::

    python3 -m pytest --dynamic-rerun-schedule="* * * * * *"

To set the INI key add the following to your config file's ``[pytest]`` section::

    [pytest]
    dynamic_rerun_schedule = * * * * * *

Note that any valid cron schedule is accepted. If this flag is not passed or set in the INI file, this plugin will not take effect. Passing an invalid value will force the interval to default to ``* * * * * *`` ( every second ).

Ignoring this plugin
####################

You can ignore this plugin by passing the ``--dynamic-rerun-disabled`` flag to python when invoking ``pytest`` or including the ``dynamic_rerun_disabled`` INI key.

To pass the flag::

    python3 -m pytest --dynamic-rerun-disabled="True"

To set the INI key add the following to your config file's ``[pytest]`` section::

    [pytest]
    dynamic_rerun_disabled = True


Note that if this flag is omitted, we do not disable the plugin ( so it is equivalent to passing ``--dynamic-rerun-disabled=False`` )

Using markers to rerun tests
############################

We can achieve the above functionality through markers as well. This plugin defines the ``dynamicrerun`` mark, which can be used as follows::

    @pytest.mark.dynamicrerun(attempts=10, disabled=False, schedule="* * * * * *", triggers="foo")
    def test_print_foo():
        print("foo")

Mark arguments correspond to INI keys as follows:

* ``attempts`` corresponds to ``dynamic_rerun_attempts``
* ``disabled`` corresponds to ``dynanic_rerun_disabled``
* ``schedule`` corresponds to ``dynamic_rerun_schedule``
* ``triggers`` corresponds to ``dynamic_rerun_triggers``

To pass multiple values to the ``triggers`` argument, provide a list as so::

    @pytest.mark.dynamicrerun(attempts=10, disabled=False, schedule="* * * * * *", triggers=["foo", "bar", "baz"])
    def test_print_foo():
        print("foo")

In the above example, reruns will be triggered on ``foo``, ``bar``, and ``baz``.

Argument precedence
###################

Note that first we check for arguments in markers, then command line switches, and only then do we check in INI files. Values found at lower levels ( those checked first ) take precedence over values defined at a higher level ( those checked later ).

For example, if we define the number of rerun attempts as 10 when invoking ``pytest`` from the command line, but later in a marker define the number of rerun attempts as 3, 3 would take precedence over 10 since we check markers before we check command line flags.

Developing against this plugin
------------------------------
This plugin exposes the following attributes on the ``item`` object:

* ``dynamic_rerun_run_times ( list )``: The list of times this item was run by the plugin. Note this includes the original non dynamically rerun run.
* ``dynamic_rerun_schedule(string)``: The schedule to rerun this item on. See the section ``Specifying a rerun interval`` above for more details.
* ``dynamic_rerun_sleep_times (list)``: A list of `timedelta objects`_ representing the time slept in between reruns for the item
* ``dynamic_rerun_triggers (list)``: The rerun triggers for this specific item. See the section ``Specifying what to rerun on`` above for more details.
* ``max_allowed_dynamic_rerun_attempts(int)``: The maximum amount of times we are allowed to rerun this item. See the section ``Specifying how many times to rerun`` above for more details.
* ``num_dynamic_reruns_kicked_off (int)``: The amount of reruns launched at the moment of inspection for this item.

This plugin exposes the following attributes on the ``session`` object:

* ``dynamic_rerun_items (list)``: The list of items that are set to be dynamically rerun on the next iteration


Contributing
------------
Contributions are always welcome. Tests can be run with `tox`_.

Please remember to add a `changelog`_ entry when adding a non-trivial feature.

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
.. _`changelog`: https://github.com/gnikonorov/pytest-dynamicrerun/blob/master/CHANGES.rst
.. _`file an issue`: https://github.com/gnikonorov/pytest-dynamicrerun/issues
.. _`pre-commit`: https://pre-commit.com/
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`timedelta objects`: https://docs.python.org/3/library/datetime.html#timedelta-objects
.. _`tox`: https://tox.readthedocs.io/en/latest/
