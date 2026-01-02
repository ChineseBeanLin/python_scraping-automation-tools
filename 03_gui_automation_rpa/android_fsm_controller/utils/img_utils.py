# -*- coding: utf-8 -*-
"""
Image Processing Utilities

Provides helper functions for:
- Template Matching (CV2)
- Structural Similarity Calculation (SSIM)
- Luminance analysis for UI element state detection
"""

import cv2
import numpy as np
from skimage.metrics import structural_similarity
import math

def match_tpl_loc(target, tpl, threshold=0.8, log_level=0, is_light_judging=True):
    """
    Finds the location of a template image within a target image.
    Includes an optional check for brightness difference to distinguish disabled (grayed out) buttons.
    """
    img_target = cv2.imread(target, 0)
    img_tpl = cv2.imread(tpl, 0)
    
    if img_target is None or img_tpl is None:
        return [-1, -1]

    tpl_size = img_tpl.shape[1::-1]
    flag = True
    methods = [cv2.TM_CCOEFF_NORMED]
    max_val = 0
    light_diff = 9999999999
    
    for md in methods:
        result = cv2.matchTemplate(img_target, img_tpl, md)
        locs_raw = np.where(result >= threshold)
        locs = list(zip(locs_raw[1], locs_raw[0]))
        vals = result[result >= threshold]
        
        points = list(zip(vals, locs))
        points.sort(reverse=True)
        
        if not locs: 
            flag = False
        else:
            max_loc = points[0][1]
            if is_light_judging:
                # Iterate through matches to find one that matches brightness profile
                for point in points:
                    loc = point[1]
                    val = point[0]
                    # Calculate brightness difference to filter out grayed-out buttons
                    diff = abs(light_means(img_tpl) - light_means(get_img_part(img_target, [loc, tpl_size])))
                    light_diff = diff
                    if light_diff < 50: # Threshold for brightness similarity
                        max_val = val
                        max_loc = loc
                        break
        
        if log_level == 1:
            print(f"Match Confidence: {max_val}")
            print(f"Brightness Diff: {light_diff}")
            
        if flag:
            return max_loc
        else:
            return [-1, -1]
    
def image_compare(img1_path, img2_path, threshold=0.7, log_level=0):
    """Compares two images using SSIM (Structural Similarity Index)."""
    img1 = cv2.imread(img1_path, 0)
    img2 = cv2.imread(img2_path, 0)
    return image_cv2_compare(img1, img2, threshold, log_level)

def image_cv2_compare(img1, img2, threshold=0.7, log_level=0):
    try:
        (score, diff) = structural_similarity(img1, img2, full=True)
        if log_level == 1:
            print(f"SSIM Score: {score}")
        return score > threshold
    except Exception as e:
        print(f"Error in comparison: {e}")
        return False

def light_means(src, box=None): 
    """Calculates the mean brightness of a specific region."""
    if box is None:
        box = [[0, 0], src.shape[1::-1]]
    return get_img_part(src, box).mean()

def get_img_part(src, box):
    """Crops a part of the image based on the box coordinates."""
    return src[box[0][1]:box[0][1]+box[1][1], box[0][0]:box[0][0]+box[1][0]]