from agency_swarm.tools import BaseTool
from pydantic import Field
import os

class Edit(BaseTool):
    """
    Performs exact string replacements in files. 

    Usage:
    - You must use your `Read` tool at least once in the conversation before editing. This tool will error if you attempt an edit without reading the file. 
    - When editing text from Read tool output, ensure you preserve the exact indentation (tabs/spaces) as it appears AFTER the line number prefix. The line number prefix format is: spaces + line number + tab. Everything after that tab is the actual file content to match. Never include any part of the line number prefix in the old_string or new_string.
    - ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
    - Only use emojis if the user explicitly requests it. Avoid adding emojis to files unless asked.
    - The edit will FAIL if `old_string` is not unique in the file. Either provide a larger string with more surrounding context to make it unique or use `replace_all` to change every instance of `old_string`. 
    - Use `replace_all` for replacing and renaming strings across the file. This parameter is useful if you want to rename a variable for instance.
    """
    
    file_path: str = Field(
        ..., description="The absolute path to the file to modify"
    )
    old_string: str = Field(
        ..., description="The text to replace"
    )
    new_string: str = Field(
        ..., description="The text to replace it with (must be different from old_string)"
    )
    replace_all: bool = Field(
        default=False, description="Replace all occurences of old_string (default false)"
    )

    def run(self):
        """
        Perform exact string replacement in the specified file.
        """
        # Step 1: Validate inputs
        if self.old_string == self.new_string:
            return "Error: old_string and new_string must be different"
        
        # Step 2: Validate file path is absolute
        if not os.path.isabs(self.file_path):
            return f"Error: File path must be absolute, not relative. Received: {self.file_path}"
        
        # Step 3: Check if file exists
        if not os.path.exists(self.file_path):
            return f"Error: File '{self.file_path}' does not exist"
        
        # Step 4: Check if it's a file (not directory)
        if not os.path.isfile(self.file_path):
            return f"Error: '{self.file_path}' is not a file"
        
        try:
            # Step 5: Read file contents
            with open(self.file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Step 6: Check if old_string exists in file
            if self.old_string not in content:
                return f"Error: String '{self.old_string}' not found in file '{self.file_path}'"
            
            # Step 7: Check uniqueness if not replace_all
            if not self.replace_all:
                occurrences = content.count(self.old_string)
                if occurrences > 1:
                    return f"Error: String '{self.old_string}' appears {occurrences} times in the file. Either provide a larger string with more context to make it unique, or use replace_all=True to change all instances."
            
            # Step 8: Perform replacement
            if self.replace_all:
                new_content = content.replace(self.old_string, self.new_string)
                replacement_count = content.count(self.old_string)
            else:
                new_content = content.replace(self.old_string, self.new_string, 1)
                replacement_count = 1
            
            # Step 9: Write back to file
            with open(self.file_path, 'w', encoding='utf-8') as file:
                file.write(new_content)
            
            # Step 10: Return success message
            if replacement_count == 1:
                return f"Successfully replaced 1 occurrence of the specified text in '{self.file_path}'"
            else:
                return f"Successfully replaced {replacement_count} occurrences of the specified text in '{self.file_path}'"
            
        except PermissionError:
            return f"Error: Permission denied modifying file '{self.file_path}'"
        except UnicodeDecodeError:
            return f"Error: File '{self.file_path}' contains non-UTF-8 content and cannot be edited as text"
        except Exception as e:
            return f"Error editing file '{self.file_path}': {str(e)}"

if __name__ == "__main__":
    # Test case
    import tempfile
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
        f.write("Hello World\nThis is a test file\nHello World again")
        test_file = f.name
    
    # Test single replacement
    tool = Edit(file_path=test_file, old_string="Hello World", new_string="Hi Universe")
    result = tool.run()
    print("Single replacement test:")
    print(result)
    
    # Read back to verify
    with open(test_file, 'r', encoding='utf-8') as f:
        print("File contents after edit:")
        print(f.read())
    
    # Clean up
    os.unlink(test_file)
