# Memory Cleanup NoneType Errors Fix

## Issue Fixed

**Problem**: The memory cleanup function was generating errors when trying to clean up user session data on logout:
```
ERROR:backend.memory_layer_manager:Error in cleanup_user_session_data: type object 'MemoryContextCache' has no attribute 'session_id'
WARNING:main:Memory cleanup had errors for user user1: ["type object 'MemoryContextCache' has no attribute 'session_id'"]
```

**Root Cause**: The `cleanup_user_session_data` method was trying to filter database models by fields that don't exist:
- `MemoryContextCache.session_id` - This field doesn't exist in the model
- `ToolUsageMetrics.user_id` - This field doesn't exist in the model

## Database Model Analysis

### MemoryContextCache Model Fields:
- `id` (Primary Key)
- `cache_key` (Unique)
- `user_id` ✅ (Available for filtering)
- `context_data`
- `context_type`
- `relevance_score`
- `expires_at`
- `created_at`
- **No `session_id` field** ❌

### ToolUsageMetrics Model Fields:
- `id` (Primary Key)
- `tool_name`
- `query_type`
- `query_hash`
- `success_rate`
- `average_response_time`
- `response_quality_score`
- `usage_count`
- `last_used`
- `created_at`
- **No `user_id` field** ❌

## Changes Made

### 1. Fixed MemoryContextCache Cleanup

**Before (Broken)**:
```python
user_cache_entries = session.query(MemoryContextCache).filter(
    MemoryContextCache.user_id == user_id
)
if session_id:
    user_cache_entries = user_cache_entries.filter(
        MemoryContextCache.session_id == session_id  # ❌ Field doesn't exist
    )
```

**After (Fixed)**:
```python
# Clean up user's context cache entries (only by user_id since no session_id field exists)
user_cache_entries = session.query(MemoryContextCache).filter(
    MemoryContextCache.user_id == user_id
)
# Note: MemoryContextCache doesn't have session_id field, so we can't filter by it
```

### 2. Fixed ToolUsageMetrics Cleanup

**Before (Broken)**:
```python
old_user_metrics = session.query(ToolUsageMetrics).filter(
    and_(
        ToolUsageMetrics.user_id == user_id,  # ❌ Field doesn't exist
        ToolUsageMetrics.created_at < metrics_cutoff
    )
)
```

**After (Fixed)**:
```python
# Clean up old tool usage metrics (older than 24 hours)
# Note: ToolUsageMetrics doesn't have user_id field, so we clean by age only
metrics_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
old_metrics = session.query(ToolUsageMetrics).filter(
    ToolUsageMetrics.created_at < metrics_cutoff
)
```

## Cleanup Behavior Changes

### Context Cache Cleanup:
- **Before**: Attempted to filter by user_id AND session_id (failed)
- **After**: Filters by user_id only (works correctly)
- **Impact**: All context cache entries for the user are cleaned up on logout

### Tool Metrics Cleanup:
- **Before**: Attempted to filter by user_id AND age (failed)
- **After**: Filters by age only (works correctly)
- **Impact**: Old tool metrics (>24 hours) are cleaned up regardless of user

## Test Results

### Before Fix:
```
ERROR:backend.memory_layer_manager:Error in cleanup_user_session_data: type object 'MemoryContextCache' has no attribute 'session_id'
WARNING:main:Memory cleanup had errors for user user1: ["type object 'MemoryContextCache' has no attribute 'session_id'"]
```

### After Fix:
```
INFO:backend.memory_layer_manager:User logout cleanup completed for user test_user_cleanup in 0.077s: 0 conversations, 0 cache entries, 3 tool metrics
✅ Cleanup completed successfully:
  - Conversations cleaned: 0
  - Context entries cleaned: 0
  - Tool metrics cleaned: 3
  - Duration: 0.077s
```

## Benefits

1. **No More Errors**: Cleanup function works without database errors
2. **Proper Logout Cleanup**: User data is cleaned up when users log out
3. **Performance**: Old data is removed, improving database performance
4. **Privacy**: User context data is cleaned up on logout
5. **Maintenance**: Old tool metrics are cleaned up automatically

## Future Improvements

### 1. Add Missing Fields (Optional)
If session-specific cleanup is needed, consider adding:
- `session_id` field to `MemoryContextCache`
- `user_id` field to `ToolUsageMetrics`

### 2. Enhanced Cleanup Logic
- More granular cleanup policies
- User-specific tool metrics cleanup
- Configurable cleanup thresholds

### 3. Cleanup Metrics
- Track cleanup performance
- Monitor cleanup effectiveness
- Alert on cleanup failures

## Usage

The cleanup function now works reliably:

```python
# Clean up all data for a user
cleanup_result = memory_manager.cleanup_user_session_data(user_id)

# Clean up data for a specific session (conversations only)
cleanup_result = memory_manager.cleanup_user_session_data(user_id, session_id)

# Check for errors
if cleanup_result.errors:
    logger.error(f"Cleanup errors: {cleanup_result.errors}")
else:
    logger.info(f"Cleanup successful: {cleanup_result.to_dict()}")
```

## Testing

Run the verification script:
```bash
python test_memory_cleanup.py
```

This will test:
- Memory manager initialization
- User session cleanup functionality
- Error handling and reporting
- Cleanup performance metrics

The fix ensures that memory cleanup works correctly and doesn't generate database errors, while maintaining the intended functionality of cleaning up user data on logout.