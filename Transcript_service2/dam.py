from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

import os
import re

def extract_transcript(url):
    command = [
        "yt-dlp",
        "--cookies", "cookies.txt",
        "--skip-download",
        "--write-auto-sub",
        "--sub-lang", "en",
        url
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr)

    # Find the latest .en.vtt file (subtitle file)
    vtt_file = None
    for fname in sorted(os.listdir("."), key=os.path.getmtime, reverse=True):
        if fname.endswith(".en.vtt"):
            vtt_file = fname
            break

    if not vtt_file:
        raise Exception("Subtitle file (.vtt) not found.")

    with open(vtt_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    transcript_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}", line) or "-->" in line:
            continue  # skip timestamps
        if line.startswith("WEBVTT") or "Kind:" in line or "Language:" in line:
            continue  # skip header/meta
        transcript_lines.append(line)

    return "\n".join(transcript_lines)

import re

def clean_raw_caption(raw_text):
    # Remove all timestamp tags like <00:00:00.640>
    text = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", raw_text)

    # Remove all <c> and </c> tags
    text = re.sub(r"</?c>", "", text)

    # Collapse multiple spaces and strip
    text = re.sub(r"\s+", " ", text).strip()

    return text


@app.route("/transcript", methods=["POST"])
def transcript():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        raw_output = extract_transcript(url)
        clean_output = clean_raw_caption(raw_output)
        return jsonify({"transcript": clean_output})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
