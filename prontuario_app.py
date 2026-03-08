import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta

st.set_page_config(page_title="Sistema Piedade - Login", layout="centered")

# --- CONEXÃO COM O BANCO ---
def inicializar_conexao():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    if not url or not key:
        st.error("❌ Credenciais do Banco não encontradas nos Secrets!")
        st.stop()
    return create_client(url, key)

try:
    supabase: Client = inicializar_conexao()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- LÓGICA DE ACESSO (BLOQUEIO POR DATA) ---
def verificar_bloqueio():
    hoje = datetime.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    dias_para_sabado = (5 - primeiro_dia_mes.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia_mes + timedelta(days=dias_para_sabado)
    limite_terca = primeiro_sabado - timedelta(days=4)
    
    # Bloqueia se hoje estiver entre a quarta e o sábado
    if limite_terca < hoje <= primeiro_sabado:
        return False, primeiro_sabado
    return True, None

# --- GERENCIAMENTO DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.cargo = ""

def tela_login():
    st.title("⛪ Acesso ao Sistema")
    with st.form("login_form"):
        st.subheader("Identifique-se para continuar")
        cargo = st.selectbox("Entrar como:", ["Selecione...", "Diácono", "Irmã da Piedade"])
        senha = st.text_input("Senha de Acesso:", type="password")
        
        # Buscando senhas dos secrets (explicado abaixo)
        senha_diacono = st.secrets.get("SENHA_DIACONO", "123")
        senha_irmas = st.secrets.get("SENHA_IRMAS", "456")
        
        botao_entrar = st.form_submit_button("Entrar", use_container_width=True)
        
        if botao_entrar:
            if cargo == "Diácono" and senha == senha_diacono:
                st.session_state.autenticado = True
                st.session_state.cargo = "Diácono"
                st.rerun()
            elif cargo == "Irmã da Piedade" and senha == senha_irmas:
                st.session_state.autenticado = True
                st.session_state.cargo = "Irmã da Piedade"
                st.rerun()
            else:
                st.error("Cargo ou senha incorretos.")

# --- FLUXO PRINCIPAL ---
if not st.session_state.autenticado:
    tela_login()
else:
    acesso_liberado, data_liberado = verificar_bloqueio()

    # Barra lateral com botão de Sair
    st.sidebar.write(f"Conectado como: **{st.session_state.cargo}**")
    if st.sidebar.button("Sair / Trocar Usuário"):
        st.session_state.autenticado = False
        st.rerun()

    st.title(f"📝 Cadastro - {st.session_state.cargo}")

    if not acesso_liberado:
        st.error(f"⚠️ Sistema Bloqueado.")
        st.info(f"O período de lançamentos encerrou. O sistema será liberado após o primeiro sábado ({data_liberado.strftime('%d/%m/%Y')}).")
    else:
        # Formulário de Cadastro
        with st.container(border=True):
            st.subheader("Solicitante")
            # O nome do solicitante agora já sabe o cargo pelo login
            nome_solicitante = st.text_input(f"Nome do(a) {st.session_state.cargo}:")
            comum = st.text_input("Comum Congregação (Prontuário):")

        st.subheader("Dados do Assistido")
        nome_completo = st.text_input("Nome Completo:")
        
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

        c_btn1, c_btn2 = st.columns(2)
        
        if c_btn1.button("💾 Salvar Prontuário", type="primary", use_container_width=True):
            if not nome_completo or not nome_solicitante:
                st.warning("Preencha o Nome e o Solicitante.")
            else:
                dados = {
                    "tipo_solicitante": st.session_state.cargo,
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
