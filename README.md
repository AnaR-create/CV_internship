﻿# Rock Coverage Analysis Script

This Python script is designed to analyze a video of rocks and determine the coverage percentage within a predefined polygon region. The script uses OpenCV for video processing and background subtraction techniques to identify and track objects (rocks) within the specified area. Here's a detailed explanation of what the script does:

## Setup and Initialization
- Import necessary libraries including `cv2` for OpenCV, `numpy`, `json`, `os`, and `csv`.
- Define paths to video and polygon file.
- Initialize variables and parameters such as polygon points, RGB color ranges, kernel for noise reduction, and a background subtractor.

## Video Setup
- Open the specified video.
- Check if the video is successfully opened; otherwise, exit the script.
- Read the first frame from the video and resize it to a standard size (640x360).

## Polygon Setup
- Check if a saved polygon file exists. If it does:
  - Load the polygon points from the JSON file if `DEBUG` mode is enabled.
  - Otherwise, prompt the user to define a new polygon by clicking four points on the video frame.
- If no saved polygon exists, prompt the user to click 4 points to define their region of interest.
- Save the defined polygon points to a JSON file if desired.
- Create a mask based on the defined polygon points for further processing.

## Background Subtraction
- Create a background subtractor and apply it to the video frame to separate foreground (moving objects) from the background.

## Forecast and Logging
- Introduced a forecasting system to monitor and predict rock coverage:
  - Every 10% increment of coverage (0–10%, 10–20%, ..., up to 60%) is logged with the corresponding timestamp in a CSV file.
  - Three utility functions are defined:
    - To load the CSV log file.
    - To log time intervals when thresholds are crossed.
    - To calculate a forecast for reaching 60% coverage based on logged data.
- Forecasted time until reaching 60% coverage is displayed on the video in real time.
- Logging and forecasting logic are executed within the main loop.

## Main Loop
- Continuously read frames from the video.
- For each frame:
  - Resize the frame for consistency.
  - Convert the frame to RGB format for color-based processing.
  - Apply the background subtractor to detect foreground objects.
  - Detect edges using Canny edge detection.
  - Apply a mask to focus only on the defined polygon area.
  - Perform noise reduction and morphological operations to clean up the image.
  - Use connected components or watershed segmentation to identify distinct regions of interest.
  - Calculate areas for background, rocks, and other regions inside the polygon.
  - Compute the rock coverage percentage.
  - Log coverage thresholds and update forecast as applicable.
  - Display overlays including:
    - Edge detection results.
    - Masked regions.
    - A traffic light indicator representing coverage levels:
      - **Green**: Low coverage
      - **Orange**: Moderate coverage
      - **Red**: High coverage (60% or more)
    - Forecasted time until 60% coverage is reached.

## Output
- Displays annotated video frames with analysis overlays and a traffic light indicator.
- Forecast information is shown on-screen.
- Optional debug windows are available if `DEBUG` mode is enabled.
- User can quit the video processing loop by pressing 'q' or the Escape (`Esc`) key.

## Cleanup
- Release resources used by the video capture and close all OpenCV windows.

## Contacts
Ana Rodrigues

anafontesrodrigues@gmail.com

