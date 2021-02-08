# SMTPDFix: Test email, locally

![build](https://github.com/bebleo/bebleo_smtpd_fixture/workflows/build/badge.svg)

A simple SMTP server based on `aiosmtpd` for use as a fixture with pytest that supports encryption and authentication. All this does is receives messages and appends them to a list as an `email.Message`.

This fixture is intended to address use-cases where to test an application that sends an email it needs to be intercepted for subsequent processing. For example, sending an email with a code for password reset or two-factor authentication. This fixture allows a test to trigger the email being sent, ensure that it's sent, and read the email.

## Installing

To install using pip, first upgrade pip to the latest version to avoid any issues installing `cryptography`:

```sh
python -m pip install --upgrade pip
pip install smtpdfix
```

Or, if you're using setuptools, it can be included in the `extras_require` argument of a `setup.py` file:

```python
setup(
    ...
    extras_require={
        "test": [
            "pytest",
            "smtpdfix",
        ],
    },
)
```

and then insalled with pip:

```sh
python -m pip install --upgrade pip
pip install .[test]
```

## Using

The `SMTPDFix` plugin, `smtpd`, automatically registers for use with pytest when you install smptdfix. To use it simply add to you test method.

```python
# test_mail.py
from smtplib import SMTP


def test_sendmail(smtpd):
    from_addr = "from.addr@example.org"
    to_addrs = "to.addr@example.org"
    msg = (f"From: {from_addr}\r\n"
           f"To: {to_addrs}\r\n"
           f"Subject: Foo\r\n\r\n"
           f"Foo bar")

    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.sendmail(from_addr, to_addrs, msg)

    assert len(smtpd.messages) == 1
```

To use STARTTLS:

```python
from smtplib import SMTP


def test_sendmail(monkeypatch, smtpd):
    monkeypatch.setenv('SMTPD_USE_STARTTLS', 'True')
    from_ = "from.addr@example.org"
    to_ = "to.addr@example.org"
    msg = (f"From: {from_}\r\n"
           f"To: {to_}\r\n"
           f"Subject: Foo\r\n\r\n"
           f"Foo bar")

    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()  # Note that you need to call starttls first.
        client.sendmail(from_addr, to_addrs, msg)

    assert len(smtpd.messages) == 1
```

> Before version 0.2.7 the plugin did not automatically register and it was necessary to include it manually by adding `pytest_plugins = "smtpdfix"` to the module or conftest.py.

The certificates included with the fixture will work for addresses localhost, localhost.localdomain, 127.0.0.1, 0.0.0.1, ::1. If using other addresses the key (key.pem) and certificate (cert.pem) must be in a location specified under `SMTP_SSL_CERTS_PATH`.

### Not as a fixture

In some situations it may be desirable to not use the fixture which is initialized before entering the test. This can be accomplished by using the `SMTPDFix` class.

```python
from smtplib import SMTP

from smtpdfix import SMTPDFix


def test_smtpdfix(msg):
    hostname, port = "127.0.0.1", 8025

    with SMTPDFix(hostname, port) as smtpd:
        with SMTP(hostname, port) as client:
            from_addr = "foo@example.org"
            to_addrs = "bar@example.org"
            msg = (f"From: {from_addr}\r\n"
                   f"To: {to_addrs}\r\n"
                   f"Subject: Foo\r\n\r\n"
                   f"Foo bar")

            client.sendmail(from_addr, to_addrs, msg)

        assert len(smtpd.messages) == 1
```

### Configuration

Configuration can be handled through environment variables:

Variable | Default | Description
---------|---------|------------
`SMTPD_HOST` | `127.0.0.1` | The hostname that the fixture will listen on.
`SMTPD_PORT` | `8025` | The port that the fixture will listen on.
`SMPTD_USERNAME` | `user` |  
`SMTPD_PASSWORD` | `password` |  
`SMTPD_USE_SSL` | `False` | Whether the fixture should use fixed TLS/SSL for transactions. If using smtplib requires that `SMTP_SSL` be used instead of `SMTP`.
`SMTPD_USE_STARTTLS` | `False` | Whether the fixture should use StartTLS to encrypt the connections. If using `smptlib` requires that `SMTP.starttls()` is called before other commands are issued. Overrides `SMTPD_USE_SSL` as the preferred method for securing communications with the client.
`SMTPD_ENFORCE_AUTH` | `False` | If set to true then the fixture refuses MAIL, RCPT, DATA commands until authentication is completed.
`SMTPD_SSL_CERTS_PATH` | `\certs\` | The path to the key and certificate for encrypted communication.

> If these variables are included in a `.env` file they'll be loaded automatically.

## Developing

To develop and test smtpdfix you will need to install [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) to run asynchronous tests, [isort](https://pycqa.github.io/isort/) to sort imports and [flake8](https://flake8.pycqa.org/en/latest/) to lint. To install in a virtual environment for development:

```sh
python -m venv venv
./venv/scripts/activate
pip install -e .[dev]
```

Code is tested using pytest:

```sh
pytest -p no:smtpd --cov
```

Before submitting a pull request with your changes you should ensure that all imports are sorted and that the code passes linting with flake8.

```sh
# Sorting the imports
isort .

# Linting the code
flake8 .
```

## Known Issues

+ Firewalls may interfere with the operation of the smtp server.
+ Using "localhost" as the hostname may resolve to ::1 which in some cases, depending on the system configuration, does not work.
+ Authenticating with LOGIN and PLAIN mechanisms fails over TLS/SSL, but works with STARTTLS. [Issue #10](https://github.com/bebleo/smtpdfix/issues/10)
+ Currently no support for termination through signals. [Issue #4](https://github.com/bebleo/smtpdfix/issues/4)
+ Key and certificate for encrypted communications must be called key.pem and cert.pem respectively. [Issue #15](https://github.com/bebleo/smtpdfix/issues/15)

©2020-2021, Written with ☕ and ❤ in Montreal, QC
