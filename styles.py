"""
SPX PROPHET — Styles v3.0
Premium dark trading terminal. Refined, cinematic, unforgettable.
Bloomberg Terminal × Blade Runner × Swiss design precision.
"""

from config import COLORS

MAIN_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Outfit:wght@200;300;400;500;600;700;800&display=swap');

:root {{
    --bg-void: #030308;
    --bg-primary: {COLORS["bg_primary"]};
    --bg-card: {COLORS["bg_card"]};
    --bg-card-alt: {COLORS["bg_card_alt"]};
    --accent-cyan: {COLORS["accent_cyan"]};
    --accent-purple: {COLORS["accent_purple"]};
    --accent-gold: {COLORS["accent_gold"]};
    --bullish: {COLORS["bullish"]};
    --bearish: {COLORS["bearish"]};
    --warning: {COLORS["warning"]};
    --text-primary: {COLORS["text_primary"]};
    --text-secondary: #c8c8e0;
    --text-muted: {COLORS["text_muted"]};
    --text-dim: {COLORS["text_dim"]};
    --border: {COLORS["border"]};
    --border-subtle: #12122a;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --shadow-card: 0 4px 24px rgba(0,0,0,0.4), 0 1px 4px rgba(0,0,0,0.3);
    --shadow-glow-cyan: 0 0 30px rgba(0,212,255,0.08), 0 0 60px rgba(0,212,255,0.04);
    --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    --transition-smooth: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}

/* ── Global ──────────────────────────────────────────────── */
.stApp {{
    background: var(--bg-void);
    font-family: 'Outfit', -apple-system, sans-serif;
    color: var(--text-primary);
    -webkit-font-smoothing: antialiased;
}}
.stApp > header {{ background: transparent !important; }}
.block-container {{ padding-top: 1.2rem !important; max-width: 1440px; }}
#MainMenu, footer, .stDeployButton {{ display: none !important; }}

/* ── Animated Grid + Top Glow ────────────────────────────── */
.grid-bg {{
    position: fixed; inset: 0;
    background:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0,212,255,0.06) 0%, transparent 60%),
        linear-gradient(rgba(0,212,255,0.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,0.018) 1px, transparent 1px);
    background-size: 100% 100%, 48px 48px, 48px 48px;
    pointer-events: none; z-index: -1;
    animation: grid-drift 60s linear infinite;
}}
@keyframes grid-drift {{
    0% {{ background-position: 0 0, 0 0, 0 0; }}
    100% {{ background-position: 0 0, 48px 48px, 48px 48px; }}
}}

/* Noise overlay */
.stApp::after {{
    content: ''; position: fixed; inset: 0; opacity: 0.022;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    pointer-events: none; z-index: 9999; mix-blend-mode: overlay;
}}

/* ── Sidebar ─────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #05051a 0%, #08081e 50%, #0a0a20 100%);
    border-right: 1px solid var(--border-subtle);
}}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {{
    font-family: 'Orbitron', sans-serif; color: var(--accent-cyan);
    font-size: 0.7rem; letter-spacing: 3px; text-transform: uppercase; opacity: 0.9;
}}
section[data-testid="stSidebar"] .stMarkdown h5 {{
    font-family: 'Orbitron', sans-serif; color: var(--text-muted);
    font-size: 0.6rem; letter-spacing: 2px; text-transform: uppercase;
}}
section[data-testid="stSidebar"] hr {{ border-color: var(--border-subtle); opacity: 0.4; }}

/* ── Cards ───────────────────────────────────────────────── */
.prophet-card {{
    background: linear-gradient(145deg, rgba(14,14,24,0.95) 0%, rgba(17,17,34,0.9) 100%);
    border: 1px solid var(--border); border-radius: var(--radius-lg);
    padding: 1.25rem 1.5rem; margin-bottom: 0.6rem;
    backdrop-filter: blur(16px) saturate(1.2);
    position: relative; overflow: hidden;
    box-shadow: var(--shadow-card);
    transition: border-color var(--transition-smooth), box-shadow var(--transition-smooth);
}}
.prophet-card:hover {{
    border-color: rgba(0,212,255,0.15);
    box-shadow: var(--shadow-card), var(--shadow-glow-cyan);
}}
.prophet-card::before {{
    content: ''; position: absolute; top: 0; left: 10%; right: 10%; height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent); opacity: 0.5;
}}
.prophet-card-gold::before {{ background: linear-gradient(90deg, transparent, var(--accent-gold), transparent) !important; opacity: 0.7 !important; }}
.prophet-card-bearish::before {{ background: linear-gradient(90deg, transparent, var(--bearish), transparent) !important; }}
.prophet-card-bullish::before {{ background: linear-gradient(90deg, transparent, var(--bullish), transparent) !important; }}

