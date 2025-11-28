import pymysql
import os

def get_db():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASS', ''),
        database=os.getenv('DB_NAME', 'cap_finditfast'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
