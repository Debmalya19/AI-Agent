"""
ToolOrchestrator - Intelligent tool selection and execution management.
"""

import asyncio
import time
import logging
import hashlib
from typing import List, Dict, Any, Optional, Callable, Union
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from .models import (
    BaseToolOrchestrator,
    ToolRecommendation,
    ToolResult,
    ContextEntry
)
from .exceptions import ToolExecutionError, ToolSelectionError
from .performance_cache import get_tool_performance_cache, get_performance_cache
from .resource_monitor import get_resource_monitor


class ToolOrchestrator(BaseToolOrchestrator):
    """
    Intelligent tool selection and execution management.
    
    Coordinates tool selection, execution ordering, and parallel processing
    while monitoring performance and handling failures.
    """
    
    def __init__(
        self, 
        tool_selector=None, 
        available_tools: Optional[Dict[str, Union[Callable, Any]]] = None,
        max_concurrent_tools: int = 3,
        default_timeout: float = 30.0,
        analytics_service=None
    ):
        """
        Initialize ToolOrchestrator.
        
        Args:
            tool_selector: Tool selection algorithm instance
            available_tools: Dictionary of available tools (name -> callable/tool)
            max_concurrent_tools: Maximum number of tools to execute concurrently
            default_timeout: Default timeout for tool execution in seconds
            analytics_service: Analytics service for performance tracking
        """
        self.tool_selector = tool_selector
        self.available_tools = available_tools or {}
        self.max_concurrent_tools = max_concurrent_tools
        self.default_timeout = default_timeout
        self.analytics_service = analytics_service
        self.logger = logging.getLogger(__name__)
        
        # Execution statistics and monitoring
        self._execution_stats: Dict[str, Dict[str, Any]] = {}
        self._active_executions: Dict[str, asyncio.Task] = {}
        self._thread_pool = ThreadPoolExecutor(max_workers=max_concurrent_tools)
        
        # Tool dependency mapping
        self._tool_dependencies = {
            "BTWebsiteSearch": [],
            "BTSupportHours": [],
            "BTPlansInformation": [],
            "CreateSupportTicket": ["database_connection"],
            "ComprehensiveAnswerGenerator": ["ContextRetriever"],
            "IntelligentToolOrchestrator": [],
            "ContextRetriever": ["memory_layer"],
            "web_search": [],
            "database_query": ["database_connection"],
            "file_analysis": ["file_access"]
        }
        
        # Tool timeout configurations (in seconds)
        self._tool_timeouts = {
            "BTWebsiteSearch": 15.0,
            "BTSupportHours": 10.0,
            "BTPlansInformation": 15.0,
            "CreateSupportTicket": 5.0,
            "ComprehensiveAnswerGenerator": 30.0,
            "IntelligentToolOrchestrator": 45.0,
            "ContextRetriever": 10.0,
            "web_search": 20.0,
            "database_query": 15.0,
            "file_analysis": 25.0
        }
        
    async def select_tools(self, query: str, context: List[ContextEntry]) -> List[ToolRecommendation]:
        """
        Select relevant tools for a query with performance caching.
        
        Args:
            query: User query to analyze
            context: Conversation context entries
            
        Returns:
            List of tool recommendations sorted by relevance
            
        Raises:
            ToolSelectionError: If tool selection fails
        """
        try:
            if not self.tool_selector:
                return []
            
            # Generate cache key for tool recommendations
            query_hash = self._generate_query_hash(query, context)
            tool_cache = get_tool_performance_cache()
            
            # Check cache first
            cached_recommendations = tool_cache.get_tool_recommendations(query_hash)
            if cached_recommendations:
                self.logger.debug(f"Using cached tool recommendations for query hash: {query_hash}")
                return cached_recommendations
            
            # Get available tool names
            available_tool_names = list(self.available_tools.keys())
            if not available_tool_names:
                return []
            
            # Score tools using the selector with performance data
            tool_scores = await self._score_tools_with_performance(query, available_tool_names, context)
            
            # Convert scores to recommendations
            recommendations = []
            for score in tool_scores:
                recommendation = ToolRecommendation(
                    tool_name=score.tool_name,
                    relevance_score=score.final_score,
                    expected_execution_time=self._estimate_execution_time_with_cache(score.tool_name),
                    confidence_level=min(score.final_score, 1.0),
                    dependencies=self._get_tool_dependencies(score.tool_name),
                    metadata={"reasoning": score.reasoning}
                )
                recommendations.append(recommendation)
            
            # Sort by relevance score
            recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
            
            return recommendations
            
        except Exception as e:
            raise ToolSelectionError(
                f"Failed to select tools for query: {str(e)}",
                query=query,
                available_tools=list(self.available_tools.keys()),
                context={"error": str(e)}
            )
    
    async def execute_tools(
        self, 
        tools: List[str], 
        query: str, 
        context: Dict[str, Any]
    ) -> List[ToolResult]:
        """
        Execute selected tools with dependency resolution and parallel processing.
        
        Args:
            tools: List of tool names to execute
            query: Original user query
            context: Execution context
            
        Returns:
            List of tool execution results
        """
        if not tools:
            return []
        
        try:
            # Resolve dependencies and create execution plan
            execution_plan = self._create_execution_plan(tools)
            self.logger.info(f"Executing tools in order: {execution_plan}")
            
            all_results = []
            
            # Execute tools in batches based on dependencies
            for batch in execution_plan:
                # Process batch in chunks to respect concurrency limits
                for i in range(0, len(batch), self.max_concurrent_tools):
                    chunk = batch[i:i + self.max_concurrent_tools]
                    
                    # Create execution tasks for this chunk
                    tasks = []
                    for tool_name in chunk:
                        if tool_name in self.available_tools:
                            task = self._execute_single_tool_with_timeout(
                                tool_name, query, context, all_results
                            )
                            tasks.append((tool_name, task))
                    
                    if not tasks:
                        continue
                    
                    # Execute chunk in parallel
                    chunk_results = await self._execute_batch(tasks)
                    all_results.extend(chunk_results)
                    
                    # Update analytics if available
                    if self.analytics_service:
                        for result in chunk_results:
                            try:
                                self.analytics_service.record_tool_usage(
                                    tool_name=result.tool_name,
                                    query=query,
                                    success=result.success,
                                    response_quality=0.8 if result.success else 0.2,
                                    response_time=result.execution_time
                                )
                            except Exception as e:
                                self.logger.warning(f"Failed to record analytics for {result.tool_name}: {e}")
            
            return all_results
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            # Return error results for all tools
            error_results = []
            for tool_name in tools:
                error_result = ToolResult(
                    tool_name=tool_name,
                    success=False,
                    result=None,
                    execution_time=0.0,
                    error_message=f"Orchestration failed: {str(e)}"
                )
                error_results.append(error_result)
            
            return error_results
    
    def optimize_execution_order(self, tools: List[ToolRecommendation]) -> List[ToolRecommendation]:
        """
        Optimize tool execution order based on dependencies, performance, and parallelization.
        
        Args:
            tools: List of tool recommendations
            
        Returns:
            Optimized list of tool recommendations
        """
        if not tools:
            return []
        
        try:
            # Create dependency graph
            dependency_graph = {}
            for tool in tools:
                dependency_graph[tool.tool_name] = tool.dependencies
            
            # Topological sort with performance optimization
            optimized_order = self._topological_sort_with_performance(tools, dependency_graph)
            
            return optimized_order
            
        except Exception as e:
            self.logger.warning(f"Failed to optimize execution order: {e}")
            # Fallback to simple sorting
            return sorted(tools, key=lambda t: (-t.relevance_score, t.expected_execution_time))
    
    def _create_execution_plan(self, tools: List[str]) -> List[List[str]]:
        """
        Create execution plan with dependency resolution.
        
        Args:
            tools: List of tool names to execute
            
        Returns:
            List of batches, where each batch can be executed in parallel
        """
        # Build dependency graph for the selected tools
        dependency_graph = {}
        for tool_name in tools:
            dependencies = self._get_tool_dependencies(tool_name)
            # Only include dependencies that are also in the tools list
            filtered_deps = [dep for dep in dependencies if dep in tools]
            dependency_graph[tool_name] = filtered_deps
        
        # Topological sort to create execution batches
        execution_plan = []
        remaining_tools = set(tools)
        
        while remaining_tools:
            # Find tools with no remaining dependencies
            ready_tools = []
            for tool in remaining_tools:
                deps = dependency_graph.get(tool, [])
                if not any(dep in remaining_tools for dep in deps):
                    ready_tools.append(tool)
            
            if not ready_tools:
                # Circular dependency or error - add remaining tools
                self.logger.warning(f"Potential circular dependency detected: {remaining_tools}")
                ready_tools = list(remaining_tools)
            
            execution_plan.append(ready_tools)
            remaining_tools -= set(ready_tools)
        
        return execution_plan
    
    async def _execute_batch(self, tasks: List[tuple]) -> List[ToolResult]:
        """Execute a batch of tools in parallel."""
        try:
            # Execute all tasks in the batch
            results = await asyncio.gather(
                *[task for _, task in tasks], 
                return_exceptions=True
            )
            
            # Process results
            batch_results = []
            for i, (tool_name, _) in enumerate(tasks):
                result = results[i] if i < len(results) else None
                
                if isinstance(result, Exception):
                    tool_result = ToolResult(
                        tool_name=tool_name,
                        success=False,
                        result=None,
                        execution_time=0.0,
                        error_message=str(result)
                    )
                else:
                    tool_result = result
                
                batch_results.append(tool_result)
                self._update_execution_stats(tool_name, tool_result)
            
            return batch_results
            
        except Exception as e:
            self.logger.error(f"Batch execution failed: {e}")
            # Return error results for all tools in batch
            error_results = []
            for tool_name, _ in tasks:
                error_result = ToolResult(
                    tool_name=tool_name,
                    success=False,
                    result=None,
                    execution_time=0.0,
                    error_message=f"Batch execution error: {str(e)}"
                )
                error_results.append(error_result)
            
            return error_results
    
    async def _execute_single_tool_with_timeout(
        self, 
        tool_name: str, 
        query: str, 
        context: Dict[str, Any],
        previous_results: List[ToolResult]
    ) -> ToolResult:
        """Execute a single tool with timeout and dependency context."""
        start_time = time.time()
        timeout = self._tool_timeouts.get(tool_name, self.default_timeout)
        
        try:
            # Get tool function
            tool_function = self.available_tools.get(tool_name)
            
            if not tool_function:
                raise ToolExecutionError(
                    f"Tool '{tool_name}' not found",
                    tool_name=tool_name
                )
            
            # Prepare enhanced context with previous results
            enhanced_context = context.copy()
            enhanced_context["previous_results"] = {
                result.tool_name: result.result 
                for result in previous_results 
                if result.success
            }
            
            # Execute tool with timeout
            try:
                # Check if tool is async or sync
                if asyncio.iscoroutinefunction(tool_function):
                    result = await asyncio.wait_for(
                        tool_function(query), 
                        timeout=timeout
                    )
                else:
                    # Run sync function in thread pool with timeout
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(self._thread_pool, tool_function, query),
                        timeout=timeout
                    )
                
                execution_time = time.time() - start_time
                
                return ToolResult(
                    tool_name=tool_name,
                    success=True,
                    result=result,
                    execution_time=execution_time,
                    metadata={
                        "query": query, 
                        "timeout": timeout,
                        "context_keys": list(enhanced_context.keys())
                    }
                )
                
            except asyncio.TimeoutError:
                execution_time = time.time() - start_time
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    result=None,
                    execution_time=execution_time,
                    error_message=f"Tool execution timed out after {timeout} seconds"
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _topological_sort_with_performance(
        self, 
        tools: List[ToolRecommendation], 
        dependency_graph: Dict[str, List[str]]
    ) -> List[ToolRecommendation]:
        """Perform topological sort with performance optimization."""
        # Create tool lookup
        tool_lookup = {tool.tool_name: tool for tool in tools}
        
        # Kahn's algorithm with performance weighting
        in_degree = {tool.tool_name: 0 for tool in tools}
        
        # Calculate in-degrees - count how many dependencies each tool has
        for tool_name in tool_lookup.keys():
            deps = dependency_graph.get(tool_name, [])
            for dep in deps:
                if dep in tool_lookup:
                    in_degree[tool_name] += 1
        
        # Initialize queue with tools that have no dependencies
        queue = []
        for tool in tools:
            if in_degree[tool.tool_name] == 0:
                queue.append(tool)
        
        # Sort initial queue by performance
        queue.sort(key=lambda t: (-t.relevance_score, t.expected_execution_time))
        
        result = []
        
        while queue:
            # Take the best performing tool with no dependencies
            current_tool = queue.pop(0)
            result.append(current_tool)
            
            # Update in-degrees for tools that depend on the current tool
            current_deps = dependency_graph.get(current_tool.tool_name, [])
            for tool_name in tool_lookup.keys():
                tool_deps = dependency_graph.get(tool_name, [])
                if current_tool.tool_name in tool_deps:
                    in_degree[tool_name] -= 1
                    if in_degree[tool_name] == 0:
                        # Insert in sorted order
                        new_tool = tool_lookup[tool_name]
                        inserted = False
                        for i, queued_tool in enumerate(queue):
                            if (new_tool.relevance_score > queued_tool.relevance_score or
                                (new_tool.relevance_score == queued_tool.relevance_score and
                                 new_tool.expected_execution_time < queued_tool.expected_execution_time)):
                                queue.insert(i, new_tool)
                                inserted = True
                                break
                        if not inserted:
                            queue.append(new_tool)
        
        # If there are remaining tools (circular dependencies), add them
        if len(result) < len(tools):
            remaining_tools = [tool for tool in tools if tool not in result]
            remaining_tools.sort(key=lambda t: (-t.relevance_score, t.expected_execution_time))
            result.extend(remaining_tools)
        
        return result
    
    def _estimate_execution_time(self, tool_name: str) -> float:
        """Estimate execution time for a tool based on historical data."""
        if tool_name in self._execution_stats:
            stats = self._execution_stats[tool_name]
            return stats.get("avg_execution_time", 1.0)
        return 1.0  # Default estimate
    
    def _get_tool_dependencies(self, tool_name: str) -> List[str]:
        """Get dependencies for a tool."""
        return self._tool_dependencies.get(tool_name, [])
    
    def _update_execution_stats(self, tool_name: str, result: ToolResult) -> None:
        """Update execution statistics for a tool."""
        if tool_name not in self._execution_stats:
            self._execution_stats[tool_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "total_execution_time": 0.0,
                "avg_execution_time": 0.0,
                "success_rate": 0.0,
                "last_execution": None
            }
        
        stats = self._execution_stats[tool_name]
        stats["total_executions"] += 1
        stats["total_execution_time"] += result.execution_time
        stats["last_execution"] = time.time()
        
        if result.success:
            stats["successful_executions"] += 1
        
        # Update derived metrics
        stats["avg_execution_time"] = stats["total_execution_time"] / stats["total_executions"]
        stats["success_rate"] = stats["successful_executions"] / stats["total_executions"]
        
        # Update tool selector performance metrics if available
        if self.tool_selector and hasattr(self.tool_selector, 'update_performance_metrics'):
            try:
                self.tool_selector.update_performance_metrics(
                    tool_name=tool_name,
                    query="",  # Query not available in this context
                    success=result.success,
                    execution_time=result.execution_time,
                    response_quality=0.8 if result.success else 0.2
                )
            except Exception as e:
                self.logger.warning(f"Failed to update tool selector metrics: {e}")
    
    def get_execution_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get current execution statistics."""
        return self._execution_stats.copy()
    
    def get_active_executions(self) -> List[str]:
        """Get list of currently active tool executions."""
        return list(self._active_executions.keys())
    
    async def cancel_execution(self, tool_name: str) -> bool:
        """Cancel an active tool execution."""
        if tool_name in self._active_executions:
            task = self._active_executions[tool_name]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._active_executions[tool_name]
            return True
        return False
    
    async def cancel_all_executions(self) -> int:
        """Cancel all active tool executions."""
        cancelled_count = 0
        for tool_name in list(self._active_executions.keys()):
            if await self.cancel_execution(tool_name):
                cancelled_count += 1
        return cancelled_count
    
    def __del__(self):
        """Cleanup resources."""
        try:
            if hasattr(self, '_thread_pool'):
                self._thread_pool.shutdown(wait=False)
        except Exception:
            pass    
    
# Performance optimization helper methods
    
    def _generate_query_hash(self, query: str, context: List[ContextEntry]) -> str:
        """Generate hash for query and context for caching."""
        # Create hash input from query and context
        context_str = "|".join([f"{entry.source}:{entry.content[:100]}" for entry in context[:5]])
        hash_input = f"{query}:{context_str}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    async def _score_tools_with_performance(
        self, 
        query: str, 
        available_tools: List[str], 
        context: List[ContextEntry]
    ) -> List:
        """Score tools using selector with performance data integration."""
        # Get performance cache
        tool_cache = get_tool_performance_cache()
        
        # Score tools using the selector
        tool_scores = self.tool_selector.score_tools(query, available_tools)
        
        # Enhance scores with cached performance data
        for score in tool_scores:
            # Get cached performance metrics
            performance = tool_cache.get_tool_performance(score.tool_name, "general")
            if performance:
                # Adjust score based on historical performance
                performance_factor = (
                    performance['success_rate'] * 0.4 +
                    (1.0 - min(performance['response_time'] / 10.0, 1.0)) * 0.3 +
                    performance['quality_score'] * 0.3
                )
                score.final_score = score.final_score * (0.7 + 0.3 * performance_factor)
        
        # Apply context boosting
        if context:
            tool_scores = self.tool_selector.apply_context_boost(tool_scores, context)
        
        return tool_scores
    
    def _estimate_execution_time_with_cache(self, tool_name: str) -> float:
        """Estimate execution time using cached performance data."""
        tool_cache = get_tool_performance_cache()
        
        # Try to get cached performance data
        performance = tool_cache.get_tool_performance(tool_name, "general")
        if performance and performance['response_time'] > 0:
            return performance['response_time']
        
        # Fallback to local stats
        return self._estimate_execution_time(tool_name)
    
    async def _execute_tool_with_monitoring(
        self, 
        tool_name: str, 
        query: str, 
        context: Dict[str, Any], 
        timeout: float
    ) -> ToolResult:
        """Execute tool with resource monitoring and performance tracking."""
        resource_monitor = get_resource_monitor()
        
        # Monitor tool execution with resource limits
        with resource_monitor.monitor_tool_execution(tool_name, timeout=timeout):
            return await self._execute_single_tool(tool_name, query, context, timeout)
    
    def _cache_tool_recommendations(self, query_hash: str, recommendations: List[ToolRecommendation]) -> None:
        """Cache tool recommendations for future use."""
        tool_cache = get_tool_performance_cache()
        tool_cache.cache_tool_recommendations(query_hash, recommendations)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        tool_cache = get_tool_performance_cache()
        performance_cache = get_performance_cache()
        resource_monitor = get_resource_monitor()
        
        return {
            "execution_stats": self.get_execution_stats(),
            "active_executions": len(self._active_executions),
            "cache_stats": performance_cache.get_stats(),
            "resource_usage": resource_monitor.get_current_usage(),
            "tool_performance_cache_size": len(tool_cache._tool_cache._cache) if hasattr(tool_cache, '_tool_cache') else 0
        }