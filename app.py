from datetime import datetime
import json
import os
import re
import time
from google import genai
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="SSC CGL Quant Exam Portal",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------- PERSISTENT STORAGE FILE -----------------
DATA_FILE = "cgl_user_progress.json"

DEFAULT_TRICKS = [
    {
        "topic": "Simplification — Continued Fractions",
        "title": "Bottom-Up Array Method (No Reciprocal Writing)",
        "rule": (
            "For a + 1/(b + 1/(c + 1/d)), start with the bottom fraction (1, d)"
            " and multiply-add upwards: New = (Integer × Current) + Previous."
        ),
        "example": (
            "3 + 1/(2 + 1/(1 + 1/4)) → Start (1, 4) → 1×4+1 = 5 → 2×5+4 = 14 →"
            " 3×14+5 = 47 → Answer: 47/14 in 4 seconds."
        ),
    },
    {
        "topic": "Simplification — Recurring Decimals",
        "title": "Common Base 99/990 Method",
        "rule": (
            "Instead of reducing each recurring decimal to lowest terms and"
            " finding LCM, convert all terms to base 99 or 990 and add/subtract"
            " numerators directly."
        ),
        "example": (
            "0.63(bar) + 0.37(bar) = 63/99 + 37/99 = 100/99 = 1.01(bar)."
        ),
    },
    {
        "topic": "Profit & Loss — Dishonest Dealer",
        "title": "Multiplying Factor Chain",
        "rule": (
            "Net SP/CP Ratio = (Claimed Price Factor) × (True Weight / False"
            " Weight)."
        ),
        "example": (
            "Sells at 8% loss but uses 750g for 1000g → (92/100) × (1000/750) ="
            " (23/25) × (4/3) = 92/75 → Profit = 17/75 = 22.67%."
        ),
    },
    {
        "topic": "Compound Interest — Multi-Cycle",
        "title": "3-Cycle Ratio Method (3 : 3 : 1)",
        "rule": (
            "For 3 compounding cycles at r%, calculate step1 = r% of P, step2 ="
            " r% of step1, step3 = r% of step2. Total CI = 3(step1) + 3(step2)"
            " + 1(step3)."
        ),
        "example": (
            "P = 31,250, r = 8% for 3 cycles → step1 = 2500, step2 = 200, step3"
            " = 16 → CI = 3(2500)+3(200)+16 = ₹8,116."
        ),
    },
    {
        "topic": "Time & Work — Leaving Mid-Way",
        "title": "Direct Work Fraction Subtraction",
        "rule": (
            "Skip LCM when workers leave early. Calculate fraction completed ="
            " (Days worked / Total alone days) and subtract from 1."
        ),
        "example": (
            "A (20d) works 5d = 5/20 = 1/4. B (30d) works 15d = 15/30 = 1/2."
            " Remaining for C = 1 - 3/4 = 1/4 in 10d → C alone = 40 days."
        ),
    },
]


def load_persistent_data():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r") as f:
        return json.load(f)
    except Exception:
      pass
  return {"history": [], "topic_stats": {}, "tricks_vault": DEFAULT_TRICKS}


def save_persistent_data(data):
  try:
    with open(DATA_FILE, "w") as f:
      json.dump(data, f)
  except Exception:
    pass


# ----------------- FORCE CLEAN STATE ON VERSION UPGRADE -----------------
if st.session_state.get("app_version") != "4.0":
  saved_data = load_persistent_data()
  st.session_state.clear()
  st.session_state.app_version = "4.0"
  st.session_state.exam_state = "idle"  # "idle", "active", "submitted"
  st.session_state.questions = []
  st.session_state.user_answers = {}
  st.session_state.start_time = None
  st.session_state.elapsed_seconds = 0
  st.session_state.show_explanations = False
  st.session_state.db = saved_data

