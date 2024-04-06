import time
import keyboard
import keymaps
from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import new4in2part
import textwrap
import subprocess
import signal
import os
from pathlib import Path
from waveshare_epd import epd2in13_V2  # Assuming you're using the Waveshare e-ink display library

# Initialize the e-Paper display
epd = new4in2part.EPD()
epd.init()
epd.Clear()

# Initialize display-related variables)
display_image = Image.new('1', (epd.width, epd.height), 255)
display_draw = ImageDraw.Draw(display_image)

# Display settings like font size, spacing, etc.
display_start_line = 0
font24 = ImageFont.truetype('Courier Prime.ttf', 18)  # 24
textWidth = 16
linespacing = 22
chars_per_line = 32  # 28
lines_on_screen = 12
last_display_update = time.time()

# display related
needs_display_update = True
needs_input_update = True
updating_input_area = False
input_catchup = False
display_catchup = False
display_updating = False
shift_active = False
control_active = False
exit_cleanup = False
console_message = ""
scrollindex = 1

# Initialize cursor position
cursor_position = 0

# Initialize text matrix (size of text file)
max_lines = 100  # Maximum number of lines, adjust as needed
max_chars_per_line = chars_per_line  # Maximum characters per line, adjust as needed
text_content = ""
temp_content = ""
input_content = ""
previous_lines = []
typing_last_time = time.time()  # Timestamp of last key press

# file directory setup: "/data/cache.txt"
file_path = os.path.join(os.path.dirname(__file__), 'data', 'cache.txt')

# Custom image path
custom_image_path = "/home/jman/bladerunner2049.jpg"

def load_previous_lines(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            return [line.strip() for line in lines]
    except FileNotFoundError:
        return []

def save_previous_lines(file_path, lines):
    with open(file_path, 'w') as file:
        for line in lines:
            file.write(line + '\n')

def update_display_and_shutdown():
    # Display the custom image
    display_image(custom_image_path)
    # Perform shutdown
    shutdown()

def update_display():
    global last_display_update
    global needs_display_update
    global cursor_index
    global previous_lines
    global display_updating
    global updating_input_area
    global console_message
    global current_line
    global scrollindex

    # Clear the main display area -- also clears input line (270-300)
    display_draw.rectangle((0, 0, 400, 300), fill=255)

    # Display the previous lines
    y_position = 270 - linespacing  # leaves room for cursor input

    # Make a temp array from previous_lines. And then reverse it and display as usual.
    current_line = max(0, len(previous_lines) - lines_on_screen * scrollindex)
    temp = previous_lines[current_line:current_line + lines_on_screen]

    for line in reversed(temp[-lines_on_screen:]):
       display_draw.text((10, y_position), line[:max_chars_per_line], font=font24, fill=0)
       y_position -= linespacing

    # Display Console Message
    if console_message != "":
        display_draw.rectangle((300, 270, 400, 300), fill=255)
        display_draw.text((300, 270), console_message, font=font24, fill=0)
        console_message = ""

    # Generate display buffer for display
    partial_buffer = epd.getbuffer(display_image)
    epd.display(partial_buffer)

    last_display_update = time.time()
    display_catchup = True
    display_updating = False
    needs_display_update = False

def update_input_area(): # This updates the input area of the typewriter (active line)
    global last_display_update
    global needs_display_update
    global cursor_index
    global needs_input_update
    global updating_input_area

    cursor_index = cursor_position
    display_draw.rectangle((0, 270, 400, 300), fill=255)  # Clear display

    # Add cursor
    temp_content = input_content[:cursor_index] + "|" + input_content[cursor_index:]

    # Draw input line text
    display_draw.text((10, 270), str(temp_content), font=font24, fill=0)

    # Generate display buffer for input line
    updating_input_area = True
    partial_buffer = epd.getbuffer(display_image)
    epd.display(partial_buffer)
    updating_input_area = False

def insert_character(character):
    global cursor_position
    global input_content
    global needs_display_update

    cursor_index = cursor_position

    if cursor_index <= len(input_content):
        # Insert character in the text_content string
        input_content = input_content[:cursor_index] + character + input_content[cursor_index:]
        cursor_position += 1  # Move the cursor forward

    needs_input_update = True

def delete_character():
    global cursor_position
    global input_content
    global needs_display_update

    cursor_index = cursor_position

    if cursor_index > 0:
        # Remove the character at the cursor position
        input_content = input_content[:cursor_index - 1] + input_content[cursor_index:]
        cursor_position -= 1  # Move the cursor back
        needs_input_update = True

def handle_key_down(e): # Keys being held, i.e., modifier keys
    global shift_active
    global control_active

    if e.name == 'shift':  # if shift is released
        shift_active = True
    if e.name == 'ctrl':  # if shift is released
        control_active = True

def handle_key_press(e):
    global cursor_position
    global typing_last_time
    global display_start_line
   