from agency_swarm.tools import BaseTool
from pydantic import Field
import subprocess
import os
from typing import Optional, Literal

class Grep(BaseTool):
    """
    A powerful search tool built on ripgrep

      Usage:
      - ALWAYS use Grep for search tasks. NEVER invoke `grep` or `rg` as a Bash command. The Grep tool has been optimized for correct permissions and access.
      - Supports full regex syntax (e.g., "log.*Error", "function\\s+\\w+")
      - Filter files with glob parameter (e.g., "*.js", "**/*.tsx") or type parameter (e.g., "js", "py", "rust")
      - Output modes: "content" shows matching lines, "files_with_matches" shows only file paths (default), "count" shows match counts
      - Use Task tool for open-ended searches requiring multiple rounds
      - Pattern syntax: Uses ripgrep (not grep) - literal braces need escaping (use `interface\\{\\}` to find `interface{}` in Go code)
      - Multiline matching: By default patterns match within single lines only. For cross-line patterns like `struct \\{[\\s\\S]*?field`, use `multiline: true`
    """
    
    pattern: str = Field(
        ..., description="The regular expression pattern to search for in file contents"
    )
    path: Optional[str] = Field(
        default=None, description="File or directory to search in (rg PATH). Defaults to current working directory."
    )
    glob: Optional[str] = Field(
        default=None, description="Glob pattern to filter files (e.g. \"*.js\", \"*.{ts,tsx}\") - maps to rg --glob"
    )
    output_mode: Literal["content", "files_with_matches", "count"] = Field(
        default="files_with_matches", 
        description="Output mode: \"content\" shows matching lines (supports -A/-B/-C context, -n line numbers, head_limit), \"files_with_matches\" shows file paths (supports head_limit), \"count\" shows match counts (supports head_limit). Defaults to \"files_with_matches\"."
    )
    B: Optional[int] = Field(
        default=None, description="Number of lines to show before each match (rg -B). Requires output_mode: \"content\", ignored otherwise."
    )
    A: Optional[int] = Field(
        default=None, description="Number of lines to show after each match (rg -A). Requires output_mode: \"content\", ignored otherwise."
    )
    C: Optional[int] = Field(
        default=None, description="Number of lines to show before and after each match (rg -C). Requires output_mode: \"content\", ignored otherwise."
    )
    n: Optional[bool] = Field(
        default=None, description="Show line numbers in output (rg -n). Requires output_mode: \"content\", ignored otherwise."
    )
    i: Optional[bool] = Field(
        default=None, description="Case insensitive search (rg -i)"
    )
    type: Optional[str] = Field(
        default=None, description="File type to search (rg --type). Common types: js, py, rust, go, java, etc. More efficient than include for standard file types."
    )
    head_limit: Optional[int] = Field(
        default=None, description="Limit output to first N lines/entries, equivalent to \"| head -N\". Works across all output modes: content (limits output lines), files_with_matches (limits file paths), count (limits count entries). When unspecified, shows all results from ripgrep."
    )
    multiline: Optional[bool] = Field(
        default=False, description="Enable multiline mode where . matches newlines and patterns can span lines (rg -U --multiline-dotall). Default: false."
    )

    def run(self):
        """
        Execute ripgrep search with specified parameters.
        """
        # Step 1: Build ripgrep command
        cmd = ["rg"]
        
        # Step 2: Add pattern
        cmd.append(self.pattern)
        
        # Step 3: Add path if specified
        if self.path:
            cmd.append(self.path)
        
        # Step 4: Add output mode flags
        if self.output_mode == "files_with_matches":
            cmd.append("-l")
        elif self.output_mode == "count":
            cmd.append("-c")
        # content mode is default, no flag needed
        
        # Step 5: Add context flags (only for content mode)
        if self.output_mode == "content":
            if self.B is not None:
                cmd.extend(["-B", str(self.B)])
            if self.A is not None:
                cmd.extend(["-A", str(self.A)])
            if self.C is not None:
                cmd.extend(["-C", str(self.C)])
            if self.n:
                cmd.append("-n")
        
        # Step 6: Add case insensitive flag
        if self.i:
            cmd.append("-i")
        
        # Step 7: Add file type filter
        if self.type:
            cmd.extend(["--type", self.type])
        
        # Step 8: Add glob filter
        if self.glob:
            cmd.extend(["--glob", self.glob])
        
        # Step 9: Add multiline support
        if self.multiline:
            cmd.extend(["-U", "--multiline-dotall"])
        
        try:
            # Step 10: Execute ripgrep command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            # Step 11: Process output
            output_lines = []
            
            if result.stdout:
                stdout_lines = result.stdout.strip().split('\n')
                
                # Apply head_limit if specified
                if self.head_limit is not None:
                    stdout_lines = stdout_lines[:self.head_limit]
                
                if self.output_mode == "files_with_matches":
                    output_lines.append(f"Files containing pattern '{self.pattern}':")
                    output_lines.extend(stdout_lines)
                elif self.output_mode == "count":
                    output_lines.append(f"Match counts for pattern '{self.pattern}':")
                    for line in stdout_lines:
                        if ':' in line:
                            file_path, count = line.split(':', 1)
                            output_lines.append(f"{file_path}: {count} matches")
                        else:
                            output_lines.append(line)
                else:  # content mode
                    output_lines.append(f"Content matches for pattern '{self.pattern}':")
                    output_lines.extend(stdout_lines)
            
            if result.stderr:
                output_lines.append("Errors:")
                output_lines.append(result.stderr.strip())
            
            # Step 12: Handle no matches case
            if result.returncode != 0 and not result.stderr:
                if self.output_mode == "files_with_matches":
                    return f"No files found containing pattern '{self.pattern}'"
                elif self.output_mode == "count":
                    return f"No matches found for pattern '{self.pattern}'"
                else:
                    return f"No content matches found for pattern '{self.pattern}'"
            
            if not output_lines:
                return f"No results found for pattern '{self.pattern}'"
            
            return '\n'.join(output_lines)
            
        except FileNotFoundError:
            return "Error: ripgrep (rg) not found. Please ensure ripgrep is installed and in PATH."
        except Exception as e:
            return f"Error executing ripgrep search: {str(e)}"

if __name__ == "__main__":
    # Test case
    tool = Grep(pattern="def", output_mode="files_with_matches")
    print(tool.run())
