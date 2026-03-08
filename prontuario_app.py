import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd
import time

st.set_page_config(page_title="Sistema Piedade", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILIZAÇÃO CSS COMPACTA ---
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 40px; background-color: #eee; border-radius: 5px; padding: 0px 20px; }
    .stTabs [aria-selected="true"] { background-color: #007bff !important; color: white !important; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 5px; background-color: white; }
    .badge-info { background-color: #e1f5fe; color: #01579b; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
    .nome-header { font-size: 1.2rem; font-weight: bold; color: #333; margin-bottom: 0px; }
    /* Estilo para o topo */
    .header-container { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO ---
def inicializar_conexao():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    return create_client(url, key)

try:
    supabase: Client = inicializar_conexao()
except:
    st.error("Erro de conexão.")
    st.stop()

# --- ESTADO DA SESSÃO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'form_id' not in st.session_state: st.session_state.form_id = 0

def resetar_tela():
    st.session_state.form_id += 1
    for key in list(st.session_state.keys()):
        if key not in ['autenticado', 'cargo', 'form_id']: st.session_state.pop(key)

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Sistema Piedade")
    with st.container(border=True):
        cargo_sel = st.selectbox("Acesso:", ["Diácono", "Irmã da Piedade"])
        senha = st.text_input("Senha:", type="password")
        if st.button("Entrar", use_container_width=True):
            if (cargo_sel == "Diácono" and senha == st.secrets.get("SENHA_DIACONO", "diacono123")) or \
               (cargo_sel == "Irmã da Piedade" and senha == st.secrets.get("SENHA_IRMAS", "piedade123")):
                st.session_state.autenticado, st.session_state.cargo = True, cargo_sel
                st.rerun()
            else: st.error("Senha incorreta.")
else:
    # --- CABEÇALHO COM BOTÃO SAIR ---
    col_tit, col_sair = st.columns([5, 1])
    with col_tit:
        st.subheader(f"👤 {st.session_state.cargo}")
    with col_sair:
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()

    # --- VISÃO DO DIÁCONO ---
    if st.session_state.cargo == "Diácono":
        st.title("📋 Reserva de Cestas")
        tab_novos, tab_existentes, tab_tratados = st.tabs(["🆕 Novos", "📋 Prontuários", "✅ Tratados"])
        
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            
            def exibir_registro_compacto(item):
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1])
                    
                    with c1:
                        nome = item.get('nome_completo') or "Prontuário Existente"
                        st.markdown(f"<div class='nome-header'>{nome}</div>", unsafe_allow_html=True)
                        st.caption(f"📍 {item.get('local_retirada')} | 📅 {item.get('data_sistema')}")
                    
                    with c2:
                        st.markdown(f"**📦 {item.get('quantidade_cestas')} Cesta(s)**")
                        st.markdown(f"<span class='badge-info'>ID: {item.get('num_prontuario') or 'NOVO'}</span>", unsafe_allow_html=True)
                    
                    with c3:
                        st.markdown(f"**👤 Solicitante:**\n{item.get('nome_solicitante')}")
                    
                    with c4:
                        if st.button("Tratado", key=f"btn_{item['id']}", use_container_width=True):
                            supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute()
                            st.rerun()

                    if item.get('nome_completo'):
                        with st.expander("🔍 Detalhes do Cadastro"):
                            d1, d2 = st.columns(2)
                            d1.markdown(f"**Idade:** {item.get('idade')} | **Civil:** {item.get('estado_civil')} | **Batismo:** {item.get('tempo_batismo')}")
                            d1.markdown(f"**Endereço:** {item.get('endereco')}, {item.get('bairro')} | **CEP:** {item.get('cep')}")
                            if item.get('nome_conjuge'):
                                d2.markdown(f"**💍 Cônjuge:** {item.get('nome_conjuge')} ({item.get('idade_conjuge')} anos)")
                                d2.markdown(f"**Batismo Cônjuge:** {item.get('tempo_batismo_conjuge')}")

            with tab_novos:
                for i in [x for x in dados if x.get('nome_completo') and not x.get('tratado')]: exibir_registro_compacto(i)
            with tab_existentes:
                for i in [x for x in dados if not x.get('nome_completo') and not x.get('tratado')]: exibir_registro_compacto(i)
            with tab_tratados:
                if st.button("Limpar Histórico Definitivamente", type="secondary"):
                    supabase.table("registros_piedade").delete().eq("tratado", True).execute()
                    st.rerun()
                for i in [x for x in dados if x.get('tratado')]:
                    st.text(f"✅ {i.get('nome_completo') or i.get('num_prontuario')} - Entregue")

        except Exception as e: st.error(f"Erro: {e}")

    # --- VISÃO DA IRMÃ ---
    else:
        st.title("📝 Cadastro")
        f_id = st.session_state.form_id
        with st.container(border=True):
            tipo_sol = st.radio("Solicitante:", ["Diácono", "Irmã da Piedade"], horizontal=True, key=f"t_{f_id}")
            nome_sol = st.text_input("Nome:", key=f"n_{f_id}")
            
            c1, c2 = st.columns(2)
            n_pront = c1.text_input("Nº Prontuário:", key=f"p_{f_id}")
            q_cestas = c2.number_input("Cestas:", min_value=1, key=f"q_{f_id}")
            
            loc = st.radio("Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True, key=f"l_{f_id}")
            is_novo = st.toggle("NOVO CADASTRO", key=f"v_{f_id}")

            n_comp, n_id, n_bat, n_civ, n_conj, n_conj_id, n_conj_bat, n_end, n_bai, n_cep = "", 0, "", "Solteiro(a)", "", 0, "", "", "", ""

            if is_novo:
                n_comp = st.text_input("Nome Completo:", key=f"nc_{f_id}")
                d1, d2, d3 = st.columns(3)
                n_id = d1.number_input("Idade:", min_value=0, key=f"id_{f_id}")
                n_bat = d2.text_input("Tempo Batismo:", key=f"tb_{f_id}")
                n_civ = d3.selectbox("Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)"], key=f"ec_{f_id}")
                
                if n_civ == "Casado(a)":
                    n_conj = st.text_input("Cônjuge:", key=f"nj_{f_id}")
                    n_conj_id = st.number_input("Idade Cônjuge:", min_value=0, key=f"ij_{f_id}")
                
                n_end = st.text_input("Endereço:", key=f"en_{f_id}")
                n_bai = st.text_input("Bairro:", key=f"ba_{f_id}")
                n_cep = st.text_input("CEP (Obrigatório):", key=f"ce_{f_id}")

            if st.button("💾 SALVAR", type="primary", use_container_width=True):
                if not nome_sol or (is_novo and (n_id == 0 or not n_cep)):
                    st.error("Preencha Nome, Idade e CEP"); st.stop()

                payload = {
                    "tipo_solicitante": tipo_sol, "nome_solicitante": nome_sol, "num_prontuario": n_pront,
                    "quantidade_cestas": int(q_cestas), "local_retirada": loc, "nome_completo": n_comp,
                    "idade": int(n_id), "tempo_batismo": n_bat, "estado_civil": n_civ, "nome_conjuge": n_conj,
                    "idade_conjuge": int(n_conj_id), "endereco": n_end, "bairro": n_bai, "cep": n_cep,
                    "data_sistema": datetime.now().strftime('%d/%m/%Y %H:%M'), "tratado": False
                }
                supabase.table("registros_piedade").insert(payload).execute()
                st.success("Salvo!")
                time.sleep(1)
                resetar_tela()
                st.rerun()
