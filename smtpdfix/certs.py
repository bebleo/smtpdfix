import logging
import socket
import warnings
from datetime import datetime, timedelta
from ipaddress import ip_address
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import (BasicConstraints, CertificateBuilder, DNSName,
                               IPAddress, Name, NameAttribute,
                               SubjectAlternativeName, random_serial_number)
from cryptography.x509.oid import NameOID

log = logging.getLogger(__name__)


def _generate_certs(path, days=3652, key_size=2048, separate_key=False):
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
    ip = socket.gethostbyname(hostname)
    subject = Name([NameAttribute(NameOID.COMMON_NAME, "smtpdfix_cert")])
    alt_names = [
        DNSName("localhost"),
        DNSName("localhost.localdomain"),
        DNSName(hostname),
        IPAddress(ip_address("127.0.0.1")),
        IPAddress(ip_address("0.0.0.1")),
        IPAddress(ip_address("::1")),
        IPAddress(ip_address(ip)),
    ]
    # Set it so the certificate can be a root certificate with
    # ca=true, path_length=0 means it can only sign itself.
    constraints = BasicConstraints(ca=True, path_length=0)

    cert = (CertificateBuilder()
            .issuer_name(subject)
            .subject_name(subject)
            .serial_number(random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=days))
            .add_extension(SubjectAlternativeName(alt_names), critical=False)
            .public_key(key.public_key())
            .add_extension(constraints, critical=False)
            .sign(private_key=key, algorithm=hashes.SHA256()))

    cert_path = Path(path).joinpath("cert.pem")
    with open(cert_path, "ab") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    log.debug("Certificate generated")


def generate_certs(path, days=3652, key_size=2048, separate_key=False):
    _message = ("_generate_certs will be removed from the public API as of ",
                "version 0.4.")
    warnings.warn(_message, PendingDeprecationWarning)

    return _generate_certs(path, days, key_size, separate_key)
