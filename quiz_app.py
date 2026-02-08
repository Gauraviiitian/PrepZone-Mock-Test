import streamlit as st
from typing import List, Dict
import pandas as pd
import os
from datetime import datetime
import hashlib

# Page configuration
st.set_page_config(
    page_title="MCQ Quiz",
    page_icon="📝",
    layout="centered"
)

# Authorization token (can be changed in environment variables)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "prepzoneauthuser$")  # Default token, change in production

# Load questions from Excel file
def load_questions_from_excel(file_path: str) -> List[Dict]:
    """
    Load questions from an Excel file.
    
    Expected Excel format:
    - Column A: id (1, 2, 3, ...)
    - Column B: question (Question text)
    - Column C: option1 (First option)
    - Column D: option2 (Second option)
    - Column E: option3 (Third option)
    - Column F: option4 (Fourth option)
    - Column G: correct_answer (The correct option)
    """
    if not os.path.exists(file_path):
        st.error(f"Excel file not found: {file_path}")
        return []
    
    df = pd.read_excel(file_path)
    questions = []
    
    for idx, row in df.iterrows():
        question = {
            "id": int(row["id"]),
            "question": str(row["question"]),
            "options": [
                str(row["option1"]),
                str(row["option2"]),
                str(row["option3"]),
                str(row["option4"])
            ],
            "correct_answer": str(row["correct_answer"])
        }
        questions.append(question)
    
    return questions


# Load questions from Excel
EXCEL_FILE = "questions.xlsx"
QUESTIONS = load_questions_from_excel(EXCEL_FILE)


def initialize_session_state():
    """Initialize session state variables."""
    if "quiz_started" not in st.session_state:
        st.session_state.quiz_started = False
    if "answers" not in st.session_state:
        st.session_state.answers = {}
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False


def calculate_score(answers: Dict[int, str]) -> tuple[int, int]:
    """
    Calculate the score based on user answers.
    
    Returns:
        tuple: (correct_answers, total_questions)
    """
    correct = 0
    for question_id, answer in answers.items():
        question = next((q for q in QUESTIONS if q["id"] == question_id), None)
        if question and answer == question["correct_answer"]:
            correct += 1
    return correct, len(QUESTIONS)


def calculate_stats(answers: Dict[int, str], total: int) -> tuple[int, int, int]:
    """
    Calculate detailed statistics.
    
    Returns:
        tuple: (correct_answers, wrong_answers, unattempted_answers)
    """
    correct = 0
    unattempted = 0
    
    for question_id in range(1, total + 1):
        answer = answers.get(question_id)
        if answer is None:
            unattempted += 1
        else:
            question = next((q for q in QUESTIONS if q["id"] == question_id), None)
            if question and answer == question["correct_answer"]:
                correct += 1
    
    wrong = total - correct - unattempted
    return correct, wrong, unattempted


