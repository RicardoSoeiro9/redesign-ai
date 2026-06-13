# 🛋️ ReDesign AI

App web que redesenha um cômodo a partir de uma foto. O usuário envia (ou tira)
uma foto do ambiente, escolhe um estilo e descreve suas preferências — a IA
devolve o **mesmo cômodo redesenhado**, preservando a estrutura (paredes,
janelas, portas, perspectiva) e alterando apenas móveis, cores, decoração e
iluminação.

Feito com [Streamlit](https://streamlit.io/) e o modelo de edição de imagem
**FLUX.1 Kontext** (`black-forest-labs/FLUX.1-Kontext-dev`), executado pela
[Inference API gratuita da Hugging Face](https://huggingface.co/docs/inference-providers).
É um modelo de edição por instrução, que altera a imagem preservando a estrutura
da cena.

## Funcionalidades

- 📷 Upload ou captura de foto do cômodo (câmera ou galeria)
- 🎨 Filtro de estilos modernos (Japandi, Minimalismo quente, Escandinavo, Boho
  moderno, Industrial moderno, Mid-century, Biofílico, Maximalista,
  Contemporâneo, Coastal)
- ✍️ Campo de texto livre para instruções
- 🖼️ Comparação lado a lado: original × redesenhado
- ⬇️ Download da imagem gerada
- 🔁 Gerar novas variações do mesmo ambiente

## Como rodar

1. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

2. Crie um token gratuito da Hugging Face em
   [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   (tipo *Read* já basta).

3. Configure o token: copie o arquivo de exemplo e preencha:

   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

   Edite `.streamlit/secrets.toml` e coloque seu `HF_TOKEN`.
   (Alternativa: defina a variável de ambiente `HF_TOKEN`.)

4. Rode o app:

   ```bash
   streamlit run app.py
   ```

## Como adicionar/remover estilos

Edite o dicionário `ESTILOS` em [`app.py`](app.py). A chave é o nome exibido no
app e o valor é a descrição do estilo (em inglês) enviada ao modelo.

## Observações

- O arquivo `.streamlit/secrets.toml` é ignorado pelo Git — sua chave nunca é
  versionada.
- A qualidade do resultado depende da clareza da foto e das instruções.
