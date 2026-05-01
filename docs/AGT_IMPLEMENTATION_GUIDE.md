# AGT (Autoridade Geral Tributária) - Sistema de Conformidade Fiscal Angolana

## Visão Geral

Sistema completo de conformidade fiscal para Angola, implementando os requisitos da **Autoridade Geral Tributária (AGT)** e do padrão **SAF-T (Standard Audit File - Tax)**, versão AO 1.05_01.

**Data:** Maio 2026  
**Versão:** 1.0  
**Público:** Empresas de médio porte com faturação eletrónica

---

## 1. Arquitetura do Sistema

### 1.1 Componentes Principais

```
┌─────────────────────────────────────────────────────┐
│         APLICAÇÃO FLASK (Python)                    │
│  - Rotas REST API                                   │
│  - Validação de entrada                             │
│  - Lógica de negócio                                │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┬──────────────┬──────────────┐
        │                     │              │              │
        ▼                     ▼              ▼              ▼
┌──────────────┐    ┌────────────────┐   ┌──────────┐  ┌─────────┐
│ Validadores  │    │  Imutabilidade │   │ Assinatura   │ SAF-T  │
│  (agt_      │    │   (agt_        │   │  (agt_    │  │ (agt_  │
│ validators) │    │  immutability) │   │ signature) │  │saft_   │
└──────────────┘    └────────────────┘   └──────────┘  │gen)    │
      │                    │                   │        │        │
      │                    │                   │        └────────┘
      └────────────────────┼───────────────────┴──────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
        ▼                                     ▼
┌─────────────────────────┐    ┌──────────────────────────┐
│    BANCO DE DADOS       │    │ SISTEMA DE CHAVES (Linux)│
│  (PostgreSQL/SQLite)    │    │  /etc/ssl/agt/           │
│  - Tabelas AGT          │    │  - Chaves privadas (encrypted)
│  - Audit trail          │    │  - Certificados X.509    │
│  - Compliance logs      │    │  - Configuração de rotação
└─────────────────────────┘    └──────────────────────────┘
        │                            │
        └────────────────┬───────────┘
                         │
                    ┌────▼─────┐
                    │ AUDITORIA │
                    └───────────┘
```

### 1.2 Fluxo de uma Fatura Completa

```
1. CRIAÇÃO
   ├─ Validar NIF cliente/fornecedor
   ├─ Validar IVA regime e taxas
   ├─ Validar linhas de fatura
   └─ Status: DRAFT (D)

2. EMISSÃO
   ├─ Calcular hash SHA256
   ├─ Bloquear para edição
   ├─ Gerar número série (FT SEGUNDO2026/001)
   ├─ Garantir cronologia
   └─ Status: ISSUED (I)

3. ASSINATURA (JWS)
   ├─ Carregar chave privada (/etc/ssl/agt/private/)
   ├─ Gerar payload JWS
   ├─ Assinar com RS256
   ├─ Registar auditoria
   └─ Status: SIGNED (S)

4. SUBMISSÃO À AGT
   ├─ Exportar SAF-T XML
   ├─ Enviar para API AGT
   ├─ Receber confirmação
   └─ Status: SUBMITTED (S)

5. CONFIRMAÇÃO AGT
   ├─ Aguardar validação
   ├─ Receber validação_code
   └─ Status: ACKNOWLEDGED (A)

6. ARQUIVO
   ├─ Guardar em backup encriptado
   ├─ Manter auditoria completa
   ├─ Preparar para inspeção
   └─ Status: ARCHIVED
```

---

## 2. Modelos de Base de Dados

### 2.1 Tabelas Principais

