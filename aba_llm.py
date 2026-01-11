import streamlit as st
import pandas as pd
from openai import OpenAI

# --- UTILITÁRIO PARA GARANTIR UM DATAFRAME ---
def ensure_dataframe(obj):
    """Normaliza qualquer entrada para um único DataFrame."""
    if obj is None:
        return pd.DataFrame()
    if isinstance(obj, tuple):
        obj = obj[0]
    if isinstance(obj, pd.DataFrame):
        return obj
    if isinstance(obj, dict):
        return list(obj.values())[0]
    raise TypeError(f"Tipo não suportado em ensure_dataframe: {type(obj)}")


def aba_llm(df_desligamentos_all):
    st.title("🧠 Chat LLM – Consultas Inteligentes")

    # --- 1. NORMALIZAÇÃO ---
    try:
        df_deslig = ensure_dataframe(df_desligamentos_all)
    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return

    if df_deslig.empty:
        st.error("A planilha está vazia.")
        return

    # --- 2. CONFIGURAÇÃO DA API ---
    api_key = st.session_state.get("api_key")
    if not api_key:
        st.info("⚠️ Configure sua API Key na aba **⚙️ Configurações**.")
        return

    client = OpenAI(api_key=api_key)

    # --- 3. PRÉ-PROCESSAMENTO PARA REDUZIR TOKENS ---
    # Selecionamos apenas as colunas vitais para a análise
    colunas_interesse = ['Concessão', 'Data', 'FT', 'Causa', 'Equipamento', 'Fase']
    
    # Filtra apenas as colunas que realmente existem no seu DataFrame
    colunas_presentes = [c for c in colunas_interesse if c in df_deslig.columns]
    df_reduzido = df_deslig[colunas_presentes].copy()

    # Limitamos a 400 linhas (200 do topo + 200 do fim) para não estourar o TPM
    if len(df_reduzido) > 400:
        df_contexto = pd.concat([df_reduzido.head(200), df_reduzido.tail(200)])
        nota_limite = f"\n(Nota: Exibindo amostra de 400 linhas de um total de {len(df_deslig)})."
    else:
        df_contexto = df_reduzido
        nota_limite = ""

    # Converte para Markdown (formato que o GPT entende melhor estrutura de tabela)
    texto_planilha = df_contexto.to_markdown(index=False)

    # --- 4. CONFIGURAÇÃO DO SISTEMA ---
    system_prompt = f"""
Você é um especialista em análise de desligamentos de Linhas de Transmissão.
Responda com base nesta amostra de dados:
{nota_limite}

### DADOS:
{texto_planilha}

Regras:
- Se a resposta exigir dados que não estão nesta amostra, peça ao usuário para ser mais específico ou usar os filtros dos gráficos.
- Sempre cite a 'Fase' e a 'Causa' ao detalhar um evento.
"""

    # --- 5. INTERFACE DE CHAT ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.sidebar.markdown("### 🤖 Configurações")
    modelo = st.sidebar.selectbox("Modelo:", ['gpt-4o-mini', 'gpt-4o'])
    if st.sidebar.button("Limpar Conversa"):
        st.session_state.messages = []
        st.rerun()

    # Exibir histórico
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Entrada do usuário
    if pergunta := st.chat_input("Pergunte sobre os desligamentos ou fases..."):
        st.session_state.messages.append({"role": "user", "content": pergunta})
        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.chat_message("assistant"):
            try:
                # Prepara as mensagens incluindo o contexto atualizado
                mensagens_com_contexto = [{"role": "system", "content": system_prompt}] + st.session_state.messages
                
                response = client.chat.completions.create(
                    model=modelo,
                    messages=mensagens_com_contexto,
                    temperature=0
                )
                
                resposta = response.choices[0].message.content
                st.markdown(resposta)
                st.session_state.messages.append({"role": "assistant", "content": resposta})
                
            except Exception as e:
                st.error(f"Erro na API: {e}")
                
                
# def aba_llm(df_desligamentos_all):

#     st.title("🧠 Chat LLM – Consultas à Planilha de Desligamentos")

#     # --- NORMALIZA O DATAFRAME ---
#     try:
#         df_deslig = ensure_dataframe(df_desligamentos_all)
#     except Exception as e:
#         st.error(f"Erro ao interpretar os dados de desligamentos: {e}")
#         return

#     if df_deslig.empty:
#         st.error("A planilha de desligamentos está vazia ou não pode ser processada.")
#         return

#     # --- CONFIGURAÇÃO DO MODELO NA BARRA LATERAL ---
#     st.sidebar.markdown("### ⚙️ Configurações do Chat")
#     lista_modelos = ['gpt-4o-mini', 'gpt-4o']
#     modelo_selecionado = st.sidebar.selectbox("Escolha o modelo LLM:", lista_modelos)

#     # --- API KEY ---
#     api_key = st.session_state.get("api_key", "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")

#     if not api_key or api_key == "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":
#         st.warning("Configure sua API Key na aba ⚙️ Configurações.")
#         return

#     client = OpenAI(api_key=api_key)

#     # --- CONVERTE A PLANILHA EM TEXTO FORMATADO (RAG) ---
#     try:
#         # Markdown é excelente para o LLM entender a estrutura de tabelas
#         texto_planilha = df_deslig.to_markdown(index=False)
#     except Exception:
#         texto_planilha = df_deslig.to_csv(index=False)

#     system_prompt = f"""
# Você é um especialista em análise de desligamentos forçados de Linhas de Transmissão.
# Use EXCLUSIVAMENTE os dados da tabela abaixo para responder às perguntas.

# ### DADOS DA PLANILHA:
# {texto_planilha}

# Regras:
# - Responda sempre citando os valores encontrados.
# - Se a informação não existir na tabela, diga claramente.
# - Nunca invente dados ou valores.
# """

#     st.markdown(f"**Modelo ativo:** `{modelo_selecionado}`")
#     st.markdown("### 🔍 Pergunte algo sobre os desligamentos")
#     pergunta = st.text_area("", placeholder="Ex.: Quais foram os desligamentos causados por queimadas em 2025?")

#     if st.button("Consultar"):
#         if not pergunta.strip():
#             st.warning("Digite uma pergunta.")
#             return

#         try:
#             with st.spinner(f"Consultando {modelo_selecionado}..."):
#                 # Chamada correta da API OpenAI Chat Completion
#                 response = client.chat.completions.create(
#                     model=modelo_selecionado,
#                     messages=[
#                         {"role": "system", "content": system_prompt},
#                         {"role": "user", "content": pergunta},
#                     ],
#                     temperature=0 # Temperatura 0 para evitar alucinações em dados reais
#                 )

#                 conteudo = response.choices[0].message.content
#                 st.markdown("### 📌 Resposta")
#                 st.markdown(conteudo)

#         except Exception as e:
#             st.error(f"Erro ao consultar o modelo: {e}")

# # --- Próximo passo sugerido ---
# # Deseja que eu implemente uma funcionalidade para o LLM gerar gráficos automaticamente com base na pergunta do usuário?