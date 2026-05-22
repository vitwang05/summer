# app.py

from flask import Flask, render_template, request, redirect, jsonify
import os
import re

app = Flask(__name__)

EXAM_FOLDER = "de"


# =========================
# Đọc danh sách đề
# =========================
@app.route("/")
def index():

    exams = []

    for file in os.listdir(EXAM_FOLDER):

        if file.endswith(".txt"):

            exams.append(file)

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

    save_path = os.path.join(
        EXAM_FOLDER,
        file.filename
    )

    file.save(save_path)

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

    path = os.path.join(EXAM_FOLDER, filename)

    if os.path.exists(path):

        os.remove(path)

    return redirect("/")
# =========================
# Trang làm bài
# =========================
@app.route("/quiz/<filename>")
def quiz(filename):

    path = os.path.join(EXAM_FOLDER, filename)

    with open(path, "r", encoding="utf-8") as f:

        content = f.read()

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