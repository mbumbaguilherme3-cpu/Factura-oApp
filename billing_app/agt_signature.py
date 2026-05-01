"""
AGT Invoice Signature Engine - JWS (JSON Web Signature) Implementation
Implements digital signature for AGT compliance
Uses cryptographic signing for invoice authentication
"""

import hashlib
import hmac
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any
from enum import Enum
import logging

# Configure logging for audit trail
logger = logging.getLogger(__name__)


class SignatureAlgorithm(Enum):
    """Supported signature algorithms"""
    RS256 = "RS256"  # RSA with SHA-256 (recommended for AGT)
    RS512 = "RS512"  # RSA with SHA-512
    HS256 = "HS256"  # HMAC with SHA-256 (development only)


class SignatureException(Exception):
    """Raised when signature operation fails"""
    pass


class JWSSignatureEngine:
    """
    JWS (JSON Web Signature) implementation for AGT invoice signatures
    
    Reference: RFC 7515
    
    Structure:
    JWS = BASE64(header) + "." + BASE64(payload) + "." + BASE64(signature)
    
    Header contains:
    - alg: Algorithm (RS256)
    - typ: Type (JWT)
    - kid: Key ID (certificate version)
    - x5c: X.509 certificate chain
    
    Payload contains:
    - Invoice data hash
    - Invoice number
    - Signature timestamp
    - Certificate info
    """
    
    def __init__(self, algorithm: SignatureAlgorithm = SignatureAlgorithm.RS256):
        """Initialize signature engine"""
        self.algorithm = algorithm
        self.private_key = None
        self.public_key = None
        self.certificate = None
        self.certificate_version = None
    
    def load_keys(
        self,
        private_key_path: str,
        public_key_path: str = None,
        certificate_path: str = None,
        certificate_version: int = 1
    ) -> Tuple[bool, str]:
        """
        Load cryptographic keys and certificate
        
        Args:
            private_key_path: Path to private key (PEM format)
            public_key_path: Path to public key (PEM format)
            certificate_path: Path to X.509 certificate (PEM format)
            certificate_version: Version number of this certificate
            
        Returns:
            Tuple: (success, error_message)
        """
        try:
            # Import cryptography modules
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            from cryptography import x509
            
            # Load private key
            with open(private_key_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            
            # Load public key (optional, can derive from private)
            if public_key_path:
                with open(public_key_path, 'rb') as f:
                    self.public_key = serialization.load_pem_public_key(
                        f.read(),
                        backend=default_backend()
                    )
            else:
                # Derive public key from private key
                self.public_key = self.private_key.public_key()
            
            # Load certificate (if available)
            if certificate_path:
                with open(certificate_path, 'rb') as f:
                    cert_data = f.read()
                    self.certificate = x509.load_pem_x509_certificate(
                        cert_data,
                        backend=default_backend()
                    )
                    self.certificate_version = certificate_version
            
            logger.info(f"Keys loaded successfully. Algorithm: {self.algorithm.value}")
            return True, ""
        
        except FileNotFoundError as e:
            msg = f"Key file not found: {e}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error loading keys: {str(e)}"
            logger.error(msg)
            return False, msg
    
    def sign_invoice(
        self,
        invoice_data: Dict[str, Any],
        operator_id: str,
        operator_ip: str = None
    ) -> Tuple[Optional[str], str]:
        """
        Create JWS signature for invoice
        
        Args:
            invoice_data: Invoice data to sign
            operator_id: ID of operator performing signature
            operator_ip: IP address of operator
            
        Returns:
            Tuple: (jws_signature, error_message)
        """
        
        if not self.private_key:
            return None, "Private key not loaded"
        
        try:
            # Create JWS Header
            header = {
                "alg": self.algorithm.value,
                "typ": "JWT",
                "kid": f"agt-key-v{self.certificate_version}",
            }
            
            if self.certificate:
                header["x5c"] = self._extract_certificate_chain()
            
            # Create JWS Payload
            payload = self._create_signature_payload(invoice_data, operator_id, operator_ip)
            
            # Encode header and payload
            header_encoded = self._base64url_encode(json.dumps(header))
            payload_encoded = self._base64url_encode(json.dumps(payload))
            
            # Create signing input
            signing_input = f"{header_encoded}.{payload_encoded}".encode()
            
            # Sign using private key
            signature_bytes = self._sign_data(signing_input)
            signature_encoded = self._base64url_encode(signature_bytes, is_binary=True)
            
            # Create JWS
            jws = f"{header_encoded}.{payload_encoded}.{signature_encoded}"
            
            logger.info(f"Invoice {invoice_data.get('invoice_number')} signed successfully by {operator_id}")
            return jws, ""
        
        except Exception as e:
            msg = f"Signature error: {str(e)}"
            logger.error(msg)
            return None, msg
    
    def verify_signature(
        self,
        jws: str,
        expected_invoice_number: str = None
    ) -> Tuple[bool, str]:
        """
        Verify JWS signature
        
        Args:
            jws: JWS signature to verify
            expected_invoice_number: Expected invoice number (optional validation)
            
        Returns:
            Tuple: (is_valid, error_message)
        """
        
        if not self.public_key:
            return False, "Public key not loaded"
        
        try:
            # Split JWS
            parts = jws.split('.')
            if len(parts) != 3:
                return False, "Invalid JWS format (must have 3 parts)"
            
            header_encoded, payload_encoded, signature_encoded = parts
            
            # Decode components
            header = json.loads(self._base64url_decode(header_encoded))
            payload = json.loads(self._base64url_decode(payload_encoded))
            signature_bytes = self._base64url_decode(signature_encoded, is_binary=True)
            
            # Verify invoice number if provided
            if expected_invoice_number:
                if payload.get('invoice_number') != expected_invoice_number:
                    return False, f"Invoice number mismatch in signature"
            
            # Verify algorithm
            if header.get('alg') != self.algorithm.value:
                return False, f"Algorithm mismatch: {header.get('alg')} vs {self.algorithm.value}"
            
            # Verify signature
            signing_input = f"{header_encoded}.{payload_encoded}".encode()
            
            if not self._verify_signature(signing_input, signature_bytes):
                return False, "Signature verification failed"
            
            logger.info(f"Signature verified for invoice {payload.get('invoice_number')}")
            return True, ""
        
        except json.JSONDecodeError:
            return False, "Invalid JSON in JWS header or payload"
        except Exception as e:
            return False, f"Verification error: {str(e)}"
    
    def _create_signature_payload(
        self,
        invoice_data: Dict[str, Any],
        operator_id: str,
        operator_ip: str = None
    ) -> Dict[str, Any]:
        """Create JWS payload for invoice signature"""
        
        payload = {
            "iss": "AGT-FATURACAO",  # Issuer
            "sub": invoice_data.get('invoice_number'),  # Subject
            "invoice_number": invoice_data.get('invoice_number'),
            "invoice_id": invoice_data.get('invoice_id'),
            "invoice_date": invoice_data.get('invoice_date'),
            "supplier_nif": invoice_data.get('supplier_nif'),
            "customer_nif": invoice_data.get('customer_nif'),
            "gross_total": str(invoice_data.get('gross_total', 0)),
            "iva_total": str(invoice_data.get('iva_total', 0)),
            "net_total": str(invoice_data.get('net_total', 0)),
            "data_hash": invoice_data.get('data_hash'),  # SHA256 hash of invoice data
            "signed_at": datetime.utcnow().isoformat() + "Z",
            "iat": int(datetime.utcnow().timestamp()),  # Issued at
            "operator_id": operator_id,
        }
        
        if operator_ip:
            payload["operator_ip"] = operator_ip
        
        # Add certificate info if available
        if self.certificate:
            payload["cert_version"] = self.certificate_version
            payload["cert_subject"] = self._get_certificate_subject()
            payload["cert_valid_from"] = self.certificate.not_valid_before.isoformat()
            payload["cert_valid_to"] = self.certificate.not_valid_after.isoformat()
        
        return payload
    
    def _sign_data(self, data: bytes) -> bytes:
        """Sign data using private key"""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        if self.algorithm == SignatureAlgorithm.RS256:
            return self.private_key.sign(
                data,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
        elif self.algorithm == SignatureAlgorithm.RS512:
            return self.private_key.sign(
                data,
                padding.PKCS1v15(),
                hashes.SHA512()
            )
        else:
            raise SignatureException(f"Unsupported algorithm: {self.algorithm}")
    
    def _verify_signature(self, data: bytes, signature: bytes) -> bool:
        """Verify signature using public key"""
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            
            if self.algorithm == SignatureAlgorithm.RS256:
                self.public_key.verify(
                    signature,
                    data,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
            elif self.algorithm == SignatureAlgorithm.RS512:
                self.public_key.verify(
                    signature,
                    data,
                    padding.PKCS1v15(),
                    hashes.SHA512()
                )
            else:
                return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def _base64url_encode(data: Any, is_binary: bool = False) -> str:
        """Encode data using base64url"""
        if isinstance(data, str):
            data = data.encode()
        elif not is_binary:
            data = data.encode() if not isinstance(data, bytes) else data
        
        return base64.urlsafe_b64encode(data).decode().rstrip('=')
    
    @staticmethod
    def _base64url_decode(data: str, is_binary: bool = False) -> Any:
        """Decode base64url data"""
        # Add padding if needed
        padding = 4 - len(data) % 4
        if padding:
            data += '=' * padding
        
        decoded = base64.urlsafe_b64decode(data)
        return decoded if is_binary else decoded.decode()
    
    def _extract_certificate_chain(self) -> list:
        """Extract certificate chain for JWS header"""
        if not self.certificate:
            return []
        
        try:
            # Convert certificate to DER format (binary)
            from cryptography.hazmat.primitives import serialization
            der_cert = self.certificate.public_bytes(serialization.Encoding.DER)
            # Encode to base64
            b64_cert = base64.b64encode(der_cert).decode()
            return [b64_cert]
        except Exception:
            return []
    
    def _get_certificate_subject(self) -> str:
        """Get certificate subject name"""
        if not self.certificate:
            return ""
        try:
            cn = self.certificate.subject.get_attributes_for_oid(
                # OID for Common Name
            )[0].value
            return cn
        except Exception:
            return self.certificate.subject.rfc4514_string()


class SignatureAuditTrail:
    """
    Audit trail for signature operations
    Logs all signature activities for regulatory compliance
    """
    
    @staticmethod
    def log_signature_operation(
        operation_type: str,
        invoice_id: str,
        invoice_number: str,
        operator_id: str,
        operator_ip: str,
        status: str,
        status_code: str = None,
        status_message: str = None,
        signature_hash: str = None
    ) -> Dict[str, Any]:
        """
        Log signature operation for audit trail
        
        Args:
            operation_type: Type of operation (SIGN, VERIFY, SUBMIT)
            invoice_id: Invoice ID
            invoice_number: Invoice number
            operator_id: Operator performing operation
            operator_ip: Operator IP address
            status: Operation status (S=Success, F=Failure)
            status_code: Error/response code if applicable
            status_message: Detailed message
            signature_hash: SHA256 hash of signature
            
        Returns:
            Audit log entry dict
        """
        
        log_entry = {
            'audit_id': hashlib.sha256(
                f"{invoice_id}{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:36],
            'invoice_id': invoice_id,
            'invoice_number': invoice_number,
            'operation_type': operation_type,
            'status': status,
            'status_code': status_code,
            'status_message': status_message,
            'operator_id': operator_id,
            'operator_ip': operator_ip,
            'signature_hash': signature_hash,
            'created_at': datetime.utcnow().isoformat(),
        }
        
        logger.info(f"Signature audit: {operation_type} on {invoice_number} - Status: {status}")
        return log_entry


__all__ = [
    'SignatureAlgorithm',
    'SignatureException',
    'JWSSignatureEngine',
    'SignatureAuditTrail',
]
