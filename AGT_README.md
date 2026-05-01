# AGT Conformidade Fiscal Angolana - Sistema Completo

## 🇦🇴 Visão Geral

Sistema completo de conformidade fiscal para Angola, implementando os requisitos da **Autoridade Geral Tributária (AGT)** e do padrão **SAF-T (AO) 1.05_01**.

**Status:** ✅ Implementação Completa (Maio 2026)  
**Versão:** 1.0  
**Compatibilidade:** Python 3.8+, PostgreSQL/SQLite

---

## 📦 Componentes Criados

### 1. **Modelos de Base de Dados** (`agt_models.py`)
Tabelas AGT-conformes com campos obrigatórios:

```python
✓ AnyEntity          - Clientes/Fornecedores com NIF validado
✓ AGTProduct         - Produtos/Serviços com configuração de IVA
✓ Invoice            - Faturas com hash de integridade & assinatura JWS
✓ InvoiceLine        - Linhas com regime IVA e código de isenção
✓ InvoiceSignatureAudit - Auditoria de assinatura digital
✓ AGTComplianceLog   - Log regulatório de operações
✓ AGTCertificateKey  - Gestão de chaves e certificados
```

**Campos Obrigatórios para AGT:**
- NIF (Número de Identificação Fiscal) com formato e checksum validado
- Regime de IVA (Geral 14%, Isento, Simplificado, Não Sujeito)
- Código de Isenção (M01-M09) quando IVA = 0%
- Hash SHA256 para integridade pós-emissão
- Assinatura JWS para autenticação
- Números de série com cronologia obrigatória

### 2. **Validadores AGT** (`agt_validators.py`)
Regras de validação completas:

```python
NIFValidator           # Validação de NIF angolano (checksum)
IVAValidator          # Validação de regimes e códigos de isenção
InvoiceValidator      # Validação de números, totais e sequência
ComplianceRuleEngine  # Regras de negócio (imutabilidade, cronologia)
```

**Validações Implementadas:**
- ✅ NIF: Formato XXXXXXXXXXXXX com checksum (Luhn-like)
- ✅ IVA: Regime obrigatório, taxa válida, código de isenção quando necessário
- ✅ Número: Série + Sequência + Ano (FT SEGUNDO2026/0001)
- ✅ Totais: Gross = Σ linhas, IVA = Σ iva, Net = Gross - IVA
- ✅ Cronologia: Faturas em ordem temporal (AGT requirement)

### 3. **Motor de Imutabilidade** (`agt_immutability.py`)
Garante que faturas emitidas não podem ser modificadas:

```python
InvoiceImmutabilityEngine      # Cálculo de hash e lock
InvoiceCorrectionStrategy      # Criar NC/ND para correções
InvoiceStateTransition         # Máquina de estados
```

**Fluxo de Ciclo de Vida:**
```
DRAFT (editável) 
  ↓ issue()
ISSUED (bloqueado para edit, pode assinar)
  ↓ sign()
SIGNED (assinado, pode submeter)
  ↓ submit()
SUBMITTED (na AGT)
  ↓
ACKNOWLEDGED (confirmado)
```

**Proteções:**
- Fatura emitida: `is_editable = False`
- Hash SHA256 calculado antes de bloquear
- Tentativas de edit são bloqueadas
- Correções apenas via Notas de Crédito/Débito

### 4. **Assinatura Digital JWS** (`agt_signature.py`)
Implementa RFC 7515 (JSON Web Signature):

```python
JWSSignatureEngine     # Assinar com RS256 ou RS512
SignatureAuditTrail   # Auditoria de operações de assinatura
```

**Recursos:**
- ✅ Algoritmos: RS256 (RSA 2048-bit + SHA-256) ou RS512
- ✅ Certificados X.509 com versionamento
- ✅ Payload com: invoice_number, hash, timestamp, operator_id
- ✅ Auditoria completa de operações
- ✅ Verificação de assinatura

**Formato JWS:**
```
BASE64(header).BASE64(payload).BASE64(signature)
```

### 5. **Exportação SAF-T (AO)** (`agt_saft_generator.py`)
Gera XML conforme especificação AGT 1.05_01:

```python
SAFTAOGenerator      # Gera XML SAF-T (AO)
SAFTAOValidator      # Valida estrutura XML
```

**Secções Incluídas:**
- Header (metadados de auditoria)
- MasterFiles (Clientes, Produtos)
- SourceDocuments (Vendas, Notas de Crédito, Notas de Débito)

