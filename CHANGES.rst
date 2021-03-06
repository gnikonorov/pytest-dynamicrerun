Changelog
=========

Unreleased
----------

- Refactor argument parsing logic by wrapping argument value and the level it was extracted from into an ``ArgumentValue`` object when returning values from ``_get_arg``

1.1.1 (2020-08-15)
------------------

- Add documentation on how to append to ``dynamic_rerun_triggers`` to the README

1.1.0 (2020-08-13)
------------------

- Refactor argument parsing logic
- Add new option ``--dynamic-rerun-disabled`` which disables this plugin when passed

1.0.6 (2020-08-12)
------------------

- Better document marks and argument precedence in README.rst

1.0.5 (2020-08-10)
------------------

- Fix a bug where past test ``stdout`` and ``stderr`` was being inspected in the test's dynamic reruns

1.0.4 (2020-08-10)
------------------

- Add a changelog
- Refactor how we initialize plugin exposed ``item`` fields

1.0.3 (2020-08-09)
------------------

- Fix some README typos

1.0.2 (2020-08-09)
------------------

- Initial release
