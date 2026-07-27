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
    if request.method == "POST":
        full_name = request.form["full_name"]
        age = request.form["age"]
        grade = request.form["grade"]

        connection = sqlite3.connect("Studentdataset.db")
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO students (full_name, age, grade) VALUES (?, ?, ?)",
            (full_name, age, grade)
        )
        connection.commit()
        connection.close()

        return redirect("/students")

    return render_template("add_student.html")

if __name__ == "__main__":
    app.run(debug=True)