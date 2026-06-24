# Question Generator

A web app that generates multiple choice quizzes on any subject and topic, grades your answers, lets you save results as a PDF, and keeps a history of every quiz you've taken.

## Quick Start

1. Open your terminal in the project folder.
2. Create and activate a virtual environment:
   - Windows: `python -m venv .venv` then `.\.venv\Scripts\Activate.ps1`
   - Linux/Mac: `python -m venv .venv` then `source .venv/bin/activate`
3. Install dependencies (first time only):
   ```bash
   pip install -r requirements.txt
   ```
4. Start the app:
   ```bash
   uvicorn main:app --reload --port 3003
   ```
5. Open your browser and go to `http://localhost:3003`

## How It Works

The app opens on a **Login** page. You have two options:

- **Sign up / Log in** — Create an account to unlock quiz history. Your past quizzes are saved and accessible any time.
- **Continue as Guest** — Skip sign-up and go straight to the quiz. Guest sessions are not saved.

### Pages

1. **Login / Sign Up** — Authenticate or continue as a guest.
2. **Home** — Enter a subject (e.g. History), a topic (e.g. World War II), and how many questions you want, then click Generate.
3. **Questions** — Answer each multiple choice question and click Submit Answers.
4. **Results** — See your score, review correct and wrong answers, and download your results as a PDF.
5. **History** *(logged-in users only)* — View all past quizzes with subject, topic, score, and the date and time each quiz was taken. Most recent quizzes appear first.

## Project Structure

```
Question-Generator/
├── main.py                 # FastAPI app — routes and logic
├── requirements.txt        # Python dependencies
├── users.json              # User accounts (auto-created on first sign-up)
├── sessions.json           # Active login sessions (auto-created)
├── history.json            # Per-user quiz history (auto-created)
└── static/
    ├── index.html          # Home page template
    ├── questions.html      # Questions page template
    ├── results.html        # Results page template
    ├── history.html        # History page template
    ├── login.html          # Login page template
    ├── signup.html         # Sign up page template
    └── style.css           # Shared stylesheet
```
### Future Updates
```
1. Leaderboards for quizes globally
2. Achievement badges
3. Win streaks
```

## Dependencies

| Package          | Purpose                            |
|------------------|------------------------------------|
| fastapi          | Web framework                      |
| uvicorn          | ASGI server                        |
| requests         | HTTP client for the AI API         |
| fpdf2            | Server-side PDF generation         |
| python-multipart | HTML form data parsing             |

## Built With

- Python, HTML, CSS
- Pollinations AI (free, no API key required)

Built by Rejoice Akosua Dzanku.
