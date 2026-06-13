# 🛋️ ReDesign AI

App web que redesenha um cômodo a partir de uma foto. O usuário envia (ou tira)
uma foto do ambiente, escolhe um estilo e descreve suas preferências — a IA
devolve o **mesmo cômodo redesenhado**, preservando a estrutura (paredes,
janelas, portas, perspectiva) e alterando apenas móveis, cores, decoração e
iluminação.

Feito com [Streamlit](https://streamlit.io/) e a [AI Horde](https://aihorde.net/),
uma rede comunitária e **gratuita** de GPUs. O redesenho usa **img2img** com
Stable Diffusion: a estrutura do cômodo é preservada e o estilo/decoração são
transformados conforme o pedido.

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

2. Pegue uma chave gratuita da AI Horde em
   [aihorde.net/register](https://aihorde.net/register) (login com Google/Discord/
   GitHub). Uma chave própria dá mais prioridade na fila. Você também pode usar a
   chave anônima `0000000000` (mais lenta).

3. Configure a chave: copie o arquivo de exemplo e preencha:

   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

   Edite `.streamlit/secrets.toml` e coloque seu `AIHORDE_API_KEY`.
   (Alternativa: defina a variável de ambiente `AIHORDE_API_KEY`.)

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
- Por ser uma rede comunitária gratuita, a AI Horde tem **fila**: a geração pode
  levar de alguns segundos a alguns minutos, dependendo da demanda e da prioridade
  da sua chave.
- A intensidade da transformação é controlada por `denoising_strength` em
  [`app.py`](app.py) (mais alto = muda mais, porém preserva menos a estrutura).
