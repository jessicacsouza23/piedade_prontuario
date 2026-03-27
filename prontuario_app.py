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
    .nome-header { font-size: 1.1rem; font-weight: 800; color: #1E3A8A; border-left: 5px solid #1E3A8A; padding-left: 10px; }
    .stDownloadButton button { width: 100% !important; border-radius: 8px !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO DA TRAVA (LÓGICA CORRIGIDA) ---
def verificar_sistema_aberto():
    # Usa a data do notebook para seu teste
    hoje = datetime.now().date()
    
    def buscar_primeiro_sabado(data_ref):
        primeiro_dia = data_ref.replace(day=1)
        dias_para_sabado = (5 - primeiro_dia.weekday() + 7) % 7
        return primeiro_dia + timedelta(days=dias_para_sabado)

    proximo_sabado = buscar_primeiro_sabado(hoje)
    
    # Se hoje já passou do domingo após o sábado atual, foca no sábado do mês que vem
    if hoje > (proximo_sabado + timedelta(days=0)): 
        proximo_mes = (hoje.replace(day=28) + timedelta(days=4))
        proximo_sabado = buscar_primeiro_sabado(proximo_mes)

    terca_limite = proximo_sabado - timedelta(days=4)
    liberacao_domingo = proximo_sabado + timedelta(days=1)

    # BLOQUEIO: Entre quarta (terca+1) e sábado inclusive
    if hoje > terca_limite and hoje <= proximo_sabado:
        return False, terca_limite, proximo_sabado
    return True, terca_limite, proximo_sabado

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
        if any(key.startswith(pre) for pre in ["f_", "n_", "c_", "ts_", "inv_", "np_", "qp_", "ns_",
