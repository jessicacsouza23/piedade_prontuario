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

# --- CONTROLE DE ESTADO (SESSION STATE) ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.cargo = ""
if 'exibir_cadastro_completo' not in st.session_state:
    st.session_state.exibir_cadastro_completo = False

# --- TELA DE LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Acesso ao Sistema Piedade")
    cargo_selecionado = st.selectbox("Entrar como:", ["Diácono", "Irmã da Piedade"])
    senha = st.text_input("Senha:", type="password")
    
    if st.button("Entrar", use_container_width=True):
        senha_diacono = st.secrets.get("SENHA_DIACONO", "diacono123")
        senha_irmas = st.secrets.get("SENHA_IRMAS", "piedade123")
        
        if (cargo_selecionado == "Diácono" and senha == senha_diacono) or \
           (cargo_selecionado == "Irmã da Piedade" and senha == senha_irmas):
            st.session_state.autenticado = True
            st.session_state.cargo = cargo_selecionado
            st.rerun()
        else:
            st.error("Senha incorreta.")
else:
    # Barra lateral
    st.sidebar.title(f"Usuário: {st.session_state.cargo}")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.exibir_cadastro_completo = False
        st.rerun()

    # --- VISÃO DIÁCONO (RELATÓRIO) ---
    if st.session_state.cargo == "Diácono":
        st.title("📋 Consulta de Prontuários")
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                st.dataframe(df[["data_sistema", "num_prontuario", "nome_completo", "quantidade_cestas", "local_retirada", "nome_solicitante"]], use_container_width=True)
            else:
                st.info("Nenhum registro no banco.")
        except:
            st.error("Erro ao carregar dados.")

    # --- VISÃO IRMÃ DA PIEDADE (CADASTRO) ---
    else:
        liberado, data_lib = verificar_bloqueio()
        st.title("📝 Registro de Entregas")

        if not liberado:
            st.error(f"⚠️ Bloqueio de data. Liberação: {data_lib.strftime('%d/%m/%Y')}")
        else:
            # CAMPOS SEMPRE VISÍVEIS
            with st.container(border=True):
                st.subheader("Dados de Identificação")
                tipo_solicitante = st.radio("Solicitante:", ["Diácono", "Irmã da Piedade"], horizontal=True)
                nome_solicitante = st.text_input(f"Nome do(a) {tipo_solicitante}:")
                c1, c2 = st.columns(2)
                num_prontuario = c1.text_input("Nº Prontuário:")
                qtd_cestas = c2.number_input("Cestas:", min_value=1, step=1)
                local = st.radio("Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True)

            # LÓGICA DO BOTÃO "NOVO PRONTUÁRIO"
            if not st.session_state.exibir_cadastro_completo:
                if st.button("🆕 É um Prontuário Novo? Clique aqui"):
                    st.session_state.exibir_cadastro_completo = True
                    st.rerun()

            # CAMPOS QUE SÓ APARECEM SE CLICAR NO BOTÃO
            nome_completo, idade, batismo, civil, conjuge = "", 0, "", "Solteiro(a)", ""
            endereco, bairro, cep = "", "", ""

            if st.session_state.exibir_cadastro_completo:
                st.divider()
                st.subheader("📋 Dados do Novo Assistido")
                nome_completo = st.text_input("Nome Completo:")
                d1, d2, d3 = st.columns(3)
                idade = d1.number_input("Idade:", min_value=0)
                batismo = d2.text_input("Batismo:")
                civil = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"])
                
                if civil == "Casado(a)":
                    conjuge = st.text_input("Nome do Cônjuge:")
                
                st.subheader("Endereço")
                endereco = st.text_input("Rua/Nº:")
                b1, b2 = st.columns(2)
                bairro = b1.text_input("Bairro:")
                cep = b2.text_input("CEP:")
                
                if st.button("❌ Cancelar"):
                    st.session_state.exibir_cadastro_completo = False
                    st.rerun()

            # BOTÃO SALVAR (Sempre visível no final)
            st.divider()
            if st.button("💾 Finalizar e Salvar no Banco", type="primary", use_container_width=True):
                if not nome_solicitante or not num_prontuario:
                    st.warning("Preencha o Solicitante e o Prontuário!")
                else:
                    data_comp = datetime.now().strftime('%Y-%m-%d')
                    dados = {
                        "tipo_solicitante": tipo_solicitante,
                        "nome_solicitante": nome_solicitante,
                        "num_prontuario": num_prontuario,
                        "quantidade_cestas": int(qtd_cestas),
                        "local_retirada": local,
                        "nome_completo": nome_completo,
                        "idade": int(idade),
                        "tempo_batismo": batismo,
                        "estado_civil": civil,
                        "nome_conjuge": conjuge,
                        "endereco": endereco,
                        "bairro": bairro,
                        "cep": cep,
                        "data_sistema": data_comp
                    }
                    supabase.table("registros_piedade").insert(dados).execute()
                    st.success(f"Salvo com sucesso em {data_comp}!")
                    st.session_state.exibir_cadastro_completo = False # Volta ao normal
                    st.rerun()
