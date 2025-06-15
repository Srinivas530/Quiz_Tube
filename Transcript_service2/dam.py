from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

def extract_transcript(url):
    command = [
        "yt-dlp",
          "--cookies", "cookies.txt", 
        "--skip-download",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--print", "%(automatic_captions.en.data)s",
        "--write-info-json",
        "--quiet",
        url
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr)
    return result.stdout

@app.route("/transcript", methods=["POST"])
def transcript():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        transcript_text = extract_transcript(url)
        return jsonify({"transcript": transcript_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
