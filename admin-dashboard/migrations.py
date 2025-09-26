from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from admin_backend.app import create_app
from backend.models import db

app = create_app()
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()