/* ── Typography ──────────────────────────────────────────── */
.prophet-title {{
    font-family: 'Orbitron', sans-serif; font-weight: 900;
    font-size: clamp(1.8rem, 4vw, 3rem);
    background: linear-gradient(135deg, var(--accent-cyan) 0%, #8b5cf6 40%, var(--accent-gold) 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    letter-spacing: 0.4em; line-height: 1.1; margin: 0;
    filter: drop-shadow(0 0 30px rgba(0,212,255,0.12));
}}
.prophet-subtitle {{
    font-family: 'Orbitron', sans-serif; font-weight: 400; font-size: 0.55rem;
    color: var(--accent-gold); letter-spacing: 0.6em; text-transform: uppercase; margin-top: 0.3rem; opacity: 0.8;
}}
.prophet-label {{
    font-family: 'Orbitron', sans-serif; font-size: 0.55rem; letter-spacing: 0.2em;
    color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.4rem; display: block;
}}
.prophet-price {{
    font-family: 'JetBrains Mono', monospace; font-weight: 700;
    font-size: clamp(1.5rem, 3vw, 2.2rem); color: var(--text-primary); line-height: 1.2;
}}
.prophet-price-glow {{ text-shadow: 0 0 20px rgba(0,212,255,0.25), 0 0 40px rgba(0,212,255,0.1); }}
.prophet-price-sm {{
    font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 1.2rem; color: var(--text-primary);
}}
.prophet-data {{ font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; color: var(--text-primary); }}
.prophet-data-muted {{ font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-muted); }}

/* ── Signal Badges ───────────────────────────────────────── */
.signal-long {{
    display: inline-flex; align-items: center; gap: 0.5rem;
    background: linear-gradient(135deg, rgba(0,255,136,0.12), rgba(0,255,136,0.03));
    border: 1px solid rgba(0,255,136,0.4); color: var(--bullish);
    font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 1.3rem;
    padding: 0.6rem 1.8rem; border-radius: var(--radius-md); letter-spacing: 0.25em;
    text-shadow: 0 0 20px rgba(0,255,136,0.35);
    animation: breathe-green 3s ease-in-out infinite;
}}
.signal-short {{
    display: inline-flex; align-items: center; gap: 0.5rem;
    background: linear-gradient(135deg, rgba(255,0,102,0.12), rgba(255,0,102,0.03));
    border: 1px solid rgba(255,0,102,0.4); color: var(--bearish);
    font-family: 'Orbitron', sans-serif; font-weight: 700; font-size: 1.3rem;
    padding: 0.6rem 1.8rem; border-radius: var(--radius-md); letter-spacing: 0.25em;
    text-shadow: 0 0 20px rgba(255,0,102,0.35);
    animation: breathe-red 3s ease-in-out infinite;
}}
.signal-neutral {{
    display: inline-flex; align-items: center; gap: 0.5rem;
    background: linear-gradient(135deg, rgba(106,106,138,0.1), rgba(106,106,138,0.03));
    border: 1px solid rgba(106,106,138,0.3); color: var(--text-muted);
    font-family: 'Orbitron', sans-serif; font-weight: 600; font-size: 1rem;
    padding: 0.6rem 1.8rem; border-radius: var(--radius-md); letter-spacing: 0.2em;
    animation: scanning-pulse 2s ease-in-out infinite;
}}
@keyframes breathe-green {{
    0%, 100% {{ box-shadow: 0 0 20px rgba(0,255,136,0.06); }}
    50% {{ box-shadow: 0 0 40px rgba(0,255,136,0.15); }}
}}
@keyframes breathe-red {{
    0%, 100% {{ box-shadow: 0 0 20px rgba(255,0,102,0.06); }}
    50% {{ box-shadow: 0 0 40px rgba(255,0,102,0.15); }}
}}
@keyframes scanning-pulse {{ 0%, 100% {{ opacity: 0.7; }} 50% {{ opacity: 1; }} }}

