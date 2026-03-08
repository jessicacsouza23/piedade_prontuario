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
    
    if limite_terca < hoje <= primeiro_sabado:
        return False, primeiro_sabado
    return True, None

# --- CONTROLE DE ESTADO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'exibir_cadastro_completo' not in st.session_state:
    st.session_state.exibir_cadastro_completo = False

# --- TELA DE LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Acesso ao Sistema")
    senha = st.text_input("Senha de Acesso:", type="password")
    if st.button("Entrar", use_container_width=True):
        if senha == st.secrets.get("SENHA_GERAL", "piedade123"):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
else:
    acesso_liberado, data_liberado = verificar_bloqueio()

    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.exibir_cadastro_completo = False
        st.rerun()

    st.title("📝 Registro de Prontuários")

    if not acesso_liberado:
        st.error(f"⚠️ Sistema Bloqueado.")
        st.info(f"O período de lançamentos encerrou. Liberação após: {data_liberado.strftime('%d/%m/%Y')}")
    else:
        # --- CAMPOS INICIAIS (SEMPRE VISÍVEIS) ---
        with st.container(border=True):
            st.subheader("Informações de Entrega")
            tipo_solicitante = st.radio("Solicitante:", ["Diácono", "Irmã da Piedade"], horizontal=True)
            nome_solicitante = st.text_input(f"Nome do(a) {tipo_solicitante}:")
            
            c1, c2 = st.columns(2)
            num_prontuario = c1.text_input("Número do Prontuário:")
            qtd_cestas = c2.number_input("Quantidade de Cestas:", min_value=1, step=1)
            
            local_retirada = st.radio("Aonde retirar:", ["Pq. Guarani", "Itaquera"], horizontal=True)

        # --- BOTÃO PARA REVELAR CADASTRO NOVO ---
        if not st.session_state.exibir_cadastro_completo:
            if st.button("🆕 É um Prontuário Novo? Clique aqui para cadastrar dados completos"):
                st.session_state.exibir_cadastro_completo = True
                st.rerun()

        # --- DADOS DO ASSISTIDO (SÓ APARECE SE FOR NOVO) ---
        if st.session_state.exibir_cadastro_completo:
            st.divider()
            st.subheader("📋 Cadastro de Prontuário Novo")
            nome_completo = st.text_input("Nome Completo do Assistido:")
            
            d1, d2, d3 = st.columns(3)
            idade = d1.number_input("Idade:", min_value=0, step=1)
            tempo_batismo = d2.text_input("Tempo de Batismo:")
            estado_civil = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"])

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
            
            if st.button("❌ Cancelar Cadastro Novo"):
                st.session_state.exibir_cadastro_completo = False
                st.rerun()
        else:
            # Se não for novo, os campos de texto longo ficam vazios para o banco
            nome_completo, idade, tempo_batismo, estado_civil = "", 0, "", ""
            nome_conjuge, idade_conjuge, tempo_batismo_conjuge = None, None, None
            endereco, bairro, cep = "", "", ""

        # --- BOTÃO SALVAR ---
        st.divider()
        if st.button("💾 Salvar Todas as Informações", type="primary", use_container_width=True):
            if not nome_solicitante or not num_prontuario:
                st.warning("Por favor, preencha pelo menos o Solicitante e o Número do Prontuário.")
            else:
                dados = {
                    "tipo_solicitante": tipo_solicitante,
                    "nome_solicitante": nome_solicitante,
                    "num_prontuario": num_prontuario,
                    "quantidade_cestas": int(qtd_cestas),
                    "local_retirada": local_retirada,
                    "nome_completo": nome_completo,
                    "idade": int(idade),
                    "tempo_batismo": tempo_batismo,
                    "estado_civil": estado_civil,
                    "nome_conjuge": nome_conjuge,
                    "idade_conjuge": int(idade_conjuge) if idade_conjuge else None,
                    "tempo_batismo_conjuge": tempo_batismo_conjuge,
                    "endereco": endereco,
                    "bairro": bairro,
                    "cep": cep,
                    "data_sistema": datetime.now().strftime('%Y-%m-%d')
                }
                try:
                    supabase.table("registros_piedade").insert(dados).execute()
                    st.success("✅ Registro salvo com sucesso!")
                    # Reseta o estado para a próxima entrada
                    st.session_state.exibir_cadastro_completo = False
                    # Pequeno delay antes de recarregar
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
