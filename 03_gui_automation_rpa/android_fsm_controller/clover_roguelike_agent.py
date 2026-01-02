"""
Clover Roguelike Automation Agent

Description:
    An automated agent designed for a Roguelike dungeon crawler mode.
    It utilizes Computer Vision to identify map nodes (Battle, Event, Shop, Boss)
    and makes decisions based on OCR text analysis of random events.

Key Features:
    - Graph Traversal: Scans the screen to find valid next moves.
    - Two-Pass Verification: Uses Template Matching followed by Structural Similarity check to filter disabled nodes.
    - OCR Integration: Reads event titles to select optimal rewards based on a JSON strategy file.
"""

import sys
import os
import time
import math
import random
import json
import codecs
import cv2

# --- Path Setup for 'utils' module ---
# Allows importing from parent directory's 'utils' folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import ADBShell, img_utils, baidu_ocr
try:
    from config.config import SCREEN_SHOOT_SAVE_PATH, RES_PATH
except ImportError:
    # Fallback constants for portfolio display
    SCREEN_SHOOT_SAVE_PATH = "./debug/"
    RES_PATH = "./assets/"

# --- Configuration ---
PACKET_NAME = "com.moefantasy.clover"
DEFAULT_SCREENSHOT = os.path.join(SCREEN_SHOOT_SAVE_PATH, "screenshot.png")

# UI Regions (Bounding Boxes)
START_PERFORM_BOX = ((1154, 706), (227, 70))
SKIP_LOOT_BOX = ((622, 644), (200, 46))
BOTTOM_BOX = ((30, 735), (1300, 40))
CONFIRM_BOX = ((631, 689), (190, 58))
PERFORM_END_BOX = ((629, 532), (220, 55))
HP_UP_BOX = ((1031, 166), (259, 441))
PORTAL_BOX = ((765, 355), (100, 150))
EVENT_TITLE_BOX = ((754, 123), (381, 34))
EVENT_OPT_BOX = ((1068, 243), (108, 40))
END_SHOP_BOX = ((1006, 688), (142, 46))
GIFT_BOX = (((234, 265), (210, 210)), ((607, 265), (210, 210)), ((981, 265), (210, 210)))

OPT_SPACE = 120
PATH_ANGLE = 28

# Assets Loading
template_names = [
    "normal_battle.png", "elite_battle.png", "normal_boss.png",
    "super_boss.png", "special_boss.png", "loot.png", "event.png", "shop.png"
]
templates = [os.path.join(RES_PATH, t) for t in template_names]
template_size = []

# Load template dimensions
for tpl_path in templates:
    tpl_img = cv2.imread(tpl_path)
    if tpl_img is not None:
        template_size.append(tpl_img.shape[1::-1])
    else:
        template_size.append((0, 0)) # Placeholder for missing assets

# Load Event Strategy JSON
try:
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "event_opt.json")
    if os.path.exists(config_path):
        with codecs.open(config_path, "r", "utf-8") as file:
            EVENT_CHOOSE = json.load(file)
    else:
        EVENT_CHOOSE = {}
except Exception as e:
    print(f"Warning: Could not load event strategy: {e}")
    EVENT_CHOOSE = {}

res_map = {
    "start_perform": os.path.join(RES_PATH, "start_perform.png"),
    "skip_loot": os.path.join(RES_PATH, "skip_loot.png"),
    "end_perform": os.path.join(RES_PATH, "perform_end.png"),
    "end_shop": os.path.join(RES_PATH, "shop_end.png")
}

box_map = {
    "start_perform": START_PERFORM_BOX,
    "skip_loot": SKIP_LOOT_BOX,
    "event_opt": EVENT_OPT_BOX,
    "end_perform": PERFORM_END_BOX,
    "confirm": CONFIRM_BOX,
    "end_shop": END_SHOP_BOX
}

gift_template = (
    os.path.join(RES_PATH, "gift_hp_up.png"), 
    os.path.join(RES_PATH, "gift_lv_up.png"), 
    os.path.join(RES_PATH, "gift_artifact.png")
)

