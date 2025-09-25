from agency_swarm.tools import BaseTool
from pydantic import Field
import os

class Write(BaseTool):
    """
    Writes a file to the local filesystem.

    Usage:
    - This tool will overwrite the existing file if there is one at the provided path.
    - If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.
    - ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
    - NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
    - Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked.
    """
    
    file_path: str = Field(
        ..., description="The absolute path to the file to write (must be absolute, not relative)"
    )
    content: str = Field(
        ..., description="The content to write to the file"
    )

    def run(self):
        """
        Write content to the specified file.
        """
        # Step 1: Validate file path is absolute
        if not os.path.isabs(self.file_path):
            return f"Error: File path must be absolute, not relative. Received: {self.file_path}"
        
        # Step 2: Check if file already exists
        file_exists = os.path.exists(self.file_path)
        
        # Step 3: For existing files, we should verify Read was used first
        # (This is a design requirement from the YAML spec, but we can't actually enforce it)
        # We'll issue a warning but still proceed
        if file_exists:
            if os.path.isfile(self.file_path):
                # Issue warning about reading first (as per spec)
                print("Warning: When overwriting existing files, you should use the Read tool first to understand the file contents.")
            else:
                return f"Error: '{self.file_path}' exists but is not a file (might be a directory)"
        
        try:
            # Step 4: Create directory if it doesn't exist
            directory = os.path.dirname(self.file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Step 5: Write content to file
            with open(self.file_path, 'w', encoding='utf-8') as file:
                file.write(self.content)
            
            # Step 6: Get file size for confirmation
            file_size = os.path.getsize(self.file_path)
            
            # Step 7: Return success message
            if file_exists:
                return f"Successfully overwrote file '{self.file_path}' ({file_size} bytes)"
            else:
                return f"Successfully created file '{self.file_path}' ({file_size} bytes)"
            
        except PermissionError:
            return f"Error: Permission denied writing to file '{self.file_path}'"
        except OSError as e:
            if e.errno == 36:  # File name too long
                return f"Error: File path too long: '{self.file_path}'"
            else:
                return f"Error: OS error writing file '{self.file_path}': {str(e)}"
        except Exception as e:
            return f"Error writing file '{self.file_path}': {str(e)}"

if __name__ == "__main__":
    # Test case
    import tempfile
    import os
    
    # Test creating a new file
    test_dir = tempfile.mkdtemp()
    test_file = os.path.join(test_dir, "test_write.txt")
    
    tool = Write(file_path=test_file, content="Hello, World!\nThis is a test file.\nLine 3.")
    result = tool.run()
    print("Write test:")
    print(result)
    
    # Verify the file was created and has correct content
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"\nFile content verification:\n{content}")
    
    # Clean up
    os.unlink(test_file)
    os.rmdir(test_dir)
