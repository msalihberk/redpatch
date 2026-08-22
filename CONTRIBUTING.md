# Contributing to RedPatch

First off, thank you for considering contributing to RedPatch! This project was built to make learning web application security interactive, accessible, and structured. 

Please read the following guidelines to learn how you can add new security lab modules or improve the host application.

---

## 🛡 Responsible Disclosure & Purpose

RedPatch is an educational tool. 
- Only build labs or run testing against containers and environments you own or are authorized to test.
- Do not commit any real credentials, personal information, proprietary code, or destructive exploits.
- For security issues regarding the RedPatch orchestrator itself, please see [SECURITY.md](SECURITY.md).

---

## 🛠 Developing Labs

RedPatch uses a Docker-based architecture where lab containers are isolated and their workspace code is dynamically extracted and mounted.

### Lab Workspace Configuration (`config.json`)
Every lab must package a `config.json` inside its root folder (e.g., `<Category>/<lab-id>/config.json`). This file dictates how the Workspace interface interacts with the lab. Below is the standard structure:

```json
{
  "hints": {
    "target_snippet.py": [
      "Do not pass raw user input directly to shell execution functions.",
      "Use safe alternatives or validate/sanitize input against a strict allowlist."
    ],
    "pentester": [
      "Check how the input is handled in the ping command execution.",
      "Try appending command separators like ';' or '&&' followed by a system command."
    ]
  },
  "solutions": {
    "solution_snippet.py": "codes/solutions/solution_snippet.py",
    "pentester": "127.0.0.1 && cat /app/flag.txt"
  },
  "targets": {
    "target_snippet.py": "codes/vulnerables/target_snippet.py"
  },
  "flags": {
    "flag_1": "redpatch{command_injection_rce_compromised_77481}"
  }
}
```

### Lab Requirements
1. **Directory Structure:** Lab source files must be organized under a folder named after their high-level category (module), containing a subdirectory matching their `lab-id`. For example: `<Category>/<lab-id>/` (e.g., `IDOR/idor-1/`).
2. **Main Entrypoint:** Must include a `main.py` inside the lab folder which runs the web application.
3. **Workspace targets:** Files specified under `targets` will be loaded into the Coder Mode built-in editor and authorized for patching.
4. **Pentester elements:** Define hints under `hints.pentester` and payload walkthroughs under `solutions.pentester`.

---

## 📝 Registering Your Lab

Once your lab image is compiled and hosted (or prepared for distribution), register it in the central manifest catalog:

**File:** [`app/labs/manifest.json`](app/labs/manifest.json)

Add a new submodule under the appropriate category block:
```json
{
  "id": "cmdi-0",
  "title": "Command Injection - Arbitrary OS Execution",
  "description": "Explores OS command injection risks in network utilities.",
  "category": "web",
  "image_tag": "redpatch-lab/cmdi-0:v1.0.0",
  "port": 5002,
  "download_url": "https://github.com/msalihberk/redpatch-labs/releases/download/v1.0.0/cmdi-0.tar.gz"
}
```

### 📦 Dynamic & Custom Labs
If you are developing a custom lab or want to test one locally, you can specify your own URL (e.g. hosting the `.tar.gz` file on a local web server or a private repository release) in the `"download_url"` parameter. When launching the lab, the RedPatch engine will dynamically fetch the image archive from this URL and load it into your local Docker environment.

### 📥 Submitting to the Official Catalog
If you would like your lab to be featured in the official RedPatch catalog so all users can access it:
1. Do not submit the lab code/releases to this core engine repository.
2. Instead, submit a Pull Request to the [redpatch-labs](https://github.com/msalihberk/redpatch-labs) repository.
3. **Important Pathing Requirement:** Inside the `redpatch-labs` repository, place your code files in a folder structure matching `<Category>/<lab-id>`. For example, if you are adding an IDOR lab with `id` `idor-1`, you must place your code files in `IDOR/idor-1` and submit a Pull Request there.
4. Once approved and published, update the `manifest.json` in this repository to point to the new release URL.

---

## 🚀 Testing Your Changes

Before submitting a Pull Request:
1. Ensure the manifest parses correctly and submodule IDs are unique.
2. Confirm the lab launches successfully using Docker.
3. Verify **Pentester Mode** flag submissions resolve correctly.
4. Verify **Coder Mode** patches are applied to the container dynamically and that AI Analysis behaves as expected.

---

## ⚖️ Licensing

By contributing to this project, you agree that your contributions will be licensed under the project's license structure:
* **Host Engine Core:** Licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See the [LICENSE](LICENSE) file for details.
* **Labs & Submodules:** All official labs (source code and challenges) are licensed under the permissive **MIT License**.

