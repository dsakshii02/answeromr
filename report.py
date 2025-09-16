import os
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2

def report(student_img, student_answers, correct_answers, coordinates, student_name="", score=None, total=None):
    """
    Draw a visual OMR report highlighting correct/incorrect/unanswered answers.

    Args:
        student_img (PIL.Image.Image or OpenCV image): Student sheet image.
        student_answers (dict): Student answers, e.g., {1: 'A', 2: 'C'}
        correct_answers (dict): Correct answers, e.g., {1: 'A', 2: 'B'}
        coordinates (dict): Bubble coordinates per question.
        student_name (str): Name of the student.
        score (int): Number of correct answers.
        total (int): Total questions.

    Returns:
        PIL.Image.Image: Annotated image.
    """
    # Convert OpenCV BGR image to PIL if needed
    if isinstance(student_img, np.ndarray):
        student_img = cv2.cvtColor(student_img, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(student_img)
    else:
        img = student_img.copy()

    draw = ImageDraw.Draw(img)

    # Use a try-except block for robust font loading
    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw student name and score at the top
    if student_name or (score is not None and total is not None):
        text_lines = [f"Student: {student_name}"]
        if score is not None and total is not None:
            text_lines.append(f"Score: {score}/{total}")
        
        y_offset = 10
        for line in text_lines:
            draw.text((10, y_offset), line, fill="black", font=font_small)
            y_offset += 30

    # Draw circles and annotations for each question
    for q, bubble_dict in coordinates.items():
        student_ans = student_answers.get(q)
        correct_ans = correct_answers.get(q)
        is_correct = (student_ans == correct_ans)

        for option, (x1, y1, x2, y2) in bubble_dict.items():
            # Mark the correct answer with a green rectangle
            if correct_ans == option:
                draw.rectangle((x1, y1, x2, y2), outline="green", width=4)

            # Mark the student's selected answer
            if student_ans == option:
                if is_correct:
                    color = "green"
                    draw.rectangle((x1, y1, x2, y2), outline=color, width=4)
                else: # Incorrect or Unanswered
                    color = "red"
                    draw.rectangle((x1, y1, x2, y2), outline=color, width=4)
                    draw.line((x1, y1, x2, y2), fill="red", width=4)
                    draw.line((x1, y2, x2, y1), fill="red", width=4)

    return img

def save_report(report_img, save_dir, student_name="student"):
    """
    Save report image to the specified directory with a unique filename.

    Args:
        report_img (PIL.Image.Image): Annotated report image
        save_dir (str): The directory to save the report in.
        student_name (str): Name of student for filename

    Returns:
        str: Filename of the saved report (relative to the directory).
    """
    os.makedirs(save_dir, exist_ok=True)
    timestamp = int(time.time())
    filename = f"{secure_filename(student_name)}_{timestamp}.png"
    path = os.path.join(save_dir, filename)
    report_img.save(path)
    return filename