# AGT Compliance - Cibersegurança e Gestão de Chaves Privadas

## Visão Geral de Segurança

Este documento descreve as melhores práticas para proteger chaves de certificação e implementar um sistema de assinatura de faturas seguro e auditável para conformidade fiscal angolana (AGT).

## 1. Armazenamento Seguro de Chaves Privadas em Linux

### 1.1 Estrutura de Diretórios

```bash
/etc/ssl/agt/
├── private/                      # Apenas root pode ler
│   ├── keys/
│   │   ├── key_v1.pem          # Versão 1 (ativa)
│   │   ├── key_v2.pem          # Versão 2 (ativa)
│   │   └── key_v_archived/
│   │       └── key_v0.pem.archived  # Versão 0 (descativada)
│   ├── .keypass               # Senha de proteção (modo 0400)
│   └── README                 # Instruções (modo 0444)
├── public/                       # Legível publicamente
│   ├── certificates/
│   │   ├── agt_cert_v1.pem
│   │   └── agt_cert_v2.pem
│   ├── ca_chain.pem            # Cadeia de certificados da AGT
│   └── crls/                   # Certificate Revocation Lists
│       └── agt_crl.pem
└── config/
    └── key_rotation.conf       # Configuração de rotação
```

### 1.2 Permissões de Ficheiros

```bash
# Chaves privadas - ultra-restritivo
chmod 0400 /etc/ssl/agt/private/keys/*.pem
chown root:billing-app /etc/ssl/agt/private/keys/

# Ficheiro de senha - máxima segurança
chmod 0400 /etc/ssl/agt/private/.keypass
chown root:root /etc/ssl/agt/private/.keypass

# Certificados públicos - legíveis
chmod 0644 /etc/ssl/agt/public/certificates/*.pem
chown root:root /etc/ssl/agt/public/certificates/

# Configuração - legível apenas por root
chmod 0600 /etc/ssl/agt/config/key_rotation.conf
chown root:root /etc/ssl/agt/config/key_rotation.conf

# Diretório principal - protegido
chmod 0750 /etc/ssl/agt/
chmod 0700 /etc/ssl/agt/private/
chmod 0755 /etc/ssl/agt/public/
```

### 1.3 Proteção de Chaves com Encriptação

#### Opção 1: LUKS (Linux Unified Key Setup)

```bash
# Criar volume encriptado para chaves
sudo fallocate -l 100M /var/lib/agt_keys.img
sudo cryptsetup luksFormat /var/lib/agt_keys.img
sudo cryptsetup luksOpen /var/lib/agt_keys.img agt_keys_crypt
sudo mkfs.ext4 /dev/mapper/agt_keys_crypt
sudo mkdir -p /mnt/agt_secure
sudo mount /dev/mapper/agt_keys_crypt /mnt/agt_secure

# Mover chaves para volume encriptado
sudo mv /etc/ssl/agt/private/keys/* /mnt/agt_secure/
sudo umount /mnt/agt_secure
sudo cryptsetup luksClose agt_keys_crypt
```

#### Opção 2: eCryptfs (Encriptação por ficheiro)

```bash
sudo apt-get install ecryptfs-utils
sudo mount -t ecryptfs /etc/ssl/agt/private/keys /etc/ssl/agt/private/keys
# Será solicitada password de encriptação
```

#### Opção 3: Proteger chaves com senha OpenSSL

```bash
# Criar chave protegida com AES-256
openssl genrsa -aes256 -out /etc/ssl/agt/private/keys/key_v1_protected.pem -passout file:/etc/ssl/agt/private/.keypass 2048

# Desencriptar quando necessário (em memória)
openssl rsa -in /etc/ssl/agt/private/keys/key_v1_protected.pem -passin file:/etc/ssl/agt/private/.keypass -text -noout
```

## 2. Arquivo de Configuração de Chaves

**Ficheiro: /etc/ssl/agt/config/key_config.json**

