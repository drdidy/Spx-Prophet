"""
SPX PROPHET — Styles v9.0  LEGENDARY DARK
Cinematic dark command-center theme. Glowing accents, gradient cards,
pulsing animations. Three fonts: Orbitron, JetBrains Mono, Outfit.
"""

from config import COLORS

MAIN_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Outfit:wght@200;300;400;500;600;700;800&display=swap');

:root {{
    --bg-page: #020209;
    --bg-card: #0c0c1f;
    --bg-card-alt: #0a0a1a;
    --bg-card-end: #08081a;
    --sidebar-bg: #050510;
    --accent: #00d4ff;
    --accent-light: #33ddff;
    --accent2: #7B2CBF;
    --gold: #f0c040;
    --gold-light: #f5d060;
    --green: #00ff88;
    --green-dim: #00cc6a;
    --red: #ff0055;
    --red-dim: #cc0044;
    --orange: #ff9500;
    --cyan: #00d4ff;
    --text: #e8e8f0;
    --text2: #a0a0c0;
    --text3: #555577;
    --border: #1a1a35;
    --border-light: #14142a;
    --shadow: 0 2px 12px rgba(0,0,0,0.5), 0 8px 32px rgba(0,0,0,0.3);
    --shadow-lg: 0 4px 16px rgba(0,0,0,0.6), 0 16px 48px rgba(0,0,0,0.4);
    --shadow-glow-cyan: 0 0 25px rgba(0,212,255,0.15), 0 4px 16px rgba(0,0,0,0.4);
    --shadow-glow-green: 0 0 25px rgba(0,255,136,0.15), 0 4px 16px rgba(0,0,0,0.4);
    --shadow-glow-red: 0 0 25px rgba(255,0,85,0.15), 0 4px 16px rgba(0,0,0,0.4);
    --shadow-glow-gold: 0 0 25px rgba(240,192,64,0.15), 0 4px 16px rgba(0,0,0,0.4);
}}

/* ═══ GLOBAL ═══ */
.stApp {{
    background: var(--bg-page) !important;
    color: var(--text);
    font-family: 'Outfit', sans-serif;
}}

/* ═══ ANIMATED GRID BACKGROUND ═══ */
.grid-bg {{
    position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; pointer-events: none;
    background-image:
        linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
    background-size: 60px 60px;
    animation: grid-drift 20s linear infinite;
}}
@keyframes grid-drift {{
    0% {{ background-position: 0 0; }}
    100% {{ background-position: 60px 60px; }}
}}

/* ═══ HIDE CHROME ═══ */
.stApp > header {{ background: transparent !important; }}
#MainMenu, footer, .stDeployButton, [data-testid="stToolbar"] {{ display: none !important; }}
.block-container {{ padding-top: 1rem !important; padding-bottom: 2rem !important; max-width: 1500px !important; }}

