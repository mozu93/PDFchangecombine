"""
PyInstaller runtime hook for win32com
Ensures proper COM initialization in frozen executables
"""

import sys
import os

# Add pywin32_system32 to PATH for DLL loading
if hasattr(sys, 'frozen'):
    # Get the path to _internal directory
    if hasattr(sys, '_MEIPASS'):
        pywin32_system32 = os.path.join(sys._MEIPASS, 'pywin32_system32')
    else:
        pywin32_system32 = os.path.join(os.path.dirname(sys.executable), 'pywin32_system32')

    if os.path.exists(pywin32_system32):
        os.environ['PATH'] = pywin32_system32 + os.pathsep + os.environ.get('PATH', '')
        # Also add DLL directory for Windows LoadLibrary
        try:
            os.add_dll_directory(pywin32_system32)
        except (OSError, AttributeError):
            pass

# Ensure win32com uses gen_py from temp directory
try:
    import win32com
    if hasattr(sys, 'frozen'):
        import win32com.client
        # Force dynamic dispatch for frozen apps
        win32com.client.gencache.is_readonly = True
except ImportError:
    pass
