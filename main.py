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
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Vi lägger till en kolumn 'frys_id' i tabellen
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
    cursor.execute("SELECT * FROM varor WHERE frys_id = %s ORDER BY datum DESC", (frys_id,))
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
    if data.get("mangd") == "0":
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
    <title>❄️ Fryskoll</title>
    <style>
        body { font-family: sans-serif; background: #f8fafc; padding: 20px; }
        .app-container { max-width: 500px; margin: 0 auto; }
        #inlogg-skarm { text-align: center; margin-top: 50px; }
    </style>
</head>
<body>
<div class="app-container">
    <div id="inlogg-skarm">
        <h1>Välkommen till Fryskoll</h1>
        <input type="text" id="frys-id-input" placeholder="Ange namn på din frys...">
        <button onclick="startaFrys()">Gå till min frys</button>
    </div>
    
    <div id="frys-app" style="display:none;">
        <h1 id="frys-namn-rubrik"></h1>
        <!-- Resten av din HTML här -->
        <input type="text" id="namn" placeholder="Vara...">
        <select id="kategori">
            <option value="Kött">🥩 Kött</option>
            <option value="Fisk">🐟 Fisk</option>
        </select>
        <input type="text" id="mangd" placeholder="Mängd...">
        <input type="date" id="datum">
        <button onclick="laggTillVara()">Spara</button>
        <ul id="frys-lista"></ul>
    </div>
</div>

<script>
    let aktuelltFrysId = localStorage.getItem('frys_id');

    function startaFrys() {
        const id = document.getElementById('frys-id-input').value;
        if(id) {
            localStorage.setItem('frys_id', id);
            aktuelltFrysId = id;
            location.reload();
        }
    }

    if(aktuelltFrysId) {
        document.getElementById('inlogg-skarm').style.display = 'none';
        document.getElementById('frys-app').style.display = 'block';
        document.getElementById('frys-namn-rubrik').innerText = "Frys: " + aktuelltFrysId;
        laddaFrysen();
    }

    async function laddaFrysen() {
        const res = await fetch('/varor/' + aktuelltFrysId);
        const data = await res.json();
        // ... rendera listan
    }
    
    // Uppdatera laggTillVara för att skicka med aktuelltFrysId
</script>
</body>
</html>
"""