```sql
-- Cliente/Fornecedor (campo NIF obrigatório)
agt_any_entity
├── entity_id (UUID)
├── nif (String 14) [ÚNICO]
├── nif_type (ENUM)
├── name, address, city, country
├── is_tax_resident, is_vat_registered
└── created_at, updated_at, deleted_at

-- Produto/Serviço
agt_product
├── product_id (UUID)
├── product_code (String 50)
├── description
├── unit_price (Numeric)
├── iva_regime (ENUM)
├── iva_rate (Numeric)
├── iva_exemption_code (String 3) [obrigatório se rate=0]
└── created_at, updated_at

-- Cabeçalho Fatura
agt_invoice
├── invoice_id (UUID)
├── invoice_number (String 50) [ÚNICO] "FT SEGUNDO2026/0001"
├── supplier_id, customer_id (FK)
├── invoice_date, due_date
├── gross_total, iva_total, net_total
├── data_hash_before_issue (SHA256)
├── is_issued, is_editable
├── signature_jws (Text)
├── certificate_version
├── agt_submission_id, agt_validation_code
└── created_at, updated_at, deleted_at

-- Linhas Fatura
agt_invoice_line
├── line_id (UUID)
├── invoice_id (FK)
├── product_id (FK)
├── line_number, description
├── quantity, unit_price
├── line_gross, iva_amount, line_net
├── iva_regime, iva_exemption_code
└── created_at

-- Auditoria Assinatura
agt_invoice_signature_audit
├── audit_id (UUID)
├── invoice_id (FK)
├── operation_type (SIGN/VERIFY/SUBMIT)
├── status, status_code, status_message
├── operator_id, operator_ip
├── agt_response_code, agt_response_body
└── created_at

-- Log de Conformidade
agt_compliance_log
├── log_id (UUID)
├── event_type, entity_type, entity_id
├── action, details
├── operator_id, operator_ip
├── data_before, data_after (JSON)
├── is_compliant, compliance_notes
└── created_at

-- Gestão Certificados
agt_certificate_key
├── key_id (UUID)
├── certificate_version
├── subject, issuer
├── valid_from, valid_to
├── key_path, key_fingerprint
├── key_protected_with (AES256-GCM/HSM)
├── is_active
└── created_at
```

---

## 3. Validadores (Conformidade com AGT)

### 3.1 Validação de NIF

```python
# Formato: XXX-XXXX-XXXX (11 dígitos)
# Verificação: Checksum (última dígito é dígito verificador)

validador = NIFValidator()
is_valid, error = validador.validate_format("123-4567-8901")
nif_type = validador.get_nif_type("123-4567-8901")  # NATURAL_PERSON
formatted = validador.format_nif("123-4567-8901")   # "123-4567-8901"
```

### 3.2 Validação de IVA

```python
# Regimes: GENERAL (14%), SIMPLIFIED, EXEMPT (0%), NOT_SUBJECT, REVERSE_CHARGE
# Códigos de Isenção: M01-M09 (obrigatório se rate=0%)

validador_iva = IVAValidator()

# Regime Geral
is_valid, msg = validador_iva.validate_iva_rate(
    rate=Decimal('14.00'),
    regime='GENERAL'
)

# Regime Isento
is_valid, msg = validador_iva.validate_iva_rate(
    rate=Decimal('0.00'),
    regime='EXEMPT',
    exemption_code='M01'  # Artigo 14 CIVA
)
```

### 3.3 Validação de Fatura

```python
# Verificar sequência numérica: FT SEGUNDO2026/0001
# Verificar totais (gross = lines, iva = sum, net = gross - iva)
# Verificar imutabilidade após emissão

validador_fatura = InvoiceValidator()

# Validar número
is_valid, msg = validador_fatura.validate_invoice_number_format(
    "FT SEGUNDO2026/0001",
    "FT",
    1,
    2026
)

# Validar totais
is_valid, msg = validador_fatura.validate_invoice_line_total(
    lines=[...],
    expected_gross=Decimal('1000.00'),
    expected_iva=Decimal('140.00'),
    expected_net=Decimal('860.00')
)
```

---

## 4. Imutabilidade de Faturas

### 4.1 Ciclo de Vida

```
DRAFT (D)  ──issue──>  ISSUED (I)  ──submit──>  SUBMITTED (S)
  │                         │                        │
  │ (editable)              │ (NOT editable)         │
  │                      (locked)                    │
  └─ Cancellable        ┌──────────────────────────┐
                        │                          │
                   Can create:               ┌────▼────┐
                   - Credit Note (NC)        │ SIGNED  │
                   - Debit Note (ND)         │ (JWS)   │
                   - Correction              └─────────┘
```

### 4.2 Proteção de Dados

```python
# Calcular hash SHA256 antes de emitir
engine = InvoiceImmutabilityEngine()
data_hash = engine.calculate_invoice_hash(invoice_data)

# Bloquear fatura após emissão
hash_value, locked_invoice = engine.lock_invoice(
    invoice_data,
    operator_id='user_001'
)

# Verificar integridade
is_intact = engine.verify_invoice_integrity(
    invoice_data,
    stored_hash=hash_value
)

# Prevenir modificações
can_edit, reason = engine.prevent_modification(
    invoice_data,
    operation='EDIT'
)
# Output: (False, "Operation 'EDIT' not allowed for invoice in status 'I'")
```

