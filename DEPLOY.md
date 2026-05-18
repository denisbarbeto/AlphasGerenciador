# DEPLOY.md — Alphas Gerenciador do Windows
## Guia para Desenvolvedores e Contribuidores

---

## 1. AMBIENTE DE DESENVOLVIMENTO

### Pré-requisitos

- Python 3.10 ou superior
- pip atualizado (`python -m pip install --upgrade pip`)
- Dependências do projeto:

```bash
pip install customtkinter psutil wmi pywin32
```

### Clonando o repositório

```bash
git clone https://github.com/AlphasConsultoria/AlphasGerenciador.git
cd AlphasGerenciador
```

### Rodando localmente

```bash
# Executar diretamente (modo desenvolvimento)
python app.py

# Ou com privilégios de administrador (necessário para algumas funções):
# clique com botão direito em Executar_como_Admin.bat → Executar como administrador
```

---

## 2. COMO CONTRIBUIR

> **A branch `main` é protegida.** Não é possível fazer push direto — todas as contribuições passam por Pull Request.

### Fluxo de contribuição (Fork → Branch → PR)

```bash
# 1. Faça um fork do repositório pelo GitHub (botão "Fork" no topo da página)

# 2. Clone o seu fork
git clone https://github.com/<seu-usuario>/AlphasGerenciador.git
cd AlphasGerenciador

# 3. Configure seu nome e email
git config user.name "Seu Nome"
git config user.email "seu@email.com"

# 4. Crie uma branch para sua contribuição
git checkout -b feature/nome-da-sua-funcionalidade
# ou
git checkout -b fix/nome-do-bug

# 5. Faça suas alterações e commite
git add .
git commit -m "feat: descrição clara da mudança"

# 6. Envie para o seu fork
git push origin feature/nome-da-sua-funcionalidade

# 7. Abra um Pull Request no GitHub apontando para a branch main deste repositório
```

### Regras para Pull Requests

- Descreva claramente o que foi alterado e por quê
- PRs sem descrição ou com código de baixa qualidade podem ser rejeitados
- Mantenha o escopo pequeno — um PR por funcionalidade/correção
- Respeite o padrão visual e de código existente no projeto

---

## 3. PADRÃO DE COMMITS

| Prefixo | Quando usar |
|---------|-------------|
| `feat:` | Nova funcionalidade |
| `fix:`  | Correção de bug |
| `chore:`| Atualização de versão, build |
| `docs:` | Documentação |
| `style:`| Visual, ícones, cores |

Exemplos:
```bash
git commit -m "feat: adiciona nova aba de monitoramento de CPU"
git commit -m "fix: corrige travamento ao limpar temp com arquivos em uso"
git commit -m "style: ajusta cores do tema na sidebar"
```

---

## 4. ESTRUTURA DO PROJETO

```
AlphasGerenciador/
│
├── app.py              → Janela principal + sidebar + lógica de navegação
├── backend.py          → Chamadas ao Windows (WMI, PowerShell)
├── updater.py          → Sistema de auto-update via GitHub Releases
├── installer.py        → Instalador com seleção de pasta
├── theme.py            → Cores e constantes visuais
├── widgets.py          → Componentes reutilizáveis (StatusBar, ConfirmDialog)
├── version.json        → Versão atual (atualizado a cada release)
├── build.bat           → Gera o EXE (Nuitka ou PyInstaller fallback)
├── Executar_como_Admin.bat
├── .gitignore
├── DEPLOY.md           → Este arquivo
│
└── modules/
    ├── __init__.py
    └── pages.py        → Todas as abas do painel
```

---

## 5. PUBLICANDO UMA NOVA VERSÃO (somente mantenedores)

### 5.1 Atualizar o version.json

```json
{
  "version": "1.1.0",
  "release_date": "AAAA-MM-DD",
  "changelog": "- Nova funcionalidade X\n- Correção no módulo Y",
  "download_url": "https://github.com/<usuario>/AlphasGerenciador/releases/latest/download/AlphasGerenciador.exe",
  "releases_api": "https://api.github.com/repos/<usuario>/AlphasGerenciador/releases/latest"
}
```

### 5.2 Gerar o EXE

```bash
build.bat
# O EXE será gerado em dist\AlphasGerenciador.exe
```

### 5.3 Commit + tag de versão

```bash
git add .
git commit -m "chore: release v1.1.0"

git tag -a v1.1.0 -m "Versão 1.1.0"
git push
git push --tags
```

### 5.4 Criar o Release no GitHub

1. Acesse a página do repositório no GitHub
2. Clique em **Releases** → **Create a new release**
3. Em **Choose a tag**, selecione `v1.1.0`
4. Preencha o título e descrição com o changelog
5. Anexe o arquivo `dist\AlphasGerenciador.exe`
6. Clique em **Publish release**

Após publicado, todos os usuários com o app instalado receberão a notificação de atualização automaticamente.

---

## 6. ARQUIVO .gitignore

O projeto já inclui um `.gitignore`. Caso precise recriar:

```gitignore
# Build
dist/
build/
*.manifest
__pycache__/
*.pyc
*.pyo

# Nuitka
*.build/
*.dist/
*.onefile-build/

# Python
.venv/
venv/
*.egg-info/

# Sistema
.DS_Store
Thumbs.db
desktop.ini

# IDE
.windsurf/
.vscode/settings.json
*.swp
```

---

## 7. ANTIVÍRUS — FALSO POSITIVO

### Por que acontece?

O Nuitka/PyInstaller empacota um interpretador Python dentro do EXE, o que alguns antivírus detectam como comportamento suspeito.

### Soluções

**Opção A — Exclusão manual (rápido):**
```
Windows Defender → Proteção → Exclusões → Adicionar pasta
→ selecione a pasta onde o AlphasGerenciador está instalado
```

**Opção B — Certificado Digital (definitivo):**
```
Comprar um Code Signing Certificate (~U$70/ano)
Fornecedores: DigiCert, Sectigo, GlobalSign

Assinar o EXE:
signtool sign /a /t http://timestamp.digicert.com AlphasGerenciador.exe
```

---

## 8. CONFIGURANDO A PROTEÇÃO DA BRANCH MAIN (mantenedores)

Para proteger a branch `main` e exigir PRs de todos os contribuidores:

1. Acesse **Settings → Branches** no repositório GitHub
2. Clique em **Add branch protection rule**
3. Em **Branch name pattern**: `main`
4. Marque:
   - [x] **Require a pull request before merging**
   - [x] **Require approvals** (mínimo 1)
   - [x] **Do not allow bypassing the above settings**
5. Clique em **Create**

Com isso, ninguém — nem o dono do repositório — pode fazer push direto na `main`.

---

## 9. COMANDOS GIT ÚTEIS

```bash
# Ver histórico de commits
git log --oneline

# Ver diferenças antes de commitar
git diff

# Desfazer alteração em um arquivo (sem commitar)
git checkout -- nome_do_arquivo.py

# Ver todas as versões/tags
git tag

# Baixar atualizações do repositório original (após fork)
git remote add upstream https://github.com/<usuario-original>/AlphasGerenciador.git
git fetch upstream
git merge upstream/main

# Ver branches
git branch -a

# Criar branch para nova feature
git checkout -b feature/nova-funcionalidade

# Voltar para a main
git checkout main
```
