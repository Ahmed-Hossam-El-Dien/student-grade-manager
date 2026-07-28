from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import quote
from datetime import date, datetime
import sqlite3

app = Flask(__name__)
app.secret_key = "replace-this-with-your-own-random-secret-string"
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin12345"
def get_connection():
    return sqlite3.connect("Studentdataset.db")
ADMIN_ROUTE_PREFIXES = ["/students", "/teachers", "/courses", "/classrooms", "/add", "/edit", "/delete"]

@app.before_request
def restrict_access():
    if request.path.startswith("/static/"):
        return

    role = session.get("role")
    path = request.path

    is_admin_route = path == "/" or any(
        path == prefix or path.startswith(prefix + "/") for prefix in ADMIN_ROUTE_PREFIXES
    )

    if is_admin_route and role != "admin":
        if role in ("student", "teacher"):
            return redirect(f"/my/{role}")
        return redirect("/login")

# ---------- Dashboard ----------

@app.route("/")
def home():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    student_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM teachers")
    teacher_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM courses")
    course_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM classrooms")
    classroom_count = cursor.fetchone()[0]

    today = date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M")

    cursor.execute("""
        SELECT classrooms.id, courses.course_name, courses.course_code,
               teachers.full_name, classrooms.start_time, classrooms.end_time
        FROM classrooms
        JOIN courses ON classrooms.course_id = courses.id
        JOIN teachers ON classrooms.teacher_id = teachers.id
        WHERE classrooms.session_date = ?
        ORDER BY classrooms.start_time ASC
    """, (today,))
    active_classrooms = []
    for row in cursor.fetchall():
        classroom_id, course_name, course_code, teacher_name, start_time, end_time = row
        is_ongoing = start_time <= now_time <= end_time
        active_classrooms.append({
            "course_name": course_name,
            "course_code": course_code,
            "teacher_name": teacher_name,
            "start_time": start_time,
            "end_time": end_time,
            "is_ongoing": is_ongoing
        })

    cursor.execute("""
        SELECT courses.course_name, COUNT(DISTINCT student_classrooms.student_id)
        FROM courses
        LEFT JOIN classrooms ON classrooms.course_id = courses.id
        LEFT JOIN student_classrooms ON student_classrooms.classroom_id = classrooms.id
        GROUP BY courses.id
        ORDER BY courses.course_name ASC
    """)
    course_stats = cursor.fetchall()
    course_labels = [row[0] for row in course_stats]
    course_counts = [row[1] for row in course_stats]

    cursor.execute("""
        SELECT student_id, full_name, grade FROM students
        ORDER BY grade DESC
        LIMIT 10
    """)
    top_students = cursor.fetchall()

    connection.close()

    return render_template(
        "home.html",
        student_count=student_count,
        teacher_count=teacher_count,
        course_count=course_count,
        classroom_count=classroom_count,
        active_classrooms=active_classrooms,
        course_labels=course_labels,
        course_counts=course_counts,
        top_students=top_students
    )


