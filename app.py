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
        "topic": "Simplification — Continued Fraction Ladder",
        "title": "Bottom-Up Chain Multiplication (No Reciprocal Writing)",
        "rule": (
            "Never solve a continued fraction ladder by flipping reciprocals"
            " step-by-step. Start with the bottom-most fraction"
            " $\\dfrac{n}{d}$ as $(n, d)$, then move up through each integer"
            " $k$using:$\\text{Next} = (k \\times \\text{Current}) +"
            " \\text{Previous}$."
        ),
        "exam_question": (
            "If $x = 3 + \\cfrac{1}{2 + \\cfrac{1}{1 + \\dfrac{1}{4}}}$, then"
            " what is the value of $x$?\n\n**Options:** A) $\\dfrac{47}{14}$"
            " &nbsp;&nbsp; B) $\\dfrac{43}{14}$ &nbsp;&nbsp; C)"
            " $\\dfrac{47}{19}$ &nbsp;&nbsp; D) $\\dfrac{39}{14}$"
        ),
        "shortcut_solution": (
            "**Step 1:** Write the bottom fraction $\\dfrac{1}{4}$ as starting"
            " pair: $(1, 4)$.\n\n**Step 2:** Multiply-add moving upwards"
            " through the integers $1, 2, 3$:\n* At $1 \\rightarrow (1 \\times" " 4) + 1 = 5$\n* At $2 \\rightarrow (2 \\times 5) + 4 = 14$\n* At"
            " $3 \\rightarrow (3 \\times 14) + 5 = 47$\n\n**Step 3:** Final"
            " fraction $= \\dfrac{\\text{Last}}{\\text{Second Last}} ="
            " \\mathbf{\\dfrac{47}{14}}$ (**Option A** in 5 seconds)."
        ),
    },
    {
        "topic": "Simplification — Recurring Decimals",
        "title": "Common Base 990 Numerator Method",
        "rule": (
            "Instead of reducing each recurring decimal to lowest terms and"
            " taking LCM, write all terms directly over a common denominator of"
            " $990$ (or $99$) using $\\dfrac{\\text{All Digits} -" " \\text{Non-Repeating Digits}}{990}$ and add/subtract numerators"
            " in one step."
        ),
        "exam_question": (
            "What is the simplest fractional value of $0.\\overline{63} +"
            " 0.4\\overline{27} - 0.3\\overline{8}$?\n\n**Options:** A)"
            " $\\dfrac{331}{495}$ &nbsp;&nbsp; B) $\\dfrac{334}{495}$"
            " &nbsp;&nbsp; C) $\\dfrac{337}{495}$ &nbsp;&nbsp; D)"
            " $\\dfrac{329}{495}$"
        ),
        "shortcut_solution": (
            "**Step 1:** Express each term over base $990$:\n* $0.\\overline{63}"
            " = \\dfrac{63}{99} = \\dfrac{630}{990}$\n* $0.4\\overline{27} ="
            " \\dfrac{427 - 4}{990} = \\dfrac{423}{990}$\n* $0.3\\overline{8} ="
            " \\dfrac{38 - 3}{90} = \\dfrac{35}{90} ="
            " \\dfrac{385}{990}$\n\n**Step 2:** Combine numerators: $\\dfrac{630"
            " + 423 - 385}{990} = \\dfrac{668}{990} ="
            " \\mathbf{\\dfrac{334}{495}}$ (**Option B**)."
        ),
    },
    {
        "topic": "Profit & Loss — Dishonest Dealer",
        "title": "Single Multiplying Factor Chain",
        "rule": (
            "Set up a direct ratio $\\dfrac{\\text{SP}}{\\text{CP}} ="
            " \\left(\\text{Claimed Price Factor}\\right) \\times"
            " \\left(\\dfrac{\\text{True Weight Billed}}{\\text{Actual Weight"
            " Given}}\\right)$ and cancel common factors crosswise."
        ),
        "exam_question": (
            "A dishonest dealer claims to sell pulses at an $8\\%$ loss on cost"
            " price, but uses a false weight of $750\\text{ g}$ instead of"
            " $1\\text{ kg}$. What is his actual profit percentage?\n\n"
            "**Options:** A) $20\\%$ &nbsp;&nbsp; B) $22\\dfrac{2}{3}\\%$"
            " &nbsp;&nbsp; C) $24\\%$ &nbsp;&nbsp; D) $18\\dfrac{1}{3}\\%$"
        ),
        "shortcut_solution": (
            "**Step 1:** Price factor ($8\\%$loss)$= \\dfrac{92}{100} ="
            " \\dfrac{23}{25}$.\n\n**Step 2:** Weight factor ($1000\\text{ g}$"
            " billed for $750\\text{ g}$)$= \\dfrac{1000}{750} ="
            " \\dfrac{4}{3}$.\n\n**Step 3:** Multiply factors:"
            " $\\dfrac{\\text{SP}}{\\text{CP}} = \\dfrac{23}{25} \\times"
            " \\dfrac{4}{3} = \\dfrac{92}{75} \\implies \\text{Profit} ="
            " \\dfrac{17}{75} \\times 100 = \\mathbf{22\\dfrac{2}{3}\\%}$"
            " (**Option B**)."
        ),
    },
    {
        "topic": "Compound Interest — Multi-Cycle (8-Monthly / Half-Yearly)",
        "title": "3-Cycle Ratio Method (3 : 3 : 1)",
        "rule": (
            "For 3 compounding cycles at rate $r\\%$ per cycle, avoid cubing"
            " $(1 + r/100)^3$. Compute $S_1 = r\\%$ of $P$, $S_2 = r\\%$ of"
            " $S_1$,$S_3 = r\\%$of$S_2$. Total $\\text{CI} = 3S_1 + 3S_2 +"
            " 1S_3$."
        ),
        "exam_question": (
            "What is the compound interest on a sum of ₹$31,250$ for $2\\text{" " years}$ at $12\\%$ p.a., if the interest is compounded"
            " $8\\text{-monthly}$?\n\n**Options:** A) ₹$8,016$ &nbsp;&nbsp; B)"
            " ₹$8,116$ &nbsp;&nbsp; C) ₹$8,216$ &nbsp;&nbsp; D) ₹$7,916$"
        ),
        "shortcut_solution": (
            "**Step 1:** $2\\text{ years} = 24\\text{ months} \\implies n ="
            " \\dfrac{24}{8} = 3\\text{ cycles}$. Cycle rate $r = 12\\% \\times"
            " \\dfrac{8}{12} = 8\\%$.\n\n**Step 2:** Take $8\\%$ successively"
            " 3 times:\n* $S_1 = 8\\%$ of $31,250 = 2500$\n* $S_2 = 8\\%$ of"
            " $2500 = 200$\n* $S_3 = 8\\%$ of $200 = 16$\n\n**Step 3:**"
            " $\\text{CI} = 3(2500) + 3(200) + 1(16) = 7500 + 600 + 16 ="
            " \\mathbf{₹8,116}$ (**Option B**)."
        ),
    },
    {
        "topic": "Time & Work — Leaving Mid-Way",
        "title": "Direct Work-Fraction Subtraction (Zero LCM)",
        "rule": (
            "When workers work for a known number of days and leave, skip"
            " finding the LCM of total work. Subtract each worker's fraction"
            " $\\left(\\dfrac{\\text{Days Worked}}{\\text{Total Alone" " Days}}\\right)$ from $1$."
        ),
        "exam_question": (
            "$A$ can complete a work in $20\\text{ days}$ and $B$ in $30\\text{" " days}$. They work together for $5\\text{ days}$, then $A$ leaves."
            " $C$ joins $B$ and they finish the remaining work in $10\\text{" " days}$. In how many days can $C$ alone finish the entire"
            " work?\n\n**Options:** A) $30\\text{ days}$ &nbsp;&nbsp; B)"
            " $36\\text{ days}$ &nbsp;&nbsp; C) $40\\text{ days}$ &nbsp;&nbsp;"
            " D) $45\\text{ days}$"
        ),
        "shortcut_solution": (
            "**Step 1:** $A$ works $5\\text{ days} = \\dfrac{5}{20} ="
            " \\dfrac{1}{4}$ work.\n\n**Step 2:** $B$ works $5 + 10 = 15\\text{" " days} = \\dfrac{15}{30} = \\dfrac{1}{2}$ work.\n\n**Step 3:**"
            " Remaining work for $C = 1 - \\left(\\dfrac{1}{4} +" " \\dfrac{1}{2}\\right) = \\dfrac{1}{4}$ work in $10\\text{ days}$"
            " $\\implies$ Whole work $= 10 \\times 4 = \\mathbf{40\\text{" " days}}$ (**Option C**)."
        ),
    },
]


