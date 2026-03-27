import streamlit as st
from supabase import create_client, Client
import datetime  # Importado como módulo para evitar erro de conflito
import pandas as pd
import numpy as np
import time
import pytz

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Sistema Piedade", layout="wide")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .metric-container { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e1e4e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; margin-bottom: 10px; }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #1E3A8A; }
    .metric-label { font-size: 0.7rem; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px; }
    .nome-header { font-size: 1.1rem; font-weight: 800; color: #1E3A8A; border-left: 5px solid #1E3A8A; padding-left: 10px; }
    .section-divider { border-top: 1px solid #e5e7eb; margin: 12px 0 8px 0; padding-top: 5px; font-weight: bold; color: #4B5563; font-size: 0.85rem; }
    .stDownloadButton button { width: 100% !important; border-radius: 8px !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES CORE E TRAVA DE DATA ---
def inicializar_conexao():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def verificar_sistema_aberto():
    """Lógica: Fecha na quarta (após a terça limite) e reabre no domingo do primeiro sábado."""
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.datetime.now(fuso).date()
    
    # Encontrar o primeiro sábado do mês atual
    primeiro_dia = hoje.replace(day=1)
    # weekday: 0=Seg, 5=Sáb, 6=Dom
    dias_para_sabado = (5 - primeiro_dia.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia + datetime.timedelta(days=dias_para_sabado)
    
    # Terça-feira que antecede esse sábado
    terca_limite = primeiro_sabado - datetime.timedelta(days=4)
    
    # BLOQUEIO: Se for depois da terça E antes do domingo (dia após o sábado)
    # O sistema reabre no domingo (primeiro_sabado + 1 dia)
    if hoje > terca_limite and hoje <= primeiro_sabado:
        return False, terca_limite, primeiro_sabado
    return True, terca_limite, primeiro_sabado

try:
    supabase: Client = inicializar_conexao()
except:
    st.error("Erro de conexão com o banco de dados.")
    st.stop()

# --- ESTADOS DA SESSÃO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'lista_prontuarios' not in st.session_state: st.session_state.lista_prontuarios = []
if 'form_key' not in st.session_state: st.session_state.form_key = 0
if 'p_key' not in st.session_state: st.session_state.p_key = 0 

def resetar_formulario():
    st.session_state.form_key += 1
    st.session_state.p_key += 1
    st.session_state.lista_prontuarios = []
    for key in list(st.session_state.keys()):
        if any(key.startswith(pre) for pre in ["f_", "n_", "c_", "ts_", "inv_", "np_", "qp_", "ns_", "cs_", "loc_"]):
            st.session_state.pop(key)

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("Sistema Piedade - Reservas de Cesta Básica")
    with st.container(border=True):
        cargo_sel = st.selectbox("Acesso:", ["Reserva de Cesta Básica", "Lançados"])
        senha = st.text_input("Senha:", type="password")
        if st.button("Entrar", use_container_width=True):
            if (cargo_sel == "Lançados" and senha == st.secrets.get("SENHA_DIACONO", "diacono@26")) or \
               (cargo_sel == "Reserva de Cesta Básica" and senha == st.secrets.get("SENHA_IRMAS", "piedade123")):
                st.session_state.autenticado, st.session_state.cargo = True, cargo_sel
                st.rerun()
            else: st.error("Senha incorreta.")
else:
    # Header
    c_user, c_space, c_btn = st.columns([2, 3, 1])
    c_user.markdown(f"**Logado como:** `{st.session_state.cargo}`")
    if c_btn.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    # --- VISÃO: LANÇADOS (DIÁCONOS) ---
    if st.session_state.cargo == "Lançados":
        col_tit, col_sync = st.columns([4, 1])
        col_tit.title("📋 Painel de Controle")
        if col_sync.button("🔄 Sincronizar"): st.rerun()
            
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            df_all = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            
            if not df_all.empty:
                # Tratamento de dados
                df_all['quantidade_cestas'] = pd.to_numeric(df_all['quantidade_cestas'], errors='coerce').fillna(0).astype(int)
                df_p = df_all[df_all['nome_completo'].isna() | (df_all['nome_completo'] == "")]
                df_n = df_all[df_all['nome_completo'].notna() & (df_all['nome_completo'] != "")]
                df_pend = df_all[df_all['tratado'] == False]

                # --- MÉTRICAS ---
                st.markdown("##### 📊 Resumo Geral")
                r1, r2, r3, r4 = st.columns(4)
                r1.markdown(f"<div class='metric-container'><div class='metric-label'>📝 Total Geral</div><div class='metric-value'>{len(df_all)}</div></div>", unsafe_allow_html=True)
                r2.markdown(f"<div class='metric-container'><div class='metric-label'>📋 Prontuários</div><div class='metric-value'>{len(df_p)}</div></div>", unsafe_allow_html=True)
                r3.markdown(f"<div class='metric-container'><div class='metric-label'>🆕 Novos</div><div class='metric-value'>{len(df_n)}</div></div>", unsafe_allow_html=True)
                r4.markdown(f"<div class='metric-container'><div class='metric-label'>⏳ A Lançar</div><div class='metric-value' style='color: #E11D48;'>{len(df_pend)}</div></div>", unsafe_allow_html=True)

                st.markdown("##### 📍 Cestas por Local")
                l1, l2, l3 = st.columns(3)
                l1.markdown(f"<div class='metric-container'><div class='metric-label'>📦 Total Cestas</div><div class='metric-value'>{int(df_all['quantidade_cestas'].sum())}</div></div>", unsafe_allow_html=True)
                l2.markdown(f"<div class='metric-container'><div class='metric-label'>🏠 Itaquera</div><div class='metric-value'>{int(df_all[df_all['local_retirada'] == 'Itaquera']['quantidade_cestas'].sum())}</div></div>", unsafe_allow_html=True)
                l3.markdown(f"<div class='metric-container'><div class='metric-label'>🌳 Pq. Guarani</div><div class='metric-value'>{int(df_all[df_all['local_retirada'] == 'Pq. Guarani']['quantidade_cestas'].sum())}</div></div>", unsafe_allow_html=True)

                # --- EXCEL ---
                st.markdown("##### 📥 Baixar Relatórios")
                e1, e2 = st.columns(2)
                with e1:
                    if not df_p.empty:
                        csv_p = df_p.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                        st.download_button("📥 EXCEL: TODOS PRONTUÁRIOS", csv_p, "relatorio_prontuarios.csv", "text/csv")
                with e2:
                    if not df_n.empty:
                        csv_n = df_n.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                        st.download_button("📥 EXCEL: TODOS NOVOS", csv_n, "relatorio_novos.csv", "text/csv")

                st.divider()
                tab_p, tab_n, tab_h = st.tabs(["📋 Prontuários Pendentes", "🆕 Novos Pendentes", "✅ Histórico"])
                
                with tab_p:
                    for _, row in df_pend[df_pend['nome_completo'].isna() | (df_pend['nome_completo'] == "")].iterrows():
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"<div class='nome-header'>Prontuário: {row['num_prontuario']}</div>", unsafe_allow_html=True)
                            c1.caption(f"Solicitante: {row['nome_solicitante']}")
                            c2.write(f"**{row['quantidade_cestas']} un** | {row['local_retirada']}")
                            if c3.button("Lançar", key=f"p_{row['id']}"):
                                supabase.table("registros_piedade").update({"tratado": True}).eq("id", row['id']).execute(); st.rerun()

                with tab_n:
                    for _, row in df_pend[df_pend['nome_completo'].notna() & (df_pend['nome_completo'] != "")].iterrows():
                        with st.container(border=True):
                            st.markdown(f"<div class='nome-header'>👤 {row['nome_completo']}</div>", unsafe_allow_html=True)
                            st.write(f"Comum: {row['comum_assistido']} | Qtd: {row['quantidade_cestas']} | Local: {row['local_retirada']}")
                            if st.button("Lançar Novo", key=f"n_{row['id']}", type="primary"):
                                supabase.table("registros_piedade").update({"tratado": True}).eq("id", row['id']).execute(); st.rerun()

            else: st.info("Banco de dados vazio.")
        except Exception as e: st.error(f"Erro: {e}")

    # --- VISÃO: RESERVA (IRMÃS) ---
    else:
        # APLICAÇÃO DA TRAVA
        aberto, terca, sabado = verificar_sistema_aberto()
        if not aberto:
            st.error("### 🛑 SISTEMA TEMPORARIAMENTE FECHADO")
            st.info(f"As reservas para o sábado {sabado.strftime('%d/%m')} se encerraram na terça-feira ({terca.strftime('%d/%m')}). O sistema reabrirá no domingo.")
            st.stop()

        st.title("📝 Nova Reserva")
        f_key = st.session_state.form_key
        
        with st.container(border=True):
            st.markdown("#### 👤 Solicitante")
            c1, c2, c3 = st.columns(3)
            t_sol = c1.radio("Cargo:", ["Diácono", "Irmã da Piedade"], horizontal=True, key=f"ts_{f_key}")
            n_sol = c2.text_input("Nome:", key=f"ns_{f_key}")
            c_sol = c3.text_input("Comum:", key=f"cs_{f_key}")

        st.divider()
        st.markdown("#### 📋 Prontuários")
        with st.expander("Adicionar Prontuário", expanded=True):
            cp1, cp2, cp3 = st.columns([2, 1, 1])
            num_p = cp1.text_input("Número", key=f"np_{st.session_state.p_key}")
            qtd_p = cp2.number_input("Qtd", min_value=1, value=1, key=f"qp_{st.session_state.p_key}")
            if cp3.button("➕ Adicionar"):
                if num_p:
                    st.session_state.lista_prontuarios.append({"id": time.time(), "pront": num_p, "qtd": int(qtd_p)})
                    st.session_state.p_key += 1; st.rerun()

        for i, p in enumerate(st.session_state.lista_prontuarios):
            ci, cd = st.columns([9, 1])
            ci.info(f"Nº {p['pront']} — {p['qtd']} cesta(s)")
            if cd.button("🗑️", key=f"del_{p['id']}"): st.session_state.lista_prontuarios.pop(i); st.rerun()

        st.divider()
        is_novo = st.toggle("Pessoa sem prontuário?", key=f"inv_{f_key}")
        if is_novo:
            with st.container(border=True):
                n_comp = st.text_input("Nome Assistido:", key=f"nc_{f_key}")
                c_ast = st.text_input("Comum Assistido:", key=f"ca_{f_key}")
                q_novo = st.number_input("Qtd Cestas:", min_value=1, value=1, key=f"qn_{f_key}")

        loc_ret = st.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True, key=f"loc_{f_key}")

        if st.button("💾 ENVIAR RESERVA", type="primary", use_container_width=True):
            if not n_sol or not c_sol: st.error("Preencha seu nome e comum!"); st.stop()
            agora = datetime.datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')
            try:
                for it in st.session_state.lista_prontuarios:
                    supabase.table("registros_piedade").insert({
                        "tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol,
                        "num_prontuario": str(it['pront']), "quantidade_cestas": int(it['qtd']),
                        "local_retirada": loc_ret, "data_sistema": agora, "tratado": False
                    }).execute()
                if is_novo:
                    supabase.table("registros_piedade").insert({
                        "tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol,
                        "nome_completo": n_comp, "comum_assistido": c_ast, "quantidade_cestas": int(q_novo),
                        "local_retirada": loc_ret, "data_sistema": agora, "tratado": False
                    }).execute()
                st.balloons(); st.success("✅ ENVIADO!"); resetar_formulario(); time.sleep(1); st.rerun()
            except Exception as e: st.error(f"Erro: {e}")
