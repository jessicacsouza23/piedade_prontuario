import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="Sistema Piedade", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [aria-selected="true"] { background-color: #007bff !important; color: white !important; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 5px; background-color: white; }
    .nome-header { font-size: 1.1rem; font-weight: bold; color: #333; }
    .bloqueio-msg { background-color: #fff2f2; border: 1px solid #ff4b4b; padding: 20px; border-radius: 10px; color: #b91c1c; text-align: center; }
    .prontuario-item { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #007bff; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }
    .badge-comum { background-color: #fff3e0; color: #ef6c00; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #ffe0b2; }
    /* Estilo para os Cards de Resumo */
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #dcdfe3; }
    .metric-value { font-size: 1.8rem; font-weight: bold; color: #007bff; }
    .metric-label { font-size: 0.9rem; color: #555; text-transform: uppercase; letter-spacing: 1px; }
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
except:
    st.error("Erro de conexão com o banco de dados.")
    st.stop()

# --- ESTADO DA SESSÃO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'lista_prontuarios' not in st.session_state: st.session_state.lista_prontuarios = []
if 'form_key' not in st.session_state: st.session_state.form_key = 0
if 'p_key' not in st.session_state: st.session_state.p_key = 0 

def resetar_formulario():
    st.session_state.form_key += 1
    st.session_state.p_key += 1
    st.session_state.lista_prontuarios = []
    for key in list(st.session_state.keys()):
        if any(key.startswith(prefix) for prefix in ["f_", "n_", "c_", "ts_", "inv_"]):
            st.session_state.pop(key)

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Sistema Piedade")
    with st.container(border=True):
        cargo_sel = st.selectbox("Acesso:", ["Lançados", "Reserva de Cesta Básica"])
        senha = st.text_input("Senha:", type="password")
        if st.button("Entrar", use_container_width=True):
            if cargo_sel == "Reserva de Cesta Básica" and is_sistema_bloqueado():
                st.markdown("<div class='bloqueio-msg'><h3>🚫 ACESSO BLOQUEADO</h3><p>O prazo de reservas expirou.</p></div>", unsafe_allow_html=True)
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
        st.title("📋 Reserva de Cesta Básica")
        
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            
            # --- CÁLCULO DE MÉTRICAS ---
            pendentes = [x for x in dados if not x.get('tratado')]
            pronts_pendentes = [x for x in pendentes if not x.get('nome_completo')]
            novos_pendentes = [x for x in pendentes if x.get('nome_completo')]
            
            total_cestas = sum(int(x.get('quantidade_cestas') or 0) for x in pendentes)
            
            # --- PAINEL DE RESUMO ---
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.markdown(f"<div class='metric-card'><div class='metric-label'>📦 Total Cestas</div><div class='metric-value'>{total_cestas}</div></div>", unsafe_allow_html=True)
            with m2: st.markdown(f"<div class='metric-card'><div class='metric-label'>📋 Prontuários</div><div class='metric-value'>{len(pronts_pendentes)}</div></div>", unsafe_allow_html=True)
            with m3: st.markdown(f"<div class='metric-card'><div class='metric-label'>🆕 Casos Novos</div><div class='metric-value'>{len(novos_pendentes)}</div></div>", unsafe_allow_html=True)
            with m4: st.markdown(f"<div class='metric-card'><div class='metric-label'>📉 Total Casos</div><div class='metric-value'>{len(pendentes)}</div></div>", unsafe_allow_html=True)
            
            st.divider()

            tab_pront, tab_novos, tab_tratados = st.tabs(["📋 Prontuários", "🆕 Novos Cadastros", "✅ Tratados"])
            
            def render_card(item):
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 1.5, 2, 1.5])
                    with c1:
                        st.markdown(f"<div class='nome-header'>{item.get('nome_completo') or 'Prontuário: ' + str(item.get('num_prontuario'))}</div>", unsafe_allow_html=True)
                        if item.get('comum_assistido'): 
                            st.markdown(f"<span class='badge-comum'>⛪ Comum: {item.get('comum_assistido')}</span>", unsafe_allow_html=True)
                        st.caption(f"📅 Cadastro em: {item.get('data_sistema')}")
                    with c2:
                        st.markdown(f"**📦 {item.get('quantidade_cestas')} Cesta(s)**")
                        st.caption(f"📍 {item.get('local_retirada')}")
                    with c3:
                        st.markdown(f"**👤 {item.get('nome_solicitante')}**")
                        st.caption(f"De: {item.get('comum_solicitante')}")
                    with c4:
                        if not item.get('tratado'):
                            if st.button("Lançar", key=f"l_{item['id']}", use_container_width=True):
                                supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute()
                                st.rerun()
                        else: st.write("✅ Lançado")
                    
                    if item.get('nome_completo'):
                        with st.expander("🔍 FICHA COMPLETA"):
                            d1, d2 = st.columns(2)
                            with d1:
                                st.write(f"**Idade:** {item.get('idade')} | **Batismo:** {item.get('tempo_batismo')}")
                                st.write(f"**Endereço:** {item.get('endereco')} - {item.get('bairro')}")
                                st.write(f"**CEP:** {item.get('cep') or 'Não informado'}")
                            with d2:
                                if item.get('nome_conjuge'):
                                    st.write(f"**💍 Cônjuge:** {item.get('nome_conjuge')}")
                                    st.write(f"**Idade Cônjuge:** {item.get('idade_conjuge')}")
                                    st.write(f"**Batismo Cônjuge:** {item.get('batismo_conjuge')}")

            with tab_pront:
                if not pronts_pendentes: st.info("Nenhum prontuário pendente.")
                for p in pronts_pendentes: render_card(p)
            with tab_novos:
                if not novos_pendentes: st.info("Nenhum cadastro novo pendente.")
                for n in novos_pendentes: render_card(n)
            with tab_tratados:
                tratados = [x for x in dados if x.get('tratado')]
                if tratados and st.button("🚨 LIMPAR HISTÓRICO"):
                    supabase.table("registros_piedade").delete().eq("tratado", True).execute()
                    st.rerun()
                for t in tratados: render_card(t)

        except Exception as e: st.error(f"Erro: {e}")

    # --- VISÃO: RESERVA ---
    else:
        st.title("📝 Solicitação de Cesta Básica")
        f_key = st.session_state.form_key
        p_key = st.session_state.p_key
        
        with st.container(border=True):
            st.markdown("### 1. Identificação do Solicitante")
            col1, col2, col3 = st.columns([1, 1.5, 1.5])
            t_sol = col1.radio("Sou:", ["Diácono", "Irmã"], horizontal=True, key=f"ts_{f_key}")
            n_sol = col2.text_input("Seu Nome:", key=f"ns_{f_key}")
            c_sol = col3.text_input("Sua Comum Congregação:", key=f"cs_{f_key}")

        st.divider()
        st.markdown("### 2. Prontuários Existentes")
        with st.expander("➕ Adicionar Prontuário", expanded=True):
            col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
            num_p = col_p1.text_input("Nº do Prontuário", key=f"np_{p_key}")
            qtd_p = col_p2.number_input("Qtd Cestas", min_value=1, value=1, key=f"qp_{p_key}")
            if col_p3.button("Adicionar"):
                if num_p:
                    st.session_state.lista_prontuarios.append({"id": time.time(), "pront": num_p, "qtd": qtd_p})
                    st.session_state.p_key += 1
                    st.rerun()

        for i, p in enumerate(st.session_state.lista_prontuarios):
            c_i, c_d = st.columns([9, 1])
            c_i.markdown(f"<div class='prontuario-item'>Prontuário: {p['pront']} | Cestas: {p['qtd']}</div>", unsafe_allow_html=True)
            if c_d.button("🗑️", key=f"del_{p['id']}"):
                st.session_state.lista_prontuarios.pop(i)
                st.rerun()

        st.divider()
        st.markdown("### 3. Cadastro Novo")
        is_novo = st.toggle("INCLUIR NOVO CADASTRO?", key=f"inv_{f_key}")
        
        n_comp, n_id, n_bat, n_civ, n_conj, n_conj_id, n_conj_bat, n_end, n_bai, n_cep, c_ast, q_novo = "", 0, "", "Solteiro(a)", "", 0, "", "", "", "", "", 1
        
        if is_novo:
            with st.container(border=True):
                n_comp = st.text_input("Nome Completo do Assistido *:", key=f"nc_{f_key}")
                c_ast = st.text_input("Comum do Assistido:", key=f"ca_{f_key}")
                d1, d2, d3 = st.columns(3)
                n_id = d1.number_input("Idade do Assistido *:", min_value=0, key=f"id_{f_key}")
                n_bat = d2.text_input("Tempo Batismo (Assistido):", key=f"ba_{f_key}")
                n_civ = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"], key=f"civ_{f_key}")
                
                if n_civ == "Casado(a)":
                    with st.container(border=True):
                        nj1, nj2, nj3 = st.columns([2, 1, 1])
                        n_conj = nj1.text_input("Nome do Cônjuge *:", key=f"nco_{f_key}")
                        n_conj_id = nj2.number_input("Idade do Cônjuge *:", min_value=0, key=f"ico_{f_key}")
                        n_conj_bat = nj3.text_input("Batismo Cônjuge:", key=f"bco_{f_key}")
                
                n_end = st.text_input("Endereço:", key=f"en_{f_key}")
                b1, b2 = st.columns(2)
                n_bai, n_cep = b1.text_input("Bairro:", key=f"bai_{f_key}"), b2.text_input("CEP:", key=f"cep_{f_key}")
                q_novo = st.number_input("Quantidade Cestas:", min_value=1, key=f"qn_{f_key}")

        loc_ret = st.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True, key=f"loc_{f_key}")

        if st.button("💾 SALVAR TUDO", type="primary", use_container_width=True):
            if not n_sol or not c_sol: st.error("Identifique-se!"); st.stop()
            if is_novo:
                if not n_comp or n_id <= 0: st.error("Dados do assistido obrigatórios!"); st.stop()
                if n_civ == "Casado(a)" and (not n_conj or n_conj_id <= 0): st.error("Dados do cônjuge obrigatórios!"); st.stop()

            data_atual = datetime.now().strftime('%d/%m/%Y %H:%M')
            try:
                for item in st.session_state.lista_prontuarios:
                    supabase.table("registros_piedade").insert({"tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, "num_prontuario": str(item['pront']), "quantidade_cestas": int(item['qtd']), "local_retirada": loc_ret, "data_sistema": data_atual, "tratado": False}).execute()
                if is_novo:
                    supabase.table("registros_piedade").insert({"tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, "comum_assistido": c_ast, "nome_completo": n_comp, "quantidade_cestas": int(q_novo), "idade": int(n_id), "tempo_batismo": n_bat, "estado_civil": n_civ, "nome_conjuge": n_conj, "idade_conjuge": int(n_conj_id), "batismo_conjuge": n_conj_bat, "endereco": n_end, "bairro": n_bai, "cep": n_cep, "local_retirada": loc_ret, "data_sistema": data_atual, "tratado": False}).execute()
                
                st.balloons()
                st.success("✅ GRAVADO!"); time.sleep(1.5); resetar_formulario(); st.rerun()
            except Exception as e: st.error(f"Erro: {e}")
