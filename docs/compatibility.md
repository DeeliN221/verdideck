# AiiDA compatibility

verdideck supports AiiDA 1.6.9 through the supported 2.x releases. It probes
available command interfaces instead of assuming capabilities from a version number.

## Command behavior

The computer, code, plugin, process, calcjob, group, config, profile and daemon
commands remain available when their corresponding verdi interfaces can be imported.
AiiDA 1.6.9 lacks newer node, storage and presto interfaces. Their tabs remain
visible and explain that the operation is unsupported; missing imports must not
prevent the application from starting.

The compatibility layer lives in `src/verdideck/commands/compat.py`. It recognizes
stale reentry caches, attempts one repair, and reports environment problems
separately from missing features. `commands/base.py` builds registries and formats
status errors. The existing runner supports both ordinary Click commands and
newer verdi commands that require a top-level context.

## Configuration

The status view accommodates the configuration interfaces in AiiDA 1.x and 2.x.
When a configuration file belongs to an incompatible version, it reports that
problem without a traceback or instructions to initialize a replacement profile.
verdideck does not migrate or rewrite existing AiiDA configuration.

## Verification

Run `uv run pytest tests` for the normal regression suite. The dedicated contract
in `tests/compat/test_aiida169.py` runs only with AiiDA 1.6.9; other environments
skip it. CI uses a separate Python 3.9 environment with that exact AiiDA version.
The four contract tests cover import and registry availability, visible fallbacks,
configuration error formatting, and `computer list --help` through the runner.
They do not require a production database or profile and do not establish support
for versions older than 1.6.9.

## Publishing from the rebuilt repository

The PyPI project remains `verdideck`. Before publishing, its owner must authorize
`DeeliN221/verdideck` and the `publish.yml` workflow in the existing project's
Trusted Publisher settings. Continue the package version sequence; resetting Git
history does not reset the versions already published on PyPI.
