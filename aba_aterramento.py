import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px # Importação para gráficos interativos
import re


def aba_aterramento(source):
    # 1. CONFIGURAÇÃO INICIAL E FUNÇÕES AUXILIARES
    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------

    # --- CONSTANTES DE ARQUIVO PARA ANÁLISE ---
    RESISTENCIA_FILE = "Controle Resistência Aterramento.xlsx"
    OCORRENCIAS_FILE = "Desligamentos forçados Taesa.xlsx"


    # Função para extrair o número da torre (limpa 'Torre', 'T', e espaços)
    def extrair_numero_torre(texto):
        """Extrai o ID numérico da torre do campo de texto, como 'Torre 019' ou 'T368 (km 210,5)'."""
        if pd.isna(texto):
            return None
        
        texto = str(texto).strip()
        # Remove 'Torre' e 'T' no início, e extrai o primeiro número
        
        # Tenta encontrar o número da torre no início da string
        match = re.search(r'^\d+', texto)
        if match:
            return match.group(0).lstrip('0')
        
        return None


    @st.cache_data
    def load_data_analise():
        """Carrega as planilhas de Resistência e Desligamentos para a análise."""
        try:
            # Carregar dados de Resistência de Aterramento
            # Assumindo que o arquivo está na pasta local
            df_resistencia = pd.read_excel(RESISTENCIA_FILE, sheet_name='LT Torre', header=0) # Nome da planilha de Resistência
            df_resistencia.columns = ['ID', 'Linha de Transmissão', 'Número Operação', 'Tipo de Torre', 'Fase de Aterramento', 'Data da medição da resistência do aterramento', 
                                    'Última Medição Resistência de aterramento (Ω)', 'Supervisor', 'Melhoria Aterramento', 'Data Medição', 'Medição Paralelo Antes (Ω)', 
                                    'Medição Paralelo Depois (Ω)', 'Medição Oposto Antes (Ω)', 'Medição Oposto Depois (Ω)', 'Fases Implementadas']
            
            # Carregar dados de Desligamentos Forçados (ajustando o cabeçalho)
            df_ocorrencias = pd.read_excel(OCORRENCIAS_FILE, sheet_name='Ocorrências', header=0) # Nome da planilha de Ocorrências
            
            # Limpeza na coluna de resistência
            df_resistencia['Última Medição Resistência de aterramento (Ω)'] = pd.to_numeric(
                df_resistencia['Última Medição Resistência de aterramento (Ω)'], errors='coerce'
            )
            
            # Limpeza na coluna de data de desligamento
            df_ocorrencias['Data'] = pd.to_datetime(df_ocorrencias['Data'], errors='coerce')
            
            return df_resistencia, df_ocorrencias
        except FileNotFoundError:
            # Não para o app, apenas retorna DFs vazios se os arquivos de análise não existirem
            return pd.DataFrame(), pd.DataFrame()
        except ValueError as e:
            # Captura erro se o nome da aba não for encontrado
            st.error(f"❌ Erro ao carregar planilhas: Verifique se o arquivo '{RESISTENCIA_FILE}' tem uma aba chamada 'LT Torre' e se o arquivo '{OCORRENCIAS_FILE}' tem uma aba chamada 'Ocorrências'. Detalhe: {e}")
            return pd.DataFrame(), pd.DataFrame()


    @st.cache_data
    def prepare_and_merge_data(df_resistencia, df_ocorrencias):
        """Prepara os dados para o cruzamento e realiza o merge."""
        
        # 1. Normalizar ID da Torre nos Desligamentos
        df_ocorrencias['Torre_ID_Normalizada'] = df_ocorrencias['Torre'].apply(extrair_numero_torre)
        df_ocorrencias_filtradas = df_ocorrencias.dropna(subset=['Torre_ID_Normalizada'])
        
        # 2. Contar desligamentos por Torre e LT (FT)
        # FT é o nome da coluna de Linha de Transmissão no arquivo de Ocorrências (provavelmente abreviação de Função Transmissão)
        contagem_desligamentos_lt = df_ocorrencias_filtradas.groupby(['Torre_ID_Normalizada', 'FT']).size().reset_index(name='Contagem_Desligamentos')
        
        # 3. Normalizar ID da Torre na Resistência
        df_resistencia['Número Operação Normalizado'] = df_resistencia['Número Operação'].astype(str).str.strip().str.lstrip('0')
        
        # 4. Realizar o Merge (Cruzamento)
        # Nota: O nome da LT no arquivo de Ocorrências é 'FT' e no de Resistência é 'Linha de Transmissão'. O cruzamento é feito pela Torre.
        df_cruzado = pd.merge(
            contagem_desligamentos_lt, 
            df_resistencia[['Número Operação Normalizado', 'Linha de Transmissão', 'Última Medição Resistência de aterramento (Ω)', 'Melhoria Aterramento', 'Data da medição da resistência do aterramento']], 
            left_on='Torre_ID_Normalizada', 
            right_on='Número Operação Normalizado', 
            how='inner'
        ).drop(columns=['Número Operação Normalizado']).drop_duplicates(subset=['Torre_ID_Normalizada', 'FT'], keep='first')
        
        return df_cruzado


    # Carrega os dados de análise apenas uma vez
    df_resistencia, df_ocorrencias = load_data_analise()

    # Processa o cruzamento
    if not df_resistencia.empty and not df_ocorrencias.empty:
        df_cruzado = prepare_and_merge_data(df_resistencia, df_ocorrencias)
    else:
        df_cruzado = pd.DataFrame()
        
    @st.cache_data
    def load_data_analise():
        """Carrega as planilhas de Resistência e Desligamentos para a análise."""
        try:
            # Carregar dados de Resistência de Aterramento
            # Assumindo que o arquivo está na pasta local
            df_resistencia = pd.read_excel(RESISTENCIA_FILE, sheet_name='LT Torre', header=0) # Nome da planilha de Resistência
            df_resistencia.columns = ['ID', 'Linha de Transmissão', 'Número Operação', 'Tipo de Torre', 'Fase de Aterramento', 'Data da medição da resistência do aterramento', 
                                    'Última Medição Resistência de aterramento (Ω)', 'Supervisor', 'Melhoria Aterramento', 'Data Medição', 'Medição Paralelo Antes (Ω)', 
                                    'Medição Paralelo Depois (Ω)', 'Medição Oposto Antes (Ω)', 'Medição Oposto Depois (Ω)', 'Fases Implementadas']
            
            # Carregar dados de Desligamentos Forçados (ajustando o cabeçalho)
            df_ocorrencias = pd.read_excel(OCORRENCIAS_FILE, sheet_name='Ocorrências', header=0) # Nome da planilha de Ocorrências
            
            # Limpeza na coluna de resistência
            df_resistencia['Última Medição Resistência de aterramento (Ω)'] = pd.to_numeric(
                df_resistencia['Última Medição Resistência de aterramento (Ω)'], errors='coerce'
            )
            
            # Limpeza na coluna de data de desligamento
            df_ocorrencias['Data'] = pd.to_datetime(df_ocorrencias['Data'], errors='coerce')
            
            return df_resistencia, df_ocorrencias
        except FileNotFoundError:
            # Não para o app, apenas retorna DFs vazios se os arquivos de análise não existirem
            return pd.DataFrame(), pd.DataFrame()
        except ValueError as e:
            # Captura erro se o nome da aba não for encontrado
            st.error(f"❌ Erro ao carregar planilhas: Verifique se o arquivo '{RESISTENCIA_FILE}' tem uma aba chamada 'LT Torre' e se o arquivo '{OCORRENCIAS_FILE}' tem uma aba chamada 'Ocorrências'. Detalhe: {e}")
            return pd.DataFrame(), pd.DataFrame()
        

    # ----------------------------------------------------------------------
    # Funções de Geração de Gráficos (Plotly)
    # ----------------------------------------------------------------------

    def plot_resistance_vs_shutdowns(df_cruzado):
        """Cria o gráfico de dispersão da Resistência vs. Desligamentos, colorido por LT (FT)."""
        fig = px.scatter(
            df_cruzado,
            x='Última Medição Resistência de aterramento (Ω)',
            y='Contagem_Desligamentos',
            color='FT',
            size='Contagem_Desligamentos',
            hover_data={'Torre_ID_Normalizada': True, 'Melhoria Aterramento': True, 'Última Medição Resistência de aterramento (Ω)': ':.2f'},
            title='Dispersão: Resistência de Aterramento vs. Desligamentos por Torre e LT',
            labels={'Última Medição Resistência de aterramento (Ω)': 'Resistência de Aterramento (Ω)', 
                    'Contagem_Desligamentos': 'Nº de Desligamentos Forçados'},
            height=500
        )
        fig.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey')))
        fig.update_layout(xaxis_tickformat='.2f')
        return fig

    def plot_shutdown_count_by_lt(df_cruzado):
        """Cria o gráfico de barras da contagem total de desligamentos por LT (FT)."""
        contagem_lt = df_cruzado.groupby('FT')['Contagem_Desligamentos'].sum().reset_index(name='Total Desligamentos')
        
        fig = px.bar(
            contagem_lt,
            x='FT',
            y='Total Desligamentos',
            color='FT',
            title='Total de Desligamentos (com Resistência Conhecida) por Linha de Transmissão (FT)',
            labels={'FT': 'Linha de Transmissão', 'Total Desligamentos': 'Total de Desligamentos (Ocorrências)'},
            text='Total Desligamentos'
        )
        fig.update_layout(xaxis={'categoryorder':'total descending'})
        return fig

    def plot_resistance_histogram(df_resistencia_filtrada):
        """Cria o histograma da distribuição de resistência de aterramento."""
        fig = px.histogram(
            df_resistencia_filtrada.dropna(subset=['Última Medição Resistência de aterramento (Ω)']),
            x='Última Medição Resistência de aterramento (Ω)',
            title='Distribuição da Resistência de Aterramento',
            labels={'Última Medição Resistência de aterramento (Ω)': 'Resistência de Aterramento (Ω)'},
            nbins=50,
            height=400
        )
        fig.update_layout(bargap=0.1)
        return fig

    def get_top_causas(df):
        """Calcula o Top 20 de causas de desligamento por frequência."""
        # Pressupõe coluna 'Causa'
        if 'Causa' not in df.columns: return pd.DataFrame()
        return df['Causa'].value_counts().nlargest(20).reset_index(name='Total_Desligamentos')

    def get_resistencia_media_causa(df):
        """Calcula a resistência média de aterramento por causa (Top 20)."""
        # Pressupõe colunas 'Causa' e 'ResistenciaAterramento'
        if 'Causa' not in df.columns or 'ResistenciaAterramento' not in df.columns: return pd.DataFrame()
        return df.groupby('Causa')['ResistenciaAterramento'].mean().nlargest(20).reset_index(name='Resistencia_Media')

    def get_torres_criticas(df):
        """Calcula o Score de Criticidade (Frequência * Resistência Média)."""
        # Pressupõe colunas 'Torre', 'ResistenciaAterramento'
        if 'Torre' not in df.columns or 'ResistenciaAterramento' not in df.columns: return pd.DataFrame()
        
        freq_falhas = df['Torre'].value_counts().reset_index(name='Frequencia_Falhas')
        media_resistencia = df.groupby('Torre')['ResistenciaAterramento'].mean().reset_index(name='Resistencia_Media')
        df_score = pd.merge(freq_falhas, media_resistencia, on='Torre')
        df_score['Score_Criticidade'] = df_score['Frequencia_Falhas'] * df_score['Resistencia_Media'] 
        return df_score.sort_values('Score_Criticidade', ascending=False).head(20)

    def get_falhas_por_torre(df):
        """Calcula o Top 20 de torres por frequência de falhas (pura)."""
        # Pressupõe coluna 'Torre'
        if 'Torre' not in df.columns: return pd.DataFrame()
        return df['Torre'].value_counts().nlargest(20).reset_index(name='Total_Falhas')


    if not df_resistencia.empty:
            # --- FILTROS NA SIDEBAR PARA A ABA DE ATERRAMENTO ---
            st.header("⚙️ Filtros de Aterramento")
            
            # 1. Filtro por Linha de Transmissão
            todas_lts_resistencia = sorted(df_resistencia['Linha de Transmissão'].astype(str).unique())
            lt_selecionada = st.selectbox(
                "🔹 Linha de Transmissão:", 
                ['Todas'] + todas_lts_resistencia,
                key='filter_lt_resistencia'
            )

            # 2. Filtro por Faixa de Resistência
            # Filtra o DataFrame de acordo com a seleção
            df_filtrado = df_resistencia[df_resistencia['Linha de Transmissão'] == lt_selecionada]
           # Calcula min e max apenas do DataFrame filtrado
            if not df_filtrado.empty:
                min_resistencia = float(df_filtrado['Última Medição Resistência de aterramento (Ω)'].min())
                max_resistencia = float(df_filtrado['Última Medição Resistência de aterramento (Ω)'].max())
            else:
                min_resistencia = 0.0
                max_resistencia = 999.0
                
            # Arredonda para o inteiro mais próximo para o slider, mas mantém o float para a filtragem
            resistencia_range = st.slider(
                '🔹 Faixa de Resistência (Ω):',
                min_value=max(0.0, float(np.floor(min_resistencia))), 
                max_value=float(np.ceil(max_resistencia)), 
                value=(max(0.0, float(np.floor(min_resistencia))), float(np.ceil(max_resistencia))),
                step=0.1,
                key='filter_resistencia_range'
            )
            
            # --- APLICAR OS FILTROS ---
            df_resistencia_filtrada = df_resistencia.copy()

            # Filtrar por LT
            if lt_selecionada != 'Todas':
                df_resistencia_filtrada = df_resistencia_filtrada[df_resistencia_filtrada['Linha de Transmissão'] == lt_selecionada]
            
            # Filtrar por Faixa de Resistência
            df_resistencia_filtrada = df_resistencia_filtrada[
                (df_resistencia_filtrada['Última Medição Resistência de aterramento (Ω)'] >= resistencia_range[0]) &
                (df_resistencia_filtrada['Última Medição Resistência de aterramento (Ω)'] <= resistencia_range[1])
            ]
            
            # --- EXIBIÇÃO DOS DADOS FILTRADOS ---
            st.info(f"Mostrando **{len(df_resistencia_filtrada)}** medições filtradas.")
            
            # 1. Histograma
            if not df_resistencia_filtrada.empty:
                st.subheader("Distribuição da Resistência de Aterramento")
                st.plotly_chart(plot_resistance_histogram(df_resistencia_filtrada), use_container_width=True)
                
                # 2. Tabela Filtrada
                st.subheader("Detalhes das Medições de Aterramento")
                # Seleciona colunas principais para melhor visualização
                colunas_principais = [
                    'Linha de Transmissão', 'Número Operação', 
                    'Última Medição Resistência de aterramento (Ω)', 
                    'Data da medição da resistência do aterramento', 'Melhoria Aterramento'
                ]
                
                st.dataframe(df_resistencia_filtrada[colunas_principais], use_container_width=True)
            else:
                st.warning("Nenhuma medição encontrada com os filtros aplicados.")

    else:
        st.error(f"❌ Não foi possível carregar a planilha de Resistência de Aterramento: **'{RESISTENCIA_FILE}'**.")
        # Limpa o cabeçalho da sidebar se não houver dados para filtrar
        st.sidebar.empty()