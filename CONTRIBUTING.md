# Contributing to RedPatch

Thank you for helping improve RedPatch. This guide explains how to run the project, add a security lab module, and prepare a contribution that fits the current module system.

## Purpose and responsible use

RedPatch is an educational, isolated security-learning environment. Only create labs and use the application against systems, data, and networks that you own or are explicitly authorized to test. Keep demonstrations self-contained, deterministic, and safe to run locally. Do not include real credentials, personal data, malware, persistence techniques, destructive payloads, or instructions that target third-party systems.

## Run the project locally

The host application is a FastAPI service and lab submodules are started in Docker. Install the root dependencies, configure the AI provider if you intend to use AI analysis, and start the application with Uvicorn.

```bash
python -m venv .venv
# Activate the virtual environment for your shell.
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Docker must be installed and running before launching a lab from the workspace. The AI analysis feature additionally needs the environment variables expected by `app/core/config.py` (such as `API_KEY`, and optionally `LLM_PROVIDER` and `MODEL`). Never commit `.env` files or API keys.

## How the module system works

RedPatch discovers modules at startup request time by scanning `app/modules`. A category module is a direct child directory with a valid `config.json`; each listed lab is a submodule beneath its `submodules` directory.

```text
app/modules/
└── SQLI/
    ├── config.json                 # Category registration
    └── submodules/
        └── BASIC_SQLI/
            ├── config.json         # Workspace hints and solutions
            ├── main.py              # Uvicorn entry module; exports `app`
            ├── requirements.txt     # Optional lab-only Python dependencies
            ├── templates/
            └── codes/
                ├── vulnerables/
                └── solutions/
```

Category and submodule names are normalized to uppercase by the loader. They must be unique across the whole registry: two categories cannot share a name, and two submodules cannot share a name even when they are in different categories. Keep directory names, configuration names, and URLs consistent by using uppercase underscore-separated identifiers such as `AUTH_BYPASS`.

The loader ignores malformed or incomplete entries rather than failing the entire registry. If a lab does not appear in the Modules page, check its parent configuration first.

## Create a new module or submodule

1. Create a category directory in `app/modules`. Add a `config.json`, or extend an existing category when the new lab belongs to it.
2. Create the lab at `app/modules/<CATEGORY>/submodules/<SUBMODULE>/`.
3. Add the lab metadata to the parent category's `sub_modules` array.
4. Implement the lab application and its workspace files.
5. Start the application, confirm the category and lab appear, then launch the container and exercise both the vulnerable and fixed behavior.

The parent configuration is the registration source of truth. A minimal valid example is:

```json
{
  "name": "SQLI",
  "description": "Training labs for SQL injection vulnerabilities.",
  "sub_modules": [
    {
      "name": "BASIC_SQLI",
      "description": "Authentication bypass caused by SQL string concatenation.",
      "runtime": "python:3.11-slim",
      "entrypoint": "main.py",
      "internal_port": 5000,
      "codes": {
        "target_snippet.py": "vulnerable",
        "solution_snippet.py": "fixed"
      }
    }
  ]
}
```

Every registered submodule needs the following fields:

| Field | Requirement |
| --- | --- |
| `name` | Unique, non-empty lab identifier. |
| `description` | Short explanation shown in the module browser. |
| `runtime` | Docker image used to run the lab, for example `python:3.11-slim`. |
| `entrypoint` | Python file name whose stem is imported by Uvicorn. `main.py` means `main:app`. |
| `internal_port` | Positive TCP port exposed by the lab application. |
| `codes` | Object mapping editable file names to their role. |

At present, the runner starts `uvicorn <entrypoint-stem>:app` in the selected runtime image and bind-mounts a session-specific copy of the submodule into `/app`. Therefore the entry module must export an ASGI object named `app`, listen on `internal_port`, and include all startup dependencies in the submodule's `requirements.txt` when they are not in the runtime image. A submodule `Dockerfile` is not built or used by the current runner; do not rely on it for setup.

## Workspace contract

`codes` controls which files can be patched through the workspace API. Each key is a file name, not a path. The file must exist exactly once under the submodule directory; duplicate file names can make the editor unable to resolve the intended source. Use `"vulnerable"` for every file that should be visible in the editor. Other values may be registered for clarity, but only vulnerable files are currently loaded into the workspace.

Use a submodule-level `config.json` to provide hints and reference fixes:

```json
{
  "hints": {
    "target_snippet.py": [
      "Keep untrusted input out of query strings.",
      "Use parameter binding for database values."
    ]
  },
  "solutions": {
    "target_snippet.py": "codes/solutions/solution_snippet.py"
  }
}
```

Hint values must be arrays of strings. Each `solutions` key must match a vulnerable file name and each value must be a non-empty path relative to the submodule directory. Keep solution files outside `codes/vulnerables` and ensure they demonstrate the intended remediation without changing the lesson's scope.

## Lab design rules

- Make the vulnerable route and the secure route easy to identify and test.
- Keep the exploit demonstration confined to the lab's own data and container.
- Seed only fictional, non-sensitive test data. Reset or recreate mutable state predictably.
- Include a lightweight health endpoint when practical, such as `GET /health`.
- Do not hard-code host ports. RedPatch assigns an available host port and proxies requests to the lab.
- Treat the original submodule directory as source material. Workspace edits occur in per-session temporary copies and should not modify committed lab files.
- Keep dependencies minimal and pin them when reproducibility requires it.
- Write all user-facing names, descriptions, hints, messages, and documentation in English.

## Testing a contribution

Before opening a pull request, verify the following manually:

- The JSON files parse and the module and submodule names are unique.
- The category and lab are listed at `/modules`.
- The workspace loads each declared vulnerable file, its hints, and its solution.
- Starting the lab creates a functioning container and the app responds through the RedPatch proxy.
- Applying a patch changes only the active session copy; Reset Lab restores the original files.
- The vulnerable scenario is reproducible and the secure scenario prevents the demonstrated issue.
- A clean environment can install the root requirements and any submodule requirements.

## Pull requests and code quality

Keep pull requests focused: one lab or one related improvement per change set. Explain the security concept, the expected vulnerable behavior, the expected fix, and how you tested it. Include screenshots only when a UI change needs visual context. Do not submit secrets, generated databases containing sensitive data, local virtual environments, or unrelated formatting changes.

Follow the existing Python and JSON style, use UTF-8 files, and favor clear names over clever abstractions. If your change affects module discovery, workspace editing, container startup, or proxy behavior, describe the compatibility impact and test an existing lab as well as the new one.

## Reporting issues

For ordinary bugs, include steps to reproduce, expected and actual behavior, operating system, Python version, Docker version, and relevant sanitized logs. For a security issue in RedPatch itself, do not publish exploit details or secrets in a public issue; contact the maintainers privately through the project's security reporting channel when one is available.
