import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd
import time
import io

st.set_page_config(page_title="Sistema Piedade", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .metric-container { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e1e4e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .metric-value { font-size: 2rem; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .metric-label { font-size: 0.85rem; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; border-radius: 8px; }
    .badge-comum { background-color: #DBEAFE; color: #1E40AF; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; }
    .nome-header { font-size: 1.2rem; font-weight: 700; color: #111827; }
    .info-box { background-color: #f9fafb; padding: 15px; border-radius: 8px; border: 1px solid #edf2f7; margin-top: 10px; }
    .label-info { color: #4b5563; font-weight: 600; font-size: 0.9rem; }
    .value-info { color: #1f2937; font-weight: 400; font-size: 0.95rem; }
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

# --- LOGIN ---
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
    c_user, c_space, c_btn = st.columns([2, 3, 1])
    c_user.markdown(f"**Logado como:** `{st.session_state.cargo}`")
    if c_btn.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    # --- VISÃO: LANÇADOS ---
    if st.session_state.cargo == "Lançados":
        st.title("📋 Painel de Controle")
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            pendentes = [x for x in dados if not x.get('tratado')]
            pronts_pend = [x for x in pendentes if not x.get('nome_completo')]
            novos_pend = [x for x in pendentes if x.get('nome_completo')]
            
            # Métricas
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f"<div class='metric-container'><div class='metric-label'>📦 Total Cestas</div><div class='metric-value'>{sum(int(x.get('quantidade_cestas') or 0) for x in pendentes)}</div></div>", unsafe_allow_html=True)
            m2.markdown(f"<div class='metric-container'><div class='metric-label'>📋 Prontuários</div><div class='metric-value'>{len(pronts_pend)}</div></div>", unsafe_allow_html=True)
            m3.markdown(f"<div class='metric-container'><div class='metric-label'>🆕 Novos Casos</div><div class='metric-value'>{len(novos_pend)}</div></div>", unsafe_allow_html=True)
            m4.markdown(f"<div class='metric-container'><div class='metric-label'>📊 Total Casos</div><div class='metric-value'>{len(pendentes)}</div></div>", unsafe_allow_html=True)

            st.write("")
            if pendentes:
                df_export = pd.DataFrame(pendentes)
                csv = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 BAIXAR LISTA COMPLETA (CSV)", csv, f"piedade_{datetime.now().strftime('%d_%m')}.csv", "text/csv", use_container_width=True, type="primary")

            st.divider()
            tab_p, tab_n, tab_t = st.tabs(["📋 Prontuários Pendentes", "🆕 Novos para Análise", "✅ Histórico Tratados"])

            with tab_p:
                for item in pronts_pend:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 2, 1])
                        c1.markdown(f"<div class='nome-header'>Prontuário: {item['num_prontuario']}</div>", unsafe_allow_html=True)
                        c1.caption(f"📅 {item['data_sistema']} | Solicitado por: {item['nome_solicitante']} ({item['comum_solicitante']})")
                        c2.markdown(f"**📦 {item['quantidade_cestas']} Cesta(s)** | 📍 {item['local_retirada']}")
                        if c3.button("Lançar", key=f"lp_{item['id']}", use_container_width=True):
                            supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute(); st.rerun()

            with tab_n:
                for item in novos_pend:
                    with st.container(border=True):
                        st.markdown(f"<div class='nome-header'>👤 {item['nome_completo']}</div>", unsafe_allow_html=True)
                        
                        # Grid de Informações Detalhadas
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.markdown(f"<span class='label-info'>🎂 Idade:</span> <span class='value-info'>{item.get('idade')} anos</span>", unsafe_allow_html=True)
                            st.markdown(f"<span class='label-info'>💍 Estado Civil:</span> <span class='value-info'>{item.get('estado_civil')}</span>", unsafe_allow_html=True)
                        with col_b:
                            st.markdown(f"<span class='label-info'>⛪ Comum:</span> <span class='value-info'>{item.get('comum_assistido')}</span>", unsafe_allow_html=True)
                            st.markdown(f"<span class='label-info'>🌊 Batismo:</span> <span class='value-info'>{item.get('tempo_batismo') or 'Não inf.'}</span>", unsafe_allow_html=True)
                        with col_c:
                            st.markdown(f"<span class='label-info'>📦 Cestas:</span> <span class='value-info'>{item.get('quantidade_cestas')} un.</span>", unsafe_allow_html=True)
                            st.markdown(f"<span class='label-info'>📅 Data:</span> <span class='value-info'>{item.get('data_sistema')}</span>", unsafe_allow_html=True)

                        # Seção Cônjuge (Se for Casado)
                        if item.get('estado_civil') == "Casado(a)":
                            st.markdown("""<div style='margin-top:10px; border-top:1px dashed #ddd; padding-top:10px;'>
                                <span class='label-info'>👩‍❤️‍👨 Dados do Cônjuge:</span></div>""", unsafe_allow_html=True)
                            ca, cb, cc = st.columns(3)
                            ca.markdown(f"<span class='label-info'>Nome:</span> <span class='value-info'>{item.get('nome_conjuge')}</span>", unsafe_allow_html=True)
                            cb.markdown(f"<span class='label-info'>Idade:</span> <span class='value-info'>{item.get('idade_conjuge')} anos</span>", unsafe_allow_html=True)
                            cc.markdown(f"<span class='label-info'>Batismo:</span> <span class='value-info'>{item.get('batismo_conjuge') or 'Não inf.'}</span>", unsafe_allow_html=True)

                        st.markdown(f"<div style='margin-top:5px;'><span class='label-info'>📍 Local Retirada:</span> <span class='value-info'>{item.get('local_retirada')}</span> | <span class='label-info'>🏠 Endereço:</span> <span class='value-info'>{item.get('endereco')}, {item.get('bairro')}</span></div>", unsafe_allow_html=True)
                        
                        if st.button("Marcar como Lançado", key=f"ln_{item['id']}", type="primary"):
                            supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute(); st.rerun()

            with tab_t:
                tratados = [x for x in dados if x.get('tratado')]
                if tratados and st.button("🚨 LIMPAR HISTÓRICO"):
                    supabase.table("registros_piedade").delete().eq("tratado", True).execute(); st.rerun()
                for t in tratados:
                    st.text(f"✅ {t.get('nome_completo') or 'Pront. ' + str(t.get('num_prontuario'))} - {t.get('data_sistema')}")

        except Exception as e: st.error(f"Erro: {e}")

    # --- VISÃO: RESERVA ---
    else:
        st.title("📝 Reserva de Cestas")
        f_key, p_key = st.session_state.form_key, st.session_state.p_key
        
        with st.container(border=True):
            st.markdown("#### 👤 Identificação do Solicitante")
            c1, c2, c3 = st.columns([1, 1.5, 1.5])
            t_sol = c1.radio("Cargo:", ["Diácono", "Irmã"], horizontal=True, key=f"ts_{f_key}")
            n_sol = c2.text_input("Seu Nome:", key=f"ns_{f_key}")
            c_sol = c3.text_input("Sua Comum:", key=f"cs_{f_key}")

        st.divider()
        st.markdown("#### 📋 Prontuários Existentes")
        with st.expander("Adicionar Prontuário", expanded=True):
            cp1, cp2, cp3 = st.columns([2, 1, 1])
            num_p = cp1.text_input("Número do Prontuário", key=f"np_{p_key}")
            qtd_p = cp2.number_input("Qtd", min_value=1, value=1, key=f"qp_{p_key}")
            if cp3.button("➕ Adicionar"):
                if num_p:
                    if any(x['pront'] == num_p for x in st.session_state.lista_prontuarios): st.error("Já está na lista.")
                    else:
                        st.session_state.lista_prontuarios.append({"id": time.time(), "pront": num_p, "qtd": qtd_p})
                        st.session_state.p_key += 1; st.rerun()

        for i, p in enumerate(st.session_state.lista_prontuarios):
            ci, cd = st.columns([9, 1])
            ci.info(f"Nº {p['pront']} — {p['qtd']} cesta(s)")
            if cd.button("🗑️", key=f"del_{p['id']}"): st.session_state.lista_prontuarios.pop(i); st.rerun()

        st.divider()
        st.markdown("#### 🆕 Caso Novo")
        is_novo = st.toggle("Cadastrar pessoa sem prontuário?", key=f"inv_{f_key}")
        if is_novo:
            with st.container(border=True):
                n_comp = st.text_input("Nome Completo *:", key=f"nc_{f_key}")
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
                n_end = st.text_input("Endereço:", key=f"en_{f_key}")
                b1, b2 = st.columns(2)
                n_bai, n_cep = b1.text_input("Bairro:", key=f"bai_{f_key}"), b2.text_input("CEP:", key=f"cep_{f_key}")
                q_novo = st.number_input("Qtd de Cestas:", min_value=1, key=f"qn_{f_key}")

        loc_ret = st.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True, key=f"loc_{f_key}")

        if st.button("💾 ENVIAR RESERVA", type="primary", use_container_width=True):
            if not n_sol or not c_sol: st.error("Identifique-se!"); st.stop()
            try:
                res_check = supabase.table("registros_piedade").select("num_prontuario").execute()
                banco_p = [str(x['num_prontuario']) for x in res_check.data if x['num_prontuario']]
                for p in st.session_state.lista_prontuarios:
                    if str(p['pront']) in banco_p: st.error(f"Prontuário {p['pront']} já existe!"); st.stop()
            except: pass
            if is_novo and (not n_comp or n_id <= 0): st.error("Preencha Nome e Idade."); st.stop()
            data_agora = datetime.now().strftime('%d/%m/%Y %H:%M')
            try:
                for it in st.session_state.lista_prontuarios:
                    supabase.table("registros_piedade").insert({"tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, "num_prontuario": str(it['pront']), "quantidade_cestas": int(it['qtd']), "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False}).execute()
                if is_novo:
                    supabase.table("registros_piedade").insert({"tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, "nome_completo": n_comp, "comum_assistido": c_ast, "quantidade_cestas": int(q_novo), "idade": int(n_id), "tempo_batismo": n_bat, "estado_civil": n_civ, "nome_conjuge": n_conj, "idade_conjuge": int(n_conj_id), "batismo_conjuge": n_conj_bat, "endereco": n_end, "bairro": n_bai, "cep": n_cep, "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False}).execute()
                st.balloons(); st.success("✅ ENVIADO!"); time.sleep(1); resetar_formulario(); st.rerun()
            except Exception as e: st.error(f"Erro: {e}")
