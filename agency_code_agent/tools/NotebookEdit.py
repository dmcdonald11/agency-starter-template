from agency_swarm.tools import BaseTool
from pydantic import Field
import os
import json
from typing import Optional, Literal

class NotebookEdit(BaseTool):
    """
    Completely replaces the contents of a specific cell in a Jupyter 
    notebook (.ipynb file) with new source. Jupyter notebooks are interactive 
    documents that combine code, text, and visualizations, commonly used for 
    data analysis and scientific computing. The notebook_path parameter must be 
    an absolute path, not a relative path. The cell_number is 0-indexed. Use 
    edit_mode=insert to add a new cell at the index specified by cell_number. 
    Use edit_mode=delete to delete the cell at the index specified by 
    cell_number.
    """
    
    notebook_path: str = Field(
        ..., description="The absolute path to the Jupyter notebook file to edit (must be absolute, not relative)"
    )
    cell_id: Optional[str] = Field(
        default=None, description="The ID of the cell to edit. When inserting a new cell, the new cell will be inserted after the cell with this ID, or at the beginning if not specified."
    )
    new_source: str = Field(
        ..., description="The new source for the cell"
    )
    cell_type: Optional[Literal["code", "markdown"]] = Field(
        default=None, description="The type of the cell (code or markdown). If not specified, it defaults to the current cell type. If using edit_mode=insert, this is required."
    )
    edit_mode: Literal["replace", "insert", "delete"] = Field(
        default="replace", description="The type of edit to make (replace, insert, delete). Defaults to replace."
    )

    def run(self):
        """
        Edit the specified Jupyter notebook cell.
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
        
        # Step 4: Validate edit mode requirements
        if self.edit_mode == "insert" and self.cell_type is None:
            return "Error: cell_type is required when edit_mode is 'insert'"
        
        try:
            # Step 5: Read and parse notebook JSON
            with open(self.notebook_path, 'r', encoding='utf-8') as file:
                notebook_data = json.load(file)
            
            # Step 6: Validate notebook structure
            if 'cells' not in notebook_data:
                return f"Error: Invalid notebook format - no 'cells' found in '{self.notebook_path}'"
            
            cells = notebook_data['cells']
            
            # Step 7: Find target cell or position
            target_index = None
            target_cell = None
            
            if self.cell_id:
                # Find by cell ID
                for i, cell in enumerate(cells):
                    if cell.get('id') == self.cell_id:
                        target_index = i
                        target_cell = cell
                        break
                
                # Also try numeric cell ID (index)
                if target_index is None:
                    try:
                        cell_index = int(self.cell_id)
                        if 0 <= cell_index < len(cells):
                            target_index = cell_index
                            target_cell = cells[cell_index]
                    except ValueError:
                        pass
                
                if target_index is None:
                    return f"Error: Cell with ID '{self.cell_id}' not found in notebook"
            else:
                # If no cell_id provided, use first cell or insert at beginning
                if self.edit_mode == "insert":
                    target_index = 0
                elif cells:
                    target_index = 0
                    target_cell = cells[0]
                else:
                    return "Error: No cells in notebook and no cell_id specified"
            
            # Step 8: Perform the edit operation
            if self.edit_mode == "delete":
                if target_index is None or target_index >= len(cells):
                    return f"Error: Cannot delete cell - invalid index"
                
                deleted_cell = cells.pop(target_index)
                result_message = f"Successfully deleted cell {target_index} ({deleted_cell.get('cell_type', 'unknown')} type)"
            
            elif self.edit_mode == "insert":
                # Create new cell
                new_cell = {
                    "cell_type": self.cell_type,
                    "source": self._format_source(self.new_source),
                    "metadata": {}
                }
                
                # Add cell-type specific fields
                if self.cell_type == "code":
                    new_cell.update({
                        "execution_count": None,
                        "outputs": []
                    })
                
                # Generate a simple ID
                new_cell["id"] = f"cell-{len(cells)}"
                
                # Insert cell
                if self.cell_id:
                    # Insert after the specified cell
                    insert_position = target_index + 1 if target_index is not None else 0
                else:
                    # Insert at beginning
                    insert_position = 0
                
                cells.insert(insert_position, new_cell)
                result_message = f"Successfully inserted new {self.cell_type} cell at position {insert_position}"
            
            else:  # replace mode
                if target_index is None or target_index >= len(cells):
                    return f"Error: Cannot replace cell - invalid index"
                
                # Update cell source
                cells[target_index]["source"] = self._format_source(self.new_source)
                
                # Update cell type if specified
                if self.cell_type:
                    old_type = cells[target_index].get("cell_type", "unknown")
                    cells[target_index]["cell_type"] = self.cell_type
                    
                    # Add/remove type-specific fields
                    if self.cell_type == "code" and old_type != "code":
                        cells[target_index].setdefault("execution_count", None)
                        cells[target_index].setdefault("outputs", [])
                    elif self.cell_type == "markdown" and old_type == "code":
                        cells[target_index].pop("execution_count", None)
                        cells[target_index].pop("outputs", None)
                
                result_message = f"Successfully replaced cell {target_index} content"
            
            # Step 9: Write back to file
            with open(self.notebook_path, 'w', encoding='utf-8') as file:
                json.dump(notebook_data, file, indent=1, ensure_ascii=False)
            
            return result_message
            
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON in notebook file '{self.notebook_path}': {str(e)}"
        except PermissionError:
            return f"Error: Permission denied modifying notebook file '{self.notebook_path}'"
        except Exception as e:
            return f"Error editing notebook file '{self.notebook_path}': {str(e)}"
    
    def _format_source(self, source_text):
        """
        Format source text for notebook cell (ensure it's a list of lines).
        """
        if not source_text:
            return []
        
        # Split into lines and ensure each line ends with \n except the last
        lines = source_text.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            if i == len(lines) - 1 and line == '':
                # Skip empty last line
                continue
            elif i == len(lines) - 1:
                # Last line without newline
                formatted_lines.append(line)
            else:
                # All other lines with newline
                formatted_lines.append(line + '\n')
        
        return formatted_lines

if __name__ == "__main__":
    # Test case - create and edit a simple test notebook
    import tempfile
    
    test_notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "cell1",
                "source": ["# Original Title\n", "Original content"],
                "metadata": {}
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "cell2",
                "source": ["print('original code')"],
                "outputs": [],
                "metadata": {}
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
    
    # Test replacing a cell
    tool = NotebookEdit(
        notebook_path=test_file,
        cell_id="cell1",
        new_source="# Updated Title\nThis content has been updated!",
        edit_mode="replace"
    )
    result = tool.run()
    print("NotebookEdit replace test:")
    print(result)
    
    # Test inserting a new cell
    tool2 = NotebookEdit(
        notebook_path=test_file,
        cell_id="cell1",
        new_source="x = 42\nprint(f'The answer is {x}')",
        cell_type="code",
        edit_mode="insert"
    )
    result2 = tool2.run()
    print("\nNotebookEdit insert test:")
    print(result2)
    
    # Verify changes by reading back
    with open(test_file, 'r', encoding='utf-8') as f:
        updated_notebook = json.load(f)
        print(f"\nNotebook now has {len(updated_notebook['cells'])} cells")
        for i, cell in enumerate(updated_notebook['cells']):
            print(f"Cell {i}: {cell['cell_type']} - {''.join(cell['source'])[:50]}...")
    
    # Clean up
    os.unlink(test_file)
