from agency_swarm.tools import BaseTool
from pydantic import Field
import os
from typing import Optional

class Read(BaseTool):
    """
    Reads a file from the local filesystem. You can access any file directly by using this tool.
    Assume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.

    Usage:
    - The file_path parameter must be an absolute path, not a relative path
    - By default, it reads up to 2000 lines starting from the beginning of the file
    - You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters
    - Any lines longer than 2000 characters will be truncated
    - Results are returned using cat -n format, with line numbers starting at 1
    - This tool allows Claude Code to read images (eg PNG, JPG, etc). When reading an image file the contents are presented visually as Claude Code is a multimodal LLM.
    - For Jupyter notebooks (.ipynb files), use the NotebookRead instead
    - You have the capability to call multiple tools in a single response. It is always better to speculatively read multiple files as a batch that are potentially useful. 
    - You will regularly be asked to read screenshots. If the user provides a path to a screenshot ALWAYS use this tool to view the file at the path. This tool will work with all temporary file paths like /var/folders/123/abc/T/TemporaryItems/NSIRD_screencaptureui_ZfB1tD/Screenshot.png
    - If you read a file that exists but has empty contents you will receive a system reminder warning in place of file contents.
    """
    
    file_path: str = Field(
        ..., description="The absolute path to the file to read"
    )
    offset: Optional[int] = Field(
        default=None, description="The line number to start reading from. Only provide if the file is too large to read at once"
    )
    limit: Optional[int] = Field(
        default=None, description="The number of lines to read. Only provide if the file is too large to read at once."
    )

    def run(self):
        """
        Read file contents with optional line range specification.
        """
        # Step 1: Validate file path is absolute
        if not os.path.isabs(self.file_path):
            return f"Error: File path must be absolute, not relative. Received: {self.file_path}"
        
        # Step 2: Check if file exists
        if not os.path.exists(self.file_path):
            return f"Error: File '{self.file_path}' does not exist"
        
        # Step 3: Check if it's a file (not directory)
        if not os.path.isfile(self.file_path):
            return f"Error: '{self.file_path}' is not a file"
        
        try:
            # Step 4: Check for binary files (images, etc.)
            # For now, we'll attempt text reading and handle encoding errors
            with open(self.file_path, 'r', encoding='utf-8', errors='replace') as file:
                lines = file.readlines()
            
            # Step 5: Handle empty file
            if not lines:
                return f"File is empty."
            
            # Step 6: Apply offset and limit if specified
            start_line = (self.offset - 1) if self.offset else 0
            if start_line < 0:
                start_line = 0
            
            if self.limit:
                end_line = start_line + self.limit
                selected_lines = lines[start_line:end_line]
            else:
                # Default limit to 2000 lines as specified
                default_limit = 2000
                end_line = min(start_line + default_limit, len(lines))
                selected_lines = lines[start_line:end_line]
            
            # Step 7: Format output with line numbers (cat -n format)
            output_lines = []
            for i, line in enumerate(selected_lines):
                line_num = start_line + i + 1
                
                # Truncate lines longer than 2000 characters
                if len(line) > 2000:
                    line_content = line[:2000] + "... [line truncated]"
                else:
                    line_content = line.rstrip('\n\r')
                
                # Format with right-aligned 6-character line number
                output_lines.append(f"{line_num:>6}|{line_content}")
            
            # Step 8: Add file info header
            total_lines = len(lines)
            if self.offset or self.limit:
                header = f"File: {self.file_path} (showing lines {start_line + 1}-{start_line + len(selected_lines)} of {total_lines})\n"
            else:
                if len(selected_lines) < total_lines:
                    header = f"File: {self.file_path} (showing first {len(selected_lines)} lines of {total_lines})\n"
                else:
                    header = f"File: {self.file_path} ({total_lines} lines)\n"
            
            return header + "\n".join(output_lines)
            
        except UnicodeDecodeError:
            # Handle binary files
            try:
                # Try to determine file type
                _, ext = os.path.splitext(self.file_path)
                if ext.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']:
                    return f"This appears to be an image file ({ext}). Image reading is not implemented in this tool - use appropriate image handling tools."
                elif ext.lower() in ['.pdf']:
                    return f"This appears to be a PDF file. PDF reading is not implemented in this tool - use appropriate PDF handling tools."
                else:
                    return f"This appears to be a binary file. Cannot read as text."
            except Exception:
                return f"Error: Unable to read file '{self.file_path}' - appears to be binary or has encoding issues"
        
        except PermissionError:
            return f"Error: Permission denied reading file '{self.file_path}'"
        except Exception as e:
            return f"Error reading file '{self.file_path}': {str(e)}"

if __name__ == "__main__":
    # Test case
    import tempfile
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Line 1\nLine 2\nLine 3\n")
        test_file = f.name
    
    tool = Read(file_path=test_file)
    result = tool.run()
    print(result)
    
    # Clean up
    os.unlink(test_file)
