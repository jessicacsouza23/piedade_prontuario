import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Sistema Piedade", layout="wide")

# --- CONEXÃO COM O BANCO ---
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

# --- LÓGICA DE BLOQUEIO POR DATA ---
def verificar_bloqueio():
    hoje = datetime.now().date()
    primeiro_dia_mes = hoje.replace(day=1)
    dias_para_sabado = (5 - primeiro_dia_mes.weekday() + 7) % 7
    primeiro_sabado = primeiro_dia_mes + timedelta(days=dias_para_sabado)
    limite_terca = primeiro_sabado - timedelta(days=4)
    if limite_terca < hoje <= primeiro_sabado:
        return False, primeiro_sabado
    return True, None

# --- ESTADO DA SESSÃO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.cargo = ""
if 'novo_prontuario' not in st.session_state:
    st.session_state.novo_prontuario = False

# --- TELA DE LOGIN ---
if not st.session_state.autenticado:
    st.title("⛪ Acesso ao Sistema Piedade")
    cargo_sel = st.selectbox("Entrar como:", ["Diácono", "Irmã da Piedade"])
    senha = st.text_input("Senha:", type="password")
    if st.button("Entrar", use_container_width=True):
        s_diacono = st.secrets.get("SENHA_DIACONO", "diacono123")
        s_irmas = st.secrets.get("SENHA_IRMAS", "piedade123")
        if (cargo_sel == "Diácono" and senha == s_diacono) or (cargo_sel == "Irmã da Piedade" and senha == s_irmas):
            st.session_state.autenticado, st.session_state.cargo = True, cargo_sel
            st.rerun()
        else: st.error("Senha incorreta.")
