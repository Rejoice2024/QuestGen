import json
from html import escape, unescape
import requests
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

AI_API = "https://text.pollinations.ai/"


def build_page(results_html=""):
    file = open("static/index.html")
    html = file.read()
    file.close()
    html = html.replace("<!-- RESULTS -->", results_html)
    return html


def build_questions_page(content=""):
    file = open("static/questions.html")
    html = file.read()
    file.close()
    html = html.replace("<!-- CONTENT -->", content)
    return html


def build_results_page(content=""):
    file = open("static/results.html")
    html = file.read()
    file.close()
    html = html.replace("<!-- CONTENT -->", content)
    return html


def clean_json(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    return text.strip()


def safe_text(text):
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


@app.get("/")
def home():
    return HTMLResponse(build_page())


@app.post("/generate")
def generate(subject: str = Form(), topic: str = Form(), num_questions: int = Form()):
    intructions = (
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
            "messages": [{"role": "user", "content": intructions}],
            "model": "openai",
            "seed": 42,
        },
        timeout=60,
    )

    raw = clean_json(response.text)
    try:
        questions = json.loads(raw)
    except Exception:
        return HTMLResponse(build_page("<p class='error'>Could not generate questions. Please try again.</p>"))

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

    return HTMLResponse(build_questions_page(content))


@app.post("/results")
async def check_results(request: Request):
    form = await request.form()
    subject = form.get("subject", "")
    topic = form.get("topic", "")
    quiz_data = json.loads(form.get("quiz_data", "[]"))

    score = 0
    result_items = []

    for i, q in enumerate(quiz_data):
        user_ans = form.get(f"answer_{i}", "").strip()
        correct_ans = q["answer"].strip()

        # normalize correct answer to exactly match one of the options
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

    return HTMLResponse(build_results_page(content))


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
