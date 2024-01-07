import logging
import socket
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from pathlib import Path
from typing import Union

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import (BasicConstraints, CertificateBuilder, DNSName,
                               IPAddress, Name, NameAttribute,
                               SubjectAlternativeName, random_serial_number)
from cryptography.x509.oid import NameOID

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
    # DO NOT USE THIS FOR ANYTHING PRODUCTION RELATED, EVER!
    # Generate private key
    # 2048 is the minimum that works as of 3.9
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    key_file = "key.pem" if separate_key else "cert.pem"
    key_path = Path(path).joinpath(key_file)
    with open(key_path, "ab") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            encryption_algorithm=serialization.NoEncryption(),
            format=serialization.PrivateFormat.TraditionalOpenSSL
        ))
    log.debug("Private key generated")

    # Generate public certificate
    hostname = socket.gethostname()
    subject = Name([NameAttribute(NameOID.COMMON_NAME, "smtpdfix_cert")])
    alt_names = [
        DNSName("localhost"),
        DNSName("localhost.localdomain"),
        DNSName(hostname),
        IPAddress(ip_address("127.0.0.1")),
        IPAddress(ip_address("0.0.0.1")),
        IPAddress(ip_address("::1")),
    ]

    # Because on misconfigured systems it's possible to have a hostname that
    # doesn't resolve to an IP we catch the error and skip adding it to the
    # list of altnames. (issue #195)
    try:
        ip = socket.gethostbyname(hostname)
        alt_names.append(IPAddress(ip_address(ip)))
    except socket.gaierror as err:
        log.info(f"{hostname} failed to resolve to ip")
        log.error(err.strerror)

    # Set it so the certificate can be a root certificate with
    # ca=true, path_length=0 means it can only sign itself.
    constraints = BasicConstraints(ca=True, path_length=0)

    cert = (CertificateBuilder()
            .issuer_name(subject)
            .subject_name(subject)
            .serial_number(random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=days))
            .add_extension(SubjectAlternativeName(alt_names), critical=False)
            .public_key(key.public_key())
            .add_extension(constraints, critical=False)
            .sign(private_key=key, algorithm=hashes.SHA256()))

    cert_path = Path(path).joinpath("cert.pem")
    with open(cert_path, "ab") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    log.debug("Certificate generated")

    return Cert(cert_path, [key_path if separate_key else None])
