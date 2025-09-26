#!/usr/bin/env python

import click
import random
from datetime import datetime, timedelta
from faker import Faker

from admin_backend.app import create_app
from backend.models import db, User, Ticket, Comment, TicketActivity
from backend.models import TicketStatus, TicketPriority, TicketCategory

app = create_app()
fake = Faker()

@click.command()
@click.option('--users', default=10, help='Number of users to create')
@click.option('--tickets', default=50, help='Number of tickets to create')
@click.option('--comments', default=100, help='Number of comments to create')
@click.option('--reset', is_flag=True, help='Reset database before generating data')
def generate_sample_data(users, tickets, comments, reset):
    """Generate sample data for testing"""
    with app.app_context():
        if reset:
            click.confirm('This will delete all existing data. Continue?', abort=True)
            db.drop_all()
            db.create_all()
            click.echo("Database reset.")
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                full_name='Admin User',
                phone=fake.phone_number(),
                is_admin=True,
                is_active=True,
                created_at=datetime.utcnow()
            )
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            click.echo("Admin user created.")
        
        # Create regular users
        created_users = []
        for i in range(users):
            username = fake.user_name()
            while User.query.filter_by(username=username).first():
                username = fake.user_name()
            
            email = fake.email()
            while User.query.filter_by(email=email).first():
                email = fake.email()
            
            user = User(
                username=username,
                email=email,
                full_name=fake.name(),
                phone=fake.phone_number(),
                is_admin=random.random() < 0.2,  # 20% chance of being admin
                is_active=random.random() < 0.9,  # 90% chance of being active
                created_at=fake.date_time_between(start_date='-1y', end_date='now')
            )
            user.set_password('password')
            db.session.add(user)
            created_users.append(user)
        
        db.session.commit()
        click.echo(f"{len(created_users)} users created.")
        
        # Create tickets
        created_tickets = []
        all_users = User.query.all()
        admin_users = [u for u in all_users if u.is_admin]
        
        for i in range(tickets):
            # Random dates within the last year
            created_at = fake.date_time_between(start_date='-1y', end_date='now')
            updated_at = fake.date_time_between(start_date=created_at, end_date='now')
            
            # Randomly decide if ticket is resolved
            status = random.choice(list(TicketStatus))
            resolved_at = None
            if status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
                resolved_at = fake.date_time_between(start_date=updated_at, end_date='now')
            
            # Random customer and agent
            customer = random.choice(all_users)
            assigned_to = random.choice(admin_users) if random.random() < 0.8 else None  # 80% chance of assignment
            
            ticket = Ticket(
                subject=fake.sentence(),
                description=fake.paragraph(nb_sentences=5),
                status=status,
                priority=random.choice(list(TicketPriority)),
                category=random.choice(list(TicketCategory)),
                customer_id=customer.id,
                assigned_to_id=assigned_to.id if assigned_to else None,
                created_at=created_at,
                updated_at=updated_at,
                resolved_at=resolved_at
            )
            db.session.add(ticket)
            created_tickets.append(ticket)
        
        db.session.commit()
        click.echo(f"{len(created_tickets)} tickets created.")
        
        # Create comments and activities
        for i in range(comments):
            ticket = random.choice(created_tickets)
            user = random.choice(all_users)
            created_at = fake.date_time_between(start_date=ticket.created_at, end_date='now')
            
            # Create comment
            comment = Comment(
                content=fake.paragraph(),
                ticket_id=ticket.id,
                user_id=user.id,
                created_at=created_at,
                is_internal=random.random() < 0.3  # 30% chance of being internal
            )
            db.session.add(comment)
            
            # Create activity
            activity_types = ['comment_added', 'status_changed', 'priority_changed', 'assigned']
            activity = TicketActivity(
                ticket_id=ticket.id,
                user_id=user.id,
                activity_type=random.choice(activity_types),
                description=fake.sentence(),
                created_at=created_at
            )
            db.session.add(activity)
        
        db.session.commit()
        click.echo(f"{comments} comments and activities created.")
        
        click.echo("\nSample data generation complete!")
        click.echo("\nAdmin login:")
        click.echo("Username: admin")
        click.echo("Password: admin")


if __name__ == '__main__':
    generate_sample_data()