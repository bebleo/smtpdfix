#! /bin/sh

# Generates new key and certificate in the folder based on the information
# in req.cnf and good for 10 years. Default is a certificate usable for
# connections to localhost, localhost.localdomain, 127.0.0.1, 0.0.0.1,
# and ::1.
openssl req              \
        -new             \
        -x509            \
        -sha256          \
        -config req.cnf  \
        -newkey rsa:4096 \
        -nodes           \
        -keyout key.pem  \
        -out cert.pem    \
        -days 3653
    