# ---------- Students ----------

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

    sort_column = f"students.{sort}"

    connection = get_connection()
    cursor = connection.cursor()

    base_query = """
        SELECT students.id, students.student_id, students.full_name,
               students.age, students.grade, users.email
        FROM students
        LEFT JOIN users ON users.role = 'student' AND users.linked_id = students.id
    """

    if search:
        query = base_query + f" WHERE students.full_name LIKE ? OR students.student_id LIKE ? ORDER BY {sort_column} {direction}"
        search_term = f"%{search}%"
        cursor.execute(query, (search_term, search_term))
    else:
        query = base_query + f" ORDER BY {sort_column} {direction}"
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
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
        existing_student = cursor.fetchone()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()

        if existing_student:
            error = "A student with this ID already exists. Please use a different ID."
        elif existing_user:
            error = "This email is already registered to another account."
        else:
            cursor.execute(
                "INSERT INTO students (student_id, full_name, age, grade) VALUES (?, ?, ?, ?)",
                (student_id, full_name, age, grade)
            )
            new_student_id = cursor.lastrowid

            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (email, password_hash, role, linked_id) VALUES (?, ?, ?, ?)",
                (email, password_hash, "student", new_student_id)
            )

            connection.commit()
            connection.close()
            return redirect("/students")

        connection.close()

    return render_template("add_student.html", error=error)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_student(id):
    connection = get_connection()
    cursor = connection.cursor()
    error = None

    cursor.execute("SELECT * FROM users WHERE role = 'student' AND linked_id = ?", (id,))
    existing_user = cursor.fetchone()

    if request.method == "POST":
        student_id = request.form["student_id"]
        full_name = request.form["full_name"]
        age = request.form["age"]
        grade = request.form["grade"]
        email = request.form["email"].strip().lower()
        password = request.form.get("password", "").strip()

        cursor.execute(
            "SELECT * FROM students WHERE student_id = ? AND id != ?",
            (student_id, id)
        )
        duplicate_student = cursor.fetchone()

        cursor.execute(
            "SELECT * FROM users WHERE email = ? AND NOT (role = 'student' AND linked_id = ?)",
            (email, id)
        )
        duplicate_email = cursor.fetchone()

        if duplicate_student:
            error = "Another student already uses this ID. Please choose a different one."
        elif duplicate_email:
            error = "This email is already registered to another account."
        elif not existing_user and not password:
            error = "Please set a password to create this student's login (first time only)."
        else:
            cursor.execute(
                "UPDATE students SET student_id = ?, full_name = ?, age = ?, grade = ? WHERE id = ?",
                (student_id, full_name, age, grade, id)
            )

            if existing_user:
                if password:
                    cursor.execute(
                        "UPDATE users SET email = ?, password_hash = ? WHERE id = ?",
                        (email, generate_password_hash(password), existing_user[0])
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET email = ? WHERE id = ?",
                        (email, existing_user[0])
                    )
            else:
                cursor.execute(
                    "INSERT INTO users (email, password_hash, role, linked_id) VALUES (?, ?, 'student', ?)",
                    (email, generate_password_hash(password), id)
                )

            connection.commit()
            connection.close()
            return redirect("/students")

    cursor.execute("SELECT * FROM students WHERE id = ?", (id,))
    student = cursor.fetchone()
    connection.close()

    student_email = existing_user[1] if existing_user else ""

    return render_template("edit_student.html", student=student, error=error, student_email=student_email)


