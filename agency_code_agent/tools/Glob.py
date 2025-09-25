from agency_swarm.tools import BaseTool
from pydantic import Field
import glob
import os
from typing import Optional

class Glob(BaseTool):
    """
    - Fast file pattern matching tool that works with any codebase size
    - Supports glob patterns like "**/*.js" or "src/**/*.ts"
    - Returns matching file paths sorted by modification time
    - Use this tool when you need to find files by name patterns
    - When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead
    - You have the capability to call multiple tools in a single response. It is always better to speculatively perform multiple searches as a batch that are potentially useful.
    """
    
    pattern: str = Field(
        ..., description="The glob pattern to match files against"
    )
    path: Optional[str] = Field(
        default=None, 
        description="The directory to search in. If not specified, the current working directory will be used. IMPORTANT: Omit this field to use the default directory. DO NOT enter \"undefined\" or \"null\" - simply omit it for the default behavior. Must be a valid directory path if provided."
    )

    def run(self):
        """
        Execute the glob pattern matching and return sorted results.
        """
        # Step 1: Determine search directory
        search_dir = self.path if self.path else os.getcwd()
        
        # Step 2: Validate directory exists
        if not os.path.exists(search_dir):
            return f"Error: Directory '{search_dir}' does not exist"
        
        if not os.path.isdir(search_dir):
            return f"Error: '{search_dir}' is not a directory"
        
        # Step 3: Build full pattern path
        if os.path.isabs(self.pattern):
            full_pattern = self.pattern
        else:
            full_pattern = os.path.join(search_dir, self.pattern)
        
        try:
            # Step 4: Execute glob search with recursive option
            matches = glob.glob(full_pattern, recursive=True)
            
            # Step 5: Filter out directories if pattern doesn't explicitly ask for them
            file_matches = [f for f in matches if os.path.isfile(f)]
            
            # Step 6: Sort by modification time (most recent first)
            file_matches.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # Step 7: Convert to relative paths if searching in current directory
            if search_dir == os.getcwd():
                relative_matches = []
                for match in file_matches:
                    try:
                        rel_path = os.path.relpath(match, search_dir)
                        relative_matches.append(rel_path)
                    except ValueError:
                        # Handle case where path can't be made relative (different drives on Windows)
                        relative_matches.append(match)
                file_matches = relative_matches
            
            # Step 8: Format output
            if not file_matches:
                return f"No files found matching pattern '{self.pattern}' in directory '{search_dir}'"
            
            result_lines = [f"Found {len(file_matches)} files matching pattern '{self.pattern}':\n"]
            result_lines.extend(file_matches)
            
            return "\n".join(result_lines)
            
        except Exception as e:
            return f"Error executing glob pattern '{self.pattern}': {str(e)}"

if __name__ == "__main__":
    # Test case
    tool = Glob(pattern="*.py")
    print(tool.run())
