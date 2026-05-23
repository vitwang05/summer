# app.py

from flask import Flask, render_template, request, redirect, jsonify
import os
import re
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

# Database setup
DB_PATH = "exams.db"

def init_db():
    """Khởi tạo database nếu chưa tồn tại"""
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

def get_db():
    """Kết nối đến database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Khởi tạo database khi app start
init_db()

# Disable caching để tránh browser cache nội dung cũ
@app.after_request
def set_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# =========================
# Đọc danh sách đề
# =========================
@app.route("/")
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM exams ORDER BY created_at DESC")
    exams = [row['filename'] for row in cursor.fetchall()]
    conn.close()
    
    return render_template(
        "index.html",
        exams=exams
    )

# =========================
# Upload đề
# =========================
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")

    if not file:
        return redirect("/")

    if not file.filename.endswith(".txt"):
        return redirect("/")

    content = file.read().decode("utf-8")
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO exams (filename, content) VALUES (?, ?)",
            (file.filename, content)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # File đã tồn tại - cập nhật nó
        cursor.execute(
            "UPDATE exams SET content = ? WHERE filename = ?",
            (content, file.filename)
        )
        conn.commit()
    
    conn.close()
    return redirect("/")

# =========================
# Validate file đề
# =========================
@app.route("/validate", methods=["POST"])
def validate_exam():

    file = request.files.get("file")

    if not file:
        return jsonify({
            "success": False,
            "message": "Không có file"
        })

    text = file.read().decode("utf-8")

    result = validate_questions(text)

    return jsonify(result)    

# =========================
# Xóa đề
# =========================
@app.route("/delete/<filename>")
def delete_exam(filename):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exams WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()
    
    return redirect("/")
# =========================
# Trang làm bài
# =========================
@app.route("/quiz/<filename>")
def quiz(filename):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM exams WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return redirect("/")
    
    content = row['content']
    questions = parse_questions(content)

    return render_template(
        "quiz.html",
        filename=filename,
        questions=questions
    )


# =========================
# Parse câu hỏi
# =========================
def parse_questions(text):

    questions = []

    blocks = re.split(r"\n\s*\n", text.strip())

    for block in blocks:

        lines = [
            line.strip()
            for line in block.split("\n")
            if line.strip()
        ]

        if len(lines) < 6:
            continue

        question_text = lines[0]

        answers = []

        correct = ""

        for line in lines[1:]:

            if line.startswith("ANSWER:"):

                correct = line.replace(
                    "ANSWER:",
                    ""
                ).strip()

            else:

                answers.append(line)

        questions.append({
            "question": question_text,
            "answers": answers,
            "correct": correct
        })

    return questions

def validate_questions(text):

    blocks = re.split(r"\n\s*\n", text.strip())

    errors = []

    parsed_questions = []

    for index, block in enumerate(blocks):

        lines = [
            line.strip()
            for line in block.split("\n")
            if line.strip()
        ]

        question_number = index + 1

        if len(lines) < 6:

            errors.append(
                f"Câu {question_number}: thiếu dữ liệu"
            )

            continue

        if not lines[0].startswith("Câu"):

            errors.append(
                f"Câu {question_number}: dòng đầu không hợp lệ"
            )

        answer_lines = []

        correct = None

        for line in lines[1:]:

            if re.match(r"^[A-D]\.", line):

                answer_lines.append(line)

            elif line.startswith("ANSWER:"):

                correct = line.replace(
                    "ANSWER:",
                    ""
                ).strip()

        if len(answer_lines) != 4:

            errors.append(
                f"Câu {question_number}: phải có đúng 4 đáp án A B C D"
            )

        if correct not in ["A","B","C","D"]:

            errors.append(
                f"Câu {question_number}: đáp án đúng không hợp lệ"
            )

        parsed_questions.append({
            "question": lines[0],
            "answers": answer_lines,
            "correct": correct
        })

    return {
        "success": len(errors) == 0,
        "errors": errors,
        "questions": parsed_questions
    }

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000)