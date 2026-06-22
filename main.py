import hashlib
import json
import os
import secrets
from datetime import datetime
from html import escape, unescape
import requests
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

AI_API      = "https://text.pollinations.ai/"
USERS_FILE   = "users.json"
SESSIONS_FILE = "sessions.json"
HISTORY_FILE  = "history.json"


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE) as f:
        return json.load(f)


def save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)


def load_sessions() -> dict:
    if not os.path.exists(SESSIONS_FILE):
        return {}
    with open(SESSIONS_FILE) as f:
        return json.load(f)


def save_sessions(sessions: dict):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f)


def load_history() -> dict:
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE) as f:
        return json.load(f)


def save_history(history: dict):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)


def add_to_history(username, subject, topic, score, total, percent):
    history = load_history()
    if username not in history:
        history[username] = []
    now = datetime.now()
    history[username].append({
        "date": now.strftime("%b %d, %Y"),
        "time": now.strftime("%I:%M %p"),
        "subject": subject,
        "topic": topic,
        "score": score,
        "total": total,
        "percent": percent,
    })
    save_history(history)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Session / auth helpers
# ---------------------------------------------------------------------------

def get_username(request: Request):
    token = request.cookies.get("session")
    if not token:
        return None
    return load_sessions().get(token)


def is_guest(request: Request) -> bool:
    return request.cookies.get("guest") == "1"


def is_authenticated(request: Request) -> bool:
    return get_username(request) is not None or is_guest(request)


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

def build_navbar(username=None) -> str:
    if username:
        return (
            '<nav class="navbar">'
            '<a href="/" class="navbar-brand">Question Generator</a>'
            '<div class="navbar-right">'
            f'<span class="navbar-user">Hi, {escape(username)}</span>'
            '<a href="/history" class="navbar-link">History</a>'
            '<a href="/logout" class="navbar-link navbar-logout">Log Out</a>'
            '</div>'
            '</nav>'
        )
    return (
        '<nav class="navbar">'
        '<a href="/" class="navbar-brand">Question Generator</a>'
        '<a href="/login" class="navbar-link">Log In</a>'
        '</nav>'
    )


def _render(template: str, replacements: dict) -> str:
    with open(f"static/{template}") as f:
        html = f.read()
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    return html


def build_page(results_html="", navbar_html=""):
    return _render("index.html", {
        "<!-- NAVBAR -->": navbar_html,
        "<!-- RESULTS -->": results_html,
    })


def build_questions_page(content="", navbar_html=""):
    return _render("questions.html", {
        "<!-- NAVBAR -->": navbar_html,
        "<!-- CONTENT -->": content,
    })


def build_results_page(content="", navbar_html=""):
    return _render("results.html", {
        "<!-- NAVBAR -->": navbar_html,
        "<!-- CONTENT -->": content,
    })


def build_history_page(content="", navbar_html=""):
    return _render("history.html", {
        "<!-- NAVBAR -->": navbar_html,
        "<!-- CONTENT -->": content,
    })


