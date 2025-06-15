from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import *

app = Flask(__name__)

def extract_video_id(url):
    import re
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@app.route("/transcript", methods=["POST"])
def get_transcript():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' in request body"}), 400

    video_id = extract_video_id(data["url"])
    if not video_id:
        return jsonify({"error": "Invalid URL"}), 400

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join([t["text"] for t in transcript])
        return jsonify({"transcript": full_text})
    except TranscriptsDisabled:
        return jsonify({"error": "Subtitles disabled"}), 400
    except NoTranscriptFound:
        return jsonify({"error": "No transcript found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
