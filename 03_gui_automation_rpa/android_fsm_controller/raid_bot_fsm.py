"""
Raid Event Automation Controller

Description:
    Advanced bot for "Raid" events. It supports two modes:
    1. Normal Raid: Scans list, sorts by HP (via OCR/Image Rec), fights.
    2. Slayer Mode: Navigates to special high-difficulty instance.
    
    Demonstrates integration of Cloud OCR APIs for sorting logic where 
    simple template matching is insufficient.
"""

import sys
import os
import time
import argparse
import cv2
from enum import Enum

# --- Path Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import ADBShell, img_utils, baidu_ocr
try:
    from config.config import SCREEN_SHOOT_SAVE_PATH, RES_PATH
except ImportError:
    SCREEN_SHOOT_SAVE_PATH = "./debug/"
    RES_PATH = "./assets/"

# --- Configuration ---
PACKET_NAME = "com.linegames.dcglobal"
DEFAULT_SCREENSHOT = os.path.join(SCREEN_SHOOT_SAVE_PATH, "screenshot.png")

# Load Templates
TEMPLATE_NAMES = [
    "boss_level", "slayer_button", "slayer", "battle_start", "finished_boss",
    "confirm", "instance_list", "enter_raid", "mailbox", "get_ticket", "fetch", 
    "complete_battle", "sort_boss", "full_hp", "no_participate", "sort_by_hp", 
    "confirm_sort", "full_hp_in_boss", "refresh_raid", "amplification", "raid"
]

template_size = {}
for tpl_name in TEMPLATE_NAMES:
    path = os.path.join(RES_PATH, tpl_name + ".png")
    tpl_img = cv2.imread(path)
    if tpl_img is not None:
        template_size[tpl_name] = tpl_img.shape[1::-1]

client = ADBShell.ADBShell()

class State(Enum):
    IN_RAID_LIST = 0
    IN_BATTLE = 1
    IN_MAINMENU = 2
    IN_SLAYER_LIST = 3
    UNKNOWN_STATE = -1

def detect_current_state():
    client.get_screen_shot()
    if is_template_in_screenshot("enter_raid"):
        return State.IN_MAINMENU
    elif is_template_in_screenshot("raid"):
        return State.IN_RAID_LIST
    elif is_template_in_screenshot("slayer"):
        return State.IN_SLAYER_LIST
    else:
        return State.UNKNOWN_STATE

def enter_slayer_mode():
    """Navigates from Raid List to Slayer Mode."""
    print("Navigating to Slayer Mode...")
    while block_until_img_exist("slayer_button", 2):
        client.get_mouse_click_random(get_box("slayer_button"))
    
    time.sleep(5)
    if block_until_img_exist("slayer", 16):
        return block_until_img_exist("boss_level", 16)
    return False

def return_to_main_menu():
    """Emergency exit to main menu."""
    try_cnt = 0
    client.get_screen_shot()
    while detect_current_state() != State.IN_MAINMENU:
        client.click_back_keyevent() 
        try_cnt += 1
        time.sleep(3)
        client.get_screen_shot()
        if try_cnt > 7:
            restart_game()

def sort_boss_list():
    """Sorts boss list by HP using UI filters."""
    click_template("sort_boss")
    time.sleep(0.5)
    click_template("sort_by_hp")
    time.sleep(2)
    click_template("no_participate") # Filter only new bosses
    time.sleep(1)
    click_template("confirm_sort")
    time.sleep(0.5)

def find_boss_in_list(consume_first=False):
    """
    Scans the list for specific boss conditions.
    If 'consume_first' is True, it looks for bosses with HP remaining (to finish them off).
    """
    sort_boss_list()
    while True:
        client.get_screen_shot()
        # Logic to find "Full HP" tag
        target_template = "full_hp"
        
        if is_template_in_screenshot(target_template):
            click_template(target_template)
            time.sleep(3)
            client.get_screen_shot()
            
            # Double check inside boss room
            if is_template_in_screenshot("full_hp_in_boss"):
                while block_until_img_exist("battle_start", 2):
                    client.get_mouse_click_random(get_box("battle_start"))
                return not is_boss_finished()
            else:
                return False
        else:
            # Refresh list if no suitable boss found
            click_template("refresh_raid")
            time.sleep(1)
            if is_template_in_screenshot("sort_boss"):
                sort_boss_list()

def enter_boss_combat():
    """Enters combat from the boss detail view."""
    if is_template_in_screenshot("boss_level"):
        client.get_mouse_click_random(get_box("boss_level"))
    else:
        return False
    time.sleep(2)
    while block_until_img_exist("battle_start", 2):
        client.get_mouse_click_random(get_box("battle_start"))
    return not is_boss_finished()

def fetch_extra_tickets(count):
    """
    Automation to fetch tickets from mailbox.
    Demonstrates scrolling (swipe) and collection logic.
    """
    cnt_get = 0
    return_to_main_menu()
    while block_until_img_exist("mailbox", 2):
        client.get_mouse_click_random(get_box("mailbox"))
        time.sleep(1)
        
    while cnt_get < count:
        client.get_screen_shot()
        if is_template_in_screenshot("get_ticket"):
            client.get_mouse_click_random(get_box("get_ticket"))
            time.sleep(1)
            client.get_mouse_click_random(get_box("fetch"))
            time.sleep(5)
            cnt_get += 1
        
        # Scroll up to find more
        client.get_mouse_swipe(
            [client.resolution[0]/2, client.resolution[1]/4*3-200], 
            [client.resolution[0]/2, client.resolution[1]/4]
        )

