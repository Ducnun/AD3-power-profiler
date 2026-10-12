import tkinter as tk

from gui.main_window import MainWindow


def main():
    root = tk.Tk()

    window = MainWindow(root)
    root.protocol("WM_DELETE_WINDOW", window.close)
    root.mainloop()

if __name__ == "__main__":
    main()
