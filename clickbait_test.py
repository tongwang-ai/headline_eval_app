import streamlit as st
import pandas as pd
import psycopg2
import random
from datetime import datetime  # <-- we need datetime for timestamps

########################################
# 1) Database Connection Function
########################################
def create_connection():
    """
    Returns a psycopg2 connection object using credentials
    in Streamlit secrets.
    """
    return psycopg2.connect(
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        sslmode="require"
    )

########################################
# 2) Data Loading
########################################
def load_pairs_data(conn):
    """
    Load all rows from the 'theoryguided_clickbait_survey_200_v2' table
    into a pandas DataFrame using a psycopg2 connection.
    """
    query = "SELECT content, headline, cos_similarity, status FROM theoryguided_clickbait_survey_200_v2;"
    
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    
    # Convert list of tuples into a DataFrame
    df = pd.DataFrame(rows, columns=["content", "headline", "cos_similarity", "status"])
    return df

########################################
# 3) Sampling Logic
########################################
def sample_questions(df, n=10):
    """
    Filter out rows where status < 5, then sample 'n' rows
    with weights proportional to (5 - status).
    """
    # Filter: only rows with status < 5
    df_filtered = df[df["status"] < 5].copy()

    # Compute weights = 5 - status
    df_filtered["weight"] = 5 - df_filtered["status"]

    # If fewer than n rows remain, sample as many as possible
    sample_size = min(n, len(df_filtered))

    if sample_size == 0:
        return pd.DataFrame(columns=df_filtered.columns)  # Empty DF

    # Weighted sampling without replacement
    df_sampled = df_filtered.sample(
        n=sample_size,
        weights="weight",
        replace=False,
        random_state=None  # or an integer for reproducibility
    )

    return df_sampled

########################################
# 4) Main Streamlit App
########################################
########################################
# 4) Main Streamlit App
########################################
def main():
    st.title("Evaluating the Headlines")

    # Record the survey start time if not already set
    if "start_time" not in st.session_state:
        st.session_state["start_time"] = datetime.now()

    # 1. Connect to DB
    conn = create_connection()

    try:
        # 2. Load data from 'theoryguided_clickbait'
        if "df_pairs" not in st.session_state:
            st.session_state["df_pairs"] = load_pairs_data(conn)

        # 3. Sample 10 questions and store them persistently in session_state
        if "df_questions" not in st.session_state:
            st.session_state["df_questions"] = sample_questions(st.session_state["df_pairs"], n=10)

        # Get the persisted sampled questions
        df_questions = st.session_state["df_questions"]

        # If there are no rows to sample, notify the user
        if df_questions.empty:
            st.warning("No rows available (all have status >= 5).")
            return

        # 4. Display the questions
        st.info("""
        **We are studying the relevance of headlines for news articles.**
    
        You will be presented with 10 questions. For each question, you will see content from a news article along with its headline. Some of the content may be a summary of a video. After reviewing the content and headline, please answer whether you think the headline is clickbait or not, as if you were a user browsing online news.
        """)

        # Initialize user responses
        user_responses = []
        i = 1

        for idx, row in df_questions.iterrows():
            st.markdown(f"Question {i}")
            i += 1
            st.markdown(f"**Headline:** {row['headline']}")
            st.markdown(f"**Content:** {row['content']}")

            # Define a unique session state key for each question
            question_key = f"question_{idx}_{row['headline']}"

            # Initialize the session state for this question if not already set
            if question_key not in st.session_state:
                st.session_state[question_key] = ""  # Default to empty string

            # Render the radio button directly tied to the session state
            st.session_state[question_key] = st.radio(
                f"Do you feel the headline is clickbait? (Question {i-1})",
                options=["", "Yes", "No"],  # Options include an empty default
                index=["", "Yes", "No"].index(st.session_state[question_key])  # Match the current value
            )

            # Append the response to user_responses
            user_responses.append({
                "content": row["content"],
                "headline": row["headline"],
                "cos_similarity": row["cos_similarity"],
                "status": row["status"],
                "clickbait_judgment": st.session_state[question_key],  # Use updated session state
            })

            # Add a horizontal rule to separate questions
            st.markdown("---")

        # Validate responses
        if st.button("Submit Answers"):
            if any(resp["clickbait_judgment"] == "" for resp in user_responses):
                st.warning("Please answer all questions before submitting.")
            else:
                submission_time = datetime.now()
                st.write("**Thank you!**")
                st.write("The completion code is headline2024")

                # Insert responses into the evaluation table and update statuses
                with conn.cursor() as cur:
                    # Insert user responses
                    insert_query = """
                        INSERT INTO theoryguided_headline_evaluation
                        (content, headline, cos_similarity, clickbait_judgment, start_time, submission_time)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    # Update status
                    update_query = """
                        UPDATE theoryguided_clickbait_survey_200_v2
                        SET status = status + 1
                        WHERE content = %s AND headline = %s;
                    """
                    for resp in user_responses:
                        # Insert response
                        cur.execute(
                            insert_query,
                            (
                                resp["content"],
                                resp["headline"],
                                resp["cos_similarity"],
                                resp["clickbait_judgment"],
                                st.session_state["start_time"],  # Survey start time
                                submission_time                  # Survey end time
                            )
                        )
                        # Update status
                        cur.execute(
                            update_query,
                            (resp["content"], resp["headline"])
                        )
                    conn.commit()

                # Indicate success
                st.success("Responses have been recorded! Thank you!")
    finally:
        # Ensure the connection is closed
        conn.close()

if __name__ == "__main__":
    main()
