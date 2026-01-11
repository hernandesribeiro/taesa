import streamlit as st
from modules.data_loader import load_sheet_from_path_or_buffer
from modules.preprocess import prepare_lt_dataframe
from modules.lt_plot import plot_lt
import pandas as pd
import os


# =====================================================
#  CONFIGURAÇÃO DO ARQUIVO PADRÃO
# =====================================================
diretorio = r"D:\09 - Desenvolvimento de Softwares\Python\Localizacaodetorres"
DEFAULT_EXCEL_PATH = "Localizador de Vão.xlsx"
caminho_arquivo = os.path.join(diretorio, DEFAULT_EXCEL_PATH)



def aba_transposicao():

    st.header("📡 Transposição de Torres")

    # -------------------------------------------------
    # 1) Verifica caminho
    # -------------------------------------------------
    if not os.path.exists(caminho_arquivo):
        st.error(f"Arquivo não encontrado:\n{caminho_arquivo}")
        return

    # -------------------------------------------------
    # 2) Carrega lista de abas com ExcelFile
    # -------------------------------------------------
    try:
        excel = pd.ExcelFile(caminho_arquivo)
    except Exception as e:
        st.error(f"Erro ao abrir o arquivo Excel: {e}")
        return

    # -------------------------------------------------
    # 3) Seleção de aba
    # -------------------------------------------------
    lt_escolhida = st.selectbox("Selecione a LT", excel.sheet_names)

    # -------------------------------------------------
    # 4) Lê somente a aba escolhida (forma CORRETA)
    # -------------------------------------------------
    try:
        df_raw = load_sheet_from_path_or_buffer(
            caminho_arquivo,
            sheet_name=lt_escolhida
        )
    except Exception as e:
        st.error(f"Erro ao carregar aba '{lt_escolhida}': {e}")
        return

    # -------------------------------------------------
    # 5) Pré-processa LT
    # -------------------------------------------------
    try:
        df_lt = prepare_lt_dataframe(df_raw)
    except Exception as e:
        st.error(f"Erro ao processar dados da LT: {e}")
        return

    # -------------------------------------------------
    # 6) Entradas do usuário
    # -------------------------------------------------
    torre_central = st.text_input(
        "Torre central (ex: T-123):",
        placeholder="Opcional"
    )

    km_busca = st.number_input(
        "Buscar por KM (opcional)",
        min_value=0.0,
        step=0.1
    )

    # -------------------------------------------------
    # 7) Botão para gerar gráfico
    # -------------------------------------------------
    if st.button("Gerar Gráfico"):

        try:
            fig = plot_lt(
                df=df_lt,
                km_busca=km_busca if km_busca > 0 else None,
                torre_central=torre_central if torre_central else None,
                titulo=f"Transposição — {lt_escolhida}"
            )
        except Exception as e:
            st.error(f"Erro ao gerar gráfico: {e}")
            return

        st.pyplot(fig)
        st.success("Gráfico gerado com sucesso!")
