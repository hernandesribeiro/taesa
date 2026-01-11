import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO
from typing import Optional, List
import numpy as np
import re
import os
import plotly.express as px
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------

# --- 1. DICIONÁRIOS ---
DE_PARA_CAUSAS = {
    'Não se Aplica': 'NA', 'Descarga Atmosférica': 'DAT', 'Queimada': 'QMD',
    'Queimadas': 'QMD', 'Curicaca / Aves': 'CRC', 'Excremento de Pássaro': 'CRC',
    'Vegetação': 'VGT', 'Outros': 'OTR', 'EXPLOSÃO': 'EXP', 'ACIDENTAL': 'DAC',
    'PROTEÇÃO, MEDIÇÃO E CONTROLE': 'PMC', 'FALHA EM ACESSÓRIOS E COMPONENTES': 'FAC',
    'Equipamentos e Acessórios': 'FAC', 'INDETERMINADA': 'IND', 'Causa indeterminada': 'IND',
    'CONDIÇÕES ANORMAIS DE OPERAÇÃO': 'CAO', 'ERRO DE AJUSTE': 'EDA', 'RAJADA DE VENTO': 'RDV',
    'Queda de Torre': 'QTR', 'Condições Metereológicas Adversas': 'CMA',
    'Falhas humanas': 'FHU', 'Colisão Avião Agricola': 'CAA', 'Causa Externa a FT': 'CEFT'
}

DE_LINHA_SIGLA = {
    'LT 500kV Serra da Mesa - Samambaia': 'LT SMSB C3',
    'LT 500kV Serra da Mesa - Gurupi': 'LT SMGU C2',
    'LT 500kV Gurupi - Miracema': 'LT GUMC C2',
    'LT 500kV Colinas - Miracema': 'LT COMC C2',
    'LT 500kV Imperatriz - Colinas': 'LT IZCO C2',
    'LT 500kV Serra da Mesa - Serra da Mesa 2': 'LT SMSD',
    'LT 500kV Serra da Mesa 2 - Rio das Éguas': 'LT SDRDE',
    'LT 500kV Rio das Éguas - Bom Jesus da Lapa': 'LT RDEBJD',
    'LT 500kV MIRACEMA-GURUPI C2': 'LT GUMC C2',
    'LT 500kV RIO DAS ÉGUAS-B JESUS LAPA II': 'LT RDEBJD',
    'LT 500kV LAJEADO-MIRACEMA C1': 'LT LJMC C1',
    'LT 500kV GURUPI-SERRA DA MESA C2': 'LT SMGU C2',
    'LT 500kV SERRA DA MESA II-RIO DAS ÉGUAS': 'LT SDRDE',
    'LT 230 kV BRASNORTE - NOVA MUTUM 1': 'LT BNNM C1',
    'LT 230 kV BRASNORTE - NOVA MUTUM 2': 'LT BNNM C2',
    'LT 230kV BARREIRAS/RIO GRANDE II C1': 'LT RGDBRA C1',
    'LT 230kV BARREIRAS II/RIO GRANDE II C1': 'LT BRABRD C1',
    'LT 500kV COLINAS-MIRACEMA C2': 'LT COMC C2',
    'LT 230kV LAJEADO-PALMAS C1': 'LT LJPL C1',
    'LT 500kV SERRA DA MESA-SAMAMBAIA C3': 'LT SMSB C3',
    'LT 500kV LAJEADO-MIRACEMA C2': 'LT LJMC C2',
    'LT 500kV SERRA DA MESA-SERRA DA MESA II': 'LT SMSD',
    'LT 230kV JAURU-JUBA C2': 'LT JUJB C2',
    'LT 230kV JAURU-JUBA C1': 'LT JUJB C2',
    'LT 230kV LAJEADO-PALMAS C2': 'LT LJPL C2',
    'LT 230 kV BRASNORTE - NOVA MUTUM 1 / LT 230 kV BRASNORTE - NOVA MUTUM 2': 'LT BNNM C1 / LT BNNM C2 '
}

