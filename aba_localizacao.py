import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import re
from io import BytesIO
from collections import defaultdict

def _excel_file_and_sheets_from_source(source):
    """
    Dado source (str caminho ou UploadedFile / file-like),
    retorna (excel_file_like, sheet_names_list, bytes_data_if_buffer)
    excel_file_like pode ser usado em pd.read_excel(excel_file_like, sheet_name=...)
    Se source for UploadedFile, retornamos também os bytes (data) para múltiplas leituras.
    """
    if isinstance(source, str):
        # caminho local
        excel_path = source
        excel_file_like = excel_path
        sheet_names = pd.ExcelFile(excel_path).sheet_names
        return excel_file_like, sheet_names, None
    else:
        # file-like (UploadedFile)
        try:
            source.seek(0)
        except Exception:
            pass
        data = source.read()
        buf = BytesIO(data)
        sheet_names = pd.ExcelFile(buf).sheet_names
        # note: for further reads we'll use BytesIO(data) again
        return data, sheet_names, data

def aba_localizacao(source):
    """
    Aba de localização de torres.
    source: caminho (str) ou UploadedFile (file-like)
    """

    st.header("📍 Localização de Torres")

    if source is None:
        st.info("Carregue um arquivo Excel na sidebar para usar esta aba.")
        return

    try:
        excel_file_like, abas, buffer_bytes = _excel_file_and_sheets_from_source(source)
        # st.write("buffer_bytes",buffer_bytes)
        # st.write("abas",list(abas))
    except Exception as e:
        st.error(f"Erro ao abrir o arquivo Excel: {e}")
        return

    # --- Leitura da aba Dados ---
    try:
        if buffer_bytes is None:
            df_dados = pd.read_excel(excel_file_like, sheet_name="DADOS").fillna("")
            #st.write("dados", list(df_dados))
        else:
            df_dados = pd.read_excel(BytesIO(buffer_bytes), sheet_name="DADOS").fillna("")
    except Exception as e:
        st.error(f"Erro ao ler a aba 'DADOS': {e}")
        return

    if "CONCESSÕES" not in df_dados.columns or "LT" not in df_dados.columns:
        st.error("❌ A aba 'DADOS' deve conter exatamente as colunas 'CONCESSÕES' e 'LT'.")
        return

    df_dados["CONCESSÕES"] = df_dados["CONCESSÕES"].astype(str).str.strip()
    df_dados["LT"] = df_dados["LT"].astype(str).str.strip()

    todas_concessoes = sorted(df_dados["CONCESSÕES"].unique().tolist())
    todas_concessoes = [c for c in todas_concessoes if c != ""]

    # --- Leitura da aba KM_LT ---
    comprimento = None
    terminal_a = "Não Encontrado"
    if "KM_LT" in abas:
        try:
            if buffer_bytes is None:
                df_km = pd.read_excel(excel_file_like, sheet_name="KM_LT").fillna("")
            else:
                df_km = pd.read_excel(BytesIO(buffer_bytes), sheet_name="KM_LT").fillna("")
        except Exception:
            df_km = pd.DataFrame()
    else:
        df_km = pd.DataFrame()

    # -----------------------------------------------------------
    # LÓGICA: IDENTIFICAR COLUNAS NA KM_LT (COLUNA A, B, C)
    # -----------------------------------------------------------
    if not df_km.empty and len(df_km.columns) >= 3:
        lt_col_km_lt = df_km.columns[0]  # Coluna A: LT
        km_col_km_lt = df_km.columns[1]  # Coluna B: KM (Comprimento)
        terminal_a_col = df_km.columns[2]  # Coluna C: Terminal A
    else:
        lt_col_km_lt = "LT"
        km_col_km_lt = "KM"
        terminal_a_col = "Terminal A"
        if "KM_LT" in abas and df_km.empty:
            st.warning("⚠️ A aba 'KM_LT' está vazia ou não tem as colunas esperadas (A, B, C).")

    # --- CARREGAMENTO DO MAPA DE TORRES JBJU (MANTIDO) ---
    torres_jbju_map = {}
    if "Torres JBJU" in abas:
        try:
            if buffer_bytes is None:
                df_jbju = pd.read_excel(excel_file_like, sheet_name="Torres JBJU").fillna("")
            else:
                df_jbju = pd.read_excel(BytesIO(buffer_bytes), sheet_name="Torres JBJU").fillna("")
        except Exception:
            df_jbju = pd.DataFrame()

        if not df_jbju.empty and len(df_jbju.columns) >= 5:
            df_jbju.columns = [str(c).strip().lower().replace(' ', '') for c in df_jbju.columns]

            codigo_col_jbju = df_jbju.columns[0]
            figura_col_jbju = df_jbju.columns[1]
            sequencia_col_jbju = df_jbju.columns[2]
            imagem_col_jbju = df_jbju.columns[4]

            torres_jbju_map = df_jbju.set_index(codigo_col_jbju).apply(
                lambda row: (str(row[figura_col_jbju]).strip(), str(row[sequencia_col_jbju]).strip().upper(),
                             str(row[imagem_col_jbju]).strip()), axis=1
            ).to_dict()
        else:
            if "Torres JBJU" in abas:
                st.warning("⚠️ A aba 'Torres JBJU' deve ter pelo menos 5 colunas para ler o Caminho da Imagem da COLUNA E. (A, B, C, D, E)")

    # 1. Concessão
    col1,col2,col3,col4,col5=st.columns([1,1,1,1,1])
    with col1:
        concessao_escolhida = st.selectbox("🔹 CONCESSÃO:", todas_concessoes, key='filter_concessao_localizacao')

    # 2. LT
    lt_escolhida = None
    if concessao_escolhida:
        df_filtrado_lt = df_dados[
            (df_dados["CONCESSÕES"] == concessao_escolhida) &
            (df_dados["LT"] != "")
        ]
        lts = sorted(df_filtrado_lt["LT"].unique().tolist())
        with col2:
            lt_escolhida = st.selectbox("🔹 LT:", lts, key='filter_lt_localizacao') if lts else None

    # 3. Fase e Método (Colunas dentro da sidebar)
  
    with col3:
        fase_escolhida = st.selectbox("🔹 Fase Defeito:", ['AG', 'BG', 'CG'], key='filter_fase_localizacao')
    with col4:
        metodo = st.selectbox("⚙️ Método:",
                                    ["Sequência Negativa", "TW", "SIGRA 1 Terminal", "SIGRA 2 Terminais"],
                                    key='filter_metodo_localizacao')

    # 4. KM de Busca
    with col5:
        valor_busca = st.number_input(
            "🎯 KM de Busca:",
            min_value=0.0,
            step=0.1,
            format="%.2f",
            value=0.0,
            help="Distância em KM a partir do Terminal A.",
            key='filter_km_localizacao'
        )

    # ==========================================================
    # >>> LAYOUT DA SIDEBAR: TERMINAL A e COMPRIMENTO <<<
    # ==========================================================
    if lt_escolhida and not df_km.empty:
        if lt_col_km_lt in df_km.columns and terminal_a_col in df_km.columns and km_col_km_lt in df_km.columns:
            df_km[lt_col_km_lt] = df_km[lt_col_km_lt].astype(str).str.strip()
            linha_lt_km = df_km[df_km[lt_col_km_lt] == str(lt_escolhida).strip()]

            if not linha_lt_km.empty:
                terminal_a = str(linha_lt_km[terminal_a_col].iloc[0]).strip()
                try:
                    comprimento = pd.to_numeric(linha_lt_km[km_col_km_lt].iloc[0])
                except Exception:
                    comprimento = None

    
    col11,col12,col13=st.columns([2,2,2])
    with col11:
        st.header("Informações da Linha")
    with col12:
        st.text_input(
            "📍 Distância Calculada a Partir do Terminal A:",
            value=terminal_a,
            disabled=True,
            help="Este campo é apenas para visualização e confirma que o 'KM de Busca' deve ser medido a partir deste Terminal."
        )
    with col13:
        if comprimento is not None:
            st.metric(label="📏 Comprimento (km)", value=f"{comprimento:.2f}")
        else:
            st.warning("Comprimento N/D", icon="⚠️")

    #st.markdown("---")
    
    # ==========================================================
    # >>> LAYOUT DA ÁREA PRINCIPAL: GRÁFICO, TABELA E IMAGEM <<<
    # ==========================================================
    if lt_escolhida:
        st.markdown("### 📈 Representação da Sequência de Fases")

        graph_placeholder = st.empty()
        col_btn, col_gap_btn = st.columns([1, 5])
        with col_btn:
            plotar_clicado = st.button("🔍 Plotar Resultados")

        torres_na_janela_df = None

        if plotar_clicado and lt_escolhida in abas and valor_busca > 0:
            # prepara um buffer novo para leitura dessa aba LT específica
            try:
                if buffer_bytes is None:
                    # source is a path str
                    df_lt = pd.read_excel(excel_file_like, sheet_name=lt_escolhida)
                else:
                    df_lt = pd.read_excel(BytesIO(buffer_bytes), sheet_name=lt_escolhida)
            except Exception as e:
                graph_placeholder.error(f"❌ Erro ao ler a aba '{lt_escolhida}': {e}")
                return

            # padroniza nomes de colunas
            df_lt.columns = [str(c).strip().lower().replace(' ', '') for c in df_lt.columns]

            # Definindo colunas esperadas na aba da LT
            km_col = "km"
            desc_col = df_lt.columns[3] if len(df_lt.columns) >= 4 else "descrição"
            fase_seq_col = "fases"

            cols_ok = km_col in df_lt.columns and fase_seq_col in df_lt.columns

            if not cols_ok:
                graph_placeholder.error(f"❌ Colunas esperadas (KM e FASES) não encontradas na aba {lt_escolhida}.")
                return
            if not (len(df_lt.columns) >= 4):
                graph_placeholder.error(f"❌ A aba '{lt_escolhida}' deve ter pelo menos 4 colunas (A, B, C, D) para ler a descrição na Coluna D.")
                return

            df_lt = df_lt.dropna(subset=[km_col])
            df_lt[km_col] = pd.to_numeric(df_lt[km_col], errors="coerce")
            df_lt = df_lt.dropna(subset=[km_col]).sort_values(km_col).reset_index(drop=True)

            torre_idx = df_lt[df_lt[km_col] >= valor_busca].index

            if len(torre_idx) > 0:
                idx_central = torre_idx[0]

                start_idx = max(0, idx_central - 3)
                end_idx = min(len(df_lt) - 1, idx_central + 3)

                df_plot = df_lt.loc[start_idx:end_idx].copy()
                df_plot["x_pos"] = np.linspace(1, 9, len(df_plot))

                Y_POS_FIXED = {1: 3, 2: 2, 3: 1}
                fase_points = defaultdict(list)

                km_central = 0.0
                imagem_torre_central_excel = None
                current_code = ""

                for index, row in df_plot.iterrows():
                    x = row["x_pos"]
                    raw_seq_or_code = str(row[fase_seq_col]).strip().upper()
                    seq_fase_real = raw_seq_or_code
                    tower_label = str(row[desc_col]).strip()
                    caminho_imagem = None
                    is_brasnorte = concessao_escolhida == "BRASNORTE"

                    if is_brasnorte and raw_seq_or_code in torres_jbju_map:
                        figura_ref_jbju, seq_fase_real_map, caminho_imagem_map = torres_jbju_map.get(raw_seq_or_code, ("", raw_seq_or_code, None))
                        seq_fase_real = seq_fase_real_map
                        caminho_imagem = caminho_imagem_map

                    if index == idx_central:
                        km_central = row[km_col]
                        x_central = x
                        imagem_torre_central_excel = caminho_imagem
                        current_code = raw_seq_or_code

                    if len(seq_fase_real) == 3:
                        fases_na_torre = {
                            seq_fase_real[0]: Y_POS_FIXED[1],
                            seq_fase_real[1]: Y_POS_FIXED[2],
                            seq_fase_real[2]: Y_POS_FIXED[3]
                        }
                        for fase_letra, y_pos in fases_na_torre.items():
                            fase_points[fase_letra].append((x, y_pos))

                # Plotagem
                col_fig, col_gap = graph_placeholder.columns([3, 0.1])
                with col_fig:
                    fig, ax = plt.subplots(figsize=(12, 5))
                    ax.set_xlim(0, 10)
                    ax.set_ylim(0, 5)
                    ax.axis("off")

                    y_start_torre = 0.8
                    y_end_torre = 3.2
                    FASE_COLORS = {"A": "orange", "B": "green", "C": "purple"}

                    # 1. Desenha as Linhas de Fase (Transposição)
                    for fase_letra, points in fase_points.items():
                        if points:
                            x_coords = [p[0] for p in points]
                            y_coords = [p[1] for p in points]

                            color = FASE_COLORS.get(fase_letra, "gray")
                            linewidth = 3 if fase_letra == fase_escolhida else 1.5
                            linestyle = '-' if fase_letra == fase_escolhida else '--'

                            ax.plot(x_coords, y_coords, color=color, linewidth=linewidth, linestyle=linestyle, alpha=0.7, zorder=1)

                            if len(x_coords) > 0:
                                ax.text(x_coords[-1] + 0.1, y_coords[-1], f"Fase {fase_letra}", va="center", fontsize=10, color=color)

                    # 2. Desenha as Torres e Rótulos
                    for index, row in df_plot.iterrows():
                        x = row["x_pos"]
                        is_central = index == idx_central

                        line_color = "red" if is_central else "gray"
                        line_style = "-" if is_central else "--"
                        line_width = 3 if is_central else 1.5

                        ax.vlines(x, y_start_torre, y_end_torre,
                                  colors=line_color, linestyles=line_style, linewidth=line_width, zorder=3)

                        km_text = f"{row[km_col]:.2f} km"

                        tower_label_plot = str(row[desc_col]).strip()
                        current_code_plot = str(row[fase_seq_col]).strip().upper()
                        seq_to_display = current_code_plot

                        if is_brasnorte and current_code_plot in torres_jbju_map:
                            _, seq_fase_real, _ = torres_jbju_map[current_code_plot]
                            seq_to_display = seq_fase_real

                        ax.text(x, 0.7, f"Torre: {tower_label_plot}\n{km_text}", ha="center", fontsize=9, color=line_color if is_central else "black")

                        ax.text(x, y_end_torre + 0.1, f"Seq: {seq_to_display}", ha="center", fontsize=9,
                                bbox=dict(facecolor='white', alpha=0.8, edgecolor=line_color if is_central else 'gray', boxstyle='round,pad=0.3'),
                                zorder=4)

                    # 3. Desenha o KM de Busca (Lógica de interpolação mantida)
                    x_busca = x_central
                    if valor_busca != km_central:
                        torre_ant = df_lt[(df_lt[km_col] < valor_busca)].iloc[-1] if not df_lt[df_lt[km_col] < valor_busca].empty else None
                        torre_prox = df_lt[(df_lt[km_col] >= valor_busca)].iloc[0] if not df_lt[df_lt[km_col] >= valor_busca].empty else None

                        if torre_ant is not None and torre_prox is not None:
                            km_ant = torre_ant[km_col]
                            km_prox = torre_prox[km_col]

                            x_ant_idx = df_plot.index[df_plot[km_col] == km_ant].tolist()
                            x_prox_idx = df_plot.index[df_plot[km_col] == km_prox].tolist()

                            if x_ant_idx and x_prox_idx and km_prox > km_ant:
                                x_ant = df_plot.loc[x_ant_idx[0], "x_pos"]
                                x_prox = df_plot.loc[x_prox_idx[0], "x_pos"]

                                distancia_total = km_prox - km_ant
                                distancia_relativa = valor_busca - km_ant
                                proporcao = distancia_relativa / distancia_total
                                x_busca = x_ant + proporcao * (x_prox - x_ant)

                    ax.vlines(x_busca, y_start_torre, y_end_torre, colors="blue", linestyles="dotted", linewidth=2, zorder=5)
                    ax.text(x_busca, 0.4, f"KM de Busca: {valor_busca:.2f}", ha="center", color="blue", fontsize=10,
                            bbox=dict(facecolor='lightblue', alpha=0.7, edgecolor='blue', boxstyle='round,pad=0.3'), zorder=6)

                    # Destaque do PONTO do KM de busca na fase afetada
                    target_fase_points = fase_points.get(fase_escolhida)
                    if target_fase_points:
                        x_coords = [p[0] for p in target_fase_points]
                        y_coords = [p[1] for p in target_fase_points]
                        for i in range(len(x_coords) - 1):
                            if x_coords[i] <= x_busca <= x_coords[i + 1]:
                                x1, y1 = x_coords[i], y_coords[i]
                                x2, y2 = x_coords[i + 1], y_coords[i + 1]
                                if x2 - x1 != 0:
                                    y_busca = y1 + (y2 - y1) * (x_busca - x1) / (x2 - x1)
                                    ax.plot(x_busca, y_busca, 'o', markersize=10, color='red', markeredgecolor='black', zorder=10)
                                    break

                    st.pyplot(fig)
                    
                    col_tabela, col_imagem = st.columns([2, 2])
                    st.markdown("---") # Separador para o gráfico

                    # --- Exibição da Imagem da Torre Central ---
                    with col_imagem:
                        st.markdown("### 🖼️ Figura da Torre")
                        if imagem_torre_central_excel and imagem_torre_central_excel.strip():
                            
                            caminho_excel = imagem_torre_central_excel.strip()
                            caminho_final = os.path.normpath(caminho_excel)

                            imagem_carregada = False
                            
                            if os.path.exists(caminho_final):
                                st.image(caminho_final, caption=f"Torre {current_code}")
                            else:
                                st.warning(f"Imagem da torre ({current_code}) não encontrada no caminho: {caminho_final}")
                        else:
                            st.info("Caminho da imagem não especificado ou torre não mapeada.")

                    # --- Tabela de Torres no Vão ---
                    with col_tabela:
                        st.markdown("### 📋 Torres no Vão de Análise")
                        # Seleciona as colunas a serem exibidas para a tabela
                        torres_na_janela_df = df_plot[['km', desc_col, fase_seq_col]].rename(
                            columns={'km': 'KM', desc_col: 'Torre', fase_seq_col: 'Sequência de Fases'}
                        )
                        # Adiciona um marcador visual para a torre central
                        torres_na_janela_df['Status'] = np.where(torres_na_janela_df['KM'] == km_central, '🎯 Central', '')
                        
                        st.dataframe(torres_na_janela_df, use_container_width=True)

            else:
                graph_placeholder.warning(f"Nenhuma torre encontrada após o KM {valor_busca:.2f}. Verifique a aba '{lt_escolhida}'.")

        elif plotar_clicado and valor_busca <= 0:
            graph_placeholder.error("Por favor, insira um 'KM de Busca' válido (maior que 0).")
        elif plotar_clicado and lt_escolhida not in abas:
            graph_placeholder.error(f"❌ Não foi possível encontrar a aba '{lt_escolhida}' no arquivo principal. Verifique se o nome confere.")
    else:
        st.info("Selecione uma Concessão e uma LT para iniciar a análise de localização de torres.")

