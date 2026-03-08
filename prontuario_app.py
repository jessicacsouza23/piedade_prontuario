import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta

st.set_page_config(page_title="Sistema Piedade - Registro", layout="centered")

# --- CONEXÃO COM O BANCO ---
def inicializar_conexao():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    
    if not url or not key:
        st.error("❌ Credenciais não encontradas nos Secrets!")
        st.stop()
    return create_client(url, key)

try:
    supabase: Client = inicializar_conexao()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- NOVA LÓGICA DE ACESSO ---
def verificar_bloqueio():
    hoje = datetime.now().date()
    
    # Encontrar o primeiro sábado do mês atual
    primeiro_dia_mes = hoje.replace(day=1)
    dias_para_sabado = (5 - primeiro_dia_mes.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia_mes + timedelta(days=dias_para_sabado)
    
    # Terça-feira que antecede o primeiro sábado (último dia permitido)
    limite_terca = primeiro_sabado - timedelta(days=4)
    
    # BLOQUEIO: Se hoje for DEPOIS da terça E ANTES ou IGUAL ao sábado
    if limite_terca < hoje <= primeiro_sabado:
        return False, primeiro_sabado
    return True, None

acesso_liberado, data_liberado = verificar_bloqueio()

st.title("⛪ Cadastro de Prontuários")

if not acesso_liberado:
    st.error(f"⚠️ Sistema Temporariamente Bloqueado.")
    st.info(f"O período de lançamentos encerrou na terça-feira. O sistema será liberado após o primeiro sábado ({data_liberado.strftime('%d/%m/%Y')}).")
else:
    # --- FORMULÁRIO DE CADASTRO ---
    with st.container(border=True):
        st.subheader("Solicitante")
        tipo = st.radio("Selecione seu cargo:", ["Diácono", "Irmã da Piedade"], horizontal=True)
        nome_solicitante = st.text_input(f"Nome do(a) {tipo}:")
        comum = st.text_input("Comum Congregação (Prontuário):")

    st.subheader("Dados do Assistido")
    nome_completo = st.text_input("Nome Completo do Assistido:")
    
    col1, col2, col3 = st.columns(3)
    idade = col1.number_input("Idade:", min_value=0, step=1)
    tempo_batismo = col2.text_input("Tempo de Batismo:")
    estado_civil = col3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"])

    nome_conjuge, idade_conjuge, tempo_batismo_conjuge = None, None, None
    if estado_civil == "Casado(a)":
        with st.expander("Dados do Cônjuge", expanded=True):
            nome_conjuge = st.text_input("Nome do Cônjuge:")
            c1, c2 = st.columns(2)
            idade_conjuge = c1.number_input("Idade Cônjuge:", min_value=0)
            tempo_batismo_conjuge = c2.text_input("Tempo Batismo Cônjuge:")

    st.subheader("Endereço e Cestas")
    endereco = st.text_input("Endereço Completo:")
    b1, b2, b3 = st.columns([2, 1, 1])
    bairro = b1.text_input("Bairro:")
    cep = b2.text_input("CEP:")
    qtd_cestas = b3.number_input("Quantidade de Cestas:", min_value=1, step=1)

    st.write("")
    c_btn1, c_btn2 = st.columns(2)
    
    if c_btn1.button("💾 Salvar Prontuário", type="primary", use_container_width=True):
        if not nome_completo or not nome_solicitante:
            st.warning("Preencha o Nome e o Solicitante.")
        else:
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
                "quantidade_cestas": qtd_cestas,
                "data_sistema": datetime.now().strftime('%Y-%m-%d')
            }
            try:
                supabase.table("registros_piedade").insert(dados).execute()
                st.success("✅ Informações salvas com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

    if c_btn2.button("🆕 Novo Prontuário", use_container_width=True):
        st.rerun()
