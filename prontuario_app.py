import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd
import time
import io

st.set_page_config(page_title="Sistema Piedade", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILIZAÇÃO CSS AVANÇADA ---
st.markdown("""
    <style>
    /* Estilo dos Cards de Métrica */
    .metric-container {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e1e4e8;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: #1E3A8A; /* Azul Escuro */
        margin-bottom: 5px;
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    /* Tabs e Outros */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; border-radius: 8px; }
    .badge-comum { background-color: #DBEAFE; color: #1E40AF; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; }
    .nome-header { font-size: 1.15rem; font-weight: 700; color: #111827; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES CORE ---
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

# --- LOGIN E NAVEGAÇÃO ---
if not st.session_state.autenticado:
    st.title("⛪ Sistema Piedade")
    with st.container(border=True):
        cargo_sel = st.selectbox("Acesso:", ["Lançados", "Reserva de Cesta Básica"])
        senha = st.text_input("Senha:", type="password")
        if st.button("Entrar", use_container_width=True):
            if (cargo_sel == "Lançados" and senha == st.secrets.get("SENHA_DIACONO", "diacono123")) or \
               (cargo_sel == "Reserva de Cesta Básica" and senha == st.secrets.get("SENHA_IRMAS", "piedade123")):
                st.session_state.autenticado, st.session_state.cargo = True, cargo_sel
                st.rerun()
            else: st.error("Senha incorreta.")
else:
    # Cabeçalho Superior
    c_user, c_space, c_btn = st.columns([2, 3, 1])
    c_user.markdown(f"**Logado como:** `{st.session_state.cargo}`")
    if c_btn.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    # --- VISÃO: LANÇADOS (DIÁCONOS) ---
    if st.session_state.cargo == "Lançados":
        st.title("📋 Reserva de Cesta Básica")
        
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            
            # Filtros de Dados
            pendentes = [x for x in dados if not x.get('tratado')]
            pronts_pend = [x for x in pendentes if not x.get('nome_completo')]
            novos_pend = [x for x in pendentes if x.get('nome_completo')]
            
            # Cálculos das Métricas
            total_casos = len(pendentes)
            total_cestas = sum(int(x.get('quantidade_cestas') or 0) for x in pendentes)
            count_pront = len(pronts_pend)
            count_novos = len(novos_pend)

            # --- LINHA 1: DASHBOARD ---
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.markdown(f"<div class='metric-container'><div class='metric-label'>📦 Total Cestas</div><div class='metric-value'>{total_cestas}</div></div>", unsafe_allow_html=True)
            with m2: st.markdown(f"<div class='metric-container'><div class='metric-label'>📋 Prontuários</div><div class='metric-value'>{count_pront}</div></div>", unsafe_allow_html=True)
            with m3: st.markdown(f"<div class='metric-container'><div class='metric-label'>🆕 Novos Casos</div><div class='metric-value'>{count_novos}</div></div>", unsafe_allow_html=True)
            with m4: st.markdown(f"<div class='metric-container'><div class='metric-label'>📊 Total Casos</div><div class='metric-value'>{total_casos}</div></div>", unsafe_allow_html=True)

            # --- LINHA 2: EXPORTAÇÃO ---
            st.write("")
            col_exp_label, col_exp_btn = st.columns([4, 2])
            with col_exp_btn:
                if total_casos > 0:
                    df_export = pd.DataFrame(pendentes)
                    # Organizar colunas para o Diácono ver melhor no Excel
                    cols_ordem = ['num_prontuario', 'nome_completo', 'quantidade_cestas', 'local_retirada', 'comum_assistido', 'nome_solicitante', 'data_sistema']
                    df_export = df_export[[c for c in cols_ordem if c in df_export.columns]]
                    
                    csv = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button(
                        label="📥 BAIXAR LISTA PARA EXCEL (CSV)",
                        data=csv,
                        file_name=f"piedade_pendentes_{datetime.now().strftime('%d_%m')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        type="primary"
                    )

            st.divider()

            # --- ABAS DE LISTAGEM ---
            tab_p, tab_n, tab_t = st.tabs(["📋 Prontuários Pendentes", "🆕 Novos para Análise", "✅ Histórico Tratados"])
            
            def render_card(item):
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 1.5, 2, 1.5])
                    with c1:
                        st.markdown(f"<div class='nome-header'>{item.get('nome_completo') or 'Prontuário: ' + str(item.get('num_prontuario'))}</div>", unsafe_allow_html=True)
                        if item.get('comum_assistido'): st.markdown(f"<span class='badge-comum'>⛪ {item.get('comum_assistido')}</span>", unsafe_allow_html=True)
                        st.caption(f"📅 Registrado em: {item.get('data_sistema')}")
                    with c2: st.markdown(f"**📦 {item.get('quantidade_cestas')} Cesta(s)**"); st.caption(f"📍 {item.get('local_retirada')}")
                    with c3: st.markdown(f"**👤 {item.get('nome_solicitante')}**"); st.caption(f"Sol.: {item.get('comum_solicitante')}")
                    with c4:
                        if not item.get('tratado'):
                            if st.button("Lançar", key=f"l_{item['id']}", use_container_width=True):
                                supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute()
                                st.rerun()
                        else: st.write("✅ Concluído")

            with tab_p:
                if not pronts_pend: st.info("Nenhum prontuário aguardando.")
                for p in pronts_pend: render_card(p)
            
            with tab_n:
                if not novos_pend: st.info("Nenhum cadastro novo pendente.")
                for n in novos_pend: render_card(n)
                
            with tab_t:
                tratados = [x for x in dados if x.get('tratado')]
                if tratados and st.button("🚨 LIMPAR HISTÓRICO CONCLUÍDO"):
                    supabase.table("registros_piedade").delete().eq("tratado", True).execute()
                    st.rerun()
                for t in tratados: render_card(t)

        except Exception as e: st.error(f"Erro ao carregar dados: {e}")

    # --- VISÃO: RESERVA (IRMÃS/DIÁCONOS) ---
    else:
        st.title("📝 Solicitação de Cesta Básica")
        f_key, p_key = st.session_state.form_key, st.session_state.p_key
        
        with st.container(border=True):
            st.markdown("#### 👤 Quem está solicitando?")
            c1, c2, c3 = st.columns([1, 1.5, 1.5])
            t_sol = c1.radio("Cargo:", ["Diácono", "Irmã"], horizontal=True, key=f"ts_{f_key}")
            n_sol = c2.text_input("Seu Nome:", key=f"ns_{f_key}")
            c_sol = c3.text_input("Sua Comum Congregação:", key=f"cs_{f_key}")

        st.divider()
        
        # Prontuários
        st.markdown("#### 📋 Prontuários Existentes")
        with st.expander("Adicionar Prontuário à Lista", expanded=True):
            cp1, cp2, cp3 = st.columns([2, 1, 1])
            num_p = cp1.text_input("Número do Prontuário", key=f"np_{p_key}")
            qtd_p = cp2.number_input("Qtd de Cesta", min_value=1, value=1, key=f"qp_{p_key}")
            if cp3.button("➕ Adicionar"):
                if num_p:
                    if any(x['pront'] == num_p for x in st.session_state.lista_prontuarios):
                        st.error("Já está na lista.")
                    else:
                        st.session_state.lista_prontuarios.append({"id": time.time(), "pront": num_p, "qtd": qtd_p})
                        st.session_state.p_key += 1; st.rerun()

        for i, p in enumerate(st.session_state.lista_prontuarios):
            ci, cd = st.columns([9, 1])
            ci.markdown(f"<div class='prontuario-item'>Nº {p['pront']} — {p['qtd']} cesta(s)</div>", unsafe_allow_html=True)
            if cd.button("🗑️", key=f"del_{p['id']}"):
                st.session_state.lista_prontuarios.pop(i); st.rerun()

        st.divider()
        
        # Cadastro Novo
        st.markdown("#### 🆕 Caso Novo (Sem Prontuário)")
        is_novo = st.toggle("Houve algum caso novo este mês?", key=f"inv_{f_key}")
        
        if is_novo:
            with st.container(border=True):
                n_comp = st.text_input("Nome Completo do Assistido *:", key=f"nc_{f_key}")
                c_ast = st.text_input("Comum do Assistido:", key=f"ca_{f_key}")
                d1, d2, d3 = st.columns(3)
                n_id = d1.number_input("Idade *:", min_value=0, key=f"id_{f_key}")
                n_bat = d2.text_input("Tempo de Batismo:", key=f"ba_{f_key}")
                n_civ = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"], key=f"civ_{f_key}")
                
                n_conj, n_conj_id, n_conj_bat = "", 0, ""
                if n_civ == "Casado(a)":
                    nj1, nj2, nj3 = st.columns([2, 1, 1])
                    n_conj = nj1.text_input("Nome Cônjuge *:", key=f"nco_{f_key}")
                    n_conj_id = nj2.number_input("Idade Cônjuge *:", min_value=0, key=f"ico_{f_key}")
                    n_conj_bat = nj3.text_input("Batismo Cônjuge:", key=f"bco_{f_key}")
                
                n_end = st.text_input("Endereço Completo:", key=f"en_{f_key}")
                b1, b2 = st.columns(2)
                n_bai, n_cep = b1.text_input("Bairro:", key=f"bai_{f_key}"), b2.text_input("CEP:", key=f"cep_{f_key}")
                q_novo = st.number_input("Qtd de Cestas (Novo):", min_value=1, key=f"qn_{f_key}")

        loc_ret = st.radio("Local de Retirada das Cestas:", ["Pq. Guarani", "Itaquera"], horizontal=True, key=f"loc_{f_key}")

        if st.button("💾 FINALIZAR E ENVIAR RESERVA", type="primary", use_container_width=True):
            if not n_sol or not c_sol: st.error("Por favor, preencha seu nome e sua comum."); st.stop()
            
            # Validação Duplicidade Global
            try:
                res_check = supabase.table("registros_piedade").select("num_prontuario").execute()
                banco_p = [str(x['num_prontuario']) for x in res_check.data if x['num_prontuario']]
                for p in st.session_state.lista_prontuarios:
                    if str(p['pront']) in banco_p:
                        st.error(f"O prontuário {p['pront']} já existe no sistema!"); st.stop()
            except: pass

            if is_novo and (not n_comp or n_id <= 0): st.error("Preencha os dados do novo assistido."); st.stop()

            data_agora = datetime.now().strftime('%d/%m/%Y %H:%M')
            try:
                for it in st.session_state.lista_prontuarios:
                    supabase.table("registros_piedade").insert({"tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, "num_prontuario": str(it['pront']), "quantidade_cestas": int(it['qtd']), "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False}).execute()
                if is_novo:
                    supabase.table("registros_piedade").insert({"tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, "nome_completo": n_comp, "comum_assistido": c_ast, "quantidade_cestas": int(q_novo), "idade": int(n_id), "tempo_batismo": n_bat, "estado_civil": n_civ, "nome_conjuge": n_conj, "idade_conjuge": int(n_conj_id), "batismo_conjuge": n_conj_bat, "endereco": n_end, "bairro": n_bai, "cep": n_cep, "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False}).execute()
                
                st.balloons(); st.success("✅ RESERVA ENVIADA COM SUCESSO!"); time.sleep(1.5); resetar_formulario(); st.rerun()
            except Exception as e: st.error(f"Erro ao salvar: {e}")
