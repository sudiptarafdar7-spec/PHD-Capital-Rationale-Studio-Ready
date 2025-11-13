"""
Shared path utilities for resolving job folder paths
"""
import os


def resolve_job_folder_path(folder_path):
    """
    Resolve job folder path to absolute path.
    Handles both relative paths (backend/job_files/...) and absolute paths.
    Fixes the double "backend" issue when Flask runs from backend/ directory.
    
    Args:
        folder_path: Path to resolve (e.g., 'backend/job_files/premium-xxx')
    
    Returns:
        Absolute path to the folder
    """
    if not folder_path:
        return None
    
    # If already absolute, return as-is
    if os.path.isabs(folder_path):
        return folder_path
    
    # Convert relative path to absolute
    # __file__ is at: /home/runner/workspace/backend/utils/path_utils.py
    # Go up 2 levels to reach workspace root: utils/ -> backend/ -> workspace/
    current_file = os.path.abspath(__file__)
    utils_dir = os.path.dirname(current_file)  # backend/utils/
    backend_dir = os.path.dirname(utils_dir)   # backend/
    workspace_root = os.path.dirname(backend_dir)  # workspace/
    
    return os.path.join(workspace_root, folder_path)
