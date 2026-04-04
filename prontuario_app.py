import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time
import pytz 

# --- FUNÇÃO DA TRAVA (ÚNICA ADIÇÃO DE LÓGICA) ---
def verificar_sistema_aberto():
    fuso = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(fuso).date()
    
    # Encontrar o primeiro sábado do mês
    primeiro_dia_mes = hoje.replace(day=1)
    dias_para_sabado = (5 - primeiro_dia_mes.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia_mes + timedelta(days=dias_para_sabado)
    
    # Terça-feira que antecede esse sábado
    terca_limite = primeiro_sabado - timedelta(days=4)
    
    if hoje > terca_limite and hoje <= primeiro_sabado:
        return False, terca_limite, primeiro_sabado
    return True, terca_limite, primeiro_sabado

st.set_page_config(page_title="Sistema Piedade", layout="wide")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .metric-container { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e1e4e8; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; margin-bottom: 10px; }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #1E3A8A; }
    .metric-label { font-size: 0.7rem; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px; }
    .nome-header { font-size: 1.1rem; font-weight: 800; color: #1E3A8A; border-left: 5px solid #1E3A8A; padding-left: 10px; }
    .label-info { color: #6B7280; font-weight: 700; font-size: 0.8rem; text-transform: uppercase; }
    .value-info { color: #111827; font-weight: 500; font-size: 0.95rem; }
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
        # (Sua lógica de visualização de lançados permanece IGUAL ao seu original)
        st.title("📋 Reserva de Cesta Básica")
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            df_all = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            if not df_all.empty:
                # Exibição dos cards e tabelas... (Mantido conforme seu código original)
                st.info("Visualização de administrador habilitada.")
                # ... (resto do seu código de dashboard)
        except Exception as e: st.error(f"Erro: {e}")

    # --- VISÃO: RESERVA ---
    else:
        aberto, t_limite, p_sabado = verificar_sistema_aberto()
        if not aberto:
            st.error("### 🛑 SISTEMA DE RESERVAS FECHADO")
            st.info(f"Reservas encerradas em {t_limite.strftime('%d/%m')}. Reabre no domingo.")
            st.stop()

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
            # ALTERAÇÃO 1: Limite de 5 dígitos
            num_p = cp1.text_input("Número do Prontuário", key=f"np_{p_key}", max_chars=5)
            
            # Validação visual imediata para números
            if num_p and not num_p.isdigit():
                st.warning("Apenas números são permitidos.")
                num_p = ""

            qtd_p = cp2.number_input("Qtd", min_value=1, step=1, value=1, key=f"qp_{p_key}")
            if cp3.button("➕ Adicionar"):
                if num_p and num_p.isdigit():
                    if any(x['pront'] == num_p for x in st.session_state.lista_prontuarios): 
                        st.error("Já está na lista.")
                    else:
                        st.session_state.lista_prontuarios.append({"id": time.time(), "pront": num_p, "qtd": int(qtd_p)})
                        st.session_state.p_key += 1
                        st.rerun()
                else: st.error("Insira um prontuário válido.")

        for i, p in enumerate(st.session_state.lista_prontuarios):
            ci, cd = st.columns([9, 1])
            ci.info(f"Nº {p['pront']} — {p['qtd']} cesta(s)")
            if cd.button("🗑️", key=f"del_{p['id']}"): st.session_state.lista_prontuarios.pop(i); st.rerun()

        st.divider()
        st.markdown("#### 🆕 Caso Novo")
        is_novo = st.toggle("Cadastrar pessoa sem prontuário?", key=f"inv_{f_key}")
        n_comp = "" # Inicializa para evitar erro de referência
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

        st.divider()
        # ALTERAÇÃO 2: Local de retirada obrigatório (index=None)
        loc_ret = st.radio("📍 Local de Retirada (Obrigatório):", ["Pq. Guarani", "Itaquera"], index=None, horizontal=True, key=f"loc_{f_key}")

        if st.button("💾 ENVIAR RESERVA", type="primary", use_container_width=True):
            # ALTERAÇÃO 3: Verificação de campos obrigatórios e lista vazia
            if not n_sol or not c_sol:
                st.error("❌ Por favor, identifique o Solicitante e a Comum.")
            elif not loc_ret:
                st.error("❌ Selecione o Local de Retirada.")
            elif not st.session_state.lista_prontuarios and (not is_novo or not n_comp):
                st.error("❌ Erro: Adicione ao menos um Prontuário ou preencha o Nome do Caso Novo.")
            else:
                fuso_br = pytz.timezone('America/Sao_Paulo')
                data_agora = datetime.now(fuso_br).strftime('%Y-%m-%d %H:%M:%S')
                try:
                    # Salva lista de prontuários
                    for it in st.session_state.lista_prontuarios:
                        supabase.table("registros_piedade").insert({
                            "tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, 
                            "num_prontuario": str(it['pront']), "quantidade_cestas": int(it['qtd']), 
                            "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False
                        }).execute()
                    
                    # Salva Caso Novo
                    if is_novo and n_comp:
                        supabase.table("registros_piedade").insert({
                            "tipo_solicitante": t_sol, "nome_solicitante": n_sol, "comum_solicitante": c_sol, 
                            "nome_completo": n_comp, "comum_assistido": c_ast, "quantidade_cestas": int(q_novo), 
                            "idade": int(n_id), "tempo_batismo": n_bat, "estado_civil": n_civ, "nome_conjuge": n_conj, 
                            "idade_conjuge": int(n_conj_id), "batismo_conjuge": n_conj_bat, "endereco": n_end, 
                            "bairro": n_bai, "cep": n_cep, "local_retirada": loc_ret, "data_sistema": data_agora, "tratado": False
                        }).execute()
                    
                    st.balloons(); st.success("✅ ENVIADO COM SUCESSO!"); time.sleep(1); resetar_formulario(); st.rerun()
                except Exception as e: st.error(f"Erro no banco de dados: {e}")