```json
{
  "keys": [
    {
      "version": 1,
      "algorithm": "RSA",
      "key_size": 2048,
      "private_key_path": "/etc/ssl/agt/private/keys/key_v1.pem",
      "public_key_path": "/etc/ssl/agt/public/certificates/agt_cert_v1.pem",
      "certificate_subject": "CN=AGT Faturacao,O=Company,C=AO",
      "valid_from": "2025-01-01T00:00:00Z",
      "valid_to": "2027-12-31T23:59:59Z",
      "is_active": true,
      "rotation_date": "2026-06-01",
      "status": "ACTIVE",
      "fingerprint": "SHA256:abc123def456...",
      "protection": "AES256-GCM",
      "access_log": "/var/log/agt/key_v1_access.log"
    },
    {
      "version": 2,
      "algorithm": "RSA",
      "key_size": 2048,
      "private_key_path": "/etc/ssl/agt/private/keys/key_v2.pem",
      "public_key_path": "/etc/ssl/agt/public/certificates/agt_cert_v2.pem",
      "certificate_subject": "CN=AGT Faturacao,O=Company,C=AO",
      "valid_from": "2026-06-01T00:00:00Z",
      "valid_to": "2028-05-31T23:59:59Z",
      "is_active": false,
      "rotation_date": "2027-06-01",
      "status": "PENDING",
      "fingerprint": "SHA256:xyz789uvw012...",
      "protection": "AES256-GCM",
      "access_log": "/var/log/agt/key_v2_access.log"
    }
  ],
  "key_management": {
    "rotation_interval_months": 12,
    "backup_retention_days": 2555,
    "encrypted_backup_path": "/backup/agt_keys_backup/",
    "hsm_enabled": false,
    "hsm_device": "/dev/pkcs11"
  }
}
```

## 3. Script Seguro de Assinatura Isolado

**Ficheiro: /usr/local/bin/agt_sign_invoice.py**

