#!/usr/bin/env python3
"""
Extrai os dados da planilha de carteira de investimentos (.xlsm) para CSVs limpos
em esquema estrela, prontos para serem importados pelo projeto Power BI (PBIP).

Uso:
    python scripts/extrair_dados.py CAMINHO_DA_PLANILHA.xlsm

Se nenhum caminho for informado, procura por um .xlsm na pasta atual.
Não depende de bibliotecas externas (apenas a stdlib): lê o .xlsm como ZIP/XML.

Gera em data/:
    dim_ativo.csv          - 1 linha por ativo (atributos da aba "Dados")
    fato_valores.csv       - série histórica de valor por ativo (unpivot de "Dados")
    fato_posicoes_acoes.csv- posições de Ações/FIIs (aba "ResumoAções")
    dim_fundos.csv         - cadastro de fundos (aba "Fundos", transposta)
    juros_real.csv         - cenários de juros (aba "JurosReal", formato tidy)
    volume_corretora.csv   - volume por corretora (bloco da aba "Dados")
"""
import csv
import datetime as dt
import glob
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
EXCEL_EPOCH = dt.date(1899, 12, 30)  # base de datas do Excel (Windows)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")


# --------------------------------------------------------------------------- #
# Leitura do workbook
# --------------------------------------------------------------------------- #
def col_to_idx(ref):
    """'AB' -> 28 (1-based)."""
    letters = re.match(r"[A-Z]+", ref).group(0)
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx


def idx_to_col(idx):
    """28 -> 'AB' (1-based)."""
    s = ""
    while idx > 0:
        idx, r = divmod(idx - 1, 26)
        s = chr(ord("A") + r) + s
    return s


class Workbook:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.shared = self._shared_strings()
        self.name2path = self._sheet_map()

    def _shared_strings(self):
        out = []
        try:
            root = ET.fromstring(self.z.read("xl/sharedStrings.xml"))
        except KeyError:
            return out
        for si in root.findall("m:si", NS):
            out.append("".join(t.text or "" for t in si.iter(MAIN + "t")))
        return out

    def _sheet_map(self):
        rels = self.z.read("xl/_rels/workbook.xml.rels").decode("utf-8", "ignore")
        rid2tgt = {
            m.group(1): m.group(2)
            for m in re.finditer(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels)
        }
        wb = self.z.read("xl/workbook.xml").decode("utf-8", "ignore")
        name2path = {}
        for m in re.finditer(r'<sheet [^>]*name="([^"]*)"[^>]*r:id="([^"]*)"', wb):
            name, rid = m.group(1), m.group(2)
            tgt = rid2tgt.get(rid, "")
            if tgt:
                name2path[name] = "xl/" + tgt.lstrip("/")
        return name2path

    def cells(self, sheet_name):
        """Retorna dict {(col_idx, row_idx): valor} da aba (valores já resolvidos)."""
        path = self.name2path[sheet_name]
        root = ET.fromstring(self.z.read(path))
        sd = root.find("m:sheetData", NS)
        grid = {}
        for r in sd.findall("m:row", NS):
            for c in r.findall("m:c", NS):
                ref = c.get("r")
                t = c.get("t")
                col = col_to_idx(ref)
                row = int(re.search(r"\d+", ref).group(0))
                val = None
                if t == "e":  # erro de fórmula (#VALUE!, #DIV/0!...) -> vazio
                    val = None
                elif t == "inlineStr":
                    isv = c.find("m:is", NS)
                    if isv is not None:
                        val = "".join(tt.text or "" for tt in isv.iter(MAIN + "t"))
                else:
                    v = c.find("m:v", NS)
                    if v is not None and v.text is not None:
                        if t == "s":
                            try:
                                val = self.shared[int(v.text)]
                            except (ValueError, IndexError):
                                val = v.text
                        else:
                            val = v.text
                if val not in (None, ""):
                    grid[(col, row)] = val
        return grid


# --------------------------------------------------------------------------- #
# Helpers de valor
# --------------------------------------------------------------------------- #
def as_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def serial_to_iso(v):
    """Converte serial Excel (int/float) para 'YYYY-MM-DD'. Mantém texto se não for serial."""
    f = as_float(v)
    if f is None:
        return None
    # seriais plausíveis de data (entre ~1990 e ~2100)
    if 30000 <= f <= 80000:
        return (EXCEL_EPOCH + dt.timedelta(days=int(f))).isoformat()
    return None


