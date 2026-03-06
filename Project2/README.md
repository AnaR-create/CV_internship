# YOLOv8 Segmentation Dataset Preparation and Training

This repository contains the code for preparing a dataset, training, validating, and visualizing predictions using the YOLOv8 segmentation model.

---

## File

The main script is saved in the file named `train_yolov8_segmentation.py`.

---

## Description

This script performs the following tasks:

1. **Dataset Setup:**
   - Defines paths for images and labels.
   - Creates directories for training, validation, and test splits for both images and labels.
   - Loads images and their corresponding label files from specified source directories.

2. **Dataset Splitting:**
   - Splits the dataset into training (70%), validation (10%), and test (20%) sets using `sklearn.model_selection.train_test_split`.

3. **File Copying:**
   - Copies images and labels into their respective train, val, and test directories.
   - Checks for missing label files and notifies if any are missing.

4. **Dataset YAML Creation:**
   - Generates a `data.yaml` file describing the dataset structure and class names for YOLO training.

5. **Model Training and Validation:**
   - Loads the YOLOv8 segmentation model (`yolo11m-seg.pt`).
   - Trains the model for 50 epochs on the prepared dataset.
   - Validates the model on the test split and stores the metrics.

6. **Prediction and Visualization:**
   - Loads the best trained weights.
   - Performs prediction on a test image.
   - Visualizes the segmentation masks using matplotlib.

---

## Requirements

- Python 3.x
- Libraries:
  - `opencv-python`
  - `matplotlib`
  - `torch`
  - `ultralytics`
  - `scikit-learn`

Install dependencies with:

```bash
pip install opencv-python matplotlib torch ultralytics scikit-learn
