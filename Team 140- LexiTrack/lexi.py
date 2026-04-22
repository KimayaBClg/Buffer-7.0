import pdfplumber
from docx import Document as DocxDocument
from flask import Flask, render_template, request, redirect, url_for, session
import os
import re
import threading
import queue
from datetime import datetime
from werkzeug.utils import secure_filename
import urllib.parse

app = Flask(__name__)
# FORCES LOGIN ON RESTART: Generates a new random key every time the program runs
app.secret_key = os.urandom(24) 

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt"}
PASSWORD = "lex2024"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

upload_queue = queue.Queue()
documents = [] 
doc_id_counter = 1

def document_worker():
    global doc_id_counter
    while True:
        filepath, filename = upload_queue.get()
        try:
            text = extract_text_from_file(filepath, filename)
            subject, subject_type = detect_subject(filename, text)
            
            existing_doc = next((d for d in documents if d["name"] == filename), None)
            
            doc_data = {
                "id": existing_doc["id"] if existing_doc else doc_id_counter,
                "name": filename,
                "subject": subject,
                "subject_type": subject_type,
                "dates": extract_dates(text),
                "snippet": extract_snippet(text),
                "uploaded_at": existing_doc["uploaded_at"] if existing_doc else datetime.now().strftime("%d %b %Y, %I:%M %p"),
            }
            if existing_doc:
                idx = documents.index(existing_doc)
                documents[idx] = doc_data
            else:
                documents.insert(0, doc_data)
                doc_id_counter += 1
        except Exception as e: print(f"Worker Error: {e}")
        finally: upload_queue.task_done()

threading.Thread(target=document_worker, daemon=True).start()

def reload_and_rescan():
    global doc_id_counter
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            if allowed_file(filename):
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                documents.append({"id": doc_id_counter, "name": filename, "subject": "Analyzing...", "subject_type": "unknown", "dates": [], "snippet": "Re-syncing...", "uploaded_at": "Stored"})
                doc_id_counter += 1
                upload_queue.put((filepath, filename))

def allowed_file(f): return "." in f and f.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_dates(text):
    patterns = [
        r"\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?[a-z,]*\s*\b\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s\d{4}\b"
    ]
    found = []
    for p in patterns: found.extend(re.findall(p, text, re.IGNORECASE))
    cleaned = [re.sub(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s*", "", d, flags=re.IGNORECASE).strip() for d in found]
    return list(dict.fromkeys(cleaned))

def detect_subject(n, t):
    combined = (n + " " + t).lower()
    if re.search(r"land|registry|property|deed|plot|rent|lease|tenant", combined): 
        return "Land Document", "land"
    if re.search(r"court|justice|v\.|suit|order|case|scheduling", combined): 
        return "Legal Order", "court"
    return "Legal Document", "unknown"

def extract_snippet(t): return t[:140].replace("\n", " ").strip() + "…"

def extract_text_from_file(filepath, filename):
    text = ""
    if filename.lower().endswith(".pdf"):
        with pdfplumber.open(filepath) as pdf: text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif filename.lower().endswith(".docx"):
        doc = DocxDocument(filepath)
        text = "\n".join(p.text for p in doc.paragraphs)
    return text

@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("logged_in"): return redirect(url_for("dashboard"))
    if request.method == "POST":
        input_pass = request.form.get("password", "").strip().lower()
        if input_pass == PASSWORD:
            session.clear()
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid Access Key")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"): return redirect(url_for("login"))
    return render_template("dashboard.html", docs=documents)

@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("logged_in"): return redirect(url_for("login"))
    file = request.files.get("file")
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        upload_queue.put((filepath, filename))
    return redirect(url_for("dashboard"))

@app.route("/delete/<int:doc_id>", methods=["POST"])
def delete_document(doc_id):
    if not session.get("logged_in"): return redirect(url_for("login"))
    global documents
    doc = next((d for d in documents if d["id"] == doc_id), None)
    if doc:
        path = os.path.join(UPLOAD_FOLDER, doc["name"])
        if os.path.exists(path): os.remove(path)
        documents = [d for d in documents if d["id"] != doc_id]
    return redirect(url_for("dashboard"))

@app.route("/calendar/<int:doc_id>")
def add_calendar(doc_id):
    if not session.get("logged_in"): return redirect(url_for("login"))
    target = next((d for d in documents if d["id"] == doc_id), None)
    if not target: return redirect(url_for("dashboard"))
    links = []
    fmts = ["%d/%m/%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y"]
    for raw in target["dates"]:
        for f in fmts:
            try:
                dt = datetime.strptime(raw, f)
                s, e = dt.strftime("%Y%m%dT090000"), dt.strftime("%Y%m%dT100000")
                p = urllib.parse.urlencode({"action": "TEMPLATE", "text": f"Deadline: {target['name']}", "dates": f"{s}/{e}"})
                links.append({"date": raw, "url": f"https://calendar.google.com/calendar/render?{p}"})
                break
            except ValueError: continue
    links_html = "".join([f'<a href="{i["url"]}" target="_blank" style="display:block;margin:12px 0;padding:18px;background:#1e1e1e;color:#ffb74d;text-decoration:none;border-radius:10px;border:1px solid #333;">{i["date"]}</a>' for i in links])
    return f"<html><body style='background:#0f0f0f;color:white;font-family:sans-serif;display:flex;justify-content:center;padding-top:80px;'><div style='width:400px;background:#121212;padding:40px;border-radius:20px;text-align:center;border:1px solid #222;'><h2>LexiTrack Sync</h2><div style='text-align:left;margin-top:20px;'>{links_html}</div><a href='/dashboard' style='display:block;margin-top:20px;color:#00e5ff;text-decoration:none;'>← Back</a></div></body></html>"

if __name__ == "__main__":
    reload_and_rescan()
    app.run(debug=True, port=5001, threaded=True)