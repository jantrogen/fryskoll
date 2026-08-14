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
            frys_id TEXT NOT NULL,
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
    frys_id: str
    namn: str
    kategori: str
    mangd: str
    datum: date

@app.get("/varor/{frys_id}")
def hamta_varor(frys_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, frys_id, namn, kategori, mangd, datum FROM varor WHERE frys_id = %s ORDER BY datum DESC", (frys_id,))
    rader = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rader]

@app.post("/varor")
def lagg_till_vara(vara: NyVara):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO varor (frys_id, namn, kategori, mangd, datum) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (vara.frys_id, vara.namn, vara.kategori, vara.mangd, str(vara.datum))
    )
    nytt_id = cursor.fetchone()["id"]
    conn.commit()
    conn.close()
    return {"status": "ok", "id": nytt_id}

@app.put("/varor/{vara_id}")
def uppdatera_vara(vara_id: int, data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
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
        .item-main { display: flex; align-items: center; gap: 12px; }
        .icon-box { width: 40px; height: 40px; background: #f1f5f9; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .btn-edit { background: #f1f5f9; border: none; padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; }
        .ai-textarea { width: 100%; height: 120px; margin-bottom: 10px; display: none; padding: 10px; border: 1px solid #059669; border-radius: 8px; font-family: inherit; font-size: 13px; }
        .btn-copy { width: 100%; background: #059669; color: white; border: none; padding: 12px; border-radius: 10px; cursor: pointer; font-weight: 600; }
        input, select { width: 100%; padding: 10px; margin-bottom: 8px; border: 1px solid var(--border); border-radius: 8px; font-family: inherit; box-sizing: border-box; }
        #inlogg-skarm { background: #fff; padding: 30px; border-radius: 12px; border: 1px solid var(--border); text-align: center; margin-top: 50px; }
    </style>
</head>
<body>
<div class="app-container">
    
    <div id="inlogg-skarm">
        <h1 style="margin-top:0;">❄️ Fryskoll</h1>
        <p style="color:#64748b; margin-bottom:20px;">Ange ett namn på din frys för att komma igång (eller dela med familjen).</p>
        <input type="text" id="frys-id-input" placeholder="T.ex. Min-Frys eller Stugan...">
        <button onclick="startaFrys()" style="width:100%; padding:12px; background:var(--primary); color:white; border:none; border-radius:8px; font-weight:600; cursor:pointer; margin-top:5px;">Öppna frysen</button>
    </div>
    
    <div id="frys-app" style="display:none;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h1 id="frys-namn-rubrik" style="margin:0;">❄️ Fryskoll</h1>
            <button onclick="bytFrys()" style="background:#f1f5f9; border:1px solid var(--border); padding:6px 12px; border-radius:6px; cursor:pointer; font-size:12px; font-weight:600;">Byt frys</button>
        </div>
        
        <div style="background: #ecfdf5; padding: 15px; border-radius: 12px; border: 1px solid #a7f3d0; margin-bottom: 20px;">
            <textarea id="ai-text-box" class="ai-textarea" readonly></textarea>
            <button class="btn-copy" onclick="kopieraInnehall()">Kopiera innehåll till AI</button>
        </div>
        
        <div style="background:#fff; padding:20px; border-radius:12px; border: 1px solid var(--border); margin-bottom:20px;">
            <h3 style="margin-top:0; margin-bottom: 12px;">+ Lägg till ny vara</h3>
            <input type="text" id="namn" placeholder="Vara (t.ex. Kyckling)...">
            <select id="kategori">
                <option value="Kött">🥩 Kött</option>
                <option value="Fisk">🐟 Fisk & Skaldjur</option>
                <option value="Grönsaker">🥦 Grönsaker & Bär</option>
                <option value="Färdigmat">🍲 Färdigmat / Lådor</option>
                <option value="Bröd">🍞 Bröd & Bakat</option>
                <option value="Övrigt">📦 Övrigt</option>
            </select>
            <input type="text" id="mangd" placeholder="Mängd / Vikt (t.ex. 500g)...">
            <input type="date" id="datum">
            <button onclick="laggTillVara()" style="width:100%; padding:12px; margin-top:5px; background:var(--primary); color:white; border:none; border-radius:8px; font-weight:600; cursor:pointer;">Spara i frysen</button>
        </div>

        <ul id="frys-lista" style="list-style:none; padding:0;"></ul>
    </div>

</div>

<script>
    document.getElementById('datum').valueAsDate = new Date();
    let globalaVaror = [];
    let aktuelltFrysId = localStorage.getItem('frys_id');

    const ikoner = {
        'Kött': '🥩',
        'Fisk': '🐟',
        'Grönsaker': '🥦',
        'Färdigmat': '🍲',
        'Bröd': '🍞',
        'Övrigt': '📦'
    };

    function startaFrys() {
        const id = document.getElementById('frys-id-input').value.trim();
        if(id) {
            localStorage.setItem('frys_id', id);
            location.reload();
        } else {
            alert('Skriv ett namn på frysen först!');
        }
    }

    function bytFrys() {
        localStorage.removeItem('frys_id');
        location.reload();
    }

    if(aktuelltFrysId) {
        document.getElementById('inlogg-skarm').style.display = 'none';
        document.getElementById('frys-app').style.display = 'block';
        document.getElementById('frys-namn-rubrik').innerText = "❄️ Fryskoll (" + aktuelltFrysId + ")";
        laddaFrysen();
    }

    async function laddaFrysen() {
        const res = await fetch('/varor/' + encodeURIComponent(aktuelltFrysId));
        globalaVaror = await res.json();
        const lista = document.getElementById('frys-lista');
        lista.innerHTML = '';
        
        if (globalaVaror.length === 0) {
            lista.innerHTML = '<div style="text-align:center; color:#64748b; padding:20px;">Frysen är tom!</div>';
            return;
        }

        globalaVaror.forEach(v => {
            const ikon = ikoner[v.kategori] || '📦';
            lista.innerHTML += `
                <li class="item-card">
                    <div class="item-main">
                        <div class="icon-box">${ikon}</div>
                        <div>
                            <strong>${v.namn}</strong><br>
                            <small style="color:#64748b;">${v.mangd} • ${v.datum}</small>
                        </div>
                    </div>
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
            frys_id: aktuelltFrysId,
            namn: document.getElementById('namn').value,
            kategori: document.getElementById('kategori').value,
            mangd: document.getElementById('mangd').value,
            datum: document.getElementById('datum').value
        };

        if (!data.namn || !data.mangd) {
            alert('Fyll i både vara och mängd!');
            return;
        }

        await fetch('/varor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        document.getElementById('namn').value = '';
        document.getElementById('mangd').value = '';
        document.getElementById('datum').valueAsDate = new Date();
        laddaFrysen();
    }

    async function kopieraInnehall() {
        let text = "Mina varor i frysen:\\n" + 
                   globalaVaror.map(v => `- ${v.namn}: ${v.mangd} (${v.kategori})`).join("\\n") + 
                   "\\n\\nFöreslå ett gott middagsrecept baserat huvudsakligen på dessa ingredienser!";
        
        const box = document.getElementById('ai-text-box');
        box.value = text;
        box.style.display = 'block';
        await navigator.clipboard.writeText(text);
        alert('Kopierat till urklipp!');
    }
</script>
</body>
</html>
"""