def build_auth_page(template: str, error: str = "") -> str:
    minimal_nav = (
        '<nav class="navbar">'
        '<a href="/" class="navbar-brand">Question Generator</a>'
        '</nav>'
    )
    error_html = f'<p class="auth-error">{escape(error)}</p>' if error else ""
    return _render(template, {
        "<!-- NAVBAR -->": minimal_nav,
        "<!-- ERROR -->": error_html,
    })


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def clean_json(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    return text.strip()


def safe_text(text):
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.get("/login")
def login_page():
    return HTMLResponse(build_auth_page("login.html"))


@app.post("/login")
def login(username: str = Form(), password: str = Form()):
    users = load_users()
    stored = users.get(username.strip())
    if not stored or stored != hash_password(password):
        return HTMLResponse(build_auth_page("login.html", "Invalid username or password."))
    token = secrets.token_hex(32)
    sessions = load_sessions()
    sessions[token] = username.strip()
    save_sessions(sessions)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("session", token, httponly=True)
    resp.delete_cookie("guest")
    return resp


@app.get("/signup")
def signup_page():
    return HTMLResponse(build_auth_page("signup.html"))


@app.post("/signup")
def signup(
    username: str = Form(),
    password: str = Form(),
    confirm_password: str = Form(),
):
    username = username.strip()
    if not username:
        return HTMLResponse(build_auth_page("signup.html", "Username cannot be empty."))
    if len(password) < 6:
        return HTMLResponse(build_auth_page("signup.html", "Password must be at least 6 characters."))
    if password != confirm_password:
        return HTMLResponse(build_auth_page("signup.html", "Passwords do not match."))
    users = load_users()
    if username in users:
        return HTMLResponse(build_auth_page("signup.html", "That username is already taken."))
    users[username] = hash_password(password)
    save_users(users)
    return RedirectResponse("/login", status_code=303)


@app.get("/guest")
def continue_as_guest():
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("guest", "1", httponly=True)
    return resp


@app.get("/logout")
def logout(request: Request):
    token = request.cookies.get("session")
    if token:
        sessions = load_sessions()
        sessions.pop(token, None)
        save_sessions(sessions)
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("session")
    resp.delete_cookie("guest")
    return resp


# ---------------------------------------------------------------------------
# App routes
# ---------------------------------------------------------------------------

@app.get("/")
def home(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=303)
    username = get_username(request)
    navbar = build_navbar(username)
    return HTMLResponse(build_page(navbar_html=navbar))


@app.post("/generate")
def generate(
    request: Request,
    subject: str = Form(),
    topic: str = Form(),
    num_questions: int = Form(),
):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=303)

    username = get_username(request)
    navbar = build_navbar(username)

    instructions = (
        f"Generate exactly {num_questions} multiple choice questions about the topic "
        f'"{topic}" in the subject "{subject}". '
        f"Return ONLY a valid JSON array with no markdown or extra text. "
        f'Each object must have: "question" (string), "options" (array of exactly 4 strings), '
        f'"answer" (string that exactly matches one of the 4 options). '
        f'Example: [{{"question": "What is 2+2?", "options": ["3", "4", "5", "6"], "answer": "4"}}]'
    )

    response = requests.post(
        AI_API,
        json={
            "messages": [{"role": "user", "content": instructions}],
            "model": "openai",
            "seed": 42,
        },
        timeout=60,
    )

    raw = clean_json(response.text)
    try:
        questions = json.loads(raw)
    except Exception:
        return HTMLResponse(build_page(
            "<p class='error'>Could not generate questions. Please try again.</p>",
            navbar_html=navbar,
        ))

    quiz_json = escape(json.dumps(questions))

    content = (
        f'<input type="hidden" name="subject" value="{escape(subject)}">'
        f'<input type="hidden" name="topic" value="{escape(topic)}">'
        f'<input type="hidden" name="quiz_data" value="{quiz_json}">'
        f'<h2 class="quiz-heading">{escape(subject)} &mdash; {escape(topic)}</h2>'
    )

    for i, q in enumerate(questions):
        content += '<div class="question-card">'
        content += f'<p class="question-text"><span class="q-num">{i + 1}.</span> {escape(q["question"])}</p>'
        content += '<div class="options">'
        for option in q["options"]:
            safe_val = escape(option)
            content += (
                f'<label class="option-label">'
                f'<input type="radio" name="answer_{i}" value="{safe_val}" required>'
                f'<span>{safe_val}</span>'
                f'</label>'
            )
        content += "</div></div>"

    return HTMLResponse(build_questions_page(content, navbar_html=navbar))


