import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta

st.set_page_config(page_title="Sistema Piedade - Registro", layout="centered")

# --- FUNÇÃO DE CONEXÃO MANUAL (MAIS ESTÁVEL) ---
def inicializar_conexao():
    # Tenta buscar nos Secrets do Streamlit
    url = st.secrets.get("SUPABASE_URL") or st.secrets.get("connections", {}).get("supabase", {}).get("url")
    key = st.secrets.get("SUPABASE_KEY") or st.secrets.get("connections", {}).get("supabase", {}).get("key")
    
    if not url or not key:
        st.error("❌ Credenciais não encontradas nos Secrets!")
        st.info("Certifique-se de que os Secrets no Streamlit Cloud contenham 'url' e 'key'.")
        st.stop()
        
    return create_client(url, key)

try:
    supabase: Client = inicializar_conexao()
except Exception as e:
    st.error(f"Erro ao conectar ao Supabase: {e}")
    st.stop()

# --- LÓGICA DE BLOQUEIO POR DATA ---
def verificar_acesso():
    hoje = datetime.now()
    # Primeiro dia do mês atual
    primeiro_dia = hoje.replace(day=1)
    # Encontra o primeiro sábado (weekday 5)
    dias_para_sabado = (5 - primeiro_dia.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia + timedelta(days=dias_para_sabado)
    # Terça anterior ao primeiro sábado
    limite_terca = primeiro_sabado - timedelta(days=4)
    
    # Se hoje for depois da terça-feira limite, bloqueia
    if hoje.date() > limite_terca.date():
        return False, limite_terca
    return True, limite_terca

acesso_liberado, data_limite = verificar_acesso()

# --- INTERFACE ---
st.title("⛪ Cadastro de Prontuários")

if not acesso_liberado:
    st.error(f"⚠️ Sistema Bloqueado. O prazo encerrou na terça-feira ({data_limite.strftime('%d/%m/%Y')}).")
else:
    # Cabeçalho do Solicitante
    with st.container(border=True):
        st.subheader("Solicitante")
        tipo = st.radio("Selecione seu cargo:", ["Diácono", "Irmã da Piedade"], horizontal=True)
        nome_solicitante = st.text_input(f"Nome do(a) {tipo}:")
        comum = st.text_input("Comum Congregação (Prontuário):")

    # Dados do Assistido
    st.subheader("Dados do Prontuário")
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

    # Botões de Ação
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
                "quantidade_cestas": qtd_cestas
            }
            res = supabase.table("registros_piedade").insert(dados).execute()
            st.success("✅ Informações salvas com sucesso!")

    if c_btn2.button("🆕 Novo Prontuário", use_container_width=True):
        st.rerun()
