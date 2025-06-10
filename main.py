import os
import random
import sys
import time

# ASCII art title
TITLE = r"""
   ██████╗████████╗███████╗ ████████╗ ██████╗  ██████╗ ██╗     ██╗  ██╗██╗████████╗
  ██╔════╝╚══██╔══╝██╔════╝ ╚══██╔══╝██╔═══██╗██╔═══██╗██║     ██║ ██╔╝██║╚══██╔══╝
  ██║        ██║   █████╗█████╗██║   ██║   ██║██║   ██║██║     █████╔╝ ██║   ██║   
  ██║        ██║   ██╔══╝╚════╝██║   ██║   ██║██║   ██║██║     ██╔═██╗ ██║   ██║   
  ╚██████╗   ██║   ██║         ██║   ╚██████╔╝╚██████╔╝███████╗██║  ██╗██║   ██║   
   ╚═════╝   ╚═╝   ╚═╝         ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝   ╚═╝   
"""

GLITCH_SYMBOLS = ['@', '#', '$', '%', '&', '?', '!', '*', '+', '=', '~', '^', '/', '\\', '|', '<', '>', '0', '1']
GLITCH_COLORS = [
    '\033[91m',  # Red
    '\033[94m',  # Blue
    '\033[95m',  # Magenta
    '\033[96m',  # Cyan
    '\033[97m',  # White
    '\033[93m',  # Yellow
]
RESET_COLOR = '\033[0m'

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

# Glitch effect animation
def glitch_title(duration=5, interval=0.08):
    start_time = time.time()
    title_lines = TITLE.splitlines()
    while time.time() - start_time < duration:
        clear()
        glitched_lines = []
        for line in title_lines:
            glitched_line = ''
            for char in line:
                if char != ' ' and random.random() < 0.18:
                    color = random.choice(GLITCH_COLORS)
                    symbol = random.choice(GLITCH_SYMBOLS)
                    glitched_line += f"{color}{symbol}{RESET_COLOR}"
                elif char != ' ' and random.random() < 0.12:
                    color = random.choice(GLITCH_COLORS)
                    glitched_line += f"{color}{char}{RESET_COLOR}"
                else:
                    glitched_line += char
            glitched_lines.append(glitched_line)
        print('\n'.join(glitched_lines))
        time.sleep(interval)
    # Final clean title
    clear()
    print("\033[92m" + TITLE + RESET_COLOR)
    time.sleep(0.5)

# Main execution
if __name__ == "__main__":
    try:
        glitch_title(duration=5)
        # Execute ctf_toolkit.py after animation
        if os.name == "nt":
            os.system("python ctf_toolkit.py")
        else:
            os.system("python3 ctf_toolkit.py")
    except Exception as e:
        print(f"Error during glitch animation or execution: {e}")