@app.route("/delete/<int:id>", methods=["POST"])
def delete_student(id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM student_classrooms WHERE student_id = ?", (id,))
    cursor.execute("DELETE FROM users WHERE role = 'student' AND linked_id = ?", (id,))
    cursor.execute("DELETE FROM students WHERE id = ?", (id,))
    connection.commit()
    connection.close()
    return redirect("/students")


# ---------- Teachers ----------

@app.route("/teachers")
def teachers_page():
    error = request.args.get("error")
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT teachers.id, teachers.teacher_id, teachers.full_name, users.email
        FROM teachers
        LEFT JOIN users ON users.role = 'teacher' AND users.linked_id = teachers.id
        ORDER BY teachers.full_name ASC
    """)
    all_teachers = cursor.fetchall()
    connection.close()
    return render_template("teachers.html", teachers=all_teachers, error=error)


@app.route("/teachers/add", methods=["GET", "POST"])
def add_teacher():
    error = None

    if request.method == "POST":
        teacher_id = request.form["teacher_id"].strip()
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM teachers WHERE teacher_id = ?", (teacher_id,))
        existing_teacher = cursor.fetchone()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()

        if existing_teacher:
            error = "A teacher with this ID already exists."
        elif existing_user:
            error = "This email is already registered to another account."
        else:
            cursor.execute(
                "INSERT INTO teachers (teacher_id, full_name) VALUES (?, ?)",
                (teacher_id, full_name)
            )
            new_teacher_id = cursor.lastrowid

            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (email, password_hash, role, linked_id) VALUES (?, ?, ?, ?)",
                (email, password_hash, "teacher", new_teacher_id)
            )

            connection.commit()
            connection.close()
            return redirect("/teachers")

        connection.close()

    return render_template("add_teacher.html", error=error)


@app.route("/teachers/edit/<int:id>", methods=["GET", "POST"])
def edit_teacher(id):
    connection = get_connection()
    cursor = connection.cursor()
    error = None

    cursor.execute("SELECT * FROM users WHERE role = 'teacher' AND linked_id = ?", (id,))
    existing_user = cursor.fetchone()

    if request.method == "POST":
        teacher_id = request.form["teacher_id"].strip()
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form.get("password", "").strip()

        cursor.execute(
            "SELECT * FROM teachers WHERE teacher_id = ? AND id != ?",
            (teacher_id, id)
        )
        duplicate_teacher = cursor.fetchone()

        cursor.execute(
            "SELECT * FROM users WHERE email = ? AND NOT (role = 'teacher' AND linked_id = ?)",
            (email, id)
        )
        duplicate_email = cursor.fetchone()

        if duplicate_teacher:
            error = "Another teacher already uses this ID."
        elif duplicate_email:
            error = "This email is already registered to another account."
        elif not existing_user and not password:
            error = "Please set a password to create this teacher's login (first time only)."
        else:
            cursor.execute(
                "UPDATE teachers SET teacher_id = ?, full_name = ? WHERE id = ?",
                (teacher_id, full_name, id)
            )

            if existing_user:
                if password:
                    cursor.execute(
                        "UPDATE users SET email = ?, password_hash = ? WHERE id = ?",
                        (email, generate_password_hash(password), existing_user[0])
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET email = ? WHERE id = ?",
                        (email, existing_user[0])
                    )
            else:
                cursor.execute(
                    "INSERT INTO users (email, password_hash, role, linked_id) VALUES (?, ?, 'teacher', ?)",
                    (email, generate_password_hash(password), id)
                )

            connection.commit()
            connection.close()
            return redirect("/teachers")

    cursor.execute("SELECT * FROM teachers WHERE id = ?", (id,))
    teacher = cursor.fetchone()
    connection.close()

    teacher_email = existing_user[1] if existing_user else ""

    return render_template("edit_teacher.html", teacher=teacher, error=error, teacher_email=teacher_email)


@app.route("/teachers/delete/<int:id>", methods=["POST"])
def delete_teacher(id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM classrooms WHERE teacher_id = ?", (id,))
    classroom_count = cursor.fetchone()[0]

    if classroom_count > 0:
        connection.close()
        message = f"Cannot delete: this teacher is assigned to {classroom_count} classroom(s)."
        return redirect(f"/teachers?error={quote(message)}")

    cursor.execute("DELETE FROM users WHERE role = 'teacher' AND linked_id = ?", (id,))
    cursor.execute("DELETE FROM teachers WHERE id = ?", (id,))
    connection.commit()
    connection.close()
    return redirect("/teachers")


# ---------- Courses ----------

@app.route("/courses")
def courses_page():
    error = request.args.get("error")
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM courses ORDER BY course_name ASC")
    all_courses = cursor.fetchall()
    connection.close()
    return render_template("courses.html", courses=all_courses, error=error)


@app.route("/courses/add", methods=["GET", "POST"])
def add_course():
    error = None
    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":
        course_name = request.form["course_name"].strip()
        course_code = request.form["course_code"].strip()

        cursor.execute("SELECT * FROM courses WHERE course_code = ?", (course_code,))
        existing_course = cursor.fetchone()

        if existing_course:
            error = "A course with this code already exists."
        else:
            cursor.execute(
                "INSERT INTO courses (course_name, course_code) VALUES (?, ?)",
                (course_name, course_code)
            )
            connection.commit()
            connection.close()
            return redirect("/courses")

    connection.close()
    return render_template("add_course.html", error=error)


@app.route("/courses/edit/<int:id>", methods=["GET", "POST"])
def edit_course(id):
    connection = get_connection()
    cursor = connection.cursor()
    error = None

    if request.method == "POST":
        course_name = request.form["course_name"].strip()
        course_code = request.form["course_code"].strip()

        cursor.execute(
            "SELECT * FROM courses WHERE course_code = ? AND id != ?",
            (course_code, id)
        )
        existing_course = cursor.fetchone()

        if existing_course:
            error = "Another course already uses this code."
        else:
            cursor.execute(
                "UPDATE courses SET course_name = ?, course_code = ? WHERE id = ?",
                (course_name, course_code, id)
            )
            connection.commit()
            connection.close()
            return redirect("/courses")

    cursor.execute("SELECT * FROM courses WHERE id = ?", (id,))
    course = cursor.fetchone()
    connection.close()
    return render_template("edit_course.html", course=course, error=error)


@app.route("/courses/delete/<int:id>", methods=["POST"])
def delete_course(id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM classrooms WHERE course_id = ?", (id,))
    classroom_count = cursor.fetchone()[0]

    if classroom_count > 0:
        connection.close()
        message = f"Cannot delete: this course is used in {classroom_count} classroom(s)."
        return redirect(f"/courses?error={quote(message)}")

    cursor.execute("DELETE FROM courses WHERE id = ?", (id,))
    connection.commit()
    connection.close()
    return redirect("/courses")


# ---------- Classrooms ----------

def times_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a


def find_teacher_conflict(cursor, teacher_id, session_date, start_time, end_time, exclude_classroom_id=None):
    cursor.execute("""
        SELECT id, start_time, end_time FROM classrooms
        WHERE teacher_id = ? AND session_date = ?
    """, (teacher_id, session_date))
    for classroom_id, existing_start, existing_end in cursor.fetchall():
        if exclude_classroom_id and classroom_id == exclude_classroom_id:
            continue
        if times_overlap(start_time, end_time, existing_start, existing_end):
            return classroom_id
    return None


def find_student_conflict(cursor, student_ids, session_date, start_time, end_time, exclude_classroom_id=None):
    for student_id in student_ids:
        cursor.execute("""
            SELECT classrooms.id, classrooms.start_time, classrooms.end_time, students.full_name
            FROM student_classrooms
            JOIN classrooms ON student_classrooms.classroom_id = classrooms.id
            JOIN students ON student_classrooms.student_id = students.id
            WHERE student_classrooms.student_id = ? AND classrooms.session_date = ?
        """, (student_id, session_date))
        for classroom_id, existing_start, existing_end, full_name in cursor.fetchall():
            if exclude_classroom_id and classroom_id == exclude_classroom_id:
                continue
            if times_overlap(start_time, end_time, existing_start, existing_end):
                return full_name
    return None


@app.route("/classrooms")
def classrooms_page():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT classrooms.id, courses.course_name, courses.course_code,
               teachers.full_name, classrooms.session_date,
               classrooms.start_time, classrooms.end_time
        FROM classrooms
        JOIN courses ON classrooms.course_id = courses.id
        JOIN teachers ON classrooms.teacher_id = teachers.id
        ORDER BY classrooms.session_date ASC, classrooms.start_time ASC
    """)
    all_classrooms = cursor.fetchall()

    classrooms_with_students = []
    for classroom in all_classrooms:
        classroom_id = classroom[0]
        cursor.execute("""
            SELECT students.full_name FROM student_classrooms
            JOIN students ON student_classrooms.student_id = students.id
            WHERE student_classrooms.classroom_id = ?
        """, (classroom_id,))
        student_names = [row[0] for row in cursor.fetchall()]
        classrooms_with_students.append((classroom, student_names))

    connection.close()
    return render_template("classrooms.html", classrooms=classrooms_with_students)


