from agency_swarm.tools import BaseTool
from pydantic import Field, BaseModel
from typing import List, Literal

class TodoItem(BaseModel):
    """Individual todo item."""
    content: str = Field(..., min_length=1, description="The todo task description")
    status: Literal["pending", "in_progress", "completed"] = Field(..., description="Current status of the todo item")
    priority: Literal["high", "medium", "low"] = Field(..., description="Priority level of the todo item")
    id: str = Field(..., description="Unique identifier for the todo item")

class TodoWrite(BaseTool):
    """
    Use this tool to create and manage a structured task list for your current coding session. This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user.
    It also helps the user understand the progress of the task and overall progress of their requests.

    ## When to Use This Tool
    Use this tool proactively in these scenarios:

    1. Complex multi-step tasks - When a task requires 3 or more distinct steps or actions
    2. Non-trivial and complex tasks - Tasks that require careful planning or multiple operations
    3. User explicitly requests todo list - When the user directly asks you to use the todo list
    4. User provides multiple tasks - When users provide a list of things to be done (numbered or comma-separated)
    5. After receiving new instructions - Immediately capture user requirements as todos
    6. When you start working on a task - Mark it as in_progress BEFORE beginning work. Ideally you should only have one todo as in_progress at a time
    7. After completing a task - Mark it as completed and add any new follow-up tasks discovered during implementation

    ## When NOT to Use This Tool

    Skip using this tool when:
    1. There is only a single, straightforward task
    2. The task is trivial and tracking it provides no organizational benefit
    3. The task can be completed in less than 3 trivial steps
    4. The task is purely conversational or informational

    NOTE that you should not use this tool if there is only one trivial task to do. In this case you are better off just doing the task directly.

    ## Task States and Management

    1. **Task States**: Use these states to track progress:
       - pending: Task not yet started
       - in_progress: Currently working on (limit to ONE task at a time)
       - completed: Task finished successfully

    2. **Task Management**:
       - Update task status in real-time as you work
       - Mark tasks complete IMMEDIATELY after finishing (don't batch completions)
       - Only have ONE task in_progress at any time
       - Complete current tasks before starting new ones
       - Remove tasks that are no longer relevant from the list entirely

    3. **Task Completion Requirements**:
       - ONLY mark a task as completed when you have FULLY accomplished it
       - If you encounter errors, blockers, or cannot finish, keep the task as in_progress
       - When blocked, create a new task describing what needs to be resolved
       - Never mark a task as completed if:
         - Tests are failing
         - Implementation is partial
         - You encountered unresolved errors
         - You couldn't find necessary files or dependencies

    4. **Task Breakdown**:
       - Create specific, actionable items
       - Break complex tasks into smaller, manageable steps
       - Use clear, descriptive task names

    When in doubt, use this tool. Being proactive with task management demonstrates attentiveness and ensures you complete all requirements successfully.
    """
    
    todos: List[TodoItem] = Field(
        ..., description="The updated todo list"
    )

    def run(self):
        """
        Update the todo list and return a formatted summary.
        """
        # Step 1: Validate todos list
        if not self.todos:
            return "Error: Todo list cannot be empty"
        
        # Step 2: Validate unique IDs
        ids = [todo.id for todo in self.todos]
        if len(ids) != len(set(ids)):
            return "Error: All todo items must have unique IDs"
        
        # Step 3: Count todos by status
        status_counts = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0
        }
        
        for todo in self.todos:
            status_counts[todo.status] += 1
        
        # Step 4: Validate in_progress constraint
        if status_counts["in_progress"] > 1:
            in_progress_items = [todo.content for todo in self.todos if todo.status == "in_progress"]
            return f"Warning: Multiple tasks marked as in_progress. Recommended to have only one task in_progress at a time:\n" + "\n".join(f"- {item}" for item in in_progress_items)
        
        # Step 5: Format todo list display
        output_lines = ["=== TODO LIST ===\n"]
        
        # Group by status
        status_order = ["in_progress", "pending", "completed"]
        status_symbols = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅"
        }
        
        for status in status_order:
            status_todos = [todo for todo in self.todos if todo.status == status]
            if not status_todos:
                continue
                
            output_lines.append(f"{status.upper().replace('_', ' ')} ({len(status_todos)}):")
            
            # Sort by priority within each status
            priority_order = {"high": 1, "medium": 2, "low": 3}
            status_todos.sort(key=lambda x: priority_order.get(x.priority, 4))
            
            for todo in status_todos:
                symbol = status_symbols[todo.status]
                priority_indicator = {
                    "high": "🔴",
                    "medium": "🟡", 
                    "low": "🟢"
                }.get(todo.priority, "⚪")
                
                output_lines.append(f"  {symbol} [{todo.id}] {priority_indicator} {todo.content}")
            
            output_lines.append("")
        
        # Step 6: Add summary
        total_todos = len(self.todos)
        completed_todos = status_counts["completed"]
        progress_percentage = (completed_todos / total_todos * 100) if total_todos > 0 else 0
        
        output_lines.append(f"PROGRESS: {completed_todos}/{total_todos} completed ({progress_percentage:.0f}%)")
        
        # Step 7: Add next action suggestion
        if status_counts["in_progress"] > 0:
            current_task = next(todo for todo in self.todos if todo.status == "in_progress")
            output_lines.append(f"CURRENT FOCUS: {current_task.content}")
        elif status_counts["pending"] > 0:
            # Find highest priority pending task
            pending_todos = [todo for todo in self.todos if todo.status == "pending"]
            pending_todos.sort(key=lambda x: priority_order.get(x.priority, 4))
            next_task = pending_todos[0]
            output_lines.append(f"NEXT UP: {next_task.content}")
        else:
            output_lines.append("🎉 All tasks completed!")
        
        return "\n".join(output_lines)

if __name__ == "__main__":
    # Test case
    test_todos = [
        TodoItem(
            id="1",
            content="Create project structure",
            status="completed",
            priority="high"
        ),
        TodoItem(
            id="2", 
            content="Implement core functionality",
            status="in_progress",
            priority="high"
        ),
        TodoItem(
            id="3",
            content="Write unit tests",
            status="pending",
            priority="medium"
        ),
        TodoItem(
            id="4",
            content="Update documentation",
            status="pending", 
            priority="low"
        )
    ]
    
    tool = TodoWrite(todos=test_todos)
    result = tool.run()
    print("TodoWrite test:")
    print(result)
