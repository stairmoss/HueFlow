import sys
import os

# Ensure the current directory is in the path 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import launch_app

def main():
    launch_app()

if __name__ == "__main__":
    main()
