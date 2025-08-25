"""
Tool Usage Analytics Integration Example

This example demonstrates how to integrate the Tool Usage Analytics system
with the existing tool infrastructure to track performance and optimize tool selection.
"""

import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

from tool_usage_analytics import ToolUsageAnalytics
from database import SessionLocal
from memory_models import ToolRecommendationDTO


class EnhancedToolOrchestrator:
    """
    Enhanced tool orchestrator that uses analytics for intelligent tool selection.
    
    This class demonstrates how to integrate the analytics system with existing tools
    to provide data-driven tool recommendations and performance tracking.
    """
    
    def __init__(self):
        """Initialize the enhanced orchestrator with analytics"""
        self.db_session = SessionLocal()
        self.analytics = ToolUsageAnalytics(self.db_session)
        
        # Available tools (simulating the existing tools)
        self.available_tools = [
            "BTWebsiteSearch",
            "BTPlansInformation", 
            "BTSupportHours",
            "ComprehensiveAnswerGenerator",
            "CreateSupportTicket",
            "ContextRetriever",
            "DuckDuckGoSearchRun"
        ]
        
        # Tool execution simulators (for demonstration)
        self.tool_simulators = {
            "BTWebsiteSearch": self._simulate_bt_website_search,
            "BTPlansInformation": self._simulate_bt_plans_info,
            "BTSupportHours": self._simulate_bt_support_hours,
            "ComprehensiveAnswerGenerator": self._simulate_comprehensive_generator,
            "CreateSupportTicket": self._simulate_create_ticket,
            "ContextRetriever": self._simulate_context_retriever,
            "DuckDuckGoSearchRun": self._simulate_web_search
        }
    
    def process_query_with_analytics(self, query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a query using analytics-driven tool selection.
        
        Args:
            query: User query to process
            user_context: Additional context about the user/session
            
        Returns:
            Dictionary containing response and analytics data
        """
        print(f"\n🔍 Processing query: '{query}'")
        
        # Step 1: Get tool recommendations from analytics
        recommendations = self.analytics.get_tool_recommendations(
            query=query,
            available_tools=self.available_tools,
            context=user_context,
            max_recommendations=3
        )
        
        print(f"📊 Analytics recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec.tool_name} (confidence: {rec.confidence_score:.2f})")
            print(f"     Reason: {rec.reason}")
        
        # Step 2: Optimize tool selection order
        optimized_tools = self.analytics.optimize_tool_selection(
            query=query,
            available_tools=self.available_tools,
            context=user_context
        )
        
        print(f"🎯 Optimized tool order: {optimized_tools[:3]}")
        
        # Step 3: Execute tools in optimized order
        results = []
        tools_used = []
        
        for tool_name in optimized_tools[:2]:  # Use top 2 tools
            print(f"\n⚡ Executing {tool_name}...")
            
            # Record start time
            start_time = time.time()
            
            # Execute tool (simulated)
            success, response, quality_score = self._execute_tool(tool_name, query)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Record usage in analytics
            self.analytics.record_tool_usage(
                tool_name=tool_name,
                query=query,
                success=success,
                response_quality=quality_score,
                response_time=execution_time,
                context=user_context
            )
            
            if success:
                results.append({
                    'tool': tool_name,
                    'response': response,
                    'quality': quality_score,
                    'execution_time': execution_time
                })
                tools_used.append(tool_name)
                
                print(f"  ✅ Success (quality: {quality_score:.2f}, time: {execution_time:.2f}s)")
            else:
                print(f"  ❌ Failed")
        
        # Step 4: Combine results and generate final response
        final_response = self._combine_tool_results(results, query)
        
        return {
            'query': query,
            'response': final_response,
            'tools_used': tools_used,
            'recommendations': [rec.to_dict() for rec in recommendations],
            'execution_stats': results
        }
    
    def get_analytics_dashboard(self) -> Dict[str, Any]:
        """Get analytics dashboard data"""
        print("\n📈 Analytics Dashboard")
        print("=" * 50)
        
        # Get usage statistics
        stats = self.analytics.get_usage_statistics(days=30)
        print(f"Total tool usage (30 days): {stats['total_usage']}")
        
        if stats['most_used']:
            print(f"Most used tool: {stats['most_used']}")
        
        # Get performance reports
        performance_reports = self.analytics.analyze_tool_performance(
            time_period=timedelta(days=30)
        )
        
        print(f"\n🏆 Top Performing Tools:")
        for i, report in enumerate(performance_reports[:5], 1):
            print(f"  {i}. {report.tool_name}")
            print(f"     Usage: {report.total_usage}, Success: {report.success_rate:.1%}")
            print(f"     Quality: {report.average_quality_score:.2f}, Trend: {report.trend}")
        
        # Get tool success rates
        print(f"\n📊 Tool Success Rates:")
        for tool in self.available_tools[:5]:
            success_rate = self.analytics.get_tool_success_rate(tool)
            print(f"  {tool}: {success_rate:.1%}")
        
        return {
            'usage_stats': stats,
            'performance_reports': [
                {
                    'tool_name': r.tool_name,
                    'total_usage': r.total_usage,
                    'success_rate': r.success_rate,
                    'quality_score': r.average_quality_score,
                    'trend': r.trend
                } for r in performance_reports
            ]
        }
    
    def _execute_tool(self, tool_name: str, query: str) -> tuple[bool, str, float]:
        """Execute a tool and return success, response, and quality score"""
        if tool_name in self.tool_simulators:
            return self.tool_simulators[tool_name](query)
        else:
            # Default simulation
            return True, f"Response from {tool_name}", random.uniform(0.6, 0.9)
    
    def _combine_tool_results(self, results: List[Dict], query: str) -> str:
        """Combine results from multiple tools into a coherent response"""
        if not results:
            return "I couldn't find information to answer your query."
        
        combined_response = f"Based on analysis using {len(results)} tools:\n\n"
        
        for result in results:
            combined_response += f"From {result['tool']} (quality: {result['quality']:.2f}):\n"
            combined_response += f"{result['response']}\n\n"
        
        return combined_response.strip()
    
    # Tool simulators (for demonstration purposes)
    
    def _simulate_bt_website_search(self, query: str) -> tuple[bool, str, float]:
        """Simulate BT website search"""
        time.sleep(random.uniform(1.0, 3.0))  # Simulate network delay
        
        if "plan" in query.lower() or "pricing" in query.lower():
            return True, "Found BT mobile plans with unlimited data starting from £20/month", random.uniform(0.8, 0.95)
        elif "support" in query.lower():
            return True, "BT customer support is available 24/7 at 0800 800 150", random.uniform(0.7, 0.9)
        else:
            return True, f"General BT information related to: {query}", random.uniform(0.6, 0.8)
    
    def _simulate_bt_plans_info(self, query: str) -> tuple[bool, str, float]:
        """Simulate BT plans information tool"""
        time.sleep(random.uniform(0.5, 2.0))
        
        if "plan" in query.lower():
            return True, "BT offers Essential (£20), Plus (£30), and Max (£40) mobile plans", random.uniform(0.85, 0.95)
        else:
            return False, "No plan information found", 0.0
    
    def _simulate_bt_support_hours(self, query: str) -> tuple[bool, str, float]:
        """Simulate BT support hours tool"""
        time.sleep(random.uniform(0.3, 1.0))
        
        if "support" in query.lower() or "contact" in query.lower():
            return True, "BT customer support: 24/7 on 0800 800 150, online chat available", random.uniform(0.9, 0.98)
        else:
            return False, "Not a support query", 0.0
    
    def _simulate_comprehensive_generator(self, query: str) -> tuple[bool, str, float]:
        """Simulate comprehensive answer generator"""
        time.sleep(random.uniform(2.0, 4.0))  # More complex processing
        return True, f"Comprehensive analysis of '{query}' with multiple data sources", random.uniform(0.75, 0.9)
    
    def _simulate_create_ticket(self, query: str) -> tuple[bool, str, float]:
        """Simulate support ticket creation"""
        time.sleep(random.uniform(0.5, 1.5))
        
        if any(word in query.lower() for word in ['problem', 'issue', 'help', 'error', 'broken']):
            return True, f"Support ticket #{random.randint(1000, 9999)} created for your issue", random.uniform(0.9, 0.98)
        else:
            return False, "No support issue detected", 0.0
    
    def _simulate_context_retriever(self, query: str) -> tuple[bool, str, float]:
        """Simulate context retrieval"""
        time.sleep(random.uniform(0.8, 2.0))
        return True, f"Retrieved relevant context for: {query}", random.uniform(0.7, 0.85)
    
    def _simulate_web_search(self, query: str) -> tuple[bool, str, float]:
        """Simulate web search"""
        time.sleep(random.uniform(1.5, 3.0))
        return True, f"Web search results for: {query}", random.uniform(0.6, 0.8)
    
    def __del__(self):
        """Cleanup database session"""
        if hasattr(self, 'db_session') and self.db_session:
            try:
                self.db_session.close()
            except:
                pass


def run_analytics_demo():
    """Run a demonstration of the analytics system"""
    print("🚀 Tool Usage Analytics Integration Demo")
    print("=" * 60)
    
    orchestrator = EnhancedToolOrchestrator()
    
    # Sample queries to demonstrate different scenarios
    sample_queries = [
        "What are the current BT mobile plans?",
        "I need help with my billing issue",
        "How do I contact BT customer support?",
        "My internet is not working properly",
        "What's the cheapest BT mobile plan?",
        "I want to upgrade my current plan",
        "BT support hours and contact information"
    ]
    
    print("Processing sample queries to build analytics data...\n")
    
    # Process queries to build analytics data
    for i, query in enumerate(sample_queries, 1):
        print(f"Query {i}/{len(sample_queries)}")
        result = orchestrator.process_query_with_analytics(query)
        print(f"Response: {result['response'][:100]}...")
        print("-" * 40)
    
    # Show analytics dashboard
    dashboard = orchestrator.get_analytics_dashboard()
    
    print("\n🎯 Analytics-driven tool recommendations for new query:")
    test_query = "What are BT's premium mobile plans with unlimited data?"
    recommendations = orchestrator.analytics.get_tool_recommendations(
        test_query,
        orchestrator.available_tools,
        max_recommendations=3
    )
    
    for rec in recommendations:
        print(f"  • {rec.tool_name} (confidence: {rec.confidence_score:.2f})")
        print(f"    {rec.reason}")
    
    print(f"\n✨ Demo completed! The analytics system has learned from {len(sample_queries)} queries.")
    print("The system will now provide better tool recommendations based on historical performance.")


if __name__ == "__main__":
    run_analytics_demo()