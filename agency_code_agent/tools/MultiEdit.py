from agency_swarm.tools import BaseTool
from pydantic import Field, BaseModel
import os
from typing import List, Optional

class EditOperation(BaseModel):
    """Single edit operation for MultiEdit."""
    old_string: str = Field(..., description="The text to replace")
    new_string: str = Field(..., description="The text to replace it with")
    replace_all: bool = Field(default=False, description="Replace all occurences of old_string (default false).")

class MultiEdit(BaseTool):
    """
    This is a tool for making multiple edits to a single file in one operation. It is built on top of the Edit tool and allows you to perform multiple find-and-replace operations efficiently. Prefer this tool over the Edit tool when you need to make multiple edits to the same file.

    Before using this tool:

    1. Use the Read tool to understand the file's contents and context
    2. Verify the directory path is correct

    To make multiple file edits, provide the following:
    1. file_path: The absolute path to the file to modify (must be absolute, not relative)
    2. edits: An array of edit operations to perform, where each edit contains:
       - old_string: The text to replace (must match the file contents exactly, including all whitespace and indentation)
       - new_string: The edited text to replace the old_string
       - replace_all: Replace all occurences of old_string. This parameter is optional and defaults to false.

    IMPORTANT:
    - All edits are applied in sequence, in the order they are provided
    - Each edit operates on the result of the previous edit
    - All edits must be valid for the operation to succeed - if any edit fails, none will be applied
    - This tool is ideal when you need to make several changes to different parts of the same file
    - For Jupyter notebooks (.ipynb files), use the NotebookEdit instead

    CRITICAL REQUIREMENTS:
    1. All edits follow the same requirements as the single Edit tool
    2. The edits are atomic - either all succeed or none are applied
    3. Plan your edits carefully to avoid conflicts between sequential operations

    WARNING:
    - The tool will fail if edits.old_string doesn't match the file contents exactly (including whitespace)
    - The tool will fail if edits.old_string and edits.new_string are the same
    - Since edits are applied in sequence, ensure that earlier edits don't affect the text that later edits are trying to find

    When making edits:
    - Ensure all edits result in idiomatic, correct code
    - Do not leave the code in a broken state
    - Always use absolute file paths (starting with /)
    - Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.
    - Use replace_all for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance.

    If you want to create a new file, use:
    - A new file path, including dir name if needed
    - First edit: empty old_string and the new file's contents as new_string
    - Subsequent edits: normal edit operations on the created content
    """
    
    file_path: str = Field(
        ..., description="The absolute path to the file to modify"
    )
    edits: List[EditOperation] = Field(
        ..., description="Array of edit operations to perform sequentially on the file"
    )

    def run(self):
        """
        Perform multiple edits to a single file atomically.
        """
        # Step 1: Validate file path is absolute
        if not os.path.isabs(self.file_path):
            return f"Error: File path must be absolute, not relative. Received: {self.file_path}"
        
        # Step 2: Validate edits list
        if not self.edits:
            return "Error: At least one edit operation must be provided"
        
        # Step 3: Check if file exists (or if we're creating a new one)
        file_exists = os.path.exists(self.file_path)
        
        # Step 4: Handle new file creation case
        if not file_exists:
            # Check if first edit is for creating new file (empty old_string)
            if self.edits[0].old_string != "":
                return f"Error: File '{self.file_path}' does not exist. To create a new file, the first edit must have an empty old_string."
        else:
            # Check if it's a file (not directory)
            if not os.path.isfile(self.file_path):
                return f"Error: '{self.file_path}' is not a file"
        
        try:
            # Step 5: Read initial content (or start with empty for new files)
            if file_exists:
                with open(self.file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
            else:
                content = ""
            
            # Step 6: Validate all edits before applying any
            validation_content = content
            for i, edit in enumerate(self.edits):
                # Check for same old/new string
                if edit.old_string == edit.new_string:
                    return f"Error in edit {i+1}: old_string and new_string must be different"
                
                # For new file creation, skip validation of first edit with empty old_string
                if not file_exists and i == 0 and edit.old_string == "":
                    validation_content = edit.new_string
                    continue
                
                # Check if old_string exists
                if edit.old_string not in validation_content:
                    return f"Error in edit {i+1}: String '{edit.old_string}' not found in file content"
                
                # Check uniqueness if not replace_all
                if not edit.replace_all:
                    occurrences = validation_content.count(edit.old_string)
                    if occurrences > 1:
                        return f"Error in edit {i+1}: String '{edit.old_string}' appears {occurrences} times. Either provide a larger string with more context or use replace_all=True"
                
                # Apply edit to validation content for next iteration
                if edit.replace_all:
                    validation_content = validation_content.replace(edit.old_string, edit.new_string)
                else:
                    validation_content = validation_content.replace(edit.old_string, edit.new_string, 1)
            
            # Step 7: Apply all edits sequentially
            current_content = content
            edit_results = []
            
            for i, edit in enumerate(self.edits):
                # Handle new file creation case
                if not file_exists and i == 0 and edit.old_string == "":
                    current_content = edit.new_string
                    edit_results.append(f"Edit {i+1}: Created new file with content")
                    continue
                
                # Apply edit
                if edit.replace_all:
                    replacement_count = current_content.count(edit.old_string)
                    current_content = current_content.replace(edit.old_string, edit.new_string)
                    edit_results.append(f"Edit {i+1}: Replaced {replacement_count} occurrences")
                else:
                    current_content = current_content.replace(edit.old_string, edit.new_string, 1)
                    edit_results.append(f"Edit {i+1}: Replaced 1 occurrence")
            
            # Step 8: Write final content to file
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as file:
                file.write(current_content)
            
            # Step 9: Return success message
            result_lines = [f"Successfully applied {len(self.edits)} edits to '{self.file_path}':"]
            result_lines.extend(edit_results)
            
            return "\n".join(result_lines)
            
        except PermissionError:
            return f"Error: Permission denied modifying file '{self.file_path}'"
        except UnicodeDecodeError:
            return f"Error: File '{self.file_path}' contains non-UTF-8 content and cannot be edited as text"
        except Exception as e:
            return f"Error applying edits to file '{self.file_path}': {str(e)}"

if __name__ == "__main__":
    # Test case
    import tempfile
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
        f.write("Hello World\nThis is line 2\nHello World again\nLine 4")
        test_file = f.name
    
    # Test multiple edits
    edits = [
        EditOperation(old_string="Hello World", new_string="Hi Universe"),
        EditOperation(old_string="line 2", new_string="the second line"),
        EditOperation(old_string="Line 4", new_string="The fourth line")
    ]
    
    tool = MultiEdit(file_path=test_file, edits=edits)
    result = tool.run()
    print("MultiEdit test:")
    print(result)
    
    # Read back to verify
    with open(test_file, 'r', encoding='utf-8') as f:
        print("\nFile contents after MultiEdit:")
        print(f.read())
    
    # Clean up
    os.unlink(test_file)