# ----------------- PREMIUM EXAM HALL CSS -----------------
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0f172a;
    }
    .stApp {
        background-color: #f1f5f9;
    }

    /* Main Banner */
    .portal-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #ffffff;
        padding: 18px 26px;
        border-radius: 12px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
    }

    /* Question Card */
    .q-container {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .topic-pill {
        background: #e0f2fe;
        color: #0369a1;
        font-size: 0.73rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        display: inline-block;
        margin-bottom: 10px;
    }
    .topic-pill-arith {
        background: #fef3c7;
        color: #b45309;
        font-size: 0.73rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        display: inline-block;
        margin-bottom: 10px;
    }
    .q-body {
        font-size: 1.04rem;
        font-weight: 600;
        color: #1e293b;
        line-height: 1.55;
        margin-bottom: 8px;
    }

    /* Side-by-Side Solution Cards */
    .concept-box {
        background: #f8fafc;
        border: 1px solid #bfdbfe;
        border-left: 5px solid #2563eb;
        border-radius: 8px;
        padding: 16px;
        height: 100%;
        font-size: 0.92rem;
        line-height: 1.6;
        color: #1e293b;
    }
    .shortcut-box {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 5px solid #16a34a;
        border-radius: 8px;
        padding: 16px;
        height: 100%;
        font-size: 0.92rem;
        line-height: 1.6;
        color: #1e293b;
    }

    /* Score Card Grid */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 14px;
        margin-bottom: 20px;
    }
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    .kpi-label {
        font-size: 0.75rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
    }
    .kpi-val {
        font-size: 1.65rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 4px;
    }
</style>
""",
    unsafe_allow_html=True,
)

api_key = st.secrets.get("GEMINI_API_KEY", None)
if not api_key:
  with st.sidebar:
    api_key = st.text_input("Enter Gemini API Key", type="password")

# ----------------- QUESTION GENERATION PROMPT -----------------
EXAM_PROMPT = """
Generate an authentic SSC CGL Tier 1 / Tier 2 Quantitative Aptitude test of EXACTLY 25 multiple-choice questions (strictly TCS PYQ pattern).

RULES:
1. Exactly 9 questions MUST be Simplification (BODMAS with 'of', recurring decimals, continued fraction ladders, surds/indices, algebraic identities).
2. Exactly 16 questions MUST be Arithmetic Word Problems (Percentage, Profit & Loss, Dishonest Dealer, Simple & Compound Interest, Ratio & Proportion, Mixture & Alligation, Time & Work, Pipes & Cisterns, Time Speed Distance, Trains/Boats, Averages, Data Interpretation).
3. SHUFFLE the 9 Simplification and 16 Arithmetic questions randomly from Q1 to Q25. Pure Maths (Geometry, Trigonometry, Algebra, Mensuration) is strictly excluded.
4. CRITICAL: For EVERY question, write out the COMPLETE numerical step-by-step calculation in `concept_solution` and the COMPLETE numerical exam shortcut in `exam_shortcut`. NEVER use placeholder text.

