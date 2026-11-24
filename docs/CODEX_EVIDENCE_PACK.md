# Codex Evidence Pack — StudyGenie

## Project

- Project source: the StudyGenie project supplied as `study genie.zip`.
- Stack: Python 3.15, Flet 1.1.2, SQLite, and Ollama's Python client.
- AI model configured in `app/prompts.py`: `gemma3:4b` (local Ollama).
- Coding assistant: Codex, powered by GPT-6.

## Work stages

1. Reviewed the project files and prepared the clean copy in this repository; the copy excludes the original `.git`, virtual environment, local database, JSON data, and backups.
2. Added local setup and run instructions in `README.md`.
3. Published the project to the public GitHub repository below. The initial GitHub README commit was merged without force-pushing.
4. Started the app locally and exposed its web port with a temporary Cloudflare Quick Tunnel for the submission demo.

## Evidence and results

- GitHub repository: [Ahmed77775/Studygenie](https://github.com/Ahmed77775/Studygenie)
- Live demo (temporary): [Open StudyGenie](https://plymouth-bikes-atlantic-bride.trycloudflare.com/)
- The local app endpoint and public HTTPS URL both returned HTTP 200.
- `gemma3:4b` was present in the local Ollama model list; an end-to-end AI conversation was not tested through the browser.
- The Python Flet and Ollama packages imported successfully.
- The Python unit test suite was not run during publishing.
- Local SQLite data is ignored by Git; the running demo stores visitor data on the host PC, shared by visitors to the same app instance.

## Demo limitations

The Cloudflare Quick Tunnel is for temporary testing. The link stops working when its tunnel process stops, and anyone who has the link can reach the app. Keep the PC and Ollama running while the demo is needed. See [Cloudflare Quick Tunnel documentation](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).
