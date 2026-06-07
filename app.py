import sys
import os

# Ensure the current directory is in the path 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow

def main():
    print("Starting HueFlow AI Color Grader...")
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