def save_results_to_excel(name: str, answers: Dict[int, str]) -> None:
    """Save user results to results.xlsx file."""
    results_file = "results.xlsx"
    
    correct, wrong, unattempted = calculate_stats(answers, len(QUESTIONS))
    marks = correct  # Assuming 1 mark per correct answer
    percentage = (correct / len(QUESTIONS)) * 100
    
    # Create new result entry
    new_result = {
        "Name": name,
        "Total Marks": marks,
        "Correct Answers": correct,
        "Wrong Answers": wrong,
        "Unattempted": unattempted,
        "Percentage": f"{percentage:.1f}%",
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Load existing results or create new file
    if os.path.exists(results_file):
        df = pd.read_excel(results_file)
        df = pd.concat([df, pd.DataFrame([new_result])], ignore_index=True)
    else:
        df = pd.DataFrame([new_result])
    
    # Sort by marks in descending order
    df = df.sort_values("Total Marks", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    
    # Save to Excel
    df.to_excel(results_file, index=False)


def display_ranklist() -> None:
    """Display the ranklist from results.xlsx."""
    results_file = "results.xlsx"
    
    if os.path.exists(results_file):
        df = pd.read_excel(results_file)
        st.subheader("📊 Ranklist")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No results yet. Be the first to take the quiz!")


def verify_token(token: str) -> bool:
    """Verify if the provided token is valid."""
    return token == ADMIN_TOKEN


def display_admin_panel():
    """Display the admin panel for uploading questions."""
    st.title("🔐 Admin Panel")
    st.write("---")
    
    st.subheader("Upload Questions")
    st.write("Upload an Excel file with the following columns:")
    
    # Show example format
    example_data = {
        'id': [1, 2],
        'question': ['Sample Question 1?', 'Sample Question 2?'],
        'option1': ['Option A', 'Option A'],
        'option2': ['Option B', 'Option B'],
        'option3': ['Option C', 'Option C'],
        'option4': ['Option D', 'Option D'],
        'correct_answer': ['Option A', 'Option B']
    }
    st.dataframe(pd.DataFrame(example_data), use_container_width=True, hide_index=True)
    
    st.write("---")
    
    # File uploader
    uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            
            # Validate columns
            required_columns = ['id', 'question', 'option1', 'option2', 'option3', 'option4', 'correct_answer']
            if not all(col in df.columns for col in required_columns):
                st.error(f"❌ Missing required columns. Expected: {required_columns}")
            else:
                # Save the file
                df.to_excel("questions.xlsx", index=False)
                st.success("✅ Questions uploaded successfully!")
                st.info(f"Total questions loaded: {len(df)}")
                
                # Reload questions
                global QUESTIONS
                QUESTIONS = load_questions_from_excel("questions.xlsx")
                st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error uploading file: {str(e)}")
    
    st.write("---")
    st.subheader("Current Questions")
    if QUESTIONS:
        st.write(f"Total questions: {len(QUESTIONS)}")
        with st.expander("View all questions"):
            for q in QUESTIONS:
                st.write(f"**Q{q['id']}: {q['question']}**")
    else:
        st.warning("No questions loaded yet. Upload a file to get started.")


def display_admin_logout():
    """Display the admin logout button."""
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.is_admin = False
        st.rerun()


def display_quiz():
    """Display the quiz interface."""
    st.title("📝 Multiple Choice Quiz")
    
    # Name input
    st.session_state.user_name = st.text_input("Enter your name:", value=st.session_state.user_name)
    st.write("---")
    
    # Create form for quiz
    with st.form("quiz_form"):
        for question in QUESTIONS:
            st.subheader(f"Question {question['id']}")
            st.write(question["question"])
            
            selected_answer = st.radio(
                label="Select your answer:",
                options=question["options"],
                index=None,
                key=f"q_{question['id']}"
            )
            st.session_state.answers[question["id"]] = selected_answer
            st.write("---")
        
        submitted = st.form_submit_button("Submit Quiz", use_container_width=True)
        
        if submitted:
            st.session_state.submitted = True
            return True
    
    return False


def display_results():
    """Display the quiz results and score."""
    st.title("📊 Quiz Results")
    st.write(f"**Name:** {st.session_state.user_name}")
    st.write("---")
    
    correct, total = calculate_score(st.session_state.answers)
    correct_ans, wrong_ans, unattempted = calculate_stats(st.session_state.answers, total)
    percentage = (correct / total) * 100
    
    # Save results to Excel
    save_results_to_excel(st.session_state.user_name, st.session_state.answers)
    
    # Display score
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Score", f"{correct}/{total}")
    with col2:
        st.metric("Percentage", f"{percentage:.1f}%")
    with col3:
        if percentage >= 80:
            status = "🟢 Excellent"
        elif percentage >= 60:
            status = "🟡 Good"
        else:
            status = "🔴 Needs Improvement"
        st.metric("Status", status)
    
    st.write("---")
    
    # Display summary statistics
    st.subheader("Summary")
    summary_cols = st.columns(3)
    with summary_cols[0]:
        st.metric("✅ Correct", correct_ans)
    with summary_cols[1]:
        st.metric("❌ Wrong", wrong_ans)
    with summary_cols[2]:
        st.metric("⏭️ Unattempted", unattempted)
    
    st.write("---")
    
    # Display detailed results
    st.subheader("Detailed Results")
    for question in QUESTIONS:
        user_answer = st.session_state.answers.get(question["id"], None)
        is_correct = user_answer == question["correct_answer"]
        
        if user_answer is None:
            status_icon = "⏭️"
        else:
            status_icon = "✅" if is_correct else "❌"
        
        st.write(f"{status_icon} **Question {question['id']}: {question['question']}**")
        st.write(f"Your answer: **{user_answer if user_answer else 'Not answered'}**")
        if user_answer and not is_correct:
            st.write(f"Correct answer: **{question['correct_answer']}**")
        st.write("---")
    
    # Reset button
    if st.button("Retake Quiz", use_container_width=True):
        st.session_state.answers = {}
        st.session_state.submitted = False
        st.rerun()


def main():
    """Main application function."""
    initialize_session_state()
    
    # Check for admin mode via query parameter or session state
    query_params = st.query_params
    
    # If admin token is provided in URL, authenticate
    if "admin_token" in query_params:
        token = query_params["admin_token"]
        if verify_token(token):
            st.session_state.is_admin = True
        else:
            st.error("❌ Invalid token")
            return
    
    # Show admin panel if authenticated
    if st.session_state.is_admin:
        st.sidebar.success("✅ Admin Mode Active")
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            st.session_state.is_admin = False
            st.query_params.clear()
            st.rerun()
        st.sidebar.write("---")
        display_admin_panel()
    else:
        # Regular user interface
        st.sidebar.title("📈 Ranklist")
        display_ranklist()
        
        # Check if questions are loaded
        if not QUESTIONS:
            st.error("❌ No questions available. Please try again later.")
        else:
            if not st.session_state.submitted:
                display_quiz()
            else:
                display_results()


if __name__ == "__main__":
    main()
