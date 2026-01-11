import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import openpyxl
import os
import plotly.express as px
import plotly.graph_objects as go

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


def autolabel(barras, ax):
    for b in barras:
        h = b.get_height()
        ax.annotate(f'{int(h)}', xy=(b.get_x() + b.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom')


def sincronizar_fluxo_total(df_upload):
    """
    Versão adaptada para Streamlit que recebe o DataFrame do upload 
    e limpa os dados para as demais abas.
    """
    st.subheader("🧹 Processamento e Limpeza de Dados")

    if df_upload is None or df_upload.empty:
        st.warning("Aguardando upload de dados para processar...")
        return

    # 1. Limpeza de "SUTIÃ" e Ruídos de Legenda
    # Filtramos onde a Concessão não é nula e não contém o termo fantasma
    col_ref = 'Concessão' if 'Concessão' in df_upload.columns else df_upload.columns[0]

    df_dados = df_upload[df_upload[col_ref].notna()].copy()

    # Filtro rigoroso contra o erro de codificação "SUTIÃ"
    df_dados = df_dados[~df_dados[col_ref].astype(
        str).str.upper().str.contains("SUTIÃ", na=False)]
    
    # --- PASSO 2: CRIAÇÃO DA COLUNA 'ANO' (A sua dúvida) ---
    if 'Data' in df_dados.columns:
        # Converte para data e extrai o ano
        df_dados['Data'] = pd.to_datetime(df_dados['Data'], errors='coerce')
        df_dados['Ano'] = df_dados['Data'].dt.year.fillna(0).astype(int)
        # Remove datas inválidas (Ano 0)
        df_dados = df_dados[df_dados['Ano'] > 0]

    # 2. Aplicação dos Dicionários (De-Para)
    if 'Causa' in df_dados.columns:
        df_dados['Causa'] = df_dados['Causa'].replace(DE_PARA_CAUSAS)
    if 'FT' in df_dados.columns:
        df_dados['FT'] = df_dados['FT'].replace(DE_LINHA_SIGLA)
    if 'Fase' in df_dados.columns:
        df_dados['Fase'] = df_dados['Fase'].replace(DE_FASE)

    # --- 3. NOVOS FILTROS DE INTERFACE ---
    st.write("### 🔍 Refinar Seleção")
    c1, c2 = st.columns(2)
    
    with c1:
        # Filtro de Concessão
        opcoes_conc = ["TODAS"] + sorted(df_dados[col_ref].unique().tolist())
        conc_escolhida = st.selectbox("Filtrar por Concessão:", opcoes_conc)

    with c2:
        # Filtro de Ano
        # Removemos o ano '0' da lista de escolha caso haja datas inválidas
        anos_disponiveis = sorted([a for a in df_dados['Ano'].unique() if a > 0], reverse=True)
        opcoes_ano = ["TODOS"] + [str(a) for a in anos_disponiveis]
        ano_escolhido = st.selectbox("Filtrar por Ano:", opcoes_ano)

    # --- 4. APLICAÇÃO DOS FILTROS NO DATAFRAME ---
    df_filtrado = df_dados.copy()

    if conc_escolhida != "TODAS":
        df_filtrado = df_filtrado[df_filtrado[col_ref] == conc_escolhida]
    
    if ano_escolhido != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['Ano'] == int(ano_escolhido)]

    # --- 5. FINALIZAÇÃO E ESTADO ---
    # Salvamos o resultado filtrado para que a aba de análises o consuma
    st.session_state["df_desligamentos_limpo"] = df_filtrado
    # Feedback visual para o usuário
    st.success(f"📈 Dados prontos! {len(df_filtrado)} registros encontrados para os filtros selecionados.")
    
    # Indicadores Rápidos
    #st.info(f"📊 Registros após filtros: {len(df_filtrado)}")

    with st.expander("Ver Tabela Processada"):
        st.dataframe(df_filtrado, use_container_width=True)

    # Gráfico de conferência rápido
    if not df_filtrado.empty:
        fig = px.bar(df_filtrado['Causa'].value_counts(), title=f"Causas: {conc_escolhida} ({ano_escolhido})")
        st.plotly_chart(fig, use_container_width=True)