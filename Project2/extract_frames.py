import cv2
import os

# === CONFIGURE THESE ===
video_path = "rocks_video.mp4"
labels_dir = "/home/laura/Ana/Internship_rocks/GridDataset/labels/train"      # Folder containing .txt files
output_dir = "/home/laura/Ana/Internship_rocks/GridDataset/images"      # Folder to save extracted frames

os.makedirs(output_dir, exist_ok=True)

# Load the video
cap = cv2.VideoCapture(video_path)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

# Read all .txt filenames (like frame_00000.txt)
label_files = sorted(f for f in os.listdir(labels_dir) if f.endswith('.txt'))

for label_file in label_files:
    # Extract frame number from filename, e.g., frame_00022.txt → 22
    frame_number = int(label_file.replace("frame_", "").replace(".txt", ""))

    if frame_number >= total_frames:
        print(f"[SKIP] Frame {frame_number} is beyond video length.")
        continue

    # Set the video to that frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()

    if not ret:
        print(f"[ERROR] Could not read frame {frame_number}")
        continue

    # Save the frame using the same base name as the .txt
    image_filename = label_file.replace('.txt', '.png')  # or .jpg
    image_path = os.path.join(output_dir, image_filename)
    cv2.imwrite(image_path, frame)
    print(f"[OK] Saved: {image_path}")

cap.release()
