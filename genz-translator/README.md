# GenZ Translator

A production-ready local web app for translating between professor or formal academic language and Gen Z slang. It runs locally with FastAPI, vanilla HTML/CSS/JavaScript, and Ollama.

## Features

- Professor / formal academic language to Gen Z slang
- Gen Z slang to professor / formal academic language
- Tone selector: Light Gen Z, Medium Gen Z, Extreme Gen Z, Professional Academic
- Optional slang explanation
- Example input buttons
- Copy-to-clipboard output
- Friendly errors when the backend, Ollama, or local model is unavailable
- Swappable local model through environment variables

## Project Structure

```text
genz-translator/
  frontend/
    index.html
    styles.css
    script.js
  backend/
    __init__.py
    main.py
    requirements.txt
  README.md
  .env.example
  start.sh
  start.bat
```

## Setup

### 1. Install Ollama

Install Ollama from:

```text
https://ollama.com/download
```

Start Ollama after installation. On many systems, opening the Ollama app starts the local server at:

```text
http://localhost:11434
```

### 2. Pull a local model

The default configuration uses:

```bash
ollama pull gemma4
```

If `gemma4` is not available in your Ollama installation, pull another local model and configure it in `.env`, for example:

```bash
ollama pull gemma3
```

Then create a local `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
LOCAL_MODEL_NAME=gemma3
OLLAMA_BASE_URL=http://localhost:11434
HOST=127.0.0.1
PORT=8000
```

The backend reads `LOCAL_MODEL_NAME`, so you can swap to any Ollama model without changing code.

### 3. Start the backend and local web app

On Windows:

```bat
start.bat
```

On macOS or Linux:

```bash
chmod +x start.sh
./start.sh
```

The startup script creates a virtual environment, installs Python dependencies, and starts FastAPI.

### 4. Open the app

Open:

```text
http://127.0.0.1:8000
```

The FastAPI backend serves the frontend and exposes the API endpoints.

## API

### Health check

```bash
curl http://127.0.0.1:8000/health
```

### Translate

```bash
curl -X POST http://127.0.0.1:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Please review the rubric before submitting.",
    "direction": "professor_to_genz",
    "tone_level": "medium_genz",
    "explain_slang": true
  }'
```

On Windows PowerShell:

```powershell
$body = @{
  text = "This lecture is lowkey cooking."
  direction = "genz_to_professor"
  tone_level = "professional_academic"
  explain_slang = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/translate" -Method Post -ContentType "application/json" -Body $body
```

## Configuration

Environment variables:

```env
LOCAL_MODEL_NAME=gemma4
OLLAMA_BASE_URL=http://localhost:11434
HOST=127.0.0.1
PORT=8000
```

Use `.env.example` as a template. The app does not call OpenAI, cloud APIs, or any external model service.

## Troubleshooting

### "Ollama is not reachable"

Start the Ollama app or service, then verify:

```bash
ollama list
```

You can also check:

```bash
curl http://localhost:11434/api/tags
```

### "The configured model is not installed"

Pull the model named in `LOCAL_MODEL_NAME`:

```bash
ollama pull gemma4
```

If that model is unavailable, choose another Ollama model:

```bash
ollama pull gemma3
```

Then update `.env`:

```env
LOCAL_MODEL_NAME=gemma3
```

### The model is slow

Try a smaller model, shorten the input text, or lower the context load by translating one paragraph at a time.

### The frontend says "Backend unavailable"

Make sure FastAPI is running and open the frontend through:

```text
http://127.0.0.1:8000
```

Opening `frontend/index.html` directly may not work because browser security rules can block API requests or static asset paths.
