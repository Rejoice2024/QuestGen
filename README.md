# Question Generator

A web app that generates multiple choice quizzes on any subject and topic, grades your answers, and lets you save your results as a PDF.

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

The app runs across three pages:

1. **Home** — Enter a subject (e.g. History), a topic (e.g. World War II), and how many questions you want, then click Generate.
2. **Questions** — Answer each multiple choice question and click Submit Answers.
3. **Results** — See your score, review which answers were correct or wrong, and download your results as a PDF.

## Project Structure

```
Quest/
├── main.py                 # FastAPI app — routes and logic
├── requirements.txt        # Python dependencies
└── static/
    ├── index.html          # Home page template
    ├── questions.html      # Questions page template
    ├── results.html        # Results page template
    └── style.css           # Shared stylesheet
```

## Dependencies

| Package  | Purpose                            |
|----------|------------------------------------|
| fastapi  | Web framework                      |
| uvicorn  | ASGI server                        |
| requests | HTTP client for the AI API         |
| fpdf2    | Server-side PDF generation         |

## Built With

- Python, HTML, CSS
- Pollinations AI (free, no API key required)

Built by Rejoice Akosua Dzanku.
