<<<<<<< HEAD
# Sistema de Faturacao da Loja

Aplicacao web de faturacao para loja, feita em Python com SQLite, focada em operacao real e integridade de dados.

## O que ja existe

- autenticacao com utilizadores, senha e sessoes
- papeis e permissoes basicas
- clientes
- categorias
- produtos
- fornecedores
- entradas de estoque
- ajustes manuais de estoque
- faturas e itens
- pagamentos
- caixa com abertura, movimentos e fecho
- relatorios e exportacao CSV
- auditoria de accoes
- backups locais
- rotina de restauro local
- edicao basica de clientes, produtos e cabecalho da fatura
- impressao de faturas
- troca de senha do utilizador autenticado
- migracoes/versionamento do banco

## Estrutura principal

- [app.py](c:\Users\Guilherme Pedro\Documents\Bababebe\app.py): arranque da aplicacao
- [billing_app/database.py](c:\Users\Guilherme Pedro\Documents\Bababebe\billing_app\database.py): conexao e migracoes
- [billing_app/web.py](c:\Users\Guilherme Pedro\Documents\Bababebe\billing_app\web.py): rotas web
- [billing_app/services.py](c:\Users\Guilherme Pedro\Documents\Bababebe\billing_app\services.py): faturacao e vendas
- [billing_app/operations.py](c:\Users\Guilherme Pedro\Documents\Bababebe\billing_app\operations.py): estoque, fornecedores e caixa
- [billing_app/admin.py](c:\Users\Guilherme Pedro\Documents\Bababebe\billing_app\admin.py): utilizadores, sessoes e auditoria
- [billing_app/maintenance.py](c:\Users\Guilherme Pedro\Documents\Bababebe\billing_app\maintenance.py): backup e restauro local
- [database/migrations/001_initial_core.sql](c:\Users\Guilherme Pedro\Documents\Bababebe\database\migrations\001_initial_core.sql): base inicial
- [database/migrations/002_security_and_operations.sql](c:\Users\Guilherme Pedro\Documents\Bababebe\database\migrations\002_security_and_operations.sql): seguranca e operacao
- [database/migrations/003_stock_entry_fk.sql](c:\Users\Guilherme Pedro\Documents\Bababebe\database\migrations\003_stock_entry_fk.sql): reforco de integridade no estoque
- [database/schema_sqlite.sql](c:\Users\Guilherme Pedro\Documents\Bababebe\database\schema_sqlite.sql): snapshot atual do schema

## Como executar

1. Abra a pasta do projeto.
2. Execute:

```powershell
python app.py
```

3. Abra no navegador:

```text
http://127.0.0.1:8000
```

## Credenciais iniciais

- utilizador: `admin`
- senha: `admin123`

Altere essa senha criando novos utilizadores administrativos assim que iniciar o sistema.

## Testes

```powershell
python -m unittest discover -s tests -q
```

## Observacao importante

O sistema ja tem base tecnica para operacao, mas as regras fiscais especificas do pais, da autoridade tributaria e do tipo de negocio ainda precisam de validacao juridico-fiscal antes de chamar isto de compliance legal completo.
=======
# Factura-oApp
>>>>>>> 5f4ddb3183ae1586956adda435c1d8cd7d9a7968
