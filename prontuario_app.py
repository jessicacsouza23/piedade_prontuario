import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd
import time

st.set_page_config(page_title="Sistema Piedade", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILIZAÇÃO ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .assistido-card { background-color: #f1f8ff; padding: 15px; border-radius: 8px; border-left: 5px solid #007bff; margin-bottom: 10px; }
    .conjuge-card { background-color: #fff9f0; padding: 10px; border-radius: 8px; border-left: 5px solid #ff9800; margin-top: 10px; }
    .badge-local { background-color: #6c757d; color: white; padding: 2px 8px; border-radius: 5px; font-weight: bold; }
    .badge-cargo { background-color: #28a745; color: white; padding: 2px 8px; border-radius: 5px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO ---
def inicializar_conexao():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    if not url or not key:
        st.error("❌ Credenciais não encontradas!")
        st.stop()
    return create_client(url, key)

try:
    supabase: Client = inicializar_conexao()
except Exception as e:
    st.error(f"Erro: {e}")
    st.stop()

# --- ESTADO DA SESSÃO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# Função Robusta para Limpar TUDO
def resetar_formulario():
    for key in list(st.session_state.keys()):
        if key not in ['autenticado', 'cargo']:
            st.session_state.pop(key)

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Acesso ao Sistema Piedade")
    with st.container(border=True):
        cargo_sel = st.selectbox("Entrar como:", ["Diácono", "Irmã da Piedade"])
        senha = st.text_input("Senha:", type="password")
        if st.button("Entrar", use_container_width=True):
            if (cargo_sel == "Diácono" and senha == st.secrets.get("SENHA_DIACONO", "diacono123")) or \
               (cargo_sel == "Irmã da Piedade" and senha == st.secrets.get("SENHA_IRMAS", "piedade123")):
                st.session_state.autenticado, st.session_state.cargo = True, cargo_sel
                st.rerun()
            else: st.error("Senha incorreta.")
else:
    st.sidebar.title(f"Usuário: {st.session_state.cargo}")
    if st.sidebar.button("Sair"):
        resetar_formulario()
        st.session_state.autenticado = False
        st.rerun()

    # --- VISÃO DO DIÁCONO ---
    if st.session_state.cargo == "Diácono":
        st.title("📋 Painel de Conferência")
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            if dados:
                df = pd.DataFrame(dados)
                st.download_button("📥 Exportar Excel", df.to_csv(index=False).encode('utf-8-sig'), "relatorio.csv", "text/csv")
                
                for item in dados:
                    with st.container(border=True):
                        h_col, a_col = st.columns([4, 1.5])
                        with h_col:
                            nome_exibir = item.get('nome_completo') if item.get('nome_completo') else "Prontuário Existente"
                            st.markdown(f"## {nome_exibir}")
                            st.markdown(f"**Nº Prontuário:** `{item.get('num_prontuario') or 'NOVO'}` | **Data:** {item.get('data_sistema')}")
                        
                        with a_col:
                            status_db = item.get('tratado', False)
                            novo_st = st.radio(f"Situação (Ref:{item['id'][:4]})", ["Pendente", "Tratado"], 
                                             index=1 if status_db else 0, key=f"r_{item['id']}")
                            if (novo_st == "Tratado") != status_db:
                                supabase.table("registros_piedade").update({"tratado": novo_st == "Tratado"}).eq("id", item['id']).execute()
                                st.toast("Status atualizado!")

                        st.divider()
                        q1, q2, q3 = st.columns(3)
                        with q1:
                            st.markdown(f"**Solicitante:** <br><span class='badge-cargo'>{item.get('tipo_solicitante')}</span> {item.get('nome_solicitante')}", unsafe_allow_html=True)
                        with q2:
                            st.markdown(f"**Quantidade:** <br>📦 {item.get('quantidade_cestas')} Cesta(s)", unsafe_allow_html=True)
                        with q3:
                            st.markdown(f"**Retirada em:** <br><span class='badge-local'>{item.get('local_retirada')}</span>", unsafe_allow_html=True)

                        if item.get('nome_completo'):
                            st.markdown("<br>**Dados do Assistido:**", unsafe_allow_html=True)
                            st.markdown(f"""
                                <div class='assistido-card'>
                                    <b>Idade:</b> {item.get('idade')} anos | <b>Estado Civil:</b> {item.get('estado_civil')} | <b>Batismo:</b> {item.get('tempo_batismo') or 'N/A'}<br>
                                    <b>Endereço:</b> {item.get('endereco')}, {item.get('bairro')} - CEP: {item.get('cep')}
                                </div>
                                """, unsafe_allow_html=True)
                            
                            if item.get('nome_conjuge'):
                                st.markdown(f"""
                                <div class='conjuge-card'>
                                    <b>💍 Cônjuge:</b> {item.get('nome_conjuge')}<br>
                                    <b>Idade:</b> {item.get('idade_conjuge')} anos | <b>Batismo Cônjuge:</b> {item.get('tempo_batismo_conjuge') or 'N/A'}
                                </div>
                                """, unsafe_allow_html=True)
            else: st.info("Sem registros.")
        except Exception as e: st.error(f"Erro: {e}")

    # --- VISÃO DA IRMÃ ---
    else:
        st.title("📝 Cadastro de Solicitações")
        # O formulário agora é envolto por um container que respeita o reset
        with st.container(border=True):
            tipo_sol = st.radio("Quem solicita?", ["Diácono", "Irmã da Piedade"], horizontal=True, key="tipo_s")
            nome_sol = st.text_input(f"Nome do(a) {tipo_sol}:", key="nome_s")
            
            cp1, cp2 = st.columns([2, 1])
            n_prontuario = cp1.text_input("Número do Prontuário:", key="pront_n")
            q_cestas = cp2.number_input("Cestas:", min_value=1, step=1, key="cestas_q")
            
            loc_retirada = st.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True, key="loc_r")
            st.divider()
            is_novo = st.toggle("🆕 CADASTRAR COMO PRONTUÁRIO NOVO", key="toggle_n")

            # Inicialização de variáveis para o payload
            n_comp, n_id, n_bat, n_civ, n_conj, n_conj_id, n_conj_bat, n_end, n_bai, n_cep = "", 0, "", "Solteiro(a)", "", 0, "", "", "", ""

            if is_novo:
                n_comp = st.text_input("Nome Completo:", key="comp_n")
                d1, d2, d3 = st.columns(3)
                n_id = d1.number_input("Idade:", min_value=0, key="id_n")
                n_bat = d2.text_input("Tempo de Batismo:", key="bat_n")
                n_civ = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"], key="civ_n")
                
                if n_civ == "Casado(a)":
                    with st.container(border=True):
                        st.write("💍 **Dados do Cônjuge**")
                        n_conj = st.text_input("Nome do Cônjuge:", key="conj_n")
                        cc1, cc2 = st.columns(2)
                        n_conj_id = cc1.number_input("Idade Cônjuge:", min_value=0, key="conj_id_n")
                        n_conj_bat = cc2.text_input("Tempo de Batismo Cônjuge:", key="conj_bat_n")
                
                n_end = st.text_input("Rua e Número:", key="end_n")
                b1, b2 = st.columns(2)
                n_bai = b1.text_input("Bairro:", key="bai_n")
                n_cep = b2.text_input("CEP:", key="cep_n")

            if st.button("💾 FINALIZAR E ENVIAR", type="primary", use_container_width=True):
                # Validações Básicas
                if not nome_sol: 
                    st.error("Informe o Nome do Solicitante!"); st.stop()
                if not is_novo and not n_prontuario: 
                    st.error("Número do Prontuário é obrigatório!"); st.stop()

                payload = {
                    "tipo_solicitante": tipo_sol, "nome_solicitante": nome_sol, "num_prontuario": n_prontuario,
                    "quantidade_cestas": int(q_cestas), "local_retirada": loc_retirada, "nome_completo": n_comp,
                    "idade": int(n_id), "tempo_batismo": n_bat, "estado_civil": n_civ, "nome_conjuge": n_conj,
                    "idade_conjuge": int(n_conj_id), "tempo_batismo_conjuge": n_conj_bat, "endereco": n_end,
                    "bairro": n_bai, "cep": n_cep, "data_sistema": datetime.now().strftime('%d/%m/%Y %H:%M'), "tratado": False
                }
                
                try:
                    supabase.table("registros_piedade").insert(payload).execute()
                    st.balloons()
                    st.success("Dados salvos")
                    time.sleep(1.5)
                    resetar_formulario() # Limpa TUDO no estado da sessão
                    st.rerun() # Recarrega a página do zero
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