**Estrutura Completa:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:AO_1.05_01">
  <Header>
    <AuditFileVersion>1.05_01</AuditFileVersion>
    <AuditFileCountry>AO</AuditFileCountry>
    <Company>
      <RegistrationNumber>...</RegistrationNumber>
      <!-- ... -->
    </Company>
  </Header>
  <MasterFiles>
    <Customers>...</Customers>
    <Products>...</Products>
  </MasterFiles>
  <SourceDocuments>
    <SalesInvoices>...</SalesInvoices>
  </SourceDocuments>
</AuditFile>
```

### 6. **Segurança em Linux** (`AGT_SECURITY.md`)
Guia completo para proteger chaves privadas:

**Implementações:**
- ✅ Estrutura de diretórios com permissões restritivas (0400/0700)
- ✅ Encriptação LUKS para volume de chaves
- ✅ Proteção com AES-256 para chaves privadas
- ✅ Acesso isolado via sudo (user dedicado: `billing-app`)
- ✅ Script seguro de assinatura (/usr/local/bin/agt_sign_invoice.py)
- ✅ Auditoria de acesso com auditctl
- ✅ Backup encriptado de chaves
- ✅ Rotação automática (anual)

**Estrutura:**
```bash
/etc/ssl/agt/
├── private/keys/          # Chaves (encriptadas)
├── public/certificates/   # Certificados (públicos)
├── config/                # Configuração (restrita)
└── logs/                  # Auditoria
```

### 7. **Exemplos Práticos** (`example_agt_compliance.py`)
Demonstra completo workflow:

```python
✓ Exemplo 1: Criação com validação AGT
✓ Exemplo 2: Emissão e bloqueio de imutabilidade
✓ Exemplo 3: Correção via Notas de Crédito/Débito
✓ Exemplo 4: Geração SAF-T XML
✓ Exemplo 5: Assinatura digital JWS
```

### 8. **Documentação Completa**
- `AGT_IMPLEMENTATION_GUIDE.md` - Guia de implementação (350+ linhas)
- `AGT_SECURITY.md` - Segurança e cibersegurança (280+ linhas)

---

## 🚀 Quick Start

### Instalação

```bash
# 1. Instalar dependências
pip install cryptography

# 2. Configurar base de dados
python -m billing_app.agt_models  # Criar tabelas

# 3. Gerar chaves (em produção, fazer uma única vez)
openssl genrsa -out /etc/ssl/agt/private/keys/key_v1.pem 2048

# 4. Executar exemplos
python example_agt_compliance.py
```

### Uso Básico

```python
from billing_app.agt_validators import NIFValidator, IVAValidator
from billing_app.agt_immutability import InvoiceImmutabilityEngine
from billing_app.agt_signature import JWSSignatureEngine
from billing_app.agt_saft_generator import SAFTAOGenerator

# 1. Validar NIF
is_valid, error = NIFValidator.validate_format("123-4567-8901")

# 2. Validar IVA
is_valid, error = IVAValidator.validate_iva_rate(
    rate=Decimal('14.00'),
    regime='GENERAL'
)

# 3. Criar e emitir fatura
invoice = create_invoice(...)
hash_value, locked = InvoiceImmutabilityEngine.lock_invoice(invoice, 'operator_1')

# 4. Assinar
engine = JWSSignatureEngine()
engine.load_keys('/etc/ssl/agt/private/keys/key_v1.pem')
jws, error = engine.sign_invoice(invoice, 'operator_1', '192.168.1.1')

# 5. Exportar SAF-T
generator = SAFTAOGenerator(company_data)
xml = generator.generate(customers, products, invoices)
```

---

## 📋 Checklist de Conformidade AGT (2026)

- ✅ **NIF Validado**: Formato XXXXXXXXXXXXX com checksum
- ✅ **Regime de IVA**: Geral (14%), Isento, Simplificado, etc.
- ✅ **Código de Isenção**: M01-M09 quando IVA = 0%
- ✅ **Número de Série**: FT SEGUNDO2026/001 (sequencial + cronologia)
- ✅ **Imutabilidade**: Hash + Lock após emissão
- ✅ **Assinatura Digital**: JWS com RS256
- ✅ **Auditoria Completa**: Todos eventos registados
- ✅ **SAF-T XML**: Conforme especificação OECD AO 1.05_01
- ✅ **Segurança**: Chaves protegidas em Linux

---

## 🔐 Segurança (Produção)

### Proteção de Chaves Privadas

```bash
# Encriptação LUKS para volume de chaves
fallocate -l 100M /var/lib/agt_keys.img
cryptsetup luksFormat /var/lib/agt_keys.img
cryptsetup luksOpen /var/lib/agt_keys.img agt_keys
mount /dev/mapper/agt_keys /mnt/agt_secure