def find_clickable_item(client):
    """
    Random search fallback if structure analysis fails.
    Swipes screen randomly to find interactive elements.
    """
    find_cnt = 0
    up_flag = 1
    while True:
        if find_cnt > 10:
            restart_game(client)
            up_flag = -1
        client.get_screen_shoot()
        for i in range(0, 7):
            loc = img_utils.match_tpl_loc(DEFAULT_SCREENSHOT, templates[i])
            if loc != [-1, -1]:
                return i, loc
        find_cnt += 1
        swipe_screen_angle(client, up_flag * random.randint(200, 220), PATH_ANGLE)

def scan_for_interactive_elements(client):
    """
    Main Logic: Graph Traversal.
    Scans the current screen to identify all reachable nodes (Battle, Event, Shop).
    Uses a hybrid recognition approach (Template Matching + Structural Comparison).
    """
    print("Scanning for next stage nodes...")
    find_max_time = 10
    all_items = []
    find_cnt = 0
    up_flag = 1
    
    while True:
        if find_cnt > find_max_time:
            restart_game(client)
            find_cnt = 0
            up_flag = -1
            
        if up_flag == -1 and find_cnt > find_max_time:
            print("Error: No clickable objects found.")
            return []

        client.get_screen_shoot()
        
        for i in range(len(templates)):
            # 1. Broad Phase: Template Matching
            locs = img_utils.match_tpl_loc_multi(DEFAULT_SCREENSHOT, templates[i], 0.9)
            
            if locs != [-1, -1]:
                for loc in locs:
                    # Crop the potential region for detailed analysis
                    crop_name = os.path.join(SCREEN_SHOOT_SAVE_PATH, "item_crop.png")
                    client.get_screen_shoot(crop_name, screen_range=(loc, tuple(template_size[i])))
                    
                    if img_utils.image_compare(crop_name, templates[i]):
                        # 2. Narrow Phase: Structural Analysis (RGB check)
                        # Specific check for Elite/Boss nodes to distinguish disabled (gray) vs active nodes
                        if i == 1 or i == 2:
                            if not img_utils.image_compare_RGB(crop_name, templates[i]):
                                continue # Skip if node is disabled (grayed out)
                        all_items.append((i, locs))
        
        if all_items:
            return all_items
            
        find_cnt += 1
        # If nothing found, explore map by swiping
        swipe_screen_angle(client, up_flag * random.randint(300, 320), PATH_ANGLE)

def restart_game(client):
    """Error Recovery: Restarts the application and navigates back to game."""
    print("State Recovery: Restarting Application...")
    client.stop_app(PACKET_NAME)
    time.sleep(2)
    client.start_app(PACKET_NAME + "/com.hm.proj212.UnityPlayerActivity")
    time.sleep(30)
    # Dismiss welcome screen
    client.get_mouse_click_random(((10, 10), (710, 395)))
    time.sleep(10)

def swipe_screen_angle(client, x, angle):
    """Calculates vector for angular swipe to simulate natural movement."""
    y = int(x * math.tan(math.pi / 180.0 * angle))
    point_o = (client.resolution[0] / 2, client.resolution[1] / 2)
    client.get_mouse_swipe(point_o, ([point_o[0] + x, point_o[1] + y]))

def handle_event_choice(client):
    """
    Intelligent Event Handling.
    1. Captures event title text.
    2. Uses OCR to convert image to text.
    3. Lookups optimal choice in 'event_opt.json'.
    4. Executes choice.
    """
    time.sleep(5)
    client.get_screen_shoot("event_title.png", EVENT_TITLE_BOX)
    
    # OCR Call
    title_text = baidu_ocr.image2text(os.path.join(SCREEN_SHOOT_SAVE_PATH, "event_title.png"))
    print(f"Event Encountered: {title_text}")
    
    if title_text in EVENT_CHOOSE:
        # Execute defined strategy
        for opt in EVENT_CHOOSE.get(title_text):
            # Calculate option button position dynamically
            opt_index = int(opt) - 1
            box_top_left = (EVENT_OPT_BOX[0][0], EVENT_OPT_BOX[0][1] + opt_index * OPT_SPACE)
            box_size = EVENT_OPT_BOX[1]
            client.get_mouse_click_random((box_top_left, box_size))
            time.sleep(1)
            
            if title_text == "Unknown Crystal": # Specific logic for special event
                handle_loot_skip(client)
        return True
    else:
        print(f"Warning: Unrecognized Event '{title_text}'. Check dictionary.")
        # Optional: Log screenshot for manual review
        return False

