from atexit import _ncallbacks
import cv2
import numpy as np
import json
import os
import pandas as pd
import copy
import time
import csv
from astral import LocationInfo
from astral.sun import sun
import datetime
from zoneinfo import ZoneInfo
import time

video_path = 'videos/Blocked_rocks.mp4'
polygon_file = 'polygon_region.json'
polygon_points = []
click = False
column_names=['colour','colour name','hex','r','g','b']
b = g = r = xpos = ypos = -1
csv_filename = "rock_forecast_times.csv"
forecast_start_time = None
forecasting = False
start_pct = None
last_logged_pct = 0
milestones = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60)]  # Milestones until 60%
milestone_times = {}
rock_times = 'rock_times.csv'
rock_percentage = 0
has_reached_60 = False  # Track if we've already reached 60% before
milestone_times = {}
city = LocationInfo("London", "England", "Europe/London")
tz = ZoneInfo("Europe/London")
delta = datetime.timedelta(minutes=30)


DEBUG = True
#DEBUG = False

#FORECAST = True
FORECAST = False

print("type(csv_file)", type(rock_times))

def load_milestone_times(csv_file):
    milestone_data = {}
    if os.path.exists(csv_file):
        with open(csv_file, mode='r') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header row
            for row in reader:
                if len(row) == 3:
                    try:
                        start, end, duration = map(float, row)
                        key = (int(start), int(end))
                        if key not in milestone_data:
                            milestone_data[key] = []
                        milestone_data[key].append(duration)
                    except ValueError:
                        # Log or silently ignore bad data rows
                        print(f"Skipping invalid row: {row}")
    return milestone_data


def save_time(start_pct, end_pct, elapsed_time, filename="rock_times.csv"):
    file_exists = os.path.isfile(filename)

    with open(filename, mode='a', newline='') as csvfile:
        fieldnames = ['start_pct', 'end_pct', 'elapsed_time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write header only if the file didn't exist before
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            'start_pct': start_pct,
            'end_pct': end_pct,
            'elapsed_time': round(elapsed_time, 3)
        })

def average_remaining_milestones(current_percentage, milestone_data):
    remaining = []
    for (start, end), durations in milestone_data.items():
        if current_percentage < end:
            # Filter out durations < 20s
            valid_durations = [d for d in durations if d >= 20]
            if valid_durations:
                avg = sum(valid_durations) / len(valid_durations)
                remaining.append(avg)
    return sum(remaining)

# Load this ONCE before the loop starts:
milestone_csv_data = load_milestone_times('rock_times.csv')



# rock_times = load_times()
# mean_time = sum(rock_times) / len(rock_times) if rock_times else None

# Load colors CSV
df=pd.read_csv('colors.csv',names=column_names,header=None)  # Ensure this exists with columns: colour name, r, g, b