def return_to_raid_menu():
    """Transition: Main Menu -> Raid List"""
    max_try = 10
    if state == State.IN_MAINMENU:
        while detect_current_state() != State.IN_RAID_LIST:
            client.get_mouse_click_random(get_box("enter_raid"))
            max_try -= 1
            if max_try <= 0:
                restart_game()
            time.sleep(1)
        return True

def is_boss_finished():
    if block_until_img_exist("finished_boss", 2):
        client.get_mouse_click_random(get_box("confirm"))
        print("Boss was already defeated.")
        return True
    return False

def wait_for_battle_end():
    cnt_wait = 0
    time.sleep(60)
    while not is_template_in_screenshot("complete_battle"):
        time.sleep(10)
        cnt_wait += 1
        if cnt_wait > 50:
            print("Battle Timeout.")
            return False
            
    if is_template_in_screenshot("complete_battle"):
        print("Battle Complete.")
        # Click arbitrary area to close reward screen
        client.get_mouse_click_random([[1819, 706], [70, 70]])
        while detect_current_state() == State.IN_RAID_LIST:
             time.sleep(1)
        return True
    return False

# --- Helpers ---
def get_box(template, is_light_judging=True):
    client.get_screen_shot()
    loc = img_utils.match_tpl_loc(DEFAULT_SCREENSHOT, os.path.join(RES_PATH, template + ".png"), is_light_judging=is_light_judging)
    if loc == [-1, -1]:
        return [[0,0], [0,0]]
    return [loc, template_size.get(template, [0,0])]

def click_template(template):
    if is_template_in_screenshot(template):
        client.get_mouse_click_random(get_box(template))

def is_template_in_screenshot(template_name):
    screenshot = cv2.imread(DEFAULT_SCREENSHOT, 0)
    tpl = cv2.imread(os.path.join(RES_PATH, template_name + ".png"), 0)
    
    loc = img_utils.match_tpl_loc(DEFAULT_SCREENSHOT, os.path.join(RES_PATH, template_name + ".png"), 0.7)
    box = [loc, tpl.shape[1::-1]]
    if loc == [-1, -1]:
        return False
    return img_utils.image_cv2_compare(img_utils.get_img_part(screenshot, box), tpl)

def block_until_img_exist(template_name, block_max_time=6):
    wait_time = 0
    client.get_screen_shot()
    # Simplified blocking logic for brevity
    while not is_template_in_screenshot(template_name):
        time.sleep(1)
        client.get_screen_shot()
        if wait_time >= block_max_time:
            return False
        wait_time += 1
    return True

def restart_game():
    print("Restarting Game...")
    client.stop_app(PACKET_NAME)
    time.sleep(2)
    client.start_app(PACKET_NAME + "/com.NextFloor.DestinyChild.MainActivity")
    time.sleep(30)
    for _ in range(10):
        if detect_current_state() == State.IN_MAINMENU:
            break
        client.get_mouse_click_random(((900, 400), (110, 195)))
        time.sleep(2)
    time.sleep(6)
    return True

def get_ticket_count():
    """Uses OCR to read remaining ticket count from UI."""
    client.get_screen_shot("remain_ticket.png", [(1152, 394), (41, 30)])
    path = os.path.join(SCREEN_SHOOT_SAVE_PATH, "remain_ticket.png")
    remain_ticket = baidu_ocr.image2num(path)
    if not remain_ticket:
        return [1] # Fallback
    return remain_ticket

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Raid Bot")
    parser.add_argument("-n", type=int, default=10, help="Max Tickets")
    parser.add_argument("--add", action='store_true', help="Auto-fetch tickets")
    parser.add_argument("--slayer", action='store_true', help="Target Slayer Mode")
    parser.add_argument("--amplify", action='store_true', help="Use Damage Amplifier")
    parser.add_argument("--log", action='store_true', default=True, help="Screenshot logging")
    
    args = parser.parse_args()
    
    ticket_limit = args.n
    state = detect_current_state()
    battles_fought = 0
    
    print(f"Starting Raid Bot. Target: {ticket_limit} battles.")
    
    while battles_fought < ticket_limit:
        print(f"Current State: {state.name}")
        
        if state == State.IN_RAID_LIST:
            if args.amplify:
                client.get_mouse_click_random(get_box("amplification"))
                
            if get_ticket_count()[0] == 0:
                if args.add:
                    fetch_extra_tickets(2)
                    return_to_main_menu()
                    state = detect_current_state()
                else:
                    print("No tickets left. Exiting.")
                    sys.exit(0)
            elif args.slayer:
                if enter_slayer_mode():
                    state = State.IN_SLAYER_LIST
                else:
                    state = detect_current_state()
            else:
                found = find_boss_in_list()
                if found:
                    state = State.IN_BATTLE
                else:
                    client.click_back_keyevent()
                    time.sleep(2)
                    state = detect_current_state()

        elif state == State.IN_SLAYER_LIST:
            # Slayer Logic
            if enter_boss_combat():
                state = State.IN_BATTLE
            else:
                state = detect_current_state()

        elif state == State.IN_BATTLE:
            if wait_for_battle_end():
                battles_fought += 1
            state = detect_current_state()

        elif state == State.IN_MAINMENU:
            return_to_raid_menu()
            state = State.IN_RAID_LIST
            
        elif state == State.UNKNOWN_STATE:
            if args.log:
                client.get_screen_shot(file_name=f"error_log_{time.time()}.png")
            
            # Retry logic
            if restart_game():
                state = detect_current_state()
            else:
                sys.exit(1)