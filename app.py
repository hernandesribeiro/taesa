import streamlit as st
import pandas as pd
import os
from streamlit_option_menu import option_menu
from io import BytesIO
from modules.data_loader import load_sheet_from_path_or_buffer
from modules.preprocess import prepare_lt_dataframe
from aba_transposicao import aba_transposicao
from aba_analises import aba_analises
from aba_llm import aba_llm
from aba_mapa import aba_mapa
from aba_localizacao import aba_localizacao   # <-- nova aba
from aba_aterramento import aba_aterramento
from aba_config import aba_config
from aba_limpeza_dados import sincronizar_fluxo_total
from modules.data_loader import load_sheet_from_path_or_buffer

global upload_localizador
global upload_aterr
global upload_desl

st.set_page_config(page_title="Desligamentos Forçados GMBR", layout="wide")
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

DE_TORRE={
    'T': 'Torre ',
    'TORRE': 'Torre ',
}

def _read_first_sheet(path_or_buffer):
    """Lê o primeiro sheet de um caminho ou UploadedFile e retorna DataFrame."""
    if isinstance(path_or_buffer, str):
        xls = pd.ExcelFile(path_or_buffer)
    else:
        # UploadedFile: posiciona no início
        try:
            path_or_buffer.seek(0)
        except Exception:
            pass
        xls = pd.ExcelFile(path_or_buffer)
    first = xls.sheet_names[0]
    return pd.read_excel(xls, sheet_name=first)



        
def processar_e_salvar_desligamentos(p1_path, p2_path, saida_path):
    try:
        if not (os.path.exists(p1_path) and os.path.exists(p2_path)):
            return False
            
        # 1. Leitura da Planilha 1 (Base de comparação)
        df1 = pd.read_excel(p1_path)
        
        # 2. Abrir Planilha 2 para manipular abas
        xls2 = pd.ExcelFile(p2_path)
        abas_p2 = xls2.sheet_names
        
        # Identificar qual aba da Planilha 2 contém as ocorrências para sincronizar
        # Se houver uma aba chamada 'Ocorrencia', usamos ela, senão usamos a primeira
        aba_alvo = 'Ocorrencia' if 'Ocorrencia' in abas_p2 else abas_p2[0]
        
        # 3. Criar o arquivo de saída preservando as abas
        with pd.ExcelWriter(saida_path, engine='xlsxwriter') as writer:
            
            for sheet in abas_p2:
                df_sheet = pd.read_excel(xls2, sheet_name=sheet)
                
                if sheet == aba_alvo:
                    # --- LÓGICA DE SINCRONIZAÇÃO (Apenas para esta aba) ---
                    df_sinc = pd.concat([df1, df_sheet], ignore_index=True, sort=False)
                    
                    # Limpeza e Formatação
                    if 'Data' in df_sinc.columns:
                        df_sinc['Data'] = pd.to_datetime(df_sinc['Data'], errors='coerce')
                        df_sinc['Ano'] = df_sinc['Data'].dt.year.fillna(0).astype(int)
                        df_sinc = df_sinc[df_sinc['Ano'] > 0]

                    if 'Hora' in df_sinc.columns:
                        df_sinc['Hora'] = pd.to_datetime(df_sinc['Hora'], errors='coerce')

                    # Sincronização por chaves únicas
                    chaves = ['Concessão', 'Data', 'FT']
                    if 'Hora' in df_sinc.columns: chaves.append('Hora')
                    df_sinc = df_sinc.drop_duplicates(subset=chaves, keep='first')

                    # Aplicar Dicionários
                    df_sinc['Causa'] = df_sinc['Causa'].replace(DE_PARA_CAUSAS) if 'Causa' in df_sinc.columns else df_sinc['Causa']
                    df_sinc['FT'] = df_sinc['FT'].replace(DE_LINHA_SIGLA) if 'FT' in df_sinc.columns else df_sinc['FT']
                    df_sinc['Fase'] = df_sinc['Fase'].replace(DE_FASE) if 'Fase' in df_sinc.columns else df_sinc
                    df_sinc['Torre'] = df_sinc['Torre'].replace(DE_TORRE) if 'Torre' in df_sinc.columns else df_sinc
                    
                    # Formatação Final
                    if 'Data' in df_sinc.columns: df_sinc['Data'] = df_sinc['Data'].dt.date
                    if 'Hora' in df_sinc.columns: df_sinc['Hora'] = df_sinc['Hora'].dt.time
                    
                    # Salva a aba sincronizada
                    df_sinc.to_excel(writer, sheet_name=sheet, index=False)
                else:
                    # --- CÓPIA SIMPLES (Para as outras abas) ---
                    df_sheet.to_excel(writer, sheet_name=sheet, index=False)
                    
        return True

    except Exception as e:
        st.error(f"Erro no processamento multi-aba: {e}")
        return False
    
