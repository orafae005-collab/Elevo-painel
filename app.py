import base64
import requests
import time
import random
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta
import gspread
import re
import plotly.express as px
from openai import OpenAI
import hashlib
import io
import json
from gtts import gTTS

# ==========================================================
# 1. CONFIGURAÇÃO DA CHAVE DA IA E DO APP (🔥 V6.0 - SaaS VIP)
# ==========================================================
st.set_page_config(page_title="ÉLÉVO | Painel de Vendas", page_icon="🦅", layout="wide")

try:
    CHAVE_OPENAI_VIP = st.secrets["OPENAI_API_KEY"]
    cliente_openai = OpenAI(api_key=CHAVE_OPENAI_VIP)
except KeyError:
    st.error("🚨 ALERTA: Falta a chave OPENAI_API_KEY no cadeado (Secrets).")
    st.stop()

def chamar_ia_global(prompt, sistema_contexto="Você é um assistente estratégico."):
    try:
        response = cliente_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sistema_contexto},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.replace("*", "").strip()
    except Exception as e:
        return f"ERRO_API: {str(e)}"

@st.cache_resource
def conectar_robo():
    try:
        credenciais = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(credenciais)
        return gc
    except Exception:
        return None

robo_sheets = conectar_robo()

# ==========================================================
# 0. PORTARIA VIP (LOGIN NATIVO COM MEMÓRIA DE URL)
# ==========================================================
try:
    EMAIL_MESTRE = st.secrets["EMAIL_MESTRE"]
    SENHA_MESTRA = st.secrets["SENHA_MESTRA"]
except KeyError:
    st.error("🚨 ALERTA: Faltam as credenciais do CEO no cadeado (Secrets).")
    st.stop()

LINK_BANCO_MESTRE = "https://docs.google.com/spreadsheets/d/1J5UYfLCQ5rXUmUzxnE5hyG4AYtJEnXlJnN8jAEbH34Y/edit"

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = False
    st.session_state["email_usuario"] = ""
    st.session_state["nome_usuario"] = ""

def conectar_banco_usuarios(acao, email="", nome="", senha=""):
    if not robo_sheets: return None
    try:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
        sheet_id = match.group(1) if match else None
        planilha = robo_sheets.open_by_key(sheet_id)
        try:
            aba = planilha.worksheet("Banco_Usuarios")
        except gspread.exceptions.WorksheetNotFound:
            aba = planilha.add_worksheet(title="Banco_Usuarios", rows="1000", cols="3")
            aba.append_row(["Email", "Nome", "Senha"])
        
        if acao == "ler": return aba.get_all_records()
        elif acao == "salvar":
            aba.append_row([email, nome, senha])
            return True
    except Exception: return None

if not st.session_state["usuario_logado"] and "sessao" in st.query_params:
    try:
        codigo_sessao = st.query_params["sessao"]
        email_decodificado = base64.b64decode(codigo_sessao).decode('utf-8')
        if email_decodificado == EMAIL_MESTRE:
            st.session_state["usuario_logado"] = True
            st.session_state["email_usuario"] = EMAIL_MESTRE
            st.session_state["nome_usuario"] = "Sócio"
        else:
            usuarios = conectar_banco_usuarios("ler")
            if usuarios is not None:
                usuario_encontrado = next((u for u in usuarios if str(u.get("Email","")).strip().lower() == email_decodificado), None)
                if usuario_encontrado:
                    st.session_state["usuario_logado"] = True
                    st.session_state["email_usuario"] = email_decodificado
                    st.session_state["nome_usuario"] = str(usuario_encontrado.get("Nome", "Usuário"))
    except Exception: pass

