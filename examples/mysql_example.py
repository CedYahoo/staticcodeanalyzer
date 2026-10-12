"""An import-safe example of code that uses a database cursor.

The database connection is supplied by the caller. This sample does not connect
to a database merely because it is imported or analyzed.
"""


def fetch_customers(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM customers")
    return cursor.fetchall()