```python
#!/usr/bin/env python3
"""
AGT Invoice Signature Service - Isolated & Audited
Runs as dedicated system user with minimal privileges
"""

import os
import sys
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Tuple

# Logging to syslog for audit trail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - AGT_SIGN - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/agt/signature.log'),
        logging.handlers.SysLogHandler(address='/dev/log')
    ]
)
logger = logging.getLogger(__name__)

# Security checks
ALLOWED_USER = 'billing-app'
KEY_DIRECTORY = '/etc/ssl/agt/private/keys'
CONFIG_FILE = '/etc/ssl/agt/config/key_config.json'
MAX_INVOICE_SIZE = 1_000_000  # 1MB max

def security_checks() -> Tuple[bool, str]:
    """Verify process is running with correct privileges"""
    
    # Check user
    current_user = os.getuid()
    expected_user = os.getpwnam(ALLOWED_USER).pw_uid
    
    if current_user != expected_user:
        return False, f"Must run as '{ALLOWED_USER}'"
    
    # Check working directory
    if not os.path.exists(KEY_DIRECTORY):
        return False, f"Key directory not found: {KEY_DIRECTORY}"
    
    # Verify directory permissions (should be 0700)
    dir_stat = os.stat(KEY_DIRECTORY)
    if oct(dir_stat.st_mode)[-3:] != '700':
        return False, f"Key directory has incorrect permissions: {oct(dir_stat.st_mode)}"
    
    return True, ""

def load_active_key() -> Tuple[str, str]:
    """Load active certificate key"""
    
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    # Find active key
    for key_config in config['keys']:
        if key_config['is_active'] and key_config['status'] == 'ACTIVE':
            return (
                key_config['private_key_path'],
                key_config['version']
            )
    
    raise Exception("No active key found in configuration")

def sign_invoice(
    invoice_json: str,
    operator_id: str,
    operator_ip: str
) -> str:
    """
    Sign invoice with audit trail
    
    Args:
        invoice_json: Invoice data as JSON
        operator_id: ID of operator
        operator_ip: IP address of operator
        
    Returns:
        JWS signature
    """
    
    # Validate input size
    if len(invoice_json) > MAX_INVOICE_SIZE:
        raise ValueError(f"Invoice data exceeds max size: {len(invoice_json)}")
    
    # Parse invoice
    invoice_data = json.loads(invoice_json)
    invoice_number = invoice_data.get('invoice_number')
    
    logger.info(f"Signing invoice {invoice_number} by operator {operator_id} from {operator_ip}")
    
    # Load key
    key_path, key_version = load_active_key()
    
    try:
        # Import signature engine
        from billing_app.agt_signature import JWSSignatureEngine, SignatureAlgorithm
        
        # Initialize engine
        engine = JWSSignatureEngine(SignatureAlgorithm.RS256)
        
        # Load keys
        success, error = engine.load_keys(
            private_key_path=key_path,
            certificate_version=int(key_version)
        )
        
        if not success:
            raise Exception(f"Failed to load keys: {error}")
        
        # Calculate data hash
        invoice_hash = hashlib.sha256(invoice_json.encode()).hexdigest()
        invoice_data['data_hash'] = invoice_hash
        
        # Sign
        jws, error = engine.sign_invoice(
            invoice_data,
            operator_id=operator_id,
            operator_ip=operator_ip
        )
        
        if error:
            raise Exception(f"Signature failed: {error}")
        
        # Log success
        logger.info(f"Successfully signed invoice {invoice_number}")
        
        return jws
    
    except Exception as e:
        logger.error(f"Signature operation failed: {str(e)}")
        raise

if __name__ == '__main__':
    # Security checks
    passed, error = security_checks()
    if not passed:
        logger.error(f"Security check failed: {error}")
        sys.exit(1)
    
    # Read stdin
    invoice_json = sys.stdin.read()
    operator_id = sys.argv[1] if len(sys.argv) > 1 else 'UNKNOWN'
    operator_ip = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1'
    
    try:
        signature = sign_invoice(invoice_json, operator_id, operator_ip)
        # Output signature
        sys.stdout.write(signature)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)
```

**Permissões:**

```bash
chmod 0750 /usr/local/bin/agt_sign_invoice.py
chown root:billing-app /usr/local/bin/agt_sign_invoice.py

# Criar usuário de sistema dedicado
useradd -r -s /bin/false -d /var/lib/agt -m billing-app
```

## 4. Integração com Aplicação Python

**Ficheiro: /etc/sudoers.d/agt-signing**

```sudoers
# Allow app to call signing script as billing-app user
www-data ALL=(billing-app) NOPASSWD: /usr/local/bin/agt_sign_invoice.py
```

**Código na aplicação:**

```python
import subprocess
import json
from pathlib import Path

class SecureSignatureService:
    """Service for secure invoice signing via isolated process"""
    
    @staticmethod
    def sign_invoice(invoice_data: dict, operator_id: str, operator_ip: str) -> str:
        """
        Sign invoice in isolated process with elevated privileges
        
        Args:
            invoice_data: Invoice to sign
            operator_id: Operator ID
            operator_ip: Operator IP
            
        Returns:
            JWS signature
        """
        
        try:
            # Prepare invoice JSON
            invoice_json = json.dumps(invoice_data)
            
            # Call isolated signing process via sudo
            result = subprocess.run(
                [
                    'sudo',
                    '-u', 'billing-app',
                    '/usr/local/bin/agt_sign_invoice.py',
                    operator_id,
                    operator_ip
                ],
                input=invoice_json,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"Signing failed: {result.stderr}")
            
            return result.stdout.strip()
        
        except subprocess.TimeoutExpired:
            raise Exception("Signature operation timed out")
        except Exception as e:
            raise Exception(f"Signature service error: {str(e)}")
```

## 5. Monitoramento e Auditoria

### 5.1 Logging de Acesso a Chaves