def carregar_desligamentos_e_aterramento(): #upload_localizador,upload_aterr,upload_desl
    st.subheader("⚙️ Configuração de Dados")

    # Caminhos Fixos (Conforme sua estrutura)
    p1 = r'D:\09 - Desenvolvimento de Softwares\Python\Localizacaodetorres\Planilha1.xlsx'
    p2 = r'D:\09 - Desenvolvimento de Softwares\Python\Localizacaodetorres\Planilha2.xlsx'
    ARQ_DESL = r'D:\09 - Desenvolvimento de Softwares\Python\Localizacaodetorres\Desligamentos forçados Taesa.xlsx'
    ARQ_ATERR = "Controle Resistência Aterramento.xlsx"
    DEFAULT_EXCEL_PATH = "Localizador de Vão.xlsx"

    # --- MOMENTO 1: PROCESSAMENTO AUTOMÁTICO ---
    # Rodamos o processamento antes de qualquer carregamento
    sucesso_etl = processar_e_salvar_desligamentos(p1, p2, ARQ_DESL)
    if sucesso_etl:
        st.success("✅ Base de Desligamentos sincronizada.")

    # --- MOMENTO 2: CARREGAMENTO DOS ARQUIVOS (Upload ou Local) ---
    upload_localizador = st.file_uploader("Upload: Localizador de Vão", type=["xlsx"], key="upl_localizador")
    upload_aterr = st.file_uploader("Upload: Medição de Aterramento", type=["xlsx"], key="upl_aterr")
    upload_desl = st.file_uploader("Upload: Desligamentos Forçados", type=["xlsx"], key="upl_desl")
   
        # for key in st.session_state.keys():
        #     del st.session_state[key]
        # st.rerun()
   

    #origem = "Arquivo padrão"
    source_localizador = None
    source_aterr = None
    df_raw = pd.DataFrame()
    df_aterr = pd.DataFrame()
    df_desl = pd.DataFrame()
    df_desl_dados = pd.DataFrame()

    # -------------- 1. CARREGAR LOCALIZADOR --------------------
    if upload_localizador:
        df_raw = load_sheet_from_path_or_buffer(upload_localizador, sheet_name="DADOS")
        source_localizador = upload_localizador
    elif os.path.exists(DEFAULT_EXCEL_PATH):
        df_raw = load_sheet_from_path_or_buffer(DEFAULT_EXCEL_PATH, sheet_name="DADOS")
        source_localizador = DEFAULT_EXCEL_PATH

    # -------------- 2. CARREGAR ATERRAMENTO --------------------
    if upload_aterr:
        df_aterr = _read_first_sheet(upload_aterr)
        source_aterr = upload_aterr
    elif os.path.exists(ARQ_ATERR):
        df_aterr = _read_first_sheet(ARQ_ATERR)
        source_aterr = ARQ_ATERR

    # -------------- 3. CARREGAR DESLIGAMENTOS (GERADO NO PASSO 1) ---
    try:
        # Se houver upload, ele tem prioridade. Se não, usa o arquivo gerado pelo processamento automático.
        target_desl = upload_desl if upload_desl else (ARQ_DESL if os.path.exists(ARQ_DESL) else None)
        
        if target_desl:
            xls = pd.ExcelFile(target_desl)
            df_desl = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
            if "Dados" in xls.sheet_names:
                df_desl_dados = pd.read_excel(xls, sheet_name="Dados")
            #origem = "Sincronizado via D:/" if not upload_desl else "Upload"
        else:
            st.sidebar.warning("Base de Desligamentos não encontrada.")
            
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar Desligamentos: {e}")

    return df_raw, df_aterr, df_desl, df_desl_dados, source_localizador, source_aterr

 
    
