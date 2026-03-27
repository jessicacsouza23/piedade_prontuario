import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
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

def verificar_disponibilidade():
    """Calcula se o sistema de reserva deve estar aberto ou fechado."""
    fuso_br = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso_br).date()
    
    # Encontrar o primeiro sábado do mês atual
    primeiro_dia_mes = hoje.replace(day=1)
    dias_para_sabado = (5 - primeiro_dia_mes.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia_mes + timedelta(days=dias_para_sabado)
    
    # Terça-feira que antecede o primeiro sábado (4 dias antes)
    terca_limite = primeiro_sabado - timedelta(days=4)
    
    # Regra: Fecha após a terça e reabre após o sábado
    if hoje > terca_limite and hoje <= primeiro_sabado:
        return False, terca_limite, primeiro_sabado
    return True, terca_limite, primeiro_sabado

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
        if any(key.startswith(prefix) for prefix in ["f_", "n_", "c_", "ts_", "inv_", "np_", "qp_", "nc_", "ca_", "id_", "ba_", "civ_", "nco_", "ico_", "bco_", "en_", "bai_", "cep_", "qn_", "loc_", "ns_", "cs_"]):
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
    c_user, c_space, c_btn = st.columns([2, 3, 1])
    c_user.markdown(f"**Logado como:** `{st.session_state.cargo}`")
    if c_btn.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    # --- VISÃO: LANÇADOS ---
    if st.session_state.cargo == "Lançados":
        col_tit, col_sync = st.columns([4, 1])
        col_tit.title("📋 Painel de Lançamentos")
        
        if col_sync.button("🔄 Sincronizar", use_container_width=True):
            st.rerun()
            
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            df_all = pd.DataFrame(dados) if dados else pd.DataFrame()
            
            if not df_all.empty:
                # Tratamento de Tipos
                cols_inteiras = ['idade', 'idade_conjuge', 'quantidade_cestas']
                for col in cols_inteiras:
                    if col in df_all.columns:
                        df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).astype(int)

                pendentes_df = df_all[df_all['tratado'] == False].copy()
                
                # Métricas
                st.markdown("##### 📊 Resumo e Logística")
                m1, m2, m3, m4 = st.columns(4)
                m1.markdown(f"<div class='metric-container'><div class='metric-label'>📦 Total Cestas</div><div class='metric-value'>{int(df_all['quantidade_cestas'].sum())}</div></div>", unsafe_allow_html=True)
                m2.markdown(f"<div class='metric-container'><div class='metric-label'>⏳ A Lançar</div><div class='metric-value' style='color: #E11D48;'>{len(pendentes_df)}</div></div>", unsafe_allow_html=True)
                m3.markdown(f"<div class='metric-container'><div class='metric-label'>🏠 Itaquera</div><div class='metric-value'>{int(df_all[df_all['local_retirada'] == 'Itaquera']['quantidade_cestas'].sum())}</div></div>", unsafe_allow_html=True)
                m4.markdown(f"<div class='metric-container'><div class='metric-label'>🌳 Pq. Guarani</div><div class='metric-value'>{int(df_all[df_all['local_retirada'] == 'Pq. Guarani']['quantidade_cestas'].sum())}</div></div>", unsafe_allow_html=True)

                # Exportação
                exp1, exp2 = st.columns(2)
                with exp1:
                    df_p_all = df_all[df_all['nome_completo'].isna() | (df_all['nome_completo'] == "")].copy()
                    if not df_p_all.empty:
                        cols_p = ['data_sistema', 'nome_solicitante', 'tipo_solicitante', 'comum_solicitante','local_retirada', 'num_prontuario', 'quantidade_cestas']
                        df_p_exp = df_p_all[cols_p]
                        csv_p = df_p_exp.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                        st.download_button("📥 EXCEL: PRONTUÁRIOS", csv_p, f"prontuarios_{datetime.now().strftime('%d_%m')}.csv", "text/csv")
                
                with exp2:
                    df_n_all = df_all[df_all['nome_completo'].notna() & (df_all['nome_completo'] != "")].copy()
                    if not df_n_all.empty:
                        cols_n = ['data_sistema', 'nome_solicitante', 'local_retirada', 'nome_completo', 'idade', 'comum_assistido', 'endereco', 'quantidade_cestas']
                        df_n_exp = df_n_all[cols_n]
                        csv_n = df_n_exp.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                        st.download_button("📥 EXCEL: CASOS NOVOS", csv_n, f"novos_{datetime.now().strftime('%d_%m')}.csv", "text/csv")

                st.divider()
                tab_p, tab_n, tab_t = st.tabs(["📋 Prontuários", "🆕 Novos", "✅ Histórico"])

                with tab_p:
                    pronts_pend = pendentes_df[pendentes_df['nome_completo'].isna() | (pendentes_df['nome_completo'] == "")]
                    for _, item in pronts_pend.iterrows():
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"<div class='nome-header'>Prontuário: {item['num_prontuario']}</div>", unsafe_allow_html=True)
                            c1.caption(f"Solicitante: {item['nome_solicitante']} ({item['tipo_solicitante']})")
                            c2.markdown(f"**📦 {int(item['quantidade_cestas'])} Cesta(s)** | 📍 {item['local_retirada']}")
                            if c3.button("Marcar Lançado", key=f"lp_{item['id']}", use_container_width=True):
                                supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute(); st.rerun()

                with tab_n:
                    novos_pend = pendentes_df[pendentes_df['nome_completo'].notna() & (pendentes_df['nome_completo'] != "")]
                    for _, item in novos_pend.iterrows():
                        with st.container(border=True):
                            st.markdown(f"<div class='nome-header'>👤 {item['nome_completo']}</div>", unsafe_allow_html=True)
                            col1, col2, col3 = st.columns(3)
                            col1.markdown(f"<span class='label-info'>Idade</span><br>{int(item['idade'])} anos", unsafe_allow_html=True)
                            col2.markdown(f"<span class='label-info'>Comum</span><br>{item['comum_assistido']}", unsafe_allow_html=True)
                            col3.markdown(f"<span class='label-info'>Pedido</span><br>{int(item['quantidade_cestas'])} un / {item['local_retirada']}", unsafe_allow_html=True)
                            if st.button("Concluir Lançamento", key=f"ln_{item['id']}", type="primary", use_container_width=True):
                                supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute(); st.rerun()

                with tab_t:
                    tratados = df_all[df_all['tratado'] == True]
                    if st.button("🚨 LIMPAR HISTÓRICO"):
                        supabase.table("registros_piedade").delete().eq("tratado", True).execute(); st.rerun()
                    for _, t in tratados.head(20).iterrows():
                        st.text(f"✅ {t['nome_completo'] if pd.notna(t['nome_completo']) and t['nome_completo'] != '' else 'Pront. ' + str(t['num_prontuario'])} - {t['data_sistema']}")
            else:
                st.info("Nenhum registro encontrado.")
        except Exception as e: st.error(f"Erro ao carregar dados: {e}")

    # --- VISÃO: RESERVA ---
    else:
        # VERIFICAÇÃO DE DISPONIBILIDADE
        aberto, terca, sabado = verificar_disponibilidade()
        
        if not aberto:
            st.error("### 🛑 SISTEMA TEMPORARIAMENTE FECHADO")
            st.warning(f"As reservas para o sábado **{sabado.strftime('%d/%m')}** foram encerradas na última terça-feira ({terca.strftime('%d/%m')}).")
            st.info("O sistema reabrirá para o próximo mês no domingo logo após a entrega.")
            st.stop() # Bloqueia o restante da página

        st.title("📝 Reserva de Cestas")
        f_key = st.session_state.form_key
        
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
            num_p = cp1.text_input("Número do Prontuário", key=f"np_{st.session_state.p_key}")
            qtd_p = cp2.number_input("Qtd", min_value=1, step=1, value=1, key=f"qp_{st.session_state.p_key}")
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
            
            fuso_br = pytz.timezone('America/Sao_Paulo')
            data_agora = datetime.now(fuso_br).strftime('%Y-%m-%d %H:%M:%S')
            
            try:
                # Envia prontuários da lista
                for it in st.session_state.lista_prontuarios:
                    check = supabase.table("registros_piedade").select("id").eq("num_prontuario", str(it['pront'])).eq("tratado", False).execute()
                    if check.data: st.error(f"🚨 Prontuário {it['pront']} já pendente!"); st.stop()
                    
                    supabase.table("registros_piedade").insert({
                        "tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, 
                        "num_prontuario": str(it['pront']), "quantidade_cestas": int(it['qtd']), 
                        "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False
                    }).execute()
                
                # Envia caso novo se marcado
                if is_novo:
                    if not n_comp: st.error("Preencha o nome do assistido!"); st.stop()
                    supabase.table("registros_piedade").insert({
                        "tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, 
                        "nome_completo": n_comp, "comum_assistido": c_ast, "quantidade_cestas": int(q_novo), 
                        "idade": int(n_id), "tempo_batismo": n_bat, "estado_civil": n_civ, 
                        "nome_conjuge": n_conj, "idade_conjuge": int(n_conj_id), "batismo_conjuge": n_conj_bat, 
                        "endereco": n_end, "bairro": n_bai, "cep": n_cep, "local_retirada": loc_ret, 
                        "data_sistema": data_agora, "tratado": False
                    }).execute()
                
                st.balloons(); st.success("✅ RESERVA ENVIADA COM SUCESSO!"); time.sleep(1); resetar_formulario(); st.rerun()
            except Exception as e: st.error(f"Erro ao salvar: {e}")
