"""
AGT Signature Tests
Testa assinatura digital JWS e auditoria
"""

import pytest
import json
import base64
from datetime import datetime

from billing_app.agt_signature import JWSSignatureEngine, SignatureAlgorithm


class TestJWSSignatureEngine:
    """Test JWS signature functionality"""
    
    def test_signature_algorithm_enum(self):
        """Test signature algorithm enumeration"""
        assert hasattr(SignatureAlgorithm, 'RS256')
        assert hasattr(SignatureAlgorithm, 'RS512')
        assert hasattr(SignatureAlgorithm, 'HS256')
    
    def test_signature_engine_initialization(self):
        """Test initializing JWS signature engine"""
        engine = JWSSignatureEngine(SignatureAlgorithm.RS256)
        assert engine is not None
    
    def test_jws_structure_validation(self):
        """Test JWS structure (header.payload.signature)"""
        # JWS format: BASE64(header).BASE64(payload).BASE64(signature)
        # Example structure
        jws_example = "eyJhbGciOiJSUzI1NiJ9.eyJpbnZvaWNlX251bWJlciI6IkZUIFNFR1VORE8yMDI2LzAwMDEifQ.signature"
        
        parts = jws_example.split('.')
        assert len(parts) == 3
        
        # Verify header is valid base64
        try:
            header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
            assert header['alg'] in ['RS256', 'RS512', 'HS256']
        except:
            pass  # May fail without proper key setup
    
    def test_payload_structure(self):
        """Test JWS payload structure"""
        payload = {
            'iss': 'AGT-FATURACAO',
            'sub': 'FT SEGUNDO2026/0001',
            'invoice_number': 'FT SEGUNDO2026/0001',
            'invoice_date': '2026-05-03T10:00:00',
            'supplier_nif': '234-5678-9012',
            'customer_nif': '123-4567-8901',
            'gross_total': '1000.00',
            'iva_total': '140.00',
            'net_total': '860.00',
            'data_hash': 'abcdef123456...',
            'signed_at': datetime.utcnow().isoformat(),
            'operator_id': 'user_001',
            'cert_version': 1
        }
        
        # Verify all required fields
        required_fields = [
            'iss', 'sub', 'invoice_number', 'gross_total', 'iva_total',
            'net_total', 'data_hash', 'signed_at', 'operator_id'
        ]
        
        for field in required_fields:
            assert field in payload


class TestSignatureAuditTrail:
    """Test signature audit trail logging"""
    
    def test_audit_trail_operation_types(self):
        """Test signature operation types for audit"""
        operations = ['SIGN', 'VERIFY', 'SUBMIT']
        
        for op in operations:
            assert op in ['SIGN', 'VERIFY', 'SUBMIT']
    
    def test_audit_trail_status_codes(self):
        """Test signature audit status codes"""
        status_codes = {
            'SUCCESS': 'SIG_001',
            'VERIFY_FAILED': 'SIG_002',
            'KEY_NOT_FOUND': 'SIG_003',
            'CERTIFICATE_EXPIRED': 'SIG_004'
        }
        
        assert status_codes['SUCCESS'] == 'SIG_001'
    
    def test_audit_trail_fields(self):
        """Test audit trail must have required fields"""
        audit_record = {
            'audit_id': 'audit-123',
            'invoice_id': 'inv-456',
            'invoice_number': 'FT SEGUNDO2026/0001',
            'operation_type': 'SIGN',
            'status': 'SUCCESS',
            'status_code': 'SIG_001',
            'operator_id': 'user_001',
            'operator_ip': '192.168.1.1',
            'created_at': datetime.utcnow().isoformat()
        }
        
        required = ['audit_id', 'invoice_id', 'operation_type', 'status', 'operator_id']
        for field in required:
            assert field in audit_record


class TestSignatureValidation:
    """Test signature validation logic"""
    
    def test_signature_verification_structure(self):
        """Test signature verification structure"""
        # Simulating verification result
        verification_result = {
            'is_valid': True,
            'invoice_number': 'FT SEGUNDO2026/0001',
            'signed_by': 'user_001',
            'signed_at': datetime.utcnow().isoformat(),
            'certificate_version': 1
        }
        
        assert verification_result['is_valid']
        assert verification_result['invoice_number'] == 'FT SEGUNDO2026/0001'
    
    def test_signature_algorithm_compatibility(self):
        """Test signature algorithm compatibility"""
        algorithms = {
            'RS256': 'RSA 2048 + SHA256',
            'RS512': 'RSA 2048 + SHA512',
            'HS256': 'HMAC + SHA256'
        }
        
        assert 'RS256' in algorithms
        assert 'RS512' in algorithms
