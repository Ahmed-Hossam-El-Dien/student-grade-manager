from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/students")
def students():
    search = request.args.get("search", "")
    sort = request.args.get("sort", "id")
    direction = request.args.get("direction", "asc")

    allowed_sort_columns = ["id", "student_id", "full_name", "age", "grade"]
    if sort not in allowed_sort_columns:
        sort = "id"

    if direction not in ["asc", "desc"]:
        direction = "asc"

    connection = sqlite3.connect("Studentdataset.db")
    cursor = connection.cursor()

    if search:
        query = f"""
            SELECT * FROM students
            WHERE full_name LIKE ? OR student_id LIKE ?
            ORDER BY {sort} {direction}
        """
        search_term = f"%{search}%"
        cursor.execute(query, (search_term, search_term))
    else:
        query = f"SELECT * FROM students ORDER BY {sort} {direction}"
        cursor.execute(query)

    all_students = cursor.fetchall()
    connection.close()

    return render_template(
        "students.html",
        students=all_students,
        search=search,
        sort=sort,
        direction=direction
    )

@app.route("/add", methods=["GET", "POST"])
def add_student():
    error = None

    if request.method == "POST":
        student_id = request.form["student_id"]
        full_name = request.form["full_name"]
        age = request.form["age"]
        grade = request.form["grade"]

        connection = sqlite3.connect("Studentdataset.db")
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
        existing_student = cursor.fetchone()

        if existing_student:
            error = "A student with this ID already exists. Please use a different ID."
            connection.close()
            return render_template("add_student.html", error=error)

        cursor.execute(
            "INSERT INTO students (student_id, full_name, age, grade) VALUES (?, ?, ?, ?)",
            (student_id, full_name, age, grade)
        )
        connection.commit()
        connection.close()

        return redirect("/students")

    return render_template("add_student.html", error=error)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_student(id):
    connection = sqlite3.connect("Studentdataset.db")
    cursor = connection.cursor()

    if request.method == "POST":
        student_id = request.form["student_id"]
        full_name = request.form["full_name"]
        age = request.form["age"]
        grade = request.form["grade"]

        cursor.execute(
            "SELECT * FROM students WHERE student_id = ? AND id != ?",
            (student_id, id)
        )
        existing_student = cursor.fetchone()

        if existing_student:
            connection.close()
            error = "Another student already uses this ID. Please choose a different one."
            cursor = sqlite3.connect("Studentdataset.db").cursor()
            cursor.execute("SELECT * FROM students WHERE id = ?", (id,))
            student = cursor.fetchone()
            return render_template("edit_student.html", student=student, error=error)

        cursor.execute(
            "UPDATE students SET student_id = ?, full_name = ?, age = ?, grade = ? WHERE id = ?",
            (student_id, full_name, age, grade, id)
        )
        connection.commit()
        connection.close()
        return redirect("/students")

    cursor.execute("SELECT * FROM students WHERE id = ?", (id,))
    student = cursor.fetchone()
    connection.close()
    return render_template("edit_student.html", student=student)

if __name__ == "__main__":
    app.run(debug=True)