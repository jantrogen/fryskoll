import os
from datetime import date
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from google import genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

# Starta Gemini-klienten (hämtar GEMINI_API_KEY automatiskt från Render)
ai_client = genai.Client()

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL saknas! Appen är inte kopplad till PostgreSQL.")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

# Skapa databastabell om den inte finns
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS varor (
            id SERIAL PRIMARY KEY,
            namn TEXT NOT NULL,
            kategori TEXT NOT NULL,
            mangd TEXT NOT NULL,
            datum TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

class NyVara(BaseModel):
    namn: str
    kategori: str
    mangd: str
    datum: date

@app.get("/varor")
def hamta_varor():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, namn, kategori, mangd, datum FROM varor ORDER BY datum DESC")
    rader = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rader]

@app.post("/varor")
def lagg_till_vara(vara: NyVara):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO varor (namn, kategori, mangd, datum) VALUES (%s, %s, %s, %s) RETURNING id",
        (vara.namn, vara.kategori, vara.mangd, str(vara.datum))
    )
    nytt_id = cursor.fetchone()["id"]
    conn.commit()
    conn.close()
    return {"status": "ok", "id": nytt_id}

@app.delete("/varor/{vara_id}")
def ta_bort_vara(vara_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM varor WHERE id = %s", (vara_id,))
    conn.commit()
    conn.close()
    return {"status": "borttagen", "id": vara_id}

@app.get("/recept")
def slumpa_recept():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT namn, mangd FROM varor")
    varor = cursor.fetchall()
    conn.close()
    
    if not varor:
        return {"recept": "Din frys är helt tom! Lägg till lite varor först så kan jag föreslå ett recept."}

    varu_lista = ", ".join([f"{v['namn']} ({v['mangd']})" for v in varor])

    prompt = (
        f"Här är en lista på vad jag har i min frys just nu: {varu_lista}. "
        "Föreslå ett gott och inspirerande middagsrecept baserat huvudsakligen på dessa ingredienser. "
        "Skriv vad som används från frysen och ge en kort inköpslista på eventuella 1-3 basvaror som behövs till. "
        "Svara på svenska med tydlig struktur (t.ex. rubriker och punktlistor)."
    )

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        return {"recept": response.text}
    except Exception as e:
        return {"recept": f"Kunde inte generera recept just nu. Fel: {str(e)}"}

@app.get("/", response_class=HTMLResponse)
def ladda_sida():
    return """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Fryskoll">
    <link rel="apple-touch-icon" href="https://fav.farm/❄️">
    <link rel="icon" href="https://fav.farm/❄️">
    
    <title>❄️ Fryskoll</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --ai-btn: #7c3aed;
            --ai-btn-hover: #6d28d9;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --danger-bg: #fef2f2;
            --danger-text: #ef4444;
        }

        * { box-sizing: border-box; }
        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background-color: var(--bg); 
            margin: 0; 
            padding: 24px 16px; 
            color: var(--text-main); 
            -webkit-tap-highlight-color: transparent;
        }

        .app-container { 
            max-width: 650px; 
            margin: 0 auto; 
        }

        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
        }
        h1 { 
            font-size: 26px; 
            font-weight: 700; 
            margin: 0; 
            display: flex; 
            align-items: center; 
            gap: 10px; 
            color: #1e293b;
        }
        .stats-badge {
            background: #dbeafe;
            color: #1e40af;
            font-weight: 700;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 14px;
        }

        .card { 
            background: var(--card-bg); 
            padding: 20px; 
            border-radius: 16px; 
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.05); 
            border: 1px solid var(--border);
            margin-bottom: 24px; 
        }
        .card-title {
            font-size: 16px;
            font-weight: 600;
            margin: 0 0 16px 0;
            color: #334155;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .form-full { grid-column: span 2; }

        label { display: block; font-weight: 600; margin-bottom: 6px; font-size: 13px; color: var(--text-muted); }
        input, select { 
            width: 100%; 
            padding: 10px 14px; 
            border: 1px solid var(--border); 
            border-radius: 10px; 
            font-size: 15px; 
            font-family: inherit;
            background: #f8fafc;
            transition: all 0.2s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: var(--primary);
            background: #fff;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
        }

        .btn-add { 
            width: 100%; 
            background-color: var(--primary); 
            color: white; 
            border: none; 
            padding: 12px; 
            font-size: 15px; 
            font-weight: 600; 
            border-radius: 10px; 
            cursor: pointer; 
            margin-top: 16px; 
            transition: background 0.2s;
        }
        .btn-add:hover { background-color: var(--primary-hover); }

        .btn-ai {
            width: 100%;
            background-color: var(--ai-btn);
            color: white;
            border: none;
            padding: 12px;
            font-size: 15px;
            font-weight: 600;
            border-radius: 10px;
            cursor: pointer;
            margin-bottom: 24px;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .btn-ai:hover { background-color: var(--ai-btn-hover); }

        .ai-result-box {
            background: #faf5ff;
            border: 1px solid #e9d5ff;
            padding: 16px;
            border-radius: 14px;
            margin-bottom: 24px;
            white-space: pre-line;
            line-height: 1.5;
            font-size: 14px;
            color: #3b0764;
            display: none;
        }

        .search-bar {
            margin-bottom: 16px;
        }

        .item-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
        .item-card { 
            background: var(--card-bg); 
            border: 1px solid var(--border); 
            padding: 16px; 
            border-radius: 14px; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            transition: transform 0.1s, box-shadow 0.1s;
        }

        .item-main { display: flex; align-items: center; gap: 14px; }
        .icon-box {
            width: 44px;
            height: 44px;
            background: #f1f5f9;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            flex-shrink: 0;
        }

        .item-title { font-weight: 600; font-size: 16px; color: var(--text-main); margin-bottom: 2px; }
        .item-meta { display: flex; gap: 10px; align-items: center; font-size: 13px; color: var(--text-muted); flex-wrap: wrap; }
        
        .badge {
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 6px;
        }
        .badge-farsk { background: #dcfce7; color: #15803d; }
        .badge-ok { background: #fef9c3; color: #a16207; }
        .badge-gammal { background: #fee2e2; color: #b91c1c; }

        .btn-delete { 
            background-color: var(--danger-bg); 
            color: var(--danger-text); 
            border: 1px solid #fca5a5; 
            padding: 8px 12px; 
            border-radius: 8px; 
            font-weight: 600; 
            cursor: pointer; 
            font-size: 13px; 
            transition: all 0.2s;
            flex-shrink: 0;
        }

        @media (max-width: 480px) {
            .form-grid { grid-template-columns: 1fr; }
            .form-full { grid-column: span 1; }
        }
    </style>
</head>
<body>

<div class="app-container">
    <header>
        <h1>❄️ Fryskoll</h1>
        <div class="stats-badge"><span id="antal-varor">0</span> i frysen</div>
    </header>

    <button class="btn-ai" onclick="hamtaRecept()">🤖 Föreslå middag med AI</button>
    <div id="ai-result" class="ai-result-box"></div>

    <div class="card">
        <h2 class="card-title">＋ Lägg till ny vara</h2>
        <div class="form-grid">
            <div class="form-full">
                <label>VARA</label>
                <input type="text" id="namn" placeholder="t.ex. Kycklingfilé, Ärtor...">
            </div>
            <div>
                <label>KATEGORI</label>
                <select id="kategori">
                    <option value="Kött">🥩 Kött</option>
                    <option value="Fisk">🐟 Fisk & Skaldjur</option>
                    <option value="Grönsaker">🥦 Grönsaker & Bär</option>
                    <option value="Färdigmat">🍲 Färdigmat / Lådor</option>
                    <option value="Bröd">🍞 Bröd & Bakat</option>
                    <option value="Övrigt">📦 Övrigt</option>
                </select>
            </div>
            <div>
                <label>MÄNGD / VIKT</label>
                <input type="text" id="mangd" placeholder="t.ex. 500g, 2 st">
            </div>
            <div class="form-full">
                <label>INFRYSNINGSDATUM</label>
                <input type="date" id="datum">
            </div>
        </div>
        <button class="btn-add" onclick="laggTillVara()">Spara i frysen</button>
    </div>

    <div class="search-bar">
        <input type="text" id="sok" placeholder="🔍 Sök i frysen..." oninput="laddaFrysen()">
    </div>

    <ul class="item-list" id="frys-lista"></ul>
</div>

<script>
    document.getElementById('datum').valueAsDate = new Date();

    const ikoner = {
        'Kött': '🥩',
        'Fisk': '🐟',
        'Grönsaker': '🥦',
        'Färdigmat': '🍲',
        'Bröd': '🍞',
        'Övrigt': '📦'
    };

    function beraknaStatus(datumStr) {
        const frysDatum = new Date(datumStr);
        const idag = new Date();
        const diffMader = (idag - frysDatum) / (1000 * 60 * 60 * 24 * 30);

        if (diffMader < 2) return { text: 'Nyligen infryst', class: 'badge-farsk' };
        if (diffMader < 6) return { text: 'Okej ålder', class: 'badge-ok' };
        return { text: 'Ät snart!', class: 'badge-gammal' };
    }

    async function hamtaRecept() {
        const box = document.getElementById('ai-result');
        box.style.display = 'block';
        box.innerHTML = '🍳 AI funderar ut ett gott recept baserat på din frys...';
        
        try {
            const res = await fetch('/recept');
            const data = await res.json();
            box.innerHTML = `<strong>✨ Receptförslag:</strong><br><br>` + data.recept;
        } catch (err) {
            box.innerHTML = 'Kunde inte hämta recept just nu. Försök igen!';
        }
    }

    async function laddaFrysen() {
        const res = await fetch('/varor');
        let varor = await res.json();
        
        const sokOrd = document.getElementById('sok').value.toLowerCase();
        if (sokOrd) {
            varor = varor.filter(v => 
                v.namn.toLowerCase().includes(sokOrd) || 
                v.kategori.toLowerCase().includes(sokOrd)
            );
        }

        const lista = document.getElementById('frys-lista');
        document.getElementById('antal-varor').innerText = varor.length;
        lista.innerHTML = '';

        if (varor.length === 0) {
            lista.innerHTML = `
                <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                    <div style="font-size: 32px; margin-bottom: 8px;">🍦</div>
                    Inga varor hittades i frysen.
                </div>
            `;
            return;
        }

        varor.forEach(v => {
            const ikon = ikoner[v.kategori] || '📦';
            const status = beraknaStatus(v.datum);

            lista.innerHTML += `
                <li class="item-card">
                    <div class="item-main">
                        <div class="icon-box">${ikon}</div>
                        <div>
                            <div class="item-title">${v.namn}</div>
                            <div class="item-meta">
                                <span>📦 ${v.mangd}</span>
                                <span>•</span>
                                <span>📅 ${v.datum}</span>
                                <span class="badge ${status.class}">${status.text}</span>
                            </div>
                        </div>
                    </div>
                    <button class="btn-delete" onclick="taBortVara(${v.id})">Ätit upp</button>
                </li>
            `;
        });
    }

    async function laggTillVara() {
        const namn = document.getElementById('namn').value;
        const kategori = document.getElementById('kategori').value;
        const mangd = document.getElementById('mangd').value;
        const datum = document.getElementById('datum').value;

        if (!namn || !mangd || !datum) {
            alert('Fyll i alla fält!');
            return;
        }

        await fetch('/varor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ namn, kategori, mangd, datum })
        });

        document.getElementById('namn').value = '';
        document.getElementById('mangd').value = '';
        laddaFrysen();
    }

    async function taBortVara(id) {
        await fetch(`/varor/${id}`, { method: 'DELETE' });
        laddaFrysen();
    }

    laddaFrysen();
</script>

</body>
</html>
    """