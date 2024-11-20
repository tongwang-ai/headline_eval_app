import streamlit as st
import pandas as pd
from datetime import datetime

# Function to save survey responses
def save_responses(responses):
    try:
        # Load existing responses if available
        existing_responses = pd.read_csv("survey_responses.csv")
    except FileNotFoundError:
        # If the file doesn't exist, create an empty DataFrame
        existing_responses = pd.DataFrame(columns=["Timestamp", "Question", "Choice"])

    # Append new responses
    all_responses = pd.concat([existing_responses, responses], ignore_index=True)
    
    # Save to CSV
    all_responses.to_csv("survey_responses.csv", index=False)

# List of questions and choices
questions = [
    {"question": "Which headline do you prefer for a new product launch?", 
     "choices": ["Headline 1A", "Headline 1B", "Headline 1C", "Headline 1D"]},
    {"question": "Which headline grabs your attention for a sale event?", 
     "choices": ["Headline 2A", "Headline 2B", "Headline 2C", "Headline 2D"]},
    {"question": "Which headline works best for a blog post about productivity?", 
     "choices": ["Headline 3A", "Headline 3B", "Headline 3C", "Headline 3D"]},
    {"question": "Which headline is most appealing for a fitness campaign?", 
     "choices": ["Headline 4A", "Headline 4B", "Headline 4C", "Headline 4D"]},
    {"question": "Which headline would you click for a tech gadget review?", 
     "choices": ["Headline 5A", "Headline 5B", "Headline 5C", "Headline 5D"]}
]

st.title("Headline Survey")
st.write("Please select the most appealing headline for each question.")

responses = []

# Iterate through questions
for i, q in enumerate(questions):
    st.subheader(f"Question {i + 1}: {q['question']}")
    choice = st.radio("Select your choice:", q['choices'], key=f"q{i+1}")
    responses.append({"Question": q['question'], "Choice": choice})

# Submit button
if st.button("Submit Survey"):
    # Add timestamp to responses
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response_df = pd.DataFrame(responses)
    response_df["Timestamp"] = timestamp

    # Save responses
    save_responses(response_df)

    st.success("Thank you for completing the survey! Your responses have been recorded.")
