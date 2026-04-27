# Instruções para Push do GitHub

O repositório Git foi preparado com sucesso localmente, mas há um bloqueio na autenticação do GitHub. Aqui estão as instruções para completar o push:

## Opção 1: Usar GitHub CLI (Recomendado - Mais Fácil)

```powershell
# 1. Instale GitHub CLI: https://cli.github.com/
# 2. Abra PowerShell como Administrador
# 3. Execute:
gh auth login
# Escolha: GitHub.com > HTTPS > Y > Y (browser auth)

# 4. Depois do login, execute o push:
cd "c:\Users\Guilherme Pedro\Documents\Bababebe"
git push -u origin main
```

## Opção 2: Personal Access Token (PAT)

```powershell
# 1. Gere um token em: https://github.com/settings/tokens/new
#    - Permissões necessárias: "repo" e "workflow"
#    - Copie o token gerado

# 2. Configure o Git com o token:
cd "c:\Users\Guilherme Pedro\Documents\Bababebe"
git config --global credential.helper manager
# Ou se usar PowerShell 7+:
# git config --global credential.helper wincred

# 3. Próxima tentativa de push pedirá username/password:
#    - Username: seu username GitHub
#    - Password: Cole o token PAT (não a senha real)
git push -u origin main
```

## Opção 3: Usar SSH

```powershell
# 1. Gere chave SSH (se não tiver):
ssh-keygen -t ed25519 -C "seu@email.com"
# (Pressione Enter 3x para aceitar defaults)

# 2. Adicione a chave pública ao GitHub:
#    - Copie: Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
#    - Vá a: https://github.com/settings/keys
#    - Clique "New SSH key" e cole

# 3. Configure o Git para usar SSH:
cd "c:\Users\Guilherme Pedro\Documents\Bababebe"
git remote set-url origin git@github.com:mbumbaguilherme3-cpu/Factura-oApp.git

# 4. Teste a conexão SSH:
ssh -T git@github.com

# 5. Faça o push:
git push -u origin main
```

## Status Atual do Repositório

- **Commits locais**: 1 commit (2631cad) com 46 ficheiros e 11.483 linhas
- **Branch**: main
- **Remote configurado**: https://github.com/mbumbaguilherme3-cpu/Factura-oApp.git
- **Ficheiros prontos**: Todos (app.py, billing_app/, tests/, docs/, database/, .github/, etc.)

## Verificação

Após fazer o push com sucesso, verifique em:
https://github.com/mbumbaguilherme3-cpu/Factura-oApp

Deve ver a lista completa de ficheiros e o commit com a mensagem:
"feat: Complete billing application with PostgreSQL/SQLite support..."
