import streamlit as st

def aba_config():
    st.header("⚙️ Configurações")
    st.write("Ajustes gerais do sistema.")

    # Campo para inserir a API Key da OpenAI
    api_key_input = st.text_input(
        "OpenAI API Key",
        value=st.session_state.get("api_key", "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"),
        type="password",
        help="Insira sua chave sk-... para habilitar as consultas na aba Chat LLM."
    )

    if st.button("Salvar Configurações"):
        if api_key_input:
            st.session_state["api_key"] = api_key_input
            st.success("API Key salva com sucesso para esta sessão!")
        else:
            st.warning("Por favor, insira uma chave válida.")