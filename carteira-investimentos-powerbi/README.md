# Carteira de Investimentos — Power BI

Projeto **Power BI (PBIP)** gerado a partir da planilha `Estudo_aplicacao_2026_v2.xlsm`
(controle pessoal de carteira de investimentos). O modelo cobre a **carteira completa**:
evolução do valor de cada ativo ao longo do tempo, dimensões (tipo de ativo, indexador,
corretora, banco), posições de Ações/FIIs, cadastro de fundos e cenários de juros.

O projeto está no formato **PBIP** (arquivos de texto/TMDL + PBIR), versionável no Git e
aberto pelo **Power BI Desktop** (versão de 2024 em diante, com o formato PBIP habilitado).

## Como abrir no Power BI Desktop

1. Habilite o formato de projeto (uma vez):
   `Arquivo > Opções e configurações > Opções > Recursos de visualização` →
   marque **"Salvar arquivos do Power BI Desktop como Projeto (.pbip)"** e
   **"Armazenar o relatório usando o formato PBIR aprimorado"**. Reinicie o Power BI Desktop.
2. Abra o arquivo **`CarteiraInvestimentos.pbip`**.
3. Aponte o parâmetro com o caminho dos dados (passo abaixo) e clique em **Atualizar**.

## Apontar o parâmetro `PastaDados` (obrigatório)

Os dados são lidos dos CSVs da pasta [`data/`](data). O caminho é controlado pelo parâmetro
**`PastaDados`** (em `CarteiraInvestimentos.SemanticModel/definition/expressions.tmdl`),
que vem com um valor de exemplo (`C:\Projetos\carteira-investimentos-powerbi\data`).

No Power BI Desktop: **Página Inicial > Transformar dados > Gerenciar Parâmetros** →
defina `PastaDados` para o caminho **absoluto** da pasta `data` na sua máquina
(ex.: `C:\Users\voce\carteira-investimentos-powerbi\data`) → **Fechar e Aplicar**.

## Reprocessar a planilha

Sempre que a planilha for atualizada, gere os CSVs novamente (não precisa de bibliotecas
externas, apenas Python 3):

```bash
python scripts/extrair_dados.py "caminho/para/Estudo_aplicacao_2026_v2.xlsm"
```

Depois, no Power BI Desktop, clique em **Atualizar**.

## Modelo de dados (esquema estrela)

| Tabela | Papel | Origem |
| --- | --- | --- |
| **Fato_Valores** | Fato: valor de cada ativo por data (série histórica) | aba `Dados` (colunas de datas, *unpivot*) |
| **Dim_Ativo** | Dimensão: atributos de cada ativo | aba `Dados` (colunas A–O) |
| **Dim_Calendario** | Dimensão de datas (gerada em M) | 2024-01-01 a 2026-12-31 |
| **Fato_PosicoesAcoes** | Posições de Ações/FIIs (snapshot) | aba `ResumoAções` |
| **Dim_Fundos** | Cadastro de fundos (CNPJ, classificação, taxas) | aba `Fundos` |
| **JurosReal** | Cenários de juros (Pré/Pós/IPCA+) | aba `JurosReal` |
| **VolumeCorretora** | Volume por corretora | aba `Dados` (bloco resumo) |

**Relacionamentos:** `Fato_Valores[Ativo_ID] → Dim_Ativo[Ativo_ID]` e
`Fato_Valores[Data] → Dim_Calendario[Date]`.

### Medidas DAX já incluídas

Pasta **1 Carteira** (em `Fato_Valores`):
- `Valor na Data` — soma do valor (use com o eixo de datas para a evolução).
- `Patrimônio Atual` — patrimônio na data mais recente do filtro.
- `Patrimônio na Data Inicial`, `Variação Patrimônio (R$)`, `Variação Patrimônio (%)`.
- `Qtde de Ativos`.

Pasta **2 Ações e FIIs** (em `Fato_PosicoesAcoes`):
- `Investido (Ações/FII)`, `Atualizado (Ações/FII)`, `L/P (Ações/FII)`,
  `Rentabilidade (Ações/FII) %`, `Dividendos (Ações/FII)`, `Yield Médio (Ações/FII)`.

## Relatório

A página **"Visão Geral da Carteira"** já vem com: cartões (Patrimônio Atual, Variação,
L/P), evolução patrimonial (linha), alocação por tipo de ativo (rosca), patrimônio por
indexador (barras) e tabela de posições de Ações/FIIs.

> Observação: os visuais foram montados pelo formato PBIR. Caso algum não renderize na sua
> versão do Power BI Desktop, o **modelo e os dados carregam normalmente** — basta arrastar
> os campos/medidas acima para recriar o visual em segundos.

## Dicionário de dados (CSVs)

- **dim_ativo.csv** — `Ativo_ID, Tipo, Papel, SubTipo, Indexador, TaxaContratada, Fundo,
  DataCompra, Dias, Vencimento, Data2, AplicAtual, AplicInicial, Corretora, Categoria, Banco`
- **fato_valores.csv** — `Ativo_ID, Data, Valor`
- **fato_posicoes_acoes.csv** — `Ativo, Segmento, Quantidade, PrecoMedio, PrecoAtual,
  Investido, Atualizado, LucroPrejuizo, Variacao, Dividendos, YieldBruto, YieldTotal`
- **dim_fundos.csv** — `Fundo, CNPJ, ClassificacaoXP, ClassificacaoCVM, InicioFundo,
  PatrimonioLiquido, Benchmark, PLMedio12M, TaxaAdm, TaxaMaxAdm, TaxaPerformance`
- **juros_real.csv** — `Titulo, Modalidade, Cenario, Taxa`
- **volume_corretora.csv** — `Corretora, Volume`

## Estrutura do repositório

```
carteira-investimentos-powerbi/
├── CarteiraInvestimentos.pbip
├── CarteiraInvestimentos.SemanticModel/   # modelo TMDL (tabelas, medidas, relacionamentos)
├── CarteiraInvestimentos.Report/          # relatório PBIR
├── data/                                   # CSVs (fonte de dados do modelo)
├── scripts/extrair_dados.py               # regenera os CSVs a partir da planilha
└── README.md
```
