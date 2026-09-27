# Base Modules
import pygame
import math
import numpy as np
import random
from collections import deque
import tkinter as tk

# Own Modules
import modules.ux_ui.settings_window as settings_window
import modules.simulation.chunk_grid as chunk_grid

# Ma Todo List for the entier Project :3333
'''
WHAT TO ADD:
    1. Numpy Vectors (Done ig)
    2. Chunk-System NOOWOOWOWOOWOWOWOWWWWWWWWWWWWWWW!!!!! | ONLY HISTORY LEFT
    3. Multi-Threading/Processing
    4. HashLife
'''
'''
WHAT TO FIX/OPTIMIZE:
    1. save_rle -> Numpy vectors (makes saving faster)
    2. history_1_step -> Save Deltas (makes history faster)
    3. center_cam -> Update for each add/remove cell instead of every CAM_CENTER_EVERY_GEN (makes it faster)
    4. Use State Enums (makes it cleaner)
    5. Use Modules instead of 1 big File (makes it cleaner) | Done a bit
    6. Cache preview/selection Surfaces instead of recreating every frame (makes it faster)
'''

# ---------------------------------- Change freely for Hotkeys etc. -------------------------------------
NUMPAD_HOTKEYS = {
    pygame.K_1: "Numpad/gosper_glider_gun.rle", # Hotkey Numpad 1
    pygame.K_2: "Numpad/eater.rle", # Hotkey Numpad 2
    pygame.K_3: "Numpad/buckaroo.rle", # Hotkey Numpad 3
    pygame.K_4: "Numpad/60p_glider_gun.rle", # Hotkey Numpad 4
    pygame.K_5: "Numpad/60p_and_gate.rle", # Hotkey Numpad 5
    pygame.K_6: "Numpad/60p_not_gate.rle", # Hotkey Numpad 6
    pygame.K_7: "Numpad/60p_or_gate.rle", # Hotkey Numpad 7
    pygame.K_8: "Numpad/duplicator.rle", # Hotkey Numpad 8
    pygame.K_9: "Numpad/60p_xor_gate.rle", # Hotkey Numpad 9
    pygame.K_0: "Numpad/"  # Hotkey Numpad 0
}
LOADING_FILE = "RLE/OCTA.rle" # Change if you want a different loaded .rle file
SAVING_FILE = "RLE/game.rle" # Change if you want a different filename for the saved .rle

WIDTH = 1000 # Game Window Width | Base = 1000
HEIGHT = 1000 # Game Window Height | Base = 1000

MIN_ZOOM = 0.0001 # Minimum Zoom Level | Base = 0.055
MAX_ZOOM = 10.0 # Maximum Zoom Level | Base = 10.0
CAM_CENTER_EVERY_GEN = 10 # Center the cam every X generations (for performance reasons) | Base = 10

HISTORY_LIMIT = 10000 # Limit of the Undo/Redo History
HISTORY_SAVE_EVERY_GEN = 10 # Save history every X generations (for performance reasons) | Base = 10 | In the Future 1

RANDOM_FILL_MAX_CELLS = 100000 # Maximum of Cells being randomly pasted at once | Base 100000
# ------------------------------------------------------------------------------------------------------

# Create Game Window + Base Values / Setup
pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

# ---------------- Touch Controls (Phone / Pydroid 3) ---------------- In future a own Module
TOUCH_MODE = False # Set to False to hide the button bar entirely (e.g. always-PC builds)
BUTTON_H = 50 # Height (in px) of a single button row

# Two rows of buttons
BUTTON_ROWS = [
    ["Play/Pause", "Step", "1Spd-", "1Spd+", "10Spd-", "10Spd+", "Zoom-", "Zoom+", "Center", "Undo", "Redo", "Clear"],
    ["Settings", "Mode", "Copy", "Paste", "Del", "RndFill", "RotCW", "RotCCW", "MirLR", "MirUD", "Save", "Load"],
]

# Build a rect for every button label, stacking the rows above the screen bottom.
BUTTON_RECTS = {} # label -> pygame.Rect
for row_index, row_labels in enumerate(BUTTON_ROWS):
    row_w = WIDTH // len(row_labels)
    row_y = HEIGHT - BUTTON_H * (len(BUTTON_ROWS) - row_index)
    for i, label in enumerate(row_labels):
        BUTTON_RECTS[label] = pygame.Rect(i * row_w, row_y, row_w, BUTTON_H)

touch_font = pygame.font.SysFont(None, 18)
active_fingers = {} # finger_id -> (x, y) in screen space, used for the 2-finger camera drag
SELECT_MODE = False # False = single tap toggles a cell (default). True = tap+drag makes a rect selection (like holding Rightclick on PC)

def draw_touch_buttons():
    """Draw the on-screen button bar. No-op if TOUCH_MODE is off."""
    if not TOUCH_MODE:
        return
    for label, rect in BUTTON_RECTS.items():
        # Highlight the Mode button green while select-mode is active, so it's obvious which mode you're in
        color = (70, 90, 70) if (label == "Mode" and SELECT_MODE) else (40, 40, 40)
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (90, 90, 90), rect, 1)
        text = touch_font.render(label, True, (255, 255, 255))
        screen.blit(text, text.get_rect(center=rect.center))

