import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd
import time

st.set_page_config(page_title="Sistema Piedade", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILIZAÇÃO CSS PARA MODERNIZAÇÃO (CORRIGIDO) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .assistido-card { background-color: #e3f2fd; padding: 15px; border-radius: 8px; border-left: 5px solid #1976d2; margin-bottom: 10px; }
    .badge-local { background-color: #ff9800; color: white; padding: 2px 8px; border-radius: 5px; font-weight: bold; }
    .badge-cargo { background-color: #4caf50; color: white; padding: 2px 8px; border-radius: 5px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

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

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Acesso ao Sistema Piedade")
    with st.container(border=True):
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

    # --- VISÃO DO DIÁCONO ---
    if st.session_state.cargo == "Diácono":
        st.title("📋 Painel de Conferência")
        
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            if dados:
                df = pd.DataFrame(dados)
                st.download_button("📥 Exportar para Excel", df.to_csv(index=False).encode('utf-8-sig'), "relatorio.csv", "text/csv")
                
                for item in dados:
                    with st.container(border=True):
                        h_col, a_col = st.columns([4, 1])
                        with h_col:
                            nome_exibir = item.get('nome_completo') if item.get('nome_completo') else "Prontuário Existente"
                            st.markdown(f"## {nome_exibir}")
                            st.markdown(f"**Nº Prontuário:** `{item.get('num_prontuario') or 'NOVO'}` | **Data:** {item.get('data_sistema')}")
                        
                        with a_col:
                            status_db = item.get('tratado', False)
                            novo_st = st.radio(f"Status (Ref:{item['id'][:4]})", ["Pendente", "Tratado"], 
                                             index=1 if status_db else 0, key=f"r_{item['id']}")
                            if (novo_st == "Tratado") != status_db:
                                supabase.table("registros_piedade").update({"tratado": novo_st == "Tratado"}).eq("id", item['id']).execute()
                                st.toast("Atualizado!")

                        st.divider()
                        q1, q2, q3 = st.columns(3)
                        with q1:
                            st.markdown(f"**Solicitante:** <br><span class='badge-cargo'>{item.get('tipo_solicitante')}</span> {item.get('nome_solicitante')}", unsafe_allow_html=True)
                        with q2:
                            st.markdown(f"**Quantidade:** <br>📦 {item.get('quantidade_cestas')} Cesta(s)", unsafe_allow_html=True)
                        with q3:
                            st.markdown(f"**Retirada em:** <br><span class='badge-local'>{item.get('local_retirada')}</span>", unsafe_allow_html=True)

                        if item.get('nome_completo'):
                            with st.expander("🔍 Detalhes do Cadastro", expanded=True):
                                st.markdown(f"""
                                <div class='assistido-card'>
                                    <b>Idade:</b> {item.get('idade')} anos | <b>Estado Civil:</b> {item.get('estado_civil')}<br>
                                    <b>Endereço:</b> {item.get('endereco')}, {item.get('bairro')} - CEP: {item.get('cep')}
                                </div>
                                """, unsafe_allow_html=True)
                                if item.get('nome_conjuge'):
                                    st.markdown(f"💍 **Cônjuge:** {item.get('nome_conjuge')} ({item.get('idade_conjuge')} anos)")
            else: st.info("Sem registros.")
        except Exception as e: st.error(f"Erro ao carregar: {e}")

    # --- VISÃO DA IRMÃ ---
    else:
        liberado, data_lib = verificar_bloqueio()
        st.title("📝 Cadastro de Solicitações")
        
        if not liberado:
            st.error(f"⚠️ Bloqueio. Liberação: {data_lib.strftime('%d/%m/%Y')}")
        else:
            with st.container(border=True):
                tipo_sol = st.radio("Quem solicita?", ["Diácono", "Irmã da Piedade"], horizontal=True)
                nome_sol = st.text_input(f"Nome do(a) {tipo_sol}:", key="nome_sol")
                
                cp1, cp2 = st.columns([2, 1])
                n_prontuario = cp1.text_input("Número do Prontuário:", key="n_pront")
                q_cestas = cp2.number_input("Cestas:", min_value=1, step=1, key="q_cestas")
                
                loc_retirada = st.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True, key="local")
                st.divider()
                is_novo = st.toggle("🆕 CADASTRAR COMO PRONTUÁRIO NOVO", key="is_novo")

                # Variáveis novo cadastro
                n_comp, n_id, n_bat, n_civ, n_conj, n_conj_id, n_conj_bat = "", 0, "", "Solteiro(a)", "", 0, ""
                n_end, n_bai, n_cep = "", "", ""

                if is_novo:
                    n_comp = st.text_input("Nome Completo:", key="n_comp")
                    d1, d2, d3 = st.columns(3)
                    n_id = d1.number_input("Idade:", min_value=0, key="n_id")
                    n_bat = d2.text_input("Tempo de Batismo:", key="n_bat")
                    n_civ = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"], key="n_civ")
                    
                    if n_civ == "Casado(a)":
                        n_conj = st.text_input("Nome do Cônjuge:", key="n_conj")
                        cc1, cc2 = st.columns(2)
                        n_conj_id = cc1.number_input("Idade Cônjuge:", min_value=0, key="n_conj_id")
                        n_conj_bat = cc2.text_input("Batismo Cônjuge:", key="n_conj_bat")
                    
                    n_end = st.text_input("Rua e Número:", key="n_end")
                    b1, b2 = st.columns(2)
                    n_bai = b1.text_input("Bairro:", key="n_bai")
                    n_cep = b2.text_input("CEP:", key="n_cep")

                if st.button("💾 FINALIZAR E ENVIAR", type="primary", use_container_width=True):
                    if not nome_sol: st.error("Nome obrigatório!"); st.stop()
                    if not is_novo and not n_prontuario: st.error("Nº Prontuário obrigatório!"); st.stop()

                    data_comp = datetime.now().strftime('%d/%m/%Y %H:%M')
                    payload = {
                        "tipo_solicitante": tipo_sol, "nome_solicitante": nome_sol, "num_prontuario": n_prontuario,
                        "quantidade_cestas": int(q_cestas), "local_retirada": loc_retirada, "nome_completo": n_comp,
                        "idade": int(n_id), "tempo_batismo": n_bat, "estado_civil": n_civ, "nome_conjuge": n_conj,
                        "idade_conjuge": int(n_conj_id), "tempo_batismo_conjuge": n_conj_bat, "endereco": n_end,
                        "bairro": n_bai, "cep": n_cep, "data_sistema": data_comp, "tratado": False
                    }
                    
                    try:
                        supabase.table("registros_piedade").insert(payload).execute()
                        st.balloons()
                        st.success("Dados salvos")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
