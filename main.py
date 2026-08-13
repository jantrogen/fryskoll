import os
from datetime import date
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL saknas!")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

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

@app.put("/varor/{vara_id}")
def uppdatera_vara(vara_id: int, data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Om ny mängd är tom eller 0, radera, annars uppdatera
    if not data.get("mangd") or data["mangd"] == "0":
        cursor.execute("DELETE FROM varor WHERE id = %s", (vara_id,))
    else:
        cursor.execute("UPDATE varor SET mangd = %s WHERE id = %s", (data["mangd"], vara_id))
    conn.commit()
    conn.close()
    return {"status": "uppdaterad"}

@app.get("/", response_class=HTMLResponse)
def ladda_sida():
    return """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>❄️ Fryskoll</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #f8fafc; --primary: #2563eb; --text: #0f172a; --border: #e2e8f0; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: var(--bg); padding: 20px; color: var(--text); }
        .app-container { max-width: 600px; margin: 0 auto; }
        .item-card { background: #fff; padding: 16px; border-radius: 12px; border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .btn-edit { background: #f1f5f9; border: none; padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; }
        .ai-textarea { width: 100%; height: 100px; margin-bottom: 10px; display: none; padding: 10px; border: 1px solid #059669; border-radius: 8px; }
        .btn-copy { width: 100%; background: #059669; color: white; border: none; padding: 12px; border-radius: 10px; cursor: pointer; }
    </style>
</head>
<body>
<div class="app-container">
    <h1>❄️ Fryskoll</h1>
    <div style="background: #ecfdf5; padding: 15px; border-radius: 12px; margin-bottom: 20px;">
        <textarea id="ai-text-box" class="ai-textarea" readonly></textarea>
        <button class="btn-copy" onclick="kopieraInnehall()">Kopiera innehåll till AI</button>
    </div>
    
    <div style="background:#fff; padding:20px; border-radius:12px; margin-bottom:20px;">
        <input type="text" id="namn" placeholder="Vara..." style="width:100%; padding:8px; margin-bottom:5px;">
        <input type="text" id="mangd" placeholder="Mängd..." style="width:100%; padding:8px; margin-bottom:5px;">
        <input type="date" id="datum" style="width:100%; padding:8px;">
        <button onclick="laggTillVara()" style="width:100%; padding:10px; margin-top:10px; background:var(--primary); color:white; border:none; border-radius:8px;">Spara</button>
    </div>

    <ul id="frys-lista" style="list-style:none; padding:0;"></ul>
</div>

<script>
    document.getElementById('datum').valueAsDate = new Date();
    let globalaVaror = [];

    async function laddaFrysen() {
        const res = await fetch('/varor');
        globalaVaror = await res.json();
        const lista = document.getElementById('frys-lista');
        lista.innerHTML = '';
        globalaVaror.forEach(v => {
            lista.innerHTML += `
                <li class="item-card">
                    <div><strong>${v.namn}</strong><br><small>${v.mangd} • ${v.datum}</small></div>
                    <button class="btn-edit" onclick="redigeraVara(${v.id}, '${v.mangd}')">Ändra mängd</button>
                </li>
            `;
        });
    }

    async function redigeraVara(id, gammalMangd) {
        const nyMangd = prompt("Hur mycket finns kvar? (Skriv 0 för att ta bort)", gammalMangd);
        if (nyMangd !== null) {
            await fetch(`/varor/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mangd: nyMangd })
            });
            laddaFrysen();
        }
    }

    async function laggTillVara() {
        const data = {
            namn: document.getElementById('namn').value,
            kategori: 'Övrigt',
            mangd: document.getElementById('mangd').value,
            datum: document.getElementById('datum').value
        };
        await fetch('/varor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        laddaFrysen();
    }

    async function kopieraInnehall() {
        let text = "Mina varor i frysen:\\n" + globalaVaror.map(v => `- ${v.namn}: ${v.mangd}`).join("\\n");
        const box = document.getElementById('ai-text-box');
        box.value = text;
        box.style.display = 'block';
        await navigator.clipboard.writeText(text);
        alert('Kopierat!');
    }

    laddaFrysen();
</script>
</body>
</html>
"""