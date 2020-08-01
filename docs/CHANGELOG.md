# Change Log

## Version 0.2.2

Release date: *Unreleased*

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