# --- Mouse functions ---
def draw_polygon(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(polygon_points) < 4:
        polygon_points.append((x, y))

def mouse_function(event, x, y, flags, param):
    global click, b, g, r, xpos, ypos, image
    if event == cv2.EVENT_LBUTTONDOWN:
        click = True
        xpos = x
        ypos = y
        b, g, r = image[y, x]
        b, g, r = int(b), int(g), int(r)
        print(f"Clicked at ({x}, {y}) - BGR: ({b}, {g}, {r})")

def Getcolorname(r, g, b):
    min_diff = float('inf')
    cname = ""
    for i in range(len(df)):
        distance = abs(df.loc[i, 'r'] - r) + abs(df.loc[i, 'g'] - g) + abs(df.loc[i, 'b'] - b)
        if distance < min_diff:
            min_diff = distance
            cname = df.loc[i, 'colour name']
    return cname

def save_polygon_to_json(points, filename):
    with open(filename, 'w') as f:
        json.dump(points, f)
    print(f"Polygon saved to {filename}.")

def load_polygon_from_json(filename):
    with open(filename, 'r') as f:
        points = json.load(f)
    return [tuple(point) for point in points]

# pre-determined RGB color ranges
background_lower = np.array([0, 0, 0])
background_upper = np.array([158, 85, 73])

#pre-determined HSV color ranges
rock_lower = np.array([0, 0, 60]) #([0, 0, 60])
rock_upper = np.array([100, 60, 170]) #([144, 64, 181])


# rock_lower = np.array([80, 79, 79])
# rock_upper = np.array([110, 110, 110])

#kernel for noise cleaning
kernel = np.ones((5,5),np.uint8)

# --- Open video ---
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

ret, first_frame = cap.read()
first_frame = cv2.resize(first_frame, (640, 360))
image = first_frame.copy() 


# --- Polygon Setup ---
if os.path.exists(polygon_file):
    if DEBUG:
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
                    cv2.polylines(temp_frame, [np.array(polygon_points)], True, (255, 0, 0), 2)
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
            if input().strip().lower() == 'y':
                save_polygon_to_json(polygon_points, polygon_file)
        else:
            print("Invalid input. Exiting.")
            cap.release()
            cv2.destroyAllWindows()
            exit()
    else:
        polygon_points = load_polygon_from_json(polygon_file)
else:
    print("No saved polygon found. Please click 4 points to define your region.")
    cv2.namedWindow("Select 4 Points")
    cv2.setMouseCallback("Select 4 Points", draw_polygon)
    while True:
        temp_frame = first_frame.copy()
        for point in polygon_points:
            cv2.circle(temp_frame, point, 5, (0, 255, 0), -1)
        if len(polygon_points) == 4:
            cv2.polylines(temp_frame, [np.array(polygon_points)], True, (255, 0, 0), 2)
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
    if input().strip().lower() == 'y':
        save_polygon_to_json(polygon_points, polygon_file)

# --- Polygon mask ---
mask = np.zeros_like(first_frame[:, :, 0], dtype=np.uint8)
cv2.fillPoly(mask, [np.array(polygon_points)], 255)
mask_3ch = cv2.merge([mask, mask, mask])
background_edges = cv2.Canny(first_frame, 100, 200)
background_edges = cv2.bitwise_and(background_edges, mask)
background_edges_colored = cv2.cvtColor(background_edges, cv2.COLOR_GRAY2BGR)
background_edge_count = cv2.countNonZero(background_edges)
fgbg = cv2.bgsegm.createBackgroundSubtractorGSOC()
cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

# # --- Set color picker callback for HSV window ---
# cv2.namedWindow("HSV")
# cv2.setMouseCallback("HSV", mouse_function)

# cap.release()
# cap = cv2.VideoCapture(video_path)
# # Check if the video file is opened correctly
# if not cap.isOpened():
#     print("Error: Could not open video.")
#     exit()

# # Read the first frame
# ret, first = cap.read()
# if not ret or first is None:
#     print("Failed to read first frame.")
#     exit()

# #Resize the first frame to desired size (640x360)
# image = cv2.resize(first, (1280, 720))

# #Convert the first frame to HSV
# hsv_frame = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

# #Create window to display image
# cv2.namedWindow("HSV")
# cv2.setMouseCallback("HSV", mouse_function)

# # Show the image and wait for the click
# while True:
#     # Show the HSV frame
#     cv2.imshow("HSV", hsv_frame)

#     # Show color info if clicked
#     if click:
#         cname = Getcolorname(r, g, b)
        
#         # Adjusting the size of the box where text will be put
#         if xpos > 0.6 * image.shape[1]:
#             xpos = xpos - 400
#         if ypos < 0.05 * image.shape[0]:
#             ypos = ypos + 40

#         # Draw rectangle for color info
#         cv2.rectangle(hsv_frame, (xpos, ypos - 40), (xpos + 600, ypos), (b, g, r), -1)
#         text = f"{cname} R = {r} G = {g} B = {b}"

#         # Dark background, light text
#         if b + g + r >= 600:
#             cv2.putText(hsv_frame, text, (xpos + 10, ypos - 10), 2, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
#         # Light background, dark text
#         else:
#             cv2.putText(hsv_frame, text, (xpos + 10, ypos - 10), 2, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

#         click = False  # Reset click after displaying the text

#     # Wait for 1 ms and check for the escape key
#     key = cv2.waitKey(1) & 0xFF
#     if key == 27:  # Exit on ESC key
#         break

# # Close windows
# cv2.destroyAllWindows()
# cap.release()


# --- Main Loop ---
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.resize(frame, (640, 360))
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    image = frame.copy()
    fgmask = fgbg.apply(frame)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_delay = int(1000 / fps)

    today = datetime.date.today()
    s = sun(city.observer, date=today, tzinfo=tz)
    sunrise_minus_30 = s["sunrise"] - delta
    sunset_plus_30 = s["sunset"] + delta
    now = datetime.datetime.now(tz)
    
    #blue edges
    current_edges = cv2.Canny(frame, 100, 200)
    current_edges = cv2.bitwise_and(current_edges, mask)

    inverted_edges = cv2.bitwise_not(current_edges)
    inverted_edges = cv2.bitwise_and(inverted_edges, mask)


    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(inverted_edges, cv2.MORPH_OPEN, kernel, iterations=2)
    dist_transform = cv2.distanceTransform(cleaned, cv2.DIST_L2, 5)
    ret, sure_fg = cv2.threshold(dist_transform, 0.4 * dist_transform.max(), 255, 0)
    sure_fg = np.uint8(sure_fg)
    sure_bg = cv2.dilate(cleaned, kernel, iterations=3)
    unknown = cv2.subtract(sure_bg, sure_fg)

    ret, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0
    ws_input = frame.copy()
    markers = cv2.watershed(ws_input, markers)

    regions_img = np.zeros_like(current_edges)
    regions_img[markers > 1] = 255
    regions_img = cv2.bitwise_and(regions_img, mask)

    # overlap = cv2.bitwise_and(background_edges, current_edges)
    # visible_edge_count = cv2.countNonZero(overlap)
    # visibility_ratio = visible_edge_count / background_edge_count if background_edge_count > 0 else 1
    # missing_edges = cv2.subtract(background_edges, overlap)
    # missing_edge_count = cv2.countNonZero(missing_edges)
    # occlusion_ratio = missing_edge_count / background_edge_count if background_edge_count > 0 else 0

    overlay = frame.copy()
    edges_colored = cv2.cvtColor(current_edges, cv2.COLOR_GRAY2BGR)
    blue_edges = np.zeros_like(edges_colored)
    blue_edges[np.where((edges_colored == [255, 255, 255]).all(axis=2))] = [255, 0, 0]
    blue_edges_region = cv2.bitwise_and(blue_edges, mask_3ch)

    # if occlusion_ratio > 0.3:
    #     red_overlay = np.zeros_like(frame)
    #     red_overlay[missing_edges > 0] = (0, 0, 255)
    #     overlay = cv2.addWeighted(overlay, 1.0, red_overlay, 0.5, 0)

    overlay = cv2.addWeighted(overlay, 1.0, blue_edges_region, 1.0, 0)
    # if visibility_ratio < 0.55:
    #     cv2.putText(overlay, "Edges Covered / Occluded", (10, 310),
    #                 cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # #create masks using rgb
    # background_mask = cv2.inRange(rgb, background_lower, background_upper)
    # rock_mask = cv2.inRange(rgb, rock_lower, rock_upper)

    #create masks using hsv
    #background_mask = cv2.inRange(hsv, background_lower, background_upper)
    rock_mask = cv2.inRange(hsv, rock_lower, rock_upper)

    rock_mask = cv2.morphologyEx(rock_mask, cv2.MORPH_OPEN, kernel)
    rock_mask = cv2.morphologyEx(rock_mask, cv2.MORPH_CLOSE, kernel)

    background_mask = cv2.bitwise_not(rock_mask)

    background_mask = cv2.morphologyEx(background_mask, cv2.MORPH_OPEN, kernel)
    background_mask = cv2.morphologyEx(background_mask, cv2.MORPH_CLOSE, kernel)

    background_mask = cv2.bitwise_and(background_mask, cv2.bitwise_not(rock_mask))

    rock_only = cv2.bitwise_and(rock_mask, cv2.bitwise_not(background_mask))


    #rock mask overlay
    focus_area = cv2.bitwise_and(frame, frame, mask=mask)
    overlay_now = focus_area.copy()
    background_black = (background_mask == 0) & (mask == 255)
    overlay_now[background_black] = (0,0,255)
    output = cv2.addWeighted(overlay_now, 0.4, focus_area, 0.6, 0)
    contours, _ = cv2.findContours(rock_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
     # Create a temporary mask to draw the edges
    edges_mask = np.zeros_like(frame)
    # Apply mask to edges (focus inside polygon only)
    edges_mask = cv2.bitwise_and(edges_mask, mask_3ch)

    # Combine red object edges into the overlay
    overlay = cv2.addWeighted(overlay, 1.0, edges_mask, 1.0, 0)

    cv2.drawContours(edges_mask, contours, -1, (0, 0, 255), 2)

    # Create a temporary mask to draw the edges
    edges_mask = np.zeros_like(frame)
    cv2.drawContours(edges_mask, contours, -1, (0, 0, 255), 2)  # Red edges for object

    # Apply mask to edges (focus inside polygon only)
    edges_mask = cv2.bitwise_and(edges_mask, mask_3ch)

    # Combine blue edges (already done earlier)

    # Now combine red object edges into the overlay
    overlay = cv2.addWeighted(overlay, 1.0, edges_mask, 1.0, 0)

    # Mask the background and rock masks to the polygon area
    background_in_polygon = cv2.bitwise_and(background_mask, mask)
    rock_in_polygon = cv2.bitwise_and(rock_mask, mask)

    # Calculate areas
    background_area = cv2.countNonZero(background_in_polygon)
    rock_area = cv2.countNonZero(rock_in_polygon)

    # Compute rock coverage percentage
    if background_area > 0:
        rock_percentage = (rock_area / background_area) * 100
    else:
        rock_percentage = 0

    if rock_percentage > 59:
        rock_status = "Maintenance"
    elif rock_percentage > 37:
        rock_status = "Percentage Full"
    else:
        rock_status = "Percentage Full"

    # --- Optional: Display it live on the overlay ---
    cv2.putText(overlay, f"Coverage: {rock_percentage:.0f}% {rock_status}", (10, 350),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
    cv2.putText(overlay, f"Coverage: {rock_percentage:.0f}% {rock_status}", (10, 350),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)


    #FORCAST STARTS HEREEEE
    if FORECAST:
        #Test Forecasting #3


        # Start forecasting if in range and not already forecasting
        if rock_percentage > 0 and not forecasting and rock_percentage < 60:
            forecasting = True
            forecast_start_time = time.time()

            # Figure out which milestone we're in
            for i, milestone in enumerate(milestones):
                if rock_percentage < milestone[1]:
                    current_milestone_index = i
                    break
            else:
                current_milestone_index = len(milestones)

            # Backfill past milestones as reached (without time)
            milestone_times = []
            for j in range(current_milestone_index):
                milestone_times.append((milestones[j - 1] if j > 0 else 0, milestones[j], 0.0))

            milestone_start_time = time.time()
            #print(f"[DEBUG] Forecast started at {forecast_start_time} from ~{rock_percentage:.1f}%")


        if forecasting and current_milestone_index < len(milestones):
            next_milestone = milestones[current_milestone_index]
            if rock_percentage >= next_milestone[1]:
                current_time = time.time()
                elapsed = current_time - milestone_start_time

                from_pct = milestones[current_milestone_index - 1][1] if current_milestone_index > 0 else 0
                to_pct = next_milestone[1]

                print(f"Time to reach {to_pct}% from {from_pct}%: {elapsed:.2f}s")
                save_time(from_pct, to_pct, elapsed)
                milestone_times.append((from_pct, to_pct, elapsed))

                milestone_start_time = current_time
                current_milestone_index += 1

        milestone_data = load_milestone_times(rock_times)

        # Forecasting overlay
        if forecasting and current_milestone_index < len(milestones):
            estimated_remaining = 0

            for (start, end) in milestones[current_milestone_index:]:
                durations = milestone_csv_data.get((start, end), [])
                valid_durations = [d for d in durations if d > 20]  # ignore < 20s
                if valid_durations:
                    avg_duration = sum(valid_durations) / len(valid_durations)
                    estimated_remaining += avg_duration
                    #print(f"[DEBUG] Milestone ({start}, {end}) -> valid durations: {valid_durations}")


            if estimated_remaining > 0:
                cv2.putText(overlay, f"Forecast to 60%: {estimated_remaining:.1f}s",
                            (10, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


        # Optionally reset everything when 60% is reached
        if forecasting and rock_percentage >= 60:
            forecasting = False
            forecast_start_time = None
            milestone_start_time = None
            current_milestone_index = 0
            #print("[DEBUG] Forecasting complete.")
 


    # Frame size (after resize)
    frame_height, frame_width = frame.shape[:2]

    # Traffic light position (top right)
    offset_x = frame_width - 70  # small offset from the right edge
    offset_y = 50                # from top

    circle_radius = 15
    spacing = 50  # space between circles

    # Circle centers (top to bottom)
    circle_center_red = (offset_x, offset_y)
    circle_center_yellow = (offset_x, offset_y + spacing)
    circle_center_green = (offset_x, offset_y + 2 * spacing)

    # Define colors
    black = (0, 0, 0)
    red_on = (0, 0, 139)
    red_dim = (0, 33, 237)
    yellow_on = (0, 191, 255)
    yellow_dim = (0, 234, 255)
    green_on = (0, 255, 0)
    green_dim = (0, 100, 0)

    # Glow if close to border (within 5%)
    glow_threshold = 8

    # Default to dim
    red_color = black
    yellow_color = black
    green_color = black

    if rock_percentage >= 60:
        # HIGH coverage => RED active
        if 90 - glow_threshold <= rock_percentage <= 90:
            red_color = red_on
        else:
            red_color = red_dim

    elif 38 < rock_percentage < 60:
        # MEDIUM coverage => YELLOW active
        if 60 - glow_threshold <= rock_percentage <= 60:
            yellow_color = yellow_on
        else:
            yellow_color = yellow_dim

    else:  # rock_percentage <= 38
        # LOW coverage => GREEN active
        if 38 - glow_threshold <= rock_percentage <= 38:
            green_color = green_on
        else:
            green_color = green_dim

    # Draw traffic light frame (optional)
    cv2.rectangle(overlay, (offset_x - 25, offset_y - 30), (offset_x + 25, offset_y + 2 * spacing + 30), (50, 50, 50), 2)

    # Draw circles
    cv2.circle(overlay, circle_center_red, circle_radius, red_color, -1, lineType=cv2.LINE_AA)
    cv2.circle(overlay, circle_center_yellow, circle_radius, yellow_color, -1, lineType=cv2.LINE_AA)
    cv2.circle(overlay, circle_center_green, circle_radius, green_color, -1, lineType=cv2.LINE_AA)

    cv2.imshow("Original + Overlays", overlay)
    if DEBUG:
        cv2.imshow("Detected Grid Spaces", regions_img)
        cv2.imshow("Masked Edges", current_edges)
        cv2.imshow("GSOC Background Subtraction", background_mask)
        cv2.imshow("Object Only", rock_only)

    if cv2.waitKey(frame_delay) in [ord('q'), 27]:
        break

cap.release()
cv2.destroyAllWindows()