/* ── Quality Score Ring ──────────────────────────────────── */
.quality-score {{
    width: 110px; height: 110px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Orbitron', sans-serif; font-weight: 800; font-size: 1.5rem;
    margin: 0 auto; box-shadow: 0 0 40px rgba(0,0,0,0.3);
}}
.quality-a {{ background: conic-gradient(var(--bullish) var(--pct), rgba(26,26,46,0.5) 0%); color: var(--bullish); text-shadow: 0 0 20px rgba(0,255,136,0.4); }}
.quality-b {{ background: conic-gradient(var(--accent-cyan) var(--pct), rgba(26,26,46,0.5) 0%); color: var(--accent-cyan); text-shadow: 0 0 20px rgba(0,212,255,0.4); }}
.quality-c {{ background: conic-gradient(var(--warning) var(--pct), rgba(26,26,46,0.5) 0%); color: var(--warning); text-shadow: 0 0 20px rgba(255,165,0,0.4); }}
.quality-d, .quality-f {{ background: conic-gradient(var(--bearish) var(--pct), rgba(26,26,46,0.5) 0%); color: var(--bearish); text-shadow: 0 0 20px rgba(255,0,102,0.4); }}
.quality-inner {{
    width: 88px; height: 88px; border-radius: 50%;
    background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-void) 100%);
    display: flex; align-items: center; justify-content: center;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.4);
}}

/* ── Micro Components ────────────────────────────────────── */
.line-dot {{
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-right: 6px; vertical-align: middle; position: relative;
}}
.line-dot::after {{
    content: ''; position: absolute; inset: -3px; border-radius: 50%;
    background: inherit; opacity: 0.3; filter: blur(3px);
}}
.vix-badge {{
    display: inline-block; font-family: 'Orbitron', sans-serif;
    font-size: 0.5rem; letter-spacing: 0.15em; padding: 0.2rem 0.6rem;
    border-radius: var(--radius-sm); font-weight: 600; text-transform: uppercase;
}}
.strength-premium {{
    background: linear-gradient(135deg, rgba(240,192,64,0.15), rgba(240,192,64,0.03));
    border: 1px solid rgba(240,192,64,0.5); color: var(--accent-gold);
    font-family: 'Orbitron', sans-serif; font-size: 0.5rem; padding: 0.2rem 0.7rem;
    border-radius: var(--radius-sm); letter-spacing: 0.15em; display: inline-block;
    text-shadow: 0 0 8px rgba(240,192,64,0.3);
}}
.strength-high {{
    background: linear-gradient(135deg, rgba(0,212,255,0.12), rgba(0,212,255,0.03));
    border: 1px solid rgba(0,212,255,0.4); color: var(--accent-cyan);
    font-family: 'Orbitron', sans-serif; font-size: 0.5rem; padding: 0.2rem 0.7rem;
    border-radius: var(--radius-sm); letter-spacing: 0.15em; display: inline-block;
}}
.strength-standard {{
    background: rgba(106,106,138,0.06); border: 1px solid rgba(68,68,102,0.3);
    color: var(--text-dim); font-family: 'Orbitron', sans-serif; font-size: 0.5rem;
    padding: 0.2rem 0.7rem; border-radius: var(--radius-sm); letter-spacing: 0.15em; display: inline-block;
}}

/* ── Confluence ──────────────────────────────────────────── */
.confluence-zone {{
    background: linear-gradient(135deg, rgba(240,192,64,0.06), rgba(123,44,191,0.06));
    border: 1px solid rgba(240,192,64,0.2); border-radius: var(--radius-md);
    padding: 0.75rem 1rem; margin: 0.4rem 0;
    animation: conf-pulse 4s ease-in-out infinite;
}}
@keyframes conf-pulse {{
    0%, 100% {{ box-shadow: 0 0 8px rgba(240,192,64,0.05); }}
    50% {{ box-shadow: 0 0 24px rgba(240,192,64,0.12); }}
}}

