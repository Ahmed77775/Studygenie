# StudyGenie – AI Study Companion

StudyGenie is a Python/Flet study app with an AI tutor, photo study, flashcards, quizzes, notes, focus timer, progress tracking, and PDF exports.

## Run locally

1. Create and activate a virtual environment.
2. Install the pinned packages:

   ```powershell
   python -m pip install -r requirements.txt
   python -m pip install --no-deps flet-web==1.1.2
   ```

3. Install and start Ollama, then download the app's model:

   ```powershell
   ollama pull gemma3:4b
   ```

4. Start the desktop app:

   ```powershell
   python studygenie.py
   ```

   Or start the browser version locally:

   ```powershell
   python studygenie.py --web --port 8550
   ```

The AI features call Ollama on the same machine as StudyGenie. The app creates its SQLite data file locally; personal data and backups are excluded from this repository.

## Tests

Run the test suite with:

```powershell
python -m unittest discover -s tests -v
```
