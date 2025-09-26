"""
Analytics Database Queries

Specialized database queries for generating unified reports across both systems.
These queries are optimized for analytics and reporting performance.
"""

from sqlalchemy import text, func, case, extract, and_, or_
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
import logging
from backend.unified_models import (
    UnifiedUser, UnifiedTicket, UnifiedChatHistory, UnifiedVoiceAnalytics,
    UnifiedPerformanceMetric, UnifiedCustomerSatisfaction, UnifiedChatSession,
    UnifiedChatMessage, UnifiedTicketComment, UnifiedTicketActivity,
    TicketStatus, TicketPriority, TicketCategory, UserRole
)

logger = logging.getLogger(__name__)

class AnalyticsQueries:
    """Optimized database queries for analytics and reporting"""
    
    @staticmethod
    def _get_date_trunc_expression(period: str, column: str = 'created_at', db_type: str = 'sqlite') -> str:
        """
        Get database-specific date truncation expression
        
        Args:
            period: Time period ('hour', 'day', 'week', 'month')
            column: Column name to truncate
            db_type: Database type ('sqlite', 'postgresql')
        """
        if db_type == 'postgresql':
            return f"DATE_TRUNC('{period}', {column})"
        else:  # SQLite
            if period == 'hour':
                return f"datetime({column}, 'start of hour')"
            elif period == 'day':
                return f"date({column})"
            elif period == 'week':
                return f"date({column}, 'weekday 0', '-6 days')"
            elif period == 'month':
                return f"date({column}, 'start of month')"
            else:
                return f"date({column})"
    
    @staticmethod
    def get_conversation_volume_by_period(
        db: Session, 
        start_date: datetime, 
        end_date: datetime,
        period: str = 'day'
    ) -> List[Dict[str, Any]]:
        """
        Get conversation volume grouped by time period with optimized query
        
        Args:
            db: Database session
            start_date: Start of period
            end_date: End of period
            period: Grouping period ('hour', 'day', 'week', 'month')
        """
        try:
            # Get SQLite-compatible date truncation
            date_trunc = AnalyticsQueries._get_date_trunc_expression(period, 'created_at', 'sqlite')
            
            query = text(f"""
                SELECT 
                    {date_trunc} as time_period,
                    COUNT(*) as total_conversations,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT session_id) as unique_sessions,
                    COUNT(CASE WHEN ticket_id IS NOT NULL THEN 1 END) as escalated_conversations,
                    AVG(CASE WHEN tools_used IS NOT NULL THEN 1.0 ELSE 0.0 END) as tool_usage_rate
                FROM unified_chat_history 
                WHERE created_at BETWEEN :start_date AND :end_date
                GROUP BY {date_trunc}
                ORDER BY time_period
            """)
            
            results = db.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            }).fetchall()
            
            return [{
                'time_period': row.time_period if isinstance(row.time_period, str) else row.time_period.isoformat(),
                'total_conversations': row.total_conversations,
                'unique_users': row.unique_users,
                'unique_sessions': row.unique_sessions,
                'escalated_conversations': row.escalated_conversations or 0,
                'success_rate': round(
                    ((row.total_conversations - (row.escalated_conversations or 0)) / 
                     row.total_conversations * 100) if row.total_conversations > 0 else 100, 2
                ),
                'tool_usage_rate': round(float(row.tool_usage_rate or 0) * 100, 2)
            } for row in results]
            
        except Exception as e:
            logger.error(f"Error in conversation volume query: {e}")
            raise
    
    @staticmethod
    def get_ticket_performance_metrics(
        db: Session, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get comprehensive ticket performance metrics with a single optimized query
        """
        try:
            query = text("""
                WITH ticket_stats AS (
                    SELECT 
                        t.id,
                        t.status,
                        t.priority,
                        t.category,
                        t.created_at,
                        t.resolved_at,
                        CASE 
                            WHEN t.resolved_at IS NOT NULL 
                            THEN (julianday(t.resolved_at) - julianday(t.created_at)) * 24 
                            ELSE NULL 
                        END as resolution_time_hours,
                        MIN(tc.created_at) as first_response_time
                    FROM unified_tickets t
                    LEFT JOIN unified_ticket_comments tc ON t.id = tc.ticket_id
                    WHERE t.created_at BETWEEN :start_date AND :end_date
                    GROUP BY t.id, t.status, t.priority, t.category, t.created_at, t.resolved_at
                ),
                satisfaction_stats AS (
                    SELECT 
                        AVG(cs.rating) as avg_satisfaction,
                        COUNT(*) as satisfaction_count
                    FROM unified_customer_satisfaction cs
                    WHERE cs.created_at BETWEEN :start_date AND :end_date
                )
                SELECT 
                    COUNT(*) as total_tickets,
                    COUNT(CASE WHEN status IN ('RESOLVED', 'CLOSED') THEN 1 END) as resolved_tickets,
                    COUNT(CASE WHEN status IN ('OPEN', 'IN_PROGRESS', 'PENDING') THEN 1 END) as open_tickets,
                    AVG(resolution_time_hours) as avg_resolution_time,
                    AVG(CASE 
                        WHEN first_response_time IS NOT NULL 
                        THEN (julianday(first_response_time) - julianday(created_at)) * 24 
                        ELSE NULL 
                    END) as avg_first_response_time,
                    COUNT(CASE WHEN priority = 'CRITICAL' THEN 1 END) as critical_tickets,
                    COUNT(CASE WHEN priority = 'HIGH' THEN 1 END) as high_tickets,
                    COUNT(CASE WHEN priority = 'MEDIUM' THEN 1 END) as medium_tickets,
                    COUNT(CASE WHEN priority = 'LOW' THEN 1 END) as low_tickets,
                    COUNT(CASE WHEN category = 'TECHNICAL' THEN 1 END) as technical_tickets,
                    COUNT(CASE WHEN category = 'BILLING' THEN 1 END) as billing_tickets,
                    COUNT(CASE WHEN category = 'GENERAL' THEN 1 END) as general_tickets,
                    (SELECT avg_satisfaction FROM satisfaction_stats) as avg_satisfaction
                FROM ticket_stats
            """)
            
            result = db.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            }).fetchone()
            
            if not result:
                return {
                    'total_tickets': 0,
                    'resolved_tickets': 0,
                    'open_tickets': 0,
                    'resolution_metrics': {},
                    'priority_distribution': {},
                    'category_distribution': {},
                    'satisfaction': 0.0
                }
            
            return {
                'total_tickets': result.total_tickets or 0,
                'resolved_tickets': result.resolved_tickets or 0,
                'open_tickets': result.open_tickets or 0,
                'resolution_metrics': {
                    'avg_resolution_time_hours': round(float(result.avg_resolution_time or 0), 2),
                    'avg_first_response_time_hours': round(float(result.avg_first_response_time or 0), 2),
                    'resolution_rate': round(
                        ((result.resolved_tickets or 0) / (result.total_tickets or 1) * 100), 2
                    )
                },
                'priority_distribution': {
                    'CRITICAL': result.critical_tickets or 0,
                    'HIGH': result.high_tickets or 0,
                    'MEDIUM': result.medium_tickets or 0,
                    'LOW': result.low_tickets or 0
                },
                'category_distribution': {
                    'TECHNICAL': result.technical_tickets or 0,
                    'BILLING': result.billing_tickets or 0,
                    'GENERAL': result.general_tickets or 0
                },
                'satisfaction': round(float(result.avg_satisfaction or 0), 2)
            }
            
        except Exception as e:
            logger.error(f"Error in ticket performance query: {e}")
            raise
    
    @staticmethod
    def get_user_engagement_analytics(
        db: Session, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get comprehensive user engagement analytics with cohort analysis
        """
        try:
            query = text("""
                WITH user_activity AS (
                    SELECT 
                        u.id,
                        u.created_at as registration_date,
                        u.last_login,
                        u.role,
                        COUNT(DISTINCT ch.session_id) as ai_sessions,
                        COUNT(DISTINCT t.id) as tickets_created,
                        MAX(ch.created_at) as last_ai_interaction,
                        MAX(t.created_at) as last_ticket_creation
                    FROM unified_users u
                    LEFT JOIN unified_chat_history ch ON u.id = ch.user_id 
                        AND ch.created_at BETWEEN :start_date AND :end_date
                    LEFT JOIN unified_tickets t ON u.id = t.customer_id 
                        AND t.created_at BETWEEN :start_date AND :end_date
                    GROUP BY u.id, u.created_at, u.last_login, u.role
                ),
                engagement_metrics AS (
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN last_login >= :start_date THEN 1 END) as active_users,
                        COUNT(CASE WHEN registration_date BETWEEN :start_date AND :end_date THEN 1 END) as new_users,
                        COUNT(CASE WHEN registration_date < :start_date AND last_login >= :start_date THEN 1 END) as returning_users,
                        COUNT(CASE WHEN ai_sessions > 0 THEN 1 END) as ai_users,
                        COUNT(CASE WHEN tickets_created > 0 THEN 1 END) as support_users,
                        AVG(ai_sessions) as avg_ai_sessions_per_user,
                        AVG(tickets_created) as avg_tickets_per_user
                    FROM user_activity
                )
                SELECT * FROM engagement_metrics
            """)
            
            result = db.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            }).fetchone()
            
            if not result:
                return {
                    'total_users': 0,
                    'engagement_summary': {},
                    'user_segments': {},
                    'retention_metrics': {}
                }
            
            # Calculate retention rate
            retention_rate = (
                (result.returning_users / (result.total_users - result.new_users) * 100)
                if (result.total_users - result.new_users) > 0 else 0
            )
            
            return {
                'total_users': result.total_users or 0,
                'engagement_summary': {
                    'active_users': result.active_users or 0,
                    'new_users': result.new_users or 0,
                    'returning_users': result.returning_users or 0,
                    'activity_rate': round(
                        ((result.active_users or 0) / (result.total_users or 1) * 100), 2
                    )
                },
                'user_segments': {
                    'ai_users': result.ai_users or 0,
                    'support_users': result.support_users or 0,
                    'hybrid_users': min(result.ai_users or 0, result.support_users or 0)
                },
                'retention_metrics': {
                    'retention_rate': round(retention_rate, 2),
                    'avg_ai_sessions_per_user': round(float(result.avg_ai_sessions_per_user or 0), 2),
                    'avg_tickets_per_user': round(float(result.avg_tickets_per_user or 0), 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in user engagement query: {e}")
            raise
    
    @staticmethod
    def get_tool_usage_analytics(
        db: Session, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get detailed tool usage analytics from AI agent conversations
        """
        try:
            # Get raw tool usage data
            query = text("""
                SELECT 
                    tools_used,
                    COUNT(*) as usage_count,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT session_id) as unique_sessions,
                    AVG(CASE WHEN ticket_id IS NOT NULL THEN 0 ELSE 1 END) as success_rate
                FROM unified_chat_history 
                WHERE created_at BETWEEN :start_date AND :end_date
                AND tools_used IS NOT NULL 
                AND tools_used != ''
                AND tools_used != '[]'
                GROUP BY tools_used
                ORDER BY usage_count DESC
            """)
            
            results = db.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            }).fetchall()
            
            # Process tool usage data
            tool_stats = {}
            tool_combinations = {}
            
            for result in results:
                try:
                    import json
                    tools = json.loads(result.tools_used) if isinstance(result.tools_used, str) else result.tools_used
                    
                    if isinstance(tools, list):
                        # Individual tool stats
                        for tool in tools:
                            if tool not in tool_stats:
                                tool_stats[tool] = {
                                    'usage_count': 0,
                                    'unique_users': set(),
                                    'unique_sessions': set(),
                                    'success_rates': []
                                }
                            
                            tool_stats[tool]['usage_count'] += result.usage_count
                            tool_stats[tool]['success_rates'].append(result.success_rate)
                        
                        # Tool combination stats
                        if len(tools) > 1:
                            combo_key = ' + '.join(sorted(tools))
                            tool_combinations[combo_key] = {
                                'usage_count': result.usage_count,
                                'success_rate': result.success_rate,
                                'tools': tools
                            }
                            
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Calculate final stats
            processed_tool_stats = {}
            for tool, stats in tool_stats.items():
                processed_tool_stats[tool] = {
                    'usage_count': stats['usage_count'],
                    'avg_success_rate': round(
                        sum(stats['success_rates']) / len(stats['success_rates']) * 100, 2
                    ) if stats['success_rates'] else 0
                }
            
            # Sort by usage
            sorted_tools = dict(sorted(processed_tool_stats.items(), 
                                     key=lambda x: x[1]['usage_count'], reverse=True))
            
            sorted_combinations = dict(sorted(tool_combinations.items(), 
                                            key=lambda x: x[1]['usage_count'], reverse=True))
            
            return {
                'individual_tools': sorted_tools,
                'tool_combinations': dict(list(sorted_combinations.items())[:10]),  # Top 10 combinations
                'summary': {
                    'total_tools_available': len(sorted_tools),
                    'most_used_tool': list(sorted_tools.keys())[0] if sorted_tools else None,
                    'avg_tools_per_conversation': sum(
                        stats['usage_count'] for stats in sorted_tools.values()
                    ) / len(sorted_tools) if sorted_tools else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in tool usage analytics query: {e}")
            raise
    
    @staticmethod
    def get_customer_journey_analytics(
        db: Session, 
        customer_id: int,
        days_back: int = 90
    ) -> Dict[str, Any]:
        """
        Get comprehensive customer journey analytics for a specific customer
        """
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back)
            
            query = text("""
                WITH customer_timeline AS (
                    SELECT 
                        'conversation' as event_type,
                        ch.created_at as event_time,
                        ch.session_id as identifier,
                        ch.user_message as description,
                        ch.tools_used,
                        CASE WHEN ch.ticket_id IS NOT NULL THEN 'escalated' ELSE 'resolved' END as outcome
                    FROM unified_chat_history ch
                    WHERE ch.user_id = :customer_id 
                    AND ch.created_at >= :start_date
                    
                    UNION ALL
                    
                    SELECT 
                        'ticket' as event_type,
                        t.created_at as event_time,
                        CAST(t.id AS VARCHAR) as identifier,
                        t.title as description,
                        NULL as tools_used,
                        t.status::text as outcome
                    FROM unified_tickets t
                    WHERE t.customer_id = :customer_id 
                    AND t.created_at >= :start_date
                    
                    UNION ALL
                    
                    SELECT 
                        'satisfaction' as event_type,
                        cs.created_at as event_time,
                        CAST(cs.ticket_id AS VARCHAR) as identifier,
                        cs.feedback as description,
                        NULL as tools_used,
                        CAST(cs.rating AS VARCHAR) as outcome
                    FROM unified_customer_satisfaction cs
                    WHERE cs.customer_id = :customer_id 
                    AND cs.created_at >= :start_date
                ),
                journey_stats AS (
                    SELECT 
                        COUNT(*) as total_interactions,
                        COUNT(CASE WHEN event_type = 'conversation' THEN 1 END) as ai_interactions,
                        COUNT(CASE WHEN event_type = 'ticket' THEN 1 END) as support_interactions,
                        COUNT(CASE WHEN event_type = 'satisfaction' THEN 1 END) as satisfaction_responses,
                        AVG(CASE WHEN event_type = 'satisfaction' THEN CAST(outcome AS INTEGER) END) as avg_satisfaction
                    FROM customer_timeline
                )
                SELECT 
                    ct.*,
                    js.total_interactions,
                    js.ai_interactions,
                    js.support_interactions,
                    js.satisfaction_responses,
                    js.avg_satisfaction
                FROM customer_timeline ct
                CROSS JOIN journey_stats js
                ORDER BY ct.event_time DESC
            """)
            
            results = db.execute(query, {
                'customer_id': customer_id,
                'start_date': start_date
            }).fetchall()
            
            if not results:
                return {
                    'customer_id': customer_id,
                    'timeline': [],
                    'summary': {
                        'total_interactions': 0,
                        'ai_interactions': 0,
                        'support_interactions': 0,
                        'satisfaction_responses': 0,
                        'avg_satisfaction': 0.0
                    }
                }
            
            # Process timeline
            timeline = []
            summary = None
            
            for row in results:
                timeline.append({
                    'event_type': row.event_type,
                    'event_time': row.event_time.isoformat(),
                    'identifier': row.identifier,
                    'description': row.description,
                    'tools_used': row.tools_used,
                    'outcome': row.outcome
                })
                
                # Summary is the same for all rows, so just take the first one
                if summary is None:
                    summary = {
                        'total_interactions': row.total_interactions or 0,
                        'ai_interactions': row.ai_interactions or 0,
                        'support_interactions': row.support_interactions or 0,
                        'satisfaction_responses': row.satisfaction_responses or 0,
                        'avg_satisfaction': round(float(row.avg_satisfaction or 0), 2)
                    }
            
            return {
                'customer_id': customer_id,
                'period_days': days_back,
                'timeline': timeline,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error in customer journey analytics query: {e}")
            raise
    
    @staticmethod
    def get_system_performance_trends(
        db: Session, 
        start_date: datetime, 
        end_date: datetime,
        group_by: str = 'day'
    ) -> Dict[str, Any]:
        """
        Get system performance trends over time
        """
        try:
            # Determine date truncation
            if group_by == 'hour':
                date_trunc = "DATE_TRUNC('hour', created_at)"
            elif group_by == 'day':
                date_trunc = "DATE_TRUNC('day', created_at)"
            elif group_by == 'week':
                date_trunc = "DATE_TRUNC('week', created_at)"
            else:
                date_trunc = "DATE_TRUNC('day', created_at)"
            
            query = text(f"""
                WITH performance_trends AS (
                    SELECT 
                        {date_trunc} as time_period,
                        COUNT(DISTINCT ch.session_id) as ai_sessions,
                        COUNT(ch.id) as ai_messages,
                        COUNT(CASE WHEN ch.ticket_id IS NOT NULL THEN 1 END) as escalations,
                        COUNT(DISTINCT t.id) as new_tickets,
                        COUNT(CASE WHEN t.resolved_at IS NOT NULL THEN 1 END) as resolved_tickets,
                        AVG(va.duration_ms) as avg_voice_duration,
                        COUNT(CASE WHEN va.error_message IS NOT NULL THEN 1 END) as voice_errors,
                        COUNT(va.id) as voice_interactions
                    FROM unified_chat_history ch
                    FULL OUTER JOIN unified_tickets t ON {date_trunc.replace('ch.created_at', 't.created_at')} = {date_trunc}
                    FULL OUTER JOIN unified_voice_analytics va ON {date_trunc.replace('ch.created_at', 'va.created_at')} = {date_trunc}
                    WHERE ch.created_at BETWEEN :start_date AND :end_date
                    OR t.created_at BETWEEN :start_date AND :end_date
                    OR va.created_at BETWEEN :start_date AND :end_date
                    GROUP BY {date_trunc}
                    ORDER BY time_period
                )
                SELECT 
                    time_period,
                    COALESCE(ai_sessions, 0) as ai_sessions,
                    COALESCE(ai_messages, 0) as ai_messages,
                    COALESCE(escalations, 0) as escalations,
                    COALESCE(new_tickets, 0) as new_tickets,
                    COALESCE(resolved_tickets, 0) as resolved_tickets,
                    COALESCE(avg_voice_duration, 0) as avg_voice_duration,
                    COALESCE(voice_errors, 0) as voice_errors,
                    COALESCE(voice_interactions, 0) as voice_interactions,
                    CASE 
                        WHEN ai_sessions > 0 THEN ROUND((ai_sessions - escalations)::numeric / ai_sessions * 100, 2)
                        ELSE 100 
                    END as ai_success_rate,
                    CASE 
                        WHEN voice_interactions > 0 THEN ROUND((voice_interactions - voice_errors)::numeric / voice_interactions * 100, 2)
                        ELSE 100 
                    END as voice_success_rate
                FROM performance_trends
            """)
            
            results = db.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            }).fetchall()
            
            trends = []
            for row in results:
                trends.append({
                    'time_period': row.time_period.isoformat() if row.time_period else None,
                    'ai_metrics': {
                        'sessions': row.ai_sessions,
                        'messages': row.ai_messages,
                        'escalations': row.escalations,
                        'success_rate': float(row.ai_success_rate or 100)
                    },
                    'support_metrics': {
                        'new_tickets': row.new_tickets,
                        'resolved_tickets': row.resolved_tickets,
                        'resolution_rate': round(
                            (row.resolved_tickets / row.new_tickets * 100) if row.new_tickets > 0 else 0, 2
                        )
                    },
                    'voice_metrics': {
                        'interactions': row.voice_interactions,
                        'avg_duration_ms': float(row.avg_voice_duration or 0),
                        'errors': row.voice_errors,
                        'success_rate': float(row.voice_success_rate or 100)
                    }
                })
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'group_by': group_by
                },
                'trends': trends,
                'summary': {
                    'total_periods': len(trends),
                    'avg_ai_success_rate': round(
                        sum(t['ai_metrics']['success_rate'] for t in trends) / len(trends), 2
                    ) if trends else 0,
                    'avg_voice_success_rate': round(
                        sum(t['voice_metrics']['success_rate'] for t in trends) / len(trends), 2
                    ) if trends else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in system performance trends query: {e}")
            raise

# Global instance for easy access
analytics_queries = AnalyticsQueries()