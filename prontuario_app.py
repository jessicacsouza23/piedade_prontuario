import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Sistema de Cadastro - Piedade", layout="centered")

# Conexão com o Banco de Dados (Configurar no Secrets do Streamlit)
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error("Erro de conexão com o banco de dados. Verifique os Secrets.")
    st.stop()

# --- LÓGICA DE BLOQUEIO POR DATA ---
def verificar_acesso():
    hoje = datetime.now()
    # Encontrar o primeiro sábado do mês atual
    primeiro_dia = hoje.replace(day=1)
    dias_para_sabado = (5 - primeiro_dia.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia + timedelta(days=dias_para_sabado)
    
    # Terça-feira que antecede o primeiro sábado
    limite_terca = primeiro_sabado - timedelta(days=4)
    
    if hoje > limite_terca:
        return False, limite_terca
    return True, limite_terca

acesso_liberado, data_limite = verificar_acesso()

# --- INTERFACE ---
st.title("⛪ Cadastro de Prontuários e Cestas")

if not acesso_liberado:
    st.error(f"Sistema bloqueado. O prazo era até terça-feira ({data_limite.strftime('%d/%m/%Y')}) que antecede o primeiro sábado do mês.")
else:
    # Escolha do Solicitante
    st.subheader("Informações do Solicitante")
    col1, col2 = st.columns(2)
    with col1:
        tipo = st.radio("Cargo do Solicitante:", ["Diácono", "Irmã da Piedade"])
    with col2:
        nome_solicitante = st.text_input(f"Nome do(a) {tipo}:")
        comum = st.text_input("Comum Congregação:")

    st.divider()

    # Dados do Prontuário
    st.subheader("Dados do Assistido")
    nome_completo = st.text_input("Nome Completo:")
    
    c1, c2, c3 = st.columns(3)
    idade = c1.number_input("Idade:", min_value=0, step=1)
    tempo_batismo = c2.text_input("Tempo de Batismo:")
    estado_civil = c3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"])

    nome_conjuge, idade_conjuge, tempo_batismo_conjuge = None, None, None
    if estado_civil == "Casado(a)":
        with st.expander("Informações do Cônjuge", expanded=True):
            nome_conjuge = st.text_input("Nome do Cônjuge:")
            cc1, cc2 = st.columns(2)
            idade_conjuge = cc1.number_input("Idade Cônjuge:", min_value=0)
            tempo_batismo_conjuge = cc2.text_input("Tempo Batismo Cônjuge:")

    st.subheader("Endereço e Entrega")
    endereco = st.text_input("Endereço Completo:")
    b1, b2, b3 = st.columns([2, 1, 1])
    bairro = b1.text_input("Bairro:")
    cep = b2.text_input("CEP:")
    qtd_cestas = b3.number_input("Qtd Cestas:", min_value=1, step=1)

    # Botões
    col_btn1, col_btn2 = st.columns(2)
    
    if col_btn1.button("💾 Salvar Informações", use_container_width=True):
        if nome_completo and nome_solicitante:
            dados = {
                "tipo_solicitante": tipo,
                "nome_solicitante": nome_solicitante,
                "comum_prontuario": comum,
                "nome_completo": nome_completo,
                "idade": idade,
                "tempo_batismo": tempo_batismo,
                "estado_civil": estado_civil,
                "nome_conjuge": nome_conjuge,
                "idade_conjuge": idade_conjuge,
                "tempo_batismo_conjuge": tempo_batismo_conjuge,
                "endereco": endereco,
                "bairro": bairro,
                "cep": cep,
                "quantidade_cestas": qtd_cestas
            }
            try:
                conn.table("registros_piedade").insert(dados).execute()
                st.success("Prontuário salvo com sucesso no banco de dados!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
        else:
            st.warning("Por favor, preencha os campos obrigatórios (Nome e Solicitante).")

    if col_btn2.button("🆕 Novo Prontuário", use_container_width=True):
        st.rerun()
