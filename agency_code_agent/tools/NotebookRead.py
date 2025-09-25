from agency_swarm.tools import BaseTool
from pydantic import Field
import os
import json
from typing import Optional

class NotebookRead(BaseTool):
    """
    Reads a Jupyter notebook (.ipynb file) and returns all of the 
    cells with their outputs. Jupyter notebooks are interactive documents that 
    combine code, text, and visualizations, commonly used for data analysis and 
    scientific computing. The notebook_path parameter must be an absolute path, 
    not a relative path.
    """
    
    notebook_path: str = Field(
        ..., description="The absolute path to the Jupyter notebook file to read (must be absolute, not relative)"
    )
    cell_id: Optional[str] = Field(
        default=None, description="The ID of a specific cell to read. If not provided, all cells will be read."
    )

    def run(self):
        """
        Read Jupyter notebook and return cell contents with outputs.
        """
        # Step 1: Validate notebook path is absolute
        if not os.path.isabs(self.notebook_path):
            return f"Error: Notebook path must be absolute, not relative. Received: {self.notebook_path}"
        
        # Step 2: Check if file exists
        if not os.path.exists(self.notebook_path):
            return f"Error: Notebook file '{self.notebook_path}' does not exist"
        
        # Step 3: Check if it's a file and has .ipynb extension
        if not os.path.isfile(self.notebook_path):
            return f"Error: '{self.notebook_path}' is not a file"
        
        if not self.notebook_path.lower().endswith('.ipynb'):
            return f"Error: File '{self.notebook_path}' is not a Jupyter notebook (.ipynb) file"
        
        try:
            # Step 4: Read and parse notebook JSON
            with open(self.notebook_path, 'r', encoding='utf-8') as file:
                notebook_data = json.load(file)
            
            # Step 5: Validate notebook structure
            if 'cells' not in notebook_data:
                return f"Error: Invalid notebook format - no 'cells' found in '{self.notebook_path}'"
            
            cells = notebook_data['cells']
            
            # Step 6: Handle specific cell ID request
            if self.cell_id:
                target_cell = None
                for cell in cells:
                    # Check both 'id' field and index-based matching
                    if cell.get('id') == self.cell_id:
                        target_cell = cell
                        break
                    # Also support numeric cell IDs (cell index)
                    try:
                        cell_index = int(self.cell_id)
                        if 0 <= cell_index < len(cells):
                            target_cell = cells[cell_index]
                            break
                    except ValueError:
                        pass
                
                if target_cell is None:
                    return f"Error: Cell with ID '{self.cell_id}' not found in notebook"
                
                # Format single cell
                return self._format_cell(target_cell, self.cell_id)
            
            # Step 7: Format all cells
            output_lines = [f"Jupyter Notebook: {self.notebook_path}"]
            output_lines.append(f"Total cells: {len(cells)}\n")
            
            for i, cell in enumerate(cells):
                cell_output = self._format_cell(cell, str(i))
                output_lines.append(cell_output)
                output_lines.append("")  # Add spacing between cells
            
            return "\n".join(output_lines)
            
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON in notebook file '{self.notebook_path}': {str(e)}"
        except PermissionError:
            return f"Error: Permission denied reading notebook file '{self.notebook_path}'"
        except Exception as e:
            return f"Error reading notebook file '{self.notebook_path}': {str(e)}"
    
    def _format_cell(self, cell, cell_id):
        """
        Format a single cell for display.
        """
        cell_type = cell.get('cell_type', 'unknown')
        source = cell.get('source', [])
        outputs = cell.get('outputs', [])
        execution_count = cell.get('execution_count')
        
        # Format cell header
        lines = [f"=== Cell {cell_id} ({cell_type}) ==="]
        
        if execution_count is not None:
            lines.append(f"Execution count: {execution_count}")
        
        # Format source code/markdown
        if source:
            lines.append("Source:")
            if isinstance(source, list):
                source_text = ''.join(source)
            else:
                source_text = str(source)
            
            lines.append("```" + ("python" if cell_type == "code" else "markdown"))
            lines.append(source_text.rstrip())
            lines.append("```")
        
        # Format outputs for code cells
        if cell_type == "code" and outputs:
            lines.append("Outputs:")
            for i, output in enumerate(outputs):
                output_type = output.get('output_type', 'unknown')
                lines.append(f"  Output {i+1} ({output_type}):")
                
                if output_type == 'stream':
                    # Handle stdout/stderr streams
                    stream_text = ''.join(output.get('text', []))
                    lines.append(f"    {stream_text.rstrip()}")
                
                elif output_type == 'execute_result' or output_type == 'display_data':
                    # Handle rich outputs
                    data = output.get('data', {})
                    for mime_type, content in data.items():
                        if mime_type == 'text/plain':
                            text_content = ''.join(content) if isinstance(content, list) else str(content)
                            lines.append(f"    {mime_type}: {text_content.rstrip()}")
                        elif mime_type.startswith('image/'):
                            lines.append(f"    {mime_type}: [Image data - {len(str(content))} characters]")
                        else:
                            content_preview = str(content)[:100] + "..." if len(str(content)) > 100 else str(content)
                            lines.append(f"    {mime_type}: {content_preview}")
                
                elif output_type == 'error':
                    # Handle errors
                    error_name = output.get('ename', 'Unknown')
                    error_value = output.get('evalue', '')
                    lines.append(f"    Error: {error_name}: {error_value}")
                    
                    traceback = output.get('traceback', [])
                    if traceback:
                        lines.append("    Traceback:")
                        for tb_line in traceback:
                            lines.append(f"      {tb_line}")
        
        return "\n".join(lines)

if __name__ == "__main__":
    # Test case - create a simple test notebook
    import tempfile
    
    test_notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "cell1",
                "source": ["# Test Notebook\n", "This is a test notebook"]
            },
            {
                "cell_type": "code",
                "execution_count": 1,
                "id": "cell2",
                "source": ["print('Hello, World!')\n", "x = 42\n", "x"],
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": ["Hello, World!\n"]
                    },
                    {
                        "output_type": "execute_result",
                        "execution_count": 1,
                        "data": {"text/plain": ["42"]},
                        "metadata": {}
                    }
                ]
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    # Create temporary notebook file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ipynb', encoding='utf-8') as f:
        json.dump(test_notebook, f)
        test_file = f.name
    
    # Test reading the notebook
    tool = NotebookRead(notebook_path=test_file)
    result = tool.run()
    print("NotebookRead test:")
    print(result)
    
    # Clean up
    os.unlink(test_file)
