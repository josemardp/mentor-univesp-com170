import os
import base64
import shutil
from pathlib import Path

def get_base64_img(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def main():
    root = Path(__file__).resolve().parent.parent
    assets_dir = root / "2026-3bim" / "com100" / "assets"
    
    img_interface_b64 = get_base64_img(assets_dir / "scratch_interface.png")
    img_extensions_b64 = get_base64_img(assets_dir / "scratch_extensions.png")

    html_content = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Apostila Visual Completa: Scratch & Aprendizagem Criativa | COM100 Univesp</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-primary: #0b1120;
      --bg-surface: #1e293b;
      --bg-card: #243248;
      --bg-subtle: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-accent: #38bdf8;
      --border-color: #334155;
      
      /* Cores Oficiais dos Blocos do Scratch 3.0 */
      --c-motion: #4c97ff;
      --c-looks: #9966ff;
      --c-sound: #cf63cf;
      --c-events: #ffbf00;
      --c-control: #ffab19;
      --c-sensing: #5cb1d6;
      --c-operators: #59c059;
      --c-variables: #ff8c1a;
      --c-myblocks: #ff6680;
      --c-extensions: #0fbd8c;

      --success: #10b981;
      --danger: #ef4444;
      --warning: #f59e0b;
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
      --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-main);
      line-height: 1.65;
      overflow-x: hidden;
    }}

    #progress-container {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 4px;
      background: transparent;
      z-index: 1000;
    }}
    #progress-bar {{
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
      transition: width 0.1s ease-out;
    }}

    .app-container {{
      display: flex;
      min-height: 100vh;
    }}

    /* Sidebar Navigation */
    .sidebar {{
      width: 300px;
      background-color: rgba(30, 41, 59, 0.96);
      backdrop-filter: blur(14px);
      border-right: 1px solid var(--border-color);
      position: fixed;
      top: 0;
      bottom: 0;
      left: 0;
      overflow-y: auto;
      z-index: 900;
      display: flex;
      flex-direction: column;
      padding: 1.5rem 1rem;
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 1.5rem;
    }}

    .brand-icon {{
      width: 44px;
      height: 44px;
      background: linear-gradient(135deg, #ffab19, #ff8c1a);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 1.35rem;
      color: #fff;
      box-shadow: 0 4px 15px rgba(255, 171, 25, 0.4);
    }}

    .brand-text h2 {{
      font-size: 1.1rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}

    .brand-text span {{
      font-size: 0.75rem;
      color: var(--text-accent);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .nav-group-title {{
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      font-weight: 700;
      margin: 1.25rem 0 0.5rem 0.5rem;
    }}

    .nav-links {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .nav-item a {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 0.65rem 0.85rem;
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.88rem;
      font-weight: 500;
      border-radius: var(--radius-sm);
      transition: all 0.2s ease;
    }}

    .nav-item a:hover, .nav-item a.active {{
      color: var(--text-main);
      background-color: var(--bg-subtle);
    }}

    .nav-item a.active {{
      border-left: 3px solid var(--text-accent);
      background: linear-gradient(90deg, rgba(56, 189, 248, 0.12), transparent);
    }}

    .nav-pill {{
      font-size: 0.68rem;
      padding: 2px 7px;
      border-radius: 999px;
      font-weight: 700;
      margin-left: auto;
    }}

    /* Main Content */
    .main-content {{
      margin-left: 300px;
      flex: 1;
      max-width: 1100px;
      padding: 2.5rem 3.5rem;
    }}

    .hero-banner {{
      background: linear-gradient(135deg, #1e293b 0%, #1e1b4b 60%, #0b1120 100%);
      border: 1px solid rgba(129, 140, 248, 0.3);
      border-radius: var(--radius-lg);
      padding: 2.75rem;
      margin-bottom: 3rem;
      position: relative;
      overflow: hidden;
      box-shadow: var(--shadow);
    }}

    .hero-banner::after {{
      content: '';
      position: absolute;
      top: -30%;
      right: -10%;
      width: 350px;
      height: 350px;
      background: radial-gradient(circle, rgba(255, 171, 25, 0.15) 0%, transparent 70%);
      border-radius: 50%;
      pointer-events: none;
    }}

    .badge-tag {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.4);
      color: var(--text-accent);
      padding: 4px 12px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 1rem;
    }}

    .hero-banner h1 {{
      font-size: 2.5rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1.2;
      margin-bottom: 1rem;
      background: linear-gradient(90deg, #ffffff, #cbd5e1);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .hero-banner p {{
      color: var(--text-muted);
      font-size: 1.05rem;
      max-width: 800px;
      margin-bottom: 1.5rem;
    }}

    .quick-stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
    }}

    .stat-card {{
      background: rgba(11, 17, 32, 0.65);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 1.1rem;
    }}

    .stat-label {{
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
    }}

    .stat-value {{
      font-size: 1.35rem;
      font-weight: 700;
      color: #fff;
      margin-top: 4px;
    }}

    section {{
      margin-bottom: 4rem;
      scroll-margin-top: 2rem;
    }}

    .section-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 2px solid var(--border-color);
      padding-bottom: 0.85rem;
      margin-bottom: 1.75rem;
    }}

    .section-title {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 1.65rem;
      font-weight: 800;
      letter-spacing: -0.02em;
    }}

    .section-num {{
      background: var(--text-accent);
      color: var(--bg-primary);
      width: 34px;
      height: 34px;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 0.95rem;
      font-weight: 800;
    }}

    .card {{
      background-color: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 2rem;
      margin-bottom: 1.75rem;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }}

    .card-title {{
      font-size: 1.25rem;
      font-weight: 700;
      margin-bottom: 1.2rem;
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    /* Print & Screenshot Frames */
    .print-frame {{
      background: #0f172a;
      border: 2px solid var(--border-color);
      border-radius: var(--radius-md);
      overflow: hidden;
      margin: 1.5rem 0;
      box-shadow: var(--shadow);
    }}

    .print-toolbar {{
      background: #1e293b;
      padding: 10px 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 1px solid var(--border-color);
    }}

    .print-dot {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
    }}

    .print-title {{
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-left: 10px;
    }}

    .print-img {{
      width: 100%;
      height: auto;
      display: block;
      transition: transform 0.2s ease;
    }}

    /* Real Block Models (Pure CSS / Authentic Shape) */
    .block-gallery {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
      gap: 1.5rem;
      margin: 1.5rem 0;
    }}

    .block-model-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}

    .model-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--text-accent);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding-bottom: 6px;
    }}

    /* Realistic Scratch Block Styling */
    .real-scratch-stack {{
      background: #101726;
      border: 1px solid #1e293b;
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 2px;
      align-items: flex-start;
      box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.4);
    }}

    .sb-block {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 0.85rem;
      font-weight: 700;
      color: #ffffff;
      padding: 7px 14px;
      border-radius: 6px;
      border: 1px solid rgba(0, 0, 0, 0.2);
      box-shadow: 0 2px 0 rgba(0, 0, 0, 0.25);
      position: relative;
      cursor: default;
      user-select: none;
    }}

    .sb-hat {{
      border-top-left-radius: 20px;
      border-top-right-radius: 20px;
      border-bottom-left-radius: 6px;
      border-bottom-right-radius: 6px;
      padding-top: 10px;
    }}

    .sb-c-wrap {{
      background: #ffab19;
      border-radius: 6px;
      display: inline-flex;
      flex-direction: column;
      box-shadow: 0 2px 0 rgba(0, 0, 0, 0.25);
      width: 100%;
      max-width: 320px;
      border: 1px solid rgba(0, 0, 0, 0.2);
    }}

    .sb-c-top {{
      padding: 7px 12px;
      font-size: 0.85rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .sb-c-body {{
      background: #101726;
      margin-left: 18px;
      padding: 8px 12px;
      border-left: 8px solid #ffab19;
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-height: 40px;
    }}

    .sb-c-bottom {{
      background: #ffab19;
      height: 12px;
      border-bottom-left-radius: 6px;
      border-bottom-right-radius: 6px;
    }}

    .sb-input-circle {{
      background: #ffffff;
      color: #222222;
      border-radius: 12px;
      padding: 2px 9px;
      font-weight: 700;
      font-size: 0.82rem;
      border: 1px solid rgba(0, 0, 0, 0.2);
    }}

    .sb-input-bool {{
      background: rgba(0, 0, 0, 0.2);
      border: 1px solid rgba(255, 255, 255, 0.4);
      color: #ffffff;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 0.78rem;
    }}

    .sb-input-str {{
      background: #ffffff;
      color: #1e293b;
      border-radius: 6px;
      padding: 2px 8px;
      font-weight: 600;
      font-size: 0.82rem;
    }}

    .callout {{
      border-radius: var(--radius-sm);
      padding: 1.25rem 1.5rem;
      margin: 1.25rem 0;
      display: flex;
      gap: 14px;
      align-items: flex-start;
      border-left: 4px solid;
    }}

    .callout-pegadinha {{
      background: rgba(239, 68, 68, 0.1);
      border-left-color: var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.25);
    }}

    .callout-pegadinha .callout-icon {{
      color: var(--danger);
      font-size: 1.4rem;
      line-height: 1;
    }}

    .callout-tip {{
      background: rgba(16, 185, 129, 0.1);
      border-left-color: var(--success);
      border: 1px solid rgba(16, 185, 129, 0.25);
    }}

    .callout-tip .callout-icon {{
      color: var(--success);
      font-size: 1.4rem;
      line-height: 1;
    }}

    .callout-theory {{
      background: rgba(56, 189, 248, 0.08);
      border-left-color: var(--text-accent);
      border: 1px solid rgba(56, 189, 248, 0.2);
    }}

    .callout-theory .callout-icon {{
      color: var(--text-accent);
      font-size: 1.4rem;
      line-height: 1;
    }}

    .callout-title {{
      font-weight: 700;
      font-size: 0.95rem;
      margin-bottom: 4px;
    }}

    .callout-body {{
      font-size: 0.92rem;
      color: #e2e8f0;
    }}

    .four-ps-container {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 1.25rem;
      margin: 1.5rem 0;
    }}

    .p-card {{
      background: linear-gradient(180deg, var(--bg-card) 0%, rgba(36, 50, 72, 0.5) 100%);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 1.5rem;
      text-align: center;
      position: relative;
      overflow: hidden;
    }}

    .p-letter {{
      font-size: 3.5rem;
      font-weight: 900;
      opacity: 0.15;
      position: absolute;
      top: 5px;
      right: 15px;
      line-height: 1;
    }}

    .p-icon {{
      font-size: 2.2rem;
      margin-bottom: 0.75rem;
    }}

    .p-title {{
      font-size: 1.15rem;
      font-weight: 800;
      margin-bottom: 0.35rem;
      color: var(--text-accent);
    }}

    .p-english {{
      font-size: 0.8rem;
      color: var(--text-muted);
      font-style: italic;
      margin-bottom: 0.75rem;
    }}

    .p-desc {{
      font-size: 0.88rem;
      color: #cbd5e1;
    }}

    .spiral-flow {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: center;
      gap: 12px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 1.5rem;
      margin: 1.5rem 0;
    }}

    .spiral-step {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 0.65rem 1.1rem;
      font-weight: 700;
      font-size: 0.9rem;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .spiral-arrow {{
      color: var(--text-accent);
      font-size: 1.2rem;
      font-weight: 800;
    }}

    .flashcards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.25rem;
      margin: 1.5rem 0;
    }}

    .flashcard {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 1.5rem;
      cursor: pointer;
      perspective: 1000px;
      transition: all 0.25s ease;
      min-height: 180px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}

    .flashcard:hover {{
      border-color: var(--text-accent);
      transform: translateY(-2px);
    }}

    .flashcard-tag {{
      font-size: 0.72rem;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--text-accent);
      letter-spacing: 0.05em;
    }}

    .flashcard-front {{
      font-size: 1.05rem;
      font-weight: 700;
      margin: 0.75rem 0;
      color: #fff;
    }}

    .flashcard-back {{
      font-size: 0.9rem;
      color: #cbd5e1;
      display: none;
      background: rgba(15, 23, 42, 0.6);
      padding: 0.85rem;
      border-radius: var(--radius-sm);
      border-left: 3px solid var(--success);
      margin-top: 0.5rem;
    }}

    .flashcard.flipped .flashcard-back {{
      display: block;
    }}

    .flashcard-prompt {{
      font-size: 0.75rem;
      color: var(--text-muted);
      text-align: right;
    }}

    .quiz-container {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 2rem;
      margin-bottom: 2rem;
    }}

    .quiz-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
    }}

    .quiz-badge {{
      background: rgba(129, 140, 248, 0.15);
      color: #818cf8;
      border: 1px solid rgba(129, 140, 248, 0.3);
      padding: 3px 10px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 700;
    }}

    .question-text {{
      font-size: 1.05rem;
      font-weight: 600;
      line-height: 1.5;
      margin-bottom: 1.5rem;
      color: #f1f5f9;
    }}

    .options-list {{
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }}

    .option-btn {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: #cbd5e1;
      padding: 1rem 1.25rem;
      border-radius: var(--radius-sm);
      text-align: left;
      font-size: 0.92rem;
      font-family: inherit;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: flex-start;
      gap: 12px;
    }}

    .option-btn:hover {{
      background: var(--bg-subtle);
      border-color: rgba(255, 255, 255, 0.2);
      color: #fff;
    }}

    .option-letter {{
      background: rgba(255, 255, 255, 0.1);
      width: 24px;
      height: 24px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.8rem;
      flex-shrink: 0;
    }}

    .option-btn.correct {{
      background: rgba(16, 185, 129, 0.15);
      border-color: var(--success);
      color: #fff;
    }}
    .option-btn.correct .option-letter {{
      background: var(--success);
      color: #fff;
    }}

    .option-btn.incorrect {{
      background: rgba(239, 68, 68, 0.15);
      border-color: var(--danger);
      color: #fca5a5;
    }}
    .option-btn.incorrect .option-letter {{
      background: var(--danger);
      color: #fff;
    }}

    .quiz-feedback {{
      display: none;
      padding: 1.25rem;
      border-radius: var(--radius-sm);
      margin-top: 1rem;
      font-size: 0.9rem;
      animation: fadeIn 0.3s ease;
    }}

    .quiz-feedback.show {{
      display: block;
    }}

    .quiz-feedback.correct-feedback {{
      background: rgba(16, 185, 129, 0.12);
      border-left: 4px solid var(--success);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .quiz-feedback.incorrect-feedback {{
      background: rgba(239, 68, 68, 0.12);
      border-left: 4px solid var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}

    .table-container {{
      overflow-x: auto;
      margin: 1.5rem 0;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-color);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.9rem;
    }}

    th {{
      background-color: var(--bg-card);
      color: #e2e8f0;
      padding: 0.9rem 1.2rem;
      font-weight: 700;
      border-bottom: 1px solid var(--border-color);
    }}

    td {{
      padding: 0.85rem 1.2rem;
      border-bottom: 1px solid var(--border-color);
      color: #cbd5e1;
    }}

    tr:last-child td {{
      border-bottom: none;
    }}

    tr:hover td {{
      background-color: rgba(255, 255, 255, 0.02);
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    @media (max-width: 900px) {{
      .sidebar {{
        transform: translateX(-100%);
      }}
      .main-content {{
        margin-left: 0;
        padding: 1.5rem;
      }}
    }}
  </style>
</head>
<body>

  <div id="progress-container">
    <div id="progress-bar"></div>
  </div>

  <div class="app-container">
    <nav class="sidebar" id="sidebar">
      <div class="brand">
        <div class="brand-icon">S</div>
        <div class="brand-text">
          <h2>Scratch & Resnick</h2>
          <span>COM100 · Univesp</span>
        </div>
      </div>

      <div class="nav-group-title">Conteúdo Programático</div>
      <ul class="nav-links">
        <li class="nav-item">
          <a href="#visao-geral" class="active">
            <span>🎯</span> Visão Geral da Prova
            <span class="nav-pill" style="background:#0284c7; color:#fff;">Foco</span>
          </a>
        </li>
        <li class="nav-item">
          <a href="#prints-interface">
            <span>📸</span> Print Real: Editor Scratch
            <span class="nav-pill" style="background:#38bdf8; color:#000;">Visual</span>
          </a>
        </li>
        <li class="nav-item">
          <a href="#recortes-comandos">
            <span>🧩</span> Recortes Reais de Comandos
            <span class="nav-pill" style="background:var(--c-control); color:#fff;">Blocos</span>
          </a>
        </li>
        <li class="nav-item">
          <a href="#semana-3">
            <span>🔄</span> S3: Repetições & Laços
            <span class="nav-pill" style="background:var(--c-motion); color:#fff;">S3</span>
          </a>
        </li>
        <li class="nav-item">
          <a href="#semana-4">
            <span>🔀</span> S4: Condicionais, I/O e Variáveis
            <span class="nav-pill" style="background:var(--c-variables); color:#fff;">S4</span>
          </a>
        </li>
        <li class="nav-item">
          <a href="#semana-5">
            <span>💡</span> S5: Resnick e os 4Ps
            <span class="nav-pill" style="background:var(--c-looks); color:#fff;">S5</span>
          </a>
        </li>
        <li class="nav-item">
          <a href="#semana-6">
            <span>📡</span> S6: Broadcast & Extensões
            <span class="nav-pill" style="background:var(--c-extensions); color:#fff;">S6</span>
          </a>
        </li>
      </ul>

      <div class="nav-group-title">Estudo Ativo & Fixação</div>
      <ul class="nav-links">
        <li class="nav-item">
          <a href="#flashcards">
            <span>⚡</span> Flashcards de Pegadinhas
            <span class="nav-pill" style="background:#f59e0b; color:#000;">6 cards</span>
          </a>
        </li>
        <li class="nav-item">
          <a href="#simulado-interativo">
            <span>📝</span> Simulado com Feedback
            <span class="nav-pill" style="background:#10b981; color:#fff;">5 testes</span>
          </a>
        </li>
        <li class="nav-item">
          <a href="#resumo-rapido">
            <span>📑</span> Cola Resumida (2 Min)
          </a>
        </li>
      </ul>
    </nav>

    <main class="main-content">

      <!-- Hero Header -->
      <header class="hero-banner" id="visao-geral">
        <div class="badge-tag">Apostila Visual Completa · Revisão 22/09/2026</div>
        <h1>Scratch & Aprendizagem Criativa</h1>
        <p>
          Guia definitivo de estudo ilustrado cobrindo as <strong>Semanas 3, 4, 5 e 6</strong> da disciplina 
          <strong>COM100 (Pensamento Computacional)</strong>. Com prints autênticos da interface, recortes fiéis dos blocos, 
          modelos de scripts montados, Mitchel Resnick, os 4Ps, broadcast e extensões.
        </p>

        <div class="quick-stats">
          <div class="stat-card">
            <div class="stat-label">Carga nas Questões</div>
            <div class="stat-value" style="color: #38bdf8;">~50% da Prova</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Autores-Chave</div>
            <div class="stat-value" style="color: #c084fc;">Resnick & Papert</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Conceito Central</div>
            <div class="stat-value" style="color: #facc15;">4Ps + Espiral</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Pegadinha Clássica</div>
            <div class="stat-value" style="color: #f87171;">Repita até que</div>
          </div>
        </div>
      </header>

      <!-- SEÇÃO NOVA: PRINT REAL DA INTERFACE DO SCRATCH -->
      <section id="prints-interface">
        <div class="section-header">
          <div class="section-title">
            <span class="section-num">📸</span>
            <span>Print Real: A Interface do Scratch 3.0 e suas Áreas</span>
          </div>
        </div>

        <div class="card">
          <h3 class="card-title">Visão Geral da Tela de Criação (O que a Univesp aponta em questões)</h3>
          <p style="color: var(--text-muted); margin-bottom: 1rem;">
            Abaixo está a captura autêntica de tela do Scratch 3.0. Observe com atenção as 5 regiões funcionais marcadas:
          </p>

          <div class="print-frame">
            <div class="print-toolbar">
              <span class="print-dot" style="background:#ef4444;"></span>
              <span class="print-dot" style="background:#f59e0b;"></span>
              <span class="print-dot" style="background:#10b981;"></span>
              <span class="print-title">Editor Scratch 3.0 (MIT Media Lab) — Captura Oficial em Alta Resolução</span>
            </div>
            <img class="print-img" src="data:image/png;base64,{img_interface_b64}" alt="Interface do Scratch 3.0" />
          </div>

          <div class="table-container" style="margin-top: 1.5rem;">
            <table>
              <thead>
                <tr>
                  <th style="width: 25%;">Região da Interface</th>
                  <th style="width: 40%;">Função e Elementos</th>
                  <th style="width: 35%;">Como cai na prova da Univesp</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>1. Paleta de Blocos (Esquerda)</strong></td>
                  <td>Círculos coloridos categorizados: Movimento, Aparência, Som, Eventos, Controle, Sensores, Operadores, Variáveis e Meus Blocos.</td>
                  <td>Cobram a correspondência de cores e finalidade (ex: Eventos é amarelo, Controle é laranja).</td>
                </tr>
                <tr>
                  <td><strong>2. Área de Scripts (Centro)</strong></td>
                  <td>Espaço de montagem livre (*Workspace*) onde você arrasta, solta e encaixa magneticamente as peças de quebra-cabeça.</td>
                  <td>Elimina a barreira de digitação de sintaxe textual (vírgula, chaves).</td>
                </tr>
                <tr>
                  <td><strong>3. Palco / Stage (Direita Superior)</strong></td>
                  <td>Área de exibição visual. Plano cartesiano onde o centro exato é $(0, 0)$. Eixo X vai de $-240$ a $+240$; Eixo Y vai de $-180$ a $+180$.</td>
                  <td>Perguntas sobre localização, limites de borda e onde os atores se movimentam.</td>
                </tr>
                <tr>
                  <td><strong>4. Botões de Disparo (Acima do Palco)</strong></td>
                  <td><strong>Bandeira Verde</strong> (dispara scripts do evento `quando clicada`) e <strong>Círculo Vermelho</strong> (interrompe todos os scripts).</td>
                  <td>Identificar que a bandeira verde dispara a execução geral dos projetos.</td>
                </tr>
                <tr>
                  <td><strong>5. Área de Atores e Cenários (Direita Inferior)</strong></td>
                  <td>Painel com a lista de todos os *Sprites* do projeto, suas coordenadas atuais $(x, y)$, tamanho, direção e botão de adicionar novos.</td>
                  <td>Mostra que cada ator tem seu próprio conjunto de fantasias e códigos independentes.</td>
                </tr>
                <tr>
                  <td><strong>6. Botão de Extensões (Canto Inferior Esquerdo)</strong></td>
                  <td>Ícone azul no rodapé que abre a biblioteca de extensões (Música, Caneta, Sensor de Vídeo, Texto para Fala, etc.).</td>
                  <td>Cobram onde se ativam os recursos de hardware externo e IA.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- SEÇÃO NOVA: RECORTES E MODELOS REAIS DE COMANDOS -->
      <section id="recortes-comandos">
        <div class="section-header">
          <div class="section-title">
            <span class="section-num">🧩</span>
            <span>Recortes Reais: Modelos de Comandos e Blocos Encaixados</span>
          </div>
        </div>

        <div class="card">
          <h3 class="card-title">Anatomia das Peças de Quebra-Cabeça do Scratch</h3>
          <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
            O Scratch possui 5 formatos fundamentais de blocos que evitam erros lógicos por encaixe físico impossível:
          </p>

          <div class="block-gallery">

            <!-- Modelo 1: Bloco Chapéu (Hat) -->
            <div class="block-model-card">
              <div class="model-header">
                <span>FORMATO 1: BLOCO CHAPÉU (HAT)</span>
                <span>CATEGORIA: EVENTOS</span>
              </div>
              <div class="real-scratch-stack">
                <div class="sb-block sb-hat" style="background: var(--c-events); color: #222;">
                  <span>🏁</span> quando a bandeira verde for clicada
                </div>
              </div>
              <p style="font-size: 0.86rem; color: #cbd5e1;">
                <strong>Formato:</strong> Topo curvo arredondado sem encaixe fêmea por cima. Não pode ser encaixado embaixo de nenhum outro bloco. É sempre a <strong>primeira instrução disparadora</strong> de uma pilha.
              </p>
            </div>

            <!-- Modelo 2: Bloco de Empilhamento (Stack) -->
            <div class="block-model-card">
              <div class="model-header">
                <span>FORMATO 2: PILHA (STACK BLOCK)</span>
                <span>CATEGORIA: MOVIMENTO / APARÊNCIA</span>
              </div>
              <div class="real-scratch-stack">
                <div class="sb-block" style="background: var(--c-motion);">
                  mova <span class="sb-input-circle">10</span> passos
                </div>
                <div class="sb-block" style="background: var(--c-looks);">
                  diga <span class="sb-input-str">Olá!</span> por <span class="sb-input-circle">2</span> seg
                </div>
              </div>
              <p style="font-size: 0.86rem; color: #cbd5e1;">
                <strong>Formato:</strong> Entalhe macho no topo e fêmea na base. Executa uma ação de comando direto e passa imediatamente para o bloco de baixo.
              </p>
            </div>

            <!-- Modelo 3: Bloco C (Wrap / Laço e Condicional) -->
            <div class="block-model-card">
              <div class="model-header">
                <span>FORMATO 3: BLOCO EM "C" (WRAPPER)</span>
                <span>CATEGORIA: CONTROLE</span>
              </div>
              <div class="real-scratch-stack" style="width: 100%;">
                <div class="sb-c-wrap">
                  <div class="sb-c-top">
                    repita até que <span class="sb-input-bool">&lt;tocando na borda?&gt;</span>
                  </div>
                  <div class="sb-c-body">
                    <div class="sb-block" style="background: var(--c-motion); padding: 5px 10px; font-size: 0.8rem;">
                      mova <span class="sb-input-circle">10</span> passos
                    </div>
                  </div>
                  <div class="sb-c-bottom"></div>
                </div>
              </div>
              <p style="font-size: 0.86rem; color: #cbd5e1;">
                <strong>Formato:</strong> Abertura em "C" que abraça outros blocos internos. Controla repetições ou desvios condicionais.
              </p>
            </div>

            <!-- Modelo 4: Booleano Hexagonal & Repórter Oval -->
            <div class="block-model-card">
              <div class="model-header">
                <span>FORMATO 4 & 5: REPORTADORES DE VALOR</span>
                <span>OPERADORES & VARIÁVEIS</span>
              </div>
              <div class="real-scratch-stack">
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                  <span class="sb-block" style="background: var(--c-operators); border-radius: 999px;">
                    &lt; <span class="sb-input-circle" style="background:#ff8c1a; color:#fff;">pontos</span> &gt; <span class="sb-input-circle">100</span> &gt;
                  </span>
                  <span class="sb-block" style="background: var(--c-sensing); border-radius: 999px;">
                    (resposta)
                  </span>
                </div>
              </div>
              <p style="font-size: 0.86rem; color: #cbd5e1;">
                <strong>Hexagonal pontudo:</strong> Retorna Booleano (Verdadeiro ou Falso).<br>
                <strong>Oval arredondado:</strong> Retorna números ou textos (strings) para encaixar em campos circulares.
              </p>
            </div>

          </div>
        </div>

        <!-- Scripts Reais Montados para Teste de Mesa -->
        <div class="card">
          <h3 class="card-title">Recortes de Scripts Montados (Simulação Visual de Prova)</h3>
          <p style="color: var(--text-muted); margin-bottom: 1.25rem;">
            Veja abaixo como a Univesp apresenta pilhas de blocos montados em questões de interpretação algorítmica:
          </p>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem;">

            <!-- Script A: Loop e Parada -->
            <div style="background: var(--bg-card); padding: 1.5rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
              <h4 style="color: var(--text-accent); margin-bottom: 0.75rem; font-size: 0.95rem;">Script 1: Laço com Sensor de Parada</h4>
              <div class="real-scratch-stack">
                <div class="sb-block sb-hat" style="background: var(--c-events); color: #222;">
                  🏁 quando bandeira verde clicada
                </div>
                <div class="sb-block" style="background: var(--c-motion);">
                  vá para x: <span class="sb-input-circle">-200</span> y: <span class="sb-input-circle">0</span>
                </div>
                <div class="sb-c-wrap">
                  <div class="sb-c-top">
                    repita até que <span class="sb-input-bool">&lt;tocando em [borda v]&gt;</span>
                  </div>
                  <div class="sb-c-body">
                    <div class="sb-block" style="background: var(--c-motion); padding: 5px 10px; font-size: 0.8rem;">
                      mova <span class="sb-input-circle">10</span> passos
                    </div>
                  </div>
                  <div class="sb-c-bottom"></div>
                </div>
                <div class="sb-block" style="background: var(--c-looks);">
                  diga <span class="sb-input-str">Cheguei ao fim!</span> por <span class="sb-input-circle">2</span> seg
                </div>
              </div>
              <p style="font-size: 0.84rem; color: #cbd5e1; margin-top: 0.75rem;">
                <strong>Teste de Mesa:</strong> O personagem começa na esquerda (-200). Ele anda de 10 em 10 passos enquanto NÃO tocar na borda. No momento em que bate na borda (Verdadeiro), ele sai do laço e diz "Cheguei ao fim!".
              </p>
            </div>

            <!-- Script B: Entrada e Variável -->
            <div style="background: var(--bg-card); padding: 1.5rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
              <h4 style="color: var(--text-accent); margin-bottom: 0.75rem; font-size: 0.95rem;">Script 2: Entrada e Preservação de Variável</h4>
              <div class="real-scratch-stack">
                <div class="sb-block sb-hat" style="background: var(--c-events); color: #222;">
                  🏁 quando bandeira verde clicada
                </div>
                <div class="sb-block" style="background: var(--c-sensing);">
                  pergunte <span class="sb-input-str">Qual seu nome?</span> e espere
                </div>
                <div class="sb-block" style="background: var(--c-variables);">
                  mude <span class="sb-input-str">[nome_usuario v]</span> para <span class="sb-input-bool" style="background:#5cb1d6;">(resposta)</span>
                </div>
                <div class="sb-block" style="background: var(--c-looks);">
                  diga <span class="sb-block" style="background:var(--c-operators); padding:2px 8px; font-size:0.78rem;">junte [Olá, ] com (nome_usuario)</span>
                </div>
              </div>
              <p style="font-size: 0.84rem; color: #cbd5e1; margin-top: 0.75rem;">
                <strong>Ponto Vital:</strong> A variável personalizada <code>nome_usuario</code> salvou o valor de <code>resposta</code> antes que uma nova pergunta pudesse apagá-lo!
              </p>
            </div>

          </div>
        </div>
      </section>

      <!-- SEMANA 3: REPETIÇÃO -->
      <section id="semana-3">
        <div class="section-header">
          <div class="section-title">
            <span class="section-num">S3</span>
            <span>Semana 3: Estruturas de Repetição & Lógica de Controle</span>
          </div>
        </div>

        <div class="card">
          <h3 class="card-title">As Três Estruturas de Repetição no Scratch</h3>
          
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Bloco Scratch</th>
                  <th>Tipo de Laço</th>
                  <th>Comportamento e Parada</th>
                  <th>Quando Usar</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><span class="sb-block" style="background: var(--c-control);">repita (N) vezes</span></td>
                  <td><strong>Determinístico (Finito)</strong></td>
                  <td>Executa exatamente $N$ iterações e prossegue para a próxima linha de código.</td>
                  <td>Contagens certas (ex: desenhar os 4 lados de um quadrado).</td>
                </tr>
                <tr>
                  <td><span class="sb-block" style="background: var(--c-control);">sempre</span> <em>(forever)</em></td>
                  <td><strong>Infinito (Contínuo)</strong></td>
                  <td>Não para nunca por conta própria. Roda até o jogador clicar no botão Stop vermelho.</td>
                  <td>Gravidade, checagem contínua de controles ou música de fundo.</td>
                </tr>
                <tr>
                  <td><span class="sb-block" style="background: var(--c-control);">repita até que &lt;cond&gt;</span></td>
                  <td><strong>Condicional de Parada</strong></td>
                  <td>Executa <strong>enquanto a condição for FALSA</strong>. Para assim que vira <strong>VERDADEIRA</strong>.</td>
                  <td>Mover o personagem até encostar na borda ou colidir com o obstáculo.</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="callout callout-pegadinha">
            <div class="callout-icon">⚠️</div>
            <div>
              <div class="callout-title">Pegadinha Suprema da Banca Univesp!</div>
              <div class="callout-body">
                Em linguagens como Python ou C, a instrução <code>while (condição)</code> executa enquanto ela for <strong>VERDADEIRA</strong>.<br>
                No Scratch, o bloco <strong><code>repita até que &lt;condição&gt;</code></strong> faz o inverso: ele executa enquanto ela for <strong>FALSA</strong>, e <strong>encerra imediatamente no momento em que a condição se torna VERDADEIRA</strong>!
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- SEMANA 4: CONDICIONAIS & I/O -->
      <section id="semana-4">
        <div class="section-header">
          <div class="section-title">
            <span class="section-num">S4</span>
            <span>Semana 4: Condicionais, Variáveis e Comandos de Entrada/Saída</span>
          </div>
        </div>

        <div class="card">
          <h3 class="card-title">Variáveis e Entrada/Saída (I/O)</h3>
          
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Tipo de Escopo</th>
                  <th>Configuração no Scratch</th>
                  <th>Visibilidade e Acesso</th>
                  <th>Casos de Uso Típicos</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Global</strong></td>
                  <td><em>"Para todos os atores"</em></td>
                  <td>Todos os personagens e o cenário podem ler e alterar o seu valor.</td>
                  <td>Pontuação geral, recorde, cronômetro da fase, nível do jogo.</td>
                </tr>
                <tr>
                  <td><strong>Local</strong></td>
                  <td><em>"Apenas para este ator"</em></td>
                  <td>Exclusiva do personagem onde foi criada. Nenhum outro ator a enxerga diretamente.</td>
                  <td>Velocidade individual do inimigo, vida particular daquele monstro.</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="callout callout-pegadinha">
            <div class="callout-icon">⚠️</div>
            <div>
              <div class="callout-title">Atenção para a Sobrescrita de "Resposta"</div>
              <div class="callout-body">
                A variável <code>resposta</code> armazena <strong>apenas a última entrada</strong> digitada no bloco <code>pergunte e espere</code>. 
                Se você fizer uma segunda pergunta sem salvar o valor anterior em outra variável, o primeiro dado será <strong>completamente perdido</strong>!
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- SEMANA 5: APRENDIZAGEM CRIATIVA -->
      <section id="semana-5">
        <div class="section-header">
          <div class="section-title">
            <span class="section-num">S5</span>
            <span>Semana 5: Aprendizagem Criativa: Mitchel Resnick e os 4Ps</span>
          </div>
        </div>

        <div class="card">
          <h3 class="card-title">Os Quatro Pilares (4Ps) da Aprendizagem Criativa</h3>
          <p style="color: var(--text-muted);">
            Teoria formulada por Mitchel Resnick no MIT Media Lab (Lifelong Kindergarten):
          </p>

          <div class="four-ps-container">
            <div class="p-card">
              <div class="p-letter">P</div>
              <div class="p-icon">🛠️</div>
              <div class="p-title">Projetos</div>
              <div class="p-english">Projects</div>
              <div class="p-desc">Aprende-se fazendo algo concreto e autoral (jogos, histórias, animações), não decorando listas mecânicas.</div>
            </div>

            <div class="p-card">
              <div class="p-letter">P</div>
              <div class="p-icon">❤️</div>
              <div class="p-title">Paixão</div>
              <div class="p-english">Passion</div>
              <div class="p-desc">Quando as pessoas trabalham em temas que realmente importam para elas, dedicam mais tempo e superam frustrações.</div>
            </div>

            <div class="p-card">
              <div class="p-letter">P</div>
              <div class="p-icon">👥</div>
              <div class="p-title">Pares</div>
              <div class="p-english">Peers</div>
              <div class="p-desc">Aprender é social: colaboração, troca de ideias, trabalho em equipe e compartilhamento na comunidade.</div>
            </div>

            <div class="p-card">
              <div class="p-letter">P</div>
              <div class="p-icon">🎨</div>
              <div class="p-title">Pensar Brincando</div>
              <div class="p-english">Play / Tinkering</div>
              <div class="p-desc">Bricolagem, experimentação destemida, assumir riscos e enxergar os erros como degraus do aprendizado.</div>
            </div>
          </div>
        </div>

        <div class="card">
          <h3 class="card-title">A Espiral da Aprendizagem Criativa</h3>
          <div class="spiral-flow">
            <div class="spiral-step">💭 1. Imaginar</div>
            <div class="spiral-arrow">➔</div>
            <div class="spiral-step">🔨 2. Criar</div>
            <div class="spiral-arrow">➔</div>
            <div class="spiral-step">🎲 3. Brincar</div>
            <div class="spiral-arrow">➔</div>
            <div class="spiral-step">🤝 4. Compartilhar</div>
            <div class="spiral-arrow">➔</div>
            <div class="spiral-step">🔍 5. Refletir</div>
            <div class="spiral-arrow">➔</div>
            <div class="spiral-step" style="border-color: var(--text-accent);">✨ 6. Imaginar Novamente...</div>
          </div>
        </div>
      </section>

      <!-- SEMANA 6: EXTENSÕES & BROADCAST -->
      <section id="semana-6">
        <div class="section-header">
          <div class="section-title">
            <span class="section-num">S6</span>
            <span>Semana 6: Sincronização (Broadcast) e Extensões do Scratch</span>
          </div>
        </div>

        <!-- PRINT REAL DA PÁGINA DE EXTENSÕES -->
        <div class="card">
          <h3 class="card-title">Print Real: A Biblioteca de Extensões do Scratch 3.0</h3>
          <p style="color: var(--text-muted); margin-bottom: 1rem;">
            Abaixo está a captura real da biblioteca aberta ao clicar no botão azul no canto inferior esquerdo:
          </p>

          <div class="print-frame">
            <div class="print-toolbar">
              <span class="print-dot" style="background:#ef4444;"></span>
              <span class="print-dot" style="background:#f59e0b;"></span>
              <span class="print-dot" style="background:#10b981;"></span>
              <span class="print-title">Scratch 3.0 Extension Library — Captura Autêntica dos Módulos Adicionais</span>
            </div>
            <img class="print-img" src="data:image/png;base64,{img_extensions_b64}" alt="Extensões do Scratch 3.0" />
          </div>

          <div class="table-container" style="margin-top: 1.5rem;">
            <table>
              <thead>
                <tr>
                  <th>Extensão</th>
                  <th>Tecnologia Subjacente</th>
                  <th>O que Permite Fazer na Prática</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Caneta (Pen)</strong></td>
                  <td>Rastreamento de vetores 2D</td>
                  <td>O ator desenha riscos na tela conforme anda (geometria, polígonos, fractais).</td>
                </tr>
                <tr>
                  <td><strong>Texto para Fala (Text to Speech)</strong></td>
                  <td>Síntese de voz com <strong>Amazon Polly</strong></td>
                  <td>O ator verbaliza frases com áudio narrado em português ou outros idiomas.</td>
                </tr>
                <tr>
                  <td><strong>Tradução (Translate)</strong></td>
                  <td>API do <strong>Google Translate</strong></td>
                  <td>Traduz textos dinamicamente entre dezenas de línguas em tempo real.</td>
                </tr>
                <tr>
                  <td><strong>Sensor de Vídeo</strong></td>
                  <td>Visão computacional via webcam</td>
                  <td>Detecta movimento corporal do usuário na câmera para interagir com os atores do palco.</td>
                </tr>
                <tr>
                  <td><strong>Hardware Externo</strong></td>
                  <td>Micro:bit, Makey Makey, LEGO Spike</td>
                  <td>Computação física: tocar bateria com bananas, controlar robôs e inventar joysticks.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <h3 class="card-title">Sincronização entre Atores: Broadcast</h3>
          <p>
            Para coordenar diálogos e ações simultâneas entre múltiplos atores e o palco:
          </p>

          <div class="real-scratch-stack" style="margin: 1.25rem 0;">
            <div class="sb-block" style="background: var(--c-events); color:#222;">
              transmita <span class="sb-input-str">[entrar_castelo v]</span>
            </div>
            <div class="sb-block sb-hat" style="background: var(--c-events); color:#222; margin-top: 10px;">
              quando eu receber <span class="sb-input-str">[entrar_castelo v]</span>
            </div>
            <div class="sb-block" style="background: var(--c-looks);">
              mude para o cenário <span class="sb-input-str">[Castelo v]</span>
            </div>
          </div>
        </div>
      </section>

      <!-- FLASHCARDS INTERATIVOS -->
      <section id="flashcards">
        <div class="section-header">
          <div class="section-title">
            <span class="section-num">⚡</span>
            <span>Flashcards: Memorização de Pegadinhas Críticas</span>
          </div>
        </div>
        <p style="color: var(--text-muted); margin-bottom: 1.25rem;">
          Clique no cartão para virar e conferir a resposta. Excelente para revisar 30 minutos antes da prova!
        </p>

        <div class="flashcards-grid">
          <div class="flashcard" onclick="this.classList.toggle('flipped')">
            <div>
              <span class="flashcard-tag">Semana 3 · Repetição</span>
              <div class="flashcard-front">Como funciona o bloco "repita até que &lt;condição&gt;"?</div>
            </div>
            <div class="flashcard-back">
              <strong>Pegadinha:</strong> Ele repete <strong>enquanto a condição for FALSA</strong> e encerra no momento em que ela vira <strong>VERDADEIRA</strong>. É o inverso do <code>while</code> do Python!
            </div>
            <div class="flashcard-prompt">Clique para virar ↻</div>
          </div>

          <div class="flashcard" onclick="this.classList.toggle('flipped')">
            <div>
              <span class="flashcard-tag">Semana 4 · I/O</span>
              <div class="flashcard-front">O que acontece com a variável nativa "resposta" ao fazer duas perguntas seguidas?</div>
            </div>
            <div class="flashcard-back">
              O conteúdo antigo é <strong>completamente sobrescrito e perdido</strong>! Se precisar do dado da 1ª pergunta, guarde-o em outra variável antes da 2ª.
            </div>
            <div class="flashcard-prompt">Clique para virar ↻</div>
          </div>

          <div class="flashcard" onclick="this.classList.toggle('flipped')">
            <div>
              <span class="flashcard-tag">Semana 5 · Aprendizagem Criativa</span>
              <div class="flashcard-front">O que significa a metáfora de "Paredes Largas" (Wide Walls)?</div>
            </div>
            <div class="flashcard-back">
              Significa que a ferramenta apoia uma <strong>vasta diversidade de temas, estilos e interesses</strong> (não só exatas: música, narrativas, arte, ciências).
            </div>
            <div class="flashcard-prompt">Clique para virar ↻</div>
          </div>

          <div class="flashcard" onclick="this.classList.toggle('flipped')">
            <div>
              <span class="flashcard-tag">Semana 4 · Escopo</span>
              <div class="flashcard-front">Diferença entre variável "para todos os atores" e "apenas para este ator"?</div>
            </div>
            <div class="flashcard-back">
              <strong>Para todos (Global):</strong> qualquer ator ou palco acessa/muda (ex: placar).<br>
              <strong>Apenas para este (Local):</strong> visível só por aquele ator (ex: sua velocidade).
            </div>
            <div class="flashcard-prompt">Clique para virar ↻</div>
          </div>

          <div class="flashcard" onclick="this.classList.toggle('flipped')">
            <div>
              <span class="flashcard-tag">Semana 5 · Os 4Ps</span>
              <div class="flashcard-front">Quais são os 4Ps da Aprendizagem Criativa de Resnick?</div>
            </div>
            <div class="flashcard-back">
              1. <strong>Projetos</strong> (Projects)<br>
              2. <strong>Paixão</strong> (Passion)<br>
              3. <strong>Pares</strong> (Peers)<br>
              4. <strong>Pensar Brincando</strong> (Play / Tinkering)
            </div>
            <div class="flashcard-prompt">Clique para virar ↻</div>
          </div>

          <div class="flashcard" onclick="this.classList.toggle('flipped')">
            <div>
              <span class="flashcard-tag">Semana 6 · Sincronização</span>
              <div class="flashcard-front">Como atores sincronizam suas falas e ações no Scratch?</div>
            </div>
            <div class="flashcard-back">
              Pela difusão de eventos: um ator roda <code>transmita [msg]</code> e o outro ativa seu script pelo chapéu <code>quando eu receber [msg]</code>.
            </div>
            <div class="flashcard-prompt">Clique para virar ↻</div>
          </div>
        </div>
      </section>

      <!-- SIMULADO INTERATIVO -->
      <section id="simulado-interativo">
        <div class="section-header">
          <div class="section-title">
            <span class="section-num">📝</span>
            <span>Simulado Interativo (Padrão Prova Presencial Univesp)</span>
          </div>
        </div>
        <p style="color: var(--text-muted); margin-bottom: 1.5rem;">
          Clique na alternativa para ver a correção imediata fundamentada na bibliografia da disciplina:
        </p>

        <!-- Questão 1 -->
        <div class="quiz-container" id="q1">
          <div class="quiz-header">
            <span class="quiz-badge">Questão 1 · Semana 3</span>
          </div>
          <div class="question-text">
            Um programador iniciante quer criar uma animação em que o ator dê passos continuamente pela tela até que o usuário pressione a barra de espaço do teclado para pausá-lo. Qual bloco de repetição implementa exatamente essa condição de término no Scratch?
          </div>
          <div class="options-list">
            <button class="option-btn" onclick="checkAnswer('q1', this, false, 'Incorreto. O bloco repita (10) vezes para após um número fixo de iterações, independentemente de teclas.')">
              <span class="option-letter">A</span>
              <span>repita (10) vezes</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q1', this, true, 'Correto! O bloco repita até que <tecla espaço pressionada?> repete o movimento enquanto a condição for FALSA e interrompe o laço assim que vira VERDADEIRA.')">
              <span class="option-letter">B</span>
              <span>repita até que &lt;tecla [espaço] pressionada?&gt;</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q1', this, false, 'Incorreto. O bloco sempre roda em loop infinito sem checagem de parada embutida.')">
              <span class="option-letter">C</span>
              <span>sempre</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q1', this, false, 'Incorreto. O se ... então é uma estrutura de desvio condicional de passo único, não uma estrutura de repetição contínua.')">
              <span class="option-letter">D</span>
              <span>se &lt;tecla [espaço] pressionada?&gt; então</span>
            </button>
          </div>
          <div class="quiz-feedback" id="q1-fb"></div>
        </div>

        <!-- Questão 2 -->
        <div class="quiz-container" id="q2">
          <div class="quiz-header">
            <span class="quiz-badge">Questão 2 · Semana 4</span>
          </div>
          <div class="question-text">
            Considere um programa no Scratch com dois blocos consecutivos:<br>
            1. <code>pergunte [Qual o seu nome?] e espere</code><br>
            2. <code>pergunte [Qual a sua profissão?] e espere</code><br>
            Se o usuário digitou "Josemar" na primeira pergunta e "Engenheiro" na segunda, o que conterá a variável do sistema <code>resposta</code> ao final da execução se nenhuma outra variável foi criada?
          </div>
          <div class="options-list">
            <button class="option-btn" onclick="checkAnswer('q2', this, false, 'Incorreto. O Scratch não concatena entradas de forma automática.')">
              <span class="option-letter">A</span>
              <span>"Josemar Engenheiro"</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q2', this, true, 'Correto! A cada novo comando de pergunta, o conteúdo anterior da variável de sistema \'resposta\' é inteiramente sobrescrito pelo novo valor fornecido.')">
              <span class="option-letter">B</span>
              <span>Apenas "Engenheiro", pois o valor anterior foi sobrescrito</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q2', this, false, 'Incorreto. A variável resposta é do tipo string simples, não é convertida em lista automaticamente.')">
              <span class="option-letter">C</span>
              <span>Uma lista contendo os dois valores salvos</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q2', this, false, 'Incorreto. O Scratch não trava com perguntas consecutivas.')">
              <span class="option-letter">D</span>
              <span>O programa gerará um erro de memória</span>
            </button>
          </div>
          <div class="quiz-feedback" id="q2-fb"></div>
        </div>

        <!-- Questão 3 -->
        <div class="quiz-container" id="q3">
          <div class="quiz-header">
            <span class="quiz-badge">Questão 3 · Semana 5</span>
          </div>
          <div class="question-text">
            Em sua obra sobre Aprendizagem Criativa, Mitchel Resnick elenca quatro pilares fundamentais (os 4Ps). Dentre eles, o pilar do "Pensar Brincando" (<em>Play / Tinkering</em>) caracteriza-se pedagogicamente por:
          </div>
          <div class="options-list">
            <button class="option-btn" onclick="checkAnswer('q3', this, false, 'Incorreto. Resnick combate a memorização passiva e a reprodução de manuais fixos.')">
              <span class="option-letter">A</span>
              <span>Memorização de sintaxes e reprodução rígida de manuais passo a passo</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q3', this, true, 'Correto! Pensar brincando estimula a bricolagem (tinkering), a experimentação sem receio de errar e o aprendizado pela exploração ativa.')">
              <span class="option-letter">B</span>
              <span>Postura de experimentação lúdica (tinkering), tomada de riscos e visão do erro como oportunidade de descoberta</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q3', this, false, 'Incorreto. Gamificação competitiva não é o núcleo do Play em Resnick.')">
              <span class="option-letter">C</span>
              <span>Disputa competitiva entre os alunos com atribuição de notas por velocidade</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q3', this, false, 'Incorreto. O trabalho individual isolado contraria a filosofia construcionista e o pilar de Pares.')">
              <span class="option-letter">D</span>
              <span>Isolamento individual estrito do estudante para evitar distrações</span>
            </button>
          </div>
          <div class="quiz-feedback" id="q3-fb"></div>
        </div>

        <!-- Questão 4 -->
        <div class="quiz-container" id="q4">
          <div class="quiz-header">
            <span class="quiz-badge">Questão 4 · Semana 5</span>
          </div>
          <div class="question-text">
            Ao projetar o Scratch, a equipe do MIT buscou atender ao princípio de "Paredes Largas" (<em>Wide Walls</em>). Na prática pedagógica, essa diretriz garante que:
          </div>
          <div class="options-list">
            <button class="option-btn" onclick="checkAnswer('q4', this, true, 'Correto! Paredes Largas significa que a plataforma abraça projetos de tipos e interesses muito variados: jogos, animações, ciências, música, histórias interativas.')">
              <span class="option-letter">A</span>
              <span>A ferramenta apoie uma ampla diversidade de estilos e interesses, permitindo criar desde poemas visuais até jogos e simuladores científicos</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q4', this, false, 'Incorreto. Isso diz respeito à interface gráfica ou hardware, não à pedagogia das Paredes Largas.')">
              <span class="option-letter">B</span>
              <span>O software só possa ser utilizado em monitores amplos widescreen</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q4', this, false, 'Incorreto. Isso é o conceito de Piso Baixo (Low Floor).')">
              <span class="option-letter">C</span>
              <span>O programa tenha facilidade de entrada para iniciantes sem conhecimento prévio</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q4', this, false, 'Incorreto. Isso é o conceito de Teto Alto (High Ceiling).')">
              <span class="option-letter">D</span>
              <span>A plataforma permita o desenvolvimento de códigos de alta complexidade matemática</span>
            </button>
          </div>
          <div class="quiz-feedback" id="q4-fb"></div>
        </div>

        <!-- Questão 5 -->
        <div class="quiz-container" id="q5">
          <div class="quiz-header">
            <span class="quiz-badge">Questão 5 · Semana 6</span>
          </div>
          <div class="question-text">
            Para coordenar uma cena em que o Ator 1 termina de falar e, logo em seguida, o Ator 2 inicia a sua fala e o cenário de fundo muda, qual é o mecanismo nativo ideal do Scratch?
          </div>
          <div class="options-list">
            <button class="option-btn" onclick="checkAnswer('q5', this, false, 'Incorreto. O bloco repita não faz comunicação entre diferentes atores.')">
              <span class="option-letter">A</span>
              <span>Utilizar o bloco repita (10) vezes dentro do Ator 2</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q5', this, true, 'Correto! O Ator 1 emite um broadcast com \'transmita [mensagem]\', e o Ator 2 e o Palco disparam suas ações ao ouvirem \'quando eu receber [mensagem]\'.')">
              <span class="option-letter">B</span>
              <span>O Ator 1 usa \'transmita [mensagem]\', e o Ator 2 e o Palco ativam seus códigos via \'quando eu receber [mensagem]\'</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q5', this, false, 'Incorreto. Criar variáveis globais para sincronizar falas é uma solução desnecessariamente complexa.')">
              <span class="option-letter">C</span>
              <span>Criar uma variável local para cada ator e consultar em loop infinito</span>
            </button>
            <button class="option-btn" onclick="checkAnswer('q5', this, false, 'Incorreto. Pergunte e espere serve para digitação do usuário via teclado.')">
              <span class="option-letter">D</span>
              <span>Usar o bloco pergunte e espere em ambos os atores simultaneamente</span>
            </button>
          </div>
          <div class="quiz-feedback" id="q5-fb"></div>
        </div>
      </section>

      <!-- RESUMO RÁPIDO (COLA EM 2 MIN) -->
      <section id="resumo-rapido">
        <div class="section-header">
          <div class="section-title">
            <span class="section-num">📑</span>
            <span>Resumo de Bolso: A "Cola" dos Conceitos em 2 Minutos</span>
          </div>
        </div>

        <div class="card" style="background: linear-gradient(135deg, #1e293b, #0b1120); border-color: rgba(56, 189, 248, 0.3);">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem;">
            <div>
              <h4 style="color: var(--text-accent); margin-bottom: 0.5rem; font-size: 1rem;">🧩 Scratch & Lógica</h4>
              <ul style="font-size: 0.88rem; color: #cbd5e1; display: flex; flex-direction: column; gap: 6px; padding-left: 1.2rem;">
                <li><strong>Origem:</strong> MIT Media Lab (Resnick / Papert).</li>
                <li><strong>Foco:</strong> Semântica e lógica (elimina erros de sintaxe).</li>
                <li><strong>Palco:</strong> Centro em (0,0), X [-240, 240], Y [-180, 180].</li>
                <li><strong>Repita até que:</strong> Roda no FALSO, para no VERDADEIRO.</li>
                <li><strong>Resposta:</strong> Sobrescrita a cada novo pergunte.</li>
                <li><strong>Broadcast:</strong> <code>transmita</code> e <code>quando receber</code> para sincronizar atores.</li>
              </ul>
            </div>

            <div>
              <h4 style="color: #c084fc; margin-bottom: 0.5rem; font-size: 1rem;">💡 Aprendizagem Criativa</h4>
              <ul style="font-size: 0.88rem; color: #cbd5e1; display: flex; flex-direction: column; gap: 6px; padding-left: 1.2rem;">
                <li><strong>4Ps:</strong> Projetos, Paixão, Pares e Pensar Brincando (Play).</li>
                <li><strong>Espiral:</strong> Imaginar ➔ Criar ➔ Brincar ➔ Compartilhar ➔ Refletir ➔ Imaginar.</li>
                <li><strong>Piso Baixo:</strong> Fácil para iniciantes entrarem.</li>
                <li><strong>Teto Alto:</strong> Permite criar projetos complexos.</li>
                <li><strong>Paredes Largas:</strong> Abraça múltiplos estilos e interesses.</li>
                <li><strong>Remix:</strong> Aprender pelo código aberto dando créditos.</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

    </main>
  </div>

  <script>
    window.addEventListener('scroll', () => {{
      const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
      const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const scrolled = (winScroll / height) * 100;
      document.getElementById('progress-bar').style.width = scrolled + '%';
    }});

    const sections = document.querySelectorAll('section, header');
    const navLinks = document.querySelectorAll('.nav-item a');

    window.addEventListener('scroll', () => {{
      let current = '';
      sections.forEach(section => {{
        const sectionTop = section.offsetTop - 120;
        if (pageYOffset >= sectionTop) {{
          current = section.getAttribute('id');
        }}
      }});

      navLinks.forEach(link => {{
        link.classList.remove('active');
        if (link.getAttribute('href') === '#' + current) {{
          link.classList.add('active');
        }}
      }});
    }});

    function checkAnswer(questionId, btn, isCorrect, feedbackText) {{
      const container = document.getElementById(questionId);
      const buttons = container.querySelectorAll('.option-btn');
      const feedback = document.getElementById(questionId + '-fb');

      buttons.forEach(b => {{
        b.style.pointerEvents = 'none';
        b.classList.remove('correct', 'incorrect');
      }});

      if (isCorrect) {{
        btn.classList.add('correct');
        feedback.className = 'quiz-feedback show correct-feedback';
        feedback.innerHTML = '<strong>Acertou! 🎉</strong> ' + feedbackText;
      }} else {{
        btn.classList.add('incorrect');
        buttons.forEach(b => {{
          if (b.getAttribute('onclick').includes('true')) {{
            b.classList.add('correct');
          }}
        }});
        feedback.className = 'quiz-feedback show incorrect-feedback';
        feedback.innerHTML = '<strong>Ops! Atenção:</strong> ' + feedbackText;
      }}
    }}
  </script>
</body>
</html>
'''

    dest_repo = root / "2026-3bim" / "com100" / "apostila_scratch_interativa.html"
    with open(dest_repo, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Salvo no repositorio: {dest_repo} ({len(html_content)} chars)")

    # Copia para Downloads do usuario
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        dest_downloads = Path(user_profile) / "Downloads" / "apostila_scratch_interativa.html"
        shutil.copyfile(dest_repo, dest_downloads)
        print(f"Copiado para Downloads: {dest_downloads}")

if __name__ == "__main__":
    main()
