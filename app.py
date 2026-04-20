# The ai microservice 
# This is where all blueprints are registered

from flask import Flask
from flask_cors import CORS
import os
import config


from routes.upload_routes  import upload_bp   # Member 03 - file processing
from routes.scoring_routes import scoring_bp  # Member 01 - scoring and search
from routes.comparison_routes import comparison_bp  # Member 04 - comparison
from routes.chat_routes    import chat_bp     # Member 02 - conversational AI  ← NEW
from routes.jd_routes        import jd_bp        # Member 06 - JD analysis
from routes.interview_routes import interview_bp  # Member 06 - interview questions
from routes.email_routes     import email_bp      # Email generation - kanban


app = Flask(__name__)
CORS(app) # cross origin requests  (since frontend may be on a different port)

app.config["MAX_CONTENT_LENGTH"] = config.MAX_FILE_SIZE_MB * 1024 * 1024  # file size limit converted to bytes

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# Register Blueprints 
app.register_blueprint(upload_bp)      # routes: /ai/upload/...
app.register_blueprint(scoring_bp)     # routes: /ai/scoring/...
app.register_blueprint(comparison_bp)  # routes: /ai/comparison/...
app.register_blueprint(chat_bp)        # routes: /ai/chat/...              
app.register_blueprint(jd_bp)          # routes: /ai/jd/...
app.register_blueprint(interview_bp)   # routes: /ai/interview/...
app.register_blueprint(email_bp)       # routes: /ai/email/...

# Health Check 
@app.route("/health")
def health():
    return {"status": "ok", "service": "hireiq-ai"}, 200

if __name__ == "__main__":
    app.run(debug=config.DEBUG_MODE, port=config.FLASK_PORT)