/* ── Macro Banner ────────────────────────────────────────── */
.macro-banner {{
    background: linear-gradient(135deg, rgba(255,0,102,0.08), rgba(255,165,0,0.04));
    border: 1px solid rgba(255,0,102,0.3); border-radius: var(--radius-lg);
    padding: 1rem 1.5rem; margin-bottom: 1rem;
    animation: macro-flash 4s ease-in-out infinite;
}}
@keyframes macro-flash {{
    0%, 100% {{ border-color: rgba(255,0,102,0.3); }}
    50% {{ border-color: rgba(255,0,102,0.6); }}
}}

/* ── Stat Row ────────────────────────────────────────────── */
.stat-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.5rem 0; border-bottom: 1px solid var(--border-subtle);
    transition: background var(--transition-fast);
}}
.stat-row:hover {{ background: rgba(0,212,255,0.02); }}
.stat-row:last-child {{ border-bottom: none; }}

/* ═══════════════════════════════════════════════════════════
   STREAMLIT WIDGET OVERRIDES
   ═══════════════════════════════════════════════════════════ */
.stMetric {{ background: transparent !important; }}
div[data-testid="stMetricValue"] {{ font-family: 'JetBrains Mono', monospace !important; }}

.stTabs [data-baseweb="tab-list"] {{
    gap: 2px; background: rgba(14,14,24,0.8); border-radius: var(--radius-md);
    padding: 3px; border: 1px solid var(--border-subtle);
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Orbitron', sans-serif; font-size: 0.55rem; letter-spacing: 0.12em;
    color: var(--text-dim); border-radius: var(--radius-sm); padding: 0.55rem 1rem;
    transition: all var(--transition-smooth); text-transform: uppercase;
}}
.stTabs [data-baseweb="tab"]:hover {{ color: var(--text-muted); background: rgba(0,212,255,0.04); }}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, var(--accent-cyan) 0%, #0099cc 100%) !important;
    color: var(--bg-void) !important; font-weight: 600;
    box-shadow: 0 2px 12px rgba(0,212,255,0.2);
}}

.stButton > button {{
    font-family: 'Orbitron', sans-serif; letter-spacing: 0.1em; font-size: 0.65rem;
    border-radius: var(--radius-md); transition: all var(--transition-smooth); text-transform: uppercase;
}}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, var(--accent-cyan) 0%, #0099cc 100%) !important;
    border: none !important; color: var(--bg-void) !important; font-weight: 600;
    box-shadow: 0 2px 12px rgba(0,212,255,0.15);
}}
.stButton > button[kind="primary"]:hover {{
    box-shadow: 0 4px 20px rgba(0,212,255,0.3); transform: translateY(-1px);
}}

.stPlotlyChart {{ border: 1px solid var(--border); border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-card); }}
.stDataFrame {{ border-radius: var(--radius-md) !important; overflow: hidden; }}
div[data-testid="stDataFrame"] > div {{ border-radius: var(--radius-md); border: 1px solid var(--border) !important; }}
div[data-testid="stSlider"] > div > div > div {{ background-color: var(--accent-cyan) !important; }}

.streamlit-expanderHeader {{
    font-family: 'Orbitron', sans-serif !important; font-size: 0.6rem !important;
    letter-spacing: 0.15em !important; color: var(--text-muted) !important;
    background: transparent !important; border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important; padding: 0.75rem 1rem !important;
}}
.streamlit-expanderHeader:hover {{ border-color: var(--accent-cyan) !important; }}
.stApp hr {{ border-color: var(--border-subtle); opacity: 0.4; }}

/* ── Scrollbar ───────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--accent-cyan); }}

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 768px) {{
    .prophet-title {{ letter-spacing: 0.2em; }}
    .prophet-card {{ padding: 1rem; }}
    .stTabs [data-baseweb="tab"] {{ font-size: 0.45rem; padding: 0.4rem 0.5rem; }}
}}
</style>
"""
