"""ReDesign AI — redesenha um cômodo a partir de uma foto, preservando a estrutura."""

import base64
import io
import os
import time

import requests
import streamlit as st
from PIL import Image

# AI Horde: rede comunitária e gratuita de GPUs (https://aihorde.net).
API_HORDE = "https://stablehorde.net/api/v2"
# Modelos realistas preferidos; a rede usa o primeiro disponível.
MODELOS = [
    "ICBINP - I Can't Believe It's Not Photography",
    "Deliberate",
    "stable_diffusion",
]
# Máx. 576 mantém o request dentro do limite gratuito/anônimo da AI Horde
# (acima de 576x576 a rede exige "kudos", que contas novas/anônimas não têm).
LADO_MAX = 576   # maior lado da imagem enviada (arredondado p/ múltiplo de 64)
ESPERA_MAX = 360  # tempo máximo (s) aguardando a fila

# Estilos predefinidos (conceitos modernos). Nome exibido -> descrição (em inglês).
ESTILOS = {
    "Japandi": (
        "Japandi style, blend of Japanese minimalism and Scandinavian warmth, "
        "low natural-wood furniture, calm neutral palette, clean lines, soft diffuse lighting"
    ),
    "Minimalismo quente": (
        "warm minimalism, few high-quality pieces, warm earthy neutral tones "
        "(beige, taupe, terracotta), soft natural textures, uncluttered, cozy"
    ),
    "Escandinavo": (
        "modern Scandinavian, light woods, white and soft-grey walls, functional "
        "furniture, hygge coziness, wool and linen textiles, plenty of plants"
    ),
    "Boho moderno": (
        "modern boho, layered textiles and rugs, rattan and cane furniture, lots of "
        "plants, warm earthy tones, eclectic handcrafted decor, macramé accents"
    ),
    "Industrial moderno": (
        "modern industrial, exposed brick and concrete accents, black metal and "
        "reclaimed wood, dark moody palette, Edison-bulb lighting"
    ),
    "Mid-century modern": (
        "mid-century modern, tapered-leg furniture, warm walnut wood, retro silhouettes, "
        "bold accent colors (mustard, teal, burnt orange), sleek and uncluttered"
    ),
    "Orgânico / Biofílico": (
        "biophilic organic design, abundant indoor plants, natural materials (wood, "
        "stone, jute), earthy organic palette, natural light, fresh and airy"
    ),
    "Maximalista": (
        "modern maximalism, bold saturated colors, rich patterns, layered decor, "
        "gallery walls, statement furniture, curated and harmonious"
    ),
    "Contemporâneo": (
        "contemporary design, sleek and sophisticated, neutral base with bold accents, "
        "clean lines, mix of textures, refined and elegant"
    ),
    "Coastal moderno": (
        "modern coastal, light blues, whites and sandy tones, breezy linen textiles, "
        "natural light, relaxed beachy feel, rattan and light-wood furniture"
    ),
}

# Descrição-base sempre aplicada (estilo Stable Diffusion). A preservação da
# estrutura (paredes/janelas/portas) vem do método img2img, não do texto.
PROMPT_BASE = (
    "interior design photo of a beautifully redesigned room, photorealistic, "
    "professional, cohesive decor, well lit, high quality, detailed"
)
NEGATIVO = (
    "blurry, low quality, distorted, deformed, watermark, text, messy, "
    "cluttered, ugly, bad proportions"
)
# Usada quando o usuário não escolhe estilo nem digita instruções.
DIRECAO_PADRAO = (
    "modern cozy contemporary style, warm neutral palette, quality furniture, "
    "plants, layered inviting lighting"
)


def obter_chave() -> str:
    """Chave da AI Horde; cai para a anônima (0000000000) se nada for configurado."""
    return st.secrets.get(
        "AIHORDE_API_KEY", os.environ.get("AIHORDE_API_KEY", "0000000000")
    )