else:
    st.sidebar.title(f"Usuário: {st.session_state.cargo}")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    # --- VISÃO DO DIÁCONO (FICHA DE LEITURA) ---
    if st.session_state.cargo == "Diácono":
        st.title("📋 Fichas de Prontuários Cadastrados")
        
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            
            if dados:
                # Botão para Excel
                df_excel = pd.DataFrame(dados)
                csv = df_excel.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Gerar Excel (CSV)", csv, "relatorio_piedade.csv", "text/csv")
                
                st.divider()
                
                for item in dados:
                    with st.container(border=True):
                        col_id, col_status = st.columns([3, 1])
                        with col_id:
                            st.subheader(f"📄 Prontuário: {item.get('num_prontuario', 'N/A')}")
                            st.write(f"**Data do Sistema:** {item.get('data_sistema')}")
                        
                        with col_status:
                            status_atual = "Sim" if item.get('tratado') else "Não"
                            novo_status = st.radio(f"Tratado? (ID: {item['id'][:5]})", ["Não", "Sim"], 
                                                 index=0 if status_atual == "Não" else 1, key=f"status_{item['id']}")
                            
                            if (novo_status == "Sim") != item.get('tratado'):
                                supabase.table("registros_piedade").update({"tratado": novo_status == "Sim"}).eq("id", item['id']).execute()
                                st.toast("Status atualizado!")

                        c1, c2, c3 = st.columns(3)
                        c1.write(f"**Solicitante:** {item.get('nome_solicitante')} ({item.get('tipo_solicitante')})")
                        c2.write(f"**Qtd Cestas:** {item.get('quantidade_cestas')}")
                        c3.write(f"**Local Retirada:** {item.get('local_retirada')}")
                        
                        if item.get('nome_completo'):
                            st.info(f"**Dados do Assistido:** {item.get('nome_completo')} | **Idade:** {item.get('idade')} | **Estado Civil:** {item.get('estado_civil')}")
                            st.write(f"**Endereço:** {item.get('endereco')}, {item.get('bairro')} - CEP: {item.get('cep')}")
                            if item.get('nome_conjuge'):
                                st.write(f"**Cônjuge:** {item.get('nome_conjuge')}")
            else:
                st.info("Nenhum registro encontrado.")
        except Exception as e: st.error(f"Erro ao carregar: {e}")

    # --- VISÃO DA IRMÃ DA PIEDADE (CADASTRO) ---
    else:
        liberado, data_lib = verificar_bloqueio()
        st.title("📝 Cadastro de Pedidos")

        if not liberado:
            st.error(f"⚠️ Sistema Bloqueado. Liberação: {data_lib.strftime('%d/%m/%Y')}")
        else:
            with st.form("form_piedade"):
                st.subheader("Informações Obrigatórias")
                tipo_sol = st.radio("Solicitante:", ["Diácono", "Irmã da Piedade"], horizontal=True)
                nome_sol = st.text_input("Nome de quem solicitou (Obrigatório):")
                
                col_a, col_b = st.columns(2)
                n_prontuario = col_a.text_input("Nº do Prontuário (Obrigatório se não for Novo):")
                q_cestas = col_b.number_input("Quantidade de Cestas (Obrigatório):", min_value=1, step=1)
                
                loc_retirada = st.radio("Local de Retirada (Obrigatório):", ["Pq. Guarani", "Itaquera"], horizontal=True)

                st.divider()
                is_novo = st.checkbox("🆕 ESTE É UM CADASTRO NOVO?")
                
                n_completo, n_idade, n_batismo, n_civil, n_conjuge = "", 0, "", "Solteiro(a)", ""
                n_endereco, n_bairro, n_cep = "", "", ""

                if is_novo:
                    st.subheader("📋 Dados do Novo Cadastro")
                    n_completo = st.text_input("Nome Completo (Obrigatório para novo):")
                    d1, d2, d3 = st.columns(3)
                    n_idade = d1.number_input("Idade (Obrigatório para novo):", min_value=0)
                    n_batismo = d2.text_input("Tempo de Batismo (Opcional):")
                    n_civil = d3.selectbox("Estado Civil (Obrigatório):", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"])
                    
                    if n_civil == "Casado(a)":
                        n_conjuge = st.text_input("Nome do Cônjuge (Obrigatório para casados):")
                    
                    st.subheader("Endereço Obrigatório")
                    n_endereco = st.text_input("Rua e Número:")
                    b1, b2 = st.columns(2)
                    n_bairro = b1.text_input("Bairro:")
                    n_cep = b2.text_input("CEP:")

                enviar = st.form_submit_button("💾 SALVAR REGISTRO", type="primary", use_container_width=True)

                if enviar:
                    # VALIDAÇÃO DE CAMPOS OBRIGATÓRIOS
                    erro = False
                    if not nome_sol: st.error("Nome do solicitante é obrigatório."); erro = True
                    if not is_novo and not n_prontuario: st.error("Número do prontuário é obrigatório."); erro = True
                    
                    if is_novo:
                        if not n_completo or not n_idade or not n_endereco or not n_bairro or not n_cep:
                            st.error("Para cadastro novo, preencha Nome, Idade e Endereço completo."); erro = True
                        if n_civil == "Casado(a)" and not n_conjuge:
                            st.error("Nome do cônjuge é obrigatório para casados."); erro = True

                    if not erro:
                        data_pc = datetime.now().strftime('%Y-%m-%d')
                        payload = {
                            "tipo_solicitante": tipo_sol, "nome_solicitante": nome_sol,
                            "num_prontuario": n_prontuario, "quantidade_cestas": int(q_cestas),
                            "local_retirada": loc_retirada, "nome_completo": n_completo,
                            "idade": int(n_idade), "tempo_batismo": n_batismo,
                            "estado_civil": n_civil, "nome_conjuge": n_conjuge,
                            "endereco": n_endereco, "bairro": n_bairro, "cep": n_cep,
                            "data_sistema": data_pc, "tratado": False
                        }
                        supabase.table("registros_piedade").insert(payload).execute()
                        st.success("✅ Salvo com sucesso!")
                        st.rerun()
