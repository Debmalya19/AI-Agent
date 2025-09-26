from flask import Blueprint, request, jsonify, current_app
from models import db
from models_support import Ticket, TicketComment, TicketActivity, ChatSession, ChatMessage, PerformanceMetric, CustomerSatisfaction
from models_support import TicketStatus, TicketPriority, TicketCategory
from auth import token_required, admin_required
from datetime import datetime, timedelta
import random
import os
import sys

# Add the parent directory to sys.path to allow importing from ai-agent backend
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import integration module
from integration import sync_ticket_to_ai_agent, sync_customer_to_ai_agent, AI_AGENT_BACKEND_AVAILABLE

support_bp = Blueprint('support', __name__)

# Ticket Management Endpoints
@support_bp.route('/tickets', methods=['GET'])
@token_required
def get_tickets(current_user):
    """Get all tickets with optional filtering"""
    # Get query parameters for filtering
    status = request.args.get('status')
    priority = request.args.get('priority')
    category = request.args.get('category')
    assigned_to_me = request.args.get('assigned_to_me', 'false').lower() == 'true'
    created_by_me = request.args.get('created_by_me', 'false').lower() == 'true'
    
    # Base query
    query = Ticket.query
    
    # Apply filters
    if status:
        query = query.filter(Ticket.status == TicketStatus(status))
    if priority:
        query = query.filter(Ticket.priority == TicketPriority(priority))
    if category:
        query = query.filter(Ticket.category == TicketCategory(category))
    if assigned_to_me and current_user.is_admin:
        query = query.filter(Ticket.assigned_agent_id == current_user.id)
    if created_by_me:
        query = query.filter(Ticket.customer_id == current_user.id)
    
    # Regular users can only see their own tickets
    if not current_user.is_admin:
        query = query.filter(Ticket.customer_id == current_user.id)
    
    # Get tickets and convert to dict
    tickets = query.order_by(Ticket.created_at.desc()).all()
    return jsonify({
        'success': True,
        'tickets': [ticket.to_dict() for ticket in tickets]
    }), 200

@support_bp.route('/tickets', methods=['POST'])
@token_required
def create_ticket(current_user):
    """Create a new support ticket"""
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ('title', 'description', 'category', 'priority')):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400
    
    try:
        # Create new ticket
        new_ticket = Ticket(
            title=data['title'],
            description=data['description'],
            category=TicketCategory(data['category']),
            priority=TicketPriority(data['priority']),
            customer_id=current_user.id
        )
        
        db.session.add(new_ticket)
        db.session.flush()  # Get the ticket ID without committing
        
        # Log ticket creation activity
        activity = TicketActivity(
            ticket_id=new_ticket.id,
            user_id=current_user.id,
            activity_type='created',
            description=f'Ticket created with {data["priority"]} priority'
        )
        
        db.session.add(activity)
        db.session.commit()
        
        # Sync with ai-agent backend if available
        if AI_AGENT_BACKEND_AVAILABLE:
            try:
                # Sync customer first
                ai_agent_customer = sync_customer_to_ai_agent(current_user)
                
                # Then sync ticket
                ai_agent_ticket = sync_ticket_to_ai_agent(new_ticket)
                
                if ai_agent_ticket:
                    # Update the ticket with the ai-agent ticket ID
                    new_ticket.ai_agent_ticket_id = ai_agent_ticket.id
                    db.session.commit()
            except Exception as e:
                current_app.logger.error(f"Error syncing ticket to ai-agent backend: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Ticket created successfully',
            'ticket': new_ticket.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating ticket: {str(e)}'
        }), 500

@support_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@token_required
def get_ticket(current_user, ticket_id):
    """Get a specific ticket by ID"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check if user has permission to view this ticket
    if not current_user.is_admin and ticket.customer_id != current_user.id:
        return jsonify({
            'success': False,
            'message': 'You do not have permission to view this ticket'
        }), 403
    
    # Get ticket comments
    comments = TicketComment.query.filter_by(ticket_id=ticket_id).order_by(TicketComment.created_at).all()
    
    # Get ticket activities
    activities = TicketActivity.query.filter_by(ticket_id=ticket_id).order_by(TicketActivity.created_at).all()
    
    return jsonify({
        'success': True,
        'ticket': ticket.to_dict(),
        'comments': [comment.to_dict() for comment in comments],
        'activities': [activity.to_dict() for activity in activities]
    }), 200

@support_bp.route('/tickets/<int:ticket_id>', methods=['PUT'])
@token_required
def update_ticket(current_user, ticket_id):
    """Update a ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check if user has permission to update this ticket
    if not current_user.is_admin and ticket.customer_id != current_user.id:
        return jsonify({
            'success': False,
            'message': 'You do not have permission to update this ticket'
        }), 403
    
    data = request.get_json()
    changes = []
    
    try:
        # Update ticket fields
        if 'title' in data and data['title'] != ticket.title:
            old_title = ticket.title
            ticket.title = data['title']
            changes.append(f'Title changed from "{old_title}" to "{data["title"]}"')
        
        if 'description' in data and data['description'] != ticket.description:
            ticket.description = data['description']
            changes.append('Description updated')
        
        if 'status' in data and TicketStatus(data['status']) != ticket.status:
            old_status = ticket.status.value
            ticket.status = TicketStatus(data['status'])
            changes.append(f'Status changed from {old_status} to {data["status"]}')
            
            # If status is resolved, set resolved_at timestamp
            if ticket.status == TicketStatus.RESOLVED and not ticket.resolved_at:
                ticket.resolved_at = datetime.utcnow()
        
        if 'priority' in data and TicketPriority(data['priority']) != ticket.priority:
            old_priority = ticket.priority.value
            ticket.priority = TicketPriority(data['priority'])
            changes.append(f'Priority changed from {old_priority} to {data["priority"]}')
        
        if 'category' in data and TicketCategory(data['category']) != ticket.category:
            old_category = ticket.category.value
            ticket.category = TicketCategory(data['category'])
            changes.append(f'Category changed from {old_category} to {data["category"]}')
        
        if 'assigned_agent_id' in data and data['assigned_agent_id'] != ticket.assigned_agent_id:
            old_agent = ticket.assigned_agent.username if ticket.assigned_agent else 'Unassigned'
            
            if data['assigned_agent_id'] is None:
                ticket.assigned_agent_id = None
                changes.append(f'Ticket unassigned from {old_agent}')
            else:
                ticket.assigned_agent_id = data['assigned_agent_id']
                new_agent = ticket.assigned_agent.username
                changes.append(f'Ticket assigned from {old_agent} to {new_agent}')
        
        # If there were changes, log an activity
        if changes:
            activity = TicketActivity(
                ticket_id=ticket_id,
                user_id=current_user.id,
                activity_type='updated',
                description='\n'.join(changes)
            )
            db.session.add(activity)
        
        db.session.commit()
        
        # Sync with ai-agent backend if available
        if AI_AGENT_BACKEND_AVAILABLE and changes:
            try:
                ai_agent_ticket = sync_ticket_to_ai_agent(ticket)
            except Exception as e:
                current_app.logger.error(f"Error syncing ticket to ai-agent backend: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Ticket updated successfully',
            'ticket': ticket.to_dict(),
            'changes': changes
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating ticket: {str(e)}'
        }), 500

