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
        st.error("❌ Credenciais não encontradas!")
        st.stop()
    return create_client(url, key)

try:
    supabase: Client = inicializar_conexao()
except Exception as e:
    st.error(f"Erro: {e}")
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

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Acesso ao Sistema Piedade")
    cargo_sel = st.selectbox("Entrar como:", ["Diácono", "Irmã da Piedade"])
    senha = st.text_input("Senha:", type="password")
    if st.button("Entrar", use_container_width=True):
        if (cargo_sel == "Diácono" and senha == st.secrets.get("SENHA_DIACONO", "diacono123")) or \
           (cargo_sel == "Irmã da Piedade" and senha == st.secrets.get("SENHA_IRMAS", "piedade123")):
            st.session_state.autenticado, st.session_state.cargo = True, cargo_sel
            st.rerun()
        else: st.error("Senha incorreta.")
else:
    st.sidebar.title(f"Usuário: {st.session_state.cargo}")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    # --- VISÃO DO DIÁCONO (FICHAS) ---
    if st.session_state.cargo == "Diácono":
        st.title("📋 Fichas de Prontuários")
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            if dados:
                df = pd.DataFrame(dados)
                st.download_button("📥 Gerar Excel", df.to_csv(index=False).encode('utf-8-sig'), "relatorio.csv", "text/csv")
                for item in dados:
                    with st.container(border=True):
                        c_id, c_st = st.columns([3, 1])
                        c_id.subheader(f"📄 Prontuário: {item.get('num_prontuario') or 'NOVO'}")
                        c_id.caption(f"📅 Data: {item.get('data_sistema')}")
                        novo_st = c_st.radio(f"Tratado? (ID:{item['id'][:4]})", ["Não", "Sim"], index=1 if item.get('tratado') else 0, key=f"r_{item['id']}")
                        if (novo_st == "Sim") != item.get('tratado'):
                            supabase.table("registros_piedade").update({"tratado": novo_st == "Sim"}).eq("id", item['id']).execute()
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Solicitante", item.get('nome_solicitante'))
                        col2.metric("Cestas", item.get('quantidade_cestas'))
                        col3.metric("Local", item.get('local_retirada'))
                        if item.get('nome_completo'):
                            st.divider()
                            st.write(f"**Assistido:** {item.get('nome_completo')} | **Idade:** {item.get('idade')}")
                            st.write(f"**Endereço:** {item.get('endereco')}, {item.get('bairro')} - CEP: {item.get('cep')}")
            else: st.info("Sem registros.")
        except Exception as e: st.error(f"Erro: {e}")

    # --- VISÃO DA IRMÃ (CADASTRO) ---
    else:
        liberado, data_lib = verificar_bloqueio()
        st.title("📝 Cadastro de Pedidos")
        if not liberado:
            st.error(f"⚠️ Sistema Bloqueado. Liberação: {data_lib.strftime('%d/%m/%Y')}")
        else:
            # Para o formulário abrir dinamicamente, usamos a lógica fora do st.form para os inputs de controle
            with st.container(border=True):
                st.subheader("1. Identificação")
                tipo_sol = st.radio("Solicitante:", ["Diácono", "Irmã da Piedade"], horizontal=True)
                nome_sol = st.text_input("Nome do Solicitante (Obrigatório):")
                
                # Layout solicitado: Prontuário ao lado e ANTES da Quantidade
                col_p1, col_p2 = st.columns([2, 1])
                n_prontuario = col_p1.text_input("Número do Prontuário (Obrigatório se NÃO for Novo):")
                q_cestas = col_p2.number_input("Qtd. Cestas:", min_value=1, step=1)
                
                loc_retirada = st.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True)

                st.divider()
                is_novo = st.toggle("🆕 ESTE É UM CADASTRO NOVO?")

                # Variáveis padrão
                n_comp, n_id, n_bat, n_civ, n_conj, n_end, n_bai, n_cep = "", 0, "", "Solteiro(a)", "", "", "", ""

                if is_novo:
                    st.subheader("📋 Dados do Novo Assistido")
                    n_comp = st.text_input("Nome Completo (Obrigatório):")
                    d1, d2, d3 = st.columns(3)
                    n_id = d1.number_input("Idade:", min_value=0)
                    n_bat = d2.text_input("Tempo de Batismo (Opcional):")
                    n_civ = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"])
                    if n_civ == "Casado(a)":
                        n_conj = st.text_input("Nome do Cônjuge (Obrigatório):")
                    
                    st.markdown("#### Endereço")
                    n_end = st.text_input("Rua e Número (Obrigatório):")
                    b1, b2 = st.columns(2)
                    n_bai = b1.text_input("Bairro (Obrigatório):")
                    n_cep = b2.text_input("CEP (Obrigatório):")

                if st.button("💾 SALVAR REGISTRO", type="primary", use_container_width=True):
                    erro = False
                    if not nome_sol: st.error("Informe o Nome do Solicitante."); erro = True
                    if not is_novo and not n_prontuario: st.error("O Número do Prontuário é obrigatório para cadastros existentes."); erro = True
                    if is_novo:
                        if not n_comp or n_id == 0 or not n_end or not n_bai or not n_cep:
                            st.error("Preencha todos os campos obrigatórios do novo cadastro (Nome, Idade e Endereço)."); erro = True
                        if n_civ == "Casado(a)" and not n_conj:
                            st.error("Nome do cônjuge obrigatório."); erro = True

                    if not erro:
                        data_atual = datetime.now().strftime('%d/%m/%Y')
                        payload = {
                            "tipo_solicitante": tipo_sol, "nome_solicitante": nome_sol, "num_prontuario": n_prontuario,
                            "quantidade_cestas": int(q_cestas), "local_retirada": loc_retirada, "nome_completo": n_comp,
                            "idade": int(n_id), "tempo_batismo": n_bat, "estado_civil": n_civ, "nome_conjuge": n_conj,
                            "endereco": n_end, "bairro": n_bai, "cep": n_cep, "data_sistema": data_atual, "tratado": False
                        }
                        supabase.table("registros_piedade").insert(payload).execute()
                        st.success(f"✅ Salvo com sucesso! ({data_atual})")
                        st.rerun()
