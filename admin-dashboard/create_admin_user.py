from admin_backend.app import create_app
from admin_backend.models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Check if admin user exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        # Create admin user
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password=generate_password_hash('admin123'),
            full_name='Administrator',
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created: username=admin, password=admin123")
    else:
        print("Admin user already exists")
