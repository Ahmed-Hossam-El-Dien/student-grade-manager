import sqlite3
def create_table ():
    connection = sqlite3.connect("Studentdataset.db") # Create the database that we willuse by searching for it to and If it is not found I t will be automatically created
    cursor = connection.cursor() # Create a cursor object to execute SQL commands
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            grade REAL NOT NULL
        )
    """)
    connection.commit() # Saves changes permanently to the database
    connection.close() # Close the connection to the database 
    print("Database and table created successfully.")
if __name__ == "__main__":
    create_table()
     # Python gives every file a hidden variable called __name__ when it runs a file. If the file is being run directly, then __name__ will be set to "__main__". If the file is being imported as a module, then __name__ will be set to the name of the module.
     # Therefore we want it only to create a new data set when we run the file directly not every time we import the file It creates new dataset. 