def load_persistent_data():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r") as f:
        data = json.load(f)
      vault = data.get("tricks_vault", [])
      upgraded_vault = [
          t for t in vault if "exam_question" in t and "shortcut_solution" in t
      ]
      existing_titles = {t["title"] for t in upgraded_vault}
      for dt in DEFAULT_TRICKS:
        if dt["title"] not in existing_titles:
          upgraded_vault.append(dt)
      data["tricks_vault"] = upgraded_vault
      return data
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
if st.session_state.get("app_version") != "6.1":
  saved_data = load_persistent_data()
  st.session_state.clear()
  st.session_state.app_version = "6.1"
  st.session_state.exam_state = "idle"
  st.session_state.questions = []
  st.session_state.user_answers = {}
  st.session_state.start_time = None
  st.session_state.elapsed_seconds = 0
  st.session_state.show_explanations = False
  st.session_state.db = saved_data

# ----------------- PREMIUM EXAM HALL & KATEX MATH CSS -----------------
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

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 18px 22px !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
        margin-bottom: 12px !important;
    }

    .katex {
        font-size: 1.14em !important;
        color: #0f172a !important;
    }
    .katex-display {
        margin: 0.6em 0 !important;
        overflow-x: auto;
        overflow-y: hidden;
    }
    .katex .overline .overline-line,
    .katex .mfrac .frac-line {
        border-bottom-width: 1.9px !important;
        border-color: #0f172a !important;
    }

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
        margin-bottom: 6px;
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
        margin-bottom: 6px;
    }

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