def main():
    # 1. Primeiro definimos o menu
    escolha = option_menu(
        menu_title=None,
        options=["📌 Home","📊 Análises","🧠 Chat LLM","📍 Localização de Torres","🗺️ Medição de Aterramento","⚙️ Configurações"],
        default_index=0,
        orientation="horizontal",
    )

    # 2. ROTEAMENTO DAS ABAS
    if escolha == "📌 Home":
        # CHAME AQUI para aparecer apenas na Home
        df_raw, df_aterr, df_desl, df_desl_dados, source_loc, source_aterr = carregar_desligamentos_e_aterramento()
        
        # SALVANDO NO SESSION_STATE PARA NÃO PERDER AO MUDAR DE ABA
        st.session_state['df_localizador'] = source_loc    # Este é o dataframe que a aba_localizacao espera
        st.session_state['df_aterramento'] = df_aterr
        st.session_state['df_analise'] = df_desl
        st.session_state['dados_carregados'] = True
        
        st.write("### Bem-vindo ao Sistema!")
        if st.button("🗑️ Limpeza Total do Cache"):
            st.cache_data.clear()
            st.rerun()

    elif escolha == "📊 Análises":
        # Tenta pegar do session_state ou do arquivo sincronizado
        df_para_analise = st.session_state.get("df_analise")
        
        if df_para_analise is not None and not df_para_analise.empty:
            aba_analises(df_para_analise)
        else:
            # Caso o usuário vá direto para Análises sem passar pela Home
            st.info("Sincronizando dados automáticos para análise...")
            # Aqui chamamos apenas a leitura silenciosa ou pedimos para ir na Home
            _, _, df_desl, _, _, _, _ = carregar_desligamentos_e_aterramento()
            aba_analises(df_desl)
    elif escolha == "🧠 Chat LLM":
        # Tenta pegar do session_state ou do arquivo sincronizado
        df_para_analise = st.session_state.get("df_analise")
        
        if df_para_analise is not None and not df_para_analise.empty:
            aba_llm(df_para_analise)
        else:
            # Caso o usuário vá direto para Análises sem passar pela Home
            st.info("Sincronizando dados automáticos para análise...")
            # Aqui chamamos apenas a leitura silenciosa ou pedimos para ir na Home
            _, _, df_desl, _, _, _, _ = carregar_desligamentos_e_aterramento()
            aba_llm(df_desl)

    elif escolha == "📍 Localização de Torres":
        # RECUPERANDO O DATAFRAME CORRETO
        aba_localizacao(st.session_state.get("df_localizador"))
        
        # if df_para_torres is not None and not df_para_torres.empty:
        #     aba_localizacao(df_para_torres) 
        # else:
        #    # _, _, _, _, _, source_loc, _ = carregar_desligamentos_e_aterramento()
        #     st.warning("⚠️ O DataFrame do Localizador está vazio ou não foi carregado na Home.")
        #     aba_localizacao(source_loc)

    elif escolha == "🗺️ Medição de Aterramento":
        # Chamada da sua aba de aterramento
        aba_aterramento(st.session_state.get("df_aterr"))
        st.info("Área de Medição de Aterramento")

    elif escolha == "⚙️ Configurações":
        aba_config()
        # st.title("⚙️ Configurações do Sistema")
        
        # st.subheader("🔑 Credenciais da API")
        # # Campo para inserir a API Key
        # chave_input = st.text_input("Insira sua API Key (Gemini/OpenAI):", 
        #                             value=st.session_state.api_key, 
        #                             type="password",
        #                             help="A chave será mantida apenas durante esta sessão.")
        
        # if st.button("Salvar Configurações"):
        #     st.session_state.api_key = chave_input
        #     st.success("Configurações salvas com sucesso!")

        # st.divider()
        # st.subheader("🛠️ Parâmetros Técnicos")
        # st.write("Versão do Sistema: 2.0")
        # st.write(f"Origem dos dados: {st.session_state.get('origem', 'Não carregado')}")

if __name__ == "__main__":
    main()
