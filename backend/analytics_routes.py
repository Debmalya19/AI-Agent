"""
Analytics API Routes

FastAPI routes for analytics and monitoring integration endpoints.
These routes provide unified analytics combining AI agent and admin dashboard metrics.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging
from backend.analytics_service import analytics_service
from backend.unified_auth import get_current_user, require_admin_role
from backend.unified_models import UnifiedUser

logger = logging.getLogger(__name__)

# Create analytics router
analytics_router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@analytics_router.get("/unified-dashboard")
async def get_unified_dashboard(
    period: str = Query("week", description="Time period: day, week, month, year"),
    current_user: UnifiedUser = Depends(get_current_user)
):
    """
    Get unified dashboard analytics combining AI agent and admin dashboard metrics
    
    Requirement 5.1: Display AI Agent conversation statistics in admin dashboard
    Requirement 5.2: Include AI Agent interaction history in customer profiles  
    """
    try:
        # Require admin role for analytics access
        require_admin_role(current_user)
        
        # Calculate date range based on period
        end_date = datetime.now(timezone.utc)
        
        if period == "day":
            start_date = end_date - timedelta(days=1)
        elif period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "year":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=7)  # Default to week
        
        # Get unified analytics
        analytics = analytics_service.get_unified_analytics(start_date, end_date)
        
        # Convert to dictionary for JSON response
        analytics_dict = {
            'conversation_metrics': {
                'total_conversations': analytics.conversation_metrics.total_conversations,
                'unique_users': analytics.conversation_metrics.unique_users,
                'avg_conversation_length': round(analytics.conversation_metrics.avg_conversation_length, 2),
                'total_messages': analytics.conversation_metrics.total_messages,
                'success_rate': round(analytics.conversation_metrics.success_rate, 2),
                'tools_used_count': analytics.conversation_metrics.tools_used_count,
                'response_time_avg': round(analytics.conversation_metrics.response_time_avg, 2),
                'error_rate': round(analytics.conversation_metrics.error_rate, 2)
            },
            'ticket_metrics': {
                'total_tickets': analytics.ticket_metrics.total_tickets,
                'open_tickets': analytics.ticket_metrics.open_tickets,
                'resolved_tickets': analytics.ticket_metrics.resolved_tickets,
                'avg_resolution_time': round(analytics.ticket_metrics.avg_resolution_time, 2),
                'tickets_by_priority': analytics.ticket_metrics.tickets_by_priority,
                'tickets_by_category': analytics.ticket_metrics.tickets_by_category,
                'satisfaction_avg': round(analytics.ticket_metrics.satisfaction_avg, 2),
                'first_response_time_avg': round(analytics.ticket_metrics.first_response_time_avg, 2)
            },
            'user_engagement': {
                'active_users_daily': analytics.user_engagement.active_users_daily,
                'active_users_weekly': analytics.user_engagement.active_users_weekly,
                'active_users_monthly': analytics.user_engagement.active_users_monthly,
                'new_users': analytics.user_engagement.new_users,
                'returning_users': analytics.user_engagement.returning_users,
                'user_retention_rate': round(analytics.user_engagement.user_retention_rate, 2),
                'avg_session_duration': round(analytics.user_engagement.avg_session_duration, 2)
            },
            'system_performance': {
                'voice_usage_count': analytics.system_performance.voice_usage_count,
                'voice_success_rate': round(analytics.system_performance.voice_success_rate, 2),
                'avg_voice_duration': round(analytics.system_performance.avg_voice_duration, 2),
                'system_uptime': round(analytics.system_performance.system_uptime, 2),
                'error_count': analytics.system_performance.error_count,
                'response_time_p95': round(analytics.system_performance.response_time_p95, 2)
            },
            'period': {
                'start_date': analytics.period_start.isoformat(),
                'end_date': analytics.period_end.isoformat(),
                'generated_at': analytics.generated_at.isoformat(),
                'period_type': period
            }
        }
        
        return JSONResponse(content={
            'success': True,
            'analytics': analytics_dict
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting unified dashboard analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics data")

@analytics_router.get("/ai-conversations")
async def get_ai_conversation_statistics(
    period: str = Query("week", description="Time period: day, week, month, year"),
    group_by: str = Query("day", description="Group by: hour, day, week, month"),
    current_user: UnifiedUser = Depends(get_current_user)
):
    """
    Get detailed AI agent conversation statistics for dashboard display
    
    Requirement 5.1: Display AI Agent conversation statistics in admin dashboard
    Requirement 5.3: Generate unified reports including AI Agent conversations
    """
    try:
        # Require admin role for analytics access
        require_admin_role(current_user)
        
        # Calculate date range based on period
        end_date = datetime.now(timezone.utc)
        
        if period == "day":
            start_date = end_date - timedelta(days=1)
        elif period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "year":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=7)  # Default to week
        
        # Get AI conversation statistics
        stats = analytics_service.get_ai_agent_conversation_statistics(
            start_date, end_date, group_by
        )
        
        return JSONResponse(content={
            'success': True,
            'conversation_statistics': stats
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI conversation statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation statistics")

@analytics_router.get("/customer/{customer_id}/profile")
async def get_customer_profile_with_ai_history(
    customer_id: int,
    limit: int = Query(50, description="Maximum number of interactions to return"),
    current_user: UnifiedUser = Depends(get_current_user)
):
    """
    Get comprehensive customer profile including AI agent interaction history
    
    Requirement 5.2: Include AI Agent interaction history in customer profiles
    Requirement 5.4: Monitor system performance including AI Agent metrics
    """
    try:
        # Require admin role for customer data access
        require_admin_role(current_user)
        
        # Get customer interaction history
        profile = analytics_service.get_customer_interaction_history(customer_id, limit)
        
        return JSONResponse(content={
            'success': True,
            'customer_profile': profile
        })
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting customer profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get customer profile")

@analytics_router.get("/reports/unified")
async def get_unified_reports(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    report_type: str = Query("summary", description="Report type: summary, detailed, export"),
    current_user: UnifiedUser = Depends(get_current_user)
):
    """
    Generate unified reports across both AI agent and admin dashboard systems
    
    Requirement 5.3: Generate unified reports including data from both systems
    Requirement 5.4: Monitor system performance including AI Agent metrics
    """
    try:
        # Require admin role for reports access
        require_admin_role(current_user)
        
        # Parse dates or use defaults
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_dt = datetime.now(timezone.utc) - timedelta(days=30)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end_dt = datetime.now(timezone.utc)
        
        # Get unified analytics for the report
        analytics = analytics_service.get_unified_analytics(start_dt, end_dt)
        
        # Get detailed conversation statistics
        conversation_stats = analytics_service.get_ai_agent_conversation_statistics(
            start_dt, end_dt, group_by='day'
        )
        
        # Build comprehensive report
        report = {
            'report_metadata': {
                'type': report_type,
                'period': {
                    'start_date': start_dt.isoformat(),
                    'end_date': end_dt.isoformat(),
                    'duration_days': (end_dt - start_dt).days
                },
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'generated_by': current_user.username
            },
            'executive_summary': {
                'total_customer_interactions': (
                    analytics.conversation_metrics.total_conversations + 
                    analytics.ticket_metrics.total_tickets
                ),
                'ai_resolution_rate': analytics.conversation_metrics.success_rate,
                'customer_satisfaction': analytics.ticket_metrics.satisfaction_avg,
                'system_performance_score': (
                    (analytics.system_performance.system_uptime + 
                     analytics.system_performance.voice_success_rate) / 2
                )
            },
            'ai_agent_performance': {
                'conversations': analytics.conversation_metrics.total_conversations,
                'unique_users_served': analytics.conversation_metrics.unique_users,
                'success_rate': analytics.conversation_metrics.success_rate,
                'avg_response_time': analytics.conversation_metrics.response_time_avg,
                'most_used_tools': analytics.conversation_metrics.tools_used_count,
                'voice_interactions': analytics.system_performance.voice_usage_count
            },
            'support_team_performance': {
                'tickets_handled': analytics.ticket_metrics.total_tickets,
                'resolution_rate': (
                    analytics.ticket_metrics.resolved_tickets / 
                    analytics.ticket_metrics.total_tickets * 100
                    if analytics.ticket_metrics.total_tickets > 0 else 0
                ),
                'avg_resolution_time_hours': analytics.ticket_metrics.avg_resolution_time,
                'first_response_time_hours': analytics.ticket_metrics.first_response_time_avg,
                'customer_satisfaction': analytics.ticket_metrics.satisfaction_avg
            },
            'user_engagement_insights': {
                'active_users': {
                    'daily': analytics.user_engagement.active_users_daily,
                    'weekly': analytics.user_engagement.active_users_weekly,
                    'monthly': analytics.user_engagement.active_users_monthly
                },
                'growth': {
                    'new_users': analytics.user_engagement.new_users,
                    'retention_rate': analytics.user_engagement.user_retention_rate
                }
            },
            'system_health': {
                'uptime_percentage': analytics.system_performance.system_uptime,
                'error_count': analytics.system_performance.error_count,
                'performance_metrics': {
                    'response_time_p95': analytics.system_performance.response_time_p95,
                    'voice_success_rate': analytics.system_performance.voice_success_rate
                }
            }
        }
        
        # Add detailed data for detailed reports
        if report_type == "detailed":
            report['detailed_analytics'] = {
                'conversation_trends': conversation_stats['volume_over_time'],
                'tool_usage_breakdown': conversation_stats['tool_usage'],
                'ticket_categories': analytics.ticket_metrics.tickets_by_category,
                'ticket_priorities': analytics.ticket_metrics.tickets_by_priority
            }
        
        return JSONResponse(content={
            'success': True,
            'report': report
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating unified report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

@analytics_router.get("/monitoring/health")
async def get_system_health_metrics(
    current_user: UnifiedUser = Depends(get_current_user)
):
    """
    Get real-time system health metrics for monitoring dashboard
    
    Requirement 5.4: Monitor system performance including AI Agent metrics
    """
    try:
        # Require admin role for system monitoring
        require_admin_role(current_user)
        
        # Get recent system performance (last hour)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=1)
        
        analytics = analytics_service.get_unified_analytics(start_date, end_date)
        
        # Build health status
        health_status = {
            'overall_status': 'healthy',  # Would be calculated based on thresholds
            'components': {
                'ai_agent': {
                    'status': 'healthy' if analytics.conversation_metrics.error_rate < 5 else 'warning',
                    'metrics': {
                        'conversations_last_hour': analytics.conversation_metrics.total_conversations,
                        'success_rate': analytics.conversation_metrics.success_rate,
                        'avg_response_time': analytics.conversation_metrics.response_time_avg,
                        'error_rate': analytics.conversation_metrics.error_rate
                    }
                },
                'support_system': {
                    'status': 'healthy' if analytics.ticket_metrics.first_response_time_avg < 2 else 'warning',
                    'metrics': {
                        'tickets_last_hour': analytics.ticket_metrics.total_tickets,
                        'open_tickets': analytics.ticket_metrics.open_tickets,
                        'avg_response_time': analytics.ticket_metrics.first_response_time_avg
                    }
                },
                'voice_assistant': {
                    'status': 'healthy' if analytics.system_performance.voice_success_rate > 95 else 'warning',
                    'metrics': {
                        'usage_last_hour': analytics.system_performance.voice_usage_count,
                        'success_rate': analytics.system_performance.voice_success_rate,
                        'avg_duration': analytics.system_performance.avg_voice_duration
                    }
                },
                'database': {
                    'status': 'healthy',  # Would be determined by actual DB health checks
                    'metrics': {
                        'connection_pool_usage': 45.2,  # Would be actual metrics
                        'query_performance': 'good',
                        'storage_usage': 67.8
                    }
                }
            },
            'alerts': [],  # Would include active alerts
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Determine overall status based on component statuses
        component_statuses = [comp['status'] for comp in health_status['components'].values()]
        if 'critical' in component_statuses:
            health_status['overall_status'] = 'critical'
        elif 'warning' in component_statuses:
            health_status['overall_status'] = 'warning'
        
        return JSONResponse(content={
            'success': True,
            'health_status': health_status
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system health metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health metrics")

@analytics_router.get("/trends/performance")
async def get_performance_trends(
    days: int = Query(30, description="Number of days to analyze"),
    metric: str = Query("all", description="Specific metric or 'all'"),
    current_user: UnifiedUser = Depends(get_current_user)
):
    """
    Get performance trends over time for monitoring and optimization
    
    Requirement 5.4: Monitor system performance including AI Agent metrics
    """
    try:
        # Require admin role for performance data
        require_admin_role(current_user)
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get conversation statistics with daily grouping
        conversation_trends = analytics_service.get_ai_agent_conversation_statistics(
            start_date, end_date, group_by='day'
        )
        
        # Get daily analytics for trend analysis
        daily_analytics = []
        current_date = start_date
        
        while current_date < end_date:
            day_end = current_date + timedelta(days=1)
            day_analytics = analytics_service.get_unified_analytics(current_date, day_end)
            
            daily_analytics.append({
                'date': current_date.date().isoformat(),
                'ai_success_rate': day_analytics.conversation_metrics.success_rate,
                'ticket_resolution_time': day_analytics.ticket_metrics.avg_resolution_time,
                'user_satisfaction': day_analytics.ticket_metrics.satisfaction_avg,
                'system_performance': day_analytics.system_performance.response_time_p95,
                'voice_success_rate': day_analytics.system_performance.voice_success_rate
            })
            
            current_date = day_end
        
        trends = {
            'period': {
                'start_date': start_date.date().isoformat(),
                'end_date': end_date.date().isoformat(),
                'days': days
            },
            'conversation_volume_trend': conversation_trends['volume_over_time'],
            'performance_trends': daily_analytics,
            'summary': {
                'avg_ai_success_rate': sum(d['ai_success_rate'] for d in daily_analytics) / len(daily_analytics) if daily_analytics else 0,
                'avg_resolution_time': sum(d['ticket_resolution_time'] for d in daily_analytics) / len(daily_analytics) if daily_analytics else 0,
                'avg_satisfaction': sum(d['user_satisfaction'] for d in daily_analytics) / len(daily_analytics) if daily_analytics else 0,
                'trend_direction': 'improving'  # Would be calculated based on actual trend analysis
            }
        }
        
        return JSONResponse(content={
            'success': True,
            'trends': trends
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance trends")