# Permissões restritivas
chmod 0400 /etc/ssl/agt/private/keys/key_v1.pem
chown root:billing-app /etc/ssl/agt/private/keys/
```

### Isolamento de Assinatura

```bash
# Processo isolado via sudo
www-data -> sudo -> billing-app -> /usr/local/bin/agt_sign_invoice.py
                                          ↓
                                    Load key (/etc/ssl/agt/)
                                    Sign with RS256
                                    Return JWS
```

### Auditoria

```bash
# Monitorar acesso a chaves
auditctl -w /etc/ssl/agt/private/keys -p wa -k agt_key_access

# Logs centralizados
/var/log/agt/signature.log
/var/log/agt/key_access.log
/var/log/agt/compliance.log
```

---

## 📊 Modelo de Dados

```
┌─────────────────┐         ┌──────────────────┐
│   AnyEntity     │         │   AGTProduct     │
│  (Cliente/Forn) │         │  (Produto/Serv)  │
├─────────────────┤         ├──────────────────┤
│ entity_id (PK)  │         │ product_id (PK)  │
│ nif (UNIQUE)    │◄────┐   │ iva_regime       │
│ nif_type        │     │   │ iva_rate         │
│ name            │     │   │ iva_exemption    │
└─────────────────┘     │   └──────────────────┘
                        │            ▲
                        │            │
                        │    ┌───────┘
                        │    │
                   ┌────┴────▼────────┐
                   │     Invoice      │
                   ├──────────────────┤
                   │ invoice_id (PK)  │
                   │ invoice_number   │
                   │ supplier_id (FK) │
                   │ customer_id (FK) │
                   │ data_hash        │
                   │ is_editable      │
                   │ signature_jws    │
                   └────────┬─────────┘
                            │
                   ┌────────┴──────────┐
                   │  InvoiceLine     │
                   ├──────────────────┤
                   │ invoice_id (FK)  │
                   │ product_id (FK)  │
                   │ iva_amount       │
                   └──────────────────┘
```

---

## 🧪 Testes

```bash
# Executar suite de testes
pytest tests/test_agt_*.py -v

# Cobertura
pytest --cov=billing_app tests/ --cov-report=html
```

---

## 📚 Documentação

| Documento | Conteúdo |
|-----------|----------|
| `AGT_IMPLEMENTATION_GUIDE.md` | Guia completo de implementação (arquitetura, fluxos, APIs) |
| `AGT_SECURITY.md` | Segurança em Linux, gestão de chaves, auditoria |
| `example_agt_compliance.py` | 5 exemplos práticos de workflow completo |
| `agt_models.py` | Esquema de BD (16 tabelas, 100+ campos) |
| `agt_validators.py` | Validadores (NIF, IVA, Invoice, Compliance) |
| `agt_immutability.py` | Motor de imutabilidade e estado |
| `agt_signature.py` | Assinatura JWS (RS256/RS512) |
| `agt_saft_generator.py` | Exportação SAF-T XML (OECD) |

---

## 🌍 Conformidade AGT/OECD

- ✅ **Autoridade Geral Tributária (AGT)** - Angola
- ✅ **SAF-T (AO) v1.05_01** - Standard Audit File - Tax
- ✅ **OECD** - Standard specification
- ✅ **Faturação Eletrônica 2026** - Requisitos vigentes

---

## 🎯 Características Principais

| Funcionalidade | Status | Nota |
|---|---|---|
| Validação de NIF | ✅ | Checksum completo |
| Regimes de IVA | ✅ | 5 regimes + códigos isenção |
| Imutabilidade | ✅ | Hash SHA256 + lock |
| Números Sequenciais | ✅ | Cronologia obrigatória |
| Assinatura JWS | ✅ | RS256 + auditoria |
| SAF-T XML | ✅ | OECD 1.05_01 |
| Notas de Crédito/Débito | ✅ | Para correções |
| Auditoria Completa | ✅ | Todos eventos |
| Segurança Linux | ✅ | Chaves encriptadas |
| Backups Encriptados | ✅ | Retenção 7 anos |

---

## 📞 Suporte

**AGT (Autoridade Geral Tributária)**
- Website: https://www.agt.gov.ao
- Email: suporte@agt.gov.ao
- Documentação SAF-T: https://www.agt.gov.ao/portal/saft

**Desenvolvedor**
- GitHub: [seu-repo]
- Issues: [seu-repo/issues]

---

## 📝 Licença

Sistema de Conformidade Fiscal AGT - Angola  
Desenvolvido para Autoridade Geral Tributária  
2026

---

**Versão:** 1.0 | **Status:** ✅ Completo | **Data:** Maio 2026  
**Confidencial - Acesso Restrito**
