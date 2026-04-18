#!/usr/bin/env python3
"""
Tests for Parallel Executor Tool

Covers:
- Parallel task execution
- Result aggregation
- Task delegation
"""

import json

import pytest


class TestExecuteParallel:
    """Test parallel execution functionality."""
    
    def test_execute_empty_tasks(self):
        """Test error with empty tasks."""
        from tools.parallel_executor_tool import execute_parallel_tool
        result = json.loads(execute_parallel_tool([]))
        
        assert result["success"] is False
        assert result["error_code"] == "EMPTY_TASKS"
    
    def test_execute_too_many_tasks(self):
        """Test error with too many tasks."""
        from tools.parallel_executor_tool import execute_parallel_tool
        
        tasks = [{"id": f"task_{i}", "type": "general"} for i in range(60)]
        result = json.loads(execute_parallel_tool(tasks))
        
        assert result["success"] is False
        assert result["error_code"] == "TOO_MANY_TASKS"
    
    def test_execute_single_task(self):
        """Test executing a single task."""
        from tools.parallel_executor_tool import execute_parallel_tool
        
        tasks = [{"id": "task1", "type": "general", "description": "Test task"}]
        result = json.loads(execute_parallel_tool(tasks))
        
        assert result["success"] is True
        assert result["data"]["summary"]["total_tasks"] == 1
    
    def test_execute_multiple_tasks(self):
        """Test executing multiple tasks."""
        from tools.parallel_executor_tool import execute_parallel_tool
        
        tasks = [
            {"id": "task1", "type": "general", "description": "Task 1"},
            {"id": "task2", "type": "general", "description": "Task 2"},
            {"id": "task3", "type": "general", "description": "Task 3"}
        ]
        result = json.loads(execute_parallel_tool(tasks))
        
        assert result["success"] is True
        assert result["data"]["summary"]["total_tasks"] == 3
    
    def test_execute_with_code_analysis(self):
        """Test executing code analysis task."""
        from tools.parallel_executor_tool import execute_parallel_tool
        
        tasks = [{
            "id": "code1",
            "type": "code_analysis",
            "params": {"code": "print('hello')", "language": "python"}
        }]
        result = json.loads(execute_parallel_tool(tasks))
        
        assert result["success"] is True
        assert result["data"]["results"][0]["result"]["type"] == "code_analysis"
    
    def test_execute_with_calculation(self):
        """Test executing calculation task."""
        from tools.parallel_executor_tool import execute_parallel_tool
        
        tasks = [{
            "id": "calc1",
            "type": "calculation",
            "params": {"expression": "2 + 2"}
        }]
        result = json.loads(execute_parallel_tool(tasks))
        
        assert result["success"] is True
        assert result["data"]["results"][0]["result"]["result"] == 4
    
    def test_execute_calculation_error(self):
        """Test handling calculation error."""
        from tools.parallel_executor_tool import execute_parallel_tool
        
        tasks = [{
            "id": "calc1",
            "type": "calculation",
            "params": {"expression": "invalid syntax @#$"}
        }]
        result = json.loads(execute_parallel_tool(tasks))
        
        assert result["success"] is True
        assert result["data"]["results"][0]["success"] is False


class TestAggregateResults:
    """Test result aggregation."""
    
    def test_aggregate_empty_results(self):
        """Test error with empty results."""
        from tools.parallel_executor_tool import aggregate_results_tool
        result = json.loads(aggregate_results_tool([]))
        
        assert result["success"] is False
        assert result["error_code"] == "EMPTY_RESULTS"
    
    def test_aggregate_summary(self):
        """Test summary aggregation."""
        from tools.parallel_executor_tool import aggregate_results_tool
        
        results = [
            {"success": True, "result": {"data": "value1"}},
            {"success": True, "result": {"data": "value2"}},
            {"success": False, "error": "Some error"}
        ]
        result = json.loads(aggregate_results_tool(results, "summary"))
        
        assert result["success"] is True
        assert result["data"]["successful"] == 2
        assert result["data"]["failed"] == 1
    
    def test_aggregate_merge(self):
        """Test merge aggregation."""
        from tools.parallel_executor_tool import aggregate_results_tool
        
        results = [
            {"result": {"key1": "value1"}},
            {"result": {"key2": "value2"}}
        ]
        result = json.loads(aggregate_results_tool(results, "merge"))
        
        assert result["success"] is True
        assert "key1" in result["data"]["merged"]
        assert "key2" in result["data"]["merged"]
    
    def test_aggregate_filter_errors(self):
        """Test filter_errors aggregation."""
        from tools.parallel_executor_tool import aggregate_results_tool
        
        results = [
            {"success": True, "result": {"data": "value1"}},
            {"success": False, "error": "Error"},
            {"success": True, "result": {"data": "value2"}}
        ]
        result = json.loads(aggregate_results_tool(results, "filter_errors"))
        
        assert result["success"] is True
        assert result["data"]["filtered_count"] == 2
        assert result["data"]["errors_removed"] == 1
    
    def test_aggregate_invalid_type(self):
        """Test error with invalid aggregation type."""
        from tools.parallel_executor_tool import aggregate_results_tool
        
        results = [{"success": True, "result": {}}]
        result = json.loads(aggregate_results_tool(results, "invalid"))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_AGGREGATION_TYPE"


class TestDelegateTask:
    """Test task delegation."""
    
    def test_delegate_empty_description(self):
        """Test error with empty description."""
        from tools.parallel_executor_tool import delegate_task_tool
        result = json.loads(delegate_task_tool(""))
        
        assert result["success"] is False
        assert result["error_code"] == "EMPTY_DESCRIPTION"
    
    def test_delegate_valid_task(self):
        """Test delegating a valid task."""
        from tools.parallel_executor_tool import delegate_task_tool
        
        result = json.loads(delegate_task_tool(
            task_description="Analyze this code",
            agent_type="coder"
        ))
        
        assert result["success"] is True
        assert result["data"]["delegated"] is True
        assert result["data"]["agent_type"] == "coder"
    
    def test_delegate_invalid_agent_type(self):
        """Test error with invalid agent type."""
        from tools.parallel_executor_tool import delegate_task_tool
        
        result = json.loads(delegate_task_tool(
            task_description="Do something",
            agent_type="invalid_type"
        ))
        
        assert result["success"] is False
        assert result["error_code"] == "INVALID_AGENT_TYPE"


class TestParallelExecutorRegistry:
    """Test tool registration."""
    
    def test_execute_parallel_registered(self):
        """Test execute_parallel is registered."""
        import tools.parallel_executor_tool
        from tools import registry
        entry = registry.registry.get_entry("execute_parallel")
        assert entry is not None
        assert entry.toolset == "subagents"
    
    def test_aggregate_results_registered(self):
        """Test aggregate_results is registered."""
        import tools.parallel_executor_tool
        from tools import registry
        entry = registry.registry.get_entry("aggregate_results")
        assert entry is not None
        assert entry.toolset == "subagents"
    
    def test_delegate_task_registered(self):
        """Test delegate_task is registered."""
        import tools.parallel_executor_tool
        from tools import registry
        entry = registry.registry.get_entry("delegate_task")
        assert entry is not None
        assert entry.toolset == "subagents"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])