### 4.3 Correções Autorizadas

Apenas através de Notas de Crédito (NC) e Notas de Débito (ND):

```python
# Criar Nota de Crédito (reversão)
credit_note = InvoiceCorrectionStrategy.create_credit_note(
    original_invoice,
    reason="Desconto concedido",
    operator_id='user_001'
)

# Criar Nota de Débito (cobrança adicional)
debit_note = InvoiceCorrectionStrategy.create_debit_note(
    original_invoice,
    reason="Taxa de administração",
    correction_amount=Decimal('50.00'),
    operator_id='user_001'
)
```

---

## 5. Assinatura Digital (JWS)

### 5.1 Configuração de Chaves

```bash
# 1. Gerar chaves e certificados
openssl genrsa -out /etc/ssl/agt/private/keys/key_v1.pem 2048
openssl req -new -x509 -key /etc/ssl/agt/private/keys/key_v1.pem \
  -out /etc/ssl/agt/public/certificates/agt_cert_v1.pem \
  -subj "/C=AO/O=Company/CN=AGT Faturacao"

# 2. Proteger chaves
chmod 0400 /etc/ssl/agt/private/keys/key_v1.pem
chown root:billing-app /etc/ssl/agt/private/keys/

# 3. Configurar rotação (anual)
crontab -e
# 0 0 1 6 * /usr/local/bin/agt_rotate_keys.sh
```

### 5.2 Processo de Assinatura

```python
from billing_app.agt_signature import JWSSignatureEngine, SignatureAlgorithm

# Inicializar engine
engine = JWSSignatureEngine(SignatureAlgorithm.RS256)

# Carregar chaves
success, error = engine.load_keys(
    private_key_path='/etc/ssl/agt/private/keys/key_v1.pem',
    certificate_path='/etc/ssl/agt/public/certificates/agt_cert_v1.pem',
    certificate_version=1
)

# Assinar fatura
jws_signature, error = engine.sign_invoice(
    invoice_data,
    operator_id='user_001',
    operator_ip='192.168.1.100'
)

# Verificar assinatura
is_valid, error = engine.verify_signature(
    jws_signature,
    expected_invoice_number='FT SEGUNDO2026/0001'
)
```

### 5.3 Formato JWS

```
JWS = BASE64(header) + "." + BASE64(payload) + "." + BASE64(signature)

Header:
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "agt-key-v1",
  "x5c": ["MIIDXTCCAkWgAwIBAgI..."]
}

Payload:
{
  "iss": "AGT-FATURACAO",
  "sub": "FT SEGUNDO2026/0001",
  "invoice_number": "FT SEGUNDO2026/0001",
  "invoice_date": "2026-05-01T10:30:00",
  "supplier_nif": "234-5678-9012",
  "customer_nif": "123-4567-8901",
  "gross_total": "1000.00",
  "iva_total": "140.00",
  "net_total": "860.00",
  "data_hash": "abc123def456...",
  "signed_at": "2026-05-01T15:45:30.123Z",
  "operator_id": "user_001",
  "cert_version": 1,
  "cert_valid_to": "2027-12-31T23:59:59"
}
```

---

## 6. Exportação SAF-T (AO)

