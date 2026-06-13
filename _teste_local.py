"""Teste local da chamada ao Gemini (nao versionado)."""

import sys
import tomllib
from pathlib import Path

from google import genai

import app  # reaproveita ESTILOS, montar_prompt, redesenhar

secrets = tomllib.loads(Path(".streamlit/secrets.toml").read_text(encoding="utf-8"))
cliente = genai.Client(api_key=secrets["GEMINI_API_KEY"])

print("1) Gerando foto-base de uma sala de estar...")
base = cliente.models.generate_content(
    model=app.MODELO,
    contents=[
        "A realistic photo of a plain, slightly outdated living room with a sofa, "
        "a window, a door and bare walls. Wide angle, well lit."
    ],
)
foto_bytes = None
for parte in base.candidates[0].content.parts:
    if getattr(parte, "inline_data", None) and parte.inline_data.data:
        foto_bytes = parte.inline_data.data
        break

if not foto_bytes:
    print("FALHA: modelo nao retornou a foto-base.")
    sys.exit(1)

Path("_original.png").write_bytes(foto_bytes)
print(f"   OK - foto-base salva ({len(foto_bytes)} bytes)")

print("2) Redesenhando no estilo Japandi...")
prompt = app.montar_prompt("Japandi", "mais plantas e iluminacao aconchegante")
resultado = app.redesenhar(cliente, foto_bytes, "image/png", prompt)
Path("_redesign.png").write_bytes(resultado)
print(f"   OK - imagem redesenhada salva ({len(resultado)} bytes)")
print("SUCESSO: pipeline completo funcionou.")
