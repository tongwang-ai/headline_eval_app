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
    Load all rows from the 'headline_relevance_survey_50_article_all_beta' table
    into a pandas DataFrame using a psycopg2 connection.
    """
    query = "SELECT * FROM headline_relevance_survey_50_article_all_beta;"
    
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    
    # Convert list of tuples into a DataFrame
    df = pd.DataFrame(rows, columns=["content", "headline", "original", "probability","reward","beta","model", "status"])
    return df

########################################
# 3) Sampling Logic
########################################
def sample_questions(df, n=8):
    """
    Filter out rows where status < 8, then sample 'n' rows
    with weights proportional to (8 - status).
    """
    # Filter: only rows with status < 8
    df_filtered = df[df["status"] < 8].copy()

    # Sample rows ensuring unique content
    df_sampled = df_filtered.groupby('content').apply(lambda x: x.sample(n=1)).sample(n=n, replace=False).reset_index(drop=True)
    
    return df_sampled

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
        # 2. Load data 
        if "df_pairs" not in st.session_state:
            st.session_state["df_pairs"] = load_pairs_data(conn)

        # 3. Sample 8 questions and store them persistently in session_state
        if "df_questions" not in st.session_state:
            st.session_state["df_questions"] = sample_questions(st.session_state["df_pairs"], n=8)

        # Get the persisted sampled questions
        df_questions = st.session_state["df_questions"]

        # If there are no rows to sample, notify the user
        if df_questions.empty:
            st.warning("No rows available (all have status >= 8).")
            return

        # 4. Display the questions
        st.info("""
        **We are studying the relevance of headlines for news articles.**
    
        You will be presented with 8 questions. For each question, you will see content from a news article along with its headline. Some of the content may be a summary of a video or feel like part of a longer article. 

        Please evaluate whether the **headline is relevant to the content or not** based solely on the **content provided**. Do not assume that additional context or content exists beyond what is shown. Treat the provided content as the only information available when making your evaluation.

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
                f"Do you think the headline is relevant to the content? (Question {i-1})",
                options=["", "Yes", "No"],  # Options include an empty default
                index=["", "Yes", "No"].index(st.session_state[question_key])  # Match the current value
            )

            # Append the response to user_responses
            user_responses.append({
                "content": row["content"],
                "headline": row["headline"],
                "original": row["original"],
                "probability": row["probability"],
                "reward": row["reward"],
                "beta": row["beta"],
                "model": row["model"],
                "relevance_judgement": st.session_state[question_key],  # Use updated session state
            })

            # Add a horizontal rule to separate questions
            st.markdown("---")

        # Validate responses
        if st.button("Submit Answers"):
            if any(resp["relevance_judgement"] == "" for resp in user_responses):
                st.warning("Please answer all questions before submitting.")
            else:
                submission_time = datetime.now()
                st.write("**Thank you!**")
                st.write("The completion code is headline2024")

                # Insert responses into the evaluation table and update statuses
                with conn.cursor() as cur:
                    # Insert user responses
                    insert_query = """
                        INSERT INTO headline_relevance_evaluation_50_article_all_beta
                        (content,headline,original, probability, reward, beta, model, relevance_judgement, start_time, submission_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    # Update status
                    update_query = """
                        UPDATE headline_relevance_survey_50_article_all_beta
                        SET status = status + 1
                        WHERE content = %s AND headline = %s AND beta = %s AND model = %s;
                    """
                    for resp in user_responses:
                        # Insert response
                        cur.execute(
                            insert_query,
                            (
                                resp["content"],
                                resp["headline"],
                                resp["original"],
                                resp["probability"],
                                resp["reward"],
                                resp["beta"],
                                resp["model"],
                                resp["relevance_judgement"],
                                st.session_state["start_time"],  # Survey start time
                                submission_time                 # Survey end time
                            )
                        )
                        # Update status
                        if resp["content"] is not None:
                            cur.execute(
                                update_query,
                                (resp["content"], resp["headline"], resp["beta"], resp["model"])
                            )
                    conn.commit()

                # Indicate success
                st.success("Responses have been recorded! Thank you!")
    finally:
        # Ensure the connection is closed
        conn.close()

if __name__ == "__main__":
    main()
