# PAGAFARRA

Projeto base em Django executado com Docker.

---

## 📋 Pré-requisitos

Antes de começar, instale o **Docker** e o **Docker Compose** no seu sistema:

### Windows
1. Baixe o [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
2. Execute o instalador e siga as instruções.
3. Certifique-se de que a virtualização (WSL 2 ou Hyper-V) esteja habilitada.
4. Após a instalação, reinicie a máquina se necessário.
5. Abra o **PowerShell** ou **Prompt de Comando** e verifique:
   ```bash
   docker --version
   docker compose version
   ```

### Linux
1. Atualize o gerenciador de pacotes e instale o Docker:
   ```bash
   sudo apt update
   sudo apt install docker.io docker-compose-plugin
   ```
2. Inicie o serviço do Docker (e habilite para iniciar junto com o sistema):
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker
   ```
3. (Opcional) Adicione seu usuário ao grupo `docker` para não usar `sudo`:
   ```bash
   sudo usermod -aG docker $USER
   ```
   Faça logout e login novamente para aplicar.
4. Verifique a instalação:
   ```bash
   docker --version
   docker compose version
   ```

### macOS
1. Baixe o [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).
2. Arraste o Docker.app para a pasta **Aplicativos**.
3. Abra o Docker Desktop e aguarde o motor do Docker iniciar.
4. Abra o **Terminal** e verifique:
   ```bash
   docker --version
   docker compose version
   ```

---

## 🚀 Como Executar

### 1. Iniciar a aplicação
Construa as imagens e inicie os containers em segundo plano:
```bash
docker compose up -d --build
```

Acesse a aplicação no navegador em: **http://localhost:8000**

### 2. Parar a aplicação
Para encerrar os containers em execução:
```bash
docker compose down
```

---

## ⚙️ Comandos Úteis do Django

Execute os comandos diretamente no container `web`:

| Comando | Descrição |
|---|---|
| `docker compose exec web python manage.py migrate` | Executar migrations |
| `docker compose exec web python manage.py createsuperuser` | Criar superusuário |
| `docker compose exec web python manage.py shell` | Abrir o Django Shell |

---

## 📁 Estrutura de Diretórios

```
.
├── config/              # Configurações principais do Django (settings, urls, wsgi)
├── db.sqlite3           # Banco de dados SQLite local
├── Dockerfile           # Instruções de build da imagem da aplicação
├── docker-compose.yml   # Definição e orquestração dos containers
├── manage.py            # Script utilitário de gerenciamento do Django
└── requirements.txt     # Dependências Python do projeto
```

---

## 🔒 Regras de Git

| Tipo | Descrição |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `refactor` | Melhorar/reorganizar código |
| `perf` | Melhorar performance |
| `docs` | Documentação |
| `test` | Testes |
| `style` | Formatação/estilo |
| `build` | Dependências/build |
| `ci` | CI/CD |
| `chore` | Manutenção geral |
| `revert` | Desfazer commit |
