import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Sistema Piedade", layout="wide")

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

# --- LÓGICA DE BLOQUEIO POR DATA ---
def verificar_bloqueio():
    hoje = datetime.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    dias_para_sabado = (5 - primeiro_dia_mes.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia_mes + timedelta(days=dias_para_sabado)
    limite_terca = primeiro_sabado - timedelta(days=4)
    
    if limite_terca < hoje <= primeiro_sabado:
        return False, primeiro_sabado
    return True, None

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'cargo' not in st.session_state:
    st.session_state.cargo = ""
if 'novo_prontuario' not in st.session_state:
    st.session_state.novo_prontuario = False

# --- TELA DE LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Acesso ao Sistema Piedade")
    cargo_sel = st.selectbox("Entrar como:", ["Diácono", "Irmã da Piedade"])
    senha = st.text_input("Senha:", type="password")
    
    if st.button("Entrar", use_container_width=True):
        s_diacono = st.secrets.get("SENHA_DIACONO", "diacono123")
        s_irmas = st.secrets.get("SENHA_IRMAS", "piedade123")
        
        if (cargo_sel == "Diácono" and senha == s_diacono) or (cargo_sel == "Irmã da Piedade" and senha == s_irmas):
            st.session_state.autenticado = True
            st.session_state.cargo = cargo_sel
            st.rerun()
        else:
            st.error("Senha incorreta.")
else:
    # Barra lateral
    st.sidebar.title(f"Usuário: {st.session_state.cargo}")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.novo_prontuario = False
        st.rerun()

    # --- VISÃO DIÁCONO (CONSULTA) ---
    if st.session_state.cargo == "Diácono":
        st.title("📋 Consulta de Prontuários")
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                st.dataframe(df[["data_sistema", "num_prontuario", "nome_completo", "quantidade_cestas", "local_retirada", "nome_solicitante"]], use_container_width=True)
            else:
                st.info("Nenhum registro encontrado.")
        except:
            st.error("Erro ao carregar dados.")

    # --- VISÃO IRMÃ DA PIEDADE (CADASTRO) ---
    else:
        liberado, data_lib = verificar_bloqueio()
        st.title("📝 Registro de Entregas")

        if not liberado:
            st.error(f"⚠️ Sistema Bloqueado. Liberação: {data_lib.strftime('%d/%m/%Y')}")
        else:
            # 1. CAMPOS DE IDENTIFICAÇÃO (SEMPRE APARECEM)
            with st.container(border=True):
                st.subheader("Informações Básicas")
                tipo_sol = st.radio("Solicitante:", ["Diácono", "Irmã da Piedade"], horizontal=True)
                nome_sol = st.text_input(f"Nome do(a) {tipo_sol}:")
                c1, c2 = st.columns(2)
                n_prontuario = c1.text_input("Nº Prontuário:")
                q_cestas = c2.number_input("Quantidade de Cestas:", min_value=1, step=1)
                loc_retirada = st.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True)

            st.divider()

            # 2. LÓGICA DO BOTÃO "NOVO PRONTUÁRIO"
            # Se st.session_state.novo_prontuario for False, mostra o botão para abrir.
            if not st.session_state.novo_prontuario:
                if st.button("🆕 É um Prontuário Novo? (Clique para abrir cadastro completo)"):
                    st.session_state.novo_prontuario = True
                    st.rerun()
            
            # 3. CAMPOS DO CADASTRO NOVO (SÓ APARECEM SE O BOTÃO ACIMA FOI CLICADO)
            # Definimos variáveis vazias por padrão para evitar erro no banco
            n_completo, n_idade, n_batismo, n_civil, n_conjuge = "", 0, "", "Solteiro(a)", ""
            n_endereco, n_bairro, n_cep = "", "", ""

            if st.session_state.novo_prontuario:
                with st.container(border=True):
                    st.subheader("📋 Cadastro Completo de Novo Assistido")
                    n_completo = st.text_input("Nome Completo do Assistido:")
                    d1, d2, d3 = st.columns(3)
                    n_idade = d1.number_input("Idade:", min_value=0)
                    n_batismo = d2.text_input("Tempo de Batismo:")
                    n_civil = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"])
                    
                    if n_civil == "Casado(a)":
                        n_conjuge = st.text_input("Nome do Cônjuge:")
                    
                    st.subheader("Endereço")
                    n_endereco = st.text_input("Rua e Número:")
                    b1, b2 = st.columns(2)
                    n_bairro = b1.text_input("Bairro:")
                    n_cep = b2.text_input("CEP:")
                    
                    if st.button("❌ Cancelar Cadastro Novo"):
                        st.session_state.novo_prontuario = False
                        st.rerun()

            # 4. BOTÃO SALVAR (Final da página)
            st.write("")
            if st.button("💾 FINALIZAR E SALVAR", type="primary", use_container_width=True):
                if not nome_sol or not n_prontuario:
                    st.warning("Preencha o Nome do Solicitante e o Número do Prontuário.")
                else:
                    data_pc = datetime.now().strftime('%Y-%m-%d') # Pega data do sistema
                    payload = {
                        "tipo_solicitante": tipo_sol,
                        "nome_solicitante": nome_sol,
                        "num_prontuario": n_prontuario,
                        "quantidade_cestas": int(q_cestas),
                        "local_retirada": loc_retirada,
                        "nome_completo": n_completo,
                        "idade": int(n_idade),
                        "tempo_batismo": n_batismo,
                        "estado_civil": n_civil,
                        "nome_conjuge": n_conjuge,
                        "endereco": n_endereco,
                        "bairro": n_bairro,
                        "cep": n_cep,
                        "data_sistema": data_pc
                    }
                    try:
                        supabase.table("registros_piedade").insert(payload).execute()
                        st.success(f"✅ Salvo com sucesso! Data: {data_pc}")
                        # Resetar a tela para o próximo
                        st.session_state.novo_prontuario = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                        