def handle_loot_skip(client):
    print("Skipping loot animation...")
    if block_until_img_exist(client, "skip_loot"):
        for _ in range(3): # Spam click to speed up
            client.get_mouse_click_random(SKIP_LOOT_BOX)
        return True
    return False

def block_until_img_exist(client, template_key, block_max_time=6):
    """Blocking wait until a UI element appears."""
    wait_time = 0
    box = box_map.get(template_key)
    tpl_path = res_map.get(template_key)
    
    client.get_screen_shoot(screen_range=box)
    
    while not img_utils.image_compare(DEFAULT_SCREENSHOT, tpl_path):
        time.sleep(0.75)
        client.get_screen_shoot(screen_range=box)
        if wait_time >= block_max_time:
            print(f"Timeout waiting for {template_key}")
            return False
        wait_time += 1
    return True

def handle_gift_selection(client):
    """Selects buff/gift based on priority."""
    for i in range(3):
        client.get_screen_shoot("gift.png", screen_range=GIFT_BOX[i])
        for j in range(3):
            if img_utils.image_compare(os.path.join(SCREEN_SHOOT_SAVE_PATH, "gift.png"), gift_template[j]):
                client.get_mouse_click_random(GIFT_BOX[i])
                time.sleep(0.5)
                client.get_mouse_click_random(box_map.get("confirm"))
                if j == 2: # Artifact needs skip
                    handle_loot_skip(client)
                return True

def enter_portal(client):
    client.get_mouse_click_random(PORTAL_BOX)
    client.get_mouse_click_random(PORTAL_BOX)
    time.sleep(3)

def process_node_action(client, point_type, loc, current_state):
    """Finite State Machine logic for handling different node types."""
    print(f"Interacting with Node Type: {point_type}")
    
    # Click the node
    # box_prefix adjustment for hitbox offset
    hitbox = ((loc[0], loc[1] + 125), (93, 33)) 
    for _ in range(3):
        client.get_mouse_click_random(hitbox)
    time.sleep(2)
    
    # Battle Nodes (0-4)
    if 0 <= point_type < 5:
        print("Waiting for battle transition...")
        client.get_screen_shoot(screen_range=START_PERFORM_BOX)
        if block_until_img_exist(client, "start_perform"):
            current_state = "PERFORMING"
            client.get_mouse_click_random(START_PERFORM_BOX)
            client.get_mouse_click_random(START_PERFORM_BOX)
            time.sleep(5)
            
            # Wait for battle end
            if block_until_img_exist(client, "end_perform", 20):
                current_state = "FINISHED"
                client.get_mouse_click_random(PERFORM_END_BOX)
                time.sleep(2)
                # Clear dialogs
                client.get_mouse_click_random(BOTTOM_BOX) 
                client.get_mouse_click_random(BOTTOM_BOX)
                
                if point_type > 0:
                    time.sleep(3)
                    handle_loot_skip(client)
                if point_type > 2:
                    time.sleep(3)
                    handle_gift_selection(client)
                
                time.sleep(3)
                client.get_mouse_click_random(HP_UP_BOX)
                time.sleep(0.5)
                client.get_mouse_click_random(CONFIRM_BOX)
                
                if point_type == 2 or point_type == 3:
                    time.sleep(3)
                    enter_portal(client)
            return True

    # Event Node (6)
    if point_type == 6:
        current_state = "EVENT"
        if not handle_event_choice(client):
            return False # Exit or Retry
        return True

    # Loot Node (5)
    if point_type == 5:
        current_state = "LOOT"
        return handle_loot_skip(client)

    # Shop Node (7)
    if point_type == 7:
        if block_until_img_exist(client, "end_shop"):
             client.get_mouse_click_random(END_SHOP_BOX)
             client.get_mouse_click_random(END_SHOP_BOX)
             enter_portal(client)
             return True

if __name__ == '__main__':
    state = "MAP_TRAVERSAL"
    client = ADBShell.ADBShell()
    
    print("Clover Agent Started.")
    while True:
        next_flag = False
        client.get_screen_shoot()
        
        # Step 1: Scan for nodes
        interactive_nodes = scan_for_interactive_elements(client)
        
        # Step 2: Iterate and Act
        for item in interactive_nodes:
            node_type = item[0]
            coordinates = item[1]
            
            for loc in coordinates:
                if process_node_action(client, node_type, loc, state):
                    next_flag = True
                    break
            if next_flag:
                break