import json
import time
from datetime import datetime
from google import genai
import streamlit as st

st.set_page_config(
    page_title="SSC CGL Quant Sprint — 25Q TCS Drill",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------- SESSION STATE -----------------
if "questions" not in st.session_state:
  st.session_state.questions = None
if "user_answers" not in st.session_state:
  st.session_state.user_answers = {}
if "test_submitted" not in st.session_state:
  st.session_state.test_submitted = False
if "start_time" not in st.session_state:
  st.session_state.start_time = None
if "total_time_taken" not in st.session_state:
  st.session_state.total_time_taken = 0
if "audit_history" not in st.session_state:
  st.session_state.audit_history = []
if "session_counter" not in st.session_state:
  st.session_state.session_counter = 0

# ----------------- SECRETS / SIDEBAR KEY -----------------
# Supports both Streamlit Secrets and manual sidebar input
api_key = st.secrets.get("GEMINI_API_KEY", None)

with st.sidebar:
  st.title("⚙️ Portal Settings")
  if not api_key:
    api_key = st.text_input(
        "Enter Gemini API Key",
        type="password",
        help="Get your free key from aistudio.google.com",
    )

  st.divider()
  st.subheader("📊 Lifetime Audit Tracker")
  total_drills = len(st.session_state.audit_history)
  st.metric("Drills Completed", total_drills)

  if total_drills > 0:
    avg_accuracy = (
        sum(item["accuracy"] for item in st.session_state.audit_history)
        / total_drills
    )
    avg_score = (
        sum(item["score"] for item in st.session_state.audit_history)
        / total_drills
    )
    st.metric("Average Accuracy", f"{avg_accuracy:.1f}%")
    st.metric("Average Score", f"{avg_score:.1f} / 50")

    st.write("---")
    st.caption("Recent Submissions:")
    for record in reversed(st.session_state.audit_history[-5:]):
      st.text(
          f"{record['timestamp']} | Acc: {record['accuracy']:.0f}% | Score:"
          f" {record['score']:.1f}"
      )
  else:
    st.info("No completed tests yet. Start a session!")

# ----------------- PROMPT DEFINITION -----------------
PROMPT_TEMPLATE = """
Generate an authentic SSC CGL Tier 1 and Tier 2 practice drill of exactly 25 multiple-choice questions strictly adhering to TCS PYQ patterns.
STRICT COMPOSITION:
- Exactly 9 Simplification problems (BODMAS nested brackets with 'of' and division, recurring decimals, fraction ladders, mixed fractions, surds/indices).
- Exactly 16 Arithmetic Word Problems (Percentage, Profit & Loss, CI/SI, Ratio, Mixture, Time & Work, TSD, Averages, DI).
- Shuffle and intersperse the 9 Simplification and 16 Arithmetic questions randomly throughout all 25 questions.
- Pure maths (Geometry, Mensuration, Trigonometry, Algebra) is strictly excluded.

CRITICAL JSON FORMAT RULE:
Output ONLY a raw JSON array containing 25 objects. No markdown ticks, no commentary.
Each object must have these exact keys:
[
  {
    "id": 1,
    "type": "Simplification" or "Arithmetic",
    "question": "Question text here (clear plain text with clean notation)",
    "options": ["A) option 1", "B) option 2", "C) option 3", "D) option 4"],
    "correct": "A",
    "concept_solution": "Detailed step-by-step conceptual explanation",
    "exam_shortcut": "⚡ 5-15 second topper trick / shortcut method"
  }
]
"""


def fetch_new_drill():
  if not api_key:
    st.error("Please provide a valid Gemini API Key to fetch fresh sets.")
    return

  with st.spinner(
      "⚡ Contacting Gemini to generate 25 authentic TCS PYQ questions..."
  ):
    try:
      client = genai.Client(api_key=api_key)
      response = client.models.generate_content(
          model="gemini-2.5-flash",
          contents=PROMPT_TEMPLATE,
          config={"response_mime_type": "application/json"},
      )
      questions_data = json.loads(response.text)

      if len(questions_data) == 25:
        st.session_state.questions = questions_data
        st.session_state.user_answers = {q["id"]: None for q in questions_data}
        st.session_state.test_submitted = False
        st.session_state.start_time = time.time()
        st.session_state.session_counter += 1
        st.success(
            f"Session #{st.session_state.session_counter} Loaded! 25-minute"
            " timer is active."
        )
      else:
        st.error(
            f"Received {len(questions_data)} questions instead of 25. Please"
            " refresh again."
        )
    except Exception as e:
      st.error(f"Error fetching questions: {str(e)}")


# ----------------- TOP BAR -----------------
col_title, col_action = st.columns([4, 1.2])
with col_title:
  st.title("🎯 SSC CGL Quant Sprint — 25Q Engine")
  st.caption(
      "Authentic TCS Pattern • 9 Simplification + 16 Arithmetic • 25 Minutes •"
      " Marking: +2 / -0.5"
  )

with col_action:
  st.write("")
  if st.button(
      "🔄 Next Session / Refresh", use_container_width=True, type="primary"
  ):
    fetch_new_drill()

# ----------------- MAIN PORTAL BODY -----------------
if st.session_state.questions:
  elapsed_seconds = int(time.time() - st.session_state.start_time)
  remaining_seconds = max(0, (25 * 60) - elapsed_seconds)
  rem_min, rem_sec = divmod(remaining_seconds, 60)

  col_timer, col_tracker = st.columns([1, 3])
  with col_timer:
    st.metric("⏱️ Time Remaining", f"{rem_min:02d}:{rem_sec:02d}")
  with col_tracker:
    attempted_count = sum(
        1 for ans in st.session_state.user_answers.values() if ans is not None
    )
    st.progress(
        attempted_count / 25,
        text=f"Progress: {attempted_count} of 25 Questions Answered",
    )

  st.divider()

  if not st.session_state.test_submitted:
    # Render all 25 questions
    for q in st.session_state.questions:
      qid = q["id"]
      st.markdown(f"#### Q{qid}. `[{q['type']}]` {q['question']}")

      # Extract clean option list
      opts = q["options"]
      selected = st.radio(
          label=f"q_{qid}_radio",
          options=["A", "B", "C", "D"],
          format_func=lambda x, opts=opts: next(
              (opt for opt in opts if opt.startswith(x)), x
          ),
          index=None
          if st.session_state.user_answers[qid] is None
          else ["A", "B", "C", "D"].index(st.session_state.user_answers[qid]),
          key=f"radio_input_{qid}",
          label_visibility="collapsed",
      )
      if selected:
        st.session_state.user_answers[qid] = selected
      st.write("")

    col_sub1, col_sub2, col_sub3 = st.columns([1, 2, 1])
    with col_sub2:
      if st.button(
          "🚀 Submit Test & View Full Analysis",
          type="primary",
          use_container_width=True,
      ):
        st.session_state.test_submitted = True
        st.session_state.total_time_taken = round(
            (time.time() - st.session_state.start_time) / 60, 1
        )
        st.rerun()

  else:
    # ----------------- SCORE EVALUATION -----------------
    correct = 0
    incorrect = 0
    unattempted = 0
    simp_c, simp_tot = 0, 0
    arith_c, arith_tot = 0, 0

    for q in st.session_state.questions:
      qid = q["id"]
      user_ans = st.session_state.user_answers.get(qid)
      is_simp = q["type"] == "Simplification"

      if is_simp:
        simp_tot += 1
      else:
        arith_tot += 1

      if user_ans is None:
        unattempted += 1
      elif user_ans == q["correct"]:
        correct += 1
        if is_simp:
          simp_c += 1
        else:
          arith_c += 1
      else:
        incorrect += 1

    attempted = correct + incorrect
    accuracy = (correct / attempted * 100) if attempted > 0 else 0
    raw_score = (correct * 2) - (incorrect * 0.5)

    # Save to history once
    if (
        not st.session_state.audit_history
        or st.session_state.audit_history[-1].get("session_id")
        != st.session_state.session_counter
    ):
      st.session_state.audit_history.append({
          "session_id": st.session_state.session_counter,
          "timestamp": datetime.now().strftime("%d %b, %I:%M %p"),
          "score": raw_score,
          "accuracy": accuracy,
          "time_mins": st.session_state.total_time_taken,
          "correct": correct,
          "incorrect": incorrect,
          "unattempted": unattempted,
      })

    # Summary Display
    st.subheader("📋 Performance Audit")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Raw Score", f"{raw_score:.1f} / 50")
    m2.metric("Accuracy", f"{accuracy:.1f}%")
    m3.metric("Correct / Wrong", f"{correct} / {incorrect}")
    m4.metric("Attempted", f"{attempted} / 25")
    m5.metric("Time Taken", f"{st.session_state.total_time_taken} mins")

    # Diagnostic feedback
    if accuracy >= 88 and st.session_state.total_time_taken <= 22:
      st.success(
          "🏆 Target Achieved: $\\ge 88\\%$ accuracy under 22 mins! You are"
          " ready for Pure Maths integration."
      )
    elif accuracy >= 80:
      st.warning(
          "⚠️ Good Pace, but Watch Negative Marking: Trim unforced errors in"
          " calculation."
      )
    else:
      st.error(
          "🚨 Leakage Detected: High error rate or guessing. Review shortcuts"
          " below."
      )

    st.info(
        f"**Section Breakdown:** Simplification: **{simp_c}/{simp_tot}**"
        f" | Arithmetic: **{arith_c}/{arith_tot}**"
    )

    # ----------------- DETAILED EXPLANATIONS -----------------
    st.write("---")
    with st.expander(
        "📖 Show Detailed Conceptual Solutions & Exam Shortcuts", expanded=True
    ):
      for q in st.session_state.questions:
        qid = q["id"]
        ans = st.session_state.user_answers.get(qid)
        is_correct = ans == q["correct"]

        badge = (
            "✅ Correct"
            if is_correct
            else ("⚠️ Skipped" if ans is None else "❌ Incorrect")
        )
        st.markdown(
            f"### Q{qid}. {badge} — `Your Answer: {ans or 'Unattempted'}` |"
            f" `Correct: {q['correct']}`"
        )
        st.write(f"**Question:** {q['question']}")
        st.info(f"**📘 Conceptual Method:**\n{q['concept_solution']}")
        st.success(f"**⚡ Exam Shortcut / Topper Trick:**\n{q['exam_shortcut']}")
        st.divider()

else:
  st.info(
      "👈 Click **'🔄 Next Session / Refresh'** in the top-right corner to"
      " generate your first authentic 25-question set."
  )