@app.post("/results")
async def check_results(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=303)

    username = get_username(request)
    navbar = build_navbar(username)

    form = await request.form()
    subject = form.get("subject", "")
    topic = form.get("topic", "")
    quiz_data = json.loads(form.get("quiz_data", "[]"))

    score = 0
    result_items = []

    for i, q in enumerate(quiz_data):
        user_ans = form.get(f"answer_{i}", "").strip()
        correct_ans = q["answer"].strip()

        matching = [o for o in q["options"] if o.strip().lower() == correct_ans.lower()]
        if matching:
            correct_ans = matching[0]

        is_correct = user_ans.lower() == correct_ans.lower()
        if is_correct:
            score += 1

        result_items.append({
            "question": q["question"],
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "correct": is_correct,
        })

    total = len(quiz_data)
    percent = round((score / total) * 100) if total else 0

    if username:
        add_to_history(username, subject, topic, score, total, percent)

    results_data = {
        "subject": subject,
        "topic": topic,
        "score": score,
        "total": total,
        "items": result_items,
    }
    results_json = escape(json.dumps(results_data))

    rows = ""
    for item in result_items:
        status_class = "correct" if item["correct"] else "wrong"
        status_text = "Correct" if item["correct"] else "Wrong"
        rows += (
            f'<div class="result-row {status_class}">'
            f'<p class="result-question">{escape(item["question"])}</p>'
            f'<div class="result-answers">'
            f'<span class="your-answer">Your answer: <strong>{escape(item["user_answer"])}</strong></span>'
            f'<span class="correct-answer">Correct answer: <strong>{escape(item["correct_answer"])}</strong></span>'
            f'<span class="status-badge {status_class}">{status_text}</span>'
            f'</div></div>'
        )

    content = (
        f'<div class="score-banner">'
        f'<p class="score-label">Your Score</p>'
        f'<p class="score-value">{score} / {total}</p>'
        f'<p class="score-percent">{percent}%</p>'
        f'<p class="score-sub">{escape(subject)} &mdash; {escape(topic)}</p>'
        f'</div>'
        f'<div class="results-list">{rows}</div>'
        f'<form action="/download-pdf" method="post" class="pdf-form">'
        f'<input type="hidden" name="results_data" value="{results_json}">'
        f'<button type="submit" class="pdf-btn">Save Results as PDF</button>'
        f'</form>'
    )

    return HTMLResponse(build_results_page(content, navbar_html=navbar))


@app.get("/history")
def history_page(request: Request):
    username = get_username(request)
    if not username:
        return RedirectResponse("/login", status_code=303)

    navbar = build_navbar(username)
    history_data = load_history()
    user_history = history_data.get(username, [])

    if not user_history:
        content = (
            '<p class="no-history">'
            'You haven\'t taken any quizzes yet. '
            '<a href="/">Start one now!</a>'
            '</p>'
        )
    else:
        rows = ""
        for item in reversed(user_history):
            if item["percent"] >= 70:
                badge_class = "high"
            elif item["percent"] >= 40:
                badge_class = "mid"
            else:
                badge_class = "low"

            rows += (
                f'<div class="history-row">'
                f'<div class="history-info">'
                f'<p class="history-subject">{escape(item["subject"])} &mdash; {escape(item["topic"])}</p>'
                f'<p class="history-date">{escape(item["date"])} at {escape(item["time"])}</p>'
                f'</div>'
                f'<div class="history-score {badge_class}">'
                f'<span class="history-fraction">{item["score"]}/{item["total"]}</span>'
                f'<span class="history-percent">{item["percent"]}%</span>'
                f'</div>'
                f'</div>'
            )
        content = f'<div class="history-list">{rows}</div>'

    return HTMLResponse(build_history_page(content, navbar_html=navbar))


@app.post("/download-pdf")
async def download_pdf(request: Request):
    form = await request.form()
    data = json.loads(form.get("results_data", "{}"))

    subject = data.get("subject", "")
    topic = data.get("topic", "")
    score = data.get("score", 0)
    total = data.get("total", 0)
    items = data.get("items", [])

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, safe_text(f"{subject} - {topic}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 13)
    pdf.cell(0, 8, safe_text(f"Score: {score} / {total}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(8)

    for i, item in enumerate(items):
        status = "Correct" if item["correct"] else "Wrong"
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 7, safe_text(f"{i + 1}. {item['question']}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, safe_text(f"    Your answer: {item['user_answer']}  [{status}]"), new_x="LMARGIN", new_y="NEXT")
        if not item["correct"]:
            pdf.set_text_color(180, 0, 0)
            pdf.cell(0, 6, safe_text(f"    Correct answer: {item['correct_answer']}"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    pdf_bytes = bytes(pdf.output())
    filename = f"{subject}_{topic}_results.pdf".replace(" ", "_")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
