"""
Social Media Integration Database Migration
Adds social media tables and updates existing tables with social media fields
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from datetime import datetime

# Import models
from backend.social_media_models import SocialMediaPlatform
from backend.models import TicketStatus, TicketPriority, TicketCategory

def upgrade():
    # Create social_media_mentions table
    op.create_table(
        'social_media_mentions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('platform', sa.Enum(SocialMediaPlatform), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('author_handle', sa.String(255), nullable=False),
        sa.Column('author_name', sa.String(255)),
        sa.Column('posted_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=text('CURRENT_TIMESTAMP')),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.customer_id')),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('tickets.id')),
        sa.Column('sentiment_score', sa.Float()),
        sa.Column('urgency_level', sa.Float()),
        sa.Column('extracted_keywords', sa.String(500))
    )
    
    # Create social_media_responses table
    op.create_table(
        'social_media_responses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('mention_id', sa.Integer(), sa.ForeignKey('social_media_mentions.id'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), server_default=text('CURRENT_TIMESTAMP')),
        sa.Column('status', sa.String(50))
    )
    
    # Add social media fields to customers table
    op.add_column('customers', sa.Column('twitter_handle', sa.String(255)))
    
    # Add indices for better query performance
    op.create_index('ix_social_media_mentions_external_id', 'social_media_mentions', ['external_id'])
    op.create_index('ix_social_media_mentions_customer_id', 'social_media_mentions', ['customer_id'])
    op.create_index('ix_social_media_mentions_ticket_id', 'social_media_mentions', ['ticket_id'])
    op.create_index('ix_social_media_mentions_posted_at', 'social_media_mentions', ['posted_at'])
    op.create_index('ix_customers_twitter_handle', 'customers', ['twitter_handle'])

def downgrade():
    # Remove indices
    op.drop_index('ix_customers_twitter_handle')
    op.drop_index('ix_social_media_mentions_posted_at')
    op.drop_index('ix_social_media_mentions_ticket_id')
    op.drop_index('ix_social_media_mentions_customer_id')
    op.drop_index('ix_social_media_mentions_external_id')
    
    # Remove social media fields from customers table
    op.drop_column('customers', 'twitter_handle')
    
    # Drop social media tables
    op.drop_table('social_media_responses')
    op.drop_table('social_media_mentions')