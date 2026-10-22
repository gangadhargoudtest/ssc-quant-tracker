import json
import time
from datetime import datetime
from google import genai
import streamlit as st

st.set_page_config(
    page_title="SSC CGL Quant Sprint — Exam Portal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------- CUSTOM HIGH-END EXAM CSS -----------------
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0f172a;
    }
    
    .stApp {
        background-color: #f8fafc;
    }

    /* Clean Sticky Top Bar */
    .exam-header {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 24px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Question Cards */
    .question-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
    }
    
    .badge-simp {
        background-color: #e0f2fe;
        color: #0369a1;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
        margin-bottom: 12px;
    }
    
    .badge-arith {
        background-color: #fef3c7;
        color: #b45309;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: inline-block;
        margin-bottom: 12px;
    }

    .q-text {
        font-size: 1.05rem;
        line-height: 1.6;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 16px;
    }

    /* Solution Blocks */
    .concept-card {
        background: #f1f5f9;
        border-left: 4px solid #3b82f6;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        font-size: 0.93rem;
        line-height: 1.6;
        margin-bottom: 12px;
    }

    .shortcut-card {
        background: #ecfdf5;
        border-left: 4px solid #10b981;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        font-size: 0.93rem;
        line-height: 1.6;
    }

    /* Timer Display */
    .timer-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.35rem;
        font-weight: 700;
        color: #0284c7;
        background: #f0f9ff;
        padding: 6px 16px;
        border-radius: 8px;
        border: 1px solid #bae6fd;
        display: inline-block;
    }
</style>
""",
    unsafe_allow_html=True,
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

api_key = st.secrets.get("GEMINI_API_KEY", None)

with st.sidebar:
  st.markdown("### ⚡ Exam Dashboard")
  if not api_key:
    api_key = st.text_input(
        "Enter Gemini API Key",
        type="password",
        help="Get your key from aistudio.google.com",
    )

  st.divider()
  st.markdown("#### 📈 Lifetime Audit")
  drills_count = len(st.session_state.audit_history)
  st.metric("Total Drills Completed", drills_count)

  if drills_count > 0:
    avg_accuracy = (
        sum(item["accuracy"] for item in st.session_state.audit_history)
        / drills_count
    )
    avg_score = (
        sum(item["score"] for item in st.session_state.audit_history)
        / drills_count
    )
    st.metric("Lifetime Accuracy", f"{avg_accuracy:.1f}%")
    st.metric("Average Score", f"{avg_score:.1f} / 50")
    st.caption("Target: $\\ge 88\\%$ & $< 22$ mins")

# ----------------- GENERATION PROMPT -----------------
PROMPT_TEMPLATE = """
Generate an authentic SSC CGL Tier 1 and Tier 2 practice drill of exactly 25 multiple-choice questions strictly adhering to TCS PYQ patterns.
STRICT COMPOSITION:
- Exactly 9 Simplification problems (BODMAS nested brackets with 'of' and division, recurring decimals, fraction ladders, mixed fractions, surds/indices).
- Exactly 16 Arithmetic Word Problems (Percentage, Profit & Loss, CI/SI, Ratio, Mixture, Time & Work, TSD, Averages, DI).
- Shuffle and intersperse the 9 Simplification and 16 Arithmetic questions randomly throughout all 25 questions.
- Pure maths (Geometry, Mensuration, Trigonometry, Algebra) is strictly excluded.

