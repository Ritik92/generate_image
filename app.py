from flask import Flask, request, render_template, jsonify
import ssl
import os
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from bing_image_downloader import downloader
from datetime import datetime

# Configure SSL context
ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__)

class Config:
    MAX_IMAGES = 20
    ALLOWED_FORMATS = ['jpg', 'jpeg', 'png']
    EMAIL_SENDER = "teamfooddle@gmail.com"  # Replace with your email
    EMAIL_PASSWORD = "eizy lvzb cdlk huuo"  # Replace with your App Password
    # Define base temporary directory
    TEMP_DIR = "/tmp/image_downloads"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON data received"}), 400

        prompt = data.get('prompt')
        email = data.get('email')
        image_count = min(int(data.get('imageCount', 5)), Config.MAX_IMAGES)

        if not prompt or not email:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        # Create unique directory for this request within /tmp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(Config.TEMP_DIR, f"{prompt.replace(' ', '_')}_{timestamp}")

        # Download images
        downloader.download(
            prompt,
            limit=image_count,
            output_dir=output_dir,
            adult_filter_off=True,
            force_replace=False,
            timeout=60
        )

        # Create zip file in /tmp
        zip_path = f"{output_dir}.zip"
        shutil.make_archive(output_dir, 'zip', output_dir)

        # Send email
        send_email(email, zip_path, prompt)

        # Cleanup
        shutil.rmtree(output_dir)
        os.remove(zip_path)

        return jsonify({
            "status": "success",
            "message": "Images have been downloaded and sent to your email!"
        })

    except Exception as e:
        app.logger.error(f"Error in submit: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500

def send_email(to_email, zip_file, prompt):
    msg = MIMEMultipart()
    msg['From'] = Config.EMAIL_SENDER
    msg['To'] = to_email
    msg['Subject'] = f"Your Downloaded Images: {prompt}"

    # Add HTML body
    html_body = f"""
    <html>
        <body>
            <h2>Your Image Download is Ready!</h2>
            <p>Thank you for using our Image Download Portal. Your images for the prompt "{prompt}" are attached.</p>
            <p>Best regards,<br>Image Portal Team</p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    # Attach zip file
    with open(zip_file, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={os.path.basename(zip_file)}'
        )
        msg.attach(part)

    # Send email
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(Config.EMAIL_SENDER, Config.EMAIL_PASSWORD)
        server.send_message(msg)

if __name__ == '__main__':
    # Create temporary directory in /tmp instead of the application directory
    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)