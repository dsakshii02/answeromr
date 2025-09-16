import cv2
import numpy as np
import os
from pdf2image import convert_from_path
import imutils

# -------------------------------
# Preprocessing
# -------------------------------
def preprocess_image(image_path):
    """
    Loads an image or PDF page and preprocesses it for OMR detection.
    
    Args:
        image_path (str): The file path to the image or PDF.
    
    Returns:
        tuple: A tuple containing the binary inverted image (thresh) and the original image.
    """
    if image_path.lower().endswith('.pdf'):
        try:
            pages = convert_from_path(image_path, dpi=200)
            image = np.array(pages[0])[:, :, ::-1].copy()
        except Exception as e:
            raise ValueError(f"Could not convert PDF to image: {e}")
    else:
        image = cv2.imread(image_path)
    
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    return thresh, image

# -------------------------------
# Bubble Detection and Sorting
# -------------------------------
def detect_bubbles(thresh):
    """
    Detects, sorts, and analyzes bubbles based on their physical grouping.
    This logic automatically determines the number of questions and choices.
    
    Args:
        thresh (np.array): The binary inverted image.
        
    Returns:
        tuple: A tuple containing the student answers, coordinates, and detected counts.
    """
    # Find all external contours in the binary image
    find_contours_result = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Check the number of values returned.
    if len(find_contours_result) == 3:
        # For older OpenCV versions (3.x)
        _, contours, _ = find_contours_result
    else:
        # For newer OpenCV versions (4.x)
        contours, _ = find_contours_result

    bubble_contours = []

    # Filter contours based on size and aspect ratio to find bubbles
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Assuming bubbles have an area between 500 and 5000 pixels
        if 500 < area < 5000:
            (x, y, w, h) = cv2.boundingRect(cnt)
            aspect_ratio = w / float(h)
            # Assuming bubbles are roughly circular or square
            if 0.8 <= aspect_ratio <= 1.2:
                bubble_contours.append(cnt)

    # If no bubbles are found, return empty dictionaries
    if not bubble_contours:
        return {}, {}
    
    # Sort all bubbles by their y-coordinate (vertical position)
    sorted_bubbles = sorted(bubble_contours, key=lambda b: cv2.boundingRect(b)[1])
    
    rows = []
    # Set a tolerance to group bubbles that are on the same line
    y_tolerance = 20
    
    current_row = [sorted_bubbles[0]]
    current_y = cv2.boundingRect(sorted_bubbles[0])[1]

    # Group bubbles into rows based on vertical proximity
    for bubble in sorted_bubbles[1:]:
        y = cv2.boundingRect(bubble)[1]
        if abs(y - current_y) <= y_tolerance:
            current_row.append(bubble)
        else:
            rows.append(current_row)
            current_row = [bubble]
            current_y = y
    rows.append(current_row) # Add the last row

    student_answers = {}
    coordinates = {}
    num_questions = len(rows)

    # Analyze each row to determine the selected answer
    for q_idx, row_bubbles in enumerate(rows):
        # Sort bubbles within the row from left to right (by x-coordinate)
        row_bubbles_sorted_x = sorted(row_bubbles, key=lambda b: cv2.boundingRect(b)[0])
        
        max_filled_pixels = 0
        selected = None
        coords_per_row = {}

        for choice_idx, bubble_cnt in enumerate(row_bubbles_sorted_x):
            x, y, w, h = cv2.boundingRect(bubble_cnt)
            roi = thresh[y:y+h, x:x+w]
            filled = cv2.countNonZero(roi)
            option_char = chr(65 + choice_idx)
            coords_per_row[option_char] = (x, y, x + w, y + h)
            
            if filled > max_filled_pixels:
                max_filled_pixels = filled
                selected = option_char
        
        if max_filled_pixels > 50:
            student_answers[q_idx + 1] = selected
        else:
            student_answers[q_idx + 1] = "Unanswered"
            
        coordinates[q_idx + 1] = coords_per_row

    return student_answers, coordinates, num_questions

# -------------------------------
# Main Processing Function
# -------------------------------
def process_sheet(student_sheet_path, correct_sheet_path=None):
    """
    Processes a student's answer sheet and compares it with a correct answer key.
    
    Args:
        student_sheet_path (str): File path to the student's sheet.
        correct_sheet_path (str): File path to the correct answer sheet (optional).
    
    Returns:
        dict: A dictionary containing all grading results.
    """
    thresh_student, student_img = preprocess_image(student_sheet_path)
    student_answers, coordinates, _ = detect_bubbles(thresh_student)
    
    result = {
        "student_answers": student_answers,
        "coordinates": coordinates,
        "student_img": student_img,
    }

    if correct_sheet_path:
        thresh_correct, _ = preprocess_image(correct_sheet_path)
        correct_answers, _, correct_q_count = detect_bubbles(thresh_correct)
        
        total_questions = correct_q_count
        result["correct_answers"] = correct_answers
        result["total_questions"] = total_questions
        
        score = 0
        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0
        
        for q in range(1, total_questions + 1):
            student_ans = student_answers.get(q)
            correct_ans = correct_answers.get(q)
            
            if student_ans == correct_ans:
                score += 1
                correct_count += 1
            elif student_ans == "Unanswered":
                unanswered_count += 1
            else:
                incorrect_count += 1
                
        percentage = (score / total_questions) * 100

        result["score"] = score
        result["percentage"] = percentage
        result["correct_count"] = correct_count
        result["incorrect_count"] = incorrect_count
        result["unanswered_count"] = unanswered_count
    
    return result

# Example Usage

if __name__ == "__main__":
    # Ensure you have these files in your 'uploads' directory for testing
    student_file = "uploads/student_sheet.jpg"
    correct_file = "uploads/correct_sheet.jpg"

    results = process_sheet(student_file, correct_file)
    
    print("--- Grading Results ---")
    print(f"Total Questions: {results.get('total_questions')}")
    print(f"Correct Answers: {results.get('correct_count')}")
    print(f"Incorrect Answers: {results.get('incorrect_count')}")
    print(f"Unanswered Questions: {results.get('unanswered_count')}")
    print(f"Final Score: {results.get('score')} ({results.get('percentage'):.2f}%)")
    print("\nStudent Answers:", results.get('student_answers'))
    print("Correct Answers:", results.get('correct_answers'))