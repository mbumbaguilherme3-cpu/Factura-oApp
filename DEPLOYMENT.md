# Guia de Deployment - Sistema AGT de Faturação

## 1. Configuração Inicial

### Pré-requisitos
- Docker 20.10+
- Docker Compose 2.0+
- Git
- Python 3.11+ (para desenvolvimento local sem Docker)

### Setup Rápido com Docker

1. **Clone o repositório:**
```bash
git clone https://github.com/seu-usuario/billing-agt.git
cd billing-agt
```

2. **Copie o arquivo de ambiente:**
```bash
cp .env.example .env
```

3. **Edite as variáveis de ambiente (se necessário):**
```bash
# No Windows
notepad .env

# No Linux/Mac
nano .env
```

4. **Inicie os serviços:**
```bash
docker-compose up -d
```

5. **Verifique o status:**
```bash
docker-compose ps
docker-compose logs -f flask-app
```

6. **Acesse a aplicação:**
- Dashboard: http://localhost:5000/dashboard/
- API: http://localhost:5000/api/health
- PostgreSQL: localhost:5432 (usuário: billing)

---

## 2. Executar Testes

### Com Docker
```bash
docker-compose exec flask-app pytest tests/ -v --cov=billing_app
```

### Sem Docker (setup local)
```bash
# Configure o ambiente Python
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Execute os testes
pytest tests/ -v --cov=billing_app
```

---

## 3. Migrações de Banco de Dados

### Aplicar todas as migrações
```bash
docker-compose exec flask-app alembic upgrade head
```

### Ver status das migrações
```bash
docker-compose exec flask-app alembic current
```

### Criar nova migração (automática)
```bash
docker-compose exec flask-app alembic revision --autogenerate -m "descrição da mudança"
```

### Reverter última migração
```bash
docker-compose exec flask-app alembic downgrade -1
```

---

## 4. Operações Comuns

### Ver logs
```bash
# Todos os serviços
docker-compose logs -f

# Apenas Flask app
docker-compose logs -f flask-app

# Apenas PostgreSQL
docker-compose logs -f db
```

### Parar os serviços
```bash
docker-compose down
```

### Parar e limpar volumes
```bash
docker-compose down -v
```

### Acessar o shell do container
```bash
docker-compose exec flask-app /bin/bash
```

### Acessar o banco de dados PostgreSQL
```bash
docker-compose exec db psql -U billing -d billing_agt
```

---

## 5. Desenvolvimento Local

### Setup sem Docker

1. **Crie um ambiente virtual:**
```bash
python -m venv venv
source venv/bin/activate  # ou: venv\Scripts\activate (Windows)
```

2. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

3. **Configure as variáveis de ambiente:**
```bash
cp .env.example .env
```

4. **Inicie o servidor de desenvolvimento:**
```bash
export FLASK_ENV=development
export FLASK_APP=app.py
flask run
```

5. **Execute os testes:**
```bash
pytest tests/ -v --cov
```

---

## 6. Configuração de Produção

### Variáveis de Ambiente Críticas

```bash
# NUNCA usar os valores padrão em produção!
export FLASK_ENV=production
export DEBUG=False
export SECRET_KEY=$(openssl rand -hex 32)
export DATABASE_URL=postgresql://billing:SENHA_FORTE@db-prod:5432/billing_agt
export POSTGRES_PASSWORD=SENHA_FORTE_AQUI
```

### Iniciar em Produção

```bash
# Parar modo desenvolvimento
docker-compose down

# Editar .env com valores de produção
nano .env

# Iniciar com compose de produção
docker-compose -f docker-compose.yml up -d
```

### Health Check
```bash
curl http://localhost:5000/api/health
```

---

## 7. Estrutura da API

### Endpoints Principais

#### Invoices (Faturas)
- `POST /api/invoices` - Criar fatura
- `GET /api/invoices` - Listar faturas (com paginação)
- `GET /api/invoices/{id}` - Obter detalhes da fatura
- `POST /api/invoices/{id}/issue` - Emitir fatura
- `POST /api/invoices/{id}/sign` - Assinar fatura (JWS)
- `POST /api/invoices/{id}/submit` - Submeter à AGT