### 6.1 Estrutura XML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:AO_1.05_01">
  <Header>
    <AuditFileVersion>1.05_01</AuditFileVersion>
    <AuditFileCountry>AO</AuditFileCountry>
    <AuditFileDateCreated>2026-05-31T23:59:59</AuditFileDateCreated>
    <Company>
      <RegistrationNumber>234-5678-9012</RegistrationNumber>
      <Name>Empresa Angola Lda</Name>
      <Address>
        <AddressDetail>Rua Principal, 123</AddressDetail>
        <City>Luanda</City>
        <PostalCode>1000</PostalCode>
        <Country>AO</Country>
      </Address>
      <Telephone>+244222123456</Telephone>
      <Email>info@empresa.ao</Email>
    </Company>
  </Header>
  
  <MasterFiles>
    <Customers>
      <NumberOfCustomers>1</NumberOfCustomers>
      <Customer>
        <RegistrationNumber>123-4567-8901</RegistrationNumber>
        <Name>Cliente Angola SA</Name>
        <!-- ... -->
      </Customer>
    </Customers>
    <Products>
      <NumberOfProducts>1</NumberOfProducts>
      <Product>
        <ProductCode>CONS-001</ProductCode>
        <ProductDescription>Serviço de Consultoria</ProductDescription>
        <TaxInformation>
          <IVA>
            <IVAType>Normal</IVAType>
            <IVARate>14.00</IVARate>
          </IVA>
        </TaxInformation>
      </Product>
    </Products>
  </MasterFiles>
  
  <SourceDocuments>
    <SalesInvoices>
      <NumberOfEntries>1</NumberOfEntries>
      <Sales>
        <InvoiceNumber>FT SEGUNDO2026/0001</InvoiceNumber>
        <InvoiceDate>2026-05-01</InvoiceDate>
        <Lines>
          <Line>
            <LineNumber>1</LineNumber>
            <Description>Serviço de Consultoria</Description>
            <Quantity>1</Quantity>
            <UnitPrice>1000.00</UnitPrice>
            <LineGross>1000.00</LineGross>
            <Tax>
              <IVA>
                <IVAType>Normal</IVAType>
                <IVARate>14.00</IVARate>
                <IVATaxableAmount>1000.00</IVATaxableAmount>
                <IVATaxAmount>140.00</IVATaxAmount>
              </IVA>
            </Tax>
            <LineNet>860.00</LineNet>
          </Line>
        </Lines>
        <DocumentTotals>
          <TaxPayableAmount>140.00</TaxPayableAmount>
          <NetTotal>860.00</NetTotal>
          <GrossTotal>1000.00</GrossTotal>
        </DocumentTotals>
        <DocumentSignature>eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...</DocumentSignature>
      </Sales>
      <TotalDebitAmount>860.00</TotalDebitAmount>
    </SalesInvoices>
  </SourceDocuments>
</AuditFile>
```

### 6.2 Geração em Python

```python
from billing_app.agt_saft_generator import SAFTAOGenerator

generator = SAFTAOGenerator(company_data={
    'nif': '234-5678-9012',
    'name': 'Empresa Angola Lda',
    # ...
})

xml_output = generator.generate(
    customers=customers_list,
    products=products_list,
    invoices=invoices_list,
    credit_notes=credit_notes_list,
    debit_notes=debit_notes_list
)

# Guardar ficheiro
with open('saft_2026_05.xml', 'w', encoding='utf-8') as f:
    f.write(xml_output)
```

---

## 7. API REST Endpoints

### 7.1 Operações de Fatura

```http
# Criar fatura (DRAFT)
POST /api/invoices
{
  "customer_nif": "123-4567-8901",
  "supplier_nif": "234-5678-9012",
  "invoice_date": "2026-05-01",
  "lines": [...]
}
Response: 201 Created
{
  "invoice_id": "550e8400...",
  "invoice_number": null,  # Será atribuído na emissão
  "status": "D"
}

# Emitir fatura (DRAFT -> ISSUED)
POST /api/invoices/{invoice_id}/issue
Response: 200 OK
{
  "invoice_number": "FT SEGUNDO2026/0001",
  "status": "I",
  "is_editable": false,
  "issued_at": "2026-05-01T15:00:00Z",
  "data_hash": "abc123..."
}

# Assinar fatura (ISSUED -> SIGNED)
POST /api/invoices/{invoice_id}/sign
{
  "operator_id": "user_001"
}
Response: 200 OK
{
  "signature_jws": "eyJhbGciOiJSUzI1NiJ9...",
  "signature_status": "S",
  "signature_timestamp": "2026-05-01T15:05:00Z"
}

# Submeter à AGT
POST /api/invoices/{invoice_id}/submit
Response: 200 OK
{
  "status": "S",
  "agt_submission_id": "AGT-2026-123456",
  "agt_submitted_at": "2026-05-01T15:10:00Z"
}

# Criar Nota de Crédito
POST /api/invoices/{invoice_id}/credit-note
{
  "reason": "Desconto concedido",
  "operator_id": "user_001"
}
Response: 201 Created
{
  "credit_note_id": "550e8400...",
  "series_prefix": "NC",
  "reference_invoice_id": "{invoice_id}"
}

# Exportar SAF-T
GET /api/invoices/saft/export?month=05&year=2026
Response: 200 OK (application/xml)
<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:AO_1.05_01">
  <!-- ... -->
