import cv2
import numpy as np
import json
import os

video_path = 'videos/blocked_rocks.mp4'
polygon_file = 'polygon_region.json'
polygon_points = []

def draw_polygon(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(polygon_points) < 4:
        polygon_points.append((x, y))

def save_polygon_to_json(points, filename):
    with open(filename, 'w') as f:
        json.dump(points, f)
    print(f"Polygon saved to {filename}.")

def load_polygon_from_json(filename):
    with open(filename, 'r') as f:
        points = json.load(f)
    return [tuple(point) for point in points]

# Open video
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

# Read and resize first frame for setup
ret, first_frame = cap.read()
first_frame = cv2.resize(first_frame, (640, 360))

# --- POLYGON SETUP ---
if os.path.exists(polygon_file):
    print("A saved polygon was found.")
    print("Do you want to load the saved polygon or define a new one? (l = load, n = new): ", end="")
    user_choice = input().strip().lower()

    if user_choice == 'l':
        polygon_points = load_polygon_from_json(polygon_file)
    elif user_choice == 'n':
        print("Click 4 points to define a new polygon.")
        cv2.namedWindow("Select 4 Points")
        cv2.setMouseCallback("Select 4 Points", draw_polygon)

        while True:
            temp_frame = first_frame.copy()
            for point in polygon_points:
                cv2.circle(temp_frame, point, 5, (0, 255, 0), -1)

            if len(polygon_points) == 4:
                cv2.polylines(temp_frame, [np.array(polygon_points)], isClosed=True, color=(255, 0, 0), thickness=2)
                cv2.putText(temp_frame, "Polygon selected. Press any key...", (10, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            cv2.imshow("Select 4 Points", temp_frame)

            if len(polygon_points) == 4 and cv2.waitKey(1) != -1:
                break
            elif cv2.waitKey(1) == 27:
                cap.release()
                cv2.destroyAllWindows()
                exit()

        cv2.destroyWindow("Select 4 Points")

        print("Do you want to save this new polygon region for future use? (y/n): ", end="")
        save_input = input().strip().lower()
        if save_input == 'y':
            save_polygon_to_json(polygon_points, polygon_file)
    else:
        print("Invalid input. Exiting.")
        cap.release()
        cv2.destroyAllWindows()
        exit()
else:
    print("No saved polygon found. Please click 4 points to define your region.")
    cv2.namedWindow("Select 4 Points")
    cv2.setMouseCallback("Select 4 Points", draw_polygon)

    while True:
        temp_frame = first_frame.copy()
        for point in polygon_points:
            cv2.circle(temp_frame, point, 5, (0, 255, 0), -1)

        if len(polygon_points) == 4:
            cv2.polylines(temp_frame, [np.array(polygon_points)], isClosed=True, color=(255, 0, 0), thickness=2)
            cv2.putText(temp_frame, "Polygon selected. Press any key...", (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow("Select 4 Points", temp_frame)

        if len(polygon_points) == 4 and cv2.waitKey(1) != -1:
            break
        elif cv2.waitKey(1) == 27:
            cap.release()
            cv2.destroyAllWindows()
            exit()

    cv2.destroyWindow("Select 4 Points")

    print("Do you want to save this polygon region for future use? (y/n): ", end="")
    save_input = input().strip().lower()
    if save_input == 'y':
        save_polygon_to_json(polygon_points, polygon_file)

# --- CREATE POLYGON MASK ---
mask = np.zeros_like(first_frame[:, :, 0], dtype=np.uint8)
cv2.fillPoly(mask, [np.array(polygon_points)], 255)
mask_3ch = cv2.merge([mask, mask, mask])

# Store background edge mask for comparison
background_edges = cv2.Canny(first_frame, 100, 200)
background_edges = cv2.bitwise_and(background_edges, mask)
background_edges_colored = cv2.cvtColor(background_edges, cv2.COLOR_GRAY2BGR)
background_edge_count = cv2.countNonZero(background_edges)

# Background subtractor
fgbg = cv2.bgsegm.createBackgroundSubtractorGSOC()

# Reset video to start
cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

# --- MAIN LOOP ---
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (640, 360))
    fgmask = fgbg.apply(frame)

    # Edge detection and polygon masking
    current_edges = cv2.Canny(frame, 100, 200)
    current_edges = cv2.bitwise_and(current_edges, mask)
    current_edges_colored = cv2.cvtColor(current_edges, cv2.COLOR_GRAY2BGR)

    # Compare current edges to background edges
    overlap = cv2.bitwise_and(background_edges, current_edges)
    visible_edge_count = cv2.countNonZero(overlap)

    if background_edge_count > 0:
        visibility_ratio = visible_edge_count / background_edge_count
    else:
        visibility_ratio = 1  # fallback if somehow no ref edges

    # Draw overlays
    overlay = frame.copy()

     # Blue edge overlay
    edges_colored = cv2.cvtColor(current_edges, cv2.COLOR_GRAY2BGR)
    blue_edges = np.zeros_like(edges_colored)
    blue_edges[np.where((edges_colored == [255, 255, 255]).all(axis=2))] = [255, 0, 0]
    blue_edges_region = cv2.bitwise_and(blue_edges, mask_3ch)

     # Blocking overlay – what part of background edges are missing
    missing_edges = cv2.subtract(background_edges, overlap)
    missing_overlay = cv2.cvtColor(missing_edges, cv2.COLOR_GRAY2BGR)

    # Foreground mask within polygon
    fg_mask_poly = cv2.bitwise_and(fgmask, mask)

    # Threshold the missing edges mask to get binary
    _, missing_edges_bin = cv2.threshold(missing_edges, 50, 255, cv2.THRESH_BINARY)

    # Combine the foreground mask and missing edge mask to find likely occluders
    combined_mask = cv2.bitwise_and(fg_mask_poly, missing_edges_bin)

    # Find contours (i.e., objects) in this combined mask
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Draw red overlays for each contour
    red_mask = np.zeros_like(frame)
    for cnt in contours:
        if cv2.contourArea(cnt) > 100:
            cv2.drawContours(red_mask, [cnt], -1, (0, 0, 255), thickness=cv2.FILLED)

    # Blend red overlay with the main overlay
    overlay = cv2.addWeighted(overlay, 1.0, red_mask, 0.6, 0)

    # Apply blue edge overlay
    overlay = cv2.addWeighted(overlay, 1.0, blue_edges_region, 1.0, 0)

    # Draw visibility text
    cv2.putText(overlay, f"Edge Visibility: {visibility_ratio:.2f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

    if visibility_ratio < 0.5:
        cv2.putText(overlay, "Edges Covered / Occluded", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    # Show frames
    cv2.imshow("Original + Blue Edges (Polygon Region)", overlay)
    cv2.imshow("Foreground Mask (GSOC)", fgmask)
    #cv2.imshow("Masked Canny Edges", current_edges)
    if combined_mask is not None:
        cv2.imshow("Combined Mask", combined_mask)
    else:
        print("Combined mask is None")


    if cv2.waitKey(25) in [ord('q'), 27]:
        break

cap.release()
cv2.destroyAllWindows()
