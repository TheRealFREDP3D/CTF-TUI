import os
import time
import sys

# ASCII art title
TITLE = r"""
░█▀▀░▀█▀░█▀▀░░░░░▀█▀░█▀█░█▀█░█░░░█░█░▀█▀░▀█▀
░█░░░░█░░█▀▀░▄▄▄░░█░░█░█░█░█░█░░░█▀▄░░█░░░█░
░▀▀▀░░▀░░▀░░░░░░░░▀░░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀▀▀░░▀░
"""

# Clear screen
def clear():
    os.system("cls" if os.name == "nt" else "clear")

# Flashing text animation
def flash_title(times=6, interval=0.3):
    for i in range(times):
        clear()
        if i % 2 == 0:
            print("\033[92m" + TITLE + "\033[0m")  # Green text
        else:
            print("\033[91m" + TITLE + "\033[0m")  # Red text
        time.sleep(interval)
    clear()

# Loading bar animation
def loading_bar(duration=5, length=50):
    print("\n\nLoading...")
    for i in range(length + 1):
        percent = int((i / length) * 100)
        bar = "[" + "#" * i + " " * (length - i) + f"] {percent}%"
        sys.stdout.write("\r" + bar)
        sys.stdout.flush()
        time.sleep(duration / length)
    print("\n")

# Main screen placeholder
def main_screen():
    clear()
    print("\033[94m")  # Blue text
    print(TITLE)
    print("\033[0m")
    print("Welcome to the CTF-TOOLKIT!")
    print("Available Modules:\n\n")
    print(" - Terminal")
    print(" - Markdown Notes")
    print(" - AI Assistant")
    print("\n\nTo start, run: python ctf_toolkit.py\n")

# Main execution
if __name__ == "__main__":
    flash_title()
    loading_bar()
    main_screen()