DE_FASE = {
    'A': 'AN',
    'AG': 'AN',
    'AT': 'AN',
    'B': 'BN',
    'BG': 'BN',
    'BT': 'BN',
    'C': 'CN',
    'CG': 'CN',
    'CT': 'CN',
    'V': 'CN',
    'FV': 'CN',
    'ABN': 'AB',
    'ABG': 'AB',
    'ABT': 'AB',
    'BCN': 'BC',
    'BCG': 'BC',
    'BCT': 'BC',
    'CAN': 'CA',
    'CAG': 'CA',
    'CAT': 'CA',
    'ABG': 'ABN',
    'ABT': 'ABN',
    'BCG': 'BCN',
    'BCT': 'BCN',
    'CAG': 'CAN',
    'CAT': 'CAN',
}
# --- 2. FUNÇÕES DE SUPORTE ---

# -----------------------
# Load helpers with caching
# -----------------------
@st.cache_data
def load_resistance(path: Optional[str]) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    try:
        xls = pd.ExcelFile(path)
        # prefer "LT Torre" exact
        sheet = "LT Torre" if "LT Torre" in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet)
        return df
    except Exception as e:
        st.error(f"Erro ao ler planilha de resistência: {e}")
        return pd.DataFrame()

@st.cache_data
def load_occurrences(path: Optional[str]) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    try:
        xls = pd.ExcelFile(path)
        # prefer "Ocorrências" (case-insensitive)
        sheet = None
        for s in xls.sheet_names:
            if s.strip().lower() == "ocorrências".lower() or s.strip().lower() == "ocorrencias":
                sheet = s
                break
        if sheet is None:
            # fallback first sheet
            sheet = xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet)
        return df
    except Exception as e:
        st.error(f"Erro ao ler planilha de ocorrências: {e}")
        return pd.DataFrame()

def extrair_numero_torre(valor) -> Optional[int]:
    """Extrai primeiro número encontrado (ex: 'Torre 019' -> 19). Retorna None se não houver."""
    if valor is None:
        return None
    s = str(valor).strip()
    m = re.search(r'(\d+)', s)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None

def map_res_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Mapeia nomes da planilha 'LT Torre' para colunas padrão do app."""
    # mapping baseado na imagem que você forneceu
    mapping = {
        "Linha de Transmissão": "linha",
        "Linha de transmissao": "linha",
        "Torre": "torre",
        "Tipo de Torre": "tipo_torre",
        "Fase de Aterramento": "fase_aterramento",
        "Data da medição da resistência de aterramento": "data_medicao_resistencia",
        "Última Medição Resistência de aterramento (Ω)": "resistencia",
        "Ultima Medicao Resistencia": "resistencia",
        "Supervisor": "supervisor",
        "Melhoria Aterramento": "melhoria",
        "Data Medição": "data_medicao",
        "Medição Paralelo Antes (Ω)": "paralelo_antes",
        "Medição Paralelo Depois (Ω)": "paralelo_depois",
        "Medição Oposto Antes (Ω)": "oposto_antes",
        "Medição Oposto Depois (Ω)": "oposto_depois",
        "Fases Implementadas": "fases_implementadas",
    }
    # Try to rename any columns that match keys (case-insensitive)
    rename_dict = {}
    for col in df.columns:
        for k, v in mapping.items():
            if col.strip().lower() == k.strip().lower():
                rename_dict[col] = v
                break
    df = df.rename(columns=rename_dict)
    return df

def map_oc_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Mapeia nomes da planilha 'Ocorrências' para colunas padrão do app."""
    mapping = {
        "Concessão": "concessao",
        "Concessao": "concessao",
        "Equipamento": "equipamento",
        "FT": "ft",
        "Fase": "fase",
        "Data": "data",
        "Horário": "horario",
        "Horario": "horario",
        "Problema": "problema",
        "Terminal A - Prot. (km)": "terminal_a_prot_km",
        "Terminal A - TW": "terminal_a_tw",
        "Terminal B - Prot. (km)": "terminal_b_prot_km",
        "Terminal B - TW": "terminal_b_tw",
        "Torre": "torre_oc",
        "KM Real": "km_real",
        "Causa": "causa",
        "RM": "rm",
        "Obs": "obs",
    }
    rename_dict = {}
    for col in df.columns:
        for k, v in mapping.items():
            if col.strip().lower() == k.strip().lower():
                rename_dict[col] = v
                break
    df = df.rename(columns=rename_dict)
    return df

