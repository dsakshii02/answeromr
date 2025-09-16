from flask import Flask, render_template, request, send_from_directory
import os
from werkzeug.utils import secure_filename
import time
from omr import process_sheet
from report import report, save_report

app = Flask(__name__)

# Configure folders and allowed file types
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
app.config['REPORT_FOLDER'] = os.path.join(app.root_path, 'reports')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf'}

# Ensure the necessary folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)

# Helper function for file validation
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Renders the main upload form page for a GET request."""
    return render_template('index.html')

@app.route('/grade', methods=['POST'])
def grade_sheet():
    """
    Handles the form submission (POST request) to process and grade the sheets.
    """
    student_file = request.files.get('student_sheet')
    correct_file = request.files.get('correct_sheet')
    student_name = request.form.get('student_name', 'Student')

    # Basic file validation
    if not student_file or not correct_file or student_file.filename == '' or correct_file.filename == '':
        return render_template('index.html', error="Please upload both student and correct answer sheets.")

    if not allowed_file(student_file.filename) or not allowed_file(correct_file.filename):
        return render_template('index.html', error="Invalid file type. Only PNG, JPG, JPEG, and PDF are allowed.")

    # Secure filenames and save files to the uploads folder
    student_filename = f"student_sheet_{int(time.time())}_{secure_filename(student_file.filename)}"
    correct_filename = f"correct_sheet_{int(time.time())}_{secure_filename(correct_file.filename)}"
    student_path = os.path.join(app.config['UPLOAD_FOLDER'], student_filename)
    correct_path = os.path.join(app.config['UPLOAD_FOLDER'], correct_filename)
    
    student_file.save(student_path)
    correct_file.save(correct_path)
    
    try:
        # Process the sheets and get grading results from omr.py
        results = process_sheet(student_path, correct_path)
    except ValueError as e:
        return f"Error: {e}", 500

    if not results or 'student_img' not in results:
        return "Error processing sheets. The OMR sheets might be unreadable.", 500

    # Generate the annotated report image
    report_img = report(
        results['student_img'],
        results['student_answers'],
        results['correct_answers'],
        results['coordinates'],
        student_name=student_name,
        score=results.get('score'),
        total=results.get('total_questions')
    )
    
    # Save the report image to the reports folder with a unique name
    report_filename = save_report(report_img, app.config['REPORT_FOLDER'], student_name)
    
    # Extract data for the template, converting dictionaries to lists for consistent display
    # Sort keys to ensure correct order
    sorted_questions = sorted(results.get('correct_answers', {}).keys())
    student_answers_list = [results.get('student_answers', {}).get(q, "Unanswered") for q in sorted_questions]
    correct_answers_list = [results.get('correct_answers', {}).get(q, "N/A") for q in sorted_questions]
    
    # Render the result page with all the grading data
    return render_template('result.html',
                           student_name=student_name,
                           score=results.get('score', 0),
                           total_questions=results.get('total_questions', 0),
                           student_answers=student_answers_list,
                           correct_answers=correct_answers_list,
                           report_path=report_filename)

@app.route('/reports/<filename>')
def serve_report(filename):
    """Serves the generated report images from the reports folder."""
    return send_from_directory(app.config['REPORT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)