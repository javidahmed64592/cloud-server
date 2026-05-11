"""Generate self-signed SSL certificate for local development."""

import ipaddress
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from template_python.logging_setup import setup_default_logging

from python_template_server.models import CertificateConfigModel

setup_default_logging()
logger = logging.getLogger(__name__)


class CertificateHandler:
    """Handles SSL certificate generation and management."""

    def __init__(self, certificate_config: CertificateConfigModel) -> None:
        """Initialize the CertificateHandler."""
        self.cert_dir = certificate_config.directory
        self.cert_file = certificate_config.ssl_cert_file_path
        self.key_file = certificate_config.ssl_key_file_path
        self.days_valid = certificate_config.days_valid

    @property
    def certificate_subject(self) -> x509.Name:
        """Define the subject for the self-signed certificate."""
        return x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "UK"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Development"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ]
        )

    @staticmethod
    def new_private_key() -> rsa.RSAPrivateKey:
        """Generate a new RSA private key."""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )

    @staticmethod
    def _write_to_file(file_path: Path, data: bytes) -> None:
        """Write data to a file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)

    def write_to_key_file(self, data: bytes) -> None:
        """Write data to the key file."""
        self._write_to_file(self.key_file, data)

    def write_to_cert_file(self, data: bytes) -> None:
        """Write data to the certificate file."""
        self._write_to_file(self.cert_file, data)

    def generate_self_signed_cert(self) -> None:
        """Generate a self-signed certificate and private key.

        :raise SystemExit: If certificate directory cannot be created
        :raise OSError: If certificate files cannot be written
        :raise PermissionError: If insufficient permissions to write certificate files
        """
        try:
            # Ensure certificate directory exists and is writable
            self.cert_file.parent.mkdir(parents=True, exist_ok=True)

            # Test write permissions
            if not self.cert_file.parent.exists():
                logger.error("Failed to create certificate directory: %s", self.cert_file.parent)
                sys.exit(1)

            # Generate private key
            private_key = self.new_private_key()

            # Create certificate subject and issuer (self-signed, so they're the same)
            subject = issuer = self.certificate_subject

            # Build certificate
            certificate = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.now(UTC))
                .not_valid_after(datetime.now(UTC) + timedelta(days=self.days_valid))
                .add_extension(
                    x509.SubjectAlternativeName(
                        [
                            x509.DNSName("localhost"),
                            x509.DNSName("127.0.0.1"),
                            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                        ]
                    ),
                    critical=False,
                )
                .sign(private_key, hashes.SHA256())
            )

            # Write private key to file
            self.write_to_key_file(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

            # Write certificate to file
            self.write_to_cert_file(certificate.public_bytes(serialization.Encoding.PEM))

            logger.info("Certificate generated successfully!")
            logger.info("Saved in directory: %s", self.cert_dir)
            logger.info("Valid for: %d days", self.days_valid)

        except PermissionError:
            logger.exception("Permission denied when writing certificate files: %s", self.cert_file.parent)
            raise
        except OSError:
            logger.exception("Failed to generate certificate files!")
            raise
