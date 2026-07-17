import logging
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Union

import trustme

log = logging.getLogger(__name__)

Cert = namedtuple("Cert", ["cert", "key"], defaults=[None, None])


def _generate_certs(path: Union[Path, str],
                    days: int = 365,
                    key_size: int = 2048,
                    separate_key: bool = False) -> Cert:
    """DO NOT USE THIS FOR ANYTHING PRODUCTION RELATED, EVER!

    Params:
    - path: the `Path` or `str` of the directory to write the file to.
    - days: an `int` of the number of days the certificate will be valid.
    - key_size: an `int` representing the byte size of the key.
    - separate_key: a `bool` representing whether the private key should be
      written to a separate file.

    Returns:
    - By default returns a `tuple` with a `Path` to the certificate file
      "cert.pem" and `None` for the key file.
    - If separate_key was `True` a `tuple` with the paths to the certificate
      file "cert.pem" and key file "key.pem" (each as a `Path`) will be
      returned.

    Changed as of v0.5.2
    - Now returns a tuple of the location of the cert file and, if separate,
      the key file. Previously always returned `None`
    """
    cert_path = Path(path).joinpath("cert.pem")
    key_path = Path(path).joinpath("key.pem")
    _ = key_size  # preserved for API compatibility

    cert = trustme.CA().issue_cert(
        "localhost",
        "localhost.localdomain",
        "127.0.0.1",
        "0.0.0.1",
        "::1",
        common_name="smtpdfix_cert",
        not_before=datetime.now(timezone.utc),
        not_after=datetime.now(timezone.utc) + timedelta(days=days),
    )

    if separate_key:
        cert.private_key_pem.write_to_path(key_path)
        cert.cert_chain_pems[0].write_to_path(cert_path)
        return Cert(cert_path, key_path)

    cert.private_key_and_cert_chain_pem.write_to_path(cert_path)
    log.debug("Certificate generated")

    return Cert(cert_path, [None])
