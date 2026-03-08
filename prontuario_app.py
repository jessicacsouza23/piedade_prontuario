import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd
import time

st.set_page_config(page_title="Sistema Piedade", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 40px; background-color: #eee; border-radius: 5px; padding: 0px 20px; }
    .stTabs [aria-selected="true"] { background-color: #007bff !important; color: white !important; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 5px; background-color: white; }
    .badge-info { background-color: #e1f5fe; color: #01579b; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
    .badge-comum { background-color: #fff3e0; color: #ef6c00; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #ffe0b2; }
    .nome-header { font-size: 1.2rem; font-weight: bold; color: #333; margin-bottom: 0px; }
    .bloqueio-msg { background-color: #fff2f2; border: 1px solid #ff4b4b; padding: 20px; border-radius: 10px; color: #b91c1c; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO DE BLOQUEIO TEMPORAL ---
def is_sistema_bloqueado():
    hoje = datetime.now().date()
    primeiro_dia = hoje.replace(day=1)
    dias_ate_sabado = (5 - primeiro_dia.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia + timedelta(days=dias_ate_sabado)
    terca_bloqueio = primeiro_sabado - timedelta(days=4)
    return hoje == terca_bloqueio

# --- CONEXÃO BANCO ---
def inicializar_conexao():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    return create_client(url, key)

try:
    supabase: Client = inicializar_conexao()
except:
    st.error("Erro de conexão.")
    st.stop()

# --- ESTADO DA SESSÃO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'form_id' not in st.session_state: st.session_state.form_id = 0

def resetar_tela():
    st.session_state.form_id += 1
    for key in list(st.session_state.keys()):
        if key not in ['autenticado', 'cargo', 'form_id']: st.session_state.pop(key)

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Sistema Piedade")
    with st.container(border=True):
        cargo_sel = st.selectbox("Selecione o Acesso:", ["Lançados", "Reserva de Cesta Básica"])
        senha = st.text_input("Senha:", type="password")
        
        if st.button("Entrar", use_container_width=True):
            if cargo_sel == "Reserva de Cesta Básica" and is_sistema_bloqueado():
                st.markdown(f"""
                <div class='bloqueio-msg'>
                    <h3>🚫 SISTEMA BLOQUEADO PARA RESERVAS</h3>
                    <p>O prazo de reservas expirou.</p>
                    <p><b>Caso haja casos atrasados, entre em contato com:</b><br>
                    Irmã Cal: (11) 97393-9407</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                if (cargo_sel == "Lançados" and senha == st.secrets.get("SENHA_DIACONO", "diacono123")) or \
                   (cargo_sel == "Reserva de Cesta Básica" and senha == st.secrets.get("SENHA_IRMAS", "piedade123")):
                    st.session_state.autenticado, st.session_state.cargo = True, cargo_sel
                    st.rerun()
                else: st.error("Senha incorreta.")
else:
    # --- CABEÇALHO ---
    col_tit, col_sair = st.columns([5, 1])
    with col_tit: st.subheader(f"👤 {st.session_state.cargo}")
    with col_sair:
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()

    # --- VISÃO: LANÇADOS ---
    if st.session_state.cargo == "Lançados":
        st.title("📋 Gestão de Pedidos")
        tab_novos, tab_existentes, tab_tratados = st.tabs(["🆕 Novos", "📋 Prontuários", "✅ Tratados"])
        
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            
            def exibir_registro_compacto(item):
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    with c1:
                        nome = item.get('nome_completo') or "Solicitação por Prontuário"
                        st.markdown(f"<div class='nome-header'>{nome}</div>", unsafe_allow_html=True)
                        st.markdown(f"<span class='badge-comum'>⛪ Comum Assistido: {item.get('comum_assistido')}</span>", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"**📦 {item.get('quantidade_cestas')} Cesta(s)**")
                        st.markdown(f"<span class='badge-info'>Pront: {item.get('num_prontuario') or 'NOVO'}</span>", unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"**👤 Solicitante:**\n{item.get('nome_solicitante')}")
                        st.caption(f"Comum: {item.get('comum_solicitante')}")
                    with c4:
                        if st.button("Lançado", key=f"btn_{item['id']}", use_container_width=True):
                            supabase.table("registros_piedade").update({"tratado": True}).eq("id", item['id']).execute()
                            st.rerun()

                    # Detalhes expandidos incluindo o Cônjuge
                    if item.get('nome_completo'):
                        with st.expander("🔍 Ver Detalhes Completos"):
                            d1, d2 = st.columns(2)
                            d1.markdown(f"**Idade:** {item.get('idade')} anos")
                            d1.markdown(f"**Estado Civil:** {item.get('estado_civil')}")
                            d1.markdown(f"**Endereço:** {item.get('endereco')} - CEP: {item.get('cep')}")
                            
                            if item.get('nome_conjuge'):
                                d2.markdown(f"**💍 Cônjuge:** {item.get('nome_conjuge')}")
                                d2.markdown(f"**Idade Cônjuge:** {item.get('idade_conjuge')} anos")
                            d2.markdown(f"**Tempo de Batismo:** {item.get('tempo_batismo') or 'N/A'}")

            with tab_novos:
                for i in [x for x in dados if x.get('nome_completo') and not x.get('tratado')]: exibir_registro_compacto(i)
            with tab_existentes:
                for i in [x for x in dados if not x.get('nome_completo') and not x.get('tratado')]: exibir_registro_compacto(i)
            with tab_tratados:
                for i in [x for x in dados if x.get('tratado')]:
                    st.text(f"✅ {i.get('nome_completo') or 'Prontuário '+i.get('num_prontuario')} - Finalizado")
        except: st.error("Erro ao carregar dados.")

    # --- VISÃO: RESERVA DE CESTA BÁSICA ---
    else:
        st.title("📝 Nova Reserva de Cesta")
        f_id = st.session_state.form_id
        
        with st.container(border=True):
            st.markdown("### 1. Dados de Quem Solicita")
            col_s1, col_s2, col_s3 = st.columns([1, 1.5, 1.5])
            tipo_sol = col_s1.radio("Solicitante:", ["Diácono", "Irmã da Piedade"], horizontal=True, key=f"t_{f_id}")
            nome_sol = col_s2.text_input(f"Nome do(a) {tipo_sol}:", key=f"n_{f_id}")
            comum_sol = col_s3.text_input("Comum do Solicitante:", key=f"com_s_{f_id}")
            
            st.divider()
            
            st.markdown("### 2. Dados do Assistido")
            col_p1, col_p2, col_p3 = st.columns([1.5, 1.5, 1])
            n_pront = col_p1.text_input("Número do Prontuário:", key=f"p_{f_id}")
            comum_ast = col_p2.text_input("Comum do Assistido:", key=f"com_a_{f_id}")
            q_cestas = col_p3.number_input("Quantidade de Cestas:", min_value=1, value=1, key=f"q_{f_id}")
            
            loc = st.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True, key=f"l_{f_id}")
            
            st.divider()
            is_novo = st.toggle("É UM CADASTRO NOVO?", key=f"v_{f_id}")

            n_comp, n_id, n_bat, n_civ, n_conj, n_conj_id, n_end, n_cep = "", 0, "", "Solteiro(a)", "", 0, "", ""

            if is_novo:
                n_comp = st.text_input("Nome Completo do Assistido:", key=f"nc_{f_id}")
                d1, d2, d3 = st.columns(3)
                n_id = d1.number_input("Idade:", min_value=0, key=f"id_{f_id}")
                n_bat = d2.text_input("Tempo de Batismo:", key=f"tb_{f_id}")
                n_civ = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"], key=f"ec_{f_id}")
                
                # Campos de Cônjuge aparecem se for Casado(a)
                if n_civ == "Casado(a)":
                    with st.container(border=True):
                        c_col1, c_col2 = st.columns([3, 1])
                        n_conj = c_col1.text_input("Nome do Cônjuge:", key=f"nj_{f_id}")
                        n_conj_id = c_col2.number_input("Idade Cônjuge:", min_value=0, key=f"ij_{f_id}")
                
                n_end = st.text_input("Endereço Completo:", key=f"en_{f_id}")
                n_cep = st.text_input("CEP:", key=f"ce_{f_id}")

            if st.button("💾 CONFIRMAR RESERVA", type="primary", use_container_width=True):
                if not nome_sol or not comum_sol or not comum_ast: 
                    st.error("Preencha todos os campos obrigatórios!"); st.stop()
                if is_novo and not n_comp:
                    st.error("Informe o nome do assistido!"); st.stop()

                payload = {
                    "tipo_solicitante": tipo_sol, "nome_solicitante": nome_sol, "comum_solicitante": comum_sol,
                    "comum_assistido": comum_ast, "num_prontuario": n_pront, "quantidade_cestas": int(q_cestas), 
                    "local_retirada": loc, "nome_completo": n_comp, "idade": int(n_id), "tempo_batismo": n_bat, 
                    "estado_civil": n_civ, "nome_conjuge": n_conj, "idade_conjuge": int(n_conj_id),
                    "endereco": n_end, "cep": n_cep, "data_sistema": datetime.now().strftime('%d/%m/%Y %H:%M'), 
                    "tratado": False
                }
                
                try:
                    supabase.table("registros_piedade").insert(payload).execute()
                    st.success("✅ Reserva realizada com sucesso!")
                    time.sleep(1)
                    resetar_tela()
                    st.rerun()
                except: st.error("Erro ao salvar no banco de dados.")
