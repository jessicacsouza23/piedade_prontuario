import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURAÇÃO E CONSTANTES ---
NOME_ARQUIVO = "base_pedagogica_orgao.csv"
DATA_BLOQUEIO = datetime(2026, 4, 1).date()

st.set_page_config(page_title="Gestão Pedagógica - Órgão", layout="wide")

# --- FUNÇÕES DE DADOS ---
def carregar_dados():
    if os.path.exists(NOME_ARQUIVO):
        return pd.read_csv(NOME_ARQUIVO)
    return pd.DataFrame(columns=[
        "Data Aula", "Horário Registro", "Aluno", "Postura", 
        "Técnica", "Ritmo", "Teoria", "Resumo Secretaria", 
        "Metas", "Dicas Banca", "Status"
    ])

def salvar_dados(df):
    df.to_csv(NOME_ARQUIVO, index=False)

# --- INTERFACE ---
st.title("🎹 Sistema de Análise Pedagógica")

# Simulação de Data para seu teste (Remover após validar)
hoje = st.sidebar.date_input("Simular Data de Hoje", value=datetime.now().date())

# Verificação de Bloqueio
esta_bloqueado = hoje >= DATA_BLOQUEIO

if esta_bloqueado:
    st.error(f"🚫 ACESSO RESTRITO: O sistema entrou em modo de bloqueio em {DATA_BLOQUEIO.strftime('%d/%m/%Y')}")
    st.info("Novos lançamentos estão desabilitados. Consulte a secretaria.")
else:
    st.success(f"✅ Sistema Liberado - Data: {hoje.strftime('%d/%m/%Y')}")

# Carregar dados existentes
df_pedagogico = carregar_dados()

# --- FORMULÁRIO DE LANÇAMENTO ---
with st.expander("📝 Realizar Novo Lançamento Detalhado", expanded=not esta_bloqueado):
    if esta_bloqueado:
        st.warning("O formulário de envio está desativado devido ao bloqueio de data.")
    
    with st.form("form_analise", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            aluno = st.text_input("Nome Completo do Aluno")
            data_aula = st.date_input("Data da Aula", value=hoje)
        
        st.markdown("### 🔍 Avaliação Técnica")
        c1, c2, c3, c4 = st.columns(4)
        postura = c1.text_area("Postura (Mãos, Pés, Coluna)")
        tecnica = c2.text_area("Técnica (Dedilhado, Articulação)")
        ritmo = c3.text_area("Ritmo (Metrônomo, Divisão)")
        teoria = c4.text_area("Teoria (Solfejo, Conteúdo)")

        st.markdown("### 📋 Administrativo e Metas")
        resumo_sec = st.text_area("Resumo para Secretaria (Faltas, Livros, Progresso)")
        metas = st.text_area("Metas e Lições para a Próxima Aula")
        dicas_banca = st.text_area("Dicas Específicas para a Banca Semestral")

        btn_salvar = st.form_submit_button("CONGELAR ANÁLISE", disabled=esta_bloqueado)

        if btn_salvar:
            if not aluno:
                st.warning("Por favor, preencha o nome do aluno.")
            else:
                agora = datetime.now().strftime("%H:%M:%S")
                novo_registro = {
                    "Data Aula": data_aula,
                    "Horário Registro": agora,
                    "Aluno": aluno,
                    "Postura": postura,
                    "Técnica": tecnica,
                    "Ritmo": ritmo,
                    "Teoria": teoria,
                    "Resumo Secretaria": resumo_sec,
                    "Metas": metas,
                    "Dicas Banca": dicas_banca,
                    "Status": "Lançado com Sucesso"
                }
                
                df_pedagogico = pd.concat([df_pedagogico, pd.DataFrame([novo_registro])], ignore_index=True)
                salvar_dados(df_pedagogico)
                st.balloons()
                st.success(f"Análise salva às {agora} e gravada no banco de dados!")

# --- RELATÓRIO DE CONSULTA ---
st.divider()
st.header("📊 Histórico e Relatórios")

if not df_pedagogico.empty:
    # Barra de busca rápida
    busca = st.text_input("Filtrar por nome do aluno ou data...")
    df_filtrado = df_pedagogico.copy()
    
    if busca:
        mask = df_filtrado.apply(lambda x: x.astype(str).str.contains(busca, case=False)).any(axis=1)
        df_filtrado = df_filtrado[mask]

    # Exibição da Tabela
    st.dataframe(
        df_filtrado,
        column_order=(
            "Data Aula", "Horário Registro", "Status", "Aluno", 
            "Postura", "Técnica", "Ritmo", "Teoria", "Metas", "Dicas Banca"
        ),
        use_container_width=True,
        hide_index=True
    )
    
    # Exportação
    csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Relatório para Excel/CSV",
        data=csv_data,
        file_name=f"relatorio_pedagogico_{hoje}.csv",
        mime="text/csv"
    )
else:
    st.info("Nenhum dado registrado até o momento.")