def safe_to_float_series(s: pd.Series) -> pd.Series:
    """Converte string numérica com vírgula para float, limpando textos."""
    if s is None:
        return s
    return (s.astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace(r'[^\d\.\-]', '', regex=True)
            .replace('', np.nan)
            .astype(float)
           )

def prepare_resistance(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df = map_res_columns(df)

    # ensure expected column names exist; if not, try fuzzy fallback
    if "torre" not in df.columns:
        # try to find column named like 'Torre' ignoring case
        for c in df.columns:
            if c.strip().lower() == "torre":
                df = df.rename(columns={c: "torre"})
                break

    # convert torre to str, remove PORTICO lines
    if "torre" in df.columns:
        df["torre_raw"] = df["torre"].astype(str).str.strip()
        mask_portico = df["torre_raw"].str.upper().str.startswith("PORTICO") | df["torre_raw"].str.upper().str.startswith("PÓRTICO")
        if mask_portico.any():
            df = df[~mask_portico].copy()
        # extract number
        df["torre_num"] = df["torre_raw"].apply(extrair_numero_torre)
        df = df.dropna(subset=["torre_num"]).copy()
        df["torre_num"] = df["torre_num"].astype(int)
    else:
        df["torre_num"] = np.nan

    # resistencia column
    # try common names: 'resistencia' mapped earlier
    res_col = None
    for c in ["resistencia", "Última Medição Resistência de aterramento (Ω)", "Última Medição Resistência de aterramento (Ω)".lower()]:
        if c in df.columns:
            res_col = c
            break
    if res_col is None:
        # try to find numeric-like column via header mapping or fuzzy
        for c in df.columns:
            sample = df[c].dropna().astype(str).head(20).tolist()
            # if many entries have digits or comma/points, assume numeric
            cnt = sum(1 for s in sample if re.search(r'\d', s))
            if cnt >= 1:
                # tentative
                res_col = c
                break
    if res_col is not None and res_col in df.columns:
        df = df.rename(columns={res_col: "resistencia"})
        # convert strings to float
        df["resistencia"] = safe_to_float_series(df["resistencia"])
    else:
        df["resistencia"] = np.nan

    # convert parallel/opposite columns if present
    for col in ["paralelo_antes", "paralelo_depois", "oposto_antes", "oposto_depois"]:
        if col in df.columns:
            df[col] = safe_to_float_series(df[col])

    # standardize other columns names lower-case
    df.columns = [c if c in ["torre_raw", "torre_num", "resistencia", "paralelo_antes", "paralelo_depois", "oposto_antes", "oposto_depois", "linha", "tipo_torre", "fase_aterramento", "supervisor", "melhoria", "data_medicao_resistencia", "data_medicao", "fases_implementadas"] else c for c in df.columns]

    return df

def get_top_causas(df):
    if "causa" not in df.columns:
        return pd.DataFrame()
    return (
        df.groupby("causa")
        .size()
        .reset_index(name="Total_Desligamentos")
        .sort_values("Total_Desligamentos", ascending=False)
        .head(20)
    )

def get_resistencia_media_causa(df):
    if "causa" not in df.columns or "Última Medição Resistência de aterramento (Ω)" not in df.columns:
        return pd.DataFrame()
    return (
        df.groupby("causa")["Última Medição Resistência de aterramento (Ω)"]
        .mean()
        .reset_index(name="Resistencia_Media")
        .sort_values("Resistencia_Media", ascending=False)
    )

def get_torres_criticas(df):
    if "torre" not in df.columns or "Última Medição Resistência de aterramento (Ω)" not in df.columns:
        return pd.DataFrame()

    df_falhas = df.groupby("torre").size().reset_index(name="Frequencia_Falhas")
    df_res = df.groupby("torre")["Última Medição Resistência de aterramento (Ω)"].mean().reset_index(name="Resistencia_Media")

    df_merge = pd.merge(df_falhas, df_res, on="torre", how="inner")
    df_merge["Score_Criticidade"] = df_merge["Frequencia_Falhas"] * df_merge["Resistencia_Media"]

    return df_merge.sort_values("Score_Criticidade", ascending=False).head(20)

def get_falhas_por_torre(df):
    if "torre" not in df.columns:
        return pd.DataFrame()
    return (
        df.groupby("torre")
        .size()
        .reset_index(name="Total_Falhas")
        .sort_values("Total_Falhas", ascending=False)
        .head(20)
    )
    
def read_excel_safely(path_or_buffer, sheet_name=None):
    """Lê Excel tanto de UploadedFile quanto de caminho."""
    if isinstance(path_or_buffer, str):
        return pd.read_excel(path_or_buffer, sheet_name=sheet_name)

    # UploadedFile (possui .read e .seek)
    path_or_buffer.seek(0)
    return pd.read_excel(path_or_buffer, sheet_name=sheet_name)

def prepare_ocorrencias(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df = map_oc_columns(df)

    # find tower column (mapped to 'torre_oc' if mapping worked), else try 'Torre'
    torre_col = None
    if "torre_oc" in df.columns:
        torre_col = "torre_oc"
    else:
        for c in df.columns:
            if c.strip().lower() == "torre":
                torre_col = c
                break
    if torre_col:
        df["torre_raw"] = df[torre_col].astype(str).str.strip()
        # remove portico occurrences
        mask_portico = df["torre_raw"].str.upper().str.startswith("PORTICO") | df["torre_raw"].str.upper().str.startswith("PÓRTICO")
        if mask_portico.any():
            df = df[~mask_portico].copy()
        df["torre_num"] = df["torre_raw"].apply(extrair_numero_torre)
        df = df.dropna(subset=["torre_num"]).copy()
        df["torre_num"] = df["torre_num"].astype(int)
    else:
        df["torre_raw"] = ""
        df["torre_num"] = np.nan

    # convert date column if exists (mapped earlier to 'data')
    if "data" in df.columns:
        try:
            df["data"] = pd.to_datetime(df["data"], errors="coerce")
        except:
            pass

    # standardize some columns
    for c in list(df.columns):
        # nothing yet
        pass

    return df

# ---------------------------------------------------------
# FUNÇÃO PRINCIPAL DA ABA
# ---------------------------------------------------------

# No topo do aba_analises.py (adicionar utilitários)
def _ensure_df(obj, prefer_sheet_names: List[str] = None) -> pd.DataFrame:
    """
    Garante que retornamos um DataFrame:
    - se já for DataFrame -> retorna cópia
    - se for dict (sheet_name -> df) -> tenta escolher aba preferida ou primeira
    - se for None -> DataFrame vazio
    """
    if obj is None:
        return pd.DataFrame()
    if isinstance(obj, pd.DataFrame):
        return obj.copy()
    if isinstance(obj, dict):
        # preferência por nomes comuns
        if prefer_sheet_names:
            for pref in prefer_sheet_names:
                for k in obj.keys():
                    if pref.lower() in str(k).lower():
                        return obj[k].copy()
        # fallback primeira aba
        first = list(obj.values())[0]
        return first.copy()
    # UploadedFile / buffer -> tentar ler com pandas
    try:
        # seek se possível
        if hasattr(obj, "seek"):
            obj.seek(0)
        return pd.read_excel(obj)
    except Exception:
        return pd.DataFrame()

def _normalize_and_map_columns(df: pd.DataFrame):
    """Normaliza nomes e cria colunas auxiliares esperadas."""
    if df is None or df.empty:
        return df
    # normalize headers safely
    orig_cols = list(df.columns)
    norm_map = {}
    for c in orig_cols:
        key = str(c).strip()
        norm_map[c] = key  # keep original mapping if needed
    # apply safe renaming to lowercase-without-spaces keys for easier matching
    df = df.rename(columns={c: str(c).strip() for c in df.columns})

    # Create lowercase lookup mapping for detection
    lower_map = {str(c).strip().lower(): c for c in df.columns}

    # Map common names to standardized internal names used later
    # Ensure we keep both 'causa' (lowercase) and older labels if necessary
    # find a resistance-like column
    resistencia_col = None
    for c in df.columns:
        if "resist" in str(c).lower():
            resistencia_col = c
            break

    # ensure consistent column names used in analysis functions
    if resistencia_col:
        # standard column name
        df["resistencia"] = pd.to_numeric(df[resistencia_col].astype(str).str.replace(",", ".", regex=False).str.replace(r'[^\d\.\-]', '', regex=True), errors="coerce")
        # also set legacy verbose column name to keep compatibility with other functions
        df["Última Medição Resistência de aterramento (Ω)"] = df["resistencia"]
    # ensure causa lowercase column
    if any("causa" in str(c).lower() for c in df.columns):
        cand = next(c for c in df.columns if "causa" in str(c).lower())
        df["causa"] = df[cand].astype(str).str.strip()
    # ensure torre column exists (for frequency)
    if any("torre" in str(c).lower() for c in df.columns):
        cand = next(c for c in df.columns if "torre" in str(c).lower())
        df["torre"] = df[cand].astype(str).str.strip()
    # lower-case header keys for tooltip/chart compatibility used later
    df.columns = [str(c) for c in df.columns]
    return df

# --- 2. INTERFACE DE ANÁLISES ---

def aba_analises(df_desl_sincronizado):
    """
    Recebe apenas o DataFrame já processado pelo app.py 
    ou lê o arquivo 'Desligamentos forçados Taesa.xlsx'.
    """
    st.title("📊 Painel de Análise de Desligamentos")

    # Verifica se o dataframe recebido é válido
    if df_desl_sincronizado is None or df_desl_sincronizado.empty:
        st.warning("⚠️ O arquivo 'Desligamentos forçados Taesa.xlsx' não foi carregado ou está vazio.")
        return

    # Garantir que as colunas necessárias existam (evita erros caso o arquivo mude)
    colunas_obrigatorias = ['Concessão', 'Ano', 'Causa', 'FT']
    colunas_presentes = [c for c in colunas_obrigatorias if c in df_desl_sincronizado.columns]
    
    if len(colunas_presentes) < len(colunas_obrigatorias):
        st.error(f"Erro: O arquivo carregado não possui todas as colunas necessárias: {colunas_obrigatorias}")
        return

     # --- KPIs ---
       # --- BARRA LATERAL: FILTROS ---
    st.subheader("🎯 Filtros")
    m1, m2 = st.columns(2)
    # Filtro de Concessão
    #m1.metric("Ocorrências no Filtro", len(df_filtrado))
    with m1:
        opcoes_conc = ["TODAS"] + sorted(df_desl_sincronizado['Concessão'].unique().tolist())
        conc_sel = st.selectbox("Concessão", opcoes_conc)
        df_filtrado = df_desl_sincronizado.copy()
       
        if conc_sel != "TODAS":
            df_filtrado = df_filtrado[df_filtrado['Concessão'] == conc_sel]
            st.text(f"{len(df_filtrado)} Ocorrências na {conc_sel}")
        else:
            st.text(f"{len(df_filtrado)} Ocorrências na {conc_sel}")
        
        
    with m2:
        opcoes_ano = ["TODOS"] + sorted([str(a) for a in df_desl_sincronizado['Ano'].unique()], reverse=True)
        # ano_min=min(df_filtrado['Ano'])
        # ano_max=max(df_filtrado['Ano'])
        # ano_Selecionado=st.slider("Ano",ano_min,ano_max,None,1)
        
        ano_sel = st.selectbox("Ano", opcoes_ano)
        df_filtrado = df_desl_sincronizado.copy()
         # Filtro de Ano
        if ano_sel != "TODOS":
            df_filtrado = df_filtrado[df_filtrado['Ano'] == int(ano_sel)]
            st.text(f"{len(df_filtrado)} Ocorrências em {ano_sel}")
    
    # --- LÓGICA DE FILTRAGEM ---

    st.divider()

    # --- GRÁFICOS ---
    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.subheader("Distribuição por Causa")
        df_causa = df_filtrado['Causa'].value_counts().reset_index()
        fig_causa = px.pie(df_causa, values='count', names='Causa', hole=0.4)
        st.plotly_chart(fig_causa, use_container_width=True)

    with col_dir:
        st.subheader("Top 10 Linhas (FT) Afetadas")
        df_ft = df_filtrado['FT'].value_counts().nlargest(10).reset_index()
        fig_ft = px.bar(df_ft, x='count', y='FT', orientation='h', 
                        color='count', color_continuous_scale='Reds')
        fig_ft.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_ft, use_container_width=True)

    # Tabela de dados
    with st.expander("🔍 Ver detalhes dos dados filtrados"):
        st.dataframe(df_filtrado, use_container_width=True)
    # --- 3º GRÁFICO: SAZONALIDADE MENSAL ---
    st.divider()
    #Gráfico 3
    st.subheader(f"📅 Sazonalidade: Desligamentos por Mês ({ano_sel})")

    if 'Data' in df_filtrado.columns:
        # Criamos uma cópia para não afetar o dataframe original
        df_mes = df_filtrado.copy()
        
        # Convertemos para datetime (caso ainda não esteja) e extraímos o número e nome do mês
        df_mes['Data'] = pd.to_datetime(df_mes['Data'])
        df_mes['Mes_Num'] = df_mes['Data'].dt.month
        df_mes['Mês'] = df_mes['Data'].dt.strftime('%b') # Ex: Jan, Fev, Mar

        # Agrupamos e ordenamos pelo número do mês para garantir a ordem cronológica
        sazonalidade = df_mes.groupby(['Mes_Num', 'Mês']).size().reset_index(name='Quantidade')
        sazonalidade = sazonalidade.sort_values('Mes_Num')

        # Criação do Gráfico de Linhas com Áreas (Trend)
        fig_mes = px.line(
            sazonalidade, 
            x='Mês', 
            y='Quantidade',
            markers=True,
            text='Quantidade',
            title="Evolução Mensal de Ocorrências",
            labels={'Quantidade': 'Nº de Desligamentos', 'Mês': 'Mês do Ano'},
            template="plotly_white"
        )

        # Estilização para destacar a linha
        fig_mes.update_traces(line_color='#d62728', line_width=3, fill='tozeroy') 
        fig_mes.update_traces(textposition="top center")
        
        st.plotly_chart(fig_mes, use_container_width=True)
    else:
        st.error("Coluna 'Data' não encontrada para gerar o gráfico de sazonalidade.")

    st.divider()
    st.subheader(f"🔥 Mapa de Concentração: Linhas vs Meses ({ano_sel})")

    if 'FT' in df_filtrado.columns and 'Data' in df_filtrado.columns:
        df_heat = df_filtrado.copy()
        df_heat['Data'] = pd.to_datetime(df_heat['Data'])
        df_heat['Mês'] = df_heat['Data'].dt.strftime('%b')
        df_heat['Mes_Num'] = df_heat['Data'].dt.month

        # Criamos uma tabela dinâmica (Pivot Table) para o Heatmap
        # Linhas (Index) = FT, Colunas = Mês, Valores = Contagem de Desligamentos
        df_pivot = df_heat.pivot_table(
            index='FT', 
            columns=['Mes_Num', 'Mês'], 
            values='Concessão', 
            aggfunc='count'
        ).fillna(0)

        # Reordenar colunas para garantir Jan -> Dez
        df_pivot = df_pivot.sort_index(axis=1, level=0)
        # Simplificar o nome das colunas para exibir apenas o nome do mês
        df_pivot.columns = [col[1] for col in df_pivot.columns]

        # Pegamos apenas as 20 FTs com mais desligamentos para o gráfico não ficar gigante
        top_20_fts = df_filtrado['FT'].value_counts().nlargest(20).index
        df_pivot_top = df_pivot.loc[df_pivot.index.isin(top_20_fts)]

        if not df_pivot_top.empty:
            fig_heat = px.imshow(
                df_pivot_top,
                labels=dict(x="Mês", y="Linha de Transmissão (FT)", color="Qtd Desligamentos"),
                x=df_pivot_top.columns,
                y=df_pivot_top.index,
                color_continuous_scale='YlOrRd', # Amarelo -> Laranja -> Vermelho
                aspect="auto",
                text_auto=True # Mostra o número dentro do quadradinho
            )

            fig_heat.update_xaxes(side="top")
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Dados insuficientes para gerar o mapa de calor.")
            
    # --- 5º GRÁFICO: MAPA DE CALOR (CAUSA vs MÊS) ---
    # --- BLOCO DE LEGENDAS (GLOSSÁRIO) ---
    
                
    st.divider()
    st.subheader(f"🔥 Concentração de Causas por Mês ({ano_sel})")

    if 'Causa' in df_filtrado.columns and 'Data' in df_filtrado.columns:
        df_heat_causa = df_filtrado.copy()
        df_heat_causa['Data'] = pd.to_datetime(df_heat_causa['Data'])
        df_heat_causa['Mês'] = df_heat_causa['Data'].dt.strftime('%b')
        df_heat_causa['Mes_Num'] = df_heat_causa['Data'].dt.month

        # Criamos a Pivot Table: Linhas = Causa, Colunas = Mês
        df_pivot_causa = df_heat_causa.pivot_table(
            index='Causa', 
            columns=['Mes_Num', 'Mês'], 
            values='Concessão', 
            aggfunc='count'
        ).fillna(0)

        # Ordenar cronologicamente de Jan a Dez
        df_pivot_causa = df_pivot_causa.sort_index(axis=1, level=0)
        df_pivot_causa.columns = [col[1] for col in df_pivot_causa.columns]

        if not df_pivot_causa.empty:
            fig_heat_causa = px.imshow(
                df_pivot_causa,
                labels=dict(x="Mês", y="Causa do Desligamento", color="Qtd"),
                x=df_pivot_causa.columns,
                y=df_pivot_causa.index,
                color_continuous_scale='Reds', # Escala de Vermelhos para destacar severidade
                aspect="auto",
                text_auto=True 
            )

            fig_heat_causa.update_xaxes(side="top")
            st.plotly_chart(fig_heat_causa, use_container_width=True)
            
            st.caption("💡 Dica: Quadradinhos mais escuros indicam meses com maior incidência de uma causa específica.")
        
            st.divider()
            with st.expander("📖 Legenda de Siglas (Causas)", expanded=True):
                # Filtramos o dicionário para mostrar apenas o que é relevante para o sistema
                # Você pode usar o seu DE_PARA_CAUSAS invertido
                LEGENDA_REVERSA = {
                    'DAT': 'Descarga Atmosférica',
                    'QMD': 'Queimada / Incêndio',
                    'CRC': 'Curicaca / Aves / Excrementos',
                    'VGT': 'Vegetação',
                    'OTR': 'Outros / Diversos',
                    'EXP': 'Explosão',
                    'DAC': 'Acidental / Colisão',
                    'PMC': 'Proteção, Medição e Controle',
                    'FAC': 'Falha em Acessórios / Equipamentos',
                    'IND': 'Causa Indeterminada',
                    'CAO': 'Condições Anormais de Operação',
                    'EDA': 'Erro de Ajuste',
                    'RDV': 'Rajada de Vento / Vendaval',
                    'QTR': 'Queda de Torre',
                    'CMA': 'Condições Metereológicas Adversas',
                    'FHU': 'Falha Humana',
                    'CAA': 'Colisão Avião Agrícola',
                    'CEFT': 'Causa Externa à FT'
                }

                # Organizar em 3 colunas para economizar espaço vertical
                cols_leg = st.columns(3)
                causas_presentes = (df_filtrado['Causa'].unique())
                
                for i, sigla in enumerate(causas_presentes):
                    descricao = LEGENDA_REVERSA.get(sigla, "Descrição não cadastrada")
                    with cols_leg[i % 3]:
                        st.markdown(f"**{sigla}** = {descricao}")
        else:
            st.info("Dados insuficientes para gerar o mapa de calor por causas.")
    