</AuditFile>
```

---

## 8. Segurança em Produção (Linux)

### 8.1 Checklist de Segurança

- [ ] Chaves privadas em volume encriptado LUKS
- [ ] Permissões restritivas (0400) em ficheiros de chaves
- [ ] Auditoria de acesso (auditctl) ativada
- [ ] Logs centralizados em syslog
- [ ] Processo de assinatura isolado (sudo + user dedicado)
- [ ] Rotação de chaves anual
- [ ] Backup encriptado fora do servidor
- [ ] SELinux ou AppArmor ativado
- [ ] Firewall restringindo acesso à API da AGT
- [ ] SSL/TLS para comunicação com AGT

### 8.2 Estrutura de Diretórios

```bash
/etc/ssl/agt/
├── private/                 (chmod 0700)
│   ├── keys/               (chmod 0700)
│   │   ├── key_v1.pem      (chmod 0400)
│   │   └── key_v2.pem      (chmod 0400)
│   ├── .keypass            (chmod 0400)
│   └── README              (chmod 0444)
├── public/                 (chmod 0755)
│   ├── certificates/       (chmod 0755)
│   │   ├── agt_cert_v1.pem
│   │   └── agt_cert_v2.pem
│   ├── ca_chain.pem
│   └── crls/
├── config/                 (chmod 0700)
│   └── key_config.json    (chmod 0600)
└── logs/ (chmod 0750)

/var/log/agt/
├── signature.log
├── key_v1_access.log
└── compliance.log
```

---

## 9. Testes e Validação

### 9.1 Testes Unitários

```bash
pytest tests/test_agt_validators.py -v
pytest tests/test_agt_immutability.py -v
pytest tests/test_agt_signature.py -v
pytest tests/test_agt_saft_generator.py -v
```

### 9.2 Teste de Conformidade

```python
# tests/test_agt_compliance.py

def test_nif_validation():
    """NIF deve cumprir formato e checksum"""
    valid_nif = "123-4567-8901"
    assert NIFValidator.validate_format(valid_nif)[0] == True

def test_invoice_immutability():
    """Fatura emitida não pode ser editada"""
    invoice = create_and_issue_invoice()
    assert invoice['is_editable'] == False
    
    # Tentar editar deve falhar
    with pytest.raises(ImmutabilityViolation):
        modify_invoice(invoice)

def test_saft_xml_generation():
    """SAF-T XML deve ser válido"""
    xml = generate_saft_xml([...])
    assert xml.startswith('<?xml')
    assert 'urn:OECD:StandardAuditFile-Tax:AO_1.05_01' in xml
```

---

## 10. Conformidade e Auditoria

### 10.1 Requisitos da AGT (2026)

- ✅ Faturação eletrónica com assinatura digital
- ✅ Numero de fatura sequencial (cronologia obrigatória)
- ✅ NIF cliente/fornecedor validado
- ✅ IVA com regime e código de isenção
- ✅ SAF-T XML completo
- ✅ Auditoria completa de operações
- ✅ Imutabilidade pós-emissão
- ✅ Submissão à AGT em tempo real (opcional 2026)

### 10.2 Logs de Auditoria

```json
{
  "log_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "INVOICE_ISSUED",
  "entity_type": "INVOICE",
  "entity_id": "invoice_001",
  "action": "ISSUE",
  "operator_id": "user_001",
  "operator_ip": "192.168.1.100",
  "data_before": {
    "status": "D",
    "is_issued": false
  },
  "data_after": {
    "status": "I",
    "is_issued": true,
    "invoice_number": "FT SEGUNDO2026/0001",
    "data_hash": "abc123..."
  },
  "is_compliant": true,
  "created_at": "2026-05-01T15:00:00Z"
}
```

---

## 11. Roadmap

### Fase 1 (Completo - Maio 2026)
- ✅ Modelos de BD com campos AGT
- ✅ Validadores (NIF, IVA, Fatura)
- ✅ Imutabilidade de faturas
- ✅ Assinatura JWS (RS256)
- ✅ Exportação SAF-T XML
- ✅ Segurança de chaves (Linux)

### Fase 2 (Q3 2026)
- [ ] Integração API da AGT (submissão em tempo real)
- [ ] Dashboard de conformidade
- [ ] Alertas de conformidade
- [ ] Relatórios regulatórios

### Fase 3 (Q4 2026)
- [ ] Mobile app para assinatura
- [ ] Integração com HSM (Hardware Security Module)
- [ ] Blockchain para auditoria (opcional)

---

## 12. Suporte e Contacto

**Autoridade Geral Tributária (AGT)**  
Website: https://www.agt.gov.ao  
Email: suporte@agt.gov.ao  
Telefone: +244 222 XXXXXX

---

**Documento de Implementação AGT**  
**Versão:** 1.0 | **Data:** Maio 2026  
**Confidencial - Acesso Restrito**
