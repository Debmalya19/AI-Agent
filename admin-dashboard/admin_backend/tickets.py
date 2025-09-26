from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import uuid

from .models import db, User
from .models_support import Ticket, TicketComment
from .auth import token_required, admin_required
from .integration import sync_ticket_to_ai_agent

tickets_bp = Blueprint('tickets', __name__)


@tickets_bp.route('/', methods=['GET'])
@token_required
def get_tickets(current_user):
    """Get all tickets with optional filtering"""
    try:
        # Get query parameters for filtering
        status = request.args.get('status')
        priority = request.args.get('priority')
        assignee_id = request.args.get('assignee_id')
        customer_id = request.args.get('customer_id')
        search = request.args.get('search')
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Start with base query
        query = Ticket.query
        
        # Apply filters if provided
        if status:
            query = query.filter(Ticket.status == status)
        if priority:
            query = query.filter(Ticket.priority == priority)
        if assignee_id:
            if assignee_id == 'unassigned':
                query = query.filter(Ticket.assignee_id == None)
            else:
                query = query.filter(Ticket.assignee_id == assignee_id)
        if customer_id:
            query = query.filter(Ticket.customer_id == customer_id)
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                (Ticket.subject.ilike(search_term)) | 
                (Ticket.description.ilike(search_term)) | 
                (Ticket.ticket_id.ilike(search_term))
            )
        
        # Order by created_at descending (newest first)
        query = query.order_by(Ticket.created_at.desc())
        
        # Get paginated results
        tickets_page = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Format the response
        tickets = []
        for ticket in tickets_page.items:
            # Get customer and assignee info
            customer = User.query.get(ticket.customer_id) if ticket.customer_id else None
            assignee = User.query.get(ticket.assignee_id) if ticket.assignee_id else None
            
            ticket_data = ticket.to_dict()
            ticket_data['customer'] = customer.to_dict(minimal=True) if customer else None
            ticket_data['assignee'] = assignee.to_dict(minimal=True) if assignee else None
            
            tickets.append(ticket_data)
        
        return jsonify({
            'tickets': tickets,
            'pagination': {
                'total': tickets_page.total,
                'pages': tickets_page.pages,
                'page': page,
                'per_page': per_page,
                'has_next': tickets_page.has_next,
                'has_prev': tickets_page.has_prev
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error getting tickets: {str(e)}")
        return jsonify({'error': 'Failed to retrieve tickets', 'details': str(e)}), 500


@tickets_bp.route('/<ticket_id>', methods=['GET'])
@token_required
def get_ticket(current_user, ticket_id):
    """Get a specific ticket by ID"""
    try:
        ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Get customer and assignee info
        customer = User.query.get(ticket.customer_id) if ticket.customer_id else None
        assignee = User.query.get(ticket.assignee_id) if ticket.assignee_id else None
        
        # Get comments for this ticket
        comments = TicketComment.query.filter_by(ticket_id=ticket.id).order_by(TicketComment.created_at.asc()).all()
        comments_data = [comment.to_dict() for comment in comments]
        
        ticket_data = ticket.to_dict()
        ticket_data['customer'] = customer.to_dict(minimal=True) if customer else None
        ticket_data['assignee'] = assignee.to_dict(minimal=True) if assignee else None
        ticket_data['comments'] = comments_data
        
        return jsonify(ticket_data), 200
    except Exception as e:
        current_app.logger.error(f"Error getting ticket {ticket_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve ticket', 'details': str(e)}), 500


@tickets_bp.route('/', methods=['POST'])
@token_required
def create_ticket(current_user):
    """Create a new ticket"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['subject', 'description', 'customer_id', 'priority', 'category']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Generate a unique ticket ID
        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        
        # Create new ticket
        new_ticket = Ticket(
            ticket_id=ticket_id,
            subject=data['subject'],
            description=data['description'],
            customer_id=data['customer_id'],
            assignee_id=data.get('assignee_id'),  # Optional
            status='open',  # Default status for new tickets
            priority=data['priority'],
            category=data['category'],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(new_ticket)
        db.session.commit()
        
        # Sync with AI Agent if integration is enabled
        if current_app.config.get('AI_AGENT_INTEGRATION_ENABLED', False):
            try:
                sync_ticket_to_ai_agent(new_ticket.id)
            except Exception as sync_error:
                current_app.logger.error(f"Failed to sync ticket with AI Agent: {str(sync_error)}")
        
        return jsonify(new_ticket.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating ticket: {str(e)}")
        return jsonify({'error': 'Failed to create ticket', 'details': str(e)}), 500


@tickets_bp.route('/<ticket_id>', methods=['PUT'])
@token_required
def update_ticket(current_user, ticket_id):
    """Update an existing ticket"""
    try:
        ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        data = request.get_json()
        
        # Update ticket fields if provided
        if 'subject' in data:
            ticket.subject = data['subject']
        if 'description' in data:
            ticket.description = data['description']
        if 'customer_id' in data:
            ticket.customer_id = data['customer_id']
        if 'assignee_id' in data:
            ticket.assignee_id = data['assignee_id']
        if 'status' in data:
            ticket.status = data['status']
        if 'priority' in data:
            ticket.priority = data['priority']
        if 'category' in data:
            ticket.category = data['category']
        
        # Always update the updated_at timestamp
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Sync with AI Agent if integration is enabled
        if current_app.config.get('AI_AGENT_INTEGRATION_ENABLED', False):
            try:
                sync_ticket_to_ai_agent(ticket.id)
            except Exception as sync_error:
                current_app.logger.error(f"Failed to sync ticket with AI Agent: {str(sync_error)}")
        
        return jsonify(ticket.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating ticket {ticket_id}: {str(e)}")
        return jsonify({'error': 'Failed to update ticket', 'details': str(e)}), 500


@tickets_bp.route('/<ticket_id>', methods=['DELETE'])
@admin_required
def delete_ticket(current_user, ticket_id):
    """Delete a ticket (admin only)"""
    try:
        ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Delete associated comments first
        TicketComment.query.filter_by(ticket_id=ticket.id).delete()
        
        # Delete the ticket
        db.session.delete(ticket)
        db.session.commit()
        
        return jsonify({'message': f'Ticket {ticket_id} deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting ticket {ticket_id}: {str(e)}")
        return jsonify({'error': 'Failed to delete ticket', 'details': str(e)}), 500


@tickets_bp.route('/<ticket_id>/comments', methods=['POST'])
@token_required
def add_comment(current_user, ticket_id):
    """Add a comment to a ticket"""
    try:
        ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        if 'text' not in data:
            return jsonify({'error': 'Comment text is required'}), 400
        
        # Get current user from JWT token
        current_user_id = current_user.id
        
        # Create new comment
        new_comment = TicketComment(
            ticket_id=ticket.id,
            user_id=current_user_id,
            content=data['text'],
            is_internal=data.get('is_internal', False),
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_comment)
        
        # Update ticket's updated_at timestamp
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Sync with AI Agent if integration is enabled and comment is not internal
        if current_app.config.get('AI_AGENT_INTEGRATION_ENABLED', False) and not new_comment.is_internal:
            try:
                sync_ticket_to_ai_agent(ticket.id)
            except Exception as sync_error:
                current_app.logger.error(f"Failed to sync ticket with AI Agent: {str(sync_error)}")
        
        return jsonify(new_comment.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding comment to ticket {ticket_id}: {str(e)}")
        return jsonify({'error': 'Failed to add comment', 'details': str(e)}), 500


@tickets_bp.route('/stats', methods=['GET'])
@token_required
def get_ticket_stats(current_user):
    """Get ticket statistics"""
    try:
        # Total tickets
        total_tickets = Ticket.query.count()
        
        # Tickets by status
        status_counts = {}
        for status in ['open', 'in_progress', 'waiting', 'resolved', 'closed']:
            count = Ticket.query.filter_by(status=status).count()
            status_counts[status] = count
        
        # Tickets by priority
        priority_counts = {}
        for priority in ['low', 'medium', 'high', 'urgent']:
            count = Ticket.query.filter_by(priority=priority).count()
            priority_counts[priority] = count
        
        # Unassigned tickets
        unassigned_count = Ticket.query.filter_by(assignee_id=None).count()
        
        # Recent tickets (last 7 days)
        seven_days_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=7)
        recent_tickets = Ticket.query.filter(Ticket.created_at >= seven_days_ago).count()
        
        return jsonify({
            'total': total_tickets,
            'by_status': status_counts,
            'by_priority': priority_counts,
            'unassigned': unassigned_count,
            'recent': recent_tickets
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error getting ticket stats: {str(e)}")
        return jsonify({'error': 'Failed to retrieve ticket statistics', 'details': str(e)}), 500


@tickets_bp.route('/<ticket_id>/assign', methods=['POST'])
@token_required
def assign_ticket(current_user, ticket_id):
    """Assign a ticket to a user"""
    try:
        ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        data = request.get_json()
        
        # Validate assignee_id
        assignee_id = data.get('assignee_id')
        if assignee_id:
            # Check if user exists
            assignee = User.query.get(assignee_id)
            if not assignee:
                return jsonify({'error': 'Assignee not found'}), 404
        
        # Update ticket assignee
        ticket.assignee_id = assignee_id
        ticket.updated_at = datetime.utcnow()
        
        # If ticket is being assigned and status is 'open', change to 'in_progress'
        if assignee_id and ticket.status == 'open':
            ticket.status = 'in_progress'
        
        db.session.commit()
        
        # Sync with AI Agent if integration is enabled
        if current_app.config.get('AI_AGENT_INTEGRATION_ENABLED', False):
            try:
                sync_ticket_to_ai_agent(ticket.id)
            except Exception as sync_error:
                current_app.logger.error(f"Failed to sync ticket with AI Agent: {str(sync_error)}")
        
        return jsonify(ticket.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error assigning ticket {ticket_id}: {str(e)}")
        return jsonify({'error': 'Failed to assign ticket', 'details': str(e)}), 500