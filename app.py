from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/students")
def students():
    connection = sqlite3.connect("Studentdataset.db")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM students")
    all_students = cursor.fetchall()
    connection.close()
    return render_template("students.html", students=all_students)

@app.route("/add", methods=["GET", "POST"])
def add_student():
    error = None

    if request.method == "POST":
        full_name = request.form["full_name"]
        student_id = request.form["student_id"]
        age = request.form["age"]
        grade = request.form["grade"]

        connection = sqlite3.connect("Studentdataset.db")
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        existing_student = cursor.fetchone()

        if existing_student:
            error = "A student with this ID already exists. Please use a different ID."
            connection.close()
            return render_template("add_student.html", error=error)

        cursor.execute(
            "INSERT INTO students (id, full_name, age, grade) VALUES (?, ?, ?, ?)",
            (student_id, full_name, age, grade)
        )
        connection.commit()
        connection.close()
        return redirect("/students")

    return render_template("add_student.html", error=error)
@app.route("/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    connection = sqlite3.connect("Studentdataset.db")
    cursor = connection.cursor()

    if request.method == "POST":
        full_name = request.form["full_name"]
        age = request.form["age"]
        grade = request.form["grade"]

        cursor.execute(
            "UPDATE students SET full_name = ?, age = ?, grade = ? WHERE id = ?",
            (full_name, age, grade, student_id)
        )
        connection.commit()
        connection.close()
        return redirect("/students")

    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    connection.close()
    return render_template("edit_student.html", student=student)

if __name__ == "__main__":
    app.run(debug=True)