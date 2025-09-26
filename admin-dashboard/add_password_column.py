from admin_backend.app import create_app
from admin_backend.models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Check if password column exists (SQLite compatible)
    try:
        result = db.session.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result.fetchall()]
        if 'password' not in columns:
            # Add password column to users table
            db.session.execute(text('ALTER TABLE users ADD COLUMN password VARCHAR(200) NOT NULL DEFAULT \'\''))
            db.session.commit()
            print("Password column added to users table")
        else:
            print("Password column already exists")
    except Exception as e:
        print(f"Error checking or adding password column: {e}")
        db.session.rollback()
