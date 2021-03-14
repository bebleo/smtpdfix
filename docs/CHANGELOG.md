# Change Log

## Unreleased Changes

Release date: TBD

## Version 0.3.0

Release date: 2021-03-14

- Removes redundant certificate generation script and config from source.
- Environment variables are now read only when initializing the fixture subsequent changes make no difference.
- Changing any attribute in `SMTPDFIX.config` causes the server to reset itself to the latest config.
- Messages are persisted by default when calling `reset`
- By default SSL certificates and keys are now loaded by default from a single cert.pem file.
- SSL Certificate and Key can be set separately to any filename by setting the environment variables `SMTPD_SSL_CERTIFICATE_FILE` and `SMTPD_SSL_KEY_FILE` or the `ssl_cert_files` to a tuple of `(certfile, keyfile)` in the config. Fixes [Issue #15](https://github.com/bebleo/smtpdfix/issues/15)

## Version 0.2.10

Release date: 2021-03-05

**Includes Potentially Breaking Changes:**

As of version 0.2.10 smtpdfix uses the standard aiosmtpd VRFY handler that will always return "252 Cannot VRFY user, but will accept message and attempt delivery" if an address is provided or "502 Cannot VRFY {address provided}" if not. Version 0.2.9. and earlier of smptdfix would return a 252 coded response if the username provided was verified and in all other cases a 502 error response.

- Updates requirements to aiosmtpd version 1.3.1 or above.
- `SMPTDFix` can now be initialized without providing a hostname and port which defaults to localhost: 8025.
- Better compatibility with AUTH in aiosmtpd by using `AuthResult` as return from AUTH mechanism handlers and the `Authenticator` for processing.
- Uses default aiosmtpd VRFY handling and responses.
- Adds unofficial support for PyPy3 in response to. [Issue #51](https://github.com/bebleo/smtpdfix/issues/51)
- Adds exception handling to prevent cases where unhandled exceptions cause the fixture to hang. Now returns a 421 error and closes the connection. [Issue #51](https://github.com/bebleo/smtpdfix/issues/51)

### Contributions

- [John T. Wodder II (@jwodder)](https://github.com/jwodder) Fix errors and typos in README.md [PR #49](https://github.com/bebleo/smtpdfix/pull/49)

## Version 0.2.9

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
