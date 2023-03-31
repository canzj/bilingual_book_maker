from flask import Flask, request, render_template_string, send_from_directory, Response
import os
import subprocess
from werkzeug.utils import secure_filename
import glob
import threading
import time

app = Flask(__name__)

# Set the directory to save uploaded files
UPLOAD_FOLDER = 'Books'
OUTPUT_FOLDER = UPLOAD_FOLDER
LOG_FILE = f"{OUTPUT_FOLDER}/make.log"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
PROMPT = "Translate the given text to {language}. Be faithful or accurate and authentic in translation. Make the translation readable or intelligible. Be elegant or natural in translation. If the text cannot be translated, return the original text as is. Do not translate person's name. Do not add any additional text in the translation. The text to be translated is: {text}"

# Create the folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

form_template = '''
<!doctype html>
<html>
  <head>
    <title>Make Book</title>
  </head>
  <body>
    <h1>Make Book</h1>
    <form action="/make_book" method="post" enctype="multipart/form-data">
      <label for="file">Book file:</label>
      <input type="file" name="file" id="file" required><br><br>
      <label for="openai_key">OpenAI Key:</label>
      <input type="text" name="openai_key" id="openai_key" required><br><br>
      <label for="language">Language:</label>
      <input type="text" name="language" id="language" required><br><br>
      <input type="submit" value="Submit">
    </form>
  </body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(form_template)


@app.route('/make_book', methods=['POST'])
def make_book():
    if 'file' not in request.files:
        return "Error: No file provided.", 400

    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return "Error: No file selected.", 400

    openai_key = request.form.get('openai_key')
    language = request.form.get('language')

    if not openai_key or not language:
        return "Error: Missing parameters.", 400

    # Save the uploaded file to the UPLOAD_FOLDER
    filename = secure_filename(uploaded_file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    uploaded_file.save(file_path)

    # create log file
    if not os.path.isfile(LOG_FILE):
        open(LOG_FILE, "w").close()
    cmd = f"python3 make_book.py --book_name {file_path} --openai_key {openai_key} --language {language} --prompt \"{PROMPT}\""
    thread = threading.Thread(target=run_command_and_log_output, args=(cmd,))
    thread.start()

    return Response(stream_log_output(), content_type="text/plain; charset=utf-8")


def run_command_and_log_output(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    with open(LOG_FILE, "a") as log_file:
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break

            if line:
                log_file.write(line)


def stream_log_output():
    with open(LOG_FILE, "r") as log_file:
        while True:
            line = log_file.readline()
            if line:
                yield line
            else:
                time.sleep(1)


@app.route('/list_books')
def list_books():
    epub_files = glob.glob(f"{OUTPUT_FOLDER}/*.epub")
    epub_filenames = [os.path.basename(file) for file in epub_files]

    return render_template_string('''
    <!doctype html>
    <html>
      <head>
        <title>Generated Books</title>
      </head>
      <body>
        <h1>Generated Books</h1>
        <ul>
          {% for filename in epub_filenames %}
            <li><a href="{{ url_for('download_book', filename=filename) }}">{{ filename }}</a></li>
          {% endfor %}
        </ul>
      </body>
    </html>
    ''', epub_filenames=epub_filenames)


@app.route('/download_book/<path:filename>')
def download_book(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=50001)
