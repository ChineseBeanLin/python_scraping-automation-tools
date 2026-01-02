"""
World Boss Automation Bot (FSM)

Description:
    A Finite State Machine (FSM) implementation for automating repetitive boss battles.
    It manages the game state loop: Menu -> List -> Battle Prep -> Combat -> Result -> Repeat.
    Includes robust error handling for network lags or game crashes.
"""

import sys
import os
import time
import argparse
import cv2
from enum import Enum

# --- Path Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import ADBShell, img_utils
try:
    from config.config import SCREEN_SHOOT_SAVE_PATH, RES_PATH
except ImportError:
    SCREEN_SHOOT_SAVE_PATH = "./debug/"
    RES_PATH = "./assets/"

# --- Configuration ---
PACKET_NAME = "com.linegames.dcglobal"
DEFAULT_SCREENSHOT = os.path.join(SCREEN_SHOOT_SAVE_PATH, "screenshot.png")

# Template List
TEMPLATE_NAMES = [
    "battle_start", "finished_boss", "confirm", "complete_battle", 
    "complete_battle_all", "buy_ticket", "confirm_buy_ticket", 
    "enter_wb", "retry", "trial_ready", "buy_ticket_finished"
]

template_size = {}
for tpl_name in TEMPLATE_NAMES:
    path = os.path.join(RES_PATH, tpl_name + ".png")
    tpl_img = cv2.imread(path)
    if tpl_img is not None:
        template_size[tpl_name] = tpl_img.shape[1::-1]

client = ADBShell.ADBShell()
last_got_ticket_time = 0

class State(Enum):
    IN_MAINMENU = "Main Menu"
    IN_WB_LIST = "World Boss List"
    IN_WB_BATTLE_PAGE = "Battle Prep Page"
    IN_BATTLE = "In Battle"
    NO_TICKET = "Out of Tickets"
    UNKNOWN_STATE = "Unknown State"

def block_until_template_exists(template, max_try=10, interval=0.5):
    """Blocks execution until template appears."""
    cnt = 0
    while not is_template_in_screenshot(template):
        cnt += 1
        time.sleep(interval)
        if cnt > max_try:
            return False
    return True

def transition_to_battle_prep():
    """Transition: WB List -> Battle Prep"""
    if block_until_template_exists("trial_ready"):
        while not is_template_in_screenshot("battle_start"):
            # Anti-AFK / Wakeup clicks
            client.get_mouse_click_random([(863, 537), (197, 92)])
            time.sleep(3)
        return State.IN_WB_BATTLE_PAGE
    else:
        return State.UNKNOWN_STATE

def execute_battle_start():
    """Transition: Battle Prep -> In Battle"""
    if block_until_template_exists("battle_start"):
        client.get_mouse_click_random(get_box("battle_start"))
    else:
        return State.UNKNOWN_STATE
    
    time.sleep(2)
    if is_template_in_screenshot("buy_ticket"):
        return State.NO_TICKET
    elif is_template_in_screenshot("finished_boss"):
        client.get_mouse_click_random(get_box("confirm"))
        print("Boss already finished.")
        return State.IN_WB_LIST
    else:
        return State.IN_BATTLE

def handle_ticket_purchase():
    """Handles logic for buying more entry tickets."""
    global last_got_ticket_time
    # Simple rate limit check
    if int(time.time()) - last_got_ticket_time > 300:
        last_got_ticket_time = int(time.time())
        
        if is_template_in_screenshot("buy_ticket"):
            client.get_mouse_click_random(get_box("buy_ticket"))
        time.sleep(2)
        if is_template_in_screenshot("confirm_buy_ticket"):
            client.get_mouse_click_random(get_box("confirm_buy_ticket"))
        time.sleep(2)
        if is_template_in_screenshot("buy_ticket_finished"):
            client.get_mouse_click_random(get_box("buy_ticket_finished"))
        return State.IN_WB_BATTLE_PAGE
    else:
        print("Ticket buy rate limit hit.")
        return State.UNKNOWN_STATE

