"""
Creates a test certificate chain for signing photos during development.

Real cameras get their certificate from a trusted authority (and later,
our key will live inside the ATECC608A chip). For now we make our own
"Saakshya Test CA" and a device certificate signed by it.

Run once:  python signing/make_test_certs.py
Output:    certs/device_chain.pem  (device cert + CA cert)
           certs/device_key.pem    (private key, never commit this)
           certs/ca_cert.pem       (our test CA, used by the verifier)
"""
import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

CERT_DIR = Path(__file__).resolve().parent.parent / "certs"
CERT_DIR.mkdir(exist_ok=True)

now = datetime.datetime.now(datetime.timezone.utc)


def name(cn):
    return x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Saakshya Project, NIT Hamirpur"),
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
    ])


# 1. Test CA (stands in for a real certificate authority)
ca_key = ec.generate_private_key(ec.SECP256R1())
ca_cert = (
    x509.CertificateBuilder()
    .subject_name(name("Saakshya Test CA"))
    .issuer_name(name("Saakshya Test CA"))
    .public_key(ca_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now - datetime.timedelta(days=1))
    .not_valid_after(now + datetime.timedelta(days=3650))
    .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
    .add_extension(x509.KeyUsage(
        digital_signature=False, content_commitment=False, key_encipherment=False,
        data_encipherment=False, key_agreement=False, key_cert_sign=True,
        crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
    .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
    .sign(ca_key, hashes.SHA256())
)

# 2. Device certificate (one per camera unit)
dev_key = ec.generate_private_key(ec.SECP256R1())
dev_cert = (
    x509.CertificateBuilder()
    .subject_name(name("Saakshya Capture Device 001"))
    .issuer_name(ca_cert.subject)
    .public_key(dev_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now - datetime.timedelta(days=1))
    .not_valid_after(now + datetime.timedelta(days=730))
    .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    .add_extension(x509.KeyUsage(
        digital_signature=True, content_commitment=False, key_encipherment=False,
        data_encipherment=False, key_agreement=False, key_cert_sign=False,
        crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
    .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]), critical=False)
    .add_extension(x509.SubjectKeyIdentifier.from_public_key(dev_key.public_key()), critical=False)
    .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
    .sign(ca_key, hashes.SHA256())
)

pem = serialization.Encoding.PEM
(CERT_DIR / "device_chain.pem").write_bytes(dev_cert.public_bytes(pem) + ca_cert.public_bytes(pem))
(CERT_DIR / "ca_cert.pem").write_bytes(ca_cert.public_bytes(pem))
(CERT_DIR / "device_key.pem").write_bytes(dev_key.private_bytes(
    pem, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))

print("Created test certificates in", CERT_DIR)