# ----------------- MATH & JSON SANITIZATION HELPERS -----------------
def sanitize_latex_json(raw_text: str) -> str:
  """Ensures LaTeX commands inside JSON strings have properly escaped backslashes."""
  raw_text = re.sub(r"^```json\s*", "", raw_text.strip())
  raw_text = re.sub(r"\s*```$", "", raw_text.strip())

  latex_cmds = (
      r"(?:d?frac|cfrac|tfrac|overline|underline|sqrt|root|times|div|cdot|pm|mp"
      r"|le|ge|neq|ne|approx|equiv|left|right|big|Big|bigg|Bigg|text|textbf"
      r"|mathbf|mathrm|bar|alpha|beta|gamma|theta|pi|sum|prod|implies)"
  )
  raw_text = re.sub(r"(?<!\\)\\(" + latex_cmds + r")", r"\\\\\1", raw_text) raw_text = re.sub( r'(?<!\\)\\(?![/\"\\bfnrt]|u[0-9a-fA-F]{4})', r"\\\\", raw_text
  )
  return raw_text


def format_ssc_math(text: str) -> str:
  """Upgrades any stray Unicode bars or cramped fractions into crisp SSC CGL KaTeX notation."""
  if not text:
    return ""
  text = re.sub(r"(\d)[\u0304\u0305]+", r"$\\overline{\1}$", text)
  text = re.sub(r"\\frac(?=\{)", r"\\dfrac", text)
  return text


