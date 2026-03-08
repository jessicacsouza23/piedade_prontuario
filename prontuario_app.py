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
    st.session_state.cargo = ""
if 'exibir_cadastro_completo' not in st.session_state:
    st.session_state.exibir_cadastro_completo = False

# --- TELA DE LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Acesso ao Sistema Piedade")
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.subheader("Login")
        cargo_selecionado = st.selectbox("Entrar como:", ["Diácono", "Irmã da Piedade"])
        senha = st.text_input("Senha:", type="password")
        
        if st.button("Entrar", use_container_width=True):
            senha_diacono = st.secrets.get("SENHA_DIACONO", "diacono123")
            senha_irmas = st.secrets.get("SENHA_IRMAS", "piedade123")
            
            if cargo_selecionado == "Diácono" and senha == senha_diacono:
                st.session_state.autenticado = True
                st.session_state.cargo = "Diácono"
                st.rerun()
            elif cargo_selecionado == "Irmã da Piedade" and senha == senha_irmas:
                st.session_state.autenticado = True
                st.session_state.cargo = "Irmã da Piedade"
                st.rerun()
            else:
                st.error("Senha incorreta para o cargo selecionado.")
else:
    # Barra lateral comum
    st.sidebar.title(f"Acesso: {st.session_state.cargo}")
    if st.sidebar.button("Sair / Trocar Login"):
        st.session_state.autenticado = False
        st.session_state.cargo = ""
        st.session_state.exibir_cadastro_completo = False
        st.rerun()

    # --- VISÃO DO DIÁCONO: RELATÓRIO DE DADOS SALVOS ---
    if st.session_state.cargo == "Diácono":
        st.title("📋 Registros de Prontuários Salvos")
        st.info("Abaixo estão todos os cadastros realizados, com a data registrada pelo sistema.")
        
        try:
            # Busca todos os dados da tabela
            resposta = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            df = pd.DataFrame(resposta.data)
            
            if not df.empty:
                # Renomeando colunas para ficar legível
                colunas_display = {
                    "data_sistema": "Data do Cadastro",
                    "num_prontuario": "Prontuário",
                    "nome_completo": "Nome do Assistido",
                    "quantidade_cestas": "Qtd Cestas",
                    "local_retirada": "Local",
                    "nome_solicitante": "Solicitante",
                    "tipo_solicitante": "Cargo"
                }
                st.dataframe(df[list(colunas_display.keys())].rename(columns=colunas_display), use_container_width=True)
                
                # Botão para baixar em Excel/CSV
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Planilha Completa (CSV)", csv, "registros_piedade.csv", "text/csv")
            else:
                st.warning("Nenhum registro encontrado no banco de dados.")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

    # --- VISÃO DA IRMÃ DA PIEDADE: TELA DE CADASTRO ---
    else:
        acesso_liberado, data_liberado = verificar_bloqueio()
        st.title("📝 Cadastro de Prontuários")

        if not acesso_liberado:
            st.error(f"⚠️ Sistema Bloqueado para novos registros.")
            st.info(f"O período de lançamentos encerrou. Liberação após: {data_liberado.strftime('%d/%m/%Y')}")
        else:
            # --- CAMPOS INICIAIS ---
            with st.container(border=True):
                st.subheader("Informações de Entrega")
                tipo_solicitante = st.radio("Solicitante:", ["Diácono", "Irmã da Piedade"], horizontal=True, index=1)
                nome_solicitante = st.text_input(f"Nome do(a) {tipo_solicitante}:")
                
                c1, c2 = st.columns(2)
                num_prontuario = c1.text_input("Número do Prontuário:")
                qtd_cestas = c2.number_input("Quantidade de Cestas:", min_value=1, step=1)
                
                local_retirada = st.radio("Aonde retirar:", ["Pq. Guarani", "Itaquera"], horizontal=True)

            # --- DADOS DO ASSISTIDO (OPCIONAL/NOVO) ---
            if not st.session_state.exibir_cadastro_completo:
                if st.button("🆕 É um Prontuário Novo? Clique aqui"):
                    st.session_state.exibir_cadastro_completo = True
                    st.rerun()

            nome_completo, idade, tempo_batismo, estado_civil = "", 0, "", ""
            nome_conjuge, idade_conjuge, tempo_batismo_conjuge = None, None, None
            endereco, bairro, cep = "", "", ""

            if st.session_state.exibir_cadastro_completo:
                st.divider()
                st.subheader("📋 Cadastro Completo (Novo Assistido)")
                nome_completo = st.text_input("Nome Completo do Assistido:")
                
                d1, d2, d3 = st.columns(3)
                idade = d1.number_input("Idade:", min_value=0, step=1)
                tempo_batismo = d2.text_input("Tempo de Batismo:")
                estado_civil = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"])

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

            # --- BOTÃO SALVAR ---
            st.divider()
            if st.button("💾 Salvar Registro", type="primary", use_container_width=True):
                if not nome_solicitante or not num_prontuario:
                    st.warning("Preencha o Solicitante e o Número do Prontuário.")
                else:
                    # Captura a data exata do sistema no momento do clique
                    data_hoje = datetime.now().strftime('%Y-%m-%d')
                    
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
                        "data_sistema": data_hoje # Data do sistema do computador
                    }
                    try:
                        supabase.table("registros_piedade").insert(dados).execute()
                        st.success(f"✅ Registro salvo com sucesso em {data_hoje}!")
                        st.session_state.exibir_cadastro_completo = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
