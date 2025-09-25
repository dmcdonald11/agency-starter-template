from agency_swarm.tools import BaseTool
from pydantic import Field
import subprocess
import os
import threading
from typing import Optional

class Bash(BaseTool):
    """
    Executes a given bash command in a persistent shell session with optional timeout, 
    ensuring proper handling and security measures.

    Before executing the command, please follow these steps:

    1. Directory Verification:
       - If the command will create new directories or files, first use the LS tool to verify the parent directory exists and is the correct location
       - For example, before running "mkdir foo/bar", first use LS to check that "foo" exists and is the intended parent directory

    2. Command Execution:
       - Always quote file paths that contain spaces with double quotes (e.g., cd "path with spaces/file.txt")
       - Examples of proper quoting:
         - cd "/Users/name/My Documents" (correct)
         - cd /Users/name/My Documents (incorrect - will fail)
         - python "/path/with spaces/script.py" (correct)
         - python /path/with spaces/script.py (incorrect - will fail)
       - After ensuring proper quoting, execute the command.
       - Capture the output of the command.

    Usage notes:
      - The command argument is required.
      - You can specify an optional timeout in milliseconds (up to 600000ms / 10 minutes). If not specified, commands will timeout after 120000ms (2 minutes).
      - It is very helpful if you write a clear, concise description of what this command does in 5-10 words.
      - If the output exceeds 30000 characters, output will be truncated before being returned to you.
      - VERY IMPORTANT: You MUST avoid using search commands like `find` and `grep`. Instead use Grep, Glob, or Task to search. You MUST avoid read tools like `cat`, `head`, `tail`, and `ls`, and use Read and LS to read files.
     - If you _still_ need to run `grep`, STOP. ALWAYS USE ripgrep at `rg` first, which all users have pre-installed.
      - When issuing multiple commands, use the ';' or '&&' operator to separate them. DO NOT use newlines (newlines are ok in quoted strings).
      - Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of `cd`. You may use `cd` if the User explicitly requests it.
    """
    
    command: str = Field(
        ..., description="The command to execute"
    )
    timeout: Optional[int] = Field(
        default=120000, description="Optional timeout in milliseconds (max 600000)"
    )
    description: Optional[str] = Field(
        default="", description="Clear, concise description of what this command does in 5-10 words"
    )

    def run(self):
        """
        Execute the bash command with proper timeout and error handling.
        """
        # Step 1: Validate timeout
        if self.timeout and self.timeout > 600000:
            return "Error: Timeout cannot exceed 600000ms (10 minutes)"
        
        # Step 2: Set up timeout (convert to seconds for subprocess)
        timeout_seconds = (self.timeout or 120000) / 1000
        
        # Step 3: Execute command with timeout
        try:
            # Use shell=True on Windows to properly handle commands
            result = subprocess.run(
                self.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=os.getcwd()
            )
            
            # Step 4: Format output
            output_lines = []
            if result.stdout:
                output_lines.append("Command output:")
                output_lines.append("```")
                output_lines.append(result.stdout.strip())
                output_lines.append("```")
            
            if result.stderr:
                output_lines.append("Error output:")
                output_lines.append("```")
                output_lines.append(result.stderr.strip())
                output_lines.append("```")
            
            output_lines.append(f"Exit code: {result.returncode}")
            
            if result.returncode == 0:
                output_lines.append("\nCommand completed.")
            else:
                output_lines.append(f"\nCommand failed with exit code {result.returncode}.")
            
            # Step 5: Add session info
            output_lines.append(f"\nThe previous shell command ended, so on the next invocation of this tool, you will be reusing the shell.")
            output_lines.append(f"\nOn the next terminal tool call, the directory of the shell will already be {os.getcwd()}.")
            
            full_output = "\n".join(output_lines)
            
            # Step 6: Truncate if too long
            if len(full_output) > 30000:
                return full_output[:30000] + "\n\n... [Output truncated due to length]"
            
            return full_output
            
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout_seconds} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"

if __name__ == "__main__":
    # Test case
    tool = Bash(command="echo 'Hello World'", description="Test echo command")
    print(tool.run())
