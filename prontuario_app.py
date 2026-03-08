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
        st.error("❌ Credenciais não encontradas nos Secrets!")
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
    if st.sidebar.button("Sair / Trocar Login"):
        st.session_state.autenticado = False
        st.rerun()

    # --- VISÃO DO DIÁCONO (FICHA DE LEITURA AMPLIADA) ---
    if st.session_state.cargo == "Diácono":
        st.title("📋 Fichas de Prontuários para Conferência")
        
        try:
            res = supabase.table("registros_piedade").select("*").order("data_sistema", desc=True).execute()
            dados = res.data
            
            if dados:
                df_excel = pd.DataFrame(dados)
                csv = df_excel.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Gerar Planilha Excel (CSV)", csv, "relatorio_piedade.csv", "text/csv")
                
                st.divider()
                
                for item in dados:
                    with st.container(border=True):
                        col_info, col_status = st.columns([3, 1])
                        
                        with col_info:
                            st.markdown(f"### 📄 Prontuário: {item.get('num_prontuario') or 'NOVO CADASTRO'}")
                            st.caption(f"📅 Registrado em: {item.get('data_sistema')}")
                        
                        with col_status:
                            status_db = item.get('tratado', False)
                            novo_status = st.radio(f"Tratado? (Ref:{item['id'][:4]})", ["Não", "Sim"], 
                                                 index=1 if status_db else 0, key=f"rad_{item['id']}")
                            
                            if (novo_status == "Sim") != status_db:
                                supabase.table("registros_piedade").update({"tratado": novo_status == "Sim"}).eq("id", item['id']).execute()
                                st.toast("Status atualizado!")

                        # Layout de leitura fácil
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Solicitante", item.get('nome_solicitante'))
                        c2.metric("Cestas", item.get('quantidade_cestas'))
                        c3.metric("Local", item.get('local_retirada'))
                        
                        if item.get('nome_completo'):
                            st.markdown("---")
                            st.write(f"**Assistido:** {item.get('nome_completo')} | **Idade:** {item.get('idade')} anos")
                            st.write(f"**Endereço:** {item.get('endereco')}, {item.get('bairro')} - CEP: {item.get('cep')}")
                            if item.get('nome_conjuge'):
                                st.write(f"**Cônjuge:** {item.get('nome_conjuge')}")
            else:
                st.info("Nenhum registro encontrado no banco de dados.")
        except Exception as e: st.error(f"Erro ao carregar: {e}")

    # --- VISÃO DA IRMÃ DA PIEDADE (CADASTRO COM LÓGICA DE OBRIGATORIEDADE) ---
    else:
        liberado, data_lib = verificar_bloqueio()
        st.title("📝 Cadastro de Pedidos e Prontuários")

        if not liberado:
            st.error(f"⚠️ Sistema em período de bloqueio. Liberação: {data_lib.strftime('%d/%m/%Y')}")
        else:
            with st.form("meu_formulario"):
                st.subheader("1. Identificação da Solicitação")
                tipo_sol = st.radio("Solicitante:", ["Diácono", "Irmã da Piedade"], horizontal=True)
                nome_sol = st.text_input("Nome do Solicitante (Obrigatório):")
                
                col_n1, col_n2 = st.columns(2)
                q_cestas = col_n1.number_input("Quantidade de Cestas:", min_value=1, step=1)
                loc_retirada = col_n2.radio("Local de Retirada:", ["Pq. Guarani", "Itaquera"], horizontal=True)

                # Caixa que define se os campos de cadastro vão aparecer
                st.divider()
                is_novo = st.checkbox("🆕 ESTE É UM CADASTRO NOVO? (Marque para abrir o formulário)")
                
                # Número do prontuário (Obrigatório apenas se NÃO for novo)
                n_prontuario = st.text_input("Número do Prontuário (Obrigatório se NÃO for cadastro novo):")

                # Inicializando variáveis para evitar erro de envio
                n_completo, n_idade, n_batismo, n_civil, n_conjuge = "", 0, "", "Solteiro(a)", ""
                n_endereco, n_bairro, n_cep = "", "", ""

                # --- CAMPOS QUE SÓ APARECEM SE FOR NOVO ---
                if is_novo:
                    st.markdown("### 📋 Dados para Novo Cadastro")
                    n_completo = st.text_input("Nome Completo do Assistido (Obrigatório):")
                    
                    d1, d2, d3 = st.columns(3)
                    n_idade = d1.number_input("Idade:", min_value=0)
                    n_batismo = d2.text_input("Tempo de Batismo (Opcional):")
                    n_civil = d3.selectbox("Estado Civil:", ["Solteiro(a)", "Casado(a)", "Viúvo(a)", "Desquitado(a)"])
                    
                    if n_civil == "Casado(a)":
                        n_conjuge = st.text_input("Nome do Cônjuge (Obrigatório):")
                    
                    st.markdown("#### Endereço do Assistido")
                    n_endereco = st.text_input("Rua e Número (Obrigatório):")
                    b1, b2 = st.columns(2)
                    n_bairro = b1.text_input("Bairro (Obrigatório):")
                    n_cep = b2.text_input("CEP (Obrigatório):")

                st.write("")
                btn_salvar = st.form_submit_button("💾 SALVAR REGISTRO NO SISTEMA", type="primary", use_container_width=True)

                if btn_salvar:
                    # --- VALIDAÇÕES ---
                    validado = True
                    if not nome_sol:
                        st.error("Por favor, informe o Nome do Solicitante."); validado = False
                    
                    if not is_novo and not n_prontuario:
                        st.error("Para prontuários existentes, o Número do Prontuário é obrigatório."); validado = False
                    
                    if is_novo:
                        if not n_completo or n_idade == 0 or not n_endereco or not n_bairro or not n_cep:
                            st.error("Para Cadastro Novo, preencha: Nome, Idade e Endereço Completo."); validado = False
                        if n_civil == "Casado(a)" and not n_conjuge:
                            st.error("Nome do Cônjuge é obrigatório para casados."); validado = False

                    # --- ENVIO PARA O BANCO ---
                    if validado:
                        data_atual = datetime.now().strftime('%d/%m/%Y') # Data do sistema (computador)
                        payload = {
                            "tipo_solicitante": tipo_sol,
                            "nome_solicitante": nome_sol,
                            "num_prontuario": n_prontuario,
                            "quantidade_cestas": int(q_cestas),
                            "local_retirada": loc_retirada,
                            "nome_completo": n_completo,
                            "idade": int(n_idade),
                            "tempo_batismo": n_batismo,
                            "estado_civil": n_civil,
                            "nome_conjuge": n_conjuge,
                            "endereco": n_endereco,
                            "bairro": n_bairro,
                            "cep": n_cep,
                            "data_sistema": data_atual,
                            "tratado": False
                        }
                        try:
                            supabase.table("registros_piedade").insert(payload).execute()
                            st.success(f"✅ Registro salvo com sucesso em {data_atual}!")
                            st.balloons()
                            # O formulário limpa sozinho após o rerun do sucesso
                        except Exception as e:
                            st.error(f"Erro ao salvar no banco: {e}")
