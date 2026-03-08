import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="Sistema Piedade", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .stTabs [aria-selected="true"] { background-color: #007bff !important; color: white !important; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 5px; background-color: white; }
    .badge-info { background-color: #e1f5fe; color: #01579b; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
    .badge-comum { background-color: #fff3e0; color: #ef6c00; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #ffe0b2; }
    .nome-header { font-size: 1.2rem; font-weight: bold; color: #333; }
    .bloqueio-msg { background-color: #fff2f2; border: 1px solid #ff4b4b; padding: 20px; border-radius: 10px; color: #b91c1c; text-align: center; }
    .prontuario-item { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #007bff; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO DE BLOQUEIO ---
def is_sistema_bloqueado():
    hoje = datetime.now().date()
    primeiro_dia = hoje.replace(day=1)
    dias_ate_sabado = (5 - primeiro_dia.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia + timedelta(days=dias_ate_sabado)
    terca_bloqueio = primeiro_sabado - timedelta(days=4)
    return hoje == terca_bloqueio

# --- CONEXÃO ---
def inicializar_conexao():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase: Client = inicializar_conexao()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- ESTADO DA SESSÃO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'lista_prontuarios' not in st.session_state: st.session_state.lista_prontuarios = []

def resetar_tela():
    for key in list(st.session_state.keys()):
        if key not in ['autenticado', 'cargo']: 
            st.session_state.pop(key)
    st.session_state.lista_prontuarios = []

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Sistema Piedade")
    with st.container(border=True):
        cargo_sel = st.selectbox("Acesso:", ["Lançados", "Reserva de Cesta Básica"])
        senha = st.text_input("Senha:", type="password")
        if st.button("Entrar", use_container_width=True):
            if cargo_sel == "Reserva de Cesta Básica" and is_sistema_bloqueado():
                st.markdown(f"<div class='bloqueio-msg'><h3>🚫 BLOQUEADO</h3><p>Entre em contato com Irmã Cal: (11) 97393-9407</p></div>", unsafe_allow_html=True)
            elif (cargo_sel == "Lançados" and senha == st.secrets.get("SENHA_DIACONO", "diacono123")) or \
                 (cargo_sel == "Reserva de Cesta Básica" and senha == st.secrets.get("SENHA_IRMAS", "piedade123")):
                st.session_state.autenticado, st.session_state.cargo = True, cargo_sel
                st.rerun()
            else: st.error("Senha incorreta.")
else:
    col_tit, col_sair = st.columns([5, 1])
    with col_tit: st.subheader(f"👤 {st.session_state.cargo}")
    with col_sair:
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()

    # --- VISÃO: LANÇADOS ---
    if st.session_state.cargo == "Lançados":
        st.title("📋 Pedidos para Lançamento")
        try:
            res = supabase.table("registros_piedade").select("*").eq("tratado", False).order("data_sistema", desc=True).execute()
            if not res.data:
                st.info("Nenhum pedido pendente.")
            for item in res.data:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    with c1:
                        st.markdown(f"<div class='nome-header'>{item.get('nome_completo') or 'Prontuário: ' + str(item.get('num_prontuario'))}</div>", unsafe_allow_html=True)
                        if item.get('comum_assistido'): 
                            st.markdown(f"<span class='badge-comum'>⛪ Comum: {item.get('comum_assistido')}</span>", unsafe_allow_html=True)
                        st.caption(f"📍 {item.get('local_retirada')} | 📅 {item.get('data_sistema')}")
                    with c2:
                        st.markdown(f"**📦 {item.get('quantidade_cestas')} Cesta(s)**")
                    with c3:
                        st.markdown(f"**👤 {item.get('nome_solicitante')}**")
                        st.caption(f"De: {item.get('comum_solicitante')}")
                    with c4:
                        if st.button("Lançar", key=f"l_{item['id']}", use_container_width=True):
                            supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute()
                            st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

    # --- VISÃO: RESERVA DE CESTA ---
    else:
        st.title("📝 Nova Reserva")
        
        with st.container(border=True):
            st.markdown("### 1. Identificação do Solicitante")
            col1, col2, col3 = st.columns([1, 1.5, 1.5])
            t_sol = col1.radio("Sou:", ["Diácono", "Irmã"], horizontal=True)
            n_sol = col2.text_input("Seu Nome:")
            c_sol = col3.text_input("Sua Comum Congregação:")

        st.divider()
        
        st.markdown("### 2. Prontuários e Cestas")
        with st.expander("➕ Adicionar Prontuário à Lista", expanded=True):
            col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
            num_p = col_p1.text_input("Nº do Prontuário")
            qtd_p = col_p2.number_input("Qtd Cestas", min_value=1, value=1)
            if col_p3.button("Adicionar", use_container_width=True):
                if num_p:
                    # Gera um ID temporário baseado no timestamp para exclusão precisa
                    st.session_state.lista_prontuarios.append({"id": time.time(), "pront": num_p, "qtd": qtd_p})
                    st.rerun()
                else: st.warning("Digite o número.")

        # Exibição da Lista com Botão de Excluir Individual
        if st.session_state.lista_prontuarios:
            st.markdown("##### Itens na lista:")
            for i, p in enumerate(st.session_state.lista_prontuarios):
                col_item, col_del = st.columns([9, 1])
                with col_item:
                    st.markdown(f"<div class='prontuario-item'><b>Prontuário:</b> {p['pront']} | <b>Cestas:</b> {p['qtd']}</div>", unsafe_allow_html=True)
                with col_del:
                    if st.button("🗑️", key=f"del_{p['id']}"):
                        st.session_state.lista_prontuarios.pop(i)
                        st.rerun()

        st.divider()

        st.markdown("### 3. Cadastro Novo (Se houver)")
        is_novo = st.toggle("INCLUIR NOVO CADASTRO?")
        
        n_comp, n_id, n_bat, n_civ, n_conj, n_conj_id, n_end, n_cep, c_ast, q_novo = "", 0, "", "Solteiro(a)", "", 0, "", "", "", 1
        
        if is_novo:
            with st.container(border=True):
                n_comp = st.text_input("Nome Completo do Assistido:")
                c_ast = st.text_input("Comum do Assistido (Novo Cadastro):")
                d1, d2, d3 = st.columns(3)
                n_id = d1.number_input("Idade:", min_value=0)
                n_bat = d2.text_input("Tempo de Batismo:")
                n_civ = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"])
                if n_civ == "Casado(a)":
                    nj1, nj2 = st.columns([3, 1])
                    n_conj, n_conj_id = nj1.text_input("Nome Cônjuge:"), nj2.number_input("Idade Cônjuge:", min_value=0)
                n_end, n_cep = st.text_input("Endereço:"), st.text_input("CEP:")
                q_novo = st.number_input("Cestas para este novo:", min_value=1, value=1)

        loc_ret = st.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True)

        if st.button("💾 FINALIZAR TODA RESERVA", type="primary", use_container_width=True):
            if not n_sol or not c_sol:
                st.error("Nome e Comum do solicitante são obrigatórios!"); st.stop()
            
            prazos = datetime.now().strftime('%d/%m/%Y %H:%M')
            sucesso = False
            try:
                # Salvar Lista de Prontuários
                for item in st.session_state.lista_prontuarios:
                    payload = {
                        "tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol,
                        "num_prontuario": str(item['pront']), "quantidade_cestas": int(item['qtd']), 
                        "local_retirada": loc_ret, "data_sistema": prazos, "tratado": False
                    }
                    supabase.table("registros_piedade").insert(payload).execute()
                    sucesso = True
                
                # Salvar Novo Cadastro
                if is_novo and n_comp:
                    payload_n = {
                        "tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol,
                        "comum_assistido": c_ast, "nome_completo": n_comp, "quantidade_cestas": int(q_novo),
                        "idade": int(n_id), "estado_civil": n_civ, "nome_conjuge": n_conj, 
                        "idade_conjuge": int(n_conj_id), "endereco": n_end, "cep": n_cep, 
                        "local_retirada": loc_ret, "data_sistema": prazos, "tratado": False
                    }
                    supabase.table("registros_piedade").insert(payload_n).execute()
                    sucesso = True
                
                if sucesso:
                    st.success("✅ Reserva gravada com sucesso!")
                    time.sleep(1.5)
                    resetar_tela()
                    st.rerun()
                else:
                    st.warning("Adicione itens à lista ou preencha o cadastro novo.")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
