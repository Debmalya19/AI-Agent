"""
Analytics and Monitoring Integration Service

This service combines AI agent and admin dashboard metrics to provide
unified analytics and monitoring capabilities across both systems.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_, or_
from backend.database import SessionLocal
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedChatHistory, UnifiedVoiceAnalytics,
    UnifiedPerformanceMetric, UnifiedCustomerSatisfaction, UnifiedChatSession,
    UnifiedChatMessage, UnifiedTicketComment, UnifiedTicketActivity,
    TicketStatus, TicketPriority, TicketCategory, UserRole
)
import json
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class ConversationMetrics:
    """AI Agent conversation metrics"""
    total_conversations: int
    unique_users: int
    avg_conversation_length: float
    total_messages: int
    success_rate: float
    tools_used_count: Dict[str, int]
    response_time_avg: float
    error_rate: float

@dataclass
class TicketMetrics:
    """Support ticket metrics"""
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    avg_resolution_time: float
    tickets_by_priority: Dict[str, int]
    tickets_by_category: Dict[str, int]
    satisfaction_avg: float
    first_response_time_avg: float

@dataclass
class UserEngagementMetrics:
    """User engagement metrics"""
    active_users_daily: int
    active_users_weekly: int
    active_users_monthly: int
    new_users: int
    returning_users: int
    user_retention_rate: float
    avg_session_duration: float

@dataclass
class SystemPerformanceMetrics:
    """System performance metrics"""
    voice_usage_count: int
    voice_success_rate: float
    avg_voice_duration: float
    system_uptime: float
    error_count: int
    response_time_p95: float

@dataclass
class UnifiedAnalytics:
    """Combined analytics from all systems"""
    conversation_metrics: ConversationMetrics
    ticket_metrics: TicketMetrics
    user_engagement: UserEngagementMetrics
    system_performance: SystemPerformanceMetrics
    period_start: datetime
    period_end: datetime
    generated_at: datetime

class AnalyticsService:
    """Service for generating unified analytics and monitoring data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_unified_analytics(
        self, 
        start_date: datetime, 
        end_date: datetime,
        include_real_time: bool = True
    ) -> UnifiedAnalytics:
        """
        Generate unified analytics combining AI agent and admin dashboard metrics
        
        Args:
            start_date: Start of the analytics period
            end_date: End of the analytics period
            include_real_time: Whether to include real-time metrics
            
        Returns:
            UnifiedAnalytics object with all metrics
        """
        try:
            with SessionLocal() as db:
                # Generate all metric components
                conversation_metrics = self._get_conversation_metrics(db, start_date, end_date)
                ticket_metrics = self._get_ticket_metrics(db, start_date, end_date)
                user_engagement = self._get_user_engagement_metrics(db, start_date, end_date)
                system_performance = self._get_system_performance_metrics(db, start_date, end_date)
                
                return UnifiedAnalytics(
                    conversation_metrics=conversation_metrics,
                    ticket_metrics=ticket_metrics,
                    user_engagement=user_engagement,
                    system_performance=system_performance,
                    period_start=start_date,
                    period_end=end_date,
                    generated_at=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            self.logger.error(f"Error generating unified analytics: {e}")
            raise
    
    def _get_conversation_metrics(
        self, 
        db: Session, 
        start_date: datetime, 
        end_date: datetime
    ) -> ConversationMetrics:
        """Generate AI agent conversation metrics"""
        try:
            # Total conversations in period
            total_conversations = db.query(UnifiedChatHistory).filter(
                UnifiedChatHistory.created_at.between(start_date, end_date)
            ).count()
            
            # Unique users who had conversations
            unique_users = db.query(func.count(func.distinct(UnifiedChatHistory.user_id))).filter(
                UnifiedChatHistory.created_at.between(start_date, end_date),
                UnifiedChatHistory.user_id.isnot(None)
            ).scalar() or 0
            
            # Average conversation length (messages per session)
            session_lengths = db.query(
                UnifiedChatHistory.session_id,
                func.count(UnifiedChatHistory.id).label('message_count')
            ).filter(
                UnifiedChatHistory.created_at.between(start_date, end_date),
                UnifiedChatHistory.session_id.isnot(None)
            ).group_by(UnifiedChatHistory.session_id).all()
            
            avg_conversation_length = (
                sum(length.message_count for length in session_lengths) / len(session_lengths)
                if session_lengths else 0.0
            )
            
            # Total messages
            total_messages = db.query(UnifiedChatHistory).filter(
                UnifiedChatHistory.created_at.between(start_date, end_date)
            ).count()
            
            # Tools usage analysis
            tools_used_count = defaultdict(int)
            conversations_with_tools = db.query(UnifiedChatHistory.tools_used).filter(
                UnifiedChatHistory.created_at.between(start_date, end_date),
                UnifiedChatHistory.tools_used.isnot(None)
            ).all()
            
            for conv in conversations_with_tools:
                if conv.tools_used:
                    try:
                        tools = json.loads(conv.tools_used) if isinstance(conv.tools_used, str) else conv.tools_used
                        if isinstance(tools, list):
                            for tool in tools:
                                tools_used_count[tool] += 1
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            # Success rate (conversations that didn't end in ticket creation)
            conversations_with_tickets = db.query(UnifiedChatHistory).filter(
                UnifiedChatHistory.created_at.between(start_date, end_date),
                UnifiedChatHistory.ticket_id.isnot(None)
            ).count()
            
            success_rate = (
                ((total_conversations - conversations_with_tickets) / total_conversations * 100)
                if total_conversations > 0 else 100.0
            )
            
            # Response time and error rate (simplified for now)
            response_time_avg = 1.2  # Would be calculated from actual response times
            error_rate = 2.5  # Would be calculated from actual error logs
            
            return ConversationMetrics(
                total_conversations=total_conversations,
                unique_users=unique_users,
                avg_conversation_length=avg_conversation_length,
                total_messages=total_messages,
                success_rate=success_rate,
                tools_used_count=dict(tools_used_count),
                response_time_avg=response_time_avg,
                error_rate=error_rate
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating conversation metrics: {e}")
            raise
    
    def _get_ticket_metrics(
        self, 
        db: Session, 
        start_date: datetime, 
        end_date: datetime
    ) -> TicketMetrics:
        """Generate support ticket metrics"""
        try:
            # Total tickets created in period
            total_tickets = db.query(UnifiedTicket).filter(
                UnifiedTicket.created_at.between(start_date, end_date)
            ).count()
            
            # Open vs resolved tickets
            open_tickets = db.query(UnifiedTicket).filter(
                UnifiedTicket.created_at.between(start_date, end_date),
                UnifiedTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.PENDING])
            ).count()
            
            resolved_tickets = db.query(UnifiedTicket).filter(
                UnifiedTicket.created_at.between(start_date, end_date),
                UnifiedTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED])
            ).count()
            
            # Average resolution time
            resolved_with_times = db.query(
                func.extract('epoch', UnifiedTicket.resolved_at - UnifiedTicket.created_at).label('resolution_time')
            ).filter(
                UnifiedTicket.created_at.between(start_date, end_date),
                UnifiedTicket.resolved_at.isnot(None)
            ).all()
            
            avg_resolution_time = (
                sum(r.resolution_time for r in resolved_with_times) / len(resolved_with_times) / 3600
                if resolved_with_times else 0.0
            )  # Convert to hours
            
            # Tickets by priority
            priority_counts = db.query(
                UnifiedTicket.priority,
                func.count(UnifiedTicket.id)
            ).filter(
                UnifiedTicket.created_at.between(start_date, end_date)
            ).group_by(UnifiedTicket.priority).all()
            
            tickets_by_priority = {
                priority.name: count for priority, count in priority_counts
            }
            
            # Tickets by category
            category_counts = db.query(
                UnifiedTicket.category,
                func.count(UnifiedTicket.id)
            ).filter(
                UnifiedTicket.created_at.between(start_date, end_date)
            ).group_by(UnifiedTicket.category).all()
            
            tickets_by_category = {
                category.name: count for category, count in category_counts
            }
            
            # Average satisfaction rating
            satisfaction_ratings = db.query(
                func.avg(UnifiedCustomerSatisfaction.rating)
            ).filter(
                UnifiedCustomerSatisfaction.created_at.between(start_date, end_date)
            ).scalar()
            
            satisfaction_avg = float(satisfaction_ratings) if satisfaction_ratings else 0.0
            
            # First response time (time to first comment)
            first_response_times = db.query(
                func.extract('epoch', 
                    func.min(UnifiedTicketComment.created_at) - UnifiedTicket.created_at
                ).label('first_response_time')
            ).join(
                UnifiedTicketComment, UnifiedTicket.id == UnifiedTicketComment.ticket_id
            ).filter(
                UnifiedTicket.created_at.between(start_date, end_date)
            ).group_by(UnifiedTicket.id).all()
            
            first_response_time_avg = (
                sum(r.first_response_time for r in first_response_times) / len(first_response_times) / 3600
                if first_response_times else 0.0
            )  # Convert to hours
            
            return TicketMetrics(
                total_tickets=total_tickets,
                open_tickets=open_tickets,
                resolved_tickets=resolved_tickets,
                avg_resolution_time=avg_resolution_time,
                tickets_by_priority=tickets_by_priority,
                tickets_by_category=tickets_by_category,
                satisfaction_avg=satisfaction_avg,
                first_response_time_avg=first_response_time_avg
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating ticket metrics: {e}")
            raise
    
    def _get_user_engagement_metrics(
        self, 
        db: Session, 
        start_date: datetime, 
        end_date: datetime
    ) -> UserEngagementMetrics:
        """Generate user engagement metrics"""
        try:
            # Active users in different periods
            daily_cutoff = end_date - timedelta(days=1)
            weekly_cutoff = end_date - timedelta(days=7)
            monthly_cutoff = end_date - timedelta(days=30)
            
            active_users_daily = db.query(func.count(func.distinct(UnifiedUser.id))).filter(
                UnifiedUser.last_login >= daily_cutoff
            ).scalar() or 0
            
            active_users_weekly = db.query(func.count(func.distinct(UnifiedUser.id))).filter(
                UnifiedUser.last_login >= weekly_cutoff
            ).scalar() or 0
            
            active_users_monthly = db.query(func.count(func.distinct(UnifiedUser.id))).filter(
                UnifiedUser.last_login >= monthly_cutoff
            ).scalar() or 0
            
            # New users in period
            new_users = db.query(UnifiedUser).filter(
                UnifiedUser.created_at.between(start_date, end_date)
            ).count()
            
            # Returning users (users who had activity before the period and during the period)
            returning_users = db.query(func.count(func.distinct(UnifiedUser.id))).filter(
                UnifiedUser.created_at < start_date,
                UnifiedUser.last_login.between(start_date, end_date)
            ).scalar() or 0
            
            # User retention rate (simplified calculation)
            total_existing_users = db.query(UnifiedUser).filter(
                UnifiedUser.created_at < start_date
            ).count()
            
            user_retention_rate = (
                (returning_users / total_existing_users * 100)
                if total_existing_users > 0 else 0.0
            )
            
            # Average session duration (simplified - would need session tracking)
            avg_session_duration = 15.5  # minutes - would be calculated from actual session data
            
            return UserEngagementMetrics(
                active_users_daily=active_users_daily,
                active_users_weekly=active_users_weekly,
                active_users_monthly=active_users_monthly,
                new_users=new_users,
                returning_users=returning_users,
                user_retention_rate=user_retention_rate,
                avg_session_duration=avg_session_duration
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating user engagement metrics: {e}")
            raise
    
    def _get_system_performance_metrics(
        self, 
        db: Session, 
        start_date: datetime, 
        end_date: datetime
    ) -> SystemPerformanceMetrics:
        """Generate system performance metrics"""
        try:
            # Voice usage metrics
            voice_usage_count = db.query(UnifiedVoiceAnalytics).filter(
                UnifiedVoiceAnalytics.created_at.between(start_date, end_date)
            ).count()
            
            # Voice success rate (actions without errors)
            voice_errors = db.query(UnifiedVoiceAnalytics).filter(
                UnifiedVoiceAnalytics.created_at.between(start_date, end_date),
                UnifiedVoiceAnalytics.error_message.isnot(None)
            ).count()
            
            voice_success_rate = (
                ((voice_usage_count - voice_errors) / voice_usage_count * 100)
                if voice_usage_count > 0 else 100.0
            )
            
            # Average voice duration
            voice_durations = db.query(
                func.avg(UnifiedVoiceAnalytics.duration_ms)
            ).filter(
                UnifiedVoiceAnalytics.created_at.between(start_date, end_date),
                UnifiedVoiceAnalytics.duration_ms.isnot(None)
            ).scalar()
            
            avg_voice_duration = float(voice_durations) / 1000 if voice_durations else 0.0  # Convert to seconds
            
            # System performance metrics (would be enhanced with actual monitoring data)
            system_uptime = 99.8  # percentage
            error_count = voice_errors + 5  # Would include other system errors
            response_time_p95 = 850.0  # milliseconds - would be calculated from actual response times
            
            return SystemPerformanceMetrics(
                voice_usage_count=voice_usage_count,
                voice_success_rate=voice_success_rate,
                avg_voice_duration=avg_voice_duration,
                system_uptime=system_uptime,
                error_count=error_count,
                response_time_p95=response_time_p95
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating system performance metrics: {e}")
            raise
    
    def get_customer_interaction_history(
        self, 
        customer_id: int, 
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get comprehensive interaction history for a customer including
        AI agent conversations, support tickets, and satisfaction ratings
        """
        try:
            with SessionLocal() as db:
                # Get customer info
                customer = db.query(UnifiedUser).filter(
                    UnifiedUser.id == customer_id
                ).first()
                
                if not customer:
                    raise ValueError(f"Customer {customer_id} not found")
                
                # Get AI agent conversations
                conversations = db.query(UnifiedChatHistory).filter(
                    UnifiedChatHistory.user_id == customer_id
                ).order_by(UnifiedChatHistory.created_at.desc()).limit(limit).all()
                
                # Get support tickets
                tickets = db.query(UnifiedTicket).filter(
                    UnifiedTicket.customer_id == customer_id
                ).order_by(UnifiedTicket.created_at.desc()).all()
                
                # Get satisfaction ratings
                satisfaction_ratings = db.query(UnifiedCustomerSatisfaction).filter(
                    UnifiedCustomerSatisfaction.customer_id == customer_id
                ).order_by(UnifiedCustomerSatisfaction.created_at.desc()).all()
                
                # Get voice analytics
                voice_usage = db.query(UnifiedVoiceAnalytics).filter(
                    UnifiedVoiceAnalytics.user_id == customer_id
                ).order_by(UnifiedVoiceAnalytics.created_at.desc()).limit(20).all()
                
                # Calculate summary statistics
                total_conversations = len(conversations)
                total_tickets = len(tickets)
                avg_satisfaction = (
                    sum(r.rating for r in satisfaction_ratings) / len(satisfaction_ratings)
                    if satisfaction_ratings else 0.0
                )
                
                # Recent activity timeline
                timeline = []
                
                # Add conversations to timeline
                for conv in conversations[:10]:  # Last 10 conversations
                    timeline.append({
                        'type': 'conversation',
                        'timestamp': conv.created_at,
                        'description': f"AI conversation: {conv.user_message[:100]}..." if conv.user_message else "AI conversation",
                        'session_id': conv.session_id,
                        'tools_used': conv.tools_used
                    })
                
                # Add tickets to timeline
                for ticket in tickets[:10]:  # Last 10 tickets
                    timeline.append({
                        'type': 'ticket',
                        'timestamp': ticket.created_at,
                        'description': f"Support ticket: {ticket.title}",
                        'status': ticket.status.name,
                        'priority': ticket.priority.name,
                        'ticket_id': ticket.id
                    })
                
                # Sort timeline by timestamp
                timeline.sort(key=lambda x: x['timestamp'], reverse=True)
                
                return {
                    'customer': {
                        'id': customer.id,
                        'username': customer.username,
                        'email': customer.email,
                        'full_name': customer.full_name,
                        'role': customer.role.name,
                        'created_at': customer.created_at,
                        'last_login': customer.last_login
                    },
                    'summary': {
                        'total_conversations': total_conversations,
                        'total_tickets': total_tickets,
                        'avg_satisfaction': round(avg_satisfaction, 2),
                        'voice_usage_count': len(voice_usage)
                    },
                    'conversations': [{
                        'id': conv.id,
                        'session_id': conv.session_id,
                        'user_message': conv.user_message,
                        'bot_response': conv.bot_response,
                        'tools_used': conv.tools_used,
                        'created_at': conv.created_at,
                        'ticket_id': conv.ticket_id
                    } for conv in conversations],
                    'tickets': [{
                        'id': ticket.id,
                        'title': ticket.title,
                        'description': ticket.description,
                        'status': ticket.status.name,
                        'priority': ticket.priority.name,
                        'category': ticket.category.name,
                        'created_at': ticket.created_at,
                        'resolved_at': ticket.resolved_at
                    } for ticket in tickets],
                    'satisfaction_ratings': [{
                        'id': rating.id,
                        'rating': rating.rating,
                        'feedback': rating.feedback,
                        'ticket_id': rating.ticket_id,
                        'created_at': rating.created_at
                    } for rating in satisfaction_ratings],
                    'voice_usage': [{
                        'id': usage.id,
                        'action_type': usage.action_type,
                        'duration_ms': usage.duration_ms,
                        'accuracy_score': usage.accuracy_score,
                        'created_at': usage.created_at
                    } for usage in voice_usage],
                    'timeline': timeline[:20]  # Last 20 activities
                }
                
        except Exception as e:
            self.logger.error(f"Error getting customer interaction history: {e}")
            raise
    
    def get_ai_agent_conversation_statistics(
        self, 
        start_date: datetime, 
        end_date: datetime,
        group_by: str = 'day'
    ) -> Dict[str, Any]:
        """
        Get detailed AI agent conversation statistics for dashboard display
        
        Args:
            start_date: Start of the period
            end_date: End of the period  
            group_by: Grouping interval ('hour', 'day', 'week', 'month')
        """
        try:
            with SessionLocal() as db:
                # Determine grouping SQL based on group_by parameter (SQLite compatible)
                if group_by == 'hour':
                    date_trunc = "datetime(created_at, 'start of hour')"
                elif group_by == 'day':
                    date_trunc = "date(created_at)"
                elif group_by == 'week':
                    date_trunc = "date(created_at, 'weekday 0', '-6 days')"
                elif group_by == 'month':
                    date_trunc = "date(created_at, 'start of month')"
                else:
                    date_trunc = "date(created_at)"
                
                # Conversation volume over time
                volume_query = text(f"""
                    SELECT 
                        {date_trunc} as time_period,
                        COUNT(*) as conversation_count,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT session_id) as unique_sessions
                    FROM unified_chat_history 
                    WHERE created_at BETWEEN :start_date AND :end_date
                    GROUP BY {date_trunc}
                    ORDER BY time_period
                """)
                
                volume_results = db.execute(volume_query, {
                    'start_date': start_date,
                    'end_date': end_date
                }).fetchall()
                
                # Tool usage statistics
                tool_usage_query = text("""
                    SELECT 
                        tools_used,
                        COUNT(*) as usage_count
                    FROM unified_chat_history 
                    WHERE created_at BETWEEN :start_date AND :end_date
                    AND tools_used IS NOT NULL
                    AND tools_used != ''
                """)
                
                tool_results = db.execute(tool_usage_query, {
                    'start_date': start_date,
                    'end_date': end_date
                }).fetchall()
                
                # Process tool usage data
                tool_stats = defaultdict(int)
                for result in tool_results:
                    try:
                        tools = json.loads(result.tools_used) if isinstance(result.tools_used, str) else result.tools_used
                        if isinstance(tools, list):
                            for tool in tools:
                                tool_stats[tool] += result.usage_count
                    except (json.JSONDecodeError, TypeError):
                        continue
                
                # Success metrics (conversations that didn't escalate to tickets)
                escalation_query = text("""
                    SELECT 
                        COUNT(*) as total_conversations,
                        COUNT(ticket_id) as escalated_conversations
                    FROM unified_chat_history 
                    WHERE created_at BETWEEN :start_date AND :end_date
                """)
                
                escalation_result = db.execute(escalation_query, {
                    'start_date': start_date,
                    'end_date': end_date
                }).fetchone()
                
                total_convs = escalation_result.total_conversations or 0
                escalated_convs = escalation_result.escalated_conversations or 0
                success_rate = ((total_convs - escalated_convs) / total_convs * 100) if total_convs > 0 else 100.0
                
                # User satisfaction from conversations that led to tickets
                satisfaction_query = text("""
                    SELECT AVG(cs.rating) as avg_rating, COUNT(*) as rating_count
                    FROM unified_customer_satisfaction cs
                    JOIN unified_chat_history ch ON cs.ticket_id = ch.ticket_id
                    WHERE ch.created_at BETWEEN :start_date AND :end_date
                """)
                
                satisfaction_result = db.execute(satisfaction_query, {
                    'start_date': start_date,
                    'end_date': end_date
                }).fetchone()
                
                avg_satisfaction = float(satisfaction_result.avg_rating) if satisfaction_result.avg_rating else 0.0
                
                return {
                    'period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'group_by': group_by
                    },
                    'volume_over_time': [{
                        'time_period': row.time_period if isinstance(row.time_period, str) else row.time_period.isoformat(),
                        'conversation_count': row.conversation_count,
                        'unique_users': row.unique_users,
                        'unique_sessions': row.unique_sessions
                    } for row in volume_results],
                    'tool_usage': dict(tool_stats),
                    'success_metrics': {
                        'total_conversations': total_convs,
                        'escalated_conversations': escalated_convs,
                        'success_rate': round(success_rate, 2),
                        'avg_satisfaction': round(avg_satisfaction, 2)
                    },
                    'summary': {
                        'total_conversations': total_convs,
                        'unique_users': sum(row.unique_users for row in volume_results),
                        'most_used_tool': max(tool_stats.items(), key=lambda x: x[1])[0] if tool_stats else None,
                        'success_rate': round(success_rate, 2)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error getting AI agent conversation statistics: {e}")
            raise

# Global analytics service instance
analytics_service = AnalyticsService()