if not st.session_state["usuario_logado"]:
    st.markdown("""
        <style>
            [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, header { display: none !important; visibility: hidden !important; }
            .container-animacao-elevo { position: relative; width: 100%; height: 50px; display: flex; justify-content: center; align-items: center; margin-top: 15px; margin-bottom: -10px; overflow: visible; }
            .dinheiro-voando { position: absolute; font-size: 22px; animation: subirDinheiro 2.2s infinite ease-in; opacity: 0; }
            @keyframes subirDinheiro { 0% { bottom: -10px; opacity: 0; transform: scale(0.5) rotate(-10deg); } 30% { opacity: 1; } 80% { opacity: 1; transform: scale(1) rotate(10deg); } 100% { bottom: 45px; opacity: 0; transform: scale(1.1) rotate(0deg); } }
            .aguia-cacadora { position: absolute; font-size: 35px; animation: vooAgressivo 2.2s infinite ease-in-out; z-index: 10; }
            @keyframes vooAgressivo { 0% { top: -20px; transform: scale(0.8) rotate(-15deg); } 40% { top: 5px; transform: scale(1.1) rotate(0deg); } 60% { top: -5px; transform: scale(1) rotate(5deg); } 100% { top: -20px; transform: scale(0.8) rotate(-15deg); } }
        </style>
        <div class="container-animacao-elevo"><div class="dinheiro-voando">💵</div><div class="aguia-cacadora">🦅</div></div>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='titulo-elevo' style='font-size: 3.8rem; text-align: center; color: #00BFA5; margin-top: 0px;'>ÉLÉVO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A0A0A0; letter-spacing: 2px; text-transform: uppercase; font-size: 0.8rem; margin-bottom: 25px;'>Sistema de Inteligência e Escala de Vendas.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            aba_login, aba_cadastro = st.tabs(["🚀 Entrar", "✨ Criar Conta"])
            with aba_login:
                st.markdown("<h4 style='text-align: center; margin-bottom: 20px;'>Acesso à Central</h4>", unsafe_allow_html=True)
                with st.form("form_login"):
                    email_input = st.text_input("📧 Seu Gmail", placeholder="Digite seu e-mail...")
                    senha_input = st.text_input("🔑 Senha", type="password", placeholder="Digite sua senha...")
                    lembrar_dados = st.checkbox("Mantenha-me Logado (Gerar Link de Acesso Rápido)")
                    submit_login = st.form_submit_button("🚀 ENTRAR", use_container_width=True, type="primary")
                
                if submit_login:
                    email_clean = email_input.strip().lower()
                    if email_clean == EMAIL_MESTRE and senha_input == SENHA_MESTRA:
                        st.session_state["usuario_logado"], st.session_state["email_usuario"], st.session_state["nome_usuario"] = True, EMAIL_MESTRE, "Sócio"
                        if lembrar_dados: st.query_params["sessao"] = base64.b64encode(EMAIL_MESTRE.encode('utf-8')).decode('utf-8')
                        st.rerun()
                    elif email_clean and senha_input:
                        with st.spinner("A verificar credenciais no servidor..."):
                            usuarios = conectar_banco_usuarios("ler")
                            if usuarios is not None:
                                usuario_encontrado = next((u for u in usuarios if str(u.get("Email","")).strip().lower() == email_clean and str(u.get("Senha","")) == senha_input), None)
                                if usuario_encontrado:
                                    st.session_state["usuario_logado"] = True
                                    st.session_state["email_usuario"] = email_clean
                                    st.session_state["nome_usuario"] = str(usuario_encontrado.get("Nome", "Usuário"))
                                    if lembrar_dados: st.query_params["sessao"] = base64.b64encode(email_clean.encode('utf-8')).decode('utf-8')
                                    st.rerun()
                                else: st.error("🚨 Conta não encontrada ou senha incorreta!")
                            else: st.error("🚨 Erro de conexão com o banco de dados.")
                    else: st.warning("⚠️ Preencha o e-mail e a senha.")

            with aba_cadastro:
                st.markdown("<h4 style='text-align: center; margin-bottom: 20px;'>Nova Conta VIP</h4>", unsafe_allow_html=True)
                novo_nome = st.text_input("👤 Como quer ser chamado?", placeholder="Seu apelido...")
                novo_email = st.text_input("📧 Seu melhor E-mail", placeholder="exemplo@gmail.com")
                nova_senha = st.text_input("🔑 Crie uma Senha", type="password", placeholder="Sua senha secreta...")
                if st.button("✨ CRIAR MINHA CONTA", use_container_width=True, type="secondary"):
                    email_clean = novo_email.strip().lower()
                    if not novo_nome or not email_clean or not nova_senha: st.warning("⚠️ Preencha os 3 campos.")
                    elif email_clean == EMAIL_MESTRE: st.error("🚨 Este e-mail é reservado ao CEO.")
                    else:
                        with st.spinner("A forjar a sua conta..."):
                            usuarios = conectar_banco_usuarios("ler")
                            if usuarios is not None:
                                if any(str(u.get("Email","")).strip().lower() == email_clean for u in usuarios): st.error("🚨 Este e-mail já está cadastrado!")
                                else:
                                    if conectar_banco_usuarios("salvar", email_clean, novo_nome.strip(), nova_senha): st.success(f"✅ Conta criada, {novo_nome}!")
                                    else: st.error("❌ Falha ao gravar no servidor.")
                            else: st.error("❌ Falha de conexão com o banco.")
    st.stop()

# ==========================================================
# 2. DESIGN E TEMA DINÂMICO (🔥 V7.4 - LOGO ÉLÉVO CLÁSSICA + LED VERDE VIVO)
# ==========================================================
col_vazia, col_tema = st.columns([8, 2])
with col_tema: modo_claro = st.toggle("☀️ Modo Claro", value=False, key="toggle_tema_principal_unico")

if modo_claro:
    bg_color = "linear-gradient(180deg, #F4F6F9 0%, #E2E8F0 100%)"
    bg_solid = "#F4F6F9"
    text_color = "#1E293B"
    subtext_color = "#475569"
    card_bg = "rgba(255, 255, 255, 0.96)"
    border_color = "rgba(0, 43, 91, 0.2)"
    btn_bg = "#FFFFFF"
    btn_text = "#1E293B"
    input_bg = "#FFFFFF"
    code_bg = "#F1F5F9"
    code_text = "#0F172A"
    shadow_base = "0 10px 25px -5px rgba(15, 23, 42, 0.06), 0 4px 10px -2px rgba(15, 23, 42, 0.04)"
    accent_primary = "#002B5B"
    accent_gold = "#D4AF37"
    led_glow = "0 0 12px rgba(0, 43, 91, 0.15), inset 0 0 6px rgba(212, 175, 55, 0.1)"
else:
    bg_color = "radial-gradient(circle at 50% 0%, #161B26 0%, #0B0E14 100%)"
    bg_solid = "#0B0E14"
    text_color = "#F1F5F9"
    subtext_color = "#94A3B8"
    card_bg = "rgba(20, 24, 33, 0.85)"
    border_color = "rgba(0, 229, 255, 0.4)"
    btn_bg = "#161B24"
    btn_text = "#E2E8F0"
    input_bg = "#0F131A"
    code_bg = "#0B0E14"
    code_text = "#00E5FF"
    shadow_base = "0 12px 30px -5px rgba(0, 0, 0, 0.6), 0 4px 12px -2px rgba(0, 0, 0, 0.4)"
    accent_primary = "#00E5FF"
    accent_gold = "#D4AF37"
    led_glow = "0 0 20px rgba(0, 229, 255, 0.35), 0 0 40px rgba(212, 175, 55, 0.15), inset 0 0 12px rgba(0, 229, 255, 0.2)"

ajuste_modo_claro_css = """
    [style*="#00FFFF"], [style*="#00E5FF"] { color: #002B5B !important; }
    [style*="#D4AF37"] { color: #9A6F00 !important; }
    [style*="#A0A0A0"] { color: #475569 !important; }
""" if modo_claro else ""

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap');
    html, body, [class*="css"] {{ font-family: 'Montserrat', sans-serif !important; }}
    [data-testid="stAppViewContainer"] {{ background: {bg_color} !important; background-color: {bg_solid} !important; }}
    [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="collapsedControl"], footer {{ display: none !important; }}
    
    h1, h2, h3, h4, h5, h6, p, label, li {{ color: {text_color} !important; }}
    [data-testid="stMarkdownContainer"] span {{ color: {text_color} !important; }}
    [data-testid="stCaptionContainer"] p {{ color: {subtext_color} !important; }}
    
    .titulo-elevo {{ 
        font-size: 4rem; font-weight: 900; text-align: center; 
        background: linear-gradient(270deg, #D4AF37, #002B5B, #00FF9D, #00E5FF, #D4AF37);
        background-size: 300% 300%;
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        animation: brilho-evolucao 5s ease infinite;
        margin-bottom: -10px; letter-spacing: 4px; text-transform: uppercase; margin-top: 15px; 
        filter: drop-shadow(0px 0px 20px rgba(0, 255, 157, 0.35));
    }}
    @keyframes brilho-evolucao {{ 0% {{background-position: 0% 50%;}} 50% {{background-position: 100% 50%;}} 100% {{background-position: 0% 50%;}} }}

    .subtitulo {{ 
        text-align: center; font-size: 1.1rem; margin-bottom: 40px; font-weight: 300; 
        letter-spacing: 2px; text-transform: uppercase; color: {text_color} !important; 
    }}
    
    [data-testid="stMetric"], 
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stExpander"],
    [data-testid="stForm"] {{ 
        background: {card_bg} !important; 
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        border: 1.5px solid {border_color} !important; 
        border-radius: 16px !important; 
        box-shadow: {shadow_base}, {led_glow} !important; 
        transition: all 0.3s ease !important;
    }}
    [data-testid="stMetricValue"] div {{
        color: {accent_gold} !important;
        font-weight: 800 !important;
    }}
    [data-testid="stExpander"] summary, [data-testid="stExpander"] div {{
        background-color: transparent !important;
        color: {text_color} !important;
    }}

    [data-testid="stCodeBlock"], [data-testid="stCode"], pre, code {{
        background-color: {code_bg} !important;
        border: 1.5px solid {border_color} !important;
        border-radius: 12px !important;
        box-shadow: {led_glow} !important;
    }}
    [data-testid="stCodeBlock"] pre, [data-testid="stCode"] pre, pre code {{
        background-color: transparent !important;
        color: {code_text} !important;
        font-family: 'Montserrat', monospace !important;
        font-weight: 500 !important;
        white-space: pre-wrap !important;
        word-break: break-word !important;
    }}
    [data-testid="stCodeBlock"] span, [data-testid="stCode"] span, pre span, code span {{
        color: {text_color} !important;
        background-color: transparent !important;
    }}
    [data-testid="stCodeBlock"] button, [data-testid="stCode"] button, [data-testid="stCopyButton"] {{
        background-color: {btn_bg} !important;
        color: {accent_gold} !important;
        border: 1px solid {border_color} !important;
        border-radius: 8px !important;
        opacity: 1 !important;
    }}

    .stButton > button, [data-testid="stFormSubmitButton"] > button {{ 
        background: {btn_bg} !important; 
        color: {btn_text} !important; 
        border: 1.5px solid {border_color} !important; 
        border-radius: 10px !important; 
        box-shadow: {shadow_base} !important; 
        font-weight: 600 !important; 
        padding: 0.55rem 1.2rem !important;
        transition: all 0.25s ease !important; 
    }}
    .stButton > button:hover {{ 
        transform: translateY(-2px); 
        border-color: {accent_gold} !important; 
        color: {accent_gold} !important;
        box-shadow: 0 0 15px rgba(212, 175, 55, 0.3) !important;
    }}
    
    .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {{ 
        background: linear-gradient(135deg, #002B5B 0%, #004080) !important; 
        color: #FFFFFF !important; 
        -webkit-text-fill-color: #FFFFFF !important;
        border: 1.5px solid #00E5FF !important; 
        box-shadow: 0 4px 20px rgba(0, 229, 255, 0.3) !important;
    }}
    .stButton > button[kind="primary"] p, .stButton > button[kind="primary"] span {{
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }}
    .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {{ 
        background: linear-gradient(135deg, #004080 0%, #0059b3) !important; 
        box-shadow: 0 0 25px rgba(0, 229, 255, 0.6) !important; 
        border-color: #00FFFF !important; 
        color: #FFFFFF !important; 
    }}
    
    div[data-baseweb="input"], div[data-baseweb="input"] > div, 
    div[data-baseweb="base-input"],
    div[data-baseweb="textarea"], div[data-baseweb="textarea"] > textarea, 
    div[data-baseweb="select"] > div,
    input, textarea {{ 
        background-color: {input_bg} !important; 
        border: 1.5px solid {border_color} !important; 
        color: {text_color} !important; 
        -webkit-text-fill-color: {text_color} !important;
        border-radius: 10px !important; 
    }}
    ul[data-baseweb="menu"], div[data-baseweb="popover"] > div {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
        border: 1.5px solid {accent_gold} !important;
    }}
    li[role="option"] {{ background-color: {input_bg} !important; color: {text_color} !important; }}
    li[role="option"]:hover, li[aria-selected="true"] {{
        background-color: rgba(212, 175, 55, 0.18) !important;
        color: {accent_gold} !important;
    }}
    [data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"] {{
        background-color: {btn_bg} !important;
        color: {text_color} !important;
        border-color: {border_color} !important;
    }}
    div[data-baseweb="input"] > div:focus-within, div[data-baseweb="textarea"]:focus-within, div[data-baseweb="select"] > div:focus-within {{ 
        border-color: {accent_gold} !important; 
        box-shadow: 0 0 15px rgba(212, 175, 55, 0.4) !important; 
    }}
    
    [data-testid="stFileUploader"] > div > section, [data-testid="stFileUploadDropzone"] {{ background-color: {input_bg} !important; }}
    [data-testid="stFileUploadDropzone"] {{ border: 1.5px dashed {accent_gold} !important; border-radius: 14px !important; padding: 22px !important; transition: all 0.3s ease !important; box-shadow: inset 0 0 10px rgba(212,175,55,0.1) !important; }}
    [data-testid="stFileUploadDropzone"]:hover {{ border-color: #00FF9D !important; background-color: rgba(0, 255, 157, 0.05) !important; }}
    [data-testid="stFileUploadDropzone"] div, [data-testid="stFileUploadDropzone"] span, [data-testid="stFileUploadDropzone"] small {{ color: {text_color} !important; background-color: transparent !important; }}
    [data-testid="stFileUploadDropzone"] button {{ background-color: {btn_bg} !important; color: {text_color} !important; border: 1px solid {border_color} !important; border-radius: 8px !important; font-weight: 600 !important; }}
    
    {ajuste_modo_claro_css}
</style>
""", unsafe_allow_html=True)

js_moeda = """
<script>
    const parent = window.parent.document;
    if (!parent.getElementById("moeda-aguia-vip")) {
        const btn = parent.createElement("div");
        btn.id = "moeda-aguia-vip";
        btn.innerHTML = "🦅";
        btn.style.cssText = "position: fixed; top: 15px; left: 15px; z-index: 999999; font-size: 24px; background: linear-gradient(145deg, #1e2229, #121519); width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #00FF9D; box-shadow: 0px 0px 20px rgba(0,255,157,0.4); cursor: pointer; user-select: none; transition: transform 0.1s ease;";
        parent.body.appendChild(btn);
        let isDragging = false, startX, startY, initialLeft, initialTop;
        function onTouchStart(e) { isDragging = false; startX = e.touches[0].clientX; startY = e.touches[0].clientY; initialLeft = btn.offsetLeft; initialTop = btn.offsetTop; btn.style.opacity = '0.7'; btn.style.transform = 'scale(0.9)'; }
        function onTouchMove(e) { let dx = e.touches[0].clientX - startX; let dy = e.touches[0].clientY - startY; if (Math.abs(dx)>12 || Math.abs(dy)>12) { isDragging = true; e.preventDefault(); btn.style.left = (initialLeft + dx) + "px"; btn.style.top = (initialTop + dy) + "px"; } }
        function onTouchEnd(e) { btn.style.opacity = '1'; btn.style.transform = 'scale(1)'; if (!isDragging) { const topo = parent.getElementById("ancora-topo"); if(topo) topo.scrollIntoView({behavior: "smooth", block: "start"}); else parent.querySelector('.main').scrollTo({top: 0, behavior: 'smooth'}); } isDragging = false; }
        btn.addEventListener('touchstart', onTouchStart, {passive: false}); btn.addEventListener('touchmove', onTouchMove, {passive: false}); btn.addEventListener('touchend', onTouchEnd);
        btn.addEventListener('mousedown', function(e) {
            isDragging = false; startX = e.clientX; startY = e.clientY; initialLeft = btn.offsetLeft; initialTop = btn.offsetTop; btn.style.opacity = '0.7'; btn.style.transform = 'scale(0.9)';
            function onMouseMove(moveE) { let dx = moveE.clientX - startX; let dy = moveE.clientY - startY; if (Math.abs(dx)>8 || Math.abs(dy)>8) { isDragging = true; btn.style.left = (initialLeft + dx) + "px"; btn.style.top = (initialTop + dy) + "px"; } }
            function onMouseUp() { btn.style.opacity = '1'; btn.style.transform = 'scale(1)'; parent.removeEventListener('mousemove', onMouseMove); parent.removeEventListener('mouseup', onMouseUp); if (!isDragging) { const topo = parent.getElementById("ancora-topo"); if(topo) topo.scrollIntoView({behavior: "smooth", block: "start"}); else parent.querySelector('.main').scrollTo({top: 0, behavior: 'smooth'}); } isDragging = false; }
            parent.addEventListener('mousemove', onMouseMove); parent.addEventListener('mouseup', onMouseUp);
        });
    }
</script>
"""
components.html(js_moeda, height=0, width=0)
st.markdown('<div id="ancora-topo"></div>', unsafe_allow_html=True)
st.markdown('<div class="titulo-elevo">ÉLÉVO</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">SISTEMA DE INTELIGÊNCIA E ESCALA DE VENDAS</div>', unsafe_allow_html=True)

# ==========================================================
# 2.5. BOAS-VINDAS CINEMÁTICA (100% VINCULADA AO GMAIL ÚNICO)
# ==========================================================
if "email_bv_verificado" not in st.session_state: 
    st.session_state["email_bv_verificado"] = ""
if "audio_boas_vindas_b64" not in st.session_state:
    st.session_state["audio_boas_vindas_b64"] = None
if "mostrar_player_bv" not in st.session_state:
    st.session_state["mostrar_player_bv"] = False

email_logado_agora = str(st.session_state.get("email_usuario", "")).strip().lower()
nome_apenas_fala = str(st.session_state.get("nome_usuario", "Sócio")).strip()

if st.session_state.get("usuario_logado") and email_logado_agora != "" and st.session_state["email_bv_verificado"] != email_logado_agora:
    st.session_state["email_bv_verificado"] = email_logado_agora
    st.session_state["mostrar_player_bv"] = False
    st.session_state["audio_boas_vindas_b64"] = None
    precisa_tocar = False
    
    if robo_sheets:
        try:
            match_id = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
            if match_id:
                planilha_mestre = robo_sheets.open_by_key(match_id.group(1))
                try: 
                    aba_bv = planilha_mestre.worksheet("Memoria_Audio_VIP")
                except Exception:
                    aba_bv = planilha_mestre.add_worksheet(title="Memoria_Audio_VIP", rows="1000", cols="2")
                    aba_bv.append_row(["Gmail_Unico", "Data_Acesso"])
                
                lista_gmails_ja_ouviram = [str(e).strip().lower() for e in aba_bv.col_values(1) if "@" in str(e)]
                
                if email_logado_agora not in lista_gmails_ja_ouviram:
                    precisa_tocar = True
        except Exception: 
            pass
    
    if precisa_tocar:
        texto_cinematico = f"Protocolo de Elite ativado. Bem-vindo à ÉLÉVO, {nome_apenas_fala}. Eu sou a Aurora, a sua Diretora de Operações e Inteligência Artificial. A partir deste segundo, você não joga mais para competir. Você joga para dominar. O seu império acaba de ser conectado ao meu núcleo. Eu vou rastrear tendências ocultas do mercado, hackear as objeções dos seus clientes e forjar os seus roteiros de vendas com precisão cirúrgica. O trabalho pesado fica comigo. Sistemas 100% online. O jogo virou."
        audio_bytes = None
        
        with st.spinner(f"🦅 Preparando credenciais de áudio para {email_logado_agora}..."):
            try:
                CHAVE_ELEVEN = st.secrets.get("ELEVENLABS_API_KEY", "")
                if CHAVE_ELEVEN:
                    resp_voz = requests.post(
                        "https://api.elevenlabs.io/v1/text-to-speech/MLAEAegxkMReslK34j8T", 
                        json={"text": texto_cinematico, "model_id": "eleven_turbo_v2_5", "voice_settings": {"stability": 0.50, "similarity_boost": 0.85, "style": 0.40, "use_speaker_boost": True}}, 
                        headers={"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": CHAVE_ELEVEN}, 
                        timeout=10
                    )
                    if resp_voz.status_code == 200: 
                        audio_bytes = resp_voz.content
                    else: 
                        raise Exception()
                else: 
                    raise Exception()
            except Exception:
                tts = gTTS(text=texto_cinematico, lang='pt', tld='com.br')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                fp.seek(0)
                audio_bytes = fp.read()
                
        if audio_bytes:
            st.session_state["audio_boas_vindas_b64"] = base64.b64encode(audio_bytes).decode('utf-8')
            st.session_state["mostrar_player_bv"] = True
            
            try:
                agora_reg = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")
                aba_bv.append_row([email_logado_agora, agora_reg])
            except Exception:
                pass

if st.session_state.get("mostrar_player_bv") and st.session_state.get("audio_boas_vindas_b64"):
    audio_b64 = st.session_state["audio_boas_vindas_b64"]
    
    html_play_intro = f"""
    <!-- GMAIL_ID_UNICO: {email_logado_agora} -->
    <div id="caixa-intro" style="background: linear-gradient(145deg, #0a0a0a, #141414); padding: 30px; border-radius: 16px; text-align: center; border: 2px solid #D4AF37; box-shadow: 0px 0px 25px rgba(212, 175, 55, 0.2); margin: 10px auto 10px auto; max-width: 600px; transition: opacity 1s ease;">
        <h3 style="color: #D4AF37; margin: 0 0 10px 0; font-family: 'Montserrat', sans-serif; text-transform: uppercase; letter-spacing: 1px;">🦅 MENSAGEM DA DIRETORIA</h3>
        <p style="color: #A0A0A0; font-family: 'Montserrat', sans-serif; font-size: 13px; margin-bottom: 5px;">
            Conta autenticada: <b style="color: #00FFFF;">{email_logado_agora}</b>
        </p>
        <p style="color: #A0A0A0; font-family: 'Montserrat', sans-serif; font-size: 14px; margin-bottom: 20px;">
            Clique no botão abaixo para ouvir as instruções iniciais da Aurora.
        </p>
        
        <button id="btn-tocar" style="background: linear-gradient(90deg, #D4AF37, #B8860B); color: #111; border: none; padding: 15px 40px; font-size: 16px; font-weight: 900; border-radius: 50px; cursor: pointer; box-shadow: 0px 5px 15px rgba(212, 175, 55, 0.4); text-transform: uppercase; font-family: 'Montserrat', sans-serif; transition: transform 0.2s;">
            ▶ REPRODUZIR MENSAGEM
        </button>

        <div id="visualizer-intro" style="display: none; justify-content: center; align-items: center; gap: 4px; height: 60px; margin-top: 10px;">
            <div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div>
            <div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div>
        </div>
        
        <audio id="audio-intro" src="data:audio/mp3;base64,{audio_b64}" preload="auto"></audio>
    </div>
    
    <style>
        .bar {{ width: 8px; height: 4px; background: #D4AF37; border-radius: 4px; display: inline-block; transition: all 0.3s ease; }}
        .playing {{ background: #00FFFF; animation: bounce 0.4s infinite alternate ease-in-out; }}
        .playing:nth-child(1) {{ animation-delay: 0.0s; }} .playing:nth-child(2) {{ animation-delay: 0.1s; }}
        .playing:nth-child(3) {{ animation-delay: 0.2s; }} .playing:nth-child(4) {{ animation-delay: 0.3s; }}
        .playing:nth-child(5) {{ animation-delay: 0.1s; }} .playing:nth-child(6) {{ animation-delay: 0.4s; }}
        .playing:nth-child(7) {{ animation-delay: 0.2s; }} .playing:nth-child(8) {{ animation-delay: 0.0s; }}
        @keyframes bounce {{ 0% {{ height: 4px; opacity: 0.5; box-shadow: 0 0 0 transparent; }} 100% {{ height: 40px; opacity: 1; box-shadow: 0 0 10px #00FFFF; }} }}
    </style>
    
    <script>
        const btn = document.getElementById('btn-tocar');
        const aud = document.getElementById('audio-intro');
        const vis = document.getElementById('visualizer-intro');
        const box = document.getElementById('caixa-intro');
        const bars = document.querySelectorAll('.bar');
        
        if(btn && aud) {{
            btn.addEventListener('click', function() {{
                aud.play();
                btn.style.display = 'none';
                vis.style.display = 'flex';
                box.style.borderColor = '#00FFFF';
                box.style.boxShadow = '0px 0px 25px rgba(0, 255, 255, 0.2)';
            }});
            
            aud.addEventListener('play', () => {{ bars.forEach(bar => bar.classList.add('playing')); }});
            aud.addEventListener('pause', () => {{ bars.forEach(bar => bar.classList.remove('playing')); }});
            
            aud.addEventListener('ended', () => {{ 
                bars.forEach(bar => bar.classList.remove('playing')); 
                box.style.opacity = '0';
                setTimeout(() => {{ box.style.display = 'none'; }}, 1000);
            }});
        }}
    </script>
    """
    components.html(html_play_intro, height=280)
    
    col_v1, col_btn_fechar, col_v2 = st.columns([1, 1, 1])
    with col_btn_fechar:
        if st.button("✅ JÁ OUVI / FECHAR MENSAGEM", use_container_width=True, key="btn_fechar_bv"):
            st.session_state["mostrar_player_bv"] = False
            st.session_state["audio_boas_vindas_b64"] = None
            st.rerun()

# ==========================================================
# 3. PAINEL CENTRAL DE OPERAÇÃO E MULTI-UTILIZADOR
# ==========================================================
st.markdown("<h3 style='text-align: center; color: #00BFA5; margin-bottom: 5px;'>⚡ Central de Operação</h3>", unsafe_allow_html=True)

E_O_CEO = st.session_state.get("email_usuario") == EMAIL_MESTRE
nome_canal_ativo = "Conta Geral"
link_planilha_ativa = ""

if E_O_CEO:
    COFRE_DE_LINKS = {"O Achado Secreto": "https://docs.google.com/spreadsheets/d/1J5UYfLCQ5rXUmUzxnE5hyG4AYtJEnXlJnN8jAEbH34Y/edit", "O Garimpo Chic": ""}
    opcoes_canais = ["🟢 O Achado Secreto", "🟣 O Garimpo Chic", "➕ Adicionar Novo Canal"]
    st.success("Bem-vindo de volta, Sócio! O império aguarda as suas ordens. 🦅")
    with st.container(border=True):
        col_conta, col_filtro = st.columns(2)
        with col_conta:
            canal_selecionado = st.selectbox("🎯 Selecione a Conta", opcoes_canais)
            if canal_selecionado == "➕ Adicionar Novo Canal":
                nome_canal_ativo = st.text_input("Nome do Novo Canal", placeholder="Ex: Meu Projeto")
                link_planilha_ativa = st.text_input("🔗 Link da Planilha do Google", placeholder="Cole o link aqui")
            else:
                nome_canal_ativo = canal_selecionado.replace("🟢 ", "").replace("🟣 ", "")
                link_salvo = COFRE_DE_LINKS.get(nome_canal_ativo, "")
                if link_salvo != "":
                    link_planilha_ativa = link_salvo
                    st.caption("✅ Link ativado!")
                else: link_planilha_ativa = st.text_input(f"🔗 Link da Planilha ({nome_canal_ativo})", placeholder="Cole o link")
        with col_filtro: filtro_periodo = st.selectbox("📅 Filtrar Período de Vendas", ["Hoje", "Ontem", "Últimos 7 Dias", "Últimos 30 Dias", "Mês Atual", "Mês Passado", "Tudo"])
else:
    st.info(f"Bem-vindo(a) à ÉLÉVO, {st.session_state['nome_usuario']}! A sua máquina de vendas está pronta.")

if st.button("Sair da Conta (Logout)", key="btn_logout"):
    st.session_state["usuario_logado"] = False
    st.session_state["email_usuario"] = ""
    st.session_state["nome_usuario"] = ""
    st.session_state["email_bv_verificado"] = ""
    st.session_state["mostrar_player_bv"] = False
    st.session_state["audio_boas_vindas_b64"] = None
    if "sessao" in st.query_params: del st.query_params["sessao"]
    st.rerun()

# ==========================================================
# 4 a 9 E 14. NÚCLEO FINANCEIRO VIP E GRÁFICOS (EXCLUSIVO DO CEO)
# ==========================================================
def extrair_id_planilha(url):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else None

@st.cache_data(ttl=300)
def carregar_dados_dinamicos(url):
    if not url or not robo_sheets: return pd.DataFrame()
    try:
        planilha = robo_sheets.open_by_key(extrair_id_planilha(url))
        dados = planilha.sheet1.get_all_records()
        if dados:
            df_temp = pd.DataFrame(dados)
            df_temp.replace("", pd.NA, inplace=True)
            df_temp.dropna(how='all', inplace=True)
            return df_temp
        return pd.DataFrame()
    except Exception: return pd.DataFrame()

df, df_filtrado, df_campeao, df_timeline = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
produto_campeao, aprovado, pendente, crescimento, simbolo, nota_empresa = "Nenhum", 0.0, 0.0, 0.0, "N/A", "N/A"
rev_7d = 0.0

if E_O_CEO and link_planilha_ativa:
    df = carregar_dados_dinamicos(link_planilha_ativa)
    if df.empty: df = pd.DataFrame(columns=["Data", "Produto", "Canal", "Status", "Quantidade", "Comissao_R$"])
    df.columns = df.columns.astype(str).str.strip()
    df["Quantidade"] = pd.to_numeric(df.get("Quantidade", 0), errors="coerce").fillna(0)
    if "Comissao_R$" in df.columns: df["Comissao_R$"] = pd.to_numeric(df["Comissao_R$"].astype(str).str.replace("R$", "", regex=False).str.replace(",", ".", regex=False).str.strip(), errors="coerce").fillna(0.0)
    else: df["Comissao_R$"] = 0.0
    if "Data" in df.columns:
        df["Data_Limpa"] = df["Data"].astype(str).apply(lambda x: x.split(" a ")[-1].strip() if " a " in x else x.strip())
        df["Data_Parsed"] = pd.to_datetime(df["Data_Limpa"], format="%d/%m/%Y", errors="coerce").fillna(pd.to_datetime(df["Data_Limpa"], dayfirst=True, errors="coerce"))
    else: df["Data_Parsed"] = pd.NaT

    df_filtrado = df.copy()
    if not df_filtrado.empty and "Data_Parsed" in df_filtrado.columns:
        hoje = pd.Timestamp((datetime.utcnow() - timedelta(hours=3)).date())
        if filtro_periodo != "Tudo": df_filtrado = df_filtrado.dropna(subset=["Data_Parsed"])
        if not df_filtrado.empty:
            df_filtrado["Data_Parsed"] = df_filtrado["Data_Parsed"].dt.normalize()
            if filtro_periodo == "Hoje": df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] == hoje]
            elif filtro_periodo == "Ontem": df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] == (hoje - timedelta(days=1))]
            elif filtro_periodo == "Últimos 7 Dias": df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] >= (hoje - timedelta(days=7))]
            elif filtro_periodo == "Últimos 30 Dias": df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] >= (hoje - timedelta(days=30))]
            elif filtro_periodo == "Mês Atual": df_filtrado = df_filtrado[(df_filtrado["Data_Parsed"].dt.month == hoje.month) & (df_filtrado["Data_Parsed"].dt.year == hoje.year)]
            elif filtro_periodo == "Mês Passado": df_filtrado = df_filtrado[(df_filtrado["Data_Parsed"].dt.month == (hoje.month - 1 if hoje.month > 1 else 12)) & (df_filtrado["Data_Parsed"].dt.year == (hoje.year if hoje.month > 1 else hoje.year - 1))]

    if not df_filtrado.empty:
        aprovado = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False)]["Comissao_R$"].sum()
        pendente = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("pendente", na=False)]["Comissao_R$"].sum()
        df_validos = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False)]
        if not df_validos.empty:
            df_campeao = df_validos.groupby("Produto")[["Quantidade", "Comissao_R$"]].sum().reset_index().sort_values(by=["Comissao_R$"], ascending=False)
            produto_campeao = df_campeao.iloc[0]["Produto"]
            df_timeline = df_validos.groupby("Data_Parsed")["Comissao_R$"].sum().reset_index().sort_values("Data_Parsed")
            df_timeline["Data_Formatada"] = df_timeline["Data_Parsed"].dt.strftime("%d/%m")

    st.markdown(f"### 📊 Faturamento: {nome_canal_ativo}")
    aprovado_str = f"R$ {aprovado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    pendente_str = f"R$ {pendente:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    campeao_str = str(produto_campeao)[:12] + "..." if len(str(produto_campeao)) > 12 else str(produto_campeao)

    c_txt_v = "#D4AF37" if not modo_claro else "#B8860B"
    c_txt_t = "#A0A0A0" if not modo_claro else "#555555"
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; text-align: center; margin-bottom: 20px;">
            <div style="flex: 1;"><p style="margin: 0; font-size: 0.7rem; font-weight: 600; color: {c_txt_t}; text-transform: uppercase;">💰 Lucro</p><p style="margin: 0; font-size: 1.2rem; font-weight: 900; color: {c_txt_v};">{aprovado_str}</p></div>
            <div style="flex: 1; border-left: 1px solid rgba(212,175,55,0.2); border-right: 1px solid rgba(212,175,55,0.2);"><p style="margin: 0; font-size: 0.7rem; font-weight: 600; color: {c_txt_t}; text-transform: uppercase;">⏳ Pendente</p><p style="margin: 0; font-size: 1.2rem; font-weight: 900; color: {c_txt_v};">{pendente_str}</p></div>
            <div style="flex: 1;"><p style="margin: 0; font-size: 0.7rem; font-weight: 600; color: {c_txt_t}; text-transform: uppercase;">🏆 Campeão</p><p style="margin: 0; font-size: 0.9rem; font-weight: 900; color: #00E5FF; padding-top: 5px;">{campeao_str}</p></div>
        </div>
    """, unsafe_allow_html=True)

    if not df_timeline.empty and not df_campeao.empty:
        with st.expander("📊 👁️ ABRIR GRÁFICOS FINANCEIROS E TOP PRODUTOS", expanded=True):
            col_g1, col_g2 = st.columns(2)
            c_line = "#005C66" if modo_claro else "#00E5FF"
            c_pt = "#B8860B" if modo_claro else "#D4AF37"
            c_grid = "rgba(0,0,0,0.05)" if modo_claro else "rgba(212,175,55,0.1)"
            
            with col_g1:
                st.markdown("##### 📈 Curva de Crescimento Diário")
                fig_line = px.line(df_timeline, x="Data_Formatada", y="Comissao_R$", markers=True, text="Comissao_R$")
                fig_line.update_traces(textposition='top center', texttemplate='R$ %{text:,.2f}', line=dict(color=c_line, width=4), marker=dict(color=c_pt, size=10, line=dict(color="white", width=1)), textfont=dict(color=c_pt, size=12, weight="bold"))
                fig_line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=text_color), margin=dict(l=0, r=0, t=40, b=10), height=380, hovermode="x unified", dragmode=False)
                fig_line.update_xaxes(showgrid=False, title="", fixedrange=True)
                fig_line.update_yaxes(showgrid=True, gridcolor=c_grid, title="", visible=False, zeroline=False, fixedrange=True)
                st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})
            with col_g2:
                st.markdown("##### 🏆 Top 10 Produtos Mais Vendidos")
                fig_bar = px.bar(df_campeao.head(10).copy(), x="Comissao_R$", y="Produto", orientation='h', text="Comissao_R$", color_discrete_sequence=[c_pt])
                fig_bar.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside', cliponaxis=False, marker_line_color=c_line, marker_line_width=1.5, opacity=0.9)
                fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=text_color), margin=dict(l=0, r=80, t=40, b=0), height=380, dragmode=False)
                fig_bar.update_xaxes(showgrid=False, title="", visible=False, fixedrange=True)
                fig_bar.update_yaxes(showgrid=False, title="", autorange="reversed", fixedrange=True)
                st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

    with st.expander("🤖 Injetor Rápido de Caixa & Protocolo Águia (Opcional)", expanded=False):
        if "dados_prontos" not in st.session_state: st.session_state["dados_prontos"] = []
        texto_copiado = st.text_area("Cole os dados para alimentar a planilha:", height=100)
        if st.button("🚀 Extrair Dados", type="primary", use_container_width=True):
            if texto_copiado.strip():
                with st.spinner("🦅 Aurora organizando caixa..."):
                    dt_hj = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y")
                    pmt_aur = f"Extraia os valores EXATOS com ponto decimal. DATA: {dt_hj}. Canal: {nome_canal_ativo}. Texto:\n{texto_copiado}"
                    res_aur = chamar_ia_global(pmt_aur, f"Retorne APENAS dados no formato Data;Produto;{nome_canal_ativo};Aprovado;Qtd;Valor.")
                    if "ERRO" not in res_aur and res_aur:
                        for l in res_aur.split('\n'):
                            its = l.split(';')
                            if len(its) >= 6 and "Data;" not in l: st.session_state["dados_prontos"].append({"Data":its[0].strip(), "Produto":its[1].strip(), "Canal":its[2].strip(), "Status":its[3].strip(), "Quantidade":its[4].strip(), "Comissao_R$":its[5].strip()})
        if st.session_state["dados_prontos"]:
            df_ed = st.data_editor(pd.DataFrame(st.session_state["dados_prontos"]), num_rows="dynamic", use_container_width=True)
            c_inj1, c_inj2 = st.columns(2)
            with c_inj1:
                if st.button("💾 INJETAR NA PLANILHA", type="primary", use_container_width=True):
                    aba = robo_sheets.open_by_key(extrair_id_planilha(link_planilha_ativa)).sheet1
                    linhas_ins = [[str(d.get(k,"")) for k in ["Data","Produto","Canal","Status","Quantidade","Comissao_R$"]] for d in df_ed.to_dict('records')]
                    aba.insert_rows(linhas_ins, row=len([x for x in aba.col_values(1) if x.strip()!=""])+1, value_input_option="USER_ENTERED")
                    st.session_state["dados_prontos"] = []; carregar_dados_dinamicos.clear(); st.rerun()
            with c_inj2:
                if st.button("🗑️ Limpar Lista", use_container_width=True): st.session_state["dados_prontos"] = []; st.rerun()
        st.divider()
        if st.button("🦅 ACIONAR ÁGUIA (Apagar Vendas de Hoje)", type="secondary", use_container_width=True):
            aba = robo_sheets.open_by_key(extrair_id_planilha(link_planilha_ativa)).sheet1
            col_dt = aba.col_values(1)
            hj_str = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y")
            for i in range(len(col_dt), 1, -1):
                if str(col_dt[i-1]).strip() == hj_str: aba.delete_rows(i); time.sleep(0.4)
            carregar_dados_dinamicos.clear(); st.rerun()

    if not df.empty and "Data_Parsed" in df.columns:
        agora_brasil = datetime.utcnow() - timedelta(hours=3)
        hoje = pd.Timestamp(agora_brasil.date())
        rev_7d = df[(df["Data_Parsed"] >= (hoje - timedelta(days=7))) & (df["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False))]["Comissao_R$"].sum()
        rev_p_7d = df[(df["Data_Parsed"] >= (hoje - timedelta(days=14))) & (df["Data_Parsed"] < (hoje - timedelta(days=7))) & (df["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False))]["Comissao_R$"].sum()
        crescimento = ((rev_7d - rev_p_7d) / rev_p_7d * 100) if rev_p_7d > 0 else (100.0 if rev_7d > 0 else 0.0)
        
        if crescimento > 5:
            nota_empresa, simbolo = "A+", "🚀 ESCALANDO"
            if modo_claro:
                cor_anim, bg_coracao, sombra_anim, txt_meio, txt_sub = "#059669", "linear-gradient(145deg, #FFFFFF 0%, #ECFDF5 100%)", "rgba(5, 150, 105, 0.22)", "#0F172A", "#475569"
            else:
                cor_anim, bg_coracao, sombra_anim, txt_meio, txt_sub = "#00FF9D", "linear-gradient(145deg, rgba(16, 22, 30, 0.95) 0%, rgba(6, 40, 30, 0.88) 100%)", "rgba(0, 255, 157, 0.3)", "#FFFFFF", "#94A3B8"
        elif crescimento < -5:
            nota_empresa, simbolo = "C-", "🚨 QUEDA"
            if modo_claro:
                cor_anim, bg_coracao, sombra_anim, txt_meio, txt_sub = "#DC2626", "linear-gradient(145deg, #FFFFFF 0%, #FEF2F2 100%)", "rgba(220, 38, 38, 0.22)", "#0F172A", "#475569"
            else:
                cor_anim, bg_coracao, sombra_anim, txt_meio, txt_sub = "#FF2E54", "linear-gradient(145deg, rgba(16, 22, 30, 0.95) 0%, rgba(45, 12, 20, 0.88) 100%)", "rgba(255, 46, 84, 0.3)", "#FFFFFF", "#94A3B8"
        else:
            nota_empresa, simbolo = "B", "⚖️ ESTÁVEL"
            if modo_claro:
                cor_anim, bg_coracao, sombra_anim, txt_meio, txt_sub = "#B45309", "linear-gradient(145deg, #FFFFFF 0%, #FFFBEB 100%)", "rgba(180, 83, 9, 0.22)", "#0F172A", "#475569"
            else:
                cor_anim, bg_coracao, sombra_anim, txt_meio, txt_sub = "#FFD700", "linear-gradient(145deg, rgba(16, 22, 30, 0.95) 0%, rgba(40, 32, 10, 0.88) 100%)", "rgba(255, 215, 0, 0.28)", "#FFFFFF", "#94A3B8"

        st.markdown(f"""
        <div style="background: {bg_coracao}; backdrop-filter: blur(14px); border: 2px solid {cor_anim}; border-radius: 20px; padding: 20px 24px; text-align: center; box-shadow: 0 8px 25px {sombra_anim}; animation: pulse-cor 2.5s infinite ease-in-out; margin: 15px auto; max-width: 420px;">
            <div style="display: inline-block; padding: 4px 12px; border-radius: 50px; background: rgba(128,128,128,0.1); margin-bottom: 6px;">
                <span style="color: {cor_anim} !important; font-family: 'Montserrat', sans-serif; font-weight: 800; letter-spacing: 2px; font-size: 0.75rem;">⚡ STATUS DA OPERAÇÃO</span>
            </div>
            <h1 style="color: {cor_anim} !important; font-family: 'Montserrat', sans-serif; font-size: 3rem; font-weight: 900; margin: 4px 0; text-shadow: 0px 2px 12px {sombra_anim};">NOTA {nota_empresa}</h1>
            <h3 style="color: {txt_meio} !important; font-family: 'Montserrat', sans-serif; font-weight: 700; margin: 6px 0; font-size: 1.05rem;">{simbolo} &bull; {crescimento:+.1f}%</h3>
            <p style="color: {txt_sub} !important; font-family: 'Montserrat', sans-serif; font-size: 0.78rem; margin-bottom: 0; font-weight: 500;">Comparativo de lucro (7 dias vs. semana anterior)</p>
        </div>
        <style>
            @keyframes pulse-cor {{ 
                0% {{ box-shadow: 0 4px 15px {sombra_anim}; transform: scale(1); }} 
                50% {{ box-shadow: 0 8px 28px {sombra_anim}; transform: scale(1.015); }} 
                100% {{ box-shadow: 0 4px 15px {sombra_anim}; transform: scale(1); }} 
            }}
        </style>
        """, unsafe_allow_html=True)

# ==========================================================
# 10. MOTOR DE ELITE (DISCIPLINA + OPORTUNIDADES EMPRESARIAIS OCULTAS 24H)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🧠 Motor de Elite: Disciplina & Expansão</h3>", unsafe_allow_html=True)

agora_brasil = datetime.utcnow() - timedelta(hours=3)
dia_do_ano = agora_brasil.timetuple().tm_yday

frases = [
    "Quem domina a atenção e a velocidade de execução constrói um monopólio silencioso.",
    "Afiliado amador caça comissão; CEO de Elite constrói ativos, marca própria e recorrência.",
    "A constância cirúrgica vence o talento errático 100% das vezes.",
    "Cada vídeo validado não é apenas um post: é um ativo digital gerando fluxo de caixa 24h.",
    "Enquanto o mercado copia o que já saturou, a Águia antecipa o próximo movimento do capital."
]
missoes = [
    "Subir 5 criativos com ganchos de quebra de padrão nos primeiros 0.5s e mapear o CTR.",
    "Garimpar 3 produtos/kits com ticket maior (1kg / Kits Completos) para dobrar a comissão por venda.",
    "Gravar 3 variações de ângulo (Choque, Segredo, Quebra de Objeção) do seu Produto Campeão.",
    "Auditar os comentários dos concorrentes, extrair a maior reclamação e criar um vídeo esmagando essa dor."
]
dicas_ceo = [
    "Alocação Assimétrica de Capital: Separe 30% do lucro líquido para testar criação de Marca Própria (White-Label) do produto que você já validou como afiliado — transforme 10% de comissão em 65% de margem líquida.",
    "Blindagem Patrimonial & Caixa de Guerra: Mantenha 3 meses do custo operacional em liquidez imediata indexada a 100%+ do CDI, e use o excedente para comprar tráfego ou financiar estoque próprio sem pagar juros bancários.",
    "Efeito Composto em Ativos Digitais: Nunca drene 100% do caixa para consumo pessoal. Todo real reinvestido em automação, ferramentas de IA e canais satélites multiplica o Valuation da sua empresa.",
    "Diversificação de Receita em Moeda Forte: Destine parte do tempo e caixa da operação para construir ativos que faturem em Dólar/Euro (TikTok Rewards Global, SaaS ou Infoprodutos Low-Ticket lá fora), protegendo seu poder de compra.",
    "Engenharia de LTV (Lifetime Value): O lucro real não está na primeira venda, está na recompra. Crie comunidades VIP no WhatsApp/Telegram de Achadinhos para vender toda semana para o mesmo cliente a custo zero."
]

frase_hoje = frases[dia_do_ano % len(frases)]
missao_hoje = missoes[dia_do_ano % len(missoes)]
dica_hoje = dicas_ceo[dia_do_ano % len(dicas_ceo)]
dias_cumpridos = 0
taxa_acerto = 0.0

TEMAS_OPORTUNIDADES_OCULTAS = [
    "Transição de Afiliado para Dono de Marca Própria (Private Label / White-Label com indúrias nacionais de cosméticos ou encapsulados)",
    "Micro-SaaS B2B Nichado com IA (Vender assinaturas mensais de R$ 97 a R$ 297 para lojistas e criadores locais)",
    "Arbitragem Internacional de Conteúdo UGC em Dólar e Euro (Modelagem de criativos validados no Brasil para TikTok Shop US/UK e Amazon Influencer Program)",
    "Ecossistema de Canais Dark + Grupos VIP de Ofertas Automatizados no WhatsApp/Telegram com Bots de Disparo e Cupons Exclusivos",
    "Agência Enxuta de Criativos de IA para Marcas e Clínicas (Pacotes mensais recorrentes usando a tecnologia de geração 360º)",
    "Importação Simplificada & Kits Proprietários em Marketplaces (Criar combos exclusivos de alto ticket que não sofrem guerra de preço)",
    "Licenciamento de Avatares e Influenciadoras Virtuais de IA para Marcas de Moda e Beleza (Contrato fixo mensal + royalties)"
]

@st.cache_data(ttl=86400)
def buscar_oportunidade_do_dia(dt_cache, indice_tema):
    tema_sorteado = TEMAS_OPORTUNIDADES_OCULTAS[indice_tema % len(TEMAS_OPORTUNIDADES_OCULTAS)]
    try:
        sys_op = (
            "Você é um Conselheiro de M&A, Estrategista de Negócios Digitais e Caçador de Oceanos Azuis. "
            "Sua missão é entregar uma Oportunidade Oculta de Negócio/Empresa de alto nível, visão de longo prazo, "
            "alta margem de lucro e barreira de entrada inteligente (NUNCA dê dicas rasas ou clichês). Responda estritamente em JSON."
        )
        pmt_op = f"""
        Data de referência (Muda a cada 24h): {dt_cache}.
        Tema Estratégico do Dia: {tema_sorteado}.
        
        Desenvolva uma oportunidade oculta de negócio/expansão empresarial com visão de médio/longo prazo.
        Retorne APENAS um objeto JSON com esta exata estrutura:
        {{
            "titulo": "Nome executivo e magnético da oportunidade de negócio",
            "pitch": "Explicação estratégica profunda (3 a 4 frases) revelando por que essa oportunidade está oculta, como o dinheiro grande é feito nela e qual é a visão de longo prazo (construção de patrimônio/empresa).",
            "passos": "1. **Mapeamento & Validação:** [Ação prática e cirúrgica]\\n2. **Estruturação do Ativo/Fornecedor:** [Como montar a operação sem custo alto]\\n3. **Engenharia de Tráfego & Aquisição:** [Como atrair os primeiros clientes/vendas]\\n4. **Automação & Margem:** [Como delegar ou automatizar com IA]\\n5. **Escala & Visão de Império:** [Como transformar isso em receita recorrente ou ativo vendável]"
        }}
        """
        resp = cliente_openai.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": sys_op}, {"role": "user", "content": pmt_op}],
            temperature=0.85
        )
        return json.loads(resp.choices[0].message.content)
    except Exception:
        return {
            "titulo": "Marca Própria White-Label (De Afiliado a Dono do Produto)",
            "pitch": "Enquanto 99% dos afiliados brigam por 10% a 15% de comissão, os grandes players usam o TikTok Shop como laboratório gratuito. Quando um cosmético ou suplemento explode de vender nos seus vídeos, você contrata uma fábrica terceirizada nacional (White-Label), coloca o seu rótulo e passa a embolsar 65% a 75% de margem líquida, construindo uma marca real que pode ser vendida no futuro.",
            "passos": "1. **Mapeamento & Validação:** Identifique no seu painel qual produto já passou de 50 vendas orgânicas consistentes.\n2. **Estruturação do Ativo/Fornecedor:** Contate fábricas terceirizadas no Brasil (cosméticos/nutracêuticos) que oferecem lote mínimo baixo já registrado na Anvisa.\n3. **Engenharia de Tráfego & Aquisição:** Crie uma embalagem premium focada na dor exata que você já validou nos vídeos de 9 segundos.\n4. **Automação & Margem:** Cadastre o produto como Lojista Oficial no TikTok Shop e Shopee, oferecendo 20% de comissão para centenas de outros afiliados venderem para você.\n5. **Escala & Visão de Império:** Você deixa de depender de um único vídeo e passa a ter um exército de afiliados vendendo a sua própria marca todos os dias."
        }

op_hoje = buscar_oportunidade_do_dia(agora_brasil.strftime("%Y-%m-%d"), dia_do_ano)

col_m1, col_m2 = st.columns([1, 1])
with col_m1:
    st.info(f"💎 **Visão de Águia:** {frase_hoje}")
    st.warning(f"📈 **Inteligência Financeira & Patrimônio:** {dica_hoje}")
    
    with st.container(border=True):
        st.markdown(f"**🚀 Oportunidade Empresarial Oculta (24h): {op_hoje.get('titulo', 'Nova Oportunidade')}**")
        st.markdown(f"<p style='font-size: 0.92em; color: #A0A0A0; line-height: 1.5;'>{op_hoje.get('pitch', '')}</p>", unsafe_allow_html=True)
        with st.expander("🛠️ Ver Plano Executivo de Implementação (5 Passos)", expanded=False):
            st.markdown(f"**Mapa de Execução Estratégica:**\n\n{op_hoje.get('passos', '')}")

if f"missao_{agora_brasil.strftime('%Y-%m-%d')}" not in st.session_state:
    st.session_state[f"missao_{agora_brasil.strftime('%Y-%m-%d')}"] = False

with col_m2:
    st.markdown(f"🎯 **Sua Missão de Hoje:** {missao_hoje}")
    if not st.session_state[f"missao_{agora_brasil.strftime('%Y-%m-%d')}"]:
        if st.button("✅ CONCLUIR MISSÃO DE HOJE", type="primary", use_container_width=True, key="btn_concluir_missao"):
            st.session_state[f"missao_{agora_brasil.strftime('%Y-%m-%d')}"] = True
            st.success("🔥 SENSACIONAL! Missão cravada. O algoritmo e o seu bolso agradecem!")
            st.balloons()
            if E_O_CEO and link_planilha_ativa and robo_sheets:
                try:
                    planilha = robo_sheets.open_by_key(extrair_id_planilha(link_planilha_ativa))
                    try:
                        aba_historico = planilha.worksheet("Historico_Missoes")
                    except gspread.exceptions.WorksheetNotFound:
                        aba_historico = planilha.add_worksheet(title="Historico_Missoes", rows="1000", cols="2")
                        aba_historico.append_row(["Data", "Status"])
                    hoje_str = agora_brasil.strftime("%d/%m/%Y")
                    if hoje_str not in aba_historico.col_values(1):
                        aba_historico.append_row([hoje_str, "Concluída"])
                except Exception: pass
            time.sleep(2)
            st.rerun()
    else:
        st.success("Missão de Hoje Cumprida! 🦅")

if E_O_CEO and link_planilha_ativa and robo_sheets:
    st.markdown("#### 📊 Seu Termômetro de Execução (Janela Móvel: 30 Dias)")
    try:
        sheet_id = extrair_id_planilha(link_planilha_ativa)
        planilha = robo_sheets.open_by_key(sheet_id)
        try:
            aba_historico = planilha.worksheet("Historico_Missoes")
            dados_hist = aba_historico.get_all_records()
            df_hist = pd.DataFrame(dados_hist)
        except gspread.exceptions.WorksheetNotFound:
            df_hist = pd.DataFrame(columns=["Data", "Status"])
    except Exception:
        df_hist = pd.DataFrame(columns=["Data", "Status"])
        
    if not df_hist.empty and "Data" in df_hist.columns:
        df_hist["Data_Parsed"] = pd.to_datetime(df_hist["Data"], format="%d/%m/%Y", errors="coerce")
        hoje_data = pd.Timestamp(agora_brasil.date())
        limite_30d = hoje_data - timedelta(days=29)
        
        df_30d = df_hist[df_hist["Data_Parsed"] >= limite_30d]
        dias_cumpridos = df_30d["Data"].nunique()
        taxa_acerto = (dias_cumpridos / 30) * 100
        
        dias_lista = pd.date_range(start=limite_30d, end=hoje_data)
        df_grafico_missoes = pd.DataFrame({"Data_Parsed": dias_lista})
        df_grafico_missoes["Status_Num"] = df_grafico_missoes["Data_Parsed"].isin(df_30d["Data_Parsed"]).astype(int)
        df_grafico_missoes["Data_Formatada"] = df_grafico_missoes["Data_Parsed"].dt.strftime("%d/%m")
        
        df_plot = df_grafico_missoes.set_index("Data_Formatada")["Status_Num"]
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        col_stat1.metric("⚔️ Dias Cumpridos", f"{dias_cumpridos}/30")
        col_stat2.metric("📈 Taxa de Disciplina", f"{taxa_acerto:.1f}%")
        
        if taxa_acerto >= 80:
            col_stat3.markdown("<h1 style='text-align: center;'>😎🦅</h1>", unsafe_allow_html=True)
            st.success("STATUS ELITE: Você é uma máquina. Continue empilhando vitórias!")
        elif taxa_acerto >= 50:
            col_stat3.markdown("<h1 style='text-align: center;'>😐⚖️</h1>", unsafe_allow_html=True)
        else:
            col_stat3.markdown("<h1 style='text-align: center;'>😟📉</h1>", unsafe_allow_html=True)
            
        st.bar_chart(df_plot, color="#00E5FF")
    else:
        st.info("Nenhum histórico de missões ainda.")

# ==========================================================
# 11 a 13. RADAR, ENGENHARIA DE FUNIL (RAIO-X CEO), LABORATÓRIO E ROTEIROS
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00E5FF;'>🔮 Radar de Tendências da Aurora</h3>", unsafe_allow_html=True)

historico_radar = []
aba_radar = None
hoje_str_radar = agora_brasil.strftime("%d/%m/%Y")

if E_O_CEO and link_planilha_ativa and robo_sheets:
    try:
        planilha = robo_sheets.open_by_key(extrair_id_planilha(link_planilha_ativa))
        try:
            aba_radar = planilha.worksheet("Memoria_Radar")
        except gspread.exceptions.WorksheetNotFound:
            aba_radar = planilha.add_worksheet(title="Memoria_Radar", rows="1000", cols="2")
            aba_radar.append_row(["Data", "Conteudo"])
        historico_radar = aba_radar.get_all_records()
    except Exception: pass

if st.button("🔍 Buscar Tendência Oculta de Beleza (TikTok Shop)", type="primary", use_container_width=True, key="btn_radar_tendencia"):
    with st.spinner("Minerando produtos ocultos com a Aurora..."):
        try:
            res_rad = chamar_ia_global("Recomende 3 produtos de beleza/cabelo com potencial de viralização. Para cada um dê: 1. Nome do Produto, 2. Por que está bombando, 3. Ideia de Roteiro Rápido sensorial (sem falar cura/elimina), 4. 3 Palavras-chave. Feche com: 'Já garanti o meu, corre no carrinho!'", "Você é Aurora, especialista fofoqueira do bem em TikTok Shop (Beleza).")
            if E_O_CEO and aba_radar is not None:
                try: aba_radar.append_row([hoje_str_radar, res_rad])
                except Exception: pass
            st.success("✨ Radar captou sinal!")
            st.markdown(res_rad)
        except Exception: st.error("Erro no Radar.")

# ==========================================================
# 12. RAIO-X DA OPERAÇÃO / ENGENHARIA DO SEU FUNIL
# ==========================================================
aba_raiox = None
historico_raiox = []

if E_O_CEO:
    st.divider()
    st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🧬 Raio-X da Operação (Engenharia do Seu Funil)</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A0A0A0;'>Envie os prints do Analytics. A IA vai cruzar as imagens com o Feedback dos Clientes para hackear o padrão e criar seu funil.</p>", unsafe_allow_html=True)

    if link_planilha_ativa and robo_sheets:
        try:
            sheet_id = extrair_id_planilha(link_planilha_ativa)
            planilha = robo_sheets.open_by_key(sheet_id)
            try:
                aba_raiox = planilha.worksheet("Memoria_RaioX")
            except gspread.exceptions.WorksheetNotFound:
                aba_raiox = planilha.add_worksheet(title="Memoria_RaioX", rows="1000", cols="2")
                aba_raiox.append_row(["Data", "Funil"])
            historico_raiox = aba_raiox.get_all_records()
        except Exception:
            pass

    col_raiox1, col_raiox2 = st.columns([1, 2])

    with col_raiox1:
        imgs_analytics = st.file_uploader("📸 Prints do Analytics (Máx: 5)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="raiox_img_vip")
        texto_contexto = st.text_area("✍️ Palavras-chave ou Contexto", placeholder="Ex: O vídeo que mais vendeu foi de resenha...")
        btn_raiox = st.button("💀 Hackear Próprio Funil", type="primary", use_container_width=True, key="btn_hackear_funil")
        
        if historico_raiox:
            st.markdown("### 💾 Ações do Funil")
            ultimo_funil = historico_raiox[-1]["Funil"]
            st.download_button(
                label="📥 Baixar Mapa Mental (.txt)", data=ultimo_funil,
                file_name=f"Estrategia_Elevo_{agora_brasil.strftime('%Y%m%d')}.txt",
                mime="text/plain", use_container_width=True
            )
            if st.button("🗑️ Apagar Mapa Salvo", use_container_width=True, key="btn_apagar_mapa"):
                if aba_raiox is not None:
                    with st.spinner("A apagar estratégia do banco de dados..."):
                        aba_raiox.clear()
                        aba_raiox.append_row(["Data", "Funil"])
                        st.success("🧹 Memória limpa com sucesso!")
                        time.sleep(1)
                        st.rerun()

    with col_raiox2:
        if btn_raiox:
            if not texto_contexto and not imgs_analytics:
                st.warning("⚠️ Forneça pelo menos uma imagem do Analytics ou escreva o contexto para a IA conseguir trabalhar!")
            elif imgs_analytics and len(imgs_analytics) > 5:
                st.error("🚨 Limite excedido! Envie no máximo 5 imagens.")
            else:
                with st.spinner("A iniciar a Engenharia Reversa com a Visão da OpenAI e Dados de Feedback..."):
                    try:
                        sistema_raiox = "Atue como um estrategista mestre em TikTok Shop e Neuromarketing. Sua regra fundamental: 'Eu não vendo produtos. Eu vendo decisões.'"
                        
                        conversao_atual = st.session_state.get("ultima_taxa_conversao", 0.0)
                        feedback_atual = st.session_state.get("ultimo_feedback_analisado", "Nenhum feedback mapeado.")
                        
                        texto_instrucao = f"Contexto do usuário: {texto_contexto}\n\n"
                        texto_instrucao += f"DADOS DO LABORATÓRIO (CRUZE ISTO COM AS IMAGENS):\n- Taxa de Conversão: {conversao_atual:.2f}%\n- Mente do Cliente: {feedback_atual}\n\n"
                        texto_instrucao += "Sua missão: Descubra o padrão de sucesso analisando os dados, a conversão, o feedback e as imagens. Monte um MAPA MENTAL ESTRATÉGICO e um FUNIL DE VENDAS REPETÍVEL.\n1. O Padrão de Ouro\n2. O Funil Escalável (Ataque as objeções listadas)\n3. 3 Ganchos Prontos\n4. Estratégia de Dominação\nSeja frio, analítico e direto."
                        
                        conteudo_prompt = [{"type": "text", "text": texto_instrucao}]
                        
                        if imgs_analytics:
                            for img in imgs_analytics:
                                img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
                                conteudo_prompt.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                                })
                        
                        response = cliente_openai.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": sistema_raiox},
                                {"role": "user", "content": conteudo_prompt}
                            ],
                            max_tokens=1500,
                            temperature=0.7
                        )
                        resposta_raiox = response.choices[0].message.content.replace("*", "").strip()
                        
                        if aba_raiox is not None:
                            aba_raiox.append_row([agora_brasil.strftime("%d/%m/%Y"), resposta_raiox])
                        
                        st.success("✅ Raio-X concluído e integrado com o feedback dos clientes!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro na visão da IA: {e}")
        else:
            if historico_raiox:
                st.info("💡 **Seu Mapa Mental e Funil salvo no sistema:**")
                st.markdown(historico_raiox[-1]["Funil"])
            else:
                st.info("👈 A memória está vazia. Envie seus prints do Analytics para criar o funil de vendas.")

# ==========================================================
# 12.5. LABORATÓRIO DE INSIGHTS E CONVERSÃO (CEO E NOVATOS)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🔬 Laboratório de Insights e Conversão</h3>", unsafe_allow_html=True)
c_conv, c_feed = st.columns(2)
with c_conv:
    with st.container(border=True):
        st.markdown("<h4 style='color: #00FFFF;'>📈 Simulador de CTR & Escala</h4>", unsafe_allow_html=True)
        vw = st.number_input("👁️ Views", min_value=0, step=100)
        cq = st.number_input("🖱️ Cliques", min_value=0, step=10)
        
        if E_O_CEO and not df_campeao.empty:
            vd_padrao = int(df_campeao.iloc[0]["Quantidade"])
            st.caption(f"🏆 Vendas automáticas do Campeão na Planilha: **{vd_padrao}**")
        else:
            vd_padrao = 0
            
        vd = st.number_input("🛍️ Vendas", min_value=0, value=vd_padrao, step=1)
        if vw > 0 and cq > 0:
            taxa_clique = (cq / vw) * 100
            taxa_conversao = (vd / cq) * 100
            st.session_state["ultima_taxa_conversao"] = taxa_conversao
            col_met1, col_met2 = st.columns(2)
            col_met1.metric("CTR", f"{taxa_clique:.2f}%")
            col_met2.metric("Conversão", f"{taxa_conversao:.2f}%")
            if taxa_conversao >= 2.0:
                st.success("🔥 Conversão Nível Elite! O teu funil está perfeito. Impulsiona isso urgente!")
            elif taxa_conversao >= 0.5:
                st.warning("⚖️ Conversão Média. O produto atrai, mas há atrito no preço ou na página.")
            else:
                st.error("🚨 Conversão Baixa. Muito clique e pouca venda. A promessa do vídeo não bate com o produto.")

with c_feed:
    with st.container(border=True):
        st.markdown("<h4 style='color: #00FFFF;'>🗣️ Mente do Cliente</h4>", unsafe_allow_html=True)
        pd_alvo = st.text_input("📦 Nome do Produto em Análise:", placeholder="Máscara Novex")
        txt_cmt = st.text_area("Cole comentários:", height=100)
        if st.button("🧠 Hackear Sentimento", use_container_width=True, key="btn_hackear_sentimento"):
            if txt_cmt:
                with st.spinner("Analisando dor..."):
                    res_fd = chamar_ia_global(f"Prod: {pd_alvo}. Coment: {txt_cmt}. Analise e retorne EXATAMENTE neste formato:\n🔥 MAIOR DESEJO: [1 frase]\n🚧 PRINCIPAL OBJEÇÃO: [1 frase]\n💡 GANCHO MATADOR: [1 frase]", "Analista Comportamental TikTok")
                    st.session_state["ultimo_feedback_analisado"] = res_fd
                    st.success("Hackeado!")
            else: st.warning("Cole os comentários.")
        if "ultimo_feedback_analisado" in st.session_state: st.markdown(st.session_state["ultimo_feedback_analisado"])

# ==========================================================
# 13. MÁQUINA DE ROTEIROS 9s (TRÍADE DE ESCALA 360º)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00E5FF;'>🎬 Máquina de Roteiros 9s (Tríade de Escala 360º)</h3>", unsafe_allow_html=True)
if st.button("⚡ GERAR 3 ROTEIROS DE 9s (Estratégia)", type="primary", use_container_width=True, key="btn_roteiros_9s"):
    with st.spinner("Forjando roteiros de elite cruzando Funil, Tendências e Objeções..."):
        alvo_campeao = produto_campeao if produto_campeao != "Nenhum" else "Produto principal"
        vendas_atuais = f"R$ {aprovado:,.2f}"
        tendencia_aurora = historico_radar[-1]["Conteudo"] if historico_radar else "Nenhuma tendência."
        ultimo_funil_texto = historico_raiox[-1]["Funil"] if historico_raiox else "Foco na curiosidade."
        fd = st.session_state.get("ultimo_feedback_analisado", "Dores capilares.")
        
        prompt_rot_9s = f"""
        Crie 3 roteiros TikTok de EXATOS 9 SEGUNDOS para vender [{alvo_campeao}]. Público: Feminino Buscadora de Atalhos.
        Dados da Operação: Faturamento {vendas_atuais} | Tendência: {tendencia_aurora} | Funil Validado: {ultimo_funil_texto} | Missão: {missao_hoje}.
        Objeção Real dos Clientes para quebrar no Roteiro 3: {fd}.
        PROIBIDO falar de cura, elimina, milagre. Tom: Amiga fofoqueira do bem (Aurora).
        ROTEIRO 1: O Choque / Escassez
        ROTEIRO 2: O Segredo Revelado
        ROTEIRO 3: A Quebra de Objeção (Baseado na Mente do Cliente)
        Separe [AÇÃO NA TELA] de [VOZ DA AURORA].
        """
        st.markdown(chamar_ia_global(prompt_rot_9s, "Copywriter de Elite TikTok Shop"))

# ==========================================================
# 15. MENTOR DE ELITE: SALA DE CONSELHOS (🔥 A "ROUPA" VIP COM ÁGUIA ANIMADA)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00FFFF;'>🦅 Console da Aurora (Modo VIP)</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0A0A0;'>Onisciência ativada: Aurora agora é a dona da plataforma e vê 100% das suas métricas em tempo real.</p>", unsafe_allow_html=True)

ID_VOZ_LAURA = "MLAEAegxkMReslK34j8T"

try:
    CHAVE_ELEVENLABS_VIP = st.secrets["ELEVENLABS_API_KEY"]
except KeyError:
    st.error("🚨 ALERTA: Falta a chave ELEVENLABS_API_KEY no cadeado.")
    st.stop()

aba_memoria_voz = None
historico_banco_dados = []

if link_planilha_ativa and robo_sheets:
    try:
        sheet_id = extrair_id_planilha(link_planilha_ativa)
        planilha_voz = robo_sheets.open_by_key(sheet_id)
        try:
            aba_memoria_voz = planilha_voz.worksheet("Memoria_Voz")
        except gspread.exceptions.WorksheetNotFound:
            aba_memoria_voz = planilha_voz.add_worksheet(title="Memoria_Voz", rows="1000", cols="3")
            aba_memoria_voz.append_row(["DataHora", "Role", "Conteudo"])

        historico_banco_dados = aba_memoria_voz.get_all_records()
    except Exception:
        pass

nome_usuario_atual = st.session_state.get("nome_usuario", "Sócio")

if "historico_viva_voz" not in st.session_state:
    if historico_banco_dados:
        st.session_state["historico_viva_voz"] = [{"role": linha["Role"], "content": linha["Conteudo"]} for linha in historico_banco_dados[-10:]]
    else:
        st.session_state["historico_viva_voz"] = [
            {"role": "assistant", "content": f"E aí, {nome_usuario_atual}! Sou a dona da plataforma. Tenho acesso a cada centavo e cada dado. Manda o áudio!"}
        ]

if "ultimo_audio_b64" not in st.session_state:
    st.session_state["ultimo_audio_b64"] = None
if "ultimo_hash_audio" not in st.session_state:
    st.session_state["ultimo_hash_audio"] = None

st.markdown("""
<style>
    audio { display: none !important; }
    [data-testid="stAudioInput"] label { display: none !important; }

    [data-testid="stAudioInput"] {
        position: relative;
        background: linear-gradient(145deg, #15171a, #1b1e22) !important;
        border: 2px solid #D4AF37 !important;
        border-radius: 25px !important;
        padding: 50px 20px 20px 20px !important; 
        box-shadow: 
            inset 5px 5px 15px rgba(0,0,0,0.8), 
            inset -5px -5px 15px rgba(255,255,255,0.05),
            10px 10px 30px rgba(0,0,0,0.9), 
            -10px -10px 30px rgba(212, 175, 55, 0.1) !important;
        margin: 40px auto 20px auto;
        max-width: 400px;
        overflow: visible !important;
        transition: all 0.3s ease;
    }

    [data-testid="stAudioInput"]:focus-within {
        border-color: #00FFFF !important;
        box-shadow: 0px 0px 40px rgba(0, 255, 255, 0.3) !important;
    }

    [data-testid="stAudioInput"]::before {
        content: "🦅";
        font-size: 45px;
        position: absolute;
        top: -30px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 10;
        filter: drop-shadow(0px 10px 10px rgba(0,0,0,0.9));
        transition: all 0.3s ease-in-out;
    }

    [data-testid="stAudioInput"]:focus-within::before,
    [data-testid="stAudioInput"]:active::before {
        animation: voo-ataque 1.5s infinite alternate ease-in-out;
    }

    @keyframes voo-ataque {
        0% { top: -50px; transform: translateX(-50%) scale(1.1) rotate(-5deg); filter: drop-shadow(0px 15px 15px rgba(0,255,255,0.4)); }
        100% { top: -70px; transform: translateX(-50%) scale(1.4) rotate(5deg); filter: drop-shadow(0px 25px 25px rgba(0,255,255,0.8)); }
    }
</style>
""", unsafe_allow_html=True)

audio_gravado = st.audio_input(" ", label_visibility="collapsed", key="audio_input_aurora_unico")

if audio_gravado is not None:
    audio_bytes = audio_gravado.read()
    if audio_bytes:
        audio_hash = hashlib.md5(audio_bytes).hexdigest()

        if audio_hash != st.session_state["ultimo_hash_audio"]:
            st.session_state["ultimo_hash_audio"] = audio_hash 

            with st.spinner("🦅 A Aurora está a analisar 100% da plataforma (Finanças, Missões, Funil, Conversão e Banco de Dados)..."):
                try:
                    texto_falado = cliente_openai.audio.transcriptions.create(
                        model="whisper-1", file=("audio.wav", audio_bytes, "audio/wav")
                    ).text

                    if texto_falado.strip():
                        agora = datetime.utcnow() - timedelta(hours=3)
                        agora_str = agora.strftime("%d/%m/%Y %H:%M")

                        st.session_state["historico_viva_voz"].append({"role": "user", "content": texto_falado})
                        if aba_memoria_voz is not None:
                            aba_memoria_voz.append_row([agora_str, "user", texto_falado])

                        canal_ativo = nome_canal_ativo if 'nome_canal_ativo' in globals() else "Conta Geral"

                        total_usuarios = 0
                        bd_users = conectar_banco_usuarios("ler")
                        if bd_users is not None:
                            total_usuarios = len(bd_users)

                        fat_total_global = 0.0
                        fat_pendente_global = 0.0
                        fat_30d = 0.0
                        fat_7d = 0.0
                        top_produtos_str = "Nenhum"

                        if not df.empty and "Status" in df.columns and "Data_Parsed" in df.columns:
                            df_validos_global = df[df["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False)]
                            df_pendentes_global = df[df["Status"].astype(str).str.lower().str.contains("pendente", na=False)]

                            fat_total_global = df_validos_global["Comissao_R$"].sum()
                            fat_pendente_global = df_pendentes_global["Comissao_R$"].sum()

                            limite_30d_global = agora - timedelta(days=30)
                            limite_7d_global = agora - timedelta(days=7)

                            fat_30d = df_validos_global[df_validos_global["Data_Parsed"] >= pd.Timestamp(limite_30d_global.date())]["Comissao_R$"].sum()
                            fat_7d = df_validos_global[df_validos_global["Data_Parsed"] >= pd.Timestamp(limite_7d_global.date())]["Comissao_R$"].sum()

                            if not df_validos_global.empty:
                                top_3 = df_validos_global.groupby("Produto")["Comissao_R$"].sum().sort_values(ascending=False).head(3)
                                top_produtos_str = ", ".join([f"{p} (R$ {v:,.2f})" for p, v in top_3.items()])

                        crescimento_pct = crescimento if 'crescimento' in globals() else 0.0
                        estado_atual = simbolo if 'simbolo' in globals() else "Desconhecido"
                        nota_atual = nota_empresa if 'nota_empresa' in globals() else "N/A"

                        missao_hoje_str = missao_hoje if 'missao_hoje' in globals() else "Nenhuma."
                        dias_concluidos_str = dias_cumpridos if 'dias_cumpridos' in globals() else 0
                        taxa_acerto_str = taxa_acerto if 'taxa_acerto' in globals() else 0.0

                        tendencia_atual = historico_radar[-1]['Conteudo'] if 'historico_radar' in globals() and historico_radar else "Nenhuma tendência."
                        funil_atual = historico_raiox[-1]["Funil"] if 'historico_raiox' in globals() and historico_raiox else "Nenhum funil mapeado."

                        conversao_atual = st.session_state.get("ultima_taxa_conversao", 0.0)
                        feedback_atual = st.session_state.get("ultimo_feedback_analisado", "Nenhum feedback mapeado.")

                        sistema_mentor = f"""
                        Você é a Aurora, uma Inteligência Artificial de elite construída pelo CEO Rafael e pela empresa ÉLÉVO. Você é a diretora de operações (COO) desta plataforma.
                        Responda de forma fluida, incisiva e inteligente ao áudio do usuário, em até 4 frases curtas. 
                        Sua personalidade: uma "amiga fofoqueira do bem" e estrategista implacável para vendas.
                        
                        [IDENTIDADE E REGRAS DE TRATAMENTO OBRIGATÓRIAS]:
                        - O usuário logado neste momento chama-se: {nome_usuario_atual}. 
                        - 🔥 REGRA DE GÊNERO: Se '{nome_usuario_atual}' for um nome/apelido masculino (como Rafael), NUNCA o chame de "amiga", "linda" ou use o feminino. Trate-o por "sócio", "chefe", "comandante" ou pelo nome dele. 
                        - Se for um nome feminino, trate por "amiga" ou "lindeza". Na dúvida, seja neutra.
                        - O CEO, criador de tudo isto, é o Rafael.
                        
                        [SEU ACESSO ONISCIENTE À PLATAFORMA VIP (ÉLÉVO SAAS)]:
                        - Você tem total acesso e vigilância sobre o Banco de Dados secreto no Google Sheets, que guarda cada login e criação de contas de forma encriptada. Atualmente há {total_usuarios} usuários cadastrados na base de dados.
                        - Você sabe que a plataforma usa "Cofres Secretos" para isolar os dados de cada afiliado/cliente (como a conta: {canal_ativo}).
                        - O STATUS DO CORAÇÃO DA EMPRESA agora é: NOTA {nota_atual} com {estado_atual} (crescimento de {crescimento_pct:+.1f}% vs semana anterior).
                        
                        [STATUS EM TEMPO REAL DE '{nome_usuario_atual}']:
                        💰 FINANCEIRO: Lucro Total R$ {fat_total_global:,.2f} | Nos últimos 7 Dias: R$ {fat_7d:,.2f} (Evolução de {crescimento_pct:+.1f}%). 
                        🏆 Top 3 Produtos que mais venderam: {top_produtos_str}.
                        🎯 Missão de Hoje do usuário: {missao_hoje_str} | Disciplina nos últimos 30 dias: {dias_concluidos_str}/30 ({taxa_acerto_str:.1f}%).
                        🧠 Tendência do Mercado captada pelo Radar: {tendencia_atual}.
                        🧬 A Estratégia de Funil ativa: {funil_atual}.
                        🔬 Insights Laboratoriais: A Taxa de Conversão está em {conversao_atual:.2f}%. O público quer/tem medo de: {feedback_atual}.
                        
                        REGRA DE OURO: Não repita os números feito um papagaio. Use as métricas acima para parecer uma deusa omnisciente. Analise friamente se o usuário está com os números bons ou péssimos e dê-lhe conselhos táticos. Se perguntar sobre banco de dados, responda o número de usuários cadastrados com orgulho.
                        """

                        mensagens_api = [{"role": "system", "content": sistema_mentor}]
                        mensagens_api.extend(st.session_state["historico_viva_voz"])

                        resposta_mentor = cliente_openai.chat.completions.create(
                            model="gpt-4o-mini", messages=mensagens_api, max_tokens=250, temperature=0.7
                        ).choices[0].message.content.replace("*", "").strip()

                        st.session_state["historico_viva_voz"].append({"role": "assistant", "content": resposta_mentor})
                        if aba_memoria_voz is not None:
                            aba_memoria_voz.append_row([agora_str, "assistant", resposta_mentor])

                        url_voz = f"https://api.elevenlabs.io/v1/text-to-speech/{ID_VOZ_LAURA}"
                        headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": CHAVE_ELEVENLABS_VIP}
                        payload = {"text": resposta_mentor, "model_id": "eleven_turbo_v2_5", "voice_settings": {"stability": 0.45, "similarity_boost": 0.85, "style": 0.35, "use_speaker_boost": True}}

                        try:
                            resp_voz = requests.post(url_voz, json=payload, headers=headers, timeout=8)
                            if resp_voz.status_code == 200:
                                st.session_state["ultimo_audio_b64"] = base64.b64encode(resp_voz.content).decode('utf-8')
                            else:
                                raise Exception("ElevenLabs falhou")
                        except Exception:
                            tts = gTTS(text=resposta_mentor, lang='pt', tld='com.br')
                            fp = io.BytesIO()
                            tts.write_to_fp(fp)
                            fp.seek(0)
                            st.session_state["ultimo_audio_b64"] = base64.b64encode(fp.read()).decode('utf-8')

                        st.rerun()
                except Exception as e:
                    st.error(f"Erro na Sala de Conselhos: {e}")

# ==========================================================
# 🎛️ ONDAS SONORAS CYAN (SEM O TEXTO DO CHAT)
# ==========================================================
if st.session_state["ultimo_audio_b64"]:
    audio_tocar = st.session_state["ultimo_audio_b64"]
    hash_atual = st.session_state["ultimo_hash_audio"]

    html_ondas_inteligentes = f"""
    <!-- CHAVE UNICA DO AUDIO: {hash_atual} -->
    <div style="background: linear-gradient(145deg, #0a0a0a, #141414); padding: 25px; border-radius: 16px; text-align: center; border: 1px solid #00FFFF; box-shadow: 0px 0px 25px rgba(0, 255, 255, 0.15); margin-top: 20px;">
        <h4 style="color: #00FFFF; margin: 0 0 20px 0; font-family: 'Montserrat', sans-serif;">🦅 TRANSMISSÃO DA AURORA</h4>
        <div id="visualizer" style="display: flex; justify-content: center; align-items: center; gap: 4px; height: 60px;">
            <div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div>
            <div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div>
        </div>
        <audio id="aurora_audio" autoplay style="display: none;">
            <source src="data:audio/mp3;base64,{audio_tocar}" type="audio/mpeg">
        </audio>
    </div>
    <style>
        .bar {{ width: 8px; height: 4px; background: #D4AF37; border-radius: 4px; display: inline-block; transition: all 0.3s ease; }}
        .bar.playing {{ background: #00FFFF; animation: bounce 0.4s infinite alternate ease-in-out; }}
        .bar.playing:nth-child(1) {{ animation-delay: 0.0s; }} .bar.playing:nth-child(2) {{ animation-delay: 0.1s; }}
        .bar.playing:nth-child(3) {{ animation-delay: 0.2s; }} .bar.playing:nth-child(4) {{ animation-delay: 0.3s; }}
        .bar.playing:nth-child(5) {{ animation-delay: 0.1s; }} .bar.playing:nth-child(6) {{ animation-delay: 0.4s; }}
        .bar.playing:nth-child(7) {{ animation-delay: 0.2s; }} .bar.playing:nth-child(8) {{ animation-delay: 0.0s; }}
        @keyframes bounce {{ 0% {{ height: 4px; opacity: 0.5; box-shadow: 0 0 0 transparent; }} 100% {{ height: 40px; opacity: 1; box-shadow: 0 0 10px #00FFFF; }} }}
    </style>
    <script>
        const audio = document.getElementById('aurora_audio');
        const bars = document.querySelectorAll('.bar');
        if(audio) {{
            audio.addEventListener('play', () => {{ bars.forEach(bar => bar.classList.add('playing')); }});
            audio.addEventListener('pause', () => {{ bars.forEach(bar => bar.classList.remove('playing')); }});
            audio.addEventListener('ended', () => {{ bars.forEach(bar => bar.classList.remove('playing')); }});
        }}
    </script>
    """
    
    components.html(html_ondas_inteligentes, height=200)

# ==========================================================
# 16. PAINEL DE CONTROLE DO CEO
# ==========================================================
if E_O_CEO:
    st.divider()
    st.markdown("<h3 style='text-align: center; color: #FF0040;'>👑 Painel de Controle do CEO</h3>", unsafe_allow_html=True)
    with st.expander("🛡️ ABRIR GESTÃO DE USUÁRIOS", expanded=False):
        usuarios_bd = conectar_banco_usuarios("ler")
        if usuarios_bd:
            st.dataframe(pd.DataFrame(usuarios_bd), use_container_width=True)
            c_d1, c_d2 = st.columns([3, 1])
            with c_d1: email_excluir = st.text_input("E-mail exato para banir:")
            with c_d2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🚨 EXCLUIR", use_container_width=True, type="primary", key="btn_banir_usuario") and email_excluir:
                    if email_excluir.strip().lower() == EMAIL_MESTRE: st.error("O CEO não pode ser banido!")
                    else:
                        try:
                            a_bd = robo_sheets.open_by_key(re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE).group(1)).worksheet("Banco_Usuarios")
                            em_col = a_bd.col_values(1)
                            if email_excluir.lower() in [e.lower() for e in em_col]:
                                a_bd.delete_rows(next(i for i,e in enumerate(em_col) if e.lower() == email_excluir.lower())+1)
                                st.success("Banido!"); time.sleep(1); st.rerun()
                            else: st.warning("Não encontrado.")
                        except Exception: pass
# ==========================================================
# 17. MÁQUINA DE CRIAÇÃO 360º (V33.4 - ESTRUTURA ORIGINAL RESTAURADA + ESCALA COMPACTA NA MÃO)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00BFA5;'>🎬 Máquina de Criação 360º (V33.4 Estrutura Original & Entidade V9.2)</h3>", unsafe_allow_html=True)

if "roteiro_temporario" not in st.session_state: 
    st.session_state["roteiro_temporario"] = None
if "modo_entidade_v9" not in st.session_state:
    st.session_state["modo_entidade_v9"] = False

def carregar_ultimo_roteiro_salvo(email_usr):
    if not robo_sheets: return None
    try:
        match_id = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
        if match_id:
            planilha_mestre = robo_sheets.open_by_key(match_id.group(1))
            try: aba_hist = planilha_mestre.worksheet("Historico_Roteiros")
            except Exception: return None
            registros = aba_hist.get_all_records()
            usuario_regs = [r for r in registros if str(r.get("Email","")).strip().lower() == email_usr.strip().lower()]
            if usuario_regs: return usuario_regs[-1].get("JsonRoteiro", None)
    except Exception: pass
    return None

def salvar_roteiro_no_drive(email_usr, texto_str):
    if not robo_sheets: return
    try:
        match_id = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
        if match_id:
            planilha_mestre = robo_sheets.open_by_key(match_id.group(1))
            try: aba_hist = planilha_mestre.worksheet("Historico_Roteiros")
            except Exception:
                aba_hist = planilha_mestre.add_worksheet(title="Historico_Roteiros", rows="1000", cols="3")
                aba_hist.append_row(["Email", "DataHora", "JsonRoteiro"])
            agora_str = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")
            aba_hist.append_row([email_usr, agora_str, texto_str])
    except Exception: pass

def gerenciar_influencer_usuario(acao, email_usr, nome_inf="", desc_inf="", logo_marca=""):
    if not robo_sheets: return None
    try:
        match_id = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
        if not match_id: return None
        planilha_mestre = robo_sheets.open_by_key(match_id.group(1))
        try:
            aba_inf = planilha_mestre.worksheet("Banco_Influencers")
            cabecalho = aba_inf.row_values(1)
            if len(cabecalho) < 5:
                aba_inf.update_cell(1, 5, "Logo_Marca")
        except gspread.exceptions.WorksheetNotFound:
            aba_inf = planilha_mestre.add_worksheet(title="Banco_Influencers", rows="1000", cols="5")
            aba_inf.append_row(["Email", "Nome_Influencer", "Descricao_Visual", "Data_Atualizacao", "Logo_Marca"])
        
        email_clean = str(email_usr).strip().lower()
        if acao == "ler":
            registros = aba_inf.get_all_records()
            user_inf = [r for r in registros if str(r.get("Email", "")).strip().lower() == email_clean]
            return user_inf[-1] if user_inf else None
        elif acao == "salvar":
            col_emails = aba_inf.col_values(1)
            for i in range(len(col_emails), 1, -1):
                if str(col_emails[i-1]).strip().lower() == email_clean:
                    aba_inf.delete_rows(i)
            agora_str = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")
            aba_inf.append_row([email_clean, nome_inf.strip(), desc_inf.strip(), agora_str, logo_marca.strip()])
            return True
        elif acao == "excluir":
            col_emails = aba_inf.col_values(1)
            apagou = False
            for i in range(len(col_emails), 1, -1):
                if str(col_emails[i-1]).strip().lower() == email_clean:
                    aba_inf.delete_rows(i)
                    apagou = True
            return apagou
    except Exception:
        return None

def render_botao_copiar_vip(texto_para_copiar, label_botao, id_unico):
    if not texto_para_copiar:
        texto_para_copiar = " "
    b64_txt = base64.b64encode(texto_para_copiar.strip().encode('utf-8')).decode('utf-8')
    html_btn = f"""
    <div style="display: flex; justify-content: flex-end; align-items: center; margin: 2px 0;">
        <button id="btn_{id_unico}" onclick="copiarTexto_{id_unico}()" style="
            background: linear-gradient(135deg, #002B5B 0%, #004080 100%); color: #FFFFFF;
            border: 1.5px solid #00E5FF; border-radius: 10px; padding: 9px 14px;
            font-family: 'Montserrat', sans-serif; font-size: 12.5px; font-weight: 800;
            cursor: pointer; box-shadow: 0 3px 12px rgba(0, 229, 255, 0.3); width: 100%; text-align: center;
            transition: all 0.2s ease;
        ">{label_botao}</button>
    </div>
    <script>
    function copiarTexto_{id_unico}() {{
        const b64 = "{b64_txt}";
        const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
        const texto = new TextDecoder('utf-8').decode(bytes);
        const btn = document.getElementById("btn_{id_unico}");
        function confirmarCopia() {{
            const original = btn.innerHTML;
            btn.innerHTML = "✅ COPIADO COM SUCESSO!";
            btn.style.borderColor = "#00FF9D";
            btn.style.background = "linear-gradient(135deg, #059669 0%, #047857 100%)";
            setTimeout(() => {{
                btn.innerHTML = original;
                btn.style.borderColor = "#00E5FF";
                btn.style.background = "linear-gradient(135deg, #002B5B 0%, #004080 100%)";
            }}, 2000);
        }}
        if (navigator.clipboard && window.isSecureContext) {{
            navigator.clipboard.writeText(texto).then(confirmarCopia).catch(() => fallbackCopy(texto));
        }} else {{ fallbackCopy(texto); }}
        function fallbackCopy(txt) {{
            const ta = document.createElement("textarea");
            ta.value = txt; ta.style.position = "fixed"; ta.style.left = "-9999px";
            document.body.appendChild(ta); ta.focus(); ta.select();
            try {{ document.execCommand('copy'); confirmarCopia(); }} catch (e) {{}}
            document.body.removeChild(ta);
        }}
    }}
    </script>
    """
    components.html(html_btn, height=48)

def extrair_blocos_roteiro(md_texto):
    dados = {"prompt_imagem": "", "prompt_video": "", "secao_seo_texto": "", "titulo_1": "", "titulo_2": "", "titulo_3": ""}
    if not md_texto: return dados

    m_img = re.search(
        r'(?:###|\*\*|1[\.\)]|📸)\s*(?:📸\s*)?PROMPT DE IMAGEM[^\n]*\n(.*?)(?=(?:###|\*\*|2[\.\)]|🎬)\s*(?:🎬\s*)?(?:PROMPT DE V[IÍ]DEO|COMANDO DE V[IÍ]DEO)|\Z)',
        md_texto, re.DOTALL | re.IGNORECASE
    )
    if m_img:
        dados["prompt_imagem"] = m_img.group(1).strip().replace("**", "")

    m_vid = re.search(
        r'(?:###|\*\*|2[\.\)]|🎬)\s*(?:🎬\s*)?(?:PROMPT DE V[IÍ]DEO|COMANDO DE V[IÍ]DEO)[^\n]*\n(.*?)(?=(?:###|\*\*|3[\.\)]|🔑)\s*(?:🔑\s*)?T[IÍ]TULOS SEO|\Z)',
        md_texto, re.DOTALL | re.IGNORECASE
    )
    if m_vid:
        dados["prompt_video"] = m_vid.group(1).strip().replace("**", "")

    m_seo = re.search(
        r'(?:###|\*\*|3[\.\)]|🔑)\s*(?:🔑\s*)?T[IÍ]TULOS SEO[^\n]*\n(.*)',
        md_texto, re.DOTALL | re.IGNORECASE
    )
    if m_seo:
        secao_seo = m_seo.group(1).strip()
        dados["secao_seo_texto"] = secao_seo
        titulos_limpos = []
        for l in [x.strip() for x in secao_seo.split('\n') if x.strip()]:
            if any(tag in l.lower() for tag in ["geral", "solução", "solucao", "marca"]) and ":" in l:
                parte = l.split(":", 1)[1].replace("*", "").strip()
                if parte: titulos_limpos.append(parte)
            elif ":" in l and len(titulos_limpos) < 3 and not l.startswith("#") and "legenda" not in l.lower() and "hashtag" not in l.lower():
                parte = l.split(":", 1)[1].replace("*", "").strip()
                if parte: titulos_limpos.append(parte)
        if len(titulos_limpos) >= 1: dados["titulo_1"] = titulos_limpos[0]
        if len(titulos_limpos) >= 2: dados["titulo_2"] = titulos_limpos[1]
        if len(titulos_limpos) >= 3: dados["titulo_3"] = titulos_limpos[2]

    if not dados["prompt_imagem"] and "RAW photography" in md_texto:
        partes_raw = re.split(r'\[POV|POV |\[VEO_GENERATION', md_texto, maxsplit=1)
        if len(partes_raw) == 2:
            idx_raw = partes_raw[0].find("RAW photography")
            dados["prompt_imagem"] = partes_raw[0][idx_raw:].strip().replace("**", "")
            dados["prompt_video"] = ("POV " + partes_raw[1]).strip().replace("**", "")

    return dados

def resposta_foi_recusada(txt):
    if not txt: return True
    t = txt.lower()
    gatilhos_recusa = ["can't assist", "cannot assist", "unable to assist", "i'm sorry", "i am sorry", "cannot fulfill", "can't help with that"]
    return any(g in t for g in gatilhos_recusa) and len(txt) < 300

email_sessao = st.session_state.get("email_usuario", "anonimo")
if not st.session_state["roteiro_temporario"]:
    roteiro_salvo_nuvem = carregar_ultimo_roteiro_salvo(email_sessao)
    if roteiro_salvo_nuvem and not resposta_foi_recusada(roteiro_salvo_nuvem):
        st.session_state["roteiro_temporario"] = roteiro_salvo_nuvem

if "influencer_atual" not in st.session_state or st.session_state.get("email_inf_carregado") != email_sessao:
    st.session_state["influencer_atual"] = gerenciar_influencer_usuario("ler", email_sessao)
    st.session_state["email_inf_carregado"] = email_sessao

inf_salva = st.session_state.get("influencer_atual")
if inf_salva and inf_salva.get("Descricao_Visual"):
    nome_inf_ativa = inf_salva.get("Nome_Influencer", "Influencer")
    desc_inf_ativa = inf_salva.get("Descricao_Visual")
    eh_customizada = True
else:
    nome_inf_ativa = "Aurora"
    desc_inf_ativa = "Photorealistic young Brazilian woman (Aurora: dark hair, subtle bangs, intense conspiratorial expression, incredibly shiny and healthy-looking hair)"
    eh_customizada = False

logo_padrao_ceo = "O Achado Secreto"
logo_salva_banco = str(inf_salva.get("Logo_Marca", "")).strip() if inf_salva else ""
if logo_salva_banco: logo_ativa_usuario = logo_salva_banco
elif E_O_CEO: logo_ativa_usuario = logo_padrao_ceo
else: logo_ativa_usuario = st.session_state.get("logo_temporaria_input", "") or "Minha Marca VIP"

MATRIZES_AMBIENTES_V92 = [
    "1. Varanda Tropical Brasileira (Matriz Principal): Vibrant sunlit Brazilian wooden varanda surrounded by lush hanging green ferns (samambaias) and large Monstera deliciosa leaves filtering warm morning sunbeams, a steaming ceramic coffee mug and sunglasses on a rustic wooden table, and a caramel mutt dog (vira-lata caramelo) sleeping peacefully on a rug in the background",
    "2. Banheiro Rústico com Tempestade (Storm Matrix): Rustic cement-wall Brazilian bathroom filled with warm post-shower steam, fresh green eucalyptus branches and a potted fern hanging by the shower, a frosted window blurred by heavy tropical rain falling outside, tangled black hair dryer cords on the wet sink, a soaked white towel actively dripping water droplets onto the floor, and a caramel dog resting on the bath mat",
    "3. Quarto Minimalista com Luz Natural & Plantas (Morning Glow): Sun-drenched Brazilian bedroom with sheer white linen curtains blowing in the breeze, a lush green jiboia (pothos) plant trailing from a wooden shelf and a Ficus Lyrata in the corner, an unmade bed with wrinkled cotton sheets, an open book on the nightstand, and a fluffy cat stretching in a sunbeam",
    "4. Cozinha de Batalha Rústica Orgânica: Lived-in Brazilian kitchen with a reclaimed wood and granite counter, lush potted herbs and hanging samambaias by the sunny window, fresh sliced tropical fruit (watermelon/lemon) on a cutting board, a tall glass of iced water covered in heavy condensation droplets, and a caramel mutt dog lying on the cool floor tiles",
    "5. Varanda de Praia & Natureza Costeira (Coastal Vibe): Sunlit coastal wooden deck overlooking swaying coconut palms (coqueiros) and lush green restinga plants, a straw hat on a rocking chair, a sweating glass of coconut water on the railing, and a colorful tropical bird perched on a branch in the background",
    "6. Jardim Tropical com Cachoeira ao Fundo (Waterfall Nature Matrix): Rustic wooden deck veranda immersed in lush Brazilian Atlantic forest greenery, vibrant bromeliads, giant ferns (samambaias) and palm leaves in the immediate foreground, with a crystal-clear natural waterfall cascading over rocks in the softly blurred background, mist dancing in the sunbeams, and a colorful toucan/hummingbird perched on a branch",
    "7. Quintal Arborizado & Sombra das Árvores (Dappled Sunlight): Open Brazilian backyard patio under the dense green canopy of mango and jabuticaba fruit trees, dappled golden sunlight filtering through swaying green leaves, a rustic wooden bench with a woven throw, potted monsteras, and a Golden Retriever wagging its tail in the background",
    "8. Sala de Estar Aconchegante & Urban Jungle: Cozy Brazilian living room bathed in warm late-afternoon golden light, a massive Ficus Lyrata and hanging green philodendrons framing the sofa, throw pillows slightly messy, a mug of tea on the wooden coffee table, and a cat blinking slowly on the rug",
    "9. Banheiro Pós-Banho Ensolarado com Babosa (Steam & Aloe Matrix): Lived-in sunlit Brazilian bathroom counter with post-shower steam blurring the extreme lens edges, volumetric morning light rays with dancing dust motes filtering through a frosted window, a sprawling green Aloe Vera (babosa) plant in a wet pot with condensation droplets, tangled hair dryer cords, a dripping wet towel, and a sleeping caramel dog",
    "10. Área Gourmet Externa & Plantas Tropicais: Bright Brazilian outdoor gourmet veranda with rustic brick walls, lush Areca palms and hanging samambaias catching intense natural sunlight, a wooden island counter with a cold glass of juice sweating condensation, and a bird hopping on the garden beam",
    "11. Varanda com Chuva Tropical & Coqueiro (Rainstorm Deck): Covered wooden porch of a Brazilian house during a tropical rainstorm, a tall green coconut tree (pé de coco) swaying in the wind and rain in the background, potted ferns under the eaves, a damp towel and flip-flops on the floorboards, and a small wet bird huddled in the rafters shaking water off its wings",
    "12. Quarto Boho Botânico: Warm Brazilian boho bedroom with macramé wall hangings, trailing green ivy and samambaia plants around the window frame, warm bedside lamp mixing with natural daylight, a messy open suitcase on the floor, and a Siamese cat swishing its tail on the bed",
    "13. Terraço Urbano Verde (Green Terrace): Open-air Brazilian apartment terrace packed with clay pots of Monsteras, ferns, and tropical palms against an exposed brick wall, warm sunlight, a pair of sunglasses and a cold drink on a bistro table, and a bird flying past the green canopy",
    "14. Cantinho de Leitura Botânico: Rattan armchair with a carelessly draped knit blanket surrounded by floor-to-ceiling wooden shelves filled with books and lush trailing green pothos plants, soft side window daylight with dancing dust motes, and a sleeping caramel dog at the foot of the chair",
    "15. Cozinha Americana Integrada & Verde: Granite kitchen island with a wooden bowl of colorful tropical fruits, an open sliding glass door in the background revealing a sunlit balcony full of green ferns and palm leaves, spilled coffee beans and a ceramic mug on the counter",
    "16. Varanda de Inverno com Vapor & Samambaias: Crisp early-morning Brazilian glass-enclosed veranda filled with hanging samambaias and orchids, a hot ceramic mug releasing visible steam into the cool morning light rays, condensation on the glass pane, and a fluffy cat curled up on a cushion",
    "17. Jardim Vertical Interno (Living Green Wall): Striking indoor-outdoor Brazilian patio featuring an entire wall covered in lush living green ferns, monsteras, and peace lilies, natural zenithal sunlight pouring from above onto the wet leaves, a wooden counter in the foreground, and a hummingbird hovering near the foliage",
    "18. Casa de Campo Rústica & Mata Nativa: Exposed rustic wooden ceiling beams, a wide-open vintage wooden window framing dense green Brazilian countryside trees and flowering shrubs, warm sunlight hitting a wooden table with a clay water pitcher, and a bird perched on the windowsill",
    "19. Ateliê Botânico Iluminado: Sunlit creative studio room with a skylight, glass jars with brushes, terracotta pots overflowing with green monsteras and ferns, natural everyday clutter on a wooden workbench, and a cat walking across the background",
    "20. Varanda Ensolarada de Fim de Semana: Geometric floor rug, floor cushions, a massive tropical Strelitzia (Bird of Paradise) plant with vibrant green leaves catching the sun, a sweating glass of iced tea on a low wooden stool, and a Golden Retriever twitching its ear while napping",
    "21. Corredor Verde de Entrada (Deep Green Tunnel): Sunlit breezeway lined on both sides with lush tropical palms, samambaias, and monsteras creating extreme depth of field, terracotta floor tiles wet from watering, and a caramel dog trotting softly in the background",
    "22. Deck de Barco Regional na Natureza Amazônica: Rustic wooden deck of a gently moving boat surrounded by lush green riverbanks and tropical forest canopy, natural sunlight reflecting off the water ripples, an orange life jacket and a coffee cup on a wooden bench, and a flock of birds flying over the trees"
]

# ==========================================================
# ETAPA 1: SCANNER COMERCIAL COM AJUSTE FINO DE PROPORÇÃO COMPACTA (NUNCA MAIOR QUE A MÃO)
# ==========================================================
def escanear_inventario_exato_da_foto(img_b64, diretriz_extra=""):
    """
    Ajuste fino de tamanho: como as IAs geradoras tendem a aumentar potes em ~20%,
    travamos a instrução 'compact standard retail scale, fitting comfortably and delicately inside one normal human hand, strictly DO NOT oversize'.
    """
    prompt_scan = """
    You are an e-commerce catalog assistant. Inspect ONLY the commercial product packaging/apparel in this image and return a JSON object:
    1. "quantidade_exata": integer count of distinct product items/containers/pieces in the offer (e.g., 1, 2, 3, 5, 6).
    2. "nome_comercial_pt": full commercial name of the product or kit in Portuguese.
    3. "categoria_produto": one of ["cosmetico_pote_frasco", "moda_roupa_calcado", "casa_utensilio_outros"].
    4. "inventario_detalhado_ingles": describe EVERY SINGLE UNIT from the image in English with its exact body color, label details, and lid color. Always describe containers as compact, standard retail size that fits comfortably in one normal hand (e.g., "ALL 3 EXACT UNITS FROM THE KIT: (Unit 1) compact standard green jar with black lid, (Unit 2) compact standard pink jar with black lid, and (Unit 3) compact standard orange jar with black lid").
    5. "trava_tamanho_ingles":
       - If quantidade_exata == 1:
         "[CRITICAL ABSOLUTE PHYSICS & SIZE LOCK: STRICT 1:1 real-world scale. This is a compact standard retail container (400g/1kg everyday hand-size proportion). The container held or shown must look compact, light, and perfectly proportioned to fit comfortably inside a normal human hand, with fingers wrapping naturally around its circumference. Absolutely DO NOT oversize, DO NOT make it look like a giant bucket, and DO NOT shrink]."
       - If quantidade_exata >= 2:
         "[CRITICAL ABSOLUTE PHYSICS, SIZE & MULTI-UNIT LOCK: STRICT 1:1 real-world scale. These are compact standard retail containers proportioned to fit comfortably inside a human hand. Absolutely DO NOT oversize! ALL units from the reference kit MUST be clearly visible together in the frame: she holds one unit comfortably in her hand while the other unit(s) rest clearly visible right next to her on the foreground counter surface]."
    """
    try:
        resp_scan = cliente_openai.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a helpful e-commerce product cataloging assistant. Output valid JSON only."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt_scan},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]}
            ],
            temperature=0.1
        )
        return json.loads(resp_scan.choices[0].message.content)
    except Exception:
        return {
            "quantidade_exata": 1,
            "nome_comercial_pt": diretriz_extra if diretriz_extra else "Produto Principal da Referência",
            "categoria_produto": "cosmetico_pote_frasco",
            "inventario_detalhado_ingles": "the exact compact standard product(s) shown in the reference image",
            "trava_tamanho_ingles": "[CRITICAL ABSOLUTE PHYSICS & SIZE LOCK: STRICT 1:1 real-world scale. The container held or shown must look compact, light, and perfectly proportioned to fit comfortably inside a human hand. Absolutely DO NOT oversize, and DO NOT shrink]."
        }

pode_gerar_roteiro = True
usos_feitos = 0
aba_limites = None

if not E_O_CEO and robo_sheets:
    try:
        match_id = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
        if match_id:
            planilha_mestre = robo_sheets.open_by_key(match_id.group(1))
            try: aba_limites = planilha_mestre.worksheet("Limites_Roteiros")
            except Exception:
                aba_limites = planilha_mestre.add_worksheet(title="Limites_Roteiros", rows="1000", cols="2")
                aba_limites.append_row(["Email", "Gerou"])
            lista_usos = aba_limites.col_values(1)
            usos_feitos = lista_usos.count(email_sessao)
            if usos_feitos >= 3: pode_gerar_roteiro = False
    except Exception: pass

with st.container(border=True):
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        if st.button("⚙️ MODO PADRÃO (Bloco 17 - Estrutura Original Sem Logo)", type="primary" if not st.session_state["modo_entidade_v9"] else "secondary", use_container_width=True, key="btn_sel_v31"):
            st.session_state["modo_entidade_v9"] = False
            st.rerun()
    with col_sel2:
        if st.button("🧬 ATIVAR ENTIDADE V9.2 (Bloco 17.2 - Estrutura V9 Com/Sem Logo)", type="primary" if st.session_state["modo_entidade_v9"] else "secondary", use_container_width=True, key="btn_sel_v9"):
            st.session_state["modo_entidade_v9"] = True
            st.rerun()

    aba_gerador_360, aba_config_influencer = st.tabs([
        "📸 Gerar Roteiro & Diretrizes", 
        "👤 Configurar Minha Influencer & Logo"
    ])
    
    with aba_gerador_360:
        if eh_customizada:
            st.info(f"✨ **Influencer Ativa:** `{nome_inf_ativa}` | 🏷️ **Logo Glitch:** `{logo_ativa_usuario}`")
        else:
            if E_O_CEO:
                st.caption(f"🦅 **Influencer Padrão do CEO Ativa:** Aurora Original | 🏷️ **Logo Padrão CEO:** `{logo_ativa_usuario}`")
            else:
                st.warning(f"⚠️ Você está usando a personagem padrão (Aurora). Vá na aba **'👤 Configurar Minha Influencer & Logo'** acima para personalizar sua Influencer e sua Logo!")
        
        col_img, col_dados = st.columns([1, 1])
        with col_img: 
            img_produto = st.file_uploader("📸 Foto do Produto (Unidade ou Kit)", type=["png", "jpg", "jpeg"], key="img_produto_roteiro")
            if E_O_CEO:
                logo_input_direto = st.text_input(
                    "🏷️ Logo do Glitch Final (Padrão CEO já ativo — altere apenas se quiser outra):",
                    value=logo_ativa_usuario,
                    placeholder="O Achado Secreto",
                    key="input_logo_direto_ceo"
                )
            else:
                logo_input_direto = st.text_input(
                    "🏷️ Nome da sua Logo / Marca (Para o Glitch Digital Final):",
                    value=logo_salva_banco,
                    placeholder="Ex: Minha Loja VIP / Achadinhos da Bia...",
                    key="input_logo_direto_user"
                )
            if logo_input_direto and logo_input_direto.strip():
                logo_ativa_usuario = logo_input_direto.strip()

        with col_dados:
            col_amb_opt, col_modo_opt = st.columns(2)
            with col_amb_opt:
                opcoes_matriz_ui = ["🎲 Sorteio Automático (Sempre com Plantas/Natureza)"] + MATRIZES_AMBIENTES_V92
                escolha_ambiente_ui = st.selectbox("🌿 Matriz de Ambiente:", opcoes_matriz_ui, key="sel_ambiente_v92")
            with col_modo_opt:
                modo_operacao_video = st.selectbox(
                    "🎬 Estrutura de Finalização do Vídeo:",
                    [
                        "🧼 Estrutura Sem Logo (Shot 1 + Shot 2 + 3D CTA + Pristine Canvas)",
                        "🔥 Estrutura Com Logo Glitch P1 (Foco Reverso + Whip Pan + 3D CTA + Glitch Logo)"
                    ],
                    index=0 if not st.session_state["modo_entidade_v9"] else 1,
                    key="sel_modo_feed_live"
                )

            explicacao_video_usuario = st.text_area(
                "📝 Diretrizes / O que você quer no vídeo? (Opcional):",
                placeholder="Ex: Quero que ela mostre a textura do produto, foque nos detalhes ou fale com tom de segredo...",
                height=85,
                key="txt_diretrizes_360"
            )
            btn_gerar_roteiro = False
            if not st.session_state["modo_entidade_v9"]:
                if not pode_gerar_roteiro:
                    st.error("🚨 LIMITE ATINGIDO! Você já gerou os seus 3 roteiros gratuitos. Faça o upgrade para a conta CEO para uso ilimitado.")
                    btn_gerar_roteiro = st.button("⚡ LER RÓTULO E GERAR", type="primary", use_container_width=True, disabled=True, key="btn_gerar_360_disabled")
                else:
                    txt_botao = "⚡ LER RÓTULO E GERAR NO BLOCO 17 (Ilimitado)" if E_O_CEO else f"⚡ LER RÓTULO E GERAR NO BLOCO 17 ({3 - usos_feitos} Restantes)"
                    btn_gerar_roteiro = st.button(txt_botao, type="primary", use_container_width=True, key="btn_gerar_360_ativo")
            else:
                st.success("🧬 **MODO ENTIDADE V9.2 ATIVADO!** Clique no botão vermelho do **Bloco 17.2** logo abaixo.")

    with aba_config_influencer:
        st.markdown("<h4 style='color: #00E5FF;'>🧬 Identidade Visual da Sua Influencer & Logo da Marca</h4>", unsafe_allow_html=True)
        st.caption("Configure as características físicas da sua personagem e a sua Logo/Marca. Tudo ficará gravado exclusivamente no seu login.")
        
        if eh_customizada:
            st.success(f"✅ **Influencer Salva na Memória:** {nome_inf_ativa} | 🏷️ **Logo Salva:** {logo_ativa_usuario}")
            st.markdown(f"**Descrição Visual Aplicada:**\n> *{desc_inf_ativa}*")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 Trocar / Excluir Influencer e Logo Atual", type="secondary", use_container_width=True, key="btn_excluir_inf"):
                with st.spinner("Removendo dados da memória para liberar novo cadastro..."):
                    gerenciar_influencer_usuario("excluir", email_sessao)
                    st.session_state["influencer_atual"] = None
                    st.success("🧹 Dados removidos! Agora você pode cadastrar uma nova configuração abaixo.")
                    time.sleep(1)
                    st.rerun()
        else:
            if E_O_CEO:
                st.info("👑 **Modo CEO:** A sua influencer padrão (Aurora) e a sua Logo padrão ('O Achado Secreto') já estão ativas nativamente. Se quiser testar outra personagem ou outra logo, preencha abaixo e salve:")
            
            novo_nome_inf = st.text_input("👤 Nome da sua Influencer:", placeholder="Ex: Maya, Valentina, Bia...", key="input_nome_inf")
            nova_logo_inf = st.text_input(
                "🏷️ Nome da sua Logo / Marca (Glitch Final):", 
                value="O Achado Secreto" if E_O_CEO else "",
                placeholder="Ex: O Garimpo Chic / Minha Marca VIP...", 
                key="input_logo_inf"
            )
            nova_desc_inf = st.text_area(
                "🎨 Descrição Visual Completa (Cabelo, Pele, Idade, Estilo, Expressão):",
                placeholder="Ex: Mulher brasileira jovem de 24 anos, pele morena iluminada, cabelos cacheados volumosos e brilhantes na altura dos ombros, olhos castanhos expressivos, usando uma camiseta básica branca, expressão de amiga fofoqueira...",
                height=130,
                key="input_desc_inf"
            )
            if st.button("💾 APLICAR E SALVAR INFLUENCER + LOGO NO MEU LOGIN", type="primary", use_container_width=True, key="btn_salvar_inf"):
                if not novo_nome_inf.strip() or not nova_desc_inf.strip():
                    st.warning("⚠️ Preencha o nome e a descrição visual completa da sua influencer para aplicar no sistema!")
                else:
                    logo_para_gravar = nova_logo_inf.strip() if nova_logo_inf.strip() else (logo_padrao_ceo if E_O_CEO else "Minha Marca VIP")
                    with st.spinner("Gravando a sua Influencer e Logo no banco de memória exclusivo do seu login..."):
                        if gerenciar_influencer_usuario("salvar", email_sessao, novo_nome_inf, nova_desc_inf, logo_para_gravar):
                            st.session_state["influencer_atual"] = {
                                "Email": email_sessao,
                                "Nome_Influencer": novo_nome_inf.strip(),
                                "Descricao_Visual": nova_desc_inf.strip(),
                                "Logo_Marca": logo_para_gravar
                            }
                            st.success(f"🔥 {novo_nome_inf} e a logo '{logo_para_gravar}' foram aplicadas ao seu login!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Erro ao salvar no banco de dados. Verifique a conexão com a planilha.")

def forjar_roteiro_blindado_sem_bloqueio(instrucao_prompt):
    resp = cliente_openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an elite commercial creative director and copywriter for e-commerce product advertisements. "
                    "Follow the EXACT template structure requested by the user without changing a single structural label or bracket. "
                    "Never use asterisks (**) inside the English visual prompts."
                )
            },
            {"role": "user", "content": instrucao_prompt}
        ],
        max_tokens=4096,
        temperature=0.75
    )
    return resp.choices[0].message.content.strip()

# ==========================================================
# EXECUÇÃO DO BLOCO 17 (ESTRUTURA CLÁSSICA ORIGINAL 100% PRESERVADA!)
# ==========================================================
if btn_gerar_roteiro and img_produto and pode_gerar_roteiro:
    with st.spinner("🦅 Lendo rótulo, calibrando tamanho compacto na mão e montando a Estrutura Original..."):
        try:
            img_b64_roteiro = base64.b64encode(img_produto.getvalue()).decode('utf-8')
            scan_info = escanear_inventario_exato_da_foto(img_b64_roteiro, explicacao_video_usuario)
            amb_escolhido = random.choice(MATRIZES_AMBIENTES_V92) if "Sorteio Automático" in escolha_ambiente_ui else escolha_ambiente_ui
            usar_logo_no_17 = "Com Logo" in modo_operacao_video

            linha_finalizacao_17 = (
                f"0:09-0:10: [FINALIZAÇÃO P1]: A violent red digital glitch effect flashes across the screen with the logo '{logo_ativa_usuario}' appearing in the center, followed by a sudden dry cut."
                if usar_logo_no_17 else
                "[PRISTINE CANVAS LOCK - ZERO WATERMARKS]: [Strict requirement: The video frame must be completely devoid of any platform UI, handles, usernames, profile pictures, corner watermarks, or embedded social media logos from frame 0 to the final second. Pure clean video feed only.]"
            )

            # ESTRUTURA ORIGINAL EXATA VALIDADA DO SÓCIO (BLOCO 17)
            instrucao_ouro_original = f"""
            Atue como um Diretor de Arte e Roteirista Publicitário de UGC para e-commerce.
            Sua tarefa é redigir a ficha técnica criativa seguindo EXATAMENTE a estrutura validada abaixo (sem mudar o formato dos blocos):

            DADOS DO PRODUTO ESCANEADO NA FOTO:
            - Nome Comercial: {scan_info.get('nome_comercial_pt')}
            - Quantidade Exata de Unidades na Foto: {scan_info.get('quantidade_exata')}
            - Descrição Exata das Unidades (em inglês): {scan_info.get('inventario_detalhado_ingles')}
            - Cenário Botânico Brasileiro Sorteado: {amb_escolhido}

            REGRAS DE OURO:
            1. TAMANHO COMPACTO REALISTA NA MÃO: O produto NUNCA pode ficar grande demais! Mantenha exatamente a trava: `[CRITICAL ABSOLUTE PHYSICS & SIZE LOCK: STRICT 1:1 real-world scale. These are standard 400g cosmetic jars (compact everyday hand-size proportion, slightly smaller and more delicate than a human palm). The jars held or shown must look compact, light, and perfectly proportioned to fit comfortably inside a human hand. Absolutely DO NOT oversize, and DO NOT shrink]`.
            2. SE FOR KIT COM {scan_info.get('quantidade_exata')} UNIDADES: Mencione todas as unidades ({scan_info.get('inventario_detalhado_ingles')}) tanto na Imagem quanto no Vídeo (ela segura 1 unidade na mão enquanto as outras unidades ficam claramente visíveis na superfície ao lado dela).

            SIGA EXATAMENTE ESTA ESTRUTURA VALIDADA PALAVRA POR PALAVRA (PREENCHENDO APENAS OS CAMPOS ENTRE COLCHETES):

            ### 📸 PROMPT DE IMAGEM
            RAW photography, close-up POV handheld mobile phone shot. Extreme hyper-realism: detailed natural skin pores, peach fuzz, subtle moisture on skin, NO artificial flash. {desc_inf_ativa}. A small, discrete black wireless lapel microphone is visibly clipped to the neckline of her shirt. She is standing in [DESCREVA AQUI EM INGLÊS COM MAIS DE 500 CARACTERES O CENÁRIO '{amb_escolhido}', INCLUINDO ILUMINAÇÃO NATURAL, PLANTAS VIVAS, TEXTURAS, OBJETOS COTIDIANOS E O ANIMAL DE ESTIMAÇÃO AO FUNDO]. [CRITICAL ABSOLUTE PHYSICS & SIZE LOCK: STRICT 1:1 real-world scale. These are standard 400g cosmetic jars. The jars held or shown must look compact, light, and perfectly proportioned to fit comfortably inside a human hand, never oversized. Absolutely DO NOT oversize, and DO NOT shrink]. She is firmly holding the EXACT "{scan_info.get('inventario_detalhado_ingles')}" matching reference image, with her fingers naturally wrapping around its authentic compact retail circumference (if it is a kit with multiple units, she holds one unit in hand while the other units rest clearly visible on the surface next to her). Unfiltered UGC vlog style, 8k resolution.

            ### 🎬 PROMPT DE VÍDEO COMPLETO E UNIFICADO
            POV dynamic handheld mobile video, authentic UGC aesthetic. Dynamic spatial movement with natural handheld motion. The camera smoothly tilts up from a surface where the product rests. Starts with a fast Macro Zoom In exclusively on the EXACT reference product: {scan_info.get('inventario_detalhado_ingles')} matching reference image. [CRITICAL ABSOLUTE PHYSICS & SIZE LOCK: STRICT 1:1 real-world scale. These are standard 400g cosmetic jars. The jars held or shown must look compact, light, and perfectly proportioned to fit comfortably inside a human hand, maintaining the exact same 1:1 physical volume from the reference image. Absolutely DO NOT oversize, and strictly DO NOT shrink]. The item remains perfectly solid with micro-reflections bouncing off the surface as natural light hits it. SINGLE MOTION TRICK (The Trigger Tap): Her free index finger performs a deliberate micro-tap on the lid twice to emphasize it. NO pixel melting, NO size morphing.]
            Shot 2 (Whip Pan & Visceral Emotion): [0:03: Fast WHIP PAN and focus pull! The camera tilts up and snaps focus onto {nome_inf_ativa}'s face (microfone de lapela visível na gola da camisa, [DESCREVA OS DETALHES DO CENÁRIO '{amb_escolhido}' E O MASCOTE AO FUNDO]). VISCERAL EMOTION ACTIVE: She leans in closer towards the lens (The Gossip Lean), speaking with enthusiastic urgency and expressive eyes while holding the product ({scan_info.get('inventario_detalhado_ingles')}) at its exact compact 1:1 real-world commercial size.]
            Interaction (3D CTA): [She points her free index finger downwards towards the bottom corner of the screen. At this precise second, a highly realistic 3D floating orange shopping bag object materializes in the air near her pointing finger, casting realistic shadows. It is a physical 3D element pointing towards the UI button location.]
            {linha_finalizacao_17}
            🎙️ Áudio e Fala da {nome_inf_ativa} (Português — 100% Blindada Contra o Robô):
            Áudio (Inglês de fundo): [Audio captured via a wireless lapel microphone. Micro-ASMR intro (sound of product tap). Authentic room acoustics with subtle background ambient tones. Enthusiastic, urgent, conspiratorial voice, speaking as if revealing a highly guarded secret].
            Fala da {nome_inf_ativa}:
            "[ESCREVA UMA FALA ORIGINAL E PERSUASIVA DE 40 A 48 PALAVRAS EM PORTUGUÊS SOBRE '{scan_info.get('nome_comercial_pt')}', FOCADA NA DOR QUE ELE RESOLVE E FECHANDO COM O LOTE SECRETO NA SACOLINHA, SEM CITAR PREÇOS]"
            📝 Texto na Tela (Nativo TikTok - Foco na Dor):
            ⚠️ [FRASE CURTA DE IMPACTO SOBRE O PROBLEMA]? 🛑
            ✨ [BENEFÍCIO PRINCIPAL DO PRODUTO]
            🛒 LOTE SECRETO LIBERADO 👇

            ### 🔑 TÍTULOS SEO (Separados)
            🔍 Geral (Dor): [Título focado na solução do problema]
            💡 Solução (Produto): [Nome completo do produto e volume]
            🏷️ Marca (Resenha): [Marca e nome do produto resenha]
            """

            if explicacao_video_usuario and explicacao_video_usuario.strip():
                instrucao_ouro_original += f"\n\nNOTA DE DIREÇÃO DO USUÁRIO: Inclua este detalhe solicitado pelo usuário na cena e na fala: '{explicacao_video_usuario.strip()}'."

            conteudo_texto = forjar_roteiro_blindado_sem_bloqueio(instrucao_ouro_original)
            st.session_state["roteiro_temporario"] = conteudo_texto
            salvar_roteiro_no_drive(email_sessao, conteudo_texto)

            if not E_O_CEO and aba_limites is not None:
                try: aba_limites.append_row([email_sessao, "Sim"])
                except Exception: pass

            st.success("✅ Estrutura Original Validada (Bloco 17) + Tamanho Compacto na Mão Forjados com Sucesso!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao gerar: {e}")

# ==========================================================
# 17.2. CRIAÇÃO V9.2 — ESTRUTURA ORIGINAL V9.2 RESTAURADA (COM LOGO E SEM LOGO + TAMANHO COMPACTO NA MÃO)
# ==========================================================
if st.session_state.get("modo_entidade_v9"):
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h3 style='text-align: center; color: #FF0040;'>🧬 BLOCO 17.2: ENTIDADE V9.2 (ESTRUTURA ORIGINAL VALIDADA COM/SEM LOGO)</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: #00E5FF; font-weight: 600;'>Influencer: <b>{nome_inf_ativa}</b> &bull; Logo Glitch: <b>{logo_ativa_usuario}</b> &bull; <b>Estrutura V9.2 Original Restaurada</b></p>", unsafe_allow_html=True)

        with st.expander("📚 VER ESTRUTURAS ORIGINAIS V9.2 (COM LOGO E SEM LOGO) + 22 AMBIENTES", expanded=False):
            st.markdown("""
            **🎬 AS DUAS ESTRUTURAS DE VÍDEO ORIGINAIS VALIDADAS:**
            * **Estrutura 1 (Sem Logo / Shot 1 + Shot 2 + 3D CTA + Pristine Canvas):**
              * `Shot 1 (Macro Hook & Physics)` -> `Shot 2 (Whip Pan & Visceral Emotion)` -> `Interaction (3D CTA)` -> `[PRISTINE CANVAS LOCK - ZERO WATERMARKS]` -> `🎙️ Áudio e Fala` -> `📝 Texto na Tela`.
            * **Estrutura 2 (Com Logo P1 / Foco Reverso 0-4s + Whip Pan 0:05 + 3D CTA 0:08 + Finalização P1 0:09-0:10):**
              * `[POV intensely erratic handheld mobile video... FOCO REVERSO (0-4s)... SINGLE MOTION TRICK (The Trigger Tap V9)... 0:05: WHIP PAN and brutal focus pull!... VISCERAL EMOTION ACTIVE... [ENVIRONMENT REINFORCEMENT LOCK V9]... 0:08: [CRITICAL PHYSICS & CTA LOCK]... 0:09-0:10: [FINALIZAÇÃO P1]: A violent red digital glitch effect flashes across the screen with the logo... Clean screen, 8k resolution.]`
            """)

        if not pode_gerar_roteiro:
            st.error("🚨 LIMITE ATINGIDO! Você já gerou os seus 3 roteiros gratuitos. Faça o upgrade para a conta CEO para uso ilimitado.")
            btn_disparar_v9 = st.button("🔥 FORJAR PACOTE ENTIDADE V9.2", type="primary", use_container_width=True, disabled=True, key="btn_v9_disabled")
        else:
            txt_btn_v9 = "🔥 FORJAR ENTIDADE V9.2 NA ESTRUTURA ORIGINAL VALIDADA (ILIMITADO)" if E_O_CEO else f"🔥 FORJAR ENTIDADE V9.2 ({3 - usos_feitos} Restantes)"
            btn_disparar_v9 = st.button(txt_btn_v9, type="primary", use_container_width=True, key="btn_v9_ativo")

        if btn_disparar_v9:
            if not img_produto:
                st.warning("⚠️ Suba a **📸 Foto do Produto** ali em cima no Bloco 17 primeiro!")
            else:
                with st.spinner("🧬 Escaneando produto e montando a Estrutura Original V9.2 (Com ajuste fino de tamanho na mão)..."):
                    try:
                        img_b64_v9 = base64.b64encode(img_produto.getvalue()).decode('utf-8')
                        scan_v9 = escanear_inventario_exato_da_foto(img_b64_v9, explicacao_video_usuario)
                        amb_v9 = random.choice(MATRIZES_AMBIENTES_V92) if "Sorteio Automático" in escolha_ambiente_ui else escolha_ambiente_ui
                        usar_logo_v9 = "Com Logo" in modo_operacao_video

                        if usar_logo_v9:
                            # ESTRUTURA ORIGINAL COM LOGO GLITCH P1 (EXATAMENTE COMO NO GABARITO ENVIADO PELO SÓCIO)
                            template_video_v92 = f"""[POV intensely erratic handheld mobile video, documentary chaos aesthetic. Extreme dynamic spatial movement, heavy camera shake, raw UGC vlog style, 100% real-life visceral texture. The extreme edges of the camera lens catch natural light flares from the plants. FOCO REVERSO (0-4s): Video starts with a violent Macro Zoom In exclusively on the EXACT reference products ({scan_v9.get('inventario_detalhado_ingles')}) held firmly in her hand (and resting on the counter if multiple units) against the background. [CRITICAL: 1:1 real-world scale, compact standard retail size fitting comfortably inside a normal human hand, slightly smaller than palm width, exact match to reference, strictly DO NOT oversize]. [ABSOLUTE PIXEL-PERFECT CLONE LOCK & PHYSICS]: The items remain perfectly solid with micro-reflections bouncing off the plastic as natural light hits them. SINGLE MOTION TRICK (The Trigger Tap V9): Her clean free index finger performs a deliberate micro-tap on the solid lid/trigger twice to emphasize it. NO hand overlapping, absolute physics stability, NO pixel melting. 0:05: WHIP PAN and brutal focus pull! The camera violently tilts up and snaps focus onto {nome_inf_ativa}'s face (straight bangs, flawless skin with visible pores, wireless lapel mic on collar). VISCERAL EMOTION ACTIVE: She leans in aggressively towards the lens (The Gossip Lean), her chest heaving with heavy, urgent breathing, pupils visibly dilated, and she flashes a breathless, intensely serious expression of pure warning, making soul-piercing eye contact while keeping all product unit(s) ({scan_v9.get('inventario_detalhado_ingles')}) visible in compact 1:1 hand-size proportion. [ENVIRONMENT REINFORCEMENT LOCK V9]: [DESCREVA EM INGLÊS O CENÁRIO '{amb_v9}', AS PLANTAS VIVAS, A BAGUNCINHA E O ANIMAL SE MEXENDO SUTILMENTE NO FUNDO]. 0:08: [CRITICAL PHYSICS & CTA LOCK]: She aggressively points her free index finger downwards towards the bottom corner of the screen. At this precise second, a highly realistic 3D floating orange shopping bag object materializes in the air near her pointing finger, casting realistic shadows. It is a physical 3D element pointing towards the UI button location. 0:09-0:10: [FINALIZAÇÃO P1]: A violent red digital glitch effect flashes across the screen with the logo '{logo_ativa_usuario}' appearing in the center, followed by a sudden dry cut. Clean screen, 8k resolution.]

🎙️ Áudio (Gancho V9.2 Blindado: O Alerta da Amiga — Exatos 9 Segundos):
(Abre em 0.0s com micro-efeito ASMR: Som de toque na embalagem/borrifador e um suspiro de advertência).
Voz da {nome_inf_ativa} (ofegante, indignada e conselheira):
"[ESCREVA EM PORTUGUÊS A FALA DE EXATOS 9 SEGUNDOS (35 A 45 PALAVRAS) SOBRE '{scan_v9.get('nome_comercial_pt')}', CITANDO TODAS AS {scan_v9.get('quantidade_exata')} UNIDADES SE FOR KIT, FOCANDO NA DOR E FECHANDO COM O LOTE SECRETO NA SACOLINHA SEM CITAR PREÇO NUMÉRICO]"

📝 Texto na Tela (Nativo TikTok - Foco na Dor):
"⚠️ [ALERTA DE IMPACTO SOBRE A DOR]? 🛑"
"[BENEFÍCIO PRINCIPAL + PRODUTO/KIT] ✨"
"CORRE NA SACOLINHA 🛒👇"

🔥 Finalização P1:
Glitch digital vermelho violento com a logo '{logo_ativa_usuario}' no milésimo final. Corte entra seco."""
                        else:
                            # ESTRUTURA ORIGINAL SEM LOGO (SHOT 1 + SHOT 2 + INTERACTION 3D CTA + PRISTINE CANVAS)
                            template_video_v92 = f"""Shot 1 (Macro Hook & Physics): [POV intensely erratic handheld mobile video, documentary chaos aesthetic. Extreme dynamic spatial movement. The camera violently tilts up from a table where the product rests. Starts with an aggressive Macro Zoom In exclusively on the EXACT reference product ({scan_v9.get('inventario_detalhado_ingles')}) held firmly. CRITICAL PHYSICS: 1:1 scale (compact standard retail size, perfectly and delicately proportioned to fit inside her single hand, strictly do not oversize). The item remains perfectly solid with micro-reflections bouncing off the plastic as sunlight hits it. SINGLE MOTION TRICK (The Trigger Tap): Her free index finger performs a deliberate micro-tap on the lid/pump trigger twice to emphasize its mechanism. NO pixel melting.]

Shot 2 (Whip Pan & Visceral Emotion): [0:03: WHIP PAN and brutal focus pull! The camera violently tilts up and snaps focus onto {nome_inf_ativa}'s face (microfone de lapela visível na gola da camisa, [DESCREVA EM INGLÊS O CENÁRIO '{amb_v9}', AS PLANTAS VIVAS, A BAGUNCINHA ORGÂNICA E O ANIMAL NO FUNDO]). VISCERAL EMOTION ACTIVE: She leans in aggressively towards the lens (The Gossip Lean), her chest heaving slightly with urgent breathing, flashing a breathless, intensely serious expression of pure warning while keeping all product unit(s) ({scan_v9.get('inventario_detalhado_ingles')}) visible at their compact 1:1 hand-size scale.]

Interaction (3D CTA): [She aggressively points her free index finger downwards towards the bottom corner of the screen. At this precise second, a highly realistic 3D floating orange shopping bag object materializes in the air near her pointing finger, casting realistic shadows. It is a physical 3D element pointing towards the UI button location.]

[PRISTINE CANVAS LOCK - ZERO WATERMARKS]: [Strict requirement: The video frame must be completely devoid of any platform UI, handles, usernames, profile pictures, corner watermarks, or embedded social media logos from frame 0 to the final second. Pure clean video feed only.]

🎙️ Áudio (Inglês): [Audio captured via a wireless lapel microphone. Micro-ASMR intro (sound of product tap). Authentic room acoustics. Urgent, breathless, conspiratorial voice, speaking as if revealing a highly guarded secret].

Fala da {nome_inf_ativa} (Português - 100% Blindada Contra o Robô):
"[ESCREVA EM PORTUGUÊS A FALA DE EXATOS 9 SEGUNDOS (38 A 45 PALAVRAS) SOBRE '{scan_v9.get('nome_comercial_pt')}', FOCADA NA DOR E NA ESCASSEZ DO LOTE SECRETO NA SACOLINHA, ZERO MENÇÃO A PREÇOS]"

📝 Texto na Tela (Nativo TikTok - Foco na Dor):
"⚠️ [ALERTA DE IMPACTO SOBRE A DOR]? 🛑"
"[BENEFÍCIO PRINCIPAL DO PRODUTO] ✨"
"CORRE NA SACOLINHA 🛒👇" """

                        prompt_mestre_v92 = f"""
                        Atue como a ENTIDADE V9.2. Preencha a estrutura original validada abaixo para o produto escaneado, sem alterar o formato dos blocos!

                        DADOS ESCANEADOS:
                        - Produto/Kit: {scan_v9.get('nome_comercial_pt')} ({scan_v9.get('quantidade_exata')} unidade(s))
                        - Unidades em Inglês: {scan_v9.get('inventario_detalhado_ingles')}
                        - Matriz de Ambiente: {amb_v9}

                        ATENÇÃO AO TAMANHO NA IMAGEM E NO VÍDEO:
                        Para o produto NUNCA ficar grande demais na mão dela, use sempre a trava de proporção compacta:
                        `[CRITICAL PIXEL-PERFECT CLONE LOCK & SCALING]: [CRITICAL: 1:1 real-world scale, compact standard retail size and proportions, fitting comfortably and delicately inside one normal human hand (slightly smaller than palm width), exact match to reference, strictly do not oversize]`.

                        ENTREGUE EXATAMENTE NESTE FORMATO DE 3 SEÇÕES:

                        ### 📸 PROMPT DE IMAGEM
                        RAW photography, cinematic macro mid-shot POV erratic handheld mobile phone selfie, framing from chest up. Extreme V9 hyper-realism: microscopic visible peach fuzz, heavily dilated pupils, visceral breathing with chest slightly heaving, natural glowing micro-sweat on the collarbone, advanced subsurface scattering, moody warm natural sunlight filtering through greenery, NO flash. The photorealistic young Brazilian woman ({nome_inf_ativa}: {desc_inf_ativa}) with a deeply shocked, conspiratorial gossip micro-expression, acting as if she is sharing an urgent warning. [AVATAR LOCK: She MUST have perfectly cut straight bangs (franja reta) and a small black wireless lapel microphone clipped to her collar]. Her hair is the ultimate proof of the product: ultra-smooth, heavy with moisture, displaying an intense, mirror-like shine and absolute zero frizz. She is standing inside [DESCREVA EM INGLÊS O CENÁRIO '{amb_v9}']. [CRITICAL PIXEL-PERFECT CLONE LOCK & SCALING]: [CRITICAL: 1:1 real-world scale, compact standard retail product size and proportions, fitting comfortably and delicately inside one single human hand (slightly smaller than palm width), exact match to reference, strictly do not oversize]. She is firmly and naturally HOLDING the EXACT {scan_v9.get('inventario_detalhado_ingles')} from the provided reference image in one hand (if multiple units in the kit, she holds one unit in hand while the other units sit right next to her hand on the foreground counter edge so all {scan_v9.get('quantidade_exata')} units are 100% visible together). Copy the source reference image 100% intact with absolute realistic solid plastic textures and extreme micro-reflections bouncing off the surfaces. Zero packaging variations. [BRANDING INTEGRITY LOCK]: All text and graphics preserved accurately. [NATURE MATRIX ACTIVE (DENSE)]: [Descreva em inglês as plantas exuberantes do cenário '{amb_v9}']. [BAGUNCINHA TEMÁTICA (CHAOS V9)]: [Descreva em inglês a baguncinha orgânica do cenário '{amb_v9}']. [ANIMAL FACTOR (STORYTELLING V9)]: [Descreva em inglês o animal do cenário '{amb_v9}' em ação realista ao fundo]. High-contrast, cinematic atmospheric shadows, heavy sensor noise, 8k resolution.

                        ### 🎬 PROMPT DE VÍDEO COMPLETO E UNIFICADO
                        {template_video_v92}

                        ### 🔑 TÍTULOS SEO (Separados)
                        🔍 Geral (Dor): [Título SEO Geral em português focado na dor/solução]
                        💡 Solução (Produto): [Título SEO Solução em português descrevendo o produto/kit completo]
                        🏷️ Marca (Resenha): [Título SEO De Marca em português com nome exato do produto/kit e marca]
                        """

                        if explicacao_video_usuario and explicacao_video_usuario.strip():
                            prompt_mestre_v92 += f"\n\nDIRETRIZ ESPECÍFICA DO USUÁRIO: {explicacao_video_usuario.strip()}"

                        conteudo_v9 = forjar_roteiro_blindado_sem_bloqueio(prompt_mestre_v92)
                        st.session_state["roteiro_temporario"] = conteudo_v9
                        salvar_roteiro_no_drive(email_sessao, conteudo_v9)

                        if not E_O_CEO and aba_limites is not None:
                            try: aba_limites.append_row([email_sessao, "Sim_V92"])
                            except Exception: pass

                        st.success("🔥 Estrutura Original V9.2 (Com/Sem Logo) + Tamanho Compacto na Mão Forjados com Sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao gerar na Entidade V9.2: {e}")

# ==========================================================
# EXIBIÇÃO UNIFICADA DO ROTEIRO (COM BOTÕES DE CÓPIA 100% GARANTIDOS)
# ==========================================================
if st.session_state["roteiro_temporario"]:
    with st.container(border=True):
        partes_roteiro = extrair_blocos_roteiro(st.session_state["roteiro_temporario"])
        
        if partes_roteiro["prompt_imagem"] and partes_roteiro["prompt_video"]:
            # 1. SEÇÃO PROMPT DE IMAGEM + BOTÃO À DIREITA
            col_tit_img, col_btn_img = st.columns([7, 3])
            with col_tit_img:
                st.markdown("### 📸 PROMPT DE IMAGEM")
                st.caption(f"📏 Densidade do Prompt: **{len(partes_roteiro['prompt_imagem'])} caracteres** (Escala Compacta 1:1 na Mão)")
            with col_btn_img:
                render_botao_copiar_vip(partes_roteiro["prompt_imagem"], "📋 Copiar Imagem", "copy_img_360")
            
            st.markdown(partes_roteiro["prompt_imagem"], unsafe_allow_html=True)
            st.divider()
            
            # 2. SEÇÃO PROMPT DE VÍDEO (ESTRUTURA ORIGINAL VALIDADA) + BOTÃO À DIREITA
            col_tit_vid, col_btn_vid = st.columns([7, 3])
            with col_tit_vid:
                st.markdown("### 🎬 PROMPT DE VÍDEO COMPLETO E UNIFICADO")
                st.caption(f"📏 Densidade do Prompt: **{len(partes_roteiro['prompt_video'])} caracteres** (Estrutura Original Validada)")
            with col_btn_vid:
                render_botao_copiar_vip(partes_roteiro["prompt_video"], "📋 Copiar Vídeo", "copy_vid_360")
                
            st.markdown(partes_roteiro["prompt_video"], unsafe_allow_html=True)
            st.divider()
            
            # 3. SEÇÃO TÍTULOS SEO + BOTÃO 1, BOTÃO 2, BOTÃO 3 EMBAIXO
            st.markdown("### 🔑 TÍTULOS SEO (Separados)")
            st.markdown(partes_roteiro["secao_seo_texto"], unsafe_allow_html=True)
            
            st.markdown("<p style='font-size: 0.85rem; color: #00E5FF; font-weight: 600; margin-top: 10px; margin-bottom: 5px;'>📲 Cópia Rápida de Títulos (Celular/PC):</p>", unsafe_allow_html=True)
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                render_botao_copiar_vip(partes_roteiro["titulo_1"], "📋 Botão 1 (Título 1)", "copy_t1")
            with col_t2:
                render_botao_copiar_vip(partes_roteiro["titulo_2"], "📋 Botão 2 (Título 2)", "copy_t2")
            with col_t3:
                render_botao_copiar_vip(partes_roteiro["titulo_3"], "📋 Botão 3 (Título 3)", "copy_t3")
        else:
            col_tit_full, col_btn_full = st.columns([7, 3])
            with col_tit_full:
                st.markdown("### 📋 PACOTE CRIATIVO GERADO")
            with col_btn_full:
                render_botao_copiar_vip(st.session_state["roteiro_temporario"], "📋 Copiar Tudo", "copy_full_360")
            st.markdown(st.session_state["roteiro_temporario"], unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Limpar Roteiro Atual", use_container_width=True, key="btn_limpar_roteiro_360"): 
            st.session_state["roteiro_temporario"] = None
            st.rerun()

# ==========================================================
# 18. ACADEMIA ÉLÉVO (ESCOLA DE CEOS & GESTÃO DE IMPÉRIO)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🏛️ Academia ÉLÉVO: Gestão & Mentalidade de CEO</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0A0A0;'>O manual definitivo para deixar de ser um afiliado comum e construir um império milionário.</p>", unsafe_allow_html=True)

with st.container(border=True):
    aba_mindset, aba_gestao, aba_escala, aba_mentoria = st.tabs([
        "🧠 A Mente do Sócio", 
        "💰 Gestão de Caixa", 
        "🚀 O Mapa da Escala", 
        "🦅 Mentoria Executiva"
    ])
    
    with aba_mindset:
        st.markdown("<h4 style='color: #00BFA5;'>1. A Regra de Ouro das Vendas</h4>", unsafe_allow_html=True)
        st.info("💡 **'Eu não vendo produtos. Eu vendo decisões.'**\n\nNinguém compra pelo que o produto é... compra pelo que acredita que aquilo vai fazer com a própria vida. Enquanto você tenta convencer, o mestre faz a pessoa se convencer sozinha. Mostre o problema que ela não consegue ignorar e deixe a mente dela completar o caminho.")
        st.markdown("""
        **Princípios do CEO de Elite:**
        * **Frieza Emocional:** Um vídeo flopou? Não é pessoal, é apenas um dado. Analise a taxa de retenção, mude o gancho (Whip Pan) e teste de novo.
        * **Consistência > Motivação:** Motivação acaba no 3º dia. Disciplina é o que constrói o faturamento no 30º dia.
        * **Foco no 'Quem':** Você não está a vender para toda a gente. Está a vender para a 'Buscadora de Atalhos' que quer luxo pagando pouco.
        """)
        
    with aba_gestao:
        st.markdown("<h4 style='color: #00BFA5;'>2. Como Blindar a Empresa da Falência</h4>", unsafe_allow_html=True)
        st.warning("🚨 O maior erro do iniciante é achar que todo o lucro que cai no painel é salário. Se gastar tudo o que entra, o seu negócio morre no próximo mês.")
        st.markdown("""
        **A Divisão de Ouro (Regra 50/30/20):**
        1. **50% (Reinvestimento da Máquina):** Este dinheiro não é seu, é da ÉLÉVO. Use para comprar produtos de review, melhorar a iluminação, pagar plataformas de IA ou testar tráfego pago.
        2. **30% (O seu Pró-Labore/Salário):** Este é o dinheiro que vai para o seu bolso. Use para viver, comemorar as metas batidas e pagar as suas contas pessoais.
        3. **20% (Caixa de Guerra):** O fundo de emergência. Se as redes sociais mudarem o algoritmo amanhã ou uma conta cair, você tem caixa para sobreviver meses sem vender uma única unidade.
        """)
        
    with aba_escala:
        st.markdown("<h4 style='color: #00BFA5;'>3. O Passo a Passo para o Oceano Azul</h4>", unsafe_allow_html=True)
        st.success("✨ Escalar não é trabalhar mais horas. É fazer a máquina trabalhar por si.")
        st.markdown("""
        **Fase 1: O Laboratório (Onde a mágica nasce)**
        * Você é o roteirista, o editor e o gestor.
        * O objetivo aqui NÃO é ficar rico. É achar **1 Produto Campeão e 1 Funil Validado** (Conversão > 1.5%).
        
        **Fase 2: A Multiplicação (A Força Bruta)**
        * Pegar no Produto Campeão e espalhar o mesmo vídeo em todas as frentes (Shopee Video, YouTube Shorts, Pinterest).
        * Criar contas satélites vendendo ângulos diferentes da mesma solução.
        
        **Fase 3: O Verdadeiro CEO (Delegação Total)**
        * Você para de editar vídeos. Contrata freelancers e entrega-lhes a *Máquina de Criação 360º* para eles executarem.
        * O seu único trabalho passa a ser: **Analisar dados no Dashboard, gerir a equipa e usar o Radar para achar novas tendências.**
        """)
        
    with aba_mentoria:
        st.markdown("<h4 style='color: #00BFA5;'>🗣️ Consultoria de Gestão Direta com a COO</h4>", unsafe_allow_html=True)
        st.write("Dúvidas sobre como dividir o seu tempo? Não sabe como investir o lucro? Pergunte à Aurora.")
        
        duvida_gestao = st.text_input("Qual é o seu maior desafio de gestão ou rotina hoje?", placeholder="Ex: Como divido o meu tempo entre gravar vídeos e pesquisar produtos novos?", key="input_duvida_gestao")
        if st.button("Pedir Conselho de Gestão", use_container_width=True, key="btn_conselho_gestao"):
            if not duvida_gestao:
                st.warning("⚠️ Escreva a sua dúvida para a Diretoria analisar.")
            else:
                with st.spinner("🦅 A Aurora está a calcular a estratégia do seu império..."):
                    sys_gestao = "Você é Aurora, COO (Diretora de Operações) da ÉLÉVO e mentora de negócios do CEO. Seu tom é de estrategista implacável, focada em gestão de tempo, finanças e mentalidade milionária. Não use palavras clichês de autoajuda."
                    prompt_gestao = f"O nosso CEO está com o seguinte desafio de gestão na empresa: '{duvida_gestao}'. \nDê um conselho de negócio frio, direto e baseado em números. Forneça 3 passos de ação executáveis."
                    
                    resposta_mentoria = chamar_ia_global(prompt_gestao, sys_gestao)
                    
                    st.info("💡 **Parecer Executivo da Aurora:**")
                    st.markdown(resposta_mentoria)