CRITICAL JSON FORMAT:
Return ONLY a valid JSON array containing 25 objects. No markdown ticks, no commentary.
Each object must have these exact keys:
[
  {
    "id": 1,
    "type": "Simplification" or "Arithmetic",
    "question": "Question text here (clean standard text, clear mathematical notation)",
    "options": ["A) option 1", "B) option 2", "C) option 3", "D) option 4"],
    "correct": "A",
    "concept_solution": "Detailed step-by-step conceptual explanation",
    "exam_shortcut": "5-15 second topper trick / shortcut method"
  }
]
"""


def fetch_new_drill():
  if not api_key:
    st.error("Please provide a valid Gemini API Key.")
    return

  with st.spinner("⚡ Curating 25 authentic TCS PYQ questions..."):
    try:
      client = genai.Client(api_key=api_key)
      response = client.models.generate_content(
          model="gemini-3.8-flash",
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
        st.rerun()
      else:
        st.error(
            f"Received {len(questions_data)} questions instead of 25. Please"
            " refresh."
        )
    except Exception as e:
      st.error(f"Error fetching questions: {str(e)}")


# ----------------- TOP NAVBAR -----------------
c_brand, c_refresh = st.columns([4, 1.2])
with c_brand:
  st.markdown(
      "<h2 style='margin:0; font-weight:800; color:#0f172a;'>🎯 SSC CGL Quant"
      " Speed Sprint</h2><p style='margin:0; color:#64748b; font-size:0.9rem;'"
      ">Authentic TCS Pattern • 9 Simplification + 16 Arithmetic • 25Q / 50"
      " Marks • -0.5 Negative Marking</p>",
      unsafe_allow_html=True,
  )
with c_refresh:
  if st.button(
      "🔄 Next Session / Refresh", use_container_width=True, type="primary"
  ):
    fetch_new_drill()

st.write("")

# ----------------- TEST VIEW / PALETTE -----------------
if st.session_state.questions:
  elapsed_sec = int(time.time() - st.session_state.start_time)
  rem_sec = max(0, (25 * 60) - elapsed_sec)
  rem_m, rem_s = divmod(rem_sec, 60)
  answered_count = sum(
      1 for a in st.session_state.user_answers.values() if a is not None
  )

  # Status Bar
  sb_col1, sb_col2, sb_col3 = st.columns([1.5, 3, 1.5])
  with sb_col1:
    st.markdown(
        f"<div class='timer-badge'>⏱️ {rem_m:02d}:{rem_s:02d}</div>",
        unsafe_allow_html=True,
    )
  with sb_col2:
    st.progress(
        answered_count / 25,
        text=f"Attempted: {answered_count} / 25 Questions",
    )
  with sb_col3:
    st.markdown(
        f"<div style='text-align:right; font-weight:700; color:#475569;"
        f" padding-top:6px;'>Session"
        f" #{st.session_state.session_counter}</div>",
        unsafe_allow_html=True,
    )

  st.write("")

  # ----------------- TEST TAKING VIEW -----------------
  if not st.session_state.test_submitted:
    # 2-column layout: Questions (Main) and Quick Palette (Sidebar/Right)
    q_col, p_col = st.columns([3.5, 1.2])

    with q_col:
      for q in st.session_state.questions:
        qid = q["id"]
        badge_cls = (
            "badge-simp" if q["type"] == "Simplification" else "badge-arith"
        )

        st.markdown(
            f"""
                <div class="question-box">
                    <span class="{badge_cls}">{q['type']}</span>
                    <div class="q-text">Q{qid}. {q['question']}</div>
                </div>
                """,
            unsafe_allow_html=True,
        )

        opts = q["options"]
        selected = st.radio(
            label=f"q_{qid}",
            options=["A", "B", "C", "D"],
            format_func=lambda x, opts=opts: next(
                (opt for opt in opts if opt.startswith(x)), x
            ),
            index=None
            if st.session_state.user_answers[qid] is None
            else ["A", "B", "C", "D"].index(st.session_state.user_answers[qid]),
            key=f"ans_key_{qid}",
            label_visibility="collapsed",
        )
        if selected:
          st.session_state.user_answers[qid] = selected
        st.write("")

      # Submit Action Button
      st.write("---")
      c_sub1, c_sub2, c_sub3 = st.columns([1, 2, 1])
      with c_sub2:
        if st.button(
            "🚀 Submit Test & Generate Scorecard",
            type="primary",
            use_container_width=True,
        ):
          st.session_state.test_submitted = True
          st.session_state.total_time_taken = round(
              (time.time() - st.session_state.start_time) / 60, 1
          )
          st.rerun()

    with p_col:
      st.markdown(
          "<div style='background:#ffffff; border:1px solid #e2e8f0;"
          " border-radius:12px; padding:16px; position:sticky; top:20px;'>"
          "<h4 style='margin-top:0;'>Question Palette</h4>",
          unsafe_allow_html=True,
      )
      palette_cols = st.columns(5)
      for i in range(1, 26):
        is_ans = st.session_state.user_answers.get(i) is not None
        btn_style = "●" if is_ans else "○"
        col_idx = (i - 1) % 5
        with palette_cols[col_idx]:
          st.caption(f"**Q{i}**")
          st.markdown(
              f"<span style='color:{'#059669' if is_ans else '#94a3b8'};"
              f" font-size:18px;'>{btn_style}</span>",
              unsafe_allow_html=True,
          )
      st.markdown(
          "<p style='margin-top:12px; font-size:0.75rem; color:#64748b;'>●"
          " Answered &nbsp;&nbsp; ○ Not Answered</p></div>",
          unsafe_allow_html=True,
      )

  # ----------------- SUBMISSION & RESULTS VIEW -----------------
  else:
    correct, incorrect, unattempted = 0, 0, 0
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

    # Top Results Banner
    st.markdown(
        f"""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:24px; margin-bottom:24px;">
            <h3 style="margin-top:0; color:#0f172a;">📊 Performance Scorecard</h3>
            <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:16px;">
                <div><div style="font-size:0.8rem; color:#64748b;">SCORE</div><div style="font-size:1.8rem; font-weight:800; color:#0284c7;">{raw_score:.1f} <span style="font-size:1rem; color:#94a3b8;">/ 50</span></div></div>
                <div><div style="font-size:0.8rem; color:#64748b;">ACCURACY</div><div style="font-size:1.8rem; font-weight:800; color:{'#059669' if accuracy >= 88 else '#d97706'};">{accuracy:.1f}%</div></div>
                <div><div style="font-size:0.8rem; color:#64748b;">CORRECT / WRONG</div><div style="font-size:1.8rem; font-weight:800; color:#334155;">{correct} <span style="color:#ef4444;">/ {incorrect}</span></div></div>
                <div><div style="font-size:0.8rem; color:#64748b;">TIME TAKEN</div><div style="font-size:1.8rem; font-weight:800; color:#334155;">{st.session_state.total_time_taken} <span style="font-size:1rem; color:#94a3b8;">min</span></div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Diagnostic feedback
    if accuracy >= 88 and st.session_state.total_time_taken <= 22:
      st.success(
          "🔥 Benchmark Passed: $\\ge 88\\%$ accuracy under 22 mins. Ready for"
          " Pure Maths."
      )
    elif accuracy >= 80:
      st.warning(
          "⚡ Solid Speed: Focus on reducing negative marking errors to push"
          " past 88%."
      )
    else:
      st.error(
          "🚨 Leakage Detected: High unforced errors. Focus on step-by-step"
          " accuracy before shortcuts."
      )

    st.info(
        f"**Simplification Accuracy:** {simp_c}/{simp_tot} &nbsp;|&nbsp;"
        f" **Arithmetic Accuracy:** {arith_c}/{arith_tot}"
    )

    # Explanations
    st.write("---")
    with st.expander(
        "📖 View Step-by-Step Concepts & Exam Shortcuts", expanded=True
    ):
      for q in st.session_state.questions:
        qid = q["id"]
        ans = st.session_state.user_answers.get(qid)
        is_corr = ans == q["correct"]
        status_tag = (
            "✅ Correct"
            if is_corr
            else ("⚠️ Skipped" if ans is None else "❌ Wrong")
        )

        st.markdown(
            f"""
                <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:18px; margin-bottom:18px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <strong>Q{qid}. [{q['type']}] — {status_tag}</strong>
                        <span style="font-size:0.85rem; color:#64748b;">Your Choice: <b>{ans or 'None'}</b> | Correct: <b style="color:#059669;">{q['correct']}</b></span>
                    </div>
                    <p style="margin-bottom:12px; color:#334155;">{q['question']}</p>
                    <div class="concept-card"><b>📘 Conceptual Method:</b><br>{q['concept_solution']}</div>
                    <div class="shortcut-card"><b>⚡ Exam Shortcut / Trick:</b><br>{q['exam_shortcut']}</div>
                </div>
                """,
            unsafe_allow_html=True,
        )

else:
  st.markdown(
      """
    <div style="text-align:center; padding:60px 20px; background:#ffffff; border-radius:16px; border:1px solid #e2e8f0; max-width:700px; margin:40px auto;">
        <h3 style="color:#0f172a; margin-bottom:8px;">Ready for your drill?</h3>
        <p style="color:#64748b; margin-bottom:24px;">Click the button below to generate 25 authentic, shuffled TCS PYQ questions with live 25-minute exam timing.</p>
    </div>
    """,
      unsafe_allow_html=True,
  )
  c1, c2, c3 = st.columns([1.5, 2, 1.5])
  with c2:
    if st.button(
        "🚀 Start Practice Session", type="primary", use_container_width=True
    ):
      fetch_new_drill()
