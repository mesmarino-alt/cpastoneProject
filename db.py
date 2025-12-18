import pymysql
import os

def get_db():
    # Support both Railway's MySQL service variables and custom env vars
    db_host = os.getenv('MYSQL_HOST') or os.getenv('DB_HOST', 'localhost')
    db_user = os.getenv('MYSQL_USER') or os.getenv('DB_USER', 'root')
    db_pass = os.getenv('MYSQL_PASSWORD') or os.getenv('DB_PASS', '')
    db_name = os.getenv('MYSQL_DB') or os.getenv('DB_NAME', 'cap_finditfast')
    
    return pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_pass,
        database=db_name,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
