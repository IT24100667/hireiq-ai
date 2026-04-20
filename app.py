# The ai microservice 
# This is where all blueprints are registered

from flask import Flask
from flask_cors import CORS
import os
import config



app = Flask(__name__)
CORS(app) # cross origin requests  (since frontend may be on a different port)

app.config["MAX_CONTENT_LENGTH"] = config.MAX_FILE_SIZE_MB * 1024 * 1024  # file size limit converted to bytes

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# Health Check 
@app.route("/health")
def health():
    return {"status": "ok", "service": "hireiq-ai"}, 200

if __name__ == "__main__":
    app.run(debug=config.DEBUG_MODE, port=config.FLASK_PORT)