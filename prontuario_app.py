import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="Sistema Piedade", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .metric-container { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e1e4e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; margin-bottom: 10px; }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #1E3A8A; }
    .metric-label { font-size: 0.7rem; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; border-radius: 8px; }
    .nome-header { font-size: 1.1rem; font-weight: 800; color: #1E3A8A; border-left: 5px solid #1E3A8A; padding-left: 10px; }
    .label-info { color: #6B7280; font-weight: 700; font-size: 0.8rem; text-transform: uppercase; }
    .value-info { color: #111827; font-weight: 500; font-size: 0.95rem; }
    .section-divider { border-top: 1px solid #e5e7eb; margin: 12px 0 8px 0; padding-top: 5px; font-weight: bold; color: #4B5563; font-size: 0.85rem; }
    .stDownloadButton button { width: 100% !important; border-radius: 8px !important; font-weight: bold !important; }
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
        col_tit, col_sync = st.columns([4, 1])
        col_tit.title("📋 Painel de Controle")
        if col_sync.button("🔄 Sincronizar", use_container_width=True):
            st.toast("Atualizando dados...")
            time.sleep(0.5)
            st.rerun()
            
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            df_all = pd.DataFrame(dados) if dados else pd.DataFrame()
            
            if not df_all.empty:
                pendentes_df = df_all[df_all['tratado'] == False].copy()
                pronts_pend_df = pendentes_df[pendentes_df['nome_completo'].isna() | (pendentes_df['nome_completo'] == "")]
                novos_pend_df = pendentes_df[pendentes_df['nome_completo'].notna() & (pendentes_df['nome_completo'] != "")]

                st.markdown("##### 📊 Controle de Casos")
                c_casos, c_pront, c_novos = st.columns(3)
                c_casos.markdown(f"<div class='metric-container'><div class='metric-label'>📝 Total de Casos</div><div class='metric-value'>{len(pendentes_df)}</div></div>", unsafe_allow_html=True)
                c_pront.markdown(f"<div class='metric-container'><div class='metric-label'>📋 Prontuários</div><div class='metric-value'>{len(pronts_pend_df)}</div></div>", unsafe_allow_html=True)
                c_novos.markdown(f"<div class='metric-container'><div class='metric-label'>🆕 Novos Casos</div><div class='metric-value'>{len(novos_pend_df)}</div></div>", unsafe_allow_html=True)

                st.markdown("##### 📦 Logística de Cestas")
                m_total, m_ita, m_gua = st.columns(3)
                total_geral_cestas = int(pendentes_df['quantidade_cestas'].sum())
                m_total.markdown(f"<div class='metric-container'><div class='metric-label'>📦 Total Cestas</div><div class='metric-value'>{total_geral_cestas}</div></div>", unsafe_allow_html=True)
                soma_ita = int(pendentes_df[pendentes_df['local_retirada'] == "Itaquera"]['quantidade_cestas'].sum())
                m_ita.markdown(f"<div class='metric-container'><div class='metric-label'>📍 Itaquera</div><div class='metric-value'>{soma_ita}</div></div>", unsafe_allow_html=True)
                soma_gua = int(pendentes_df[pendentes_df['local_retirada'] == "Pq. Guarani"]['quantidade_cestas'].sum())
                m_gua.markdown(f"<div class='metric-container'><div class='metric-label'>📍 Pq. Guarani</div><div class='metric-value'>{soma_gua}</div></div>", unsafe_allow_html=True)

                st.write("")
                exp1, exp2 = st.columns(2)
                
                with exp1:
                    if not pronts_pend_df.empty:
                        map_p = {'data_sistema': 'Data', 'local_retirada': 'Local Retirada', 'tipo_solicitante': 'Cargo Solicitante', 'nome_solicitante': 'Solicitante', 'num_prontuario': 'Prontuário', 'quantidade_cestas': 'Qtd'}
                        csv_p = pronts_pend_df[list(map_p.keys())].rename(columns=map_p).to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                        st.download_button("📥 EXCEL: PRONTUÁRIOS", csv_p, f"prontuarios_{datetime.now().strftime('%d_%m')}.csv", "text/csv", type="primary")

                with exp2:
                    if not novos_pend_df.empty:
                        map_n = {'data_sistema': 'Data Pedido', 'local_retirada': 'Local Retirada', 'tipo_solicitante': 'Cargo Solicitante', 'nome_solicitante': 'Solicitante', 'comum_solicitante': 'Comum Solicitante', 'nome_completo': 'Nome Assistido', 'quantidade_cestas': 'Qtd Cestas', 'idade': 'Idade', 'estado_civil': 'Estado Civil', 'comum_assistido': 'Comum Assistido', 'tempo_batismo': 'Tempo Batismo', 'nome_conjuge': 'Nome Cônjuge', 'idade_conjuge': 'Idade Cônjuge', 'batismo_conjuge': 'Batismo Cônjuge', 'endereco': 'Endereço', 'bairro': 'Bairro', 'cep': 'CEP'}
                        cols_existentes = [c for c in map_n.keys() if c in novos_pend_df.columns]
                        csv_n = novos_pend_df[cols_existentes].rename(columns=map_n).to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                        st.download_button("📥 EXCEL: CASOS NOVOS", csv_n, f"casos_novos_{datetime.now().strftime('%d_%m')}.csv", "text/csv", type="primary")

                st.divider()
                tab_p, tab_n, tab_t = st.tabs(["📋 Prontuários", "🆕 Novos Casos", "✅ Histórico"])

                with tab_p:
                    for _, item in pronts_pend_df.iterrows():
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"<div class='nome-header'>Prontuário: {item['num_prontuario']}</div>", unsafe_allow_html=True)
                            c1.caption(f"📅 {item['data_sistema']} | Solicitante: {item['nome_solicitante']} ({item['tipo_solicitante']})")
                            c2.markdown(f"**📦 {item['quantidade_cestas']} Cesta(s)** | 📍 {item['local_retirada']}")
                            if c3.button("Lançar", key=f"lp_{item['id']}", use_container_width=True):
                                supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute(); st.rerun()

                with tab_n:
                    for _, item in novos_pend_df.iterrows():
                        with st.container(border=True):
                            st.markdown(f"<div class='nome-header'>👤 {item['nome_completo']}</div>", unsafe_allow_html=True)
                            col1, col2, col3, col4 = st.columns(4)
                            col1.markdown(f"<span class='label-info'>🎂 Idade</span><br><span class='value-info'>{item['idade']} anos</span>", unsafe_allow_html=True)
                            col2.markdown(f"<span class='label-info'>💍 Est. Civil</span><br><span class='value-info'>{item['estado_civil']}</span>", unsafe_allow_html=True)
                            col3.markdown(f"<span class='label-info'>⛪ Comum</span><br><span class='value-info'>{item['comum_assistido']}</span>", unsafe_allow_html=True)
                            col4.markdown(f"<span class='label-info'>🌊 Batismo</span><br><span class='value-info'>{item['tempo_batismo'] or '---'}</span>", unsafe_allow_html=True)
                            
                            if item['estado_civil'] == "Casado(a)":
                                st.markdown("<div class='section-divider'>👩‍❤️‍👨 Dados do Cônjuge</div>", unsafe_allow_html=True)
                                cj1, cj2, cj3 = st.columns([2, 1, 1])
                                cj1.markdown(f"<span class='label-info'>Nome</span><br><span class='value-info'>{item['nome_conjuge']}</span>", unsafe_allow_html=True)
                                cj2.markdown(f"<span class='label-info'>Idade</span><br><span class='value-info'>{item['idade_conjuge']} anos</span>", unsafe_allow_html=True)
                                cj3.markdown(f"<span class='label-info'>Batismo</span><br><span class='value-info'>{item['batismo_conjuge'] or '---'}</span>", unsafe_allow_html=True)

                            st.markdown("<div class='section-divider'>📍 Endereço e Pedido</div>", unsafe_allow_html=True)
                            end1, end2, end3 = st.columns([2, 1, 1])
                            end1.markdown(f"<span class='label-info'>Endereço</span><br><span class='value-info'>{item['endereco']}</span>", unsafe_allow_html=True)
                            end2.markdown(f"<span class='label-info'>Bairro</span><br><span class='value-info'>{item['bairro']}</span>", unsafe_allow_html=True)
                            end3.markdown(f"<span class='label-info'>📦 Qtd / Local</span><br><span class='value-info'>{item['quantidade_cestas']} un / {item['local_retirada']}</span>", unsafe_allow_html=True)
                            
                            st.caption(f"Solicitante: {item['nome_solicitante']} ({item['tipo_solicitante']}) - {item['data_sistema']}")
                            if st.button("Concluir Lançamento", key=f"ln_{item['id']}", type="primary", use_container_width=True):
                                supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute(); st.rerun()

                with tab_t:
                    tratados = df_all[df_all['tratado'] == True]
                    if not tratados.empty:
                        if st.button("🚨 LIMPAR HISTÓRICO"):
                            supabase.table("registros_piedade").delete().eq("tratado", True).execute(); st.rerun()
                        for _, t in tratados.iterrows():
                            st.text(f"✅ {t['nome_completo'] if pd.notna(t['nome_completo']) and t['nome_completo'] != '' else 'Pront. ' + str(t['num_prontuario'])} - {t['data_sistema']}")
            else:
                st.info("Não há pedidos pendentes.")

        except Exception as e: st.error(f"Erro: {e}")

    # --- VISÃO: RESERVA (Irmãs da Piedade/Diáconos) ---
    else:
        st.title("📝 Reserva de Cestas")
        f_key, p_key = st.session_state.form_key, st.session_state.p_key
        with st.container(border=True):
            st.markdown("#### 👤 Identificação do Solicitante")
            c1, c2, c3 = st.columns([1.5, 1.5, 1.5])
            t_sol = c1.radio("Cargo:", ["Diácono", "Irmã da Piedade"], horizontal=True, key=f"ts_{f_key}")
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
                    if any(x['pront'] == num_p for x in st.session_state.lista_prontuarios): st.error("Já está na lista abaixo.")
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
            if not st.session_state.lista_prontuarios and not is_novo: st.error("Adicione pelo menos um prontuário ou caso novo."); st.stop()
            
            data_agora = datetime.now().strftime('%d/%m/%Y %H:%M')
            try:
                # --- TRAVA DE DUPLICIDADE ---
                for it in st.session_state.lista_prontuarios:
                    check = supabase.table("registros_piedade").select("id").eq("num_prontuario", str(it['pront'])).eq("tratado", False).execute()
                    if check.data:
                        st.error(f"🚨 O Prontuário nº {it['pront']} já possui uma reserva pendente no sistema!")
                        st.stop()

                # --- PROCESSAMENTO ---
                for it in st.session_state.lista_prontuarios:
                    supabase.table("registros_piedade").insert({"tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, "num_prontuario": str(it['pront']), "quantidade_cestas": int(it['qtd']), "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False}).execute()
                
                if is_novo:
                    supabase.table("registros_piedade").insert({"tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, "nome_completo": n_comp, "comum_assistido": c_ast, "quantidade_cestas": int(q_novo), "idade": int(n_id), "tempo_batismo": n_bat, "estado_civil": n_civ, "nome_conjuge": n_conj, "idade_conjuge": int(n_conj_id), "batismo_conjuge": n_conj_bat, "endereco": n_end, "bairro": n_bai, "cep": n_cep, "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False}).execute()
                
                st.balloons(); st.success("✅ ENVIADO COM SUCESSO!"); time.sleep(1); resetar_formulario(); st.rerun()
            except Exception as e: st.error(f"Erro ao salvar: {e}")
