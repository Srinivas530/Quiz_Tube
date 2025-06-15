import streamlit as st
from dotenv import load_dotenv
import os
import re
import json
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Extract YouTube Video ID
def extract_video_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

# Extract transcript
def extract_transcript_details(youtube_video_url):
    video_id = extract_video_id(youtube_video_url)
    if not video_id:
        raise ValueError("❌ Invalid YouTube URL")

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en']).fetch()
        return " ".join([entry.text for entry in transcript])

    except TranscriptsDisabled:
        raise RuntimeError("⚠️ Subtitles are disabled for this video.")
    except NoTranscriptFound:
        raise RuntimeError("⚠️ No English transcript found for this video.")
    except VideoUnavailable:
        raise RuntimeError("⚠️ The video is unavailable or private.")
    except Exception as e:
        raise RuntimeError(f"❌ An unexpected error occurred: {str(e)}")

# Generate notes
def generate_gemini_notes(transcript_text):
    prompt = "Generate detailed notes from this YouTube video transcript:\n"
    model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
    response = model.generate_content(prompt + transcript_text)
    return response.text

# Extract JSON quiz
def extract_json(text):
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return match.group(0)
    else:
        raise ValueError("No JSON array found in response")

# Generate quiz
def generate_quiz(transcript_text):
    prompt = """
Generate a 5-question multiple choice quiz based on the following transcript. 
Each question should have:
- a 'question' field (string),
- an 'options' field (list of 4 strings),
- a 'correct' field (index of the correct option from 0 to 3)

Output should be valid JSON like this:
[
  {
    "question": "What is ...?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 2
  },
  ...
]

Transcript:
"""
    model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
    response = model.generate_content(prompt + transcript_text)

    try:
        quiz_json_str = extract_json(response.text)
        quiz_data = json.loads(quiz_json_str)
        return quiz_data
    except json.JSONDecodeError:
        st.error("❌ Error parsing quiz JSON. Please try again.")
        st.stop()

# Initialize session state
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "user_answers" not in st.session_state:
    st.session_state.user_answers = []
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "notes" not in st.session_state:
    st.session_state.notes = ""

# UI
st.title("📺 QuizTube: YouTube to Notes + Quiz")
youtube_link = st.text_input("Enter YouTube video link:")

if youtube_link:
    try:
        st.video(youtube_link)
        st.session_state.transcript = extract_transcript_details(youtube_link)
        st.success("✅ Transcript extracted successfully.")
    except Exception as e:
        st.error(str(e))

# Notes
if st.button("📒 Generate Notes"):
    if st.session_state.transcript:
        with st.spinner("Generating notes..."):
            st.session_state.notes = generate_gemini_notes(st.session_state.transcript)
        st.subheader("📝 Detailed Notes")
        st.write(st.session_state.notes)

# Quiz
if st.button("🎯 Generate Quiz"):
    if st.session_state.transcript:
        with st.spinner("Generating quiz..."):
            st.session_state.quiz_data = generate_quiz(st.session_state.transcript)
            st.session_state.user_answers = [None] * len(st.session_state.quiz_data)
        st.success("✅ Quiz generated!")

# Quiz UI
if st.session_state.quiz_data:
    st.subheader("🧪 Attempt the Quiz")

    for i, q in enumerate(st.session_state.quiz_data):
        selected = st.radio(
            f"Q{i+1}: {q['question']}",
            q['options'],
            index=None,
            key=f"q{i}"
        )

        if selected is not None:
            st.session_state.user_answers[i] = q['options'].index(selected)
            correct_answer = q['options'][q['correct']]
            

    if st.button("📤 Submit Answers"):
        if None in st.session_state.user_answers:
            st.warning("⚠️ Please answer all questions before submitting.")
        else:
            score = 0
            st.subheader("📊 Quiz Results")
            for i, q in enumerate(st.session_state.quiz_data):
                user_idx = st.session_state.user_answers[i]
                correct_idx = q['correct']
                correct_option = q['options'][correct_idx]
                user_option = q['options'][user_idx]

                if user_idx == correct_idx:
                    st.markdown(f"**Q{i+1}: ✅ Correct** — {q['question']}")
                    score += 1
                else:
                    st.markdown(f"**Q{i+1}: ❌ Incorrect** — {q['question']}")
                    st.markdown(f"Your answer: {user_option}  \nCorrect answer: **{correct_option}**")

            st.success(f"🎉 You scored **{score} / {len(st.session_state.quiz_data)}**")