def clean_str(v):
    if v is None:
        return ""
    s = str(v).strip()
    if s in ("#VALUE!", "#DIV/0!", "#REF!", "#N/A", "#NAME?"):
        return ""
    return s


def write_csv(name, header, rows):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, name)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name:28s} {len(rows):5d} linhas")
    return path


# --------------------------------------------------------------------------- #
# Extratores por aba
# --------------------------------------------------------------------------- #
def extrair_dados(wb):
    """Aba 'Dados' -> dim_ativo.csv + fato_valores.csv + volume_corretora.csv"""
    g = wb.cells("Dados")
    HEADER_ROW = 2
    # mapa de atributos col-letter -> nome de campo
    attr = {
        "A": "Tipo",
        "B": "Papel",
        "C": "SubTipo",
        "D": "Indexador",
        "E": "TaxaContratada",
        "F": "Fundo",
        "G": "DataCompra",
        "H": "Dias",
        "I": "Vencimento",
        "J": "Data2",
        "K": "AplicAtual",
        "L": "AplicInicial",
        "M": "Corretora",
        "N": "Categoria",
        "O": "Banco",
    }
    attr_idx = {col_to_idx(k): v for k, v in attr.items()}
    date_fields = {"DataCompra", "Vencimento", "Data2"}
    float_fields = {"TaxaContratada", "Dias", "AplicAtual", "AplicInicial"}

    # colunas de datas (valor por data): de Q até DU, lendo o serial no header
    q_idx = col_to_idx("Q")
    du_idx = col_to_idx("DU")
    date_cols = {}  # col_idx -> ISO date
    for col in range(q_idx, du_idx + 1):
        iso = serial_to_iso(g.get((col, HEADER_ROW)))
        if iso:
            date_cols[col] = iso

    # linhas de dados (a partir da linha 3)
    max_row = max(r for (_, r) in g.keys())
    dim_rows = []
    fato_rows = []
    for row in range(HEADER_ROW + 1, max_row + 1):
        # Um ativo real SEMPRE tem um identificador (Papel ou Fundo). As linhas de
        # subtotal/total embutidas na planilha (ex.: "Total Renda Fixa", "TOTAL INVESTIDO")
        # têm Papel e Fundo em branco e por isso são descartadas — evitando dupla contagem.
        papel = clean_str(g.get((col_to_idx("B"), row)))
        fundo = clean_str(g.get((col_to_idx("F"), row)))
        if not (papel or fundo):
            continue
        ativo_id = row  # id estável = número da linha na planilha
        rec = {"Ativo_ID": ativo_id}
        for cidx, field in attr_idx.items():
            raw = g.get((cidx, row))
            if field in date_fields:
                rec[field] = serial_to_iso(raw) or clean_str(raw)
            elif field in float_fields:
                fv = as_float(raw)
                rec[field] = fv if fv is not None else ""
            else:
                rec[field] = clean_str(raw)
        dim_rows.append(rec)
        # fato: valor por data
        for cidx, iso in date_cols.items():
            fv = as_float(g.get((cidx, row)))
            if fv is not None and fv != 0:
                fato_rows.append([ativo_id, iso, round(fv, 2)])

    dim_header = ["Ativo_ID"] + list(attr.values())
    write_csv(
        "dim_ativo.csv",
        dim_header,
        [[r["Ativo_ID"]] + [r[f] for f in attr.values()] for r in dim_rows],
    )
    write_csv("fato_valores.csv", ["Ativo_ID", "Data", "Valor"], fato_rows)

    # volume por corretora (bloco DY:DZ)
    dy = col_to_idx("DY")
    dz = col_to_idx("DZ")
    vol_rows = []
    for row in range(3, max_row + 1):
        corr = clean_str(g.get((dy, row)))
        val = as_float(g.get((dz, row)))
        if corr and val is not None:
            vol_rows.append([corr, round(val, 2)])
    write_csv("volume_corretora.csv", ["Corretora", "Volume"], vol_rows)