def montar_prompt(estilo: str | None, instrucoes: str) -> str:
    """Combina a base + estilo + instruções num prompt descritivo (com negativo)."""
    instrucoes = (instrucoes or "").strip()
    tem_estilo = bool(estilo and estilo in ESTILOS)
    partes = [PROMPT_BASE]
    if tem_estilo:
        partes.append(ESTILOS[estilo])
    if instrucoes:
        partes.append(instrucoes)
    if not tem_estilo and not instrucoes:
        partes.append(DIRECAO_PADRAO)
    return ", ".join(partes) + " ### " + NEGATIVO


def _preparar_imagem(imagem_bytes: bytes) -> tuple[str, int, int]:
    """Redimensiona (múltiplo de 64, máx. LADO_MAX) e devolve base64 WebP + dimensões."""
    img = Image.open(io.BytesIO(imagem_bytes)).convert("RGB")
    largura, altura = img.size
    escala = min(1.0, LADO_MAX / max(largura, altura))
    nova_l = max(64, (round(largura * escala) // 64) * 64)
    nova_a = max(64, (round(altura * escala) // 64) * 64)
    img = img.resize((nova_l, nova_a))
    buffer = io.BytesIO()
    img.save(buffer, format="WEBP", quality=90)
    return base64.b64encode(buffer.getvalue()).decode(), nova_l, nova_a


def _mensagem_erro(resposta: requests.Response) -> str:
    try:
        msg = resposta.json().get("message", resposta.text)
    except ValueError:
        msg = resposta.text
    if resposta.status_code == 401:
        return "Chave da AI Horde inválida. Confira o AIHORDE_API_KEY."
    if resposta.status_code == 429:
        return "Muitas requisições na AI Horde agora. Aguarde alguns segundos e tente de novo."
    return f"Erro da AI Horde ({resposta.status_code}): {msg}"


def redesenhar(chave: str, imagem_bytes: bytes, prompt: str, atualizar=None) -> bytes:
    """Faz o img2img na AI Horde (assíncrono + polling) e retorna os bytes PNG."""
    src_b64, largura, altura = _preparar_imagem(imagem_bytes)
    headers = {"apikey": chave, "Client-Agent": "redesign-ai:1.0:streamlit"}
    payload = {
        "prompt": prompt,
        "source_image": src_b64,
        "source_processing": "img2img",
        "params": {
            "denoising_strength": 0.6,  # mantém o layout e restiliza o ambiente
            "steps": 28,
            "cfg_scale": 7.0,
            "sampler_name": "k_euler_a",
            "width": largura,
            "height": altura,
            "n": 1,
        },
        "models": MODELOS,
    }

    resp = requests.post(
        f"{API_HORDE}/generate/async", json=payload, headers=headers, timeout=30
    )
    if resp.status_code != 202:
        raise RuntimeError(_mensagem_erro(resp))
    job_id = resp.json()["id"]

    inicio = time.time()
    while time.time() - inicio < ESPERA_MAX:
        time.sleep(5)
        check = requests.get(
            f"{API_HORDE}/generate/check/{job_id}", headers=headers, timeout=30
        ).json()
        if check.get("faulted"):
            raise RuntimeError("A geração falhou na rede AI Horde. Tente novamente.")
        if check.get("done"):
            break
        if atualizar:
            atualizar(
                f"Na fila da AI Horde… posição {check.get('queue_position', 0)}, "
                f"~{check.get('wait_time', 0)}s restantes"
            )
    else:
        requests.delete(
            f"{API_HORDE}/generate/status/{job_id}", headers=headers, timeout=10
        )
        raise TimeoutError(
            "A fila da AI Horde está demorando demais agora. Tente novamente em "
            "instantes (uma chave própria da Horde dá mais prioridade)."
        )

    status = requests.get(
        f"{API_HORDE}/generate/status/{job_id}", headers=headers, timeout=30
    ).json()
    geracoes = status.get("generations") or []
    if not geracoes:
        raise RuntimeError("A AI Horde não retornou nenhuma imagem. Tente novamente.")

    ref = geracoes[0]["img"]
    dados = (
        requests.get(ref, timeout=60).content
        if ref.startswith("http")
        else base64.b64decode(ref)
    )
    img = Image.open(io.BytesIO(dados)).convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def gerar_e_guardar(chave: str) -> None:
    foto = st.session_state.get("foto_original")
    if foto is None:
        st.warning("Envie ou tire uma foto do cômodo primeiro.")
        return

    prompt = montar_prompt(
        st.session_state.get("estilo_sel"),
        st.session_state.get("instrucoes", ""),
    )

    try:
        with st.status("Enviando para a AI Horde…") as status:
            resultado = redesenhar(
                chave, foto, prompt, atualizar=lambda m: status.update(label=m)
            )
            status.update(label="Imagem gerada!", state="complete")
    except Exception as exc:  # noqa: BLE001 - exibe qualquer erro ao usuário
        st.error(f"Erro ao gerar a imagem: {exc}")
        return

    st.session_state.resultado = resultado


def main() -> None:
    st.set_page_config(page_title="ReDesign AI", page_icon="🛋️", layout="wide")
    st.title("🛋️ ReDesign AI")
    st.caption(
        "Fotografe um cômodo, descreva o estilo desejado e receba o mesmo ambiente "
        "redesenhado por IA — mantendo paredes, janelas e portas no lugar."
    )

    st.subheader("1. Foto do cômodo")
    col_cam, col_up = st.columns(2)
    with col_cam:
        foto_camera = st.camera_input("Tire uma foto")
    with col_up:
        foto_upload = st.file_uploader(
            "Ou envie uma foto", type=["jpg", "jpeg", "png"]
        )
    foto = foto_camera or foto_upload

    if foto is not None:
        st.session_state.foto_original = foto.getvalue()
        # Nova foto invalida o resultado anterior.
        if foto.getvalue() != st.session_state.get("_ultima_foto"):
            st.session_state.resultado = None
            st.session_state._ultima_foto = foto.getvalue()

    st.subheader("2. Estilo (atalho opcional)")
    try:
        estilo_sel = st.pills(
            "Escolha um estilo",
            options=list(ESTILOS.keys()),
            selection_mode="single",
            label_visibility="collapsed",
        )
    except AttributeError:
        # Streamlit sem st.pills: usa radio horizontal.
        estilo_sel = st.radio(
            "Escolha um estilo",
            options=[None, *ESTILOS.keys()],
            horizontal=True,
            format_func=lambda x: "Nenhum" if x is None else x,
            label_visibility="collapsed",
        )
    st.session_state.estilo_sel = estilo_sel

    st.subheader("3. Instruções")
    st.session_state.instrucoes = st.text_area(
        "Descreva suas preferências",
        placeholder="Ex.: tons neutros, sofá cinza, mais plantas, iluminação aconchegante",
        label_visibility="collapsed",
    )
    st.caption(
        "ℹ️ Uma descrição-base de redesenho é sempre aplicada e a estrutura "
        "(paredes, janelas e portas) é preservada pelo método img2img. O estilo e o "
        "texto acima são somados. Sem nada preenchido, usa-se um estilo contemporâneo padrão."
    )

    if st.button("✨ Gerar projeto", type="primary", use_container_width=True):
        if st.session_state.get("foto_original") is None:
            st.warning("Envie ou tire uma foto do cômodo primeiro.")
        else:
            gerar_e_guardar(obter_chave())

    resultado = st.session_state.get("resultado")
    if resultado:
        st.divider()
        st.subheader("Antes e depois")
        col_antes, col_depois = st.columns(2)
        with col_antes:
            st.markdown("**Original**")
            st.image(st.session_state.foto_original, use_container_width=True)
        with col_depois:
            st.markdown("**Redesenhado**")
            st.image(resultado, use_container_width=True)

        col_dl, col_var = st.columns(2)
        with col_dl:
            st.download_button(
                "⬇️ Baixar imagem",
                data=resultado,
                file_name="redesign-ai.png",
                mime="image/png",
                use_container_width=True,
            )
        with col_var:
            if st.button("🔁 Gerar nova variação", use_container_width=True):
                gerar_e_guardar(obter_chave())
                st.rerun()


if __name__ == "__main__":
    main()