@support_bp.route('/tickets/<int:ticket_id>/comments', methods=['POST'])
@token_required
def add_comment(current_user, ticket_id):
    """Add a comment to a ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check if user has permission to comment on this ticket
    if not current_user.is_admin and ticket.customer_id != current_user.id:
        return jsonify({
            'success': False,
            'message': 'You do not have permission to comment on this ticket'
        }), 403
    
    data = request.get_json()
    
    # Validate required fields
    if 'content' not in data or not data['content'].strip():
        return jsonify({
            'success': False,
            'message': 'Comment content is required'
        }), 400
    
    try:
        # Create new comment
        is_internal = data.get('is_internal', False) and current_user.is_admin
        
        comment = TicketComment(
            ticket_id=ticket_id,
            user_id=current_user.id,
            content=data['content'],
            is_internal=is_internal
        )
        
        db.session.add(comment)
        
        # Log comment activity
        activity_desc = 'Added an internal note' if is_internal else 'Added a comment'
        activity = TicketActivity(
            ticket_id=ticket_id,
            user_id=current_user.id,
            activity_type='commented',
            description=activity_desc
        )
        
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comment added successfully',
            'comment': comment.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error adding comment: {str(e)}'
        }), 500

@support_bp.route('/dashboard/stats', methods=['GET'])
@token_required
@admin_required
def get_dashboard_stats():
    """Get statistics for the support dashboard"""
    try:
        # Get counts by status
        status_counts = {}
        for status in TicketStatus:
            count = Ticket.query.filter_by(status=status).count()
            status_counts[status.value] = count
        
        # Get counts by priority
        priority_counts = {}
        for priority in TicketPriority:
            count = Ticket.query.filter_by(priority=priority).count()
            priority_counts[priority.value] = count
        
        # Get counts by category
        category_counts = {}
        for category in TicketCategory:
            count = Ticket.query.filter_by(category=category).count()
            category_counts[category.value] = count
        
        # Get recent tickets
        recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(5).all()
        
        # Get unassigned tickets count
        unassigned_count = Ticket.query.filter_by(assigned_agent_id=None).count()
        
        # Get tickets created in the last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        tickets_last_week = Ticket.query.filter(Ticket.created_at >= week_ago).count()
        
        # Get tickets resolved in the last 7 days
        resolved_last_week = Ticket.query.filter(
            Ticket.resolved_at >= week_ago,
            Ticket.status == TicketStatus.RESOLVED
        ).count()
        
        # Get average resolution time (in hours) for tickets resolved in the last 30 days
        month_ago = datetime.utcnow() - timedelta(days=30)
        resolved_tickets = Ticket.query.filter(
            Ticket.resolved_at >= month_ago,
            Ticket.status == TicketStatus.RESOLVED
        ).all()
        
        total_resolution_time = 0
        for ticket in resolved_tickets:
            resolution_time = ticket.resolved_at - ticket.created_at
            total_resolution_time += resolution_time.total_seconds() / 3600  # Convert to hours
        
        avg_resolution_time = total_resolution_time / len(resolved_tickets) if resolved_tickets else 0
        
        # Get integration status
        integration_status = {
            'ai_agent_backend_available': AI_AGENT_BACKEND_AVAILABLE
        }
        
        return jsonify({
            'success': True,
            'status_counts': status_counts,
            'priority_counts': priority_counts,
            'category_counts': category_counts,
            'recent_tickets': [ticket.to_dict() for ticket in recent_tickets],
            'unassigned_count': unassigned_count,
            'tickets_last_week': tickets_last_week,
            'resolved_last_week': resolved_last_week,
            'avg_resolution_time': round(avg_resolution_time, 2),
            'integration_status': integration_status
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting dashboard stats: {str(e)}'
        }), 500

@support_bp.route('/system/integration-status', methods=['GET'])
@token_required
@admin_required
def get_integration_status():
    """Get the status of the integration with the ai-agent backend"""
    return jsonify({
        'success': True,
        'ai_agent_backend_available': AI_AGENT_BACKEND_AVAILABLE,
        'message': 'Integration with AI Agent backend is active' if AI_AGENT_BACKEND_AVAILABLE else 'Integration with AI Agent backend is not available'
    }), 200