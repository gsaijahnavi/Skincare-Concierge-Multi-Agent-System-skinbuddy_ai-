# Skincare Concierge Multi-Agent System (SkinBuddy AI)

## Overview
This project is a multi-agent skincare concierge system built with FastAPI. It leverages multiple agents and tools to provide personalized skincare recommendations, reminders, and routines. The system integrates with Google Calendar and supports live chat via WebSocket.

## Features
- Multi-agent orchestration for skincare advice
- Google Calendar integration for reminders
- Evidence-based product lookup
- Routine and safety checks
- User profile management
- WebSocket live chat interface

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repo-url>
cd skincare-concierge
```

### 2. Create and Activate a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Ensure `requirements.txt` is up-to-date. Install all required packages:
```bash
pip install -r requirements.txt
```

### 4. Export Google API Key
Set your Google API credentials as environment variables:
```bash
export GOOGLE_API_KEY=<your_google_api_key>
export GOOGLE_CLIENT_SECRET=<your_client_secret>
```
Or ensure `config/google/client_secret.json` and `config/google/token.json` are present.

### 5. Run the Server
```bash
uvicorn server:app --reload
```
The app will be available at [http://localhost:8000](http://localhost:8000).

### 6. Access the Web UI
Open [http://localhost:8000](http://localhost:8000) in your browser for the homepage UI.

## File Structure
- `agents/` - Agent implementations
- `tools/` - Tool modules (calendar, reminders, product lookup, etc.)
- `data/` - Data files (reminders, profiles, product catalog, evidence)
- `static/` - Frontend HTML
- `server.py` - FastAPI server
- `requirements.txt` - Python dependencies

## Updating requirements.txt
To ensure all libraries in your virtual environment are included with correct versions, run:
```bash
pip freeze > requirements.txt
```

## Testing
Run tests using pytest:
```bash
pytest
```

## Notes
- Make sure your Google API credentials are valid and have the necessary permissions for calendar access.
- For any additional configuration, check the `config/` directory.

## License
MIT