```bash
# Monitorar acesso ao diretório de chaves
auditctl -w /etc/ssl/agt/private/keys -p wa -k agt_key_access

# Ver logs de auditoria
ausearch -k agt_key_access

# Registar em rsyslog (adicionar a /etc/rsyslog.d/agt.conf)
:programname, isequal, "agt_sign" -/var/log/agt/signature.log
& stop
```

### 5.2 Alertas de Segurança

```bash
# Detectar tentativas de acesso não autorizado
grep "Permission denied" /var/log/agt/signature.log | \
  mail -s "AGT Unauthorized Access Attempt" security@company.com

# Monitorar rotação de chaves
watch -n 3600 'ls -la /etc/ssl/agt/private/keys/ | mail -s "AGT Key Status" ops@company.com'
```

## 6. Backup Seguro de Chaves

```bash
#!/bin/bash
# Daily encrypted backup of AGT keys

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backup/agt_keys
KEY_DIR=/etc/ssl/agt/private/keys
PASSPHRASE=$(cat /etc/ssl/agt/private/.keypass)

# Create backup directory
mkdir -p $BACKUP_DIR

# Tar and encrypt backup
tar czf - $KEY_DIR | \
  openssl enc -aes-256-cbc -salt -out $BACKUP_DIR/agt_keys_$BACKUP_DATE.tar.gz.enc \
  -pass pass:"$PASSPHRASE"

# Remove backup older than 90 days
find $BACKUP_DIR -name "*.enc" -mtime +90 -delete

# Verify backup integrity
openssl enc -aes-256-cbc -d -in $BACKUP_DIR/agt_keys_$BACKUP_DATE.tar.gz.enc \
  -pass pass:"$PASSPHRASE" | tar tzf - > /dev/null

echo "Backup completed: $BACKUP_DIR/agt_keys_$BACKUP_DATE.tar.gz.enc"
```

## 7. Conformidade e Auditoria

### Requisitos de Conformidade:
- ✅ Assinatura JWS com certificado X.509
- ✅ Chaves privadas armazenadas de forma segura
- ✅ Acesso a chaves registado e auditado
- ✅ Rotação de chaves a cada 12-24 meses
- ✅ Operações de assinatura isoladas
- ✅ Backup encriptado de chaves
- ✅ Conformidade com AGT (Autoridade Geral Tributária)

### Checklist de Implementação:
- [ ] Estrutura de diretórios criada com permissões corretas
- [ ] Chaves privadas geradas e protegidas
- [ ] Certificados da AGT obtidos
- [ ] Script de assinatura isolado implementado
- [ ] Logging e auditoria ativados
- [ ] Backup automático configurado
- [ ] Rotação de chaves planeada
- [ ] Testes de segurança completados

## 8. Troubleshooting

### Erro: "Permission denied" ao aceder chaves

```bash
# Verificar proprietário e permissões
ls -la /etc/ssl/agt/private/keys/
stat /etc/ssl/agt/private/keys/key_v1.pem

# Corrigir permissões
sudo chown root:billing-app /etc/ssl/agt/private/keys/key_v1.pem
sudo chmod 0400 /etc/ssl/agt/private/keys/key_v1.pem
```

### Erro: "Signature verification failed"

```bash
# Testar chave localmente
openssl rsa -in /etc/ssl/agt/private/keys/key_v1.pem -check -noout

# Validar certificado
openssl x509 -in /etc/ssl/agt/public/certificates/agt_cert_v1.pem -text -noout

# Verificar correspondência chave-certificado
openssl x509 -in /etc/ssl/agt/public/certificates/agt_cert_v1.pem -noout -pubkey > /tmp/pub.pem
openssl pkey -in /etc/ssl/agt/private/keys/key_v1.pem -pubout > /tmp/priv_pub.pem
diff /tmp/pub.pem /tmp/priv_pub.pem
```

---

**Documento de Segurança AGT - Gerado em 2026**
**Classificação: CONFIDENCIAL - Acesso Restrito**