/* ═══ SIDEBAR — Deep dark ═══ */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #050510 0%, #0a0a1e 50%, #050510 100%) !important;
    border-right: 1px solid rgba(0,212,255,0.08) !important;
    box-shadow: 4px 0 30px rgba(0,0,0,0.6);
}}
section[data-testid="stSidebar"] * {{ color: #a0a0c0 !important; }}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {{
    font-family: 'Orbitron', sans-serif !important;
    color: #00d4ff !important; font-size: 0.85rem !important;
    letter-spacing: 3px !important; text-transform: uppercase !important;
}}
section[data-testid="stSidebar"] .stMarkdown h5 {{
    font-family: 'Orbitron', sans-serif !important;
    color: #f0c040 !important; font-size: 0.7rem !important;
    letter-spacing: 2px !important; text-transform: uppercase !important;
}}
section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.04) !important; }}
section[data-testid="stSidebar"] label {{
    font-family: 'Outfit', sans-serif !important; font-size: 0.85rem !important;
    color: #a0a0c0 !important;
}}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] select,
section[data-testid="stSidebar"] textarea,
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="input"] > div,
section[data-testid="stSidebar"] [data-baseweb="base-input"],
section[data-testid="stSidebar"] [data-testid="stDateInput"] div[class*="st-"] {{
    background: rgba(255,255,255,0.04) !important;
    border-color: rgba(255,255,255,0.08) !important;
    color: #e8e8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 8px !important;
}}
section[data-testid="stSidebar"] [data-baseweb="select"] span,
section[data-testid="stSidebar"] [data-baseweb="select"] div,
section[data-testid="stSidebar"] [data-baseweb="input"] input,
section[data-testid="stSidebar"] [data-testid="stDateInput"] input {{
    color: #e8e8f0 !important; background: transparent !important;
}}
section[data-testid="stSidebar"] .stSelectbox svg {{ fill: #555577 !important; }}
section[data-testid="stSidebar"] [data-testid="stExpander"] details {{
    background: rgba(255,255,255,0.02) !important;
    border-color: rgba(255,255,255,0.05) !important;
    border-radius: 10px !important;
}}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary {{ color: #a0a0c0 !important; }}
section[data-testid="stSidebar"] .stButton > button {{
    background: linear-gradient(135deg, #00d4ff, #7B2CBF) !important;
    border: none !important; color: #fff !important; font-weight: 700 !important;
    font-family: 'Orbitron', sans-serif !important; letter-spacing: 1.5px !important;
    font-size: 0.7rem !important; text-transform: uppercase;
    box-shadow: 0 3px 20px rgba(0,212,255,0.3) !important;
}}
section[data-testid="stSidebar"] [data-testid="stCheckbox"] label span {{ color: #a0a0c0 !important; }}
section[data-testid="stSidebar"] [data-baseweb="popover"],
section[data-testid="stSidebar"] [data-baseweb="menu"],
section[data-testid="stSidebar"] ul[role="listbox"] {{
    background: #0c0c1f !important; border-color: #1a1a35 !important;
}}
section[data-testid="stSidebar"] li[role="option"] {{ color: #e8e8f0 !important; }}
section[data-testid="stSidebar"] li[role="option"]:hover {{ background: rgba(0,212,255,0.1) !important; }}
section[data-testid="stSidebar"] [data-testid="stSlider"] > div > div > div > div {{
    background: linear-gradient(90deg, #00d4ff, #7B2CBF) !important;
}}
section[data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {{
    background-color: #00d4ff !important;
}}

/* ═══ CARDS — Glass-morphism with gradient backgrounds ═══ */
.pc, .prophet-card {{
    background: linear-gradient(145deg, #0c0c1f 0%, #0a0a1a 50%, #08081a 100%);
    border: 1px solid #1a1a35; border-radius: 14px;
    padding: 1.3rem 1.5rem; margin-bottom: 0.6rem;
    position: relative; overflow: hidden;
    box-shadow: var(--shadow);
    transition: box-shadow 0.3s ease, transform 0.2s ease, border-color 0.3s ease;
}}
.pc:hover, .prophet-card:hover {{
    box-shadow: var(--shadow-lg);
    transform: translateY(-1px);
    border-color: rgba(0,212,255,0.15);
}}
.pc::before, .prophet-card::before {{
    content: ''; position: absolute; top: 0; left: 10%; right: 10%; height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent); opacity: 0.4;
    border-radius: 2px;
    filter: blur(0.5px);
}}
.pc-gold::before, .prophet-card-gold::before {{
    background: linear-gradient(90deg, transparent, var(--gold), transparent) !important;
    opacity: 0.6 !important;
    filter: blur(0.5px);
    box-shadow: 0 0 12px rgba(240,192,64,0.2);
}}
.pc-green::before, .prophet-card-bullish::before {{
    background: linear-gradient(90deg, transparent, var(--green), transparent) !important;
    opacity: 0.6 !important;
    filter: blur(0.5px);
    box-shadow: 0 0 12px rgba(0,255,136,0.2);
}}
.pc-red::before, .prophet-card-bearish::before {{
    background: linear-gradient(90deg, transparent, var(--red), transparent) !important;
    opacity: 0.6 !important;
    filter: blur(0.5px);
    box-shadow: 0 0 12px rgba(255,0,85,0.2);
}}

/* ═══ HERO ═══ */
.hero-bar {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.8rem 0 1.2rem; flex-wrap: wrap; gap: 1rem;
}}
.hero-title {{
    font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 2.4rem;
    background: linear-gradient(135deg, #00d4ff 0%, #7B2CBF 40%, #f0c040 100%);
    background-size: 200% 200%;
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    letter-spacing: 8px; line-height: 1;
    filter: drop-shadow(0 2px 12px rgba(0,212,255,0.25));
    animation: hero-gradient 6s ease-in-out infinite;
}}
@keyframes hero-gradient {{
    0%, 100% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
}}
.hero-sub {{
    font-family: 'Orbitron', sans-serif; font-size: 0.6rem;
    color: var(--gold); letter-spacing: 6px; text-transform: uppercase;
    opacity: 0.9; margin-top: 4px;
    text-shadow: 0 0 8px rgba(240,192,64,0.3);
}}
.ticker-strip {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
.ticker-item {{
    background: linear-gradient(145deg, #0c0c1f, #0a0a1a);
    border: 1px solid #1a1a35; border-radius: 12px;
    padding: 0.8rem 1.3rem; text-align: center; min-width: 130px;
    box-shadow: var(--shadow);
    transition: transform 0.2s ease, box-shadow 0.3s ease, border-color 0.3s ease;
}}
.ticker-item:hover {{
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
    border-color: rgba(0,212,255,0.15);
}}

/* ═══ TYPOGRAPHY — Bigger sizes ═══ */
.lbl, .prophet-label {{
    font-family: 'Orbitron', sans-serif; font-size: 0.7rem; letter-spacing: 2.5px;
    color: var(--text3); text-transform: uppercase; display: block; margin-bottom: 5px;
}}
.big {{
    font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 1.8rem;
    color: var(--text); line-height: 1.2;
}}
.big-hero {{
    font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 1.8rem;
    color: var(--accent); line-height: 1;
    text-shadow: 0 0 20px rgba(0,212,255,0.3), 0 2px 12px rgba(0,212,255,0.15);
}}
.med {{
    font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 1.15rem;
    color: var(--text);
}}
.sm, .prophet-data {{
    font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--text);
}}
.dim, .prophet-data-muted {{
    font-family: 'Outfit', sans-serif; font-size: 0.78rem; color: var(--text3);
}}
.prophet-price-sm {{
    font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 1.6rem;
    color: var(--text); line-height: 1.3;
}}
.body {{
    font-family: 'Outfit', sans-serif; font-size: 0.92rem; color: var(--text2); line-height: 1.5;
}}
.icon {{ font-size: 2rem; margin-right: 0.5rem; vertical-align: middle; }}

/* ═══ SIGNAL BADGES ═══ */
.sig {{
    display: inline-flex; align-items: center; justify-content: center;
    font-family: 'Orbitron', sans-serif; font-weight: 800; font-size: 1.5rem;
    padding: 1.2rem 3.5rem; border-radius: 14px; letter-spacing: 6px;
}}
.sig-long {{
    background: linear-gradient(135deg, rgba(0,255,136,0.12), rgba(0,255,136,0.03));
    border: 2px solid var(--green); color: var(--green);
    animation: pulse-green 2.5s ease-in-out infinite;
}}
.sig-short {{
    background: linear-gradient(135deg, rgba(255,0,85,0.12), rgba(255,0,85,0.03));
    border: 2px solid var(--red); color: var(--red);
    animation: pulse-red 2.5s ease-in-out infinite;
}}
.sig-scan {{
    background: linear-gradient(145deg, #0c0c1f, #0a0a1a);
    border: 1px solid var(--border);
    color: var(--text3); font-size: 1.3rem; letter-spacing: 4px;
    animation: scan-fade 2s ease-in-out infinite;
}}
@keyframes pulse-green {{
    0%, 100% {{ box-shadow: 0 0 10px rgba(0,255,136,0.1), 0 4px 20px rgba(0,0,0,0.3); }}
    50% {{ box-shadow: 0 0 35px rgba(0,255,136,0.3), 0 4px 30px rgba(0,255,136,0.1); }}
}}
@keyframes pulse-red {{
    0%, 100% {{ box-shadow: 0 0 10px rgba(255,0,85,0.1), 0 4px 20px rgba(0,0,0,0.3); }}
    50% {{ box-shadow: 0 0 35px rgba(255,0,85,0.3), 0 4px 30px rgba(255,0,85,0.1); }}
}}
@keyframes scan-fade {{
    0%, 100% {{ opacity: 0.4; }}
    50% {{ opacity: 1; }}
}}

/* ═══ QUALITY RING ═══ */
.qring {{
    width: 140px; height: 140px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    margin: 0.6rem auto;
    font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 1.6rem;
}}
.qring-a {{
    background: conic-gradient(var(--green) var(--pct), #1a1a35 0%);
    color: var(--green);
    box-shadow: 0 0 25px rgba(0,255,136,0.15);
}}
.qring-b {{
    background: conic-gradient(var(--accent) var(--pct), #1a1a35 0%);
    color: var(--accent);
    box-shadow: 0 0 25px rgba(0,212,255,0.15);
}}
.qring-c {{
    background: conic-gradient(var(--orange) var(--pct), #1a1a35 0%);
    color: var(--orange);
    box-shadow: 0 0 25px rgba(255,149,0,0.15);
}}
.qring-d, .qring-f {{
    background: conic-gradient(var(--red) var(--pct), #1a1a35 0%);
    color: var(--red);
    box-shadow: 0 0 25px rgba(255,0,85,0.15);
}}
.qring-inner {{
    width: 112px; height: 112px; border-radius: 50%;
    background: linear-gradient(145deg, #0c0c1f, #08081a);
    display: flex; align-items: center; justify-content: center;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.4);
}}

/* ═══ MICRO COMPONENTS ═══ */
.dot, .line-dot {{
    display: inline-block; width: 10px; height: 10px; border-radius: 50%;
    margin-right: 6px; vertical-align: middle;
    box-shadow: 0 0 6px currentColor;
}}
.badge {{
    display: inline-block; font-family: 'Orbitron', sans-serif; font-size: 0.55rem;
    letter-spacing: 2px; padding: 4px 12px; border-radius: 6px; font-weight: 700;
    text-transform: uppercase;
}}
.str-p, .strength-premium {{
    color: #f0c040; background: rgba(240,192,64,0.12);
    border: 1px solid rgba(240,192,64,0.4);
}}
.str-h, .strength-high {{
    color: #00d4ff; background: rgba(0,212,255,0.1);
    border: 1px solid rgba(0,212,255,0.3);
}}
.str-s, .strength-standard {{
    color: var(--text3); background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
}}
.vix-badge {{
    display: inline-block; font-family: 'Orbitron', sans-serif; font-size: 0.55rem;
    font-weight: 700; letter-spacing: 1.5px; padding: 4px 10px; border-radius: 6px;
    text-transform: uppercase;
}}
.cz {{
    background: linear-gradient(135deg, rgba(240,192,64,0.06), rgba(123,44,191,0.04));
    border: 1px solid rgba(240,192,64,0.2); border-radius: 10px;
    padding: 0.8rem 1rem; margin: 0.4rem 0;
    animation: cz-glow 4s ease-in-out infinite;
}}
@keyframes cz-glow {{
    0%, 100% {{ box-shadow: 0 0 5px rgba(240,192,64,0.03); }}
    50% {{ box-shadow: 0 0 25px rgba(240,192,64,0.12); }}
}}
.macro-warn {{
    background: linear-gradient(135deg, rgba(255,0,85,0.06), rgba(255,149,0,0.03));
    border: 1px solid rgba(255,0,85,0.3); border-radius: 14px;
    padding: 1rem 1.4rem; margin-bottom: 0.8rem;
    animation: macro-pulse 3s ease-in-out infinite;
}}
@keyframes macro-pulse {{
    0%, 100% {{ border-color: rgba(255,0,85,0.15); box-shadow: 0 0 0 rgba(255,0,85,0); }}
    50% {{ border-color: rgba(255,0,85,0.5); box-shadow: 0 0 20px rgba(255,0,85,0.08); }}
}}
.srow, .stat-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.5rem 0.4rem; border-bottom: 1px solid var(--border-light);
    transition: background 0.15s;
}}
.srow:hover, .stat-row:hover {{
    background: rgba(0,212,255,0.04); border-radius: 6px;
}}

/* ═══ STREAMLIT OVERRIDES ═══ */
.stMarkdown, .stText, p, span, label, .stSelectbox label, .stNumberInput label,
.stCheckbox label, .stRadio label, .stSlider label {{
    color: var(--text2) !important; font-family: 'Outfit', sans-serif !important;
}}
[data-testid="stMetricValue"] {{
    font-family: 'JetBrains Mono', monospace !important;
    color: var(--text) !important;
}}

/* Tabs — Dark rounded container with glowing active */
.stTabs [data-baseweb="tab-list"] {{
    gap: 2px; background: #08081a; border-radius: 12px; padding: 5px;
    border: 1px solid #1a1a35;
    box-shadow: 0 2px 12px rgba(0,0,0,0.5);
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Orbitron', sans-serif !important; font-size: 0.55rem !important;
    letter-spacing: 1.5px !important; color: #555577 !important;
    border-radius: 8px; padding: 0.6rem 1rem; transition: all 0.25s ease;
    text-transform: uppercase;
}}
.stTabs [data-baseweb="tab"]:hover {{ color: #a0a0c0 !important; background: rgba(255,255,255,0.03); }}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, #00d4ff, #0088cc) !important;
    color: #ffffff !important; font-weight: 700 !important;
    box-shadow: 0 3px 20px rgba(0,212,255,0.35);
}}
.stTabs [data-baseweb="tab-highlight"] {{ display: none !important; }}
.stTabs [data-baseweb="tab-border"] {{ display: none !important; }}

/* Buttons */
.stButton > button {{
    font-family: 'Orbitron', sans-serif !important; letter-spacing: 1.5px !important;
    font-size: 0.65rem !important; border-radius: 10px !important; text-transform: uppercase;
    transition: all 0.25s ease !important;
    background: linear-gradient(145deg, #0c0c1f, #0a0a1a) !important;
    border: 1px solid var(--border) !important; color: var(--text2) !important;
    box-shadow: var(--shadow) !important;
}}
.stButton > button[kind="primary"], .stButton > button[data-testid="stFormSubmitButton"] {{
    background: linear-gradient(135deg, #00d4ff, #7B2CBF) !important;
    border: none !important; color: #fff !important; font-weight: 700 !important;
    box-shadow: 0 4px 20px rgba(0,212,255,0.25) !important;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: var(--shadow-lg) !important;
    border-color: rgba(0,212,255,0.2) !important;
}}

/* Inputs — main content area */
input, select, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div {{
    background: rgba(255,255,255,0.03) !important;
    border-color: #1a1a35 !important;
    color: var(--text) !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 10px !important;
}}
/* Number input — force all inner wrappers dark */
[data-testid="stNumberInput"] div[class*="st-"],
[data-testid="stNumberInput"] [data-baseweb="input"],
[data-testid="stNumberInput"] [data-baseweb="input"] > div,
[data-testid="stNumberInput"] [data-baseweb="base-input"],
[data-testid="stNumberInput"] input {{
    background: #08081a !important;
    border-color: #1a1a35 !important;
    color: #e8e8f0 !important;
}}
/* Number input +/- stepper buttons */
[data-testid="stNumberInput"] button {{
    background: #0c0c1f !important;
    border-color: #1a1a35 !important;
    color: #a0a0c0 !important;
}}
[data-testid="stNumberInput"] button:hover {{
    background: #1a1a35 !important;
    color: #00d4ff !important;
}}
[data-testid="stNumberInput"] button svg {{
    fill: #a0a0c0 !important;
}}
[data-testid="stNumberInput"] button:hover svg {{
    fill: #00d4ff !important;
}}
/* Select / Date input inner wrappers */
[data-testid="stSelectbox"] div[class*="st-"],
[data-testid="stDateInput"] div[class*="st-"],
[data-baseweb="select"] div[class*="st-"] {{
    background: #08081a !important;
    border-color: #1a1a35 !important;
    color: #e8e8f0 !important;
}}
[data-baseweb="popover"], [data-baseweb="menu"], ul[role="listbox"] {{
    background: #0c0c1f !important; border-color: #1a1a35 !important;
}}
li[role="option"] {{ color: #e8e8f0 !important; }}
li[role="option"]:hover {{ background: rgba(0,212,255,0.08) !important; }}
li[role="option"][aria-selected="true"] {{ background: rgba(0,212,255,0.12) !important; }}

/* Sliders */
[data-testid="stSlider"] [role="slider"] {{
    background-color: var(--accent) !important;
    box-shadow: 0 0 10px rgba(0,212,255,0.3) !important;
}}
[data-testid="stSlider"] > div > div > div > div {{
    background: linear-gradient(90deg, var(--accent), var(--accent2)) !important;
}}
[data-testid="stSlider"] > div > div > div {{ background: #1a1a35 !important; }}

/* Plotly */
.stPlotlyChart {{
    border: 1px solid var(--border); border-radius: 14px; overflow: hidden;
    box-shadow: var(--shadow);
}}

/* DataFrames — dark theme */
[data-testid="stDataFrame"] {{ border-radius: 12px !important; overflow: hidden !important; }}
[data-testid="stDataFrame"] > div {{ border: 1px solid var(--border) !important; border-radius: 12px !important; }}
[data-testid="stDataFrame"] table {{ background: #0c0c1f !important; color: #e8e8f0 !important; }}
[data-testid="stDataFrame"] th {{ background: #08081a !important; color: #a0a0c0 !important; }}
[data-testid="stDataFrame"] td {{ color: #e8e8f0 !important; border-color: #1a1a35 !important; }}

/* Expanders */
[data-testid="stExpander"] details {{
    border: 1px solid var(--border) !important; border-radius: 12px !important;
    background: linear-gradient(145deg, #0c0c1f, #08081a) !important;
}}
[data-testid="stExpander"] summary {{
    font-family: 'Orbitron', sans-serif !important; font-size: 0.65rem !important;
    letter-spacing: 2px !important; color: var(--text3) !important;
}}
[data-testid="stExpander"] summary:hover {{ color: var(--accent) !important; }}

/* Alerts */
.stAlert {{
    background: linear-gradient(145deg, #0c0c1f, #08081a) !important;
    border-radius: 12px !important;
    border-left-color: var(--accent) !important;
    color: var(--text2) !important;
}}

/* Checkboxes */
[data-testid="stCheckbox"] label span[data-testid="stCheckbox-label"] {{
    font-family: 'Outfit', sans-serif !important; color: var(--text2) !important;
}}
[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] {{ color: var(--text2) !important; }}

/* Number inputs, text inputs, date inputs */
[data-testid="stNumberInput"] input {{ color: #e8e8f0 !important; }}
[data-testid="stTextInput"] input {{ color: #e8e8f0 !important; }}

/* Horizontal rule */
hr {{ border-color: #1a1a35 !important; opacity: 0.5 !important; }}

/* Download button */
.stDownloadButton > button {{
    font-family: 'Orbitron', sans-serif !important; font-size: 0.6rem !important;
    letter-spacing: 1.5px !important; text-transform: uppercase;
}}

/* Spinner */
.stSpinner > div {{ border-top-color: #00d4ff !important; }}

/* Success/Info/Warning/Error boxes */
.stSuccess {{ background: rgba(0,255,136,0.06) !important; color: #00ff88 !important; }}
div[data-testid="stNotification"] {{ background: #0c0c1f !important; border-color: #1a1a35 !important; }}

/* Scrollbar — Dark */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: #050510; }}
::-webkit-scrollbar-thumb {{ background: #1a1a35; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: #00d4ff; }}

/* ═══ RESPONSIVE ═══ */
@media (max-width: 768px) {{
    .hero-title {{ font-size: 1.8rem !important; letter-spacing: 4px; }}
    .big-hero {{ font-size: 2.2rem !important; }}
    .ticker-strip {{ gap: 0.3rem; }}
    .ticker-item {{ min-width: 100px; padding: 0.5rem 0.8rem; }}
    .stTabs [data-baseweb="tab"] {{ font-size: 0.42rem !important; padding: 0.4rem 0.5rem; }}
    .sig {{ font-size: 1.5rem; padding: 0.8rem 2rem; }}
    .qring {{ width: 110px; height: 110px; }}
    .qring-inner {{ width: 88px; height: 88px; }}
}}
</style>
"""