def handle_touch_button(pos):
    """
    If pos hits a button, perform its action and return True.
    Return False if pos didn't hit any button (caller should then treat it as a normal cell click).
    """
    global active, GpS, zoom, has_selection, dragging_selection, alive_selected_cells
    global clipboard, was_active_before_edit, selecting, SELECT_MODE, SHOW_SETTINGS
    if not TOUCH_MODE:
        return False

    for label, rect in BUTTON_RECTS.items():
        if not rect.collidepoint(pos):
            continue

        match label:
            case "Play/Pause":
                active = not active
            case "Step":
                if not active: # Only allow manual stepping while paused, same rule as the 'n' hotkey
                    manage_history("step")
                    chunk_grid.step(birth_values, survive_values)
            case "1Spd-":
                GpS = max(1, GpS - 1)
            case "1Spd+":
                GpS = min(1000, GpS + 1)
            case "10Spd-":
                GpS = max(1, GpS - 10)
            case "10Spd+":
                GpS = min(1000, GpS + 10)
            case "Zoom-":
                zoom = max(MIN_ZOOM, zoom / 1.2)
            case "Zoom+":
                zoom = min(MAX_ZOOM, zoom * 1.2)
            case "Center":
                center_cam()
            case "Undo":
                manage_history("undo")
            case "Redo":
                manage_history("redo")
            case "Clear":
                chunk_grid.clear_all()
                manage_history("reset")
            case "Settings":
                SHOW_SETTINGS = not SHOW_SETTINGS
            case "Mode":
                SELECT_MODE = not SELECT_MODE
            case "Copy":
                if has_selection:
                    clipboard = alive_selected_cells.copy()
                    has_selection = False
                    active = was_active_before_edit
            case "Paste":
                if paste_cells():
                    redo_history.clear()
            case "Del":
                if has_selection:
                    x_min, _, y_min, _ = get_max_min_from_selection()
                    cells_to_delete = original_selected_cells if dragging_selection else alive_selected_cells
                    if cells_to_delete:
                        history_1_step()
                        chunk_grid.remove_cells({(dx + x_min, dy + y_min) for (dx, dy) in cells_to_delete})
                        redo_history.clear()
                    dragging_selection = False
                    has_selection = False
                    active = was_active_before_edit
            case "RndFill":
                if has_selection and not dragging_selection:
                    random_fill()
                    has_selection = False
                    active = was_active_before_edit
            case "RotCW":
                if clipboard: # Only rotates the clipboard content (not an active drag) to keep this simple on touch
                    clipboard = rotate_cells(clipboard, clockwise=True)
            case "RotCCW":
                if clipboard:
                    clipboard = rotate_cells(clipboard, clockwise=False)
            case "MirLR":
                if clipboard:
                    clipboard = mirror_cells(clipboard, x_axis=True)
            case "MirUD":
                if clipboard:
                    clipboard = mirror_cells(clipboard, x_axis=False)
            case "Save":
                if save_rle(SAVING_FILE):
                    print("Saved .rle!")
            case "Load":
                chunk_grid.clear_all()
                chunk_grid.set_cells(load_rle(LOADING_FILE), 1)
                manage_history("reset")
                center_cam()
                print("Loaded .rle!")
                if has_selection or selecting or dragging_selection:
                    has_selection = False
                    selecting = False
                    dragging_selection = False
                    active = was_active_before_edit
        return True
    return False

