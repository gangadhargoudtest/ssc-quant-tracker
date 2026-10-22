import json
import re
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

# ----------------- HIGH-PERFORMANCE MODERN STYLING -----------------
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
    
    /* Top Bar */
    .top-header {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px 22px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Question Box */
    .q-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 22px;
        margin-bottom: 18px;
        box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04);
        transition: border-color 0.15s ease;
    }
    .q-card:hover {
        border-color: #cbd5e1;
    }

    /* Badges */
    .badge-simp {
        background-color: #e0f2fe;
        color: #0369a1;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        letter-spacing: 0.5px;
        display: inline-block;
        margin-bottom: 10px;
    }
    .badge-arith {
        background-color: #fef3c7;
        color: #b45309;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        letter-spacing: 0.5px;
        display: inline-block;
        margin-bottom: 10px;
    }

    .q-title {
        font-size: 1.05rem;
        line-height: 1.6;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 12px;
    }

    /* Solution Box Styles */
    .sol-concept {
        background: #f1f5f9;
        border-left: 4px solid #2563eb;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        font-size: 0.92rem;
        line-height: 1.6;
        margin-bottom: 10px;
    }
    .sol-shortcut {
        background: #ecfdf5;
        border-left: 4px solid #059669;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        font-size: 0.92rem;
        line-height: 1.6;
    }

    /* Timer Badge */
    .timer-box {
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

    /* Palette Box */
    .palette-container {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        position: sticky;
        top: 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
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
    api_key = st.text_input("Gemini API Key", type="password")

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
    st.caption("Benchmark: $\\ge 88\\%$ & $\\le 22$ mins")

# ----------------- ULTRA-FAST LEAN PROMPT -----------------
# Optimized to complete API response in under 5 seconds
FAST_PROMPT = """
Create an SSC CGL Tier 1/2 Quant drill of exactly 25 MCQs (TCS pattern).
Strict Rules:
- Exactly 9 Simplification (BODMAS nested brackets, recurring decimals, fraction ladders, mixed fractions, surds/indices).
- Exactly 16 Arithmetic Word Problems (Percentage, Profit & Loss, CI/SI, Ratio, Mixture, Time & Work, TSD, Averages, DI).
- Shuffle the 9 Simplification and 16 Arithmetic questions across all 25 numbers. Pure maths is strictly excluded.
- Ensure concise solutions to keep response rapid.
- Return ONLY valid JSON array with 25 objects:
[
  {
    "id": 1,
    "type": "Simplification",
    "question": "Question text here",
    "options": ["A) opt1", "B) opt2", "C) opt3", "D) opt4"],
    "correct": "A",
    "concept": "1-2 sentence core mathematical steps",
    "shortcut": "5-10 second topper shortcut or digital sum/ratio trick"
  }
]
"""


def fetch_new_drill():
  if not api_key:
    st.error("Please enter a valid Gemini API Key.")
    return

  with st.spinner("⚡ Fetching 25 authentic TCS PYQs (typically 3–5s)..."):
    try:
      client = genai.Client(api_key=api_key)
      response = client.models.generate_content(
          model="gemini-3.8-flash",
          contents=FAST_PROMPT,
          config={
              "response_mime_type": "application/json",
              "temperature": 0.3,
          },
      )
      text_resp = response.text.strip()
      # Clean potential markdown wrapping if present
      text_resp = re.sub(r"^```json\s*", "", text_resp)
      text_resp = re.sub(r"\s*```$", "", text_resp)

      questions_data = json.loads(text_resp)

      if len(questions_data) >= 20:  # Valid set received
        st.session_state.questions = questions_data
        st.session_state.user_answers = {q["id"]: None for q in questions_data}
        st.session_state.test_submitted = False
        st.session_state.start_time = time.time()
        st.session_state.session_counter += 1
        st.rerun()
      else:
        st.warning("Received partial question list. Retrying...")
    except Exception as e:
      st.error(f"Error fetching questions: {str(e)}")


# ----------------- TOP CONTROLS -----------------
c_head, c_btn = st.columns([4, 1.3])
with c_head:
  st.markdown(
      "<h2 style='margin:0; font-weight:800; color:#0f172a;'>🎯 SSC CGL Quant"
      " Speed Sprint</h2><p style='margin:0; color:#64748b; font-size:0.9rem;'"
      ">Authentic TCS Pattern • 9 Simplification + 16 Arithmetic • 25Q / 50"
      " Marks • -0.5 Negative Marking</p>",
      unsafe_allow_html=True,
  )
with c_btn:
  st.write("")
  if st.button(
      "🔄 Next Session / Refresh", use_container_width=True, type="primary"
  ):
    fetch_new_drill()

st.write("")

# ----------------- ACTIVE TEST VIEW -----------------
if st.session_state.questions:
  elapsed_sec = int(time.time() - st.session_state.start_time)
  rem_sec = max(0, (25 * 60) - elapsed_sec)
  rem_m, rem_s = divmod(rem_sec, 60)
  total_q = len(st.session_state.questions)
  answered_count = sum(
      1 for a in st.session_state.user_answers.values() if a is not None
  )

  # Live Exam Status Header
  col_t, col_p, col_meta = st.columns([1.5, 3, 1.5])
  with col_t:
    color_style = (
        "color:#ef4444; background:#fef2f2; border-color:#fecaca;"
        if rem_m < 5
        else "color:#0284c7; background:#f0f9ff; border-color:#bae6fd;"
    )
    st.markdown(
        f"<div class='timer-box' style='{color_style}'>⏱️"
        f" {rem_m:02d}:{rem_s:02d}</div>",
        unsafe_allow_html=True,
    )
  with col_p:
    st.progress(
        answered_count / total_q,
        text=f"Progress: {answered_count} of {total_q} Attempted",
    )
  with col_meta:
    st.markdown(
        f"<div style='text-align:right; font-weight:700; color:#475569;"
        f" padding-top:6px;'>Session"
        f" #{st.session_state.session_counter}</div>",
        unsafe_allow_html=True,
    )

  st.write("")

  # ----------------- TEST TAKING VIEW -----------------
  if not st.session_state.test_submitted:
    q_col, p_col = st.columns([3.4, 1.2])

    with q_col:
      for q in st.session_state.questions:
        qid = q["id"]
        badge_cls = (
            "badge-simp" if q["type"] == "Simplification" else "badge-arith"
        )

        st.markdown(
            f"""
                <div class="q-card">
                    <span class="{badge_cls}">{q['type']}</span>
                    <div class="q-title">Q{qid}. {q['question']}</div>
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
            "🚀 Submit Test & View Scorecard",
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
          "<div class='palette-container'>"
          "<h4 style='margin-top:0; font-size:1rem; color:#1e293b;'>Question"
          " Palette</h4>",
          unsafe_allow_html=True,
      )
      palette_grid = st.columns(5)
      for i in range(1, total_q + 1):
        is_ans = st.session_state.user_answers.get(i) is not None
        col_idx = (i - 1) % 5
        with palette_grid[col_idx]:
          st.caption(f"**{i}**")
          icon_symbol = "🟢" if is_ans else "⚪"
          st.markdown(f"<span>{icon_symbol}</span>", unsafe_allow_html=True)
      st.markdown(
          "<p style='margin-top:14px; font-size:0.75rem; color:#64748b;'>🟢"
          " Attempted &nbsp;&nbsp; ⚪ Unattempted</p></div>",
          unsafe_allow_html=True,
      )

  # ----------------- RESULTS & ANALYSIS -----------------
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

    # Metric Cards
    st.markdown(
        f"""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:22px; margin-bottom:24px;">
            <h3 style="margin-top:0; color:#0f172a; font-weight:800;">📋 Performance Audit</h3>
            <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:16px;">
                <div><div style="font-size:0.75rem; color:#64748b; font-weight:700;">RAW SCORE</div><div style="font-size:1.8rem; font-weight:800; color:#0284c7;">{raw_score:.1f} <span style="font-size:0.95rem; color:#94a3b8;">/ 50</span></div></div>
                <div><div style="font-size:0.75rem; color:#64748b; font-weight:700;">ACCURACY</div><div style="font-size:1.8rem; font-weight:800; color:{'#059669' if accuracy >= 88 else '#d97706'};">{accuracy:.1f}%</div></div>
                <div><div style="font-size:0.75rem; color:#64748b; font-weight:700;">CORRECT / WRONG</div><div style="font-size:1.8rem; font-weight:800; color:#334155;">{correct} <span style="color:#ef4444;">/ {incorrect}</span></div></div>
                <div><div style="font-size:0.75rem; color:#64748b; font-weight:700;">TIME TAKEN</div><div style="font-size:1.8rem; font-weight:800; color:#334155;">{st.session_state.total_time_taken} <span style="font-size:0.95rem; color:#94a3b8;">min</span></div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if accuracy >= 88 and st.session_state.total_time_taken <= 22:
      st.success(
          "🏆 Benchmark Cleared: $\\ge 88\\%$ accuracy under 22 mins! You are"
          " qualified for Pure Maths inclusion."
      )
    elif accuracy >= 80:
      st.warning(
          "⚠️ Good Pace: Focus on cutting negative marking leakage ($-0.5$ per"
          " wrong answer)."
      )
    else:
      st.error(
          "🚨 Leakage Alert: High error rate. Prioritize standard steps first,"
          " then apply shortcuts."
      )

    st.info(
        f"**Simplification:** {simp_c}/{simp_tot} correct &nbsp;|&nbsp;"
        f" **Arithmetic:** {arith_c}/{arith_tot} correct"
    )

    st.write("---")
    with st.expander(
        "📖 Show Conceptual Solutions & Exam Shortcuts", expanded=True
    ):
      for q in st.session_state.questions:
        qid = q["id"]
        ans = st.session_state.user_answers.get(qid)
        is_corr = ans == q["correct"]
        status_tag = (
            "✅ Correct"
            if is_corr
            else ("⚠️ Skipped" if ans is None else "❌ Incorrect")
        )

        st.markdown(
            f"""
                <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:18px; margin-bottom:16px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <strong>Q{qid}. [{q['type']}] — {status_tag}</strong>
                        <span style="font-size:0.85rem; color:#64748b;">Your Choice: <b>{ans or 'None'}</b> | Correct: <b style="color:#059669;">{q['correct']}</b></span>
                    </div>
                    <p style="margin-bottom:12px; color:#334155; font-weight:500;">{q['question']}</p>
                    <div class="sol-concept"><b>📘 Conceptual Method:</b><br>{q.get('concept', 'Step-by-step logic')}</div>
                    <div class="sol-shortcut"><b>⚡ Exam Shortcut / Trick:</b><br>{q.get('shortcut', 'Direct calculation shortcut')}</div>
                </div>
                """,
            unsafe_allow_html=True,
        )

else:
  st.markdown(
      """
    <div style="text-align:center; padding:60px 20px; background:#ffffff; border-radius:16px; border:1px solid #e2e8f0; max-width:650px; margin:40px auto; box-shadow:0 1px 4px rgba(0,0,0,0.03);">
        <h3 style="color:#0f172a; margin-bottom:8px; font-weight:800;">Ready for Today's Drill?</h3>
        <p style="color:#64748b; margin-bottom:24px; font-size:0.95rem;">25 Questions • 25 Minutes • Authentic TCS Question Distribution.</p>
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
