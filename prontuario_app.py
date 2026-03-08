import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta

st.set_page_config(page_title="Sistema Piedade", layout="centered")

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

def tela_login():
    st.title("⛪ Acesso ao Sistema")
    with st.form("login_form"):
        st.subheader("Login Irmãs da Piedade / Diáconos")
        senha = st.text_input("Senha de Acesso:", type="password")
        # Senhas configuradas nos Secrets
        senha_acesso = st.secrets.get("SENHA_GERAL", "piedade123")
        
        botao_entrar = st.form_submit_button("Entrar", use_container_width=True)
        if botao_entrar:
            if senha == senha_acesso:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Senha incorreta.")

# --- FLUXO PRINCIPAL ---
if not st.session_state.autenticado:
    tela_login()
else:
    acesso_liberado, data_liberado = verificar_bloqueio()

    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    st.title("📝 Registro de Prontuários")

    if not acesso_liberado:
        st.error(f"⚠️ Sistema Bloqueado. Liberação após: {data_liberado.strftime('%d/%m/%Y')}")
    else:
        # --- CAMPOS SOLICITADOS ---
        with st.container(border=True):
            st.subheader("Informações Iniciais")
            
            # 1. Solicitante (Radio Button)
            tipo_solicitante = st.radio(
                "Solicitante:", 
                ["Diácono", "Irmã da Piedade"], 
                horizontal=True
            )
            
            # 2. Nome do Solicitante (Aparece após escolha)
            nome_solicitante = st.text_input(f"Nome do(a) {tipo_solicitante}:")
            
            col_dados1, col_dados2 = st.columns(2)
            # 3. Número do Prontuário
            num_prontuario = col_dados1.text_input("Número do Prontuário:")
            
            # 4. Quantidade de Cestas
            qtd_cestas = col_dados2.number_input("Quantidade de Cestas:", min_value=1, step=1)
            
            # 5. Aonde retirar (Radio Button)
            local_retirada = st.radio(
                "Local de Retirada:",
                ["Pq. Guarani", "Itaquera"],
                horizontal=True
            )

        st.divider()

        # --- DADOS COMPLEMENTARES (CADASTRO COMPLETO) ---
        st.subheader("Dados do Assistido")
        nome_completo = st.text_input("Nome Completo do Assistido:")
        
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

        st.subheader("Endereço")
        endereco = st.text_input("Endereço Completo:")
        b1, b2 = st.columns([2, 1])
        bairro = b1.text_input("Bairro:")
        cep = b2.text_input("CEP:")

        # --- BOTÕES ---
        st.write("")
        btn_salvar, btn_novo = st.columns(2)
        
        if btn_salvar.button("💾 Salvar Informações", type="primary", use_container_width=True):
            if not nome_completo or not nome_solicitante or not num_prontuario:
                st.warning("Preencha os campos obrigatórios: Nome, Solicitante e Prontuário.")
            else:
                dados = {
                    "tipo_solicitante": tipo_solicitante,
                    "nome_solicitante": nome_solicitante,
                    "num_prontuario": num_prontuario,
                    "quantidade_cestas": qtd_cestas,
                    "local_retirada": local_retirada,
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
                    "data_sistema": datetime.now().strftime('%Y-%m-%d')
                }
                try:
                    supabase.table("registros_piedade").insert(dados).execute()
                    st.success("✅ Registro salvo com sucesso no banco online!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

        if btn_novo.button("🆕 Novo Prontuário", use_container_width=True):
            st.rerun()
