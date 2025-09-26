#!/usr/bin/env python

import click
import os
import sys
from datetime import datetime
from flask.cli import FlaskGroup

from admin_backend.app import create_app
from backend.models import db, User, SystemSettings

app = create_app()
cli = FlaskGroup(create_app=lambda: app)


@cli.command('create-admin')
@click.option('--username', prompt=True, help='Admin username')
@click.option('--email', prompt=True, help='Admin email')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@click.option('--full-name', prompt=True, help='Admin full name')
def create_admin(username, email, password, full_name):
    """Create an admin user"""
    try:
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            click.echo(f"Error: User with username '{username}' or email '{email}' already exists.")
            return
        
        # Create new admin user
        admin = User(
            username=username,
            email=email,
            full_name=full_name,
            is_admin=True,
            is_active=True,
            created_at=datetime.utcnow()
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        click.echo(f"Admin user '{username}' created successfully!")
    except Exception as e:
        click.echo(f"Error creating admin user: {str(e)}")
        db.session.rollback()


@cli.command('init-db')
@click.option('--reset', is_flag=True, help='Reset the database before initialization')
def init_db(reset):
    """Initialize the database"""
    try:
        if reset:
            click.confirm('This will delete all data in the database. Continue?', abort=True)
            db.drop_all()
            click.echo("Database tables dropped.")
        
        db.create_all()
        click.echo("Database tables created.")
        
        # Initialize default settings
        default_settings = [
            ('app_name', 'AI Agent Admin Dashboard', 'Application name'),
            ('company_name', 'AI Agent Inc.', 'Company name'),
            ('support_email', 'support@example.com', 'Support email address'),
            ('theme', 'light', 'UI theme (light/dark)'),
            ('items_per_page', '10', 'Default items per page in tables'),
            ('enable_notifications', 'true', 'Enable in-app notifications'),
            ('auto_refresh_interval', '60', 'Dashboard auto-refresh interval in seconds')
        ]
        
        for key, value, description in default_settings:
            setting = SystemSettings.query.filter_by(key=key).first()
            if not setting:
                setting = SystemSettings(key=key, value=value, description=description)
                db.session.add(setting)
        
        db.session.commit()
        click.echo("Default settings initialized.")
        
    except Exception as e:
        click.echo(f"Error initializing database: {str(e)}")
        db.session.rollback()


@cli.command('list-users')
def list_users():
    """List all users"""
    try:
        users = User.query.all()
        
        if not users:
            click.echo("No users found.")
            return
        
        click.echo("\nUsers:")
        click.echo("-" * 80)
        click.echo(f"{'ID':<5} {'Username':<15} {'Email':<25} {'Admin':<8} {'Active':<8} {'Created At':<20}")
        click.echo("-" * 80)
        
        for user in users:
            created_at = user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'N/A'
            click.echo(f"{user.id:<5} {user.username:<15} {user.email:<25} {str(user.is_admin):<8} {str(user.is_active):<8} {created_at:<20}")
        
        click.echo("-" * 80)
        click.echo(f"Total users: {len(users)}")
        
    except Exception as e:
        click.echo(f"Error listing users: {str(e)}")


@cli.command('reset-password')
@click.option('--username', prompt=True, help='Username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='New password')
def reset_password(username, password):
    """Reset a user's password"""
    try:
        user = User.query.filter_by(username=username).first()
        
        if not user:
            click.echo(f"Error: User '{username}' not found.")
            return
        
        user.set_password(password)
        db.session.commit()
        
        click.echo(f"Password for user '{username}' has been reset.")
        
    except Exception as e:
        click.echo(f"Error resetting password: {str(e)}")
        db.session.rollback()


if __name__ == '__main__':
    cli()