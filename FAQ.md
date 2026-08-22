# Frequently Asked Questions (FAQ)

### 1. What is the difference between Coder Mode and Pentester Mode?
- **Pentester Mode:** You act as the attacker. Your goal is to find security flaws, trigger them to obtain a hidden flag (e.g. `redpatch{...}`), and submit it.
- **Coder Mode:** You act as the defender. Your goal is to open the vulnerable file, patch the code, save it, and verify the patch via the AI Analysis tool.

### 2. Why is the AI Analysis button not working?
To use the AI Analysis agent, you must configure a valid API key in your environment. Create a `.env` file in the root directory and supply your LLM credentials:
```env
API_KEY=your_actual_api_key_here
```
Refer to `app/core/config.py` for default provider options (e.g. Gemini, OpenAI).

### 3. How do lab updates get reflected in the workspace?
RedPatch extracts the lab contents dynamically from the Docker image target `/app` folder. If you modify files in the editor and save, RedPatch pushes the updates directly to the running container. If you break the application, you can hit the **Reset Lab** button to start fresh.

### 4. I launched a lab but I cannot access it. Why?
Verify that:
1. Docker is running on your machine.
2. The Docker container for the lab launched without errors (e.g., check `docker ps`).
3. Port conflicts: If the host port mapped by RedPatch is blocked by another application, try stopping other containers/applications and restarting the lab.

### 5. Can I run RedPatch inside Docker?
Yes, a `docker-compose.yaml` is provided. Running `docker compose up -d --build` spins up both the host service and connects it securely to your local Docker daemon (via the Docker socket mount) to spin up sub-lab containers.
