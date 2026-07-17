# GitHub Copilot Custom Instructions

- Treat this repository as a small Python library for testing email delivery with a local asyncio-based SMTP server; avoid production-oriented features unless explicitly requested.
- Keep changes minimal and preserve the public testing API, especially `smtpd`, `SMTPDFix`, `AuthController`, and `Config`.
- Maintain compatibility with the Python versions declared in `setup.cfg`, and keep type annotations on new or changed Python code.
- Prefer existing dependencies and standard library modules; only add new dependencies when they are clearly necessary for the task.
- When behavior changes, update or add pytest coverage in `tests/` alongside the implementation.
- Preserve the current TLS/authentication approach, including the `trustme`-based certificate generation used by the test fixture.
- Validate repository changes with the established commands: `pytest -p no:smtpd`, `isort --check .`, `flake8 .`, and `mypy`.
- Prior to pushing to the remote repository changes should be verified by running `tox` to run the complete test suite.
- While maintaining compatibility with the minimum required version of python take steps to minimize tech debt and to use new features as they become available. Do not write version specific code.

## Infrastructure

- Prefer `pyenv` to install and maintain python versions for development and testing. If it is not installed suggest that the user install it.
- Always use a virtualenv for development. Avoid using the system install of python unless absolutely necessary.

## Evolution

- As development moves forward suggest changes that will improve performance that would be included in these instructions as part of the updates.
