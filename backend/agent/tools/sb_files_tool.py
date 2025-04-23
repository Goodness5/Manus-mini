from typing import Optional
from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.sandbox import SandboxToolsBase, Sandbox
from utils.files_utils import EXCLUDED_FILES, EXCLUDED_DIRS, EXCLUDED_EXT, should_exclude_file, clean_path

class SandboxFilesTool(SandboxToolsBase):
    """Tool for executing file system operations in an E2B sandbox environment."""

    def __init__(self, sandbox: Sandbox):
        super().__init__(sandbox)
        self.SNIPPET_LINES = 4  # Number of context lines to show around edits
        self.workspace_path = "/workspace"  # Ensure we're always operating in /workspace

    def clean_path(self, path: str) -> str:
        """Clean and normalize a path to be relative to /workspace"""
        return clean_path(path, self.workspace_path)

    def _should_exclude_file(self, rel_path: str) -> bool:
        """Check if a file should be excluded based on path, name, or extension"""
        return should_exclude_file(rel_path)

    async def _file_exists(self, path: str) -> bool:
        """Check if a file exists in the sandbox"""
        try:
            # Using the new files API
            files = self.sandbox.fs.list(path)
            return len(files) > 0
        except Exception:
            return False

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new file with the provided contents",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to be created, relative to /workspace"
                    },
                    "file_contents": {
                        "type": "string",
                        "description": "The content to write to the file"
                    }
                },
                "required": ["file_path", "file_contents"]
            }
        }
    })
    @xml_schema(
        tag_name="create-file",
        mappings=[
            {"param_name": "file_path", "node_type": "attribute", "path": "."},
            {"param_name": "file_contents", "node_type": "content", "path": "."}
        ],
        example='''
        <create-file file_path="src/main.py">
        File contents go here
        </create-file>
        '''
    )
    async def create_file(self, file_path: str, file_contents: str) -> ToolResult:
        file_path = self.clean_path(file_path)
        try:
            full_path = f"{self.workspace_path}/{file_path}"
            if await self._file_exists(full_path):
                return self.fail_response(f"File '{file_path}' already exists")
            
            # Create parent directories if needed
            parent_dir = '/'.join(full_path.split('/')[:-1])
            if parent_dir:
                self.sandbox.fs.write_dir(parent_dir)
            
            # Write the file content using the new API
            self.sandbox.fs.write(full_path, file_contents)
            
            return self.success_response(f"File '{file_path}' created successfully")
        except Exception as e:
            return self.fail_response(f"Error creating file: {str(e)}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "full_file_rewrite",
            "description": "Completely rewrite an existing file with new content",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to be rewritten, relative to /workspace"
                    },
                    "file_contents": {
                        "type": "string",
                        "description": "The new content to write to the file"
                    }
                },
                "required": ["file_path", "file_contents"]
            }
        }
    })
    @xml_schema(
        tag_name="full-file-rewrite",
        mappings=[
            {"param_name": "file_path", "node_type": "attribute", "path": "."},
            {"param_name": "file_contents", "node_type": "content", "path": "."}
        ],
        example='''
        <full-file-rewrite file_path="src/main.py">
        This completely replaces the entire file content
        </full-file-rewrite>
        '''
    )
    async def full_file_rewrite(self, file_path: str, file_contents: str) -> ToolResult:
        try:
            file_path = self.clean_path(file_path)
            full_path = f"{self.workspace_path}/{file_path}"
            if not await self._file_exists(full_path):
                return self.fail_response(f"File '{file_path}' does not exist")
            
            # Write the new content using the new API
            self.sandbox.fs.write(full_path, file_contents)
            
            return self.success_response(f"File '{file_path}' completely rewritten successfully")
        except Exception as e:
            return self.fail_response(f"Error rewriting file: {str(e)}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "str_replace",
            "description": "Replace specific text in a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the target file, relative to /workspace"
                    },
                    "old_str": {
                        "type": "string",
                        "description": "Text to be replaced (must appear exactly once)"
                    },
                    "new_str": {
                        "type": "string",
                        "description": "Replacement text"
                    }
                },
                "required": ["file_path", "old_str", "new_str"]
            }
        }
    })
    @xml_schema(
        tag_name="str-replace",
        mappings=[
            {"param_name": "file_path", "node_type": "attribute", "path": "."},
            {"param_name": "old_str", "node_type": "element", "path": "old_str"},
            {"param_name": "new_str", "node_type": "element", "path": "new_str"}
        ],
        example='''
        <str-replace file_path="src/main.py">
            <old_str>text to replace</old_str>
            <new_str>replacement text</new_str>
        </str-replace>
        '''
    )
    async def str_replace(self, file_path: str, old_str: str, new_str: str) -> ToolResult:
        try:
            file_path = self.clean_path(file_path)
            full_path = f"{self.workspace_path}/{file_path}"
            if not await self._file_exists(full_path):
                return self.fail_response(f"File '{file_path}' does not exist")
            
            # Read content using the new API
            content = self.sandbox.fs.read(full_path)
            old_str = old_str.expandtabs()
            new_str = new_str.expandtabs()
            
            occurrences = content.count(old_str)
            if occurrences == 0:
                return self.fail_response(f"String '{old_str}' not found in file")
            if occurrences > 1:
                lines = [i+1 for i, line in enumerate(content.split('\n')) if old_str in line]
                return self.fail_response(f"Multiple occurrences found in lines {lines}")
            
            # Perform replacement and write using the new API
            new_content = content.replace(old_str, new_str)
            self.sandbox.fs.write(full_path, new_content)
            
            return self.success_response("Replacement successful")
            
        except Exception as e:
            return self.fail_response(f"Error replacing string: {str(e)}")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file at the given path",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to be deleted, relative to /workspace"
                    }
                },
                "required": ["file_path"]
            }
        }
    })
    @xml_schema(
        tag_name="delete-file",
        mappings=[
            {"param_name": "file_path", "node_type": "attribute", "path": "."}
        ],
        example='''
        <delete-file file_path="src/main.py">
        </delete-file>
        '''
    )
    async def delete_file(self, file_path: str) -> ToolResult:
        try:
            file_path = self.clean_path(file_path)
            full_path = f"{self.workspace_path}/{file_path}"
            if not await self._file_exists(full_path):
                return self.fail_response(f"File '{file_path}' does not exist")
            
            # Delete file using the new API
            self.sandbox.fs.remove(full_path)
            return self.success_response(f"File '{file_path}' deleted successfully")
        except Exception as e:
            return self.fail_response(f"Error deleting file: {str(e)}")