def touch_select_start(pos):
    """Begin a touch-based rect selection (the SELECT_MODE equivalent of holding Rightclick)."""
    global start, end, has_selection, selecting, was_active_before_edit, active
    step = get_step()
    x = math.floor((pos[0] + camera_x) // step)
    y = math.floor((pos[1] + camera_y) // step)
    start = (x, y)
    end = start
    has_selection = False
    selecting = True
    was_active_before_edit = active
    active = False

def touch_select_update(pos):
    """Update the in-progress touch selection rect as the finger drags."""
    global end
    if selecting:
        step = get_step()
        x = math.floor((pos[0] + camera_x) // step)
        y = math.floor((pos[1] + camera_y) // step)
        end = (x, y)

def touch_select_end():
    """Finish the touch selection and lock in the selected cells."""
    global selecting, has_selection, alive_selected_cells
    if selecting:
        selecting = False
        has_selection = True
        alive_selected_cells = get_selection()

# ---------------- Mobile Settings Overlay (replaces the Tkinter window on Pydroid) ------
SHOW_SETTINGS = False
active_field = None # Which field is currently being typed into (None = no field focused)
FIELD_ORDER = ["birth", "survive", "color", "density"]
FIELD_LABELS = {
    "birth": "Birth (e.g. 3)",
    "survive": "Survive (e.g. 23)",
    "color": "Color Hex (e.g. f5a9b8)",
    "density": "Random Fill Density % (0-100)",
}
# Field values are seeded from whatever settings_window currently reports (works whether
# the Tkinter window loaded fine on PC, or the phone-fallback lambdas are active).
settings_fields = {
    "birth": "".join(str(n) for n in sorted(birth_values)) if "birth_values" in dir() else "3",
    "survive": "".join(str(n) for n in sorted(survive_values)) if "survive_values" in dir() else "23",
    "color": "".join(f"{c:02x}" for c in settings_window.give_cell_color()),
    "density": str(getattr(settings_window, "density_percent", 37)),
}

FIELD_RECTS = {}
_field_y = 100
for _f in FIELD_ORDER:
    FIELD_RECTS[_f] = pygame.Rect(50, _field_y, WIDTH - 100, 40)
    _field_y += 60
APPLY_RECT = pygame.Rect(50, _field_y + 20, WIDTH - 100, 50)
settings_font = pygame.font.SysFont(None, 24)

def apply_mobile_settings():
    """Parse the 4 text fields and push valid values into the running simulation."""
    global birth_values, survive_values
    birth = {int(c) for c in settings_fields["birth"] if c.isdigit()}
    survive = {int(c) for c in settings_fields["survive"] if c.isdigit()}
    if birth:
        birth_values = birth
    if survive:
        survive_values = survive

    color_str = settings_fields["color"].strip().lstrip("#")
    if len(color_str) == 6 and all(c.upper() in "0123456789ABCDEF" for c in color_str):
        rgb = tuple(int(color_str[i:i + 2], 16) for i in (0, 2, 4))
        settings_window.give_cell_color = lambda rgb=rgb: rgb

    try:
        density = float(settings_fields["density"])
        if 0 <= density <= 100:
            settings_window.density_percent = density
    except ValueError:
        pass

def draw_settings_overlay():
    """Draw the mobile settings overlay (dark background + 4 fields + Apply button)."""
    if not SHOW_SETTINGS:
        return
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 220))
    screen.blit(overlay, (0, 0))

    for f in FIELD_ORDER:
        rect = FIELD_RECTS[f]
        border_color = (255, 255, 0) if active_field == f else (90, 90, 90)
        pygame.draw.rect(screen, (30, 30, 30), rect)
        pygame.draw.rect(screen, border_color, rect, 2)
        label = settings_font.render(FIELD_LABELS[f], True, (150, 150, 150))
        screen.blit(label, (rect.x, rect.y - 20))
        value = settings_font.render(settings_fields[f], True, (255, 255, 255))
        screen.blit(value, (rect.x + 10, rect.y + 8))

    pygame.draw.rect(screen, (70, 120, 70), APPLY_RECT)
    apply_text = settings_font.render("Apply & Close", True, (255, 255, 255))
    screen.blit(apply_text, apply_text.get_rect(center=APPLY_RECT.center))

def handle_settings_click(pos):
    """
    If the settings overlay is open, handle a tap on it (field focus or Apply) and
    return True so the caller swallows the click (never falls through to cell-toggling).
    Returns False only when the overlay isn't open at all.
    """
    global active_field, SHOW_SETTINGS
    if not SHOW_SETTINGS:
        return False

    for f in FIELD_ORDER:
        if FIELD_RECTS[f].collidepoint(pos):
            active_field = f
            pygame.key.start_text_input() # Triggers Android's on-screen keyboard
            pygame.key.set_text_input_rect(FIELD_RECTS[f])
            return True

    if APPLY_RECT.collidepoint(pos):
        apply_mobile_settings()
        SHOW_SETTINGS = False
        active_field = None
        pygame.key.stop_text_input()
        return True

    return True # Any other tap while the overlay is open is swallowed too (modal behaviour)

# Basic GoL stuffies :3
gen = 0
accumulator = 0
GpS = 1
fps = 60
game_running = True
active = True

# Cam stuff
camera_x = 0.0
camera_y = 0.0
zoom = 1.0
dragging = False
last_mouse_pos = (0, 0)

# Grid/Cell shtuff
line_width = 1
cell_size = 10

# Copy/Paste Tuffies
alive_selected_cells = set()
clipboard = set()
original_selected_cells = set()
dragging_selection = False
start_drag_selection = None
was_active_before_edit = False

# Undo/Redo thingy
history = deque(maxlen=HISTORY_LIMIT)
redo_history = deque(maxlen=HISTORY_LIMIT)

# The Copy/Paste/Drag thingys
selecting = False
has_selection = False
start = None
end = None

# Base birth values
birth_values = {3}
survive_values = {2, 3}

# Settings Window function to apply new rules from the settings window
def apply_new_rules(birth, survive):
    global birth_values, survive_values
    birth_values = birth
    survive_values = survive

try:
    settings_root = settings_window.create_settings_window(apply_new_rules)  # create the root with the settings window
except Exception:  # If using Pydroid 3 (phone):
    settings_root = None
    settings_window.give_checkbox_toggles = lambda: (False, False, False)
    settings_window.give_cell_color = lambda: (245, 169, 184)
    settings_window.density_percent = 37

# Update the GpS on Key Input
def update_speed(GpS, keys):
    if keys[pygame.K_LEFT] and GpS > 1: # Decrease Speed by 1
        GpS -= 1
    if keys[pygame.K_DOWN]: # Decrease Speed by 10 or lower
        for _ in range(10):
            if GpS == 1:
                break
            GpS -= 1
    if keys[pygame.K_RIGHT] and GpS < 1000: # Increase Speed by 1
        GpS += 1
    if keys[pygame.K_UP]: # Increase Speed by 10 or lower
        for _ in range(10):
            if GpS == 1000:
                break
            GpS += 1

    return GpS

# IN DA FUTURE MOVE THE 3 HELPY HELPERS HELP FUNCS IN A DIFFERENT MODULE / FILE
# Another helpy func with gives the step num
def get_step():
    return cell_size * zoom

# A lil help function to get the mouse pos in world cordinates
def get_mouse_world_pos():
    step = get_step()
    mx, my = pygame.mouse.get_pos()

    x = math.floor((mx + camera_x) // step)
    y = math.floor((my + camera_y) // step)

    return (x,y)

def get_max_min_from_selection():
    x_min, y_min = min(start[0], end[0]), min(start[1], end[1])
    x_max, y_max = max(start[0], end[0]), max(start[1], end[1])
    return (x_min, x_max, y_min, y_max)
# YE THESE 3 FUNCS ABOVE IN THE DIFFERENT MODULE / FILE IN DA FUTURE 

# Center the cam so you can see every cell 
def center_cam():
    global zoom, camera_x, camera_y
    bbox = chunk_grid.global_bbox()
    if not bbox:
        return

    min_x, min_y, max_x, max_y  = bbox

    pattern_height = (max_y - min_y + 1) * cell_size
    pattern_width = (max_x - min_x + 1) * cell_size

    zoom = min(MAX_ZOOM, max(MIN_ZOOM, min(WIDTH / pattern_width, HEIGHT / pattern_height) * 0.9))

    center_y = (min_y + max_y + 1) / 2 * cell_size
    center_x = (min_x + max_x + 1) / 2 * cell_size

    camera_x = center_x * zoom - WIDTH / 2
    camera_y = center_y * zoom - HEIGHT / 2

# Save the game state with "Ctrl + s"
def save_rle(file): # Move save / load in a different Module
    bbox = chunk_grid.global_bbox()
    if not bbox: # If no alive cells on the board, don't save
        return False

    min_x, min_y, max_x, max_y = bbox

    width = max_x - min_x + 1
    height = max_y - min_y + 1

    lines_out = []
    for y in range(min_y, max_y + 1):
        row_str = ""
        run_char = None
        run_count = 0

        for x in range(min_x, max_x + 1):
            cell_char = "o" if chunk_grid.get_cell(x, y) == 1 else "b"

            if cell_char == run_char:
                run_count += 1
            else:
                if run_char is not None:
                    row_str += (str(run_count) if run_count > 1 else "") + run_char
                run_char = cell_char
                run_count = 1

        if run_char == "o": # Add an last alive if alive else dont add dead
            row_str += (str(run_count) if run_count > 1 else "") + run_char

        lines_out.append(row_str)

    pattern_str = "$".join(lines_out) + "!"

    try:
        with open(file, "w") as f:
            birth_str = "".join(str(n) for n in sorted(birth_values))
            survive_str = "".join(str(n) for n in sorted(survive_values))
            f.write(f"x = {width}, y = {height}, rule = B{birth_str}/S{survive_str}\n")
            f.write(pattern_str + "\n")
        return True
    except (OSError, PermissionError):
        print(f"Couldn't save the file: {file}")
        return False

# Load the rle file with "Ctrl + l"
def load_rle(file): # CHANGE 2
    try:
        global birth_values, survive_values

        new_alive = set()
        x, y = 0, 0

        with open(file, "r") as f: # Read the file
            lines = f.readlines()

        pattern_lines = []
        for line in lines: # Ignore comments
            line = line.strip()
            if line.startswith("#"):
                continue
            if line.startswith("x"): # Read the rules
                rules = line.split()[-1]
                birth_rule_str = rules.split("/")[0]
                survive_rule_str = rules.split("/")[1]
                birth_values = {int(char) for char in birth_rule_str if char.isdigit()}
                survive_values = {int(char) for char in survive_rule_str if char.isdigit()}
                print(f"Loading changed rules to: {rules}")
                continue 
            pattern_lines.append(line)

        pattern_str = "".join(pattern_lines) # Make it 1 Line

        count_str = ""
        for char in pattern_str:
            if char.isdigit():
                count_str += char
            elif char == "b" or char == ".":
                count = int(count_str) if count_str else 1
                x += count
                count_str = ""
            elif char == "o":
                count = int(count_str) if count_str else 1
                for i in range(count):
                    new_alive.add((x + i, y))
                x += count
                count_str = ""
            elif char == "$":
                count = int(count_str) if count_str else 1
                x = 0
                y += count
            elif char == "!":
                break

        return new_alive

    except (FileNotFoundError, IsADirectoryError, PermissionError, IndexError):
        print(f"Couldn't load the file: {file}")
        return set() # Else create a empty game state if none exists
    
# Numpad hotkeys:
def numpad(event):
    global clipboard
    if event.type == pygame.KEYDOWN:
        if event.key in NUMPAD_HOTKEYS:
            file = NUMPAD_HOTKEYS[event.key]
            clipboard = load_rle(file)

# Draw the base grid
def draw_grid(line_width):
    step = get_step()
    grid_width = max(1, int(line_width * zoom))

    start_x = int(camera_x // step) - 1
    end_x = int(start_x + WIDTH // step + 2)

    for x in range(start_x, end_x): # |
        pos = round(x * step - camera_x)

        pygame.draw.line(screen, (20, 20, 20), (pos, 0), (pos, HEIGHT), grid_width)

    start_y = int(camera_y // step) - 1
    end_y = int(start_y + HEIGHT // step + 2)

    for y in range(start_y, end_y): # ⏤
        pos = round(y * step - camera_y)

        pygame.draw.line(screen, (20, 20, 20), (0, pos), (WIDTH, pos), grid_width)

# Toggle alive/dead on click
def click_cell():
    global has_selection, dragging_selection, start_drag_selection, was_active_before_edit, active, original_selected_cells

    x, y = get_mouse_world_pos()

    if has_selection and not point_in_selection(x,y):
        has_selection = False
        active = was_active_before_edit
        return False
    elif has_selection:
        dragging_selection = True
        start_drag_selection = (x,y)
        original_selected_cells = get_selection()
        return False

    history_1_step() # Checkpoint the pre-edit state so this toggle can be undone
    chunk_grid.set_cell(x, y, 1 - chunk_grid.get_cell(x, y)) # Toggle the cell state
    return True

# Fast Numpy Draw cells (one big image not many smoll images)
def draw_cells_from_grid():
    bbox = chunk_grid.global_bbox()
    if bbox is None:
        return
    step = get_step()

    view_min_x, view_min_y = math.floor(camera_x / step), math.floor(camera_y / step)
    view_max_x, view_max_y = math.ceil((camera_x + WIDTH) / step), math.ceil((camera_y + HEIGHT) / step)

    size = chunk_grid.CHUNK_SIZE
    cx_start, cx_end = view_min_x // size, (view_max_x - 1) // size
    cy_start, cy_end = view_min_y // size, (view_max_y - 1) // size

    min_x, min_y, max_x, max_y = bbox
    bbox_cx_start, bbox_cx_end = min_x // size, max_x // size
    bbox_cy_start, bbox_cy_end = min_y // size, max_y // size

    cx_start = max(cx_start, bbox_cx_start)
    cx_end = min(cx_end, bbox_cx_end)
    cy_start = max(cy_start, bbox_cy_start)
    cy_end = min(cy_end, bbox_cy_end)

    cell_color = settings_window.give_cell_color()

    for cx in range(cx_start, cx_end + 1):
        for cy in range(cy_start, cy_end + 1):
            chunk = chunk_grid.chunks.get((cx, cy))
            if chunk is None:
                continue

            chunk_world_x, chunk_world_y = cx * size, cy * size

            x_start = max(0, view_min_x - chunk_world_x)
            x_end = min(size, view_max_x - chunk_world_x)
            y_start = max(0, view_min_y - chunk_world_y)
            y_end = min(size, view_max_y - chunk_world_y)

            if x_start >= x_end or y_start >= y_end:
                continue

            visible = chunk[y_start:y_end, x_start:x_end]
            if not visible.any():
                continue

            rgb = np.stack([visible*cell_color[0], visible*cell_color[1], visible*cell_color[2]], axis=-1)
            surf = pygame.surfarray.make_surface(rgb.swapaxes(0,1))

            # Round the screen-space edges first, then derive size from them to prevent lines through the shapes
            screen_x_start = round((chunk_world_x + x_start) * step - camera_x)
            screen_x_end = round((chunk_world_x + x_end) * step - camera_x)
            screen_y_start = round((chunk_world_y + y_start) * step - camera_y)
            screen_y_end = round((chunk_world_y + y_end) * step - camera_y)

            target_w = max(1, screen_x_end - screen_x_start)
            target_h = max(1, screen_y_end - screen_y_start)

            if (target_w, target_h) != (x_end - x_start, y_end - y_start):
                surf = pygame.transform.scale(surf, (target_w, target_h))

            screen.blit(surf, (screen_x_start, screen_y_start))

# Helpy functions for rotate/drag
def get_center_for(thing):
    if not thing:
        return (0, 0)

    xs = [x for x, _ in thing]
    ys = [y for _, y in thing]

    center_x = round((min(xs) + max(xs)) / 2)
    center_y = round((min(ys) + max(ys)) / 2)

    return (center_x, center_y)

def rotate_cells(thing, clockwise=True): # Rotate around da center
    if not thing:
        return set()

    center_x, center_y = get_center_for(thing)

    if clockwise:
        return {((y - center_y) + center_x, (-x + center_x) + center_y) for (x, y) in thing}
    else:
        return {((-y + center_y) + center_x, (x - center_x) + center_y) for (x, y) in thing}

def mirror_cells(thing, x_axis=True): # Mirror around the center
    if not thing:
        return set()

    center_x, center_y = get_center_for(thing)

    if x_axis:
        return {(2 * center_x - x, y) for (x, y) in thing}
    else:
        return {(x, 2 * center_y - y) for (x, y) in thing}
    
def select_field(event): 
    global selecting, has_selection, dragging_selection, start, end, alive_selected_cells, clipboard, start_drag_selection, was_active_before_edit, active, original_selected_cells
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 3 and not dragging_selection: # Start Selecting
            x, y = get_mouse_world_pos()

            start = (x,y)
            end = start
            has_selection = False
            selecting = True
            was_active_before_edit = active
            active = False

    if event.type == pygame.MOUSEBUTTONUP:
        if event.button == 3: # Stop Selecting
            selecting = False
            has_selection = True
            alive_selected_cells = get_selection()
        if dragging_selection and event.button == 1: # Stop Drag
            dragging_selection = False
            has_selection = False
            x_min, _, y_min, _ = get_max_min_from_selection()
            x, y = get_mouse_world_pos()
            delta_x = x - start_drag_selection[0]
            delta_y = y - start_drag_selection[1]

            if delta_x != 0 or delta_y != 0: # Only touch history if the selection actually moved
                old_positions = {(dx + x_min, dy + y_min) for (dx, dy) in original_selected_cells}
                new_positions = {(dx + x_min + delta_x, dy + y_min + delta_y) for (dx, dy) in alive_selected_cells}
                history_1_step() # Checkpoint the pre-drag state so the move can be undone
                chunk_grid.remove_cells(old_positions)
                chunk_grid.set_cells(new_positions, 1)
                redo_history.clear()

            active = was_active_before_edit

    if event.type == pygame.MOUSEMOTION:
        if selecting: # While you hold rightclick select duh
            x, y = get_mouse_world_pos()
            end = (x,y)

    if event.type == pygame.KEYDOWN:
        if has_selection and event.key == pygame.K_BACKSPACE: # Delete Selected
            x_min, _, y_min, _ = get_max_min_from_selection()
            cells_to_delete = original_selected_cells if dragging_selection else alive_selected_cells
            if cells_to_delete: # Only touch history if the selection actually has cells to delete
                history_1_step() # Checkpoint the pre-delete state so the deletion can be undone
                chunk_grid.remove_cells({(dx+x_min, dy+y_min) for (dx,dy) in cells_to_delete})
                redo_history.clear()
            dragging_selection = False
            has_selection = False
            active = was_active_before_edit

        if event.key == pygame.K_a:
            if dragging_selection and alive_selected_cells: # Rotate the drag | CW
                alive_selected_cells = rotate_cells(alive_selected_cells, clockwise=True)
            elif clipboard: # Rotate the Copy to Paste | CW
                clipboard = rotate_cells(clipboard, clockwise=True)

        if event.key == pygame.K_d:
            if dragging_selection and alive_selected_cells: # Rotate the drag | CCW
                alive_selected_cells = rotate_cells(alive_selected_cells, clockwise=False)
            elif clipboard: # Rotate the Copy to Paste | CCW
                clipboard = rotate_cells(clipboard, clockwise=False)

        if event.key == pygame.K_s:
            if dragging_selection and alive_selected_cells: # Mirror the drag up down
                alive_selected_cells = mirror_cells(alive_selected_cells, x_axis=False)
            elif clipboard: # Mirror the Copy to Paste up down
                clipboard = mirror_cells(clipboard, x_axis=False)

        if event.key == pygame.K_w:
            if dragging_selection and alive_selected_cells: # Mirror the drag left right
                alive_selected_cells = mirror_cells(alive_selected_cells, x_axis=True)
            elif clipboard: # Mirror the Copy to Paste left right
                clipboard = mirror_cells(clipboard, x_axis=True)

# Draw the select rect with start(x,y) and end(x,y)
def draw_selection():
    step = get_step()
    if selecting or has_selection:
        x_min = min(start[0], end[0])
        y_min = min(start[1], end[1])
        width = abs(end[0] - start[0]) + 1
        height = abs(end[1] - start[1]) + 1

        rect = pygame.Rect(
            round(x_min * step - camera_x),
            round(y_min * step - camera_y),
            round(width * step),
            round(height * step)
        )

        fill_surface = pygame.Surface((round(width*step), round(height*step)), pygame.SRCALPHA)
        fill_surface.fill((0, 32, 255, 80))  # RGBA for a blue rect
        
        screen.blit(fill_surface, (rect.x, rect.y))

        pygame.draw.rect(screen, (0,32,255), rect, max(1, int(line_width * zoom)))

# Check if the cell is in the rect
def point_in_selection(x,y):
    x_min, x_max, y_min, y_max = get_max_min_from_selection()
    return x_min <= x <= x_max and y_min <= y <= y_max

# Get every alive cell in rect
def get_selection():
    x_min, x_max, y_min, y_max = get_max_min_from_selection()
    alive_rect_cells = chunk_grid.iterate_alive_in_rect(x_min, y_min, x_max, y_max)
    return {(x - x_min, y - y_min) for (x, y) in alive_rect_cells}

# Paste the clipboard
def paste_cells():
    if not clipboard: # Nothing to paste -> don't waste a history slot / wipe redo on a no-op
        return False

    x, y = get_mouse_world_pos()
    cordinates_clipboard = {(dx + x, dy + y) for (dx, dy) in clipboard}
    history_1_step() # Checkpoint the pre-paste state so the paste can be undone
    chunk_grid.set_cells(cordinates_clipboard, 1)
    return True

# Draw a lil preview where/what you will paste
def draw_paste_preview():
    if not clipboard:
        return
    step = get_step()
    x, y = get_mouse_world_pos()
    cell_color_rgb = settings_window.give_cell_color()
    cell_color_rgba = (*cell_color_rgb, 80)

    xs = [dx + x for dx, _ in clipboard]
    ys = [dy + y for _, dy in clipboard]
    min_x, min_y = min(xs), min(ys)
    width = round((max(xs) - min_x + 1) * step)
    height = round((max(ys) - min_y + 1) * step)

    overlay = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)
    for dx, dy in clipboard:
        px, py = round((dx + x - min_x) * step), round((dy + y - min_y) * step)
        overlay.fill(cell_color_rgba, pygame.Rect(px, py, max(1, round(step)), max(1, round(step))))

    screen.blit(overlay, (round(min_x * step - camera_x), round(min_y * step - camera_y)))

def draw_drag_preview():
    if dragging_selection:
        step = get_step()
        x, y = get_mouse_world_pos()
        
        delta_x = x - start_drag_selection[0]
        delta_y = y - start_drag_selection[1]
        x_min = min(start[0], end[0])
        y_min = min(start[1], end[1])

        for (dx, dy) in alive_selected_cells:
            absolute_x = dx + x_min 
            absolute_y = dy + y_min
            new_x = absolute_x + delta_x
            new_y = absolute_y + delta_y

            fill_surface = pygame.Surface((max(1, round(step)), max(1, round(step))), pygame.SRCALPHA)
            cell_color_rgb = settings_window.give_cell_color()
            cell_color_rgba = (*cell_color_rgb, 80)
            fill_surface.fill(cell_color_rgba)  # RGBA color_hex
            screen.blit(fill_surface, (round(new_x*step - camera_x), round(new_y*step - camera_y)))

def _reset_selection_state(): # Clear any selection/drag state so it can't reference a now-stale grid
    global has_selection, selecting, dragging_selection, active
    if has_selection or selecting or dragging_selection:
        has_selection = False
        selecting = False
        dragging_selection = False
        active = was_active_before_edit

# UPDATE HISTORY LATER FOR ACTUAL UNDO ETC
def history_1_step(): # Move the 4 History Funcs in a "History" Module
    global history, redo_history
    history.append(gen)
    redo_history.clear()
    chunk_grid.clear_dirty()

def history_undo():
    global history, redo_history, gen
    if history:
        redo_history.append(gen)
        gen = history.pop()
        _reset_selection_state()

def history_redo():
    global history, redo_history, gen
    if redo_history:
        history.append(gen)
        gen = redo_history.pop()
        _reset_selection_state()

def manage_history(action):
    global gen, history, redo_history
    if action == "step":
        if gen % HISTORY_SAVE_EVERY_GEN == 0:  # Save history every X generations
            history_1_step()
        gen += 1
    elif action == "undo":
        history_undo()
    elif action == "redo":
        history_redo()
    elif action == "reset":
        history.clear()
        redo_history.clear()
        gen = 0

# Create a random soup fill
def random_fill():
    x_min, x_max, y_min, y_max = get_max_min_from_selection()
    density_percent = settings_window.density_percent  # get desity from settings_window (% value)

    # Convert % in int for the loop
    max_cells = (x_max + 1 - x_min) * (y_max + 1 - y_min)
    density = round(max(1, (max_cells * density_percent) / 100))
    density = min(density, RANDOM_FILL_MAX_CELLS) # Clamp cap, for anti crash reasons

    added_cells = {(random.randrange(x_min, x_max + 1),random.randrange(y_min, y_max + 1)) for _ in range(density)} # Add prevention for multiple cells at 1 spot

    history_1_step()
    chunk_grid.set_cells(added_cells, 1)
    redo_history.clear()

# Print the Controls + Intro
print("Welcome to GoL:\n")
print("Controls:")
print("  'Space'                = Pause")
print("  't'                    = Clear / Terminate")
print("  'n'                    = Go 1 Step / Gen")
print("  'f'                    = Center cam once")
print("  'Right'                = +1 GpS")
print("  'Up'                   = +10 GpS")
print("  'Left'                 = -1 GpS")
print("  'Down'                 = -10 GpS")
print("  'Ctrl + k'             = Save .rle file") 
print("  'Ctrl + l'             = Load .rle file")
print("  'Ctrl + z'             = Undo by 1")
print("  'Ctrl + u'             = Undo by 10")
print("  'Ctrl + y'             = Redo by 1")
print("  'Ctrl + x'             = Redo by 10")
print("  'Ctrl + c + Selected'  = Copy")
print("  'Ctrl + v + Selected'  = Paste")
print("  'a + Drag'             = Turn CW")
print("  'd + Drag'             = Turn CCW")
print("  'w + Drag'             = Mirror left right")
print("  's + Drag'             = Mirror up down")
print("  'LeftClick'            = Toggle alive/dead")
print("  'LeftClick + Selected' = Drag")
print("  'Backspace + Selected' = Delete")
print("  'r + Selected'         = Random fill the selected rect")
print("  'Hold Rightclick'      = Select")
print("  'MouseWheel'           = Zoom")
print("  'Hold MouseWheel'      = Move cam")
print("  '0-9'                  = Print hotkeys\n")
print("On phone (Pydroid 3): use the on-screen button bar + the 'Mode' button")
print("to switch between tap-to-toggle and tap+drag-to-select, plus 2-finger")
print("drag to move the camera.\n")

# Start of Game / Main Loop
while game_running:
    show_preview, disable_grid, cam_in_center = settings_window.give_checkbox_toggles()
    if settings_root is not None:  # Protection for if it runs on Pydroid 3 (Phone)
        try: 
            settings_root.update()
        except tk.TclError:
            pass

    keys = pygame.key.get_pressed() # Setup the key events

    screen.fill((0, 0, 0)) # Make everything black

    for event in pygame.event.get(): # Move in "Input" Module in future
        if event.type == pygame.QUIT: # So you can close the Window lol
            game_running = False

        if event.type == pygame.KEYDOWN:
            # While a mobile settings text field is focused, keystrokes go into that
            # field instead of triggering any of the normal hotkeys below.
            if active_field is not None:
                if event.key == pygame.K_BACKSPACE:
                    settings_fields[active_field] = settings_fields[active_field][:-1]
                elif event.key == pygame.K_RETURN:
                    active_field = None
                    pygame.key.stop_text_input()
                continue

            # Toggle active
            if event.key == pygame.K_SPACE and not has_selection and not selecting and not dragging_selection:
                active = not active
            if event.key == pygame.K_k and event.mod & pygame.KMOD_CTRL: # Save
                if save_rle(SAVING_FILE):
                    print("Saved .rle!")
            if event.key == pygame.K_l and event.mod & pygame.KMOD_CTRL: # Load
                chunk_grid.clear_all()
                chunk_grid.set_cells(load_rle(LOADING_FILE), 1) 
                manage_history("reset")
                center_cam()
                print("Loaded .rle!")
                if has_selection or selecting or dragging_selection:
                    has_selection = False
                    selecting = False
                    dragging_selection = False
                    active = was_active_before_edit
            if event.key == pygame.K_n and not active and not has_selection and not selecting and not dragging_selection: # +1 Step
                manage_history("step")
                chunk_grid.step(birth_values, survive_values)
                if cam_in_center and gen % CAM_CENTER_EVERY_GEN == 0: # Only center cam every CAM_CENTER_EVERY_GEN for performance
                    center_cam()
            if event.key == pygame.K_t: # Clear / Terminate
                chunk_grid.clear_all()
                manage_history("reset")
                if has_selection or selecting or dragging_selection:
                    has_selection = False
                    selecting = False
                    dragging_selection = False
                    active = was_active_before_edit

            if event.key == pygame.K_z and event.mod & pygame.KMOD_CTRL: # Undo by 1 History step (1 * HISTORY_SAVE_EVERY_GEN) on ctrl + z press 
                manage_history("undo")

            if event.key == pygame.K_u and event.mod & pygame.KMOD_CTRL: # Undo by 10 History steps (10 * HISTORY_SAVE_EVERY_GEN) on ctrl + u press
                steps = min(10, len(history))

                for _ in range(steps):
                    manage_history("undo")

            if event.key == pygame.K_y and event.mod & pygame.KMOD_CTRL: # Redo by 1 History step (1 * HISTORY_SAVE_EVERY_GEN) on ctrl + y press
                manage_history("redo")

            if event.key == pygame.K_x and event.mod & pygame.KMOD_CTRL: # Redo by 10 History steps (10 * HISTORY_SAVE_EVERY_GEN) on ctrl + x press
                steps = min(10, len(redo_history))

                for _ in range(steps):
                    manage_history("redo")

            if event.key == pygame.K_c and event.mod & pygame.KMOD_CTRL and not dragging_selection: # Copy
                if has_selection:
                    clipboard = alive_selected_cells.copy()
                    has_selection = False
                    active = was_active_before_edit

            if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL and not has_selection and not selecting and not dragging_selection: # Paste
                if paste_cells():
                    redo_history.clear()

            if event.key == pygame.K_f: # Center cam once with 'f'
                center_cam()

            if event.key == pygame.K_r:
                if has_selection and not dragging_selection:
                    random_fill()
                    has_selection = False
                    active = was_active_before_edit

        if event.type == pygame.MOUSEBUTTONDOWN: # Get click input and turn them into board pos + color them with board
            if event.button == 1:  # Leftclick
                if handle_settings_click(event.pos):
                    continue # Settings overlay swallowed this click
                if handle_touch_button(event.pos):
                    continue # Was a button-bar click
                if SELECT_MODE and not has_selection and not dragging_selection:
                    touch_select_start(event.pos)
                    continue
                if click_cell():
                    redo_history.clear()
            if event.button == 2: # Middle Drag Cam
                dragging = True
                last_mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONUP: # Cam drag
            if event.button == 2:
                dragging = False
            if event.button == 1 and SELECT_MODE and selecting:
                touch_select_end()

        if event.type == pygame.MOUSEMOTION:
            if dragging: # Cam drag
                mx, my = pygame.mouse.get_pos()

                dx = mx - last_mouse_pos[0]
                dy = my - last_mouse_pos[1]

                camera_x -= dx
                camera_y -= dy

                last_mouse_pos = (mx, my)
            if SELECT_MODE and selecting:
                touch_select_update(event.pos)

        # Phone Finger Controls (multi-touch camera pan)
        if event.type == pygame.FINGERDOWN:
            active_fingers[event.finger_id] = (event.x * WIDTH, event.y * HEIGHT)
        if event.type == pygame.FINGERUP:
            active_fingers.pop(event.finger_id, None)
        if event.type == pygame.FINGERMOTION:
            old_pos = active_fingers.get(event.finger_id)
            new_pos = (event.x * WIDTH, event.y * HEIGHT)
            active_fingers[event.finger_id] = new_pos
            if len(active_fingers) == 2 and old_pos is not None: # Only pan while exactly 2 fingers are down
                dx = new_pos[0] - old_pos[0]
                dy = new_pos[1] - old_pos[1]
                camera_x -= dx
                camera_y -= dy

        # Text typed into a focused mobile settings field (fed by Android's on-screen keyboard)
        if event.type == pygame.TEXTINPUT and active_field is not None:
            settings_fields[active_field] += event.text

        if event.type == pygame.MOUSEWHEEL: # Scroll to Zoom relative to the mouse pos
            mouse_x, mouse_y = pygame.mouse.get_pos()

            world_x = (mouse_x + camera_x) / zoom
            world_y = (mouse_y + camera_y) / zoom

            if event.y > 0:
                zoom *= 1.1
            else:
                zoom /= 1.1

            zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))

            camera_x = world_x * zoom - mouse_x
            camera_y = world_y * zoom - mouse_y

        select_field(event)
        numpad(event)

    draw_cells_from_grid() # draw each cell

    if show_preview: # Draw the preview if Toggled True | CHANGE IN THE SETTINGS
        draw_paste_preview()

    draw_drag_preview() # Draw the drag preview if dragging selection

    if not disable_grid:
        if cell_size * zoom >= 2:
            draw_grid(line_width) # draw board grid above

    draw_selection() # draw the selection rect (right click stuffy) if selecting or has selection

    GpS = update_speed(GpS, keys)

    dt = clock.tick(fps) / 1000
    accumulator += dt * GpS
    accumulator = min(accumulator, 10)

    while accumulator >= 1:
        pygame.event.pump()
        if active:
            manage_history("step")
            chunk_grid.step(birth_values, survive_values)
            if cam_in_center and gen % CAM_CENTER_EVERY_GEN == 0: # Only center cam every CAM_CENTER_EVERY_GEN for performance
                center_cam()

        accumulator -= 1

    birth_str = "".join(str(n) for n in sorted(birth_values))
    survive_str = "".join(str(n) for n in sorted(survive_values))
    pygame.display.set_caption(f"Rule = B{birth_str}/S{survive_str} | Gen = {gen} | Alive={chunk_grid.total_alive_count()} | GpS = {GpS} | FPS = {clock.get_fps():.1f} | Running = {active}") # Update Data
    draw_touch_buttons()   # Drawing the phone button bar
    draw_settings_overlay() # Drawing the mobile settings overlay (only visible when SHOW_SETTINGS is True)
    pygame.display.flip()

pygame.quit()