# ----------------- QUESTION GENERATION PROMPT -----------------
EXAM_PROMPT = r"""
Generate an authentic SSC CGL Tier 1 / Tier 2 Quantitative Aptitude test of EXACTLY 25 multiple-choice questions (strictly TCS PYQ pattern).

RULES:
1. Exactly 9 questions MUST be Simplification (BODMAS with 'of' and vinculum bar, recurring decimals, continued fraction ladders, surds/indices, algebraic identities).
2. Exactly 16 questions MUST be Arithmetic Word Problems (Percentage, Profit & Loss, Dishonest Dealer, Simple & Compound Interest, Ratio & Proportion, Mixture & Alligation, Time & Work, Pipes & Cisterns, Time Speed Distance, Trains/Boats, Averages, Data Interpretation).
3. SHUFFLE the 9 Simplification and 16 Arithmetic questions randomly from Q1 to Q25. Pure Maths (Geometry, Trigonometry, Algebra, Mensuration) is strictly excluded.

CRITICAL SSC CGL MATH DISPLAY RULES (MANDATORY):
- NEVER use Unicode combining bars like `0.47̄` or flat slash ladders like `1 + 1 / (2 + 1 / 3)`.
- ALWAYS format mathematical expressions in LaTeX enclosed in `$ ... $` (or `$$ ... $$` for tall simplification expressions):
  * Recurring decimals MUST use `\overline{...}` inside `$ ... $`, e.g., `$0.4\overline{7} + 0.5\overline{83} - 0.2\overline{3}$`.
  * Continued fraction ladders MUST use vertically stacked `\cfrac` inside `$$ ... $$`, e.g.:
    `$$1 + \cfrac{1}{2 + \cfrac{1}{1 + \cfrac{1}{3 + \dfrac{1}{2}}}}$$`
  * Mixed fractions and BODMAS fractions MUST use `\dfrac{a}{b}` and `\overline{...}` for vinculum.
  * Options (`options` array) MUST also use `$ ... $` for fractions, roots, or recurring decimals.
  * Double-escape backslashes `\\` inside JSON strings.
4. For EVERY question, write out the COMPLETE numerical step-by-step calculation in `concept_solution` and the COMPLETE numerical exam shortcut in `exam_shortcut`.
5. In `new_tricks`, include 2 high-yield SSC CGL shortcuts (1 Simplification, 1 Arithmetic). Each MUST include a full `exam_question` (with 4 options) and a step-by-step `shortcut_solution` showing how to solve that exact question in under 10 seconds.

Return ONLY valid JSON matching this exact structure:
{
  "questions": [
    {
      "id": 1,
      "category": "Simplification",
      "topic": "Simplification - Recurring Decimals",
      "question": "What is the value of $0.4\\overline{7} + 0.5\\overline{83} - 0.2\\overline{3}$?",
      "options": ["A) $0.8\\overline{27}$", "B) $0.8\\overline{24}$", "C) $0.8\\overline{25}$", "D) $0.8\\overline{31}$"],
      "correct": "B",
      "concept_solution": "Step 1: Convert to fractions: $0.4\\overline{7} = \\dfrac{47-4}{90} = \\dfrac{43}{90}$. Step 2: $0.5\\overline{83} = \\dfrac{583-5}{990} = \\dfrac{578}{990}$. Step 3: $0.2\\overline{3} = \\dfrac{23-2}{90} = \\dfrac{21}{90}$. Combining over LCD $990$: $\\dfrac{473 + 578 - 231}{990} = \\dfrac{820}{990} = 0.8\\overline{24}$.",
      "exam_shortcut": "Write all over base $990$: $\\dfrac{473 + 578 - 231}{990} = \\dfrac{820}{990}$. Add non-repeating digit $8$ to numerator: $820 + 8 = 828 \\rightarrow 0.8\\overline{24}$ in 6 seconds."
    }
  ],
  "new_tricks": [
    {
      "topic": "Simplification — Algebraic Identities",
      "title": "Sum/Difference of Cubes Instant Cancellation",
      "rule": "Whenever an expression has the form $\\dfrac{a^3 + b^3}{a^2 - ab + b^2}$, ignore the decimals and directly evaluate $(a + b)$. For $\\dfrac{a^3 - b^3}{a^2 + ab + b^2}$, directly evaluate $(a - b)$.",
      "exam_question": "What is the value of $\\dfrac{(0.76)^3 + (0.24)^3}{(0.76)^2 - 0.76 \\times 0.24 + (0.24)^2}$?\n\n**Options:** A) $0.52$   B) $1.00$   C) $0.1824$   D) $2.00$",
      "shortcut_solution": "**Step 1:** Spot the $\\dfrac{a^3 + b^3}{a^2 - ab + b^2}$ pattern with $a = 0.76$ and $b = 0.24$.\n\n**Step 2:** Result $= a + b = 0.76 + 0.24 = \\mathbf{1.00}$ (**Option B** in 2 seconds)."
    }
  ]
}
"""


