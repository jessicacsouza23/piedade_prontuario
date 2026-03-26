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
        col_tit.title("📋 Reserva de Cesta Básica")
        if col_sync.button("🔄 Sincronizar", use_container_width=True):
            st.toast("Buscando novos registros...")
            time.sleep(0.5)
            st.rerun()
            
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            df_all = pd.DataFrame(dados) if dados else pd.DataFrame()
            
            if not df_all.empty:
                pendentes_df = df_all[df_all['tratado'] == False].copy()
                
                # --- TRATAMENTO DE TIPOS PARA EVITAR "300" NO LUGAR DE "30" ---
                cols_inteiras = ['idade', 'idade_conjuge', 'quantidade_cestas']
                for col in cols_inteiras:
                    if col in pendentes_df.columns:
                        pendentes_df[col] = pd.to_numeric(pendentes_df[col], errors='coerce').fillna(0).astype(int)

                pronts_pend_df = pendentes_df[pendentes_df['nome_completo'].isna() | (pendentes_df['nome_completo'] == "")].copy()
                novos_pend_df = pendentes_df[pendentes_df['nome_completo'].notna() & (pendentes_df['nome_completo'] != "")].copy()

                   try:
                        res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
                        dados = res.data
                        df_all = pd.DataFrame(dados) if dados else pd.DataFrame()
                
                        if not df_all.empty:
                            # 1. Filtramos o que é pendente para a listagem e para o cálculo do que "falta"
                            pendentes_df = df_all[df_all['tratado'] == False].copy()
                            
                            # 2. Cálculos para as Métricas Fixas (Total Geral do Dia/Banco)
                            total_geral_casos = len(df_all)
                            total_geral_cestas = int(df_all['quantidade_cestas'].sum())
                            
                            # 3. Cálculos para o que Falta Lançar (Pendentes)
                            falta_lancar_casos = len(pendentes_df)
                            falta_lancar_cestas = int(pendentes_df['quantidade_cestas'].sum())
            
                            # Separação interna para as abas
                            pronts_pend_df = pendentes_df[pendentes_df['nome_completo'].isna() | (pendentes_df['nome_completo'] == "")].copy()
                            novos_pend_df = pendentes_df[pendentes_df['nome_completo'].notna() & (pendentes_df['nome_completo'] != "")].copy()
            
                            # --- MÉTRICAS ---
                            st.markdown("##### 📊 Resumo Geral (Saldo do Dia)")
                            
                            # Primeira Linha: Totais Fixos e O que falta
                            c1, c2, c3 = st.columns(3)
                            c1.markdown(f"<div class='metric-container'><div class='metric-label'>📝 Total Geral Pedidos</div><div class='metric-value'>{total_geral_casos}</div></div>", unsafe_allow_html=True)
                            c2.markdown(f"<div class='metric-container'><div class='metric-label'>⏳ Casos a Lançar</div><div class='metric-value' style='color: #E11D48;'>{falta_lancar_casos}</div></div>", unsafe_allow_html=True)
                            c3.markdown(f"<div class='metric-container'><div class='metric-label'>📦 Cestas a Lançar</div><div class='metric-value' style='color: #E11D48;'>{falta_lancar_cestas}</div></div>", unsafe_allow_html=True)
            
                            # Segunda Linha: Distribuição por Local (Baseado no Total Geral para conferência logística)
                            st.markdown("##### 📍 Logística Total (Cestas)")
                            m_total, m_ita, m_gua = st.columns(3)
                            m_total.markdown(f"<div class='metric-container'><div class='metric-label'>📦 Total de Cestas</div><div class='metric-value'>{total_geral_cestas}</div></div>", unsafe_allow_html=True)
                            m_ita.markdown(f"<div class='metric-container'><div class='metric-label'>🏠 Itaquera</div><div class='metric-value'>{int(df_all[df_all['local_retirada'] == 'Itaquera']['quantidade_cestas'].sum())}</div></div>", unsafe_allow_html=True)
                            m_gua.markdown(f"<div class='metric-container'><div class='metric-label'>🌳 Pq. Guarani</div><div class='metric-value'>{int(df_all[df_all['local_retirada'] == 'Pq. Guarani']['quantidade_cestas'].sum())}</div></div>", unsafe_allow_html=True)
            
                            st.write("")
                
                # --- BOTÕES DE EXPORTAÇÃO ---
                exp1, exp2 = st.columns(2)
                with exp1:
                    if not pronts_pend_df.empty:
                        cols_p = ['data_sistema', 'nome_solicitante', 'tipo_solicitante', 'comum_solicitante','local_retirada', 'num_prontuario', 'quantidade_cestas']
                        map_p = {'data_sistema': 'Data', 'nome_solicitante': 'Solicitante', 'tipo_solicitante': 'Cargo', 'comum_solicitante': 'Comum Solicitante', 'local_retirada': 'Local Entrega', 'num_prontuario': 'Nº Prontuário', 'quantidade_cestas': 'Qtd Cestas'}
                        df_p_exp = pronts_pend_df[cols_p].rename(columns=map_p)
                        csv_p = df_p_exp.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                        st.download_button("📥 EXCEL: PRONTUÁRIOS", csv_p, f"prontuarios_{datetime.now().strftime('%d_%m')}.csv", "text/csv", type="primary")
                with exp2:
                    if not novos_pend_df.empty:
                        cols_n = ['data_sistema', 'nome_solicitante', 'tipo_solicitante', 'local_retirada', 'nome_completo', 'idade', 'tempo_batismo', 'estado_civil', 'comum_assistido', 'endereco', 'bairro', 'cep', 'quantidade_cestas', 'nome_conjuge', 'idade_conjuge', 'batismo_conjuge', 'comum_solicitante']
                        map_n = {'data_sistema': 'Data Pedido', 'nome_solicitante': 'Solicitante', 'tipo_solicitante': 'Cargo Solicitante', 'local_retirada': 'Local Entrega', 'nome_completo': 'Nome Assistido', 'idade': 'Idade', 'tempo_batismo': 'Tempo Batismo', 'estado_civil': 'Estado Civil', 'comum_assistido': 'Comum Assistido', 'endereco': 'Endereço', 'bairro': 'Bairro', 'cep': 'CEP', 'quantidade_cestas': 'Qtd Cestas', 'nome_conjuge': 'Nome Cônjuge', 'idade_conjuge': 'Idade Cônjuge', 'batismo_conjuge': 'Batismo Cônjuge', 'comum_solicitante': 'Comum Solicitante'}
                        df_n_exp = novos_pend_df[cols_n].rename(columns=map_n)
                        csv_n = df_n_exp.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                        st.download_button("📥 EXCEL: Prontuários NOVOS", csv_n, f"Prontuários_novos_{datetime.now().strftime('%d_%m')}.csv", "text/csv", type="primary")

                st.divider()
                tab_p, tab_n, tab_t = st.tabs(["📋 Prontuários", "🆕 Novos Prontuários", "✅ Histórico"])

                with tab_p:
                    for _, item in pronts_pend_df.iterrows():
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"<div class='nome-header'>Prontuário: {item['num_prontuario']}</div>", unsafe_allow_html=True)
                            c1.caption(f"📅 {item['data_sistema']} | Solicitante: {item['nome_solicitante']} ({item['tipo_solicitante']})")
                            c2.markdown(f"**📦 {int(item['quantidade_cestas'])} Cesta(s)** | 📍 {item['local_retirada']}")
                            if c3.button("Marcar Lançado", key=f"lp_{item['id']}", use_container_width=True):
                                supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute(); st.rerun()

                with tab_n:
                    for _, item in novos_pend_df.iterrows():
                        with st.container(border=True):
                            st.markdown(f"<div class='nome-header'>👤 {item['nome_completo']}</div>", unsafe_allow_html=True)
                            col1, col2, col3, col4 = st.columns(4)
                            col1.markdown(f"<span class='label-info'>🎂 Idade</span><br><span class='value-info'>{int(item.get('idade', 0))} anos</span>", unsafe_allow_html=True)
                            col2.markdown(f"<span class='label-info'>🌊 Batismo</span><br><span class='value-info'>{item.get('tempo_batismo') or '---'}</span>", unsafe_allow_html=True)
                            col3.markdown(f"<span class='label-info'>💍 Est. Civil</span><br><span class='value-info'>{item.get('estado_civil') or '---'}</span>", unsafe_allow_html=True)
                            col4.markdown(f"<span class='label-info'>⛪ Comum</span><br><span class='value-info'>{item.get('comum_assistido') or '---'}</span>", unsafe_allow_html=True)
                            
                            if item.get('estado_civil') == "Casado(a)":
                                st.markdown("<div class='section-divider'>👩‍❤️‍👨 Dados do Cônjuge</div>", unsafe_allow_html=True)
                                cj1, cj2, cj3 = st.columns([2, 1, 1])
                                cj1.markdown(f"<span class='label-info'>Nome</span><br><span class='value-info'>{item.get('nome_conjuge') or '---'}</span>", unsafe_allow_html=True)
                                cj2.markdown(f"<span class='label-info'>Idade</span><br><span class='value-info'>{int(item.get('idade_conjuge', 0))} anos</span>", unsafe_allow_html=True)
                                cj3.markdown(f"<span class='label-info'>Batismo</span><br><span class='value-info'>{item.get('batismo_conjuge') or '---'}</span>", unsafe_allow_html=True)

                            st.markdown("<div class='section-divider'>📍 Localização e Pedido</div>", unsafe_allow_html=True)
                            end1, end2, end3, end4 = st.columns([2, 1, 1, 1])
                            end1.markdown(f"<span class='label-info'>Endereço</span><br><span class='value-info'>{item.get('endereco') or '---'}</span>", unsafe_allow_html=True)
                            end2.markdown(f"<span class='label-info'>Bairro</span><br><span class='value-info'>{item.get('bairro') or '---'}</span>", unsafe_allow_html=True)
                            end3.markdown(f"<span class='label-info'>CEP</span><br><span class='value-info'>{item.get('cep') or '---'}</span>", unsafe_allow_html=True)
                            end4.markdown(f"<span class='label-info'>📦 Qtd / Retirada</span><br><span class='value-info'>{int(item.get('quantidade_cestas', 0))} un / {item.get('local_retirada')}</span>", unsafe_allow_html=True)

                            st.markdown("<div class='section-divider'>📝 Dados do Cadastro</div>", unsafe_allow_html=True)
                            sol1, sol2, sol3 = st.columns(3)
                            sol1.markdown(f"<span class='label-info'>Solicitante</span><br><span class='value-info'>{item.get('nome_solicitante')}</span>", unsafe_allow_html=True)
                            sol2.markdown(f"<span class='label-info'>Cargo / Comum</span><br><span class='value-info'>{item.get('tipo_solicitante')} - {item.get('comum_solicitante')}</span>", unsafe_allow_html=True)
                            sol3.markdown(f"<span class='label-info'>Data da Reserva</span><br><span class='value-info'>{item.get('data_sistema')}</span>", unsafe_allow_html=True)

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
                st.info("Nenhum pedido pendente.")
        except Exception as e: st.error(f"Erro: {e}")

    # --- VISÃO: RESERVA ---
    else:
        st.title("📝 Reserva de Cestas")
        f_key, p_key = st.session_state.form_key, st.session_state.p_key
        with st.container(border=True):
            st.markdown("#### 👤 Identificação do Solicitante")
            c1, c2, c3 = st.columns([1.5, 1.5, 1.5])
            t_sol = c1.radio("Cargo:", ["Diácono", "Irmã da Piedade"], horizontal=True, key=f"ts_{f_key}")
            n_sol = c2.text_input("Nome do Solicitante:", key=f"ns_{f_key}")
            c_sol = c3.text_input("Comum:", key=f"cs_{f_key}")

        st.divider()
        st.markdown("#### 📋 Prontuários Existentes")
        with st.expander("Adicionar Prontuário", expanded=True):
            cp1, cp2, cp3 = st.columns([2, 1, 1])
            num_p = cp1.text_input("Número do Prontuário", key=f"np_{p_key}")
            qtd_p = cp2.number_input("Qtd", min_value=1, step=1, value=1, key=f"qp_{p_key}")
            if cp3.button("➕ Adicionar"):
                if num_p:
                    if any(x['pront'] == num_p for x in st.session_state.lista_prontuarios): st.error("Já está na lista.")
                    else:
                        st.session_state.lista_prontuarios.append({"id": time.time(), "pront": num_p, "qtd": int(qtd_p)})
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
                n_id = d1.number_input("Idade *:", min_value=0, step=1, key=f"id_{f_key}")
                n_bat = d2.text_input("Tempo de Batismo:", key=f"ba_{f_key}")
                n_civ = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"], key=f"civ_{f_key}")
                n_conj, n_conj_id, n_conj_bat = "", 0, ""
                if n_civ == "Casado(a)":
                    nj1, nj2, nj3 = st.columns([2, 1, 1])
                    n_conj = nj1.text_input("Nome Cônjuge *:", key=f"nco_{f_key}")
                    n_conj_id = nj2.number_input("Idade Cônjuge *:", min_value=0, step=1, key=f"ico_{f_key}")
                    n_conj_bat = nj3.text_input("Batismo Cônjuge:", key=f"bco_{f_key}")
                n_end = st.text_input("Endereço:", key=f"en_{f_key}")
                b1, b2 = st.columns(2)
                n_bai, n_cep = b1.text_input("Bairro:", key=f"bai_{f_key}"), b2.text_input("CEP:", key=f"cep_{f_key}")
                q_novo = st.number_input("Qtd de Cestas:", min_value=1, step=1, key=f"qn_{f_key}")

        loc_ret = st.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True, key=f"loc_{f_key}")

        if st.button("💾 ENVIAR RESERVA", type="primary", use_container_width=True):
            if not n_sol or not c_sol: st.error("Identifique-se!"); st.stop()
            data_agora = datetime.now().strftime('%d/%m/%Y %H:%M')
            try:
                for it in st.session_state.lista_prontuarios:
                    check = supabase.table("registros_piedade").select("id").eq("num_prontuario", str(it['pront'])).eq("tratado", False).execute()
                    if check.data: st.error(f"🚨 Prontuário {it['pront']} já pendente!"); st.stop()
                    supabase.table("registros_piedade").insert({"tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, "num_prontuario": str(it['pront']), "quantidade_cestas": int(it['qtd']), "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False}).execute()
                if is_novo:
                    supabase.table("registros_piedade").insert({"tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, "nome_completo": n_comp, "comum_assistido": c_ast, "quantidade_cestas": int(q_novo), "idade": int(n_id), "tempo_batismo": n_bat, "estado_civil": n_civ, "nome_conjuge": n_conj, "idade_conjuge": int(n_conj_id), "batismo_conjuge": n_conj_bat, "endereco": n_end, "bairro": n_bai, "cep": n_cep, "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False}).execute()
                st.balloons(); st.success("✅ ENVIADO!"); time.sleep(1); resetar_formulario(); st.rerun()
            except Exception as e: st.error(f"Erro: {e}")
