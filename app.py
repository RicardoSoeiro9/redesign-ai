"""ReDesign AI — redesenha um cômodo a partir de uma foto, preservando a estrutura."""

import io
import os

import streamlit as st
from huggingface_hub import InferenceClient

# Modelo gratuito de edição de imagem por instrução (preserva a estrutura da cena).
MODELO = "black-forest-labs/FLUX.1-Kontext-dev"

# Estilos predefinidos (conceitos modernos). Nome exibido -> fragmento de prompt
# em inglês (o modelo rende melhor com descrições de estilo em inglês).
ESTILOS = {
    "Japandi": (
        "Japandi style: blend of Japanese minimalism and Scandinavian warmth, "
        "low natural-wood furniture, calm neutral palette, clean lines, handcrafted "
        "ceramics, soft diffuse lighting"
    ),
    "Minimalismo quente": (
        "warm minimalism: few but high-quality pieces, warm earthy neutral tones "
        "(beige, taupe, terracotta), soft natural textures, uncluttered, cozy"
    ),
    "Escandinavo": (
        "modern Scandinavian: light woods, white and soft-grey walls, functional "
        "furniture, hygge coziness, wool and linen textiles, plenty of plants"
    ),
    "Boho moderno": (
        "modern boho: layered textiles and rugs, rattan and cane furniture, lots of "
        "plants, warm earthy tones, eclectic handcrafted decor, macramé accents"
    ),
    "Industrial moderno": (
        "modern industrial: exposed brick and concrete accents, black metal and "
        "reclaimed wood, dark moody palette, Edison-bulb and matte-black lighting"
    ),
    "Mid-century modern": (
        "mid-century modern: tapered-leg furniture, warm walnut wood, retro silhouettes, "
        "bold accent colors (mustard, teal, burnt orange), sleek and uncluttered"
    ),
    "Orgânico / Biofílico": (
        "biophilic organic design: abundant indoor plants, natural materials (wood, "
        "stone, jute), earthy organic palette, maximized natural light, fresh and airy"
    ),
    "Maximalista": (
        "modern maximalism: bold saturated colors, rich patterns, layered decor, "
        "gallery walls, statement furniture, eclectic but curated and harmonious"
    ),
    "Contemporâneo": (
        "contemporary design: sleek and sophisticated, neutral base with bold accents, "
        "current trends, clean lines, mix of textures, refined and elegant"
    ),
    "Coastal moderno": (
        "modern coastal: light blues, whites and sandy tones, breezy linen textiles, "
        "natural light, relaxed beachy feel, rattan and light-wood furniture"
    ),
}

INSTRUCAO_PRESERVACAO = (
    "You are an expert interior designer. Redesign the room shown in this photo. "
    "CRITICAL: keep the architecture identical — do not move or change the walls, "
    "windows, doors, ceiling, floor layout, room dimensions, camera angle or "
    "perspective. Only change the furniture, colors, materials, textiles, decoration, "
    "wall finishes and lighting. The result must look like the SAME room, "
    "photorealistic, professionally redesigned."
)


def obter_cliente() -> InferenceClient:
    token = st.secrets.get("HF_TOKEN", os.environ.get("HF_TOKEN"))
    if not token:
        st.error(
            "Token da Hugging Face não configurado. Crie um token gratuito em "
            "https://huggingface.co/settings/tokens, copie "
            "`.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` "
            "e preencha com seu token (HF_TOKEN)."
        )
        st.stop()
    return InferenceClient(token=token)


def montar_prompt(estilo: str | None, instrucoes: str) -> str:
    partes = [INSTRUCAO_PRESERVACAO]
    if estilo and estilo in ESTILOS:
        partes.append(f"Target style — {estilo}: {ESTILOS[estilo]}.")
    instrucoes = (instrucoes or "").strip()
    if instrucoes:
        partes.append(f"Additional user preferences: {instrucoes}.")
    partes.append("Output only the redesigned image.")
    return " ".join(partes)


def redesenhar(cliente: InferenceClient, imagem_bytes: bytes, prompt: str) -> bytes:
    """Envia a foto + prompt ao modelo de edição e retorna os bytes PNG da imagem."""
    imagem = cliente.image_to_image(imagem_bytes, prompt=prompt, model=MODELO)
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return buffer.getvalue()


def gerar_e_guardar(cliente: InferenceClient) -> None:
    foto = st.session_state.get("foto_original")
    if foto is None:
        st.warning("Envie ou tire uma foto do cômodo primeiro.")
        return

    prompt = montar_prompt(
        st.session_state.get("estilo_sel"),
        st.session_state.get("instrucoes", ""),
    )

    with st.spinner("Gerando o novo projeto do ambiente..."):
        try:
            resultado = redesenhar(cliente, foto, prompt)
        except Exception as exc:  # noqa: BLE001 - exibe qualquer erro de API ao usuário
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

    cliente_holder = {}

    if st.button("✨ Gerar projeto", type="primary", use_container_width=True):
        if st.session_state.get("foto_original") is None:
            st.warning("Envie ou tire uma foto do cômodo primeiro.")
        else:
            cliente_holder["c"] = obter_cliente()
            gerar_e_guardar(cliente_holder["c"])

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
                gerar_e_guardar(obter_cliente())
                st.rerun()


if __name__ == "__main__":
    main()
