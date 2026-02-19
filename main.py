import os
import tkinter as tk
from src.ui import ImageEditor
from src.config_manager import load_config

def ensure_folders():
    folders = ['projects', 'exports', 'assets']
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)

if __name__ == "__main__":
    ensure_folders()
    config = load_config()
    
    root = tk.Tk()
    root.geometry(config.get("window_size", "900x750"))
    app = ImageEditor(root)
    root.mainloop()