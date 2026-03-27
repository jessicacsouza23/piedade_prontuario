import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
import pytz

# --- FUNÇÃO DE CONTROLE DE DATAS (PIEDADE) ---
def verificar_bloqueio_piedade():
    """
    Bloqueia na terça-feira que antecede o primeiro sábado do mês.
    Libera no domingo.
    """
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).date()
    
    # Encontrar o primeiro sábado do mês atual
    primeiro_dia_mes = hoje.replace(day=1)
    dias_para_sabado = (5 - primeiro_dia_mes.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia_mes + timedelta(days=dias_para_sabado)
    
    # Terça que antecede esse sábado
    terca_bloqueio = primeiro_sabado - timedelta(days=4)
    
    # Se hoje estiver entre a terça e o sábado (inclusive), bloqueia
    # Se for domingo (dia 6 da semana), libera.
    if terca_bloqueio <= hoje <= primeiro_sabado:
        return True, terca_bloqueio, primeiro_sabado
    return False, None, None

st.set_page_config(page_title="Sistema Piedade", layout="wide")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .metric-container { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e1e4e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; margin-bottom: 10px; }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #1E3A8A; }
    .metric-label { font-size: 0.7rem; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px; }
    .nome-header { font-size: 1.1rem; font-weight: 800; color: #1E3A8A; border-left: 5px solid #1E3A8A; padding-left: 10px; }
    .section-divider { border-top: 1px solid #e5e7eb; margin: 12px 0 8px 0; padding-top: 5px; font-weight: bold; color: #4B5563; font-size: 0.85rem; }
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

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("Sistema Piedade - Reservas")
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
    # --- CABEÇALHO ---
    c_user, c_btn = st.columns([5, 1])
    c_user.markdown(f"**Logado como:** `{st.session_state.cargo}`")
    if c_btn.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    # --- VISÃO: LANÇADOS (DIÁCONOS) ---
    if st.session_state.cargo == "Lançados":
        st.title("📋 Relatório de Reservas")
        
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            df_all = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            
            if not df_all.empty:
                # TRATAMENTO DE HORÁRIO E STATUS PARA O RELATÓRIO
                df_all['data_dt'] = pd.to_datetime(df_all['data_sistema'])
                df_all['Data'] = df_all['data_dt'].dt.strftime('%d/%m/%Y')
                df_all['Horário'] = df_all['data_dt'].dt.strftime('%H:%M:%S')
                df_all['Status_Desc'] = df_all['tratado'].map({True: "✅ Lançado", False: "⏳ Pendente"})

                # MÉTRICAS RÁPIDAS
                m1, m2, m3 = st.columns(3)
                m1.metric("Total de Pedidos", len(df_all))
                m2.metric("Pendentes", len(df_all[df_all['tratado'] == False]))
                m3.metric("Cestas Totais", int(df_all['quantidade_cestas'].sum()))

                st.divider()
                
                # TABELA DE RELATÓRIO COMPLETA
                st.subheader("Histórico Completo")
                cols_view = ["Data", "Horário", "Status_Desc", "nome_solicitante", "num_prontuario", "nome_completo", "quantidade_cestas", "local_retirada"]
                st.dataframe(df_all[cols_view].rename(columns={
                    "nome_solicitante": "Solicitante",
                    "num_prontuario": "Prontuário",
                    "nome_completo": "Nome (Caso Novo)",
                    "quantidade_cestas": "Qtd",
                    "local_retirada": "Local",
                    "Status_Desc": "Status"
                }), use_container_width=True, hide_index=True)

                # TAB VIEW PARA AÇÃO
                tab_p, tab_n = st.tabs(["📋 Prontuários Pendentes", "🆕 Novos Pendentes"])
                
                with tab_p:
                    pendentes = df_all[(df_all['tratado'] == False) & (df_all['nome_completo'].isna() | (df_all['nome_completo'] == ""))]
                    for _, item in pendentes.iterrows():
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"**Prontuário: {item['num_prontuario']}**")
                            c1.caption(f"Solicitado em: {item['Data']} às {item['Horário']}")
                            c2.write(f"📍 {item['local_retirada']} | 📦 {int(item['quantidade_cestas'])} un")
                            if c3.button("Confirmar Lançamento", key=f"p_{item['id']}"):
                                supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute()
                                st.rerun()

                with tab_n:
                    novos = df_all[(df_all['tratado'] == False) & (df_all['nome_completo'].notna() & (df_all['nome_completo'] != ""))]
                    for _, item in novos.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**👤 {item['nome_completo']}**")
                            st.write(f"Endereço: {item['endereco']}, {item['bairro']} | 📦 {int(item['quantidade_cestas'])} un")
                            if st.button("Confirmar Lançamento", key=f"n_{item['id']}", type="primary"):
                                supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute()
                                st.rerun()
            else:
                st.info("Nenhum registro encontrado.")
        except Exception as e: st.error(f"Erro ao carregar: {e}")

    # --- VISÃO: RESERVA (IRMÃS) ---
    else:
        st.title("📝 Reserva de Cestas")
        
        # VERIFICAÇÃO DE BLOQUEIO
        bloqueado, inicio, fim = verificar_bloqueio_piedade()
        
        if bloqueado:
            st.error(f"⚠️ SISTEMA EM MANUTENÇÃO / BLOQUEIO")
            st.warning(f"As reservas estão suspensas de {inicio.strftime('%d/%m')} até sábado {fim.strftime('%d/%m')}. O sistema será liberado no Domingo.")
            st.stop()

        f_key = st.session_state.form_key
        with st.container(border=True):
            st.markdown("#### 👤 Solicitante")
            c1, c2, c3 = st.columns(3)
            t_sol = c1.radio("Cargo:", ["Diácono", "Irmã da Piedade"], horizontal=True, key=f"ts_{f_key}")
            n_sol = c2.text_input("Nome:", key=f"ns_{f_key}")
            c_sol = c3.text_input("Comum:", key=f"cs_{f_key}")

        st.divider()
        st.markdown("#### 📋 Adicionar Prontuários")
        with st.expander("Clique para inserir número do prontuário", expanded=True):
            cp1, cp2, cp3 = st.columns([2, 1, 1])
            num_p = cp1.text_input("Nº Prontuário", key=f"np_{st.session_state.p_key}")
            qtd_p = cp2.number_input("Qtd", min_value=1, value=1)
            if cp3.button("➕ Adicionar"):
                if num_p:
                    st.session_state.lista_prontuarios.append({"id": time.time(), "pront": num_p, "qtd": int(qtd_p)})
                    st.session_state.p_key += 1
                    st.rerun()

        for i, p in enumerate(st.session_state.lista_prontuarios):
            col_i, col_d = st.columns([9, 1])
            col_i.info(f"Prontuário: {p['pront']} — {p['qtd']} cesta(s)")
            if col_d.button("🗑️", key=f"del_{p['id']}"):
                st.session_state.lista_prontuarios.pop(i)
                st.rerun()

        st.divider()
        st.markdown("#### 🆕 Caso Novo (Sem Prontuário)")
        is_novo = st.toggle("É um cadastro novo?")
        if is_novo:
            with st.container(border=True):
                n_comp = st.text_input("Nome Completo *:")
                c1, c2, c3 = st.columns(3)
                n_id = c1.number_input("Idade:", min_value=0)
                n_bat = c2.text_input("Tempo de Batismo:")
                n_civ = c3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Outros"])
                n_end = st.text_input("Endereço:")
                q_novo = st.number_input("Qtd de Cestas:", min_value=1, value=1)

        loc_ret = st.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True)

        if st.button("💾 ENVIAR RESERVA AGORA", type="primary", use_container_width=True):
            if not n_sol or not c_sol:
                st.error("Preencha seu nome e comum antes de enviar.")
                st.stop()
            
            fuso_br = pytz.timezone('America/Sao_Paulo')
            data_agora = datetime.now(fuso_br).strftime('%Y-%m-%d %H:%M:%S')
            
            try:
                # Enviar Prontuários
                for it in st.session_state.lista_prontuarios:
                    supabase.table("registros_piedade").insert({
                        "tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol,
                        "num_prontuario": str(it['pront']), "quantidade_cestas": it['qtd'],
                        "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False
                    }).execute()
                
                # Enviar Caso Novo
                if is_novo:
                    supabase.table("registros_piedade").insert({
                        "tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol,
                        "nome_completo": n_comp, "quantidade_cestas": int(q_novo), "idade": int(n_id),
                        "tempo_batismo": n_bat, "estado_civil": n_civ, "endereco": n_end,
                        "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False
                    }).execute()
                
                st.balloons()
                st.success("✅ RESERVA ENVIADA COM SUCESSO!")
                time.sleep(1)
                resetar_formulario()
                st.rerun()
            except Exception as e: st.error(f"Erro ao salvar: {e}")