def start_new_exam():
  if not api_key:
    st.error("Missing Gemini API Key! Please add it in Streamlit Secrets.")
    return

  with st.spinner(
      "⚡ Generating authentic SSC CGL Test Paper with stacked math notation"
      " (~15 seconds)..."
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
      clean_json = sanitize_latex_json(response.text)
      payload = json.loads(clean_json)

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
  # STATE 1: IDLE
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

        with st.container(border=True):
          st.markdown(
              f'<span class="{pill_cls}">{topic_label}</span>',
              unsafe_allow_html=True,
          )
          st.markdown(f"**Q{qid}.** {format_ssc_math(q['question'])}")

          opts = [format_ssc_math(o) for o in q["options"]]
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

  # STATE 3: SUBMITTED
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
      if st.button("🚀 Start Test", use_container_width=True):
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
          status_badge = "⚪ **Unattempted**"
        elif u_ans == c_ans:
          status_badge = "✅ **Correct (+2.0)**"
        else:
          status_badge = "❌ **Incorrect (-0.5)**"

        with st.container(border=True):
          top_c1, top_c2 = st.columns([2, 2])
          with top_c1:
            st.markdown(
                f'<span class="topic-pill">{topic_lbl}</span>',
                unsafe_allow_html=True,
            )
          with top_c2:
            st.markdown(
                f"<div style='text-align:right; font-size:0.9rem;'>{status_badge}"
                f" &nbsp;|&nbsp; Your Answer: `{u_ans or 'Skipped'}` &nbsp;|&nbsp;"
                f" Correct: **`{c_ans}`**</div>",
                unsafe_allow_html=True,
            )

          st.markdown(f"**Q{qid}.** {format_ssc_math(q['question'])}")

          opts_formatted = " &nbsp;&nbsp;•&nbsp;&nbsp; ".join(
              [format_ssc_math(o) for o in q["options"]]
          )
          st.markdown(f"**Options:** {opts_formatted}")

          sol_c1, sol_c2 = st.columns(2)
          concept_txt = format_ssc_math(
              q.get("concept_solution")
              or q.get("concept")
              or "Solution steps not provided."
          )
          shortcut_txt = format_ssc_math(
              q.get("exam_shortcut")
              or q.get("shortcut")
              or "Shortcut not provided."
          )

          with sol_c1:
            st.info(f"**📘 Detailed Conceptual Method**\n\n{concept_txt}")
          with sol_c2:
            st.success(f"**⚡ Exam Shortcut / Topper Trick**\n\n{shortcut_txt}")

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
      "Each shortcut includes the **core pattern rule**, an **authentic SSC"
      " CGL exam question**, and the **step-by-step shortcut method** to solve"
      " it in under 10 seconds. New tricks are automatically added every time"
      " you start a test."
  )

  tricks_list = st.session_state.db.get("tricks_vault", DEFAULT_TRICKS)
  for idx, tr in enumerate(tricks_list, 1):
    topic_str = tr.get("topic", "Quant Trick")
    pill_style = (
        "topic-pill" if "Simp" in topic_str else "topic-pill-arith"
    )
    exam_q = tr.get("exam_question") or tr.get("example", "")
    short_sol = tr.get("shortcut_solution") or tr.get("rule", "")

    with st.container(border=True):
      st.markdown(
          f'<span class="{pill_style}">{topic_str}</span>',
          unsafe_allow_html=True,
      )
      st.markdown(f"#### #{idx}. {tr.get('title', 'Exam Shortcut')}")
      st.markdown(
          f"**💡 The Shortcut Rule:** {format_ssc_math(tr.get('rule', ''))}"
      )

      q_col_v, s_col_v = st.columns(2)
      with q_col_v:
        st.info(
            "**📝 Authentic SSC CGL Exam Question**\n\n"
            f"{format_ssc_math(exam_q)}"
        )
      with s_col_v:
        st.success(
            "**⚡ Step-by-Step Shortcut Method**\n\n"
            f"{format_ssc_math(short_sol)}"
        )