def return_to_wb_list():
    """Transition: Main Menu -> WB List"""
    max_try = 10
    if detect_current_state() == State.IN_MAINMENU:
        while not is_template_in_screenshot("enter_wb"):
            max_try -= 1
            time.sleep(1)
            if max_try <= 0:
                restart_game()
                return State.UNKNOWN_STATE
        
        client.get_mouse_click_random(get_box("enter_wb"))
        time.sleep(3)
        if is_template_in_screenshot("trial_ready"):
            return State.IN_WB_LIST
        return State.UNKNOWN_STATE
    else:
        restart_game()
        return State.UNKNOWN_STATE

def wait_for_battle_completion():
    """Monitors battle progress."""
    cnt_wait = 0
    time.sleep(300) # Minimum battle time
    
    while not (is_template_in_screenshot("complete_battle") or is_template_in_screenshot("complete_battle_all")):
        time.sleep(10)
        cnt_wait += 1
        if cnt_wait > 50:
            print("Battle timed out.")
            return State.UNKNOWN_STATE
            
    if is_template_in_screenshot("complete_battle"):
        print("Battle finished.")
        client.get_mouse_click_random(get_box("retry"))
        # Wait until transition back to list
        while detect_current_state() == State.IN_WB_LIST:
             time.sleep(1)
    elif is_template_in_screenshot("complete_battle_all"):
        client.get_mouse_click_random(get_box("complete_battle_all"))
        
    return State.IN_WB_LIST

# --- Helpers ---
def get_box(template, is_light_judging=True):
    client.get_screen_shot()
    loc = img_utils.match_tpl_loc(DEFAULT_SCREENSHOT, os.path.join(RES_PATH, template + ".png"), is_light_judging=is_light_judging)
    if loc == [-1, -1]:
        return [[0,0], [0,0]]
    return [loc, template_size.get(template, [0,0])]

def is_template_in_screenshot(template_name):
    client.get_screen_shot()
    screenshot = cv2.imread(DEFAULT_SCREENSHOT, 0)
    tpl = cv2.imread(os.path.join(RES_PATH, template_name + ".png"), 0)
    
    if tpl is None: return False
    
    loc = img_utils.match_tpl_loc(DEFAULT_SCREENSHOT, os.path.join(RES_PATH, template_name + ".png"), 0.7)
    box = [loc, tpl.shape[1::-1]]
    
    if loc == [-1, -1]:
        return False
    return img_utils.image_cv2_compare(img_utils.get_img_part(screenshot, box), tpl)

def restart_game():
    print("Self-Healing: Restarting Game Client...")
    client.stop_app(PACKET_NAME)
    time.sleep(2)
    client.start_app(PACKET_NAME + "/com.NextFloor.DestinyChild.MainActivity")
    time.sleep(30)
    while detect_current_state() != State.IN_MAINMENU:
        client.get_mouse_click_random(((900, 400), (110, 195))) # Dismiss Ads
        time.sleep(2)
    time.sleep(6)

def detect_current_state():
    """State Identification Routine."""
    client.get_screen_shot()
    if is_template_in_screenshot("enter_wb"):
        return State.IN_MAINMENU
    elif is_template_in_screenshot("trial_ready"):
        return State.IN_WB_LIST
    elif is_template_in_screenshot("battle_start"):
        return State.IN_WB_BATTLE_PAGE
    else:
        return State.UNKNOWN_STATE

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="World Boss Bot")
    parser.add_argument("-n", type=int, default=None, help="Number of tickets to use")
    args = parser.parse_args()
    
    if args.n is None:
        try:
            ticket_limit = int(input("Enter ticket limit: "))
        except ValueError:
            ticket_limit = 5
    else:
        ticket_limit = args.n
        
    print(f"Target: {ticket_limit} tickets")
    
    current_state = detect_current_state()
    ticket_cnt = 0
    
    # Main FSM Loop
    while ticket_cnt < ticket_limit:
        time.sleep(2)
        print(f"State: {current_state.value}")
        
        if current_state == State.IN_MAINMENU:
            current_state = return_to_wb_list()
        elif current_state == State.IN_WB_LIST:
            current_state = transition_to_battle_prep()
        elif current_state == State.IN_WB_BATTLE_PAGE:
            current_state = execute_battle_start()
        elif current_state == State.IN_BATTLE:
            ticket_cnt += 1
            current_state = wait_for_battle_completion()
        elif current_state == State.NO_TICKET:
            current_state = handle_ticket_purchase()
        elif current_state == State.UNKNOWN_STATE:
            restart_game()
            current_state = State.IN_MAINMENU