Return ONLY valid JSON matching this exact structure:
{
  "questions": [
    {
      "id": 1,
      "category": "Simplification",
      "topic": "Simplification - BODMAS",
      "question": "Full question text with clear numbers",
      "options": ["A) 12", "B) 15", "C) 18", "D) 24"],
      "correct": "B",
      "concept_solution": "Step 1: Solve inner bracket (3 × 2) = 6. Step 2: 12 ÷ 6 = 2. Step 3: 15 of 3 = 45, and 90 ÷ 45 = 2. Final = 15.",
      "exam_shortcut": "Evaluate 'of' block mentally: 90/45 = 2. Bracket = 8. 2 × 8 - 1 = 15 in 5 seconds."
    }
  ],
  "new_tricks": [
    {
      "topic": "Simplification Trick",
      "title": "Name of calculation trick",
      "rule": "Clear rule explanation",
      "example": "Worked mini-example with numbers"
    },
    {
      "topic": "Arithmetic Shortcut",
      "title": "Name of quant shortcut",
      "rule": "Clear shortcut explanation",
      "example": "Worked mini-example with numbers"
    }
  ]
}
"""


def start_new_exam():
  if not api_key:
    st.error("Missing Gemini API Key! Please add it in Streamlit Secrets.")
    return

  with st.spinner(
      "⚡ Preparing your 25-Question SSC CGL Test Paper... Please wait ~15"
      " seconds."
  ):
    try:
      client = genai.Client(api_key=api_key)
      response = client.models.generate_content(
          model="gemini-3.8-flash",
          contents=EXAM_PROMPT,
          config={
              "response_mime_type": "application/json",
              "temperature": 0.35,
          },
      )
      raw_text = response.text.strip()
      raw_text = re.sub(r"^```json\s*", "", raw_text)
      raw_text = re.sub(r"\s*```$", "", raw_text)
      payload = json.loads(raw_text)

      q_list = (
          payload.get("questions", payload)
          if isinstance(payload, dict)
          else payload
      )
      new_tricks = (
          payload.get("new_tricks", []) if isinstance(payload, dict) else []
      )

      if len(q_list) > 0:
        st.session_state.questions = q_list
        st.session_state.user_answers = {q["id"]: None for q in q_list}
        st.session_state.start_time = time.time()
        st.session_state.exam_state = "active"
        st.session_state.show_explanations = False

        # Save new tricks to Shortcut Vault automatically
        if new_tricks:
          existing_titles = {
              t["title"] for t in st.session_state.db["tricks_vault"]
          }
          for tr in new_tricks:
            if tr.get("title") and tr["title"] not in existing_titles:
              st.session_state.db["tricks_vault"].insert(0, tr)
          save_persistent_data(st.session_state.db)

        st.rerun()
      else:
        st.error("Could not load questions. Please click Start Test again.")
    except Exception as e:
      st.error(f"Error generating test: {str(e)}")


def render_live_clock(start_timestamp):
  """Renders a real-time ticking JS clock that never resets on Streamlit clicks."""
  clock_html = f"""
    <div style="background:#0f172a; color:#38bdf8; font-family:'JetBrains Mono', monospace; padding:10px 18px; border-radius:10px; border:1px solid #334155; display:flex; align-items:center; justify-content:space-between;">
        <span style="font-size:0.8rem; color:#94a3b8; font-family:sans-serif; font-weight:700; text-transform:uppercase;">⏱️ Time Left</span>
        <span id="clock_display" style="font-size:1.35rem; font-weight:800;">25:00</span>
    </div>
    <script>
        const startTs = {start_timestamp} * 1000;
        const durationMs = 25 * 60 * 1000;
        function updateClock() {{
            const now = Date.now();
            const elapsed = now - startTs;
            const remaining = Math.max(0, durationMs - elapsed);
            const totalSec = Math.floor(remaining / 1000);
            const mins = String(Math.floor(totalSec / 60)).padStart(2, '0');
            const secs = String(totalSec % 60).padStart(2, '0');
            const el = document.getElementById('clock_display');
            if (el) {{
                el.innerText = mins + ":" + secs;
                if (totalSec < 300) {{
                    el.style.color = "#f87171";
                }}
            }}
        }}
        updateClock();
        setInterval(updateClock, 1000);
    </script>
    """
  components.html(clock_html, height=58)


# ----------------- TOP HEADER -----------------
st.markdown(
    """
<div class="portal-banner">
    <div>
        <div style="font-size:1.35rem; font-weight:800; letter-spacing:-0.3px;">🎯 SSC CGL Quant Exam Portal</div>
        <div style="font-size:0.82rem; color:#94a3b8;">Authentic TCS Pattern • 9 Simplification + 16 Arithmetic (Shuffled) • +2.0 / -0.5 Marking</div>
    </div>
    <div style="text-align:right; font-size:0.82rem; color:#38bdf8; font-weight:600;">
        Tier 1 & Tier 2 Speed Sprint
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ----------------- TOP TABS -----------------
tab_exam, tab_tracker, tab_tricks = st.tabs([
    "📝 Live Exam Portal",
    "📊 Progress & Weak Area Tracker",
    "⚡ Shortcut Tricks Vault",
])

