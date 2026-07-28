import sqlite3

def create_table():
    connection = sqlite3.connect("Studentdataset.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            grade REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT NOT NULL,
            course_code TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            session_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses (id),
            FOREIGN KEY (teacher_id) REFERENCES teachers (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            classroom_id INTEGER NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (classroom_id) REFERENCES classrooms (id),
            UNIQUE (student_id, classroom_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('teacher', 'student')),
            linked_id INTEGER NOT NULL
        )
    """)

    connection.commit()
    connection.close()
    print("Database and tables created successfully.")

if __name__ == "__main__":
    create_table()