#### Notas de Crédito/Débito
- `POST /api/invoices/{id}/credit-note` - Criar nota de crédito
- `POST /api/invoices/{id}/debit-note` - Criar nota de débito

#### Exportação
- `GET /api/invoices/saft/export` - Exportar SAF-T XML

#### Sistema
- `GET /api/health` - Health check da API

### Exemplo: Criar Fatura

```bash
curl -X POST http://localhost:5000/api/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust-123",
    "supplier_id": "supp-456",
    "lines": [
      {
        "product_id": "prod-789",
        "quantity": 10,
        "unit_price": 100.00,
        "iva_regime": "GENERAL"
      }
    ]
  }'
```

---

## 8. Monitoramento e Troubleshooting

### Verificar Saúde dos Serviços

```bash
# Flask App
curl http://localhost:5000/api/health

# PostgreSQL
docker-compose exec db pg_isready -U billing

# Redis
docker-compose exec redis redis-cli ping
```

### Problemas Comuns

#### Erro: "Port 5000 already in use"
```bash
# Kill processo na porta 5000
lsof -ti:5000 | xargs kill -9  # Linux/Mac
netstat -ano | findstr :5000   # Windows (encontre PID e execute: taskkill /PID <PID>)
```

#### Erro: "Database connection refused"
```bash
# Verifique se o DB está rodando
docker-compose ps db

# Verifique os logs
docker-compose logs db

# Reinicie o banco
docker-compose restart db
```

#### Erro: "Alembic migration failed"
```bash
# Verifique o status
docker-compose exec flask-app alembic current

# Veja qual migração falhou
docker-compose logs flask-app | grep -i alembic
```

---

## 9. Backup e Restauração

### Backup do Banco de Dados

```bash
# Criar backup
docker-compose exec db pg_dump -U billing -d billing_agt > backup.sql

# Restaurar backup
docker-compose exec -T db psql -U billing -d billing_agt < backup.sql
```

### Backup de Volumes

```bash
docker run --rm -v billing_agt_postgres_data:/data \
  -v $(pwd):/backup ubuntu tar czf /backup/db_backup.tar.gz /data
```

---

## 10. Deployment em Produção (Recomendações)

### Usar Docker Swarm ou Kubernetes

Para aplicações em produção de alta disponibilidade, recomendamos:

1. **Docker Swarm:**
```bash
docker stack deploy -c docker-compose.yml billing_agt
```

2. **Kubernetes:**
- Criar manifestos YAML (Deployment, Service, PersistentVolume)
- Usar Helm charts para configuração

### Reverse Proxy (nginx)

```nginx
upstream flask_app {
    server localhost:5000;
}

server {
    listen 80;
    server_name faturacao.example.com;

    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### SSL/TLS

```bash
# Com Let's Encrypt (Certbot)
certbot certonly --standalone -d faturacao.example.com
```

### Autoscaling

Configure limite de recursos em produção:

```yaml
services:
  flask-app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '1'
          memory: 512M
```

---

## 11. Métricas e Logging

### Acessar Logs

```bash
# Formato JSON para análise
docker-compose logs --no-color flask-app | tail -100

# Com timestamps
docker-compose logs --timestamps -f
```

### Health Check Dashboard

Visitar: http://localhost:5000/dashboard/

KPIs disponíveis:
- Faturas este mês
- Total faturado
- % Conformidade
- Faturas emitidas
- Pendentes AGT

---

## 12. Atualizar a Aplicação

1. **Pull latest changes:**
```bash
git pull origin main
```

2. **Rebuild container:**
```bash
docker-compose build --no-cache
```

3. **Restart services:**
```bash
docker-compose up -d
```

4. **Run migrations:**
```bash
docker-compose exec flask-app alembic upgrade head
```

---

## Suporte e Documentação

- Documentação da API: [API.md](./API.md)
- Guia de Segurança: [SECURITY.md](./SECURITY.md)
- Arquitetura AGT: [docs/AGT_COMPLIANCE.md](./docs/AGT_COMPLIANCE.md)