# ==============================================================================
# TAB 1: LIVE EXAM PORTAL
# ==============================================================================
with tab_exam:
  # STATE 1: IDLE (Landing screen with ONLY "Start Test" button)
  if st.session_state.exam_state == "idle":
    st.markdown(
        """
        <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:14px; padding:48px 32px; max-width:680px; margin:30px auto; text-align:center; box-shadow:0 4px 12px rgba(0,0,0,0.03);">
            <h2 style="margin-top:0; font-weight:800; color:#0f172a;">SSC CGL Quantitative Aptitude Mock</h2>
            <p style="color:#475569; font-size:0.98rem; line-height:1.6; margin-bottom:24px;">
                <b>25 Questions</b> (9 Simplification + 16 Arithmetic interspersed) • <b>25 Minutes</b><br>
                Correct Answer: <span style="color:#16a34a; font-weight:700;">+2.0 Marks</span> &nbsp;|&nbsp; Wrong Answer: <span style="color:#dc2626; font-weight:700;">-0.5 Marks</span>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1.6, 1.8, 1.6])
    with c2:
      if st.button("🚀 Start Test", type="primary", use_container_width=True):
        start_new_exam()

  # STATE 2: ACTIVE EXAM
  elif st.session_state.exam_state == "active":
    questions = st.session_state.questions
    total_q = len(questions)
    attempted_now = sum(
        1 for v in st.session_state.user_answers.values() if v is not None
    )

    q_col, pal_col = st.columns([3.3, 1.2])

    with pal_col:
      # Real-time JS Countdown Clock
      render_live_clock(st.session_state.start_time)

      st.markdown(
          f"""
            <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:12px; padding:16px; margin-top:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <span style="font-weight:700; font-size:0.9rem;">Question Palette</span>
                    <span style="font-size:0.8rem; font-weight:700; color:#0284c7;">{attempted_now}/{total_q} Answered</span>
                </div>
            """,
          unsafe_allow_html=True,
      )

      p_cols = st.columns(5)
      for idx, q in enumerate(questions):
        qid = q["id"]
        ans_done = st.session_state.user_answers.get(qid) is not None
        with p_cols[idx % 5]:
          badge_bg = "#16a34a" if ans_done else "#e2e8f0"
          badge_fg = "#ffffff" if ans_done else "#475569"
          st.markdown(
              f"<div style='background:{badge_bg}; color:{badge_fg};"
              " text-align:center; padding:6px 0; border-radius:6px;"
              " font-size:0.78rem; font-weight:700;"
              f" margin-bottom:8px;'>{qid}</div>",
              unsafe_allow_html=True,
          )

      st.markdown(
          "<div style='font-size:0.75rem; color:#64748b; margin-top:6px;'>🟩"
          " Answered &nbsp;&nbsp; ⬜ Unattempted</div></div>",
          unsafe_allow_html=True,
      )

      st.write("")
      if st.button("🚀 Submit Test", type="primary", use_container_width=True):
        st.session_state.elapsed_seconds = int(
            time.time() - st.session_state.start_time
        )
        st.session_state.exam_state = "submitted"

        # Grade and save to persistent tracker immediately
        corr, wrong, unatt = 0, 0, 0
        topic_Stats = st.session_state.db.get("topic_stats", {})

        for q in questions:
          qid = q["id"]
          u_ans = st.session_state.user_answers.get(qid)
          t_name = q.get("topic", q.get("category", "Arithmetic"))
          if t_name not in topic_Stats:
            topic_Stats[t_name] = {"correct": 0, "wrong": 0, "unattempted": 0}

          if u_ans is None:
            unatt += 1
            topic_Stats[t_name]["unattempted"] += 1
          elif u_ans == q["correct"]:
            corr += 1
            topic_Stats[t_name]["correct"] += 1
          else:
            wrong += 1
            topic_Stats[t_name]["wrong"] += 1

        att = corr + wrong
        acc = (corr / att * 100) if att > 0 else 0.0
        score = (corr * 2.0) - (wrong * 0.5)
        mins, secs = divmod(st.session_state.elapsed_seconds, 60)

        st.session_state.db["history"].append({
            "test_no": len(st.session_state.db["history"]) + 1,
            "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "attempted": att,
            "correct": corr,
            "incorrect": wrong,
            "unattempted": unatt,
            "accuracy": round(acc, 1),
            "score": round(score, 2),
            "time_str": f"{mins}m {secs}s",
            "time_sec": st.session_state.elapsed_seconds,
        })
        st.session_state.db["topic_stats"] = topic_Stats
        save_persistent_data(st.session_state.db)
        st.rerun()

    with q_col:
      for q in questions:
        qid = q["id"]
        cat = q.get("category", "Arithmetic")
        topic_label = q.get("topic", cat)
        pill_cls = "topic-pill" if "Simp" in cat else "topic-pill-arith"

        st.markdown(
            f"""
                <div class="q-container">
                    <span class="{pill_cls}">{topic_label}</span>
                    <div class="q-body">Q{qid}. {q['question']}</div>
                </div>
                """,
            unsafe_allow_html=True,
        )

        opts = q["options"]
        current_val = st.session_state.user_answers.get(qid)
        selected = st.radio(
            label=f"select_{qid}",
            options=["A", "B", "C", "D"],
            format_func=lambda x, opts=opts: next(
                (o for o in opts if o.strip().startswith(x)), x
            ),
            index=None
            if current_val is None
            else ["A", "B", "C", "D"].index(current_val),
            key=f"q_radio_{qid}",
            label_visibility="collapsed",
        )
        if selected != current_val:
          st.session_state.user_answers[qid] = selected
          st.rerun()
        st.write("")

  # STATE 3: SUBMITTED (Scorecard + Toggle Explanations Side-by-Side)
  elif st.session_state.exam_state == "submitted":
    last_result = st.session_state.db["history"][-1]
    avg_pace = round(last_result["time_sec"] / 25, 1)

    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Net Score</div>
                <div class="kpi-val" style="color:#0284c7;">{last_result['score']} <span style="font-size:0.9rem; color:#94a3b8;">/ 50</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Attempted</div>
                <div class="kpi-val">{last_result['attempted']} <span style="font-size:0.9rem; color:#94a3b8;">/ 25</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Correct Answers</div>
                <div class="kpi-val" style="color:#16a34a;">{last_result['correct']}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Incorrect Answers</div>
                <div class="kpi-val" style="color:#dc2626;">{last_result['incorrect']}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Accuracy</div>
                <div class="kpi-val" style="color:{'#16a34a' if last_result['accuracy'] >= 85 else '#d97706'};">{last_result['accuracy']}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Time Taken</div>
                <div class="kpi-val">{last_result['time_str']} <div style="font-size:0.72rem; color:#64748b; font-weight:500;">({avg_pace}s / Q)</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    btn_c1, btn_c2, btn_c3 = st.columns([1.5, 1.5, 2])
    with btn_c1:
      if st.button(
          "📖 Show Explanations & Shortcuts",
          type="primary",
          use_container_width=True,
      ):
        st.session_state.show_explanations = (
            not st.session_state.show_explanations
        )
    with btn_c2:
      if st.button("🚀 Start Test (New Session)", use_container_width=True):
        start_new_exam()

    if st.session_state.show_explanations:
      st.write("---")
      st.subheader(
          "🔍 Detailed Conceptual Solutions & Side-by-Side Exam Shortcuts"
      )

      for q in st.session_state.questions:
        qid = q["id"]
        u_ans = st.session_state.user_answers.get(qid)
        c_ans = q["correct"]
        topic_lbl = q.get("topic", q.get("category", "Quant"))

        if u_ans is None:
          status_badge = "<span style='background:#f1f5f9; color:#475569; padding:4px 10px; border-radius:6px; font-weight:700; font-size:0.8rem;'>⚪ Unattempted</span>"
        elif u_ans == c_ans:
          status_badge = "<span style='background:#dcfce7; color:#15803d; padding:4px 10px; border-radius:6px; font-weight:700; font-size:0.8rem;'>✅ Correct (+2.0)</span>"
        else:
          status_badge = "<span style='background:#fee2e2; color:#b91c1c; padding:4px 10px; border-radius:6px; font-weight:700; font-size:0.8rem;'>❌ Incorrect (-0.5)</span>"

        # Resolve options text
        opts_html = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join([
            f"<b style='color:#16a34a;'>{o} ✓</b>"
            if o.strip().startswith(c_ans)
            else (
                f"<span style='color:#dc2626; text-decoration:line-through;'>{o}</span>"
                if (u_ans and o.strip().startswith(u_ans))
                else f"<span style='color:#64748b;'>{o}</span>"
            )
            for o in q["options"]
        ])

        st.markdown(
            f"""
                <div style="background:#ffffff; border:1px solid #cbd5e1; border-radius:12px; padding:20px; margin-top:16px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <div><span class="topic-pill">{topic_lbl}</span></div>
                        <div>{status_badge} &nbsp; <span style="font-size:0.85rem; color:#475569;">Your Answer: <b>{u_ans or 'Skipped'}</b> | Correct: <b style="color:#16a34a;">{c_ans}</b></span></div>
                    </div>
                    <div style="font-size:1.02rem; font-weight:600; color:#0f172a; margin-bottom:10px;">Q{qid}. {q['question']}</div>
                    <div style="font-size:0.9rem; margin-bottom:14px;">{opts_html}</div>
                </div>
                """,
            unsafe_allow_html=True,
        )

        # Side-by-Side Conceptual vs Shortcut
        sol_c1, sol_c2 = st.columns(2)
        concept_txt = (
            q.get("concept_solution")
            or q.get("concept")
            or "Solution steps not provided."
        )
        shortcut_txt = (
            q.get("exam_shortcut")
            or q.get("shortcut")
            or "Shortcut not provided."
        )

        with sol_c1:
          st.markdown(
              f"""
                    <div class="concept-box">
                        <div style="font-weight:800; color:#1d4ed8; margin-bottom:6px; font-size:0.85rem; text-transform:uppercase;">📘 Detailed Conceptual Method</div>
                        {concept_txt}
                    </div>
                    """,
              unsafe_allow_html=True,
          )
        with sol_c2:
          st.markdown(
              f"""
                    <div class="shortcut-box">
                        <div style="font-weight:800; color:#15803d; margin-bottom:6px; font-size:0.85rem; text-transform:uppercase;">⚡ Exam Shortcut / Topper Trick</div>
                        {shortcut_txt}
                    </div>
                    """,
              unsafe_allow_html=True,
          )

# ==============================================================================
# TAB 2: PROGRESS & WEAK AREA TRACKER
# ==============================================================================
with tab_tracker:
  history = st.session_state.db.get("history", [])
  topic_stats = st.session_state.db.get("topic_stats", {})

  if not history:
    st.info(
        "📊 No tests completed yet. Complete your first test in the **Live Exam"
        " Portal** tab to unlock full analytics and weak area identification!"
    )
  else:
    total_tests = len(history)
    avg_score = round(sum(h["score"] for h in history) / total_tests, 1)
    best_score = max(h["score"] for h in history)
    avg_acc = round(sum(h["accuracy"] for h in history) / total_tests, 1)

    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-label">Total Tests Taken</div><div class="kpi-val">{total_tests}</div></div>
            <div class="kpi-card"><div class="kpi-label">Average Score</div><div class="kpi-val" style="color:#0284c7;">{avg_score} / 50</div></div>
            <div class="kpi-card"><div class="kpi-label">Highest Score</div><div class="kpi-val" style="color:#16a34a;">{best_score} / 50</div></div>
            <div class="kpi-card"><div class="kpi-label">Overall Accuracy</div><div class="kpi-val">{avg_acc}%</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_w, col_s = st.columns(2)

    weak_list = []
    strong_list = []
    for topic, st_val in topic_stats.items():
      c = st_val["correct"]
      w = st_val["wrong"]
      u = st_val["unattempted"]
      tot = c + w + u
      att_t = c + w
      t_acc = round((c / att_t * 100), 1) if att_t > 0 else 0.0
      entry = (topic, c, w, u, t_acc, tot)
      if t_acc < 75.0 or w >= 2 or u >= 3:
        weak_list.append(entry)
      else:
        strong_list.append(entry)

    with col_w:
      st.markdown("### 🚨 Identified Weak Areas (Priority Revision)")
      if not weak_list:
        st.success(
            "No major weak areas detected! All attempted topics are above 75%"
            " accuracy."
        )
      else:
        for t, c, w, u, acc, tot in sorted(weak_list, key=lambda x: x[4]):
          st.markdown(
              f"""
                    <div style="background:#fff1f2; border:1px solid #fecdd3; border-left:5px solid #e11d48; padding:12px 16px; border-radius:8px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; font-weight:700; color:#9f1239;">
                            <span>{t}</span>
                            <span>Accuracy: {acc}%</span>
                        </div>
                        <div style="font-size:0.82rem; color:#881337; margin-top:4px;">
                            Correct: <b>{c}</b> | Wrong: <b>{w}</b> | Skipped: <b>{u}</b> (Total seen: {tot})
                        </div>
                    </div>
                    """,
              unsafe_allow_html=True,
          )

    with col_s:
      st.markdown("### ✅ Strong Areas (High Accuracy)")
      if not strong_list:
        st.caption(
            "Take more tests to build strong topic benchmarks (≥75% accuracy)."
        )
      else:
        for t, c, w, u, acc, tot in sorted(
            strong_list, key=lambda x: x[4], reverse=True
        ):
          st.markdown(
              f"""
                    <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-left:5px solid #16a34a; padding:12px 16px; border-radius:8px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; font-weight:700; color:#166534;">
                            <span>{t}</span>
                            <span>Accuracy: {acc}%</span>
                        </div>
                        <div style="font-size:0.82rem; color:#14532d; margin-top:4px;">
                            Correct: <b>{c}</b> | Wrong: <b>{w}</b> | Skipped: <b>{u}</b> (Total seen: {tot})
                        </div>
                    </div>
                    """,
              unsafe_allow_html=True,
          )

    st.write("---")
    st.markdown("### 📜 Test-by-Test Score Log")
    st.dataframe(
        [
            {
                "Test #": f"Test #{h['test_no']}",
                "Date & Time": h["date"],
                "Score (/50)": h["score"],
                "Accuracy (%)": f"{h['accuracy']}%",
                "Attempted": h["attempted"],
                "Correct": h["correct"],
                "Incorrect": h["incorrect"],
                "Unattempted": h["unattempted"],
                "Time Taken": h["time_str"],
            }
            for h in reversed(history)
        ],
        use_container_width=True,
        hide_index=True,
    )

# ==============================================================================
# TAB 3: SHORTCUT TRICKS VAULT
# ==============================================================================
with tab_tricks:
  st.markdown(
      "### ⚡ SSC CGL Topper Shortcut Tricks Vault\n"
      "Every time you start a new test, fresh Simplification & Arithmetic"
      " shortcuts are automatically added to the top of this vault."
  )

  tricks_list = st.session_state.db.get("tricks_vault", DEFAULT_TRICKS)
  for idx, tr in enumerate(tricks_list, 1):
    st.markdown(
        f"""
        <div style="background:#ffffff; border:1px solid #cbd5e1; border-left:5px solid #0284c7; border-radius:10px; padding:18px 22px; margin-bottom:14px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
            <div style="font-size:0.75rem; font-weight:800; color:#0284c7; text-transform:uppercase; margin-bottom:4px;">{tr.get('topic', 'Quant Trick')}</div>
            <div style="font-size:1.08rem; font-weight:800; color:#0f172a; margin-bottom:8px;">#{idx}. {tr.get('title', 'Exam Shortcut')}</div>
            <div style="font-size:0.93rem; color:#334155; margin-bottom:8px;"><b>⚡ The Rule:</b> {tr.get('rule', '')}</div>
            <div style="background:#f8fafc; border:1px dashed #cbd5e1; padding:10px 14px; border-radius:6px; font-size:0.88rem; color:#0f172a;">
                <b>📘 Worked Example:</b> {tr.get('example', '')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