def extrair_posicoes_acoes(wb):
    """Aba 'ResumoAções' -> fato_posicoes_acoes.csv (linhas com Qtde > 0)."""
    g = wb.cells("ResumoAções")
    cols = {
        "B": "Ativo",
        "C": "Segmento",
        "D": "Quantidade",
        "E": "PrecoMedio",
        "G": "PrecoAtual",
        "H": "Investido",
        "I": "Atualizado",
        "J": "LucroPrejuizo",
        "K": "Variacao",
        "L": "Dividendos",
        "M": "YieldBruto",
        "N": "YieldTotal",
    }
    num_fields = {
        "Quantidade", "PrecoMedio", "PrecoAtual", "Investido", "Atualizado",
        "LucroPrejuizo", "Variacao", "Dividendos", "YieldBruto", "YieldTotal",
    }
    max_row = max(r for (_, r) in g.keys())
    rows = []
    for row in range(2, max_row + 1):
        qtd = as_float(g.get((col_to_idx("D"), row)))
        ativo = clean_str(g.get((col_to_idx("B"), row)))
        if not ativo or qtd is None or qtd <= 0:
            continue
        rec = []
        for cl, field in cols.items():
            raw = g.get((col_to_idx(cl), row))
            if field in num_fields:
                fv = as_float(raw)
                rec.append(fv if fv is not None else "")
            else:
                rec.append(clean_str(raw))
        rows.append(rec)
    write_csv("fato_posicoes_acoes.csv", list(cols.values()), rows)


def extrair_fundos(wb):
    """Aba 'Fundos' (transposta: cada coluna A-M é um fundo) -> dim_fundos.csv"""
    g = wb.cells("Fundos")
    # mapeamento linha-de-valor -> campo
    row_fields = [
        (1, "Fundo", "str"),
        (6, "CNPJ", "str"),
        (8, "ClassificacaoXP", "str"),
        (10, "ClassificacaoCVM", "str"),
        (12, "InicioFundo", "date"),
        (14, "PatrimonioLiquido", "num"),
        (16, "Benchmark", "str"),
        (18, "PLMedio12M", "num"),
        (20, "TaxaAdm", "num"),
        (22, "TaxaMaxAdm", "num"),
        (24, "TaxaPerformance", "num"),
    ]
    fund_cols = [col_to_idx(c) for c in "ABCDEFGHIJKLM"]
    rows = []
    for cidx in fund_cols:
        nome = clean_str(g.get((cidx, 1)))
        if not nome:
            continue
        rec = []
        for r, field, kind in row_fields:
            raw = g.get((cidx, r))
            if kind == "date":
                rec.append(serial_to_iso(raw) or clean_str(raw))
            elif kind == "num":
                fv = as_float(raw)
                rec.append(fv if fv is not None else "")
            else:
                rec.append(clean_str(raw))
        rows.append(rec)
    write_csv("dim_fundos.csv", [f for _, f, _ in row_fields], rows)


def extrair_juros(wb):
    """Aba 'JurosReal' -> juros_real.csv (formato tidy: Titulo, Modalidade, Coluna, Valor)."""
    g = wb.cells("JurosReal")
    # cabeçalhos das colunas de taxa (linha 1), de G a P
    headers = {}
    for cl in ["G", "H", "I", "J", "K", "L", "M", "N", "O", "P"]:
        headers[col_to_idx(cl)] = clean_str(g.get((col_to_idx(cl), 1))) or cl
    titulo = ""
    rows = []
    for row in range(2, 8):  # blocos de modalidade
        t = clean_str(g.get((col_to_idx("E"), row)))
        if t:
            titulo = t
        modalidade = clean_str(g.get((col_to_idx("F"), row)))
        if not modalidade:
            continue
        for cidx, head in headers.items():
            fv = as_float(g.get((cidx, row)))
            if fv is not None:
                rows.append([titulo, modalidade, head, fv])
    write_csv("juros_real.csv", ["Titulo", "Modalidade", "Cenario", "Taxa"], rows)


# --------------------------------------------------------------------------- #
def main():
    if len(sys.argv) > 1:
        src = sys.argv[1]
    else:
        candidatos = glob.glob(os.path.join(ROOT, "*.xlsm")) + glob.glob("*.xlsm")
        if not candidatos:
            sys.exit("Informe o caminho da planilha .xlsm como argumento.")
        src = candidatos[0]
    print(f"Lendo: {src}")
    wb = Workbook(src)
    print("Gerando CSVs em data/:")
    extrair_dados(wb)
    extrair_posicoes_acoes(wb)
    extrair_fundos(wb)
    extrair_juros(wb)
    print("Concluído.")


if __name__ == "__main__":
    main()
