from agency_swarm.tools import BaseTool
from pydantic import Field
import os
import glob
from typing import List, Optional

class LS(BaseTool):
    """
    Lists files and directories in a given path. The path parameter 
    must be an absolute path, not a relative path. You can optionally provide an
    array of glob patterns to ignore with the ignore parameter. You should 
    generally prefer the Glob and Grep tools, if you know which directories to 
    search.
    """
    
    path: str = Field(
        ..., description="The absolute path to the directory to list (must be absolute, not relative)"
    )
    ignore: Optional[List[str]] = Field(
        default=None, description="List of glob patterns to ignore"
    )

    def run(self):
        """
        List files and directories in the specified path with optional filtering.
        """
        # Step 1: Validate path is absolute
        if not os.path.isabs(self.path):
            return f"Error: Path must be absolute, not relative. Received: {self.path}"
        
        # Step 2: Check if path exists
        if not os.path.exists(self.path):
            return f"Error: Path '{self.path}' does not exist"
        
        # Step 3: Check if path is a directory
        if not os.path.isdir(self.path):
            return f"Error: Path '{self.path}' is not a directory"
        
        try:
            # Step 4: Get directory contents
            entries = os.listdir(self.path)
            
            # Step 5: Filter out ignored patterns if specified
            if self.ignore:
                filtered_entries = []
                for entry in entries:
                    entry_path = os.path.join(self.path, entry)
                    should_ignore = False
                    
                    # Check each ignore pattern
                    for pattern in self.ignore:
                        # Use glob.fnmatch for pattern matching
                        if glob.fnmatch.fnmatch(entry, pattern):
                            should_ignore = True
                            break
                        # Also check full path matching
                        if glob.fnmatch.fnmatch(entry_path, pattern):
                            should_ignore = True
                            break
                    
                    if not should_ignore:
                        filtered_entries.append(entry)
                
                entries = filtered_entries
            
            # Step 6: Sort entries (directories first, then files, both alphabetically)
            directories = []
            files = []
            
            for entry in entries:
                entry_path = os.path.join(self.path, entry)
                if os.path.isdir(entry_path):
                    directories.append(entry)
                else:
                    files.append(entry)
            
            directories.sort()
            files.sort()
            
            # Step 7: Format output
            output_lines = [f"Contents of '{self.path}':\n"]
            
            if not directories and not files:
                output_lines.append("(empty directory)")
            else:
                # Add directories with trailing slash
                for directory in directories:
                    output_lines.append(f"  {directory}/")
                
                # Add files
                for file in files:
                    output_lines.append(f"  {file}")
            
            # Step 8: Add summary
            total_items = len(directories) + len(files)
            if total_items > 0:
                output_lines.append(f"\nTotal: {len(directories)} directories, {len(files)} files")
            
            return "\n".join(output_lines)
            
        except PermissionError:
            return f"Error: Permission denied accessing '{self.path}'"
        except Exception as e:
            return f"Error listing directory '{self.path}': {str(e)}"

if __name__ == "__main__":
    # Test case
    tool = LS(path=os.path.abspath("."))
    print(tool.run())
