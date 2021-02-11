# Change Log

## Unreleased

Release date: 2021-02-11

- Now requires cryptography version 3.4.4 in response to security reports
- Upgrades Aiosmtpd to version 1.3.0 or greater to take advantages of updated `AUTH` handling. Versions of aiosmtpd below 1.3.0 are no longer comaptible

## Version 0.2.8

Release date: 2021-02-07

- Adds an `SMTPDFix` class for use in `with` blocks.
- The fixture now automatically loads as a plugin with pytest.
- Aiosmtpd version 1.2.4 or greater now required.
- Command responses now standard with aiosmtpd with the exception of AUTH mechanisms.
- Prefers StartTLS to TLS/SSL to avoid a case where if both where specified the SMTP server would report a fault.
- Minor performance enhancements from removing the lazy object proxy and setting key size to 2048 bits instead of 4096.
- Allows for late changes to StartTLS environment variables.

## Version 0.2.7

Release date: 2021-01-29

This release has been motivated by recent breaking changes to aiosmtpd.

- Certificates are now dynamically generated per session rather than stored in the package.
- Fixes aiosmtpd to version 1.2.2 or below.

## Version 0.2.6

Release date: 2021-01-17

- Enables use of `mock.patch` and `monkeypatch` to set environment variables on individual tests. [Issue #22](https://github.com/bebleo/smtpdfix/issues/22)
- updates `Config` to fix bug with Boolean values where values aren't set in a .env file. [Issue #24](https://github.com/bebleo/smtpdfix/issues/24)

### Contributions

- [Jeremy Richards (@jeremysprofile)](https://github.com/jeremysprofile) Make getenv default values strings [PR #25](https://github.com/bebleo/smtpdfix/pull/25)

## Version 0.2.5

Release date: 2020-12-28

- Corrects imports in README.md examples.
- Adds support for python 3.9.
- Corrects line endings on gen_certs.sh to LF and adds a .getattributes file to prevent git changing them back to CRLF.
- Bumps `aiosmtpd`version to 1.2.2
- Adds async test support using pytest-asyncio
- Adds coverage support using pytest-cov
- Allows .env files to override environment variables

## Version 0.2.4

Release date: 2020-08-02

- Corrects issue with default certs not being copied.

## Version 0.2.3

Release date: 2020-08-02

> Last release as bebleo_smtpd_fixture. Future releases will use smtpdfix.

- Adds deprecation warning to the fixture announcing change of project name to smtpdfix moving forward.

## Version 0.2.2

Release date: 2020-08-01

- Adds a changelog.
- Adds support for `.env` files with `python-dotenv`.
- Enforces encryption on AUTH methods that require it.
- Corrects bug that prevented cancelling authentication with the LOGIN mechanism by sending a * and updates error message to match [RFC4954 - SMTP Service Extension for Authentication](https://www.ietf.org/rfc/rfc4954.txt).
- Corrects bug that caused the fixture hang on windows if certificates were not found in the path specified by the `SMTPD_SSL_CERTS_PATH`.
- Ensures that the session is authenticated when the `SMTPD_ENFORCE_AUTH` environment flag is set to `True` before processing DATA, MAIL, RCPT commands.

## Version 0.2.1

Release date: 2020-07-30

- Implemented CRAM-MD5 authentication
- Enabled implicit SSL
