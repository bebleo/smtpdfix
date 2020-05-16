# pytest SMTPD Fixture

![build](https://github.com/bebleo/bebleo_smtpd_fixture/workflows/build/badge.svg)

**Not yet uploaded to PyPi. Version 0.1.0 coming soon.**

As simple SMTP server for use as a fixture with pytest. All this does is receives messages and appends them to a list as an `email.Message`.

## Installing

Installing handled through PyPi:

```sh
pip install bebleo-smtpd-fixture
```

Or, can equally be included in a `setup.py` file:

```python
setup(
    ...
    tests_require = [
        "pytest",
        "bebleo-smtpd-fixture",
    ],
)
```

## Using

To use the `smtpd` fixture import it into your `conftest.py` file and then use it like any other pytest fixture. for example:

```python
# conftest.py
from smtplib import SMTP
from bebleo_smtpd_fixture import smtpd

```

And then in the test:

```python
# test_mail.py
def test_sendmail(smtpd):
    from_addr = "from.addr@example.org"
    to_addrs = "to.addr@example.org"
    msg = f"From: {from_addr}\r\nTo: {to_addrs}\r\nSubject: Foo\r\n\r\nFoo bar"

    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.sendmail(from_addr, to_addrs, msg)

    assert len(smtpd.messages) == 1
```

### Configuration

Configuration is handled through two environment variables:

Variable | Default
---------|--------
`SMTPD_HOST` | `"127.0.0.1"`
`SMTPD_PORT` | `8025`

## Known Issues

+ Firewalls may interfere with the operation of the smtp server.
+ No support for SSL, TLS, STARTTLS, or authentication, yet.

-----

Written 2020 with :coffee: and :heart: in Montreal, QC