@app.route("/classrooms/add", methods=["GET", "POST"])
def add_classroom():
    error = None
    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":
        course_id = int(request.form["course_id"])
        teacher_id = int(request.form["teacher_id"])
        session_date = request.form["session_date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        student_ids = [int(sid) for sid in request.form.getlist("student_ids")]

        if start_time >= end_time:
            error = "End time must be after start time."
        else:
            teacher_conflict = find_teacher_conflict(cursor, teacher_id, session_date, start_time, end_time)
            if teacher_conflict:
                error = "This teacher is already scheduled for another classroom at this time."
            else:
                student_conflict = find_student_conflict(cursor, student_ids, session_date, start_time, end_time)
                if student_conflict:
                    error = f"{student_conflict} is already scheduled for another classroom at this time."

        if not error:
            cursor.execute(
                "INSERT INTO classrooms (course_id, teacher_id, session_date, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
                (course_id, teacher_id, session_date, start_time, end_time)
            )
            classroom_id = cursor.lastrowid

            for student_id in student_ids:
                cursor.execute(
                    "INSERT INTO student_classrooms (student_id, classroom_id) VALUES (?, ?)",
                    (student_id, classroom_id)
                )

            connection.commit()
            connection.close()
            return redirect("/classrooms")

    cursor.execute("SELECT * FROM courses ORDER BY course_name ASC")
    all_courses = cursor.fetchall()
    cursor.execute("SELECT * FROM teachers ORDER BY full_name ASC")
    all_teachers = cursor.fetchall()
    cursor.execute("SELECT * FROM students ORDER BY full_name ASC")
    all_students = cursor.fetchall()
    connection.close()

    return render_template(
        "add_classroom.html",
        error=error,
        courses=all_courses,
        teachers=all_teachers,
        students=all_students
    )


@app.route("/classrooms/edit/<int:id>", methods=["GET", "POST"])
def edit_classroom(id):
    error = None
    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":
        course_id = int(request.form["course_id"])
        teacher_id = int(request.form["teacher_id"])
        session_date = request.form["session_date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        student_ids = [int(sid) for sid in request.form.getlist("student_ids")]

        if start_time >= end_time:
            error = "End time must be after start time."
        else:
            teacher_conflict = find_teacher_conflict(
                cursor, teacher_id, session_date, start_time, end_time, exclude_classroom_id=id
            )
            if teacher_conflict:
                error = "This teacher is already scheduled for another classroom at this time."
            else:
                student_conflict = find_student_conflict(
                    cursor, student_ids, session_date, start_time, end_time, exclude_classroom_id=id
                )
                if student_conflict:
                    error = f"{student_conflict} is already scheduled for another classroom at this time."

        if not error:
            cursor.execute(
                "UPDATE classrooms SET course_id = ?, teacher_id = ?, session_date = ?, start_time = ?, end_time = ? WHERE id = ?",
                (course_id, teacher_id, session_date, start_time, end_time, id)
            )
            cursor.execute("DELETE FROM student_classrooms WHERE classroom_id = ?", (id,))
            for student_id in student_ids:
                cursor.execute(
                    "INSERT INTO student_classrooms (student_id, classroom_id) VALUES (?, ?)",
                    (student_id, id)
                )
            connection.commit()
            connection.close()
            return redirect("/classrooms")

    cursor.execute("SELECT * FROM classrooms WHERE id = ?", (id,))
    classroom = cursor.fetchone()

    cursor.execute("SELECT * FROM courses ORDER BY course_name ASC")
    all_courses = cursor.fetchall()
    cursor.execute("SELECT * FROM teachers ORDER BY full_name ASC")
    all_teachers = cursor.fetchall()
    cursor.execute("SELECT * FROM students ORDER BY full_name ASC")
    all_students = cursor.fetchall()

    cursor.execute("SELECT student_id FROM student_classrooms WHERE classroom_id = ?", (id,))
    enrolled_student_ids = [row[0] for row in cursor.fetchall()]

    connection.close()

    return render_template(
        "edit_classroom.html",
        error=error,
        classroom=classroom,
        courses=all_courses,
        teachers=all_teachers,
        students=all_students,
        enrolled_student_ids=enrolled_student_ids
    )


@app.route("/classrooms/delete/<int:id>", methods=["POST"])
def delete_classroom(id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM student_classrooms WHERE classroom_id = ?", (id,))
    cursor.execute("DELETE FROM classrooms WHERE id = ?", (id,))
    connection.commit()
    connection.close()
    return redirect("/classrooms")


# ---------- Authentication ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["user_id"] = "admin"
            session["role"] = "admin"
            session["linked_id"] = None
            return redirect("/")

        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        connection.close()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["role"] = user[3]
            session["linked_id"] = user[4]

            if user[3] == "student":
                return redirect("/my/student")
            else:
                return redirect("/my/teacher")
        else:
            error = "Invalid email or password."

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/my/student")
def my_student():
    if session.get("role") != "student":
        return redirect("/login")

    linked_id = session["linked_id"]

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM students WHERE id = ?", (linked_id,))
    student = cursor.fetchone()

    today = date.today().isoformat()
    cursor.execute("""
        SELECT courses.course_name, courses.course_code, teachers.full_name,
               classrooms.session_date, classrooms.start_time, classrooms.end_time
        FROM student_classrooms
        JOIN classrooms ON student_classrooms.classroom_id = classrooms.id
        JOIN courses ON classrooms.course_id = courses.id
        JOIN teachers ON classrooms.teacher_id = teachers.id
        WHERE student_classrooms.student_id = ? AND classrooms.session_date >= ?
        ORDER BY classrooms.session_date ASC, classrooms.start_time ASC
    """, (linked_id, today))
    upcoming_classrooms = cursor.fetchall()

    connection.close()

    return render_template("my_student.html", student=student, classrooms=upcoming_classrooms)

@app.route("/my/teacher")
def my_teacher():
    if session.get("role") != "teacher":
        return redirect("/login")

    linked_id = session["linked_id"]

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM teachers WHERE id = ?", (linked_id,))
    teacher = cursor.fetchone()

    today = date.today().isoformat()
    cursor.execute("""
        SELECT classrooms.id, courses.course_name, courses.course_code,
               classrooms.session_date, classrooms.start_time, classrooms.end_time
        FROM classrooms
        JOIN courses ON classrooms.course_id = courses.id
        WHERE classrooms.teacher_id = ? AND classrooms.session_date >= ?
        ORDER BY classrooms.session_date ASC, classrooms.start_time ASC
    """, (linked_id, today))
    upcoming_classrooms = cursor.fetchall()

    connection.close()

    return render_template("my_teacher.html", teacher=teacher, classrooms=upcoming_classrooms)


if __name__ == "__main__":
    app.run(debug=True)