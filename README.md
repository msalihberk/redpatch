<div align="center">

<img src="assets/banner.webp" alt="RedPatch" width="100%">

<br><br>

# RedPatch

**Interactive Application Security Playground & Defense Simulator**

Exploit vulnerable applications. Patch the source. Verify the fix.

All through one isolated, containerized security workflow.

<br>

[![Docker](https://img.shields.io/badge/DOCKER-READY-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/msalihberk/redpatch)
[![Labs](https://img.shields.io/badge/LABS-EXPLORE-111827?style=for-the-badge&logo=github&logoColor=white)](https://github.com/msalihberk/redpatch-labs)
[![License](https://img.shields.io/badge/AGPL--3.0-LICENSE-2ea44f?style=for-the-badge)](https://github.com/msalihberk/redpatch/blob/main/LICENSE)

<br><br>

<a href="#-how-redpatch-works">How it works</a> · <a href="#️-architecture">Architecture</a> · <a href="#-labs">Labs</a> · <a href="#-quick-start">Quick Start</a>

</div>

---

<div align="center">

### One vulnerability. Two perspectives. One complete security workflow.

<br>

**🕵️ EXPLOIT**   →   **💻 PATCH**   →   **🤖 VERIFY**

</div>

#### Description
RedPatch is an interactive, containerized application security playground and defense simulator designed to bridge the gap between offensive penetration testing and defensive secure code remediation. Built with a lightweight FastAPI orchestration engine, RedPatch goes beyond traditional vulnerability discovery by guiding users through a complete three-step security lifecycle: Exploit, Patch, and Verify.

Users begin in Pentester Mode, analyzing attack surfaces and exploiting flaws such as SQL Injection or IDOR to capture flags. They then transition to Coder Mode, gaining direct real-time access to the application's source code within an isolated workspace to write and apply root-cause security fixes. Finally, an AI Security Layer—built on an extensible provider abstraction—evaluates the applied patch to verify whether the vulnerability has been completely resolved. By decoupling the host orchestration engine from external laboratory definitions through a declarative manifest system (manifest.json), RedPatch provides a modular, lightweight, and scalable environment for practical cybersecurity education.

#### Video Demo: [Youtube](https://youtu.be/HssfXp6wzpI)

---

## ⚡ What makes RedPatch different?

Most security training environments teach you to **find** a vulnerability.

RedPatch makes you go one step further:

> **Exploit it → understand it → fix it → verify the fix.**

The platform combines offensive security practice with defensive code remediation inside disposable Docker-based environments.

No separate tools.
No disconnected exercises.
One continuous workflow.

---

## 🎯 How RedPatch Works

### Pentester Mode

Interact with an intentionally vulnerable application and investigate its attack surface.
**Find the vulnerability. Exploit the application. Capture the flag.**

<p align="center">
  <video src="https://github.com/user-attachments/assets/ff3e75a8-31f7-4efb-ad6f-fab2d8b44396" width="100%" autoplay loop muted playsinline></video>
</p>

<br>

### Coder Mode

The vulnerable application's source becomes available through the built-in workspace, allowing you to inspect and patch the underlying code.
**Inspect the vulnerable code. Patch it. Verify the remediation.**

<p align="center">
  <video src="https://github.com/user-attachments/assets/bab6065d-615d-465d-b56f-27bfd381b837" width="100%" autoplay loop muted playsinline></video>
</p>



```text
┌─────────────────────────────────────────────────────────────────┐
│                           REDPATCH                              │
│                                                                 │
│     PENTESTER              CODER              AI AGENT          │
│   ─────────────          ─────────           ──────────         │
│   Find the flaw    →     Patch it      →     Verify it          │
│   Exploit the app        Modify code         Analyze fix        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 🤖 AI Verification

Submit your remediation to the configured security analysis agent in coder mode.

The agent evaluates the patch and provides feedback on whether the vulnerability has actually been addressed.

---

# 🏗️ Architecture

RedPatch is built as a lightweight **host orchestration engine** rather than a collection of hardcoded labs.

```mermaid
flowchart LR

    USER[👤 User]

    UI[Web Interface]
    ENGINE[FastAPI Host Engine]

    MANAGER[Lab Manager]
    DOCKER[Docker Service]
    PROXY[Async HTTP Proxy]
    AI[AI Service]

    MANIFEST[Lab Manifest]
    CONTAINERS[Isolated Lab Containers]
    PROVIDER[LLM Provider]

    USER --> UI
    UI --> ENGINE

    ENGINE --> MANAGER
    ENGINE --> DOCKER
    ENGINE --> PROXY
    ENGINE --> AI

    MANAGER --> MANIFEST
    DOCKER --> CONTAINERS
    AI --> PROVIDER
    PROXY --> CONTAINERS
```

### Host Engine

`app/main.py` is the central application entry point.

It coordinates the web interface, lab lifecycle, workspace operations and request routing.

### Lab Manager

`app/services/module_manager/lab_manager.py` handles the lab catalog and manifest.

The engine does not contain the implementation of every vulnerability lab.

Instead, it consumes metadata describing available laboratories.

### Container Service

`app/services/container_services/` isolates Docker-specific lifecycle operations from the rest of the application.

### AI Service

`app/services/ai/` provides the AI analysis layer and separates provider-specific logic from the host engine.

---

# 🧩 Labs

**The labs are maintained separately from the RedPatch engine.**

This repository contains the **platform and orchestration layer**.

The actual vulnerable applications and laboratory implementations live in:

<a href="https://github.com/msalihberk/redpatch-labs">
    <img src="https://img.shields.io/badge/→%20EXPLORE%20REDPATCH%20LABS-111827?style=for-the-badge&logo=github&logoColor=white" alt="Explore RedPatch Labs">
</a>


The host engine discovers available laboratories through `app/labs/manifest.json`.

A simplified entry looks like:

```json
{
  "labs": {
    "SQLi": {
      "description": "SQL Injection",
      "submodules": [
        {
          "id": "sqli-0",
          "title": "SQL Injection - Authentication Bypass",
          "category": "web",
          "image_tag": "redpatch-lab/sqli-0:v1.0.0",
          "port": 5000,
          "dev_path": "./labs/sqli-0",
          "download_url": "..."
        }
      ]
    }
  }
}
```

The manifest acts as the bridge between the **RedPatch engine** and the externally maintained **RedPatch Labs** ecosystem.

### Why separate the labs?

This separation keeps the platform modular:

```text
redpatch
│
└── Host / Orchestration
        │
        └── manifest.json
                 │
                 ▼
          redpatch-labs
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
      SQLi     IDOR     Command Injection
```

The engine manages **how labs run**.

The labs repository defines **what the labs are**.

---

# 🔐 Containerized Execution

When a laboratory starts, RedPatch handles the runtime lifecycle through Docker.

```text
Manifest
   │
   ▼
Lab Selection
   │
   ▼
Container Creation
   │
   ▼
Workspace Preparation
   │
   ▼
Interactive Session
   │
   ▼
Teardown
```

This gives each active laboratory its own containerized runtime while keeping the orchestration logic inside the host engine.

> RedPatch is an educational security playground. Its isolation model should not be treated as a hardened production sandbox for arbitrary hostile workloads.

---

# 🤖 AI Security Layer

The AI service is intentionally separated behind a provider abstraction.

```text
                 AI Agent
                    │
                    ▼
             Provider Interface
                    │
                    ▼
             Gemini Provider
```

This means the rest of RedPatch does not need to depend directly on provider-specific API implementations.

The current configuration primarily supports Google Gemini.

### ⚙️ Managing Configuration

You can manage your AI credentials and platform settings through two methods:

#### 1. Web UI Control Panel (Recommended)
Launch the application and click the **Settings** icon in the navbar to open the in-app management panel. This allows you to update your settings dynamically without restarting the server:
* **LLM Provider** (e.g., `gemini`)
* **API Key**
* **Model Selection** (e.g., `gemini-flash-lite-latest`)

#### 2. Local Configuration File
Alternatively, you can edit `app/core/config.json` directly:

```json
{
  "API_KEY": "your_gemini_api_key_here",
  "LLM_PROVIDER": "gemini",
  "MODEL": "gemini-flash-lite-latest"
}
```

Or specify a custom configuration file path using environment variables:

```env
CONFIG_JSON=app/core/config.json
```

---

# ⚡ Quick Start

### Docker

```bash
docker network create redpatch_net
docker volume create redpatch_lab_tmp

# Linux / macOS
docker run -d \
  --name redpatch-app \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v redpatch_lab_tmp:/app/labs/archives \
  --network redpatch_net \
  msalihberk/redpatch:latest
  
# Windows
docker run -d `
  --name redpatch-app `
  -p 8000:8000 `
  -v //./pipe/docker_engine:/var/run/docker.sock `
  -v redpatch_lab_tmp:/app/labs/archives `
  --network redpatch_net `
  msalihberk/redpatch:latest
```

### Docker Compose

```bash
git clone https://github.com/msalihberk/redpatch.git
cd redpatch

docker compose up -d --build
```

Then open:

**http://localhost:8000**

---

# 🛠️ Development

### Requirements

* Python 3.10+
* Docker / Docker Desktop
* Git

```bash
git clone https://github.com/msalihberk/redpatch.git
cd redpatch

python -m venv .venv
```

Activate:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
uvicorn app.main:app --reload --port 8000
```

---

# 📁 Project Structure

```text
redpatch/
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── config.json
│   │
│   ├── labs/
│   │   └── manifest.json
│   │
│   ├── services/
│   │   ├── ai/
│   │   ├── container_services/
│   │   └── module_manager/
│   │
│   ├── static/
│   └── templates/
│
├── docker-compose.yaml
├── requirements.txt
├── CONTRIBUTING.md
├── SECURITY.md
└── LICENSE
```

The source tree follows the same separation as the runtime architecture:

**Interface → Engine → Services → External Labs**

---

# 🗺️ Roadmap

* [x] Containerized lab execution
* [x] Pentester Mode
* [x] Coder Mode
* [x] Manifest-driven lab discovery
* [x] Isolated workspaces
* [x] AI-assisted verification
* [x] Docker distribution
* [ ] More vulnerability categories
* [ ] Additional LLM providers
* [ ] Automated security regression testing
* [ ] Expanded lab ecosystem

---

# 🤝 Contributing

RedPatch is designed to grow through both **engine improvements** and **new security laboratories**.

If you want to contribute:

* Improve the host engine
* Add infrastructure capabilities
* Create new labs in the [`redpatch-labs`](https://github.com/msalihberk/redpatch-labs) repository
* Report bugs
* Suggest new security scenarios

Read the [Contributing Guide](CONTRIBUTING.md) before submitting a pull request.

---

<div align="center">

## ⭐ Like the idea?

### Star the project and follow its evolution.

<br><br>

<sub>

Built with ❤️ as a Harvard CS50x Final Project by <a href="cs50.harvard.edu/certificates/d109dc5b-07bb-4676-b01f-c5ce50d8d2ea">Mustafa Salih Berk</a>.

</sub>

</div>
