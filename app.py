import base64
import requests
import time
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
    except Exception as e:
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

# Memória por URL
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
# 2. DESIGN E TEMA DINÂMICO (🔥 V6.1 - ZERO QUADROS BRANCOS)
# ==========================================================
col_vazia, col_tema = st.columns([8, 2])
with col_tema: modo_claro = st.toggle("☀️ Modo Claro", value=False)

bg_color = "#F4F4F9" if modo_claro else "#0E1117"
text_color = "#222222" if modo_claro else "#F0F0F0"
card_bg = "#FFFFFF" if modo_claro else "rgba(25, 27, 31, 0.85)"
border_color = "rgba(0, 0, 0, 0.15)" if modo_claro else "rgba(212, 175, 55, 0.25)"
btn_bg = "#F9F9F9" if modo_claro else "#1A1C20"
btn_text = "#222222" if modo_claro else "#E0E0E0"
input_bg = "#FFFFFF" if modo_claro else "#121519"
code_bg = "#EAEAEA" if modo_claro else "#121519"
code_text = "#111111" if modo_claro else "#00E5FF"
shadow_base = "rgba(0, 0, 0, 0.05)" if modo_claro else "rgba(0, 0, 0, 0.4)"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Montserrat', sans-serif !important; }}
    [data-testid="stAppViewContainer"] {{ background-color: {bg_color} !important; }}
    [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="collapsedControl"], footer {{ display: none !important; }}
    
    /* Textos Gerais com Contraste Forte */
    h1, h2, h3, h4, h5, h6, p, label, li {{ color: {text_color} !important; }}
    [data-testid="stMarkdownContainer"] span {{ color: {text_color} !important; }}
    
    .titulo-elevo {{ font-size: 3.2rem; font-weight: 800; text-align: center; color: #00BFA5 !important; margin-bottom: -10px; letter-spacing: 3px; text-transform: uppercase; margin-top: 5px; }}
    .subtitulo {{ text-align: center; font-size: 0.95rem; margin-bottom: 30px; font-weight: 400; letter-spacing: 1px; text-transform: uppercase; color: {text_color} !important; opacity: 0.7; }}
    
    /* Cards, Containers e Expanders */
    [data-testid="stMetric"], 
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stExpander"],
    [data-testid="stForm"] {{ 
        background: {card_bg} !important; 
        border: 1px solid {border_color} !important; 
        border-radius: 12px !important; 
        box-shadow: 0 4px 10px {shadow_base} !important; 
    }}
    [data-testid="stExpander"] summary, [data-testid="stExpander"] div {{
        background-color: transparent !important;
        color: {text_color} !important;
    }}

    /* 🔥 ANIQUILAR QUADROS BRANCOS NOS BLOCOS DE CÓDIGO (st.code) EM TODA A PLATAFORMA 🔥 */
    [data-testid="stCodeBlock"], [data-testid="stCode"], pre, code {{
        background-color: {code_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 10px !important;
    }}
    [data-testid="stCodeBlock"] pre, [data-testid="stCode"] pre, pre code {{
        background-color: transparent !important;
        color: {text_color} !important;
        font-family: 'Montserrat', monospace !important;
        font-weight: 500 !important;
        white-space: pre-wrap !important;
        word-break: break-word !important;
    }}
    [data-testid="stCodeBlock"] span, [data-testid="stCode"] span, pre span, code span {{
        color: {text_color} !important;
        background-color: transparent !important;
    }}
    /* Botão de Copiar dentro das caixas de código */
    [data-testid="stCodeBlock"] button, [data-testid="stCode"] button, [data-testid="stCopyButton"] {{
        background-color: {btn_bg} !important;
        color: #D4AF37 !important;
        border: 1px solid rgba(212, 175, 55, 0.5) !important;
        border-radius: 6px !important;
        opacity: 1 !important;
    }}
    [data-testid="stCodeBlock"] button:hover, [data-testid="stCode"] button:hover {{
        border-color: #00E5FF !important;
        color: #00E5FF !important;
    }}

    /* Botões Gerais */
    .stButton > button, [data-testid="stFormSubmitButton"] > button {{ 
        background: {btn_bg} !important; 
        color: {btn_text} !important; 
        border: 1px solid {border_color} !important; 
        border-radius: 8px !important; 
        box-shadow: 0 2px 5px {shadow_base} !important; 
        font-weight: 600 !important; 
        transition: all 0.3s ease !important; 
    }}
    .stButton > button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 12px {shadow_base} !important; border-color: #D4AF37 !important; color: #D4AF37 !important; }}
    .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {{ 
        background: #004D40 !important; 
        color: #FFFFFF !important; 
        border: 1px solid #00BFA5 !important; 
    }}
    .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {{ 
        background: #00695C !important; 
        box-shadow: 0 6px 15px rgba(0, 191, 165, 0.4) !important; 
        border-color: #00E5FF !important; 
        color: #FFFFFF !important; 
    }}
    
    /* Inputs, TextAreas, NumberInputs e Menus Dropdown */
    div[data-baseweb="input"], div[data-baseweb="input"] > div, 
    div[data-baseweb="base-input"],
    div[data-baseweb="textarea"], div[data-baseweb="textarea"] > textarea, 
    div[data-baseweb="select"] > div,
    input, textarea {{ 
        background-color: {input_bg} !important; 
        border: 1px solid {border_color} !important; 
        color: {text_color} !important; 
        -webkit-text-fill-color: {text_color} !important;
        border-radius: 8px !important; 
    }}
    /* Lista suspensa quando clica no Selectbox */
    ul[data-baseweb="menu"], div[data-baseweb="popover"] > div {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
        border: 1px solid #D4AF37 !important;
    }}
    li[role="option"] {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
    }}
    li[role="option"]:hover, li[aria-selected="true"] {{
        background-color: rgba(212, 175, 55, 0.2) !important;
        color: #D4AF37 !important;
    }}

    /* Botões + e - do Number Input */
    [data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"] {{
        background-color: {btn_bg} !important;
        color: {text_color} !important;
        border-color: {border_color} !important;
    }}

    div[data-baseweb="input"] > div:focus-within, div[data-baseweb="textarea"]:focus-within, div[data-baseweb="select"] > div:focus-within {{ 
        border-color: #D4AF37 !important; 
        box-shadow: 0 0 8px rgba(212, 175, 55, 0.2) !important; 
    }}
    
    /* Uploader de Arquivos */
    [data-testid="stFileUploader"] > div > section, [data-testid="stFileUploadDropzone"] {{ background-color: {input_bg} !important; }}
    [data-testid="stFileUploadDropzone"] {{ border: 1px dashed rgba(212, 175, 55, 0.5) !important; border-radius: 12px !important; padding: 20px !important; transition: all 0.3s ease !important; }}
    [data-testid="stFileUploadDropzone"]:hover {{ border-color: #D4AF37 !important; background-color: rgba(212, 175, 55, 0.08) !important; }}
    [data-testid="stFileUploadDropzone"] div, [data-testid="stFileUploadDropzone"] span, [data-testid="stFileUploadDropzone"] small {{ color: {text_color} !important; background-color: transparent !important; }}
    [data-testid="stFileUploadDropzone"] button {{ background-color: {btn_bg} !important; color: {text_color} !important; border: 1px solid rgba(212, 175, 55, 0.3) !important; border-radius: 8px !important; font-weight: 500 !important; }}
    [data-testid="stFileUploadDropzone"] button:hover {{ border-color: #D4AF37 !important; color: #D4AF37 !important; }}
</style>
""", unsafe_allow_html=True)

js_moeda = """
<script>
    const parent = window.parent.document;
    if (!parent.getElementById("moeda-aguia-vip")) {
        const btn = parent.createElement("div");
        btn.id = "moeda-aguia-vip";
        btn.innerHTML = "🦅";
        btn.style.cssText = "position: fixed; top: 15px; left: 15px; z-index: 999999; font-size: 24px; background: #1a1c20; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #00BFA5; box-shadow: 0px 4px 10px rgba(0,0,0,0.5); cursor: pointer; user-select: none; transition: transform 0.1s ease;";
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

# Captura e padroniza o GMAIL (Única identidade que importa para o sistema)
email_logado_agora = str(st.session_state.get("email_usuario", "")).strip().lower()
nome_apenas_fala = str(st.session_state.get("nome_usuario", "Sócio")).strip()

# 1. VERIFICAÇÃO EXCLUSIVA POR GMAIL (Se mudar o Gmail, ele verifica tudo do zero!)
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
                
                # Lê apenas a Coluna 1 (Gmails) e ignora totalmente os nomes
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
            
            # Registra o GMAIL no banco de dados após gerar o áudio com sucesso
            try:
                agora_reg = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")
                aba_bv.append_row([email_logado_agora, agora_reg])
            except Exception:
                pass

# 2. EXIBIÇÃO BLINDADA COM ASSINATURA DO GMAIL NO HTML
if st.session_state.get("mostrar_player_bv") and st.session_state.get("audio_boas_vindas_b64"):
    audio_b64 = st.session_state["audio_boas_vindas_b64"]
    
    # O comentário invisível <!-- GMAIL: ... --> força o navegador a criar um novo botão 
    # mesmo que duas pessoas tenham exatamente o mesmo nome!
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
        if st.button("✅ JÁ OUVI / FECHAR MENSAGEM", use_container_width=True):
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
    st.success(f"Bem-vindo de volta, Sócio! O império aguarda as suas ordens. 🦅")
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
    st.session_state["email_bv_verificado"] = "" # <-- Limpa o vínculo do Gmail anterior
    st.session_state["mostrar_player_bv"] = False
    st.session_state["audio_boas_vindas_b64"] = None
    if "sessao" in st.query_params: del st.query_params["sessao"]
    st.rerun()
# ==========================================================
# 4 a 9 E 14. NÚCLEO FINANCEIRO VIP (EXCLUSIVO DO CEO)
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
    c_txt_v = "#D4AF37" if not modo_claro else "#B8860B"
    c_txt_t = "#A0A0A0" if not modo_claro else "#555555"
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; text-align: center; margin-bottom: 20px;">
            <div style="flex: 1;"><p style="margin: 0; font-size: 0.7rem; font-weight: 600; color: {c_txt_t}; text-transform: uppercase;">💰 Lucro</p><p style="margin: 0; font-size: 1.2rem; font-weight: 900; color: {c_txt_v};">R$ {aprovado:,.2f}</p></div>
            <div style="flex: 1; border-left: 1px solid rgba(212,175,55,0.2); border-right: 1px solid rgba(212,175,55,0.2);"><p style="margin: 0; font-size: 0.7rem; font-weight: 600; color: {c_txt_t}; text-transform: uppercase;">⏳ Pendente</p><p style="margin: 0; font-size: 1.2rem; font-weight: 900; color: {c_txt_v};">R$ {pendente:,.2f}</p></div>
            <div style="flex: 1;"><p style="margin: 0; font-size: 0.7rem; font-weight: 600; color: {c_txt_t}; text-transform: uppercase;">🏆 Campeão</p><p style="margin: 0; font-size: 0.9rem; font-weight: 900; color: #00E5FF; padding-top: 5px;">{str(produto_campeao)[:12] + '...' if len(str(produto_campeao))>12 else produto_campeao}</p></div>
        </div>
    """, unsafe_allow_html=True)

    if not df_timeline.empty and not df_campeao.empty:
        with st.expander("📊 👁️ ABRIR GRÁFICOS FINANCEIROS", expanded=False):
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
                fig_bar = px.bar(df_campeao.head(10), x="Comissao_R$", y="Produto", orientation='h', text="Comissao_R$", color_discrete_sequence=[c_pt])
                fig_bar.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside', cliponaxis=False, marker_line_color=c_line, marker_line_width=1.5, opacity=0.9)
                fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=text_color), margin=dict(l=0, r=80, t=40, b=0), height=380, dragmode=False)
                fig_bar.update_xaxes(showgrid=False, title="", visible=False, fixedrange=True)
                fig_bar.update_yaxes(showgrid=False, title="", autorange="reversed", fixedrange=True)
                st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

    if "dados_prontos" not in st.session_state: st.session_state["dados_prontos"] = []
    st.markdown("### 🤖 Motor de Auditoria e Injeção (Aurora)")
    texto_copiado = st.text_area("Cole o relatório do TikTok Shop (dados brutos):", height=150)
    if st.button("🚀 Extrair Dados do Texto", type="primary", use_container_width=True):
        if texto_copiado.strip() == "": st.warning("⚠️ Cole algum texto primeiro.")
        else:
            with st.spinner("🦅 Aurora organizando caixa..."):
                dt_hj = datetime.utcnow().strftime("%d/%m/%Y")
                pmt_aur = f"Extraia sem erro e sem usar cálculos os valores EXATOS, pontos no lugar de vírgulas. DATA: {dt_hj}. Texto bruto:\n{texto_copiado}"
                res_aur = chamar_ia_global(pmt_aur, "Você é Aurora, Auditora Financeira. Retorne APENAS dados no formato Data;Produto;Canal;Status;Qtd;Valor.")
                if "ERRO" not in res_aur and res_aur:
                    for l in res_aur.split('\n'):
                        its = l.split(';')
                        if len(its) >= 6 and "Data;" not in l: st.session_state["dados_prontos"].append({"Data":its[0].strip(), "Produto":its[1].strip(), "Canal":its[2].strip(), "Status":its[3].strip(), "Quantidade":its[4].strip(), "Comissao_R$":its[5].strip()})
                    if not st.session_state["dados_prontos"]: st.error("⚠️ Dados não encontrados.")
                else: st.error(f"Erro IA: {res_aur}")
    
    if st.session_state["dados_prontos"]:
        st.success("✨ Dados validados!")
        if st.button("🗑️ Limpar Lista"): st.session_state["dados_prontos"] = []; st.rerun()
        df_ed = st.data_editor(pd.DataFrame(st.session_state["dados_prontos"]), num_rows="dynamic", use_container_width=True)
        if st.button("💾 INJETAR DADOS NA PLANILHA", type="primary"):
            with st.spinner("Injetando no Google Drive..."):
                try:
                    aba = robo_sheets.open_by_key(extrair_id_planilha(link_planilha_ativa)).sheet1
                    linhas_ins = [[str(d.get(k,"")) for k in ["Data","Produto","Canal","Status","Quantidade","Comissao_R$"]] for d in df_ed.to_dict('records')]
                    aba.insert_rows(linhas_ins, row=len([x for x in aba.col_values(1) if x.strip()!=""])+1, value_input_option="USER_ENTERED")
                    st.success("🔥 SUCESSO! Planilha atualizada!"); st.balloons(); st.session_state["dados_prontos"] = []; carregar_dados_dinamicos.clear(); st.rerun()
                except Exception as e: st.error(f"❌ Erro: {e}")
                
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🦅 PROTOCOLO ÁGUIA (Limpar Erros de Hoje)", expanded=False):
        st.warning("⚠️ APAGA TODAS as vendas de HOJE no Drive.")
        if st.button("🦅 ACIONAR ÁGUIA", type="secondary", use_container_width=True):
            with st.spinner("Apagando..."):
                try:
                    aba = robo_sheets.open_by_key(extrair_id_planilha(link_planilha_ativa)).sheet1
                    col_dt = aba.col_values(1)
                    hj_str = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y")
                    apgs = 0
                    for i in range(len(col_dt), 1, -1):
                        if str(col_dt[i-1]).strip() == hj_str: aba.delete_rows(i); apgs += 1; time.sleep(0.5)
                    st.success(f"🦅 {apgs} linhas apagadas." if apgs > 0 else "Nenhum dado hoje.")
                    carregar_dados_dinamicos.clear(); time.sleep(2); st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

    if not df.empty and "Data_Parsed" in df.columns:
        agora_brasil = datetime.utcnow() - timedelta(hours=3)
        hoje = pd.Timestamp(agora_brasil.date())
        rev_7d = df[(df["Data_Parsed"] >= (hoje - timedelta(days=7))) & (df["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False))]["Comissao_R$"].sum()
        rev_p_7d = df[(df["Data_Parsed"] >= (hoje - timedelta(days=14))) & (df["Data_Parsed"] < (hoje - timedelta(days=7))) & (df["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False))]["Comissao_R$"].sum()
        crescimento = ((rev_7d - rev_p_7d) / rev_p_7d * 100) if rev_p_7d > 0 else (100.0 if rev_7d > 0 else 0.0)
        if crescimento > 5: cor_anim, sombra_anim, nota_empresa, simbolo = "#00FF7F", "rgba(0, 255, 127, 0.4)", "A+", "🚀 ESCALANDO"
        elif crescimento < -5: cor_anim, sombra_anim, nota_empresa, simbolo = "#FF0040", "rgba(255, 0, 64, 0.4)", "C-", "🚨 QUEDA"
        else: cor_anim, sombra_anim, nota_empresa, simbolo = "#FFD700", "rgba(212, 175, 55, 0.4)", "B", "⚖️ ESTÁVEL"
        st.markdown(f"""
        <div style="background: rgba(15,15,15,0.8); backdrop-filter: blur(10px); border: 2px solid {cor_anim}; border-radius: 16px; padding: 15px 20px; text-align: center; box-shadow: 0 0 15px {sombra_anim}; animation: pulse-cor 2s infinite ease-in-out; margin: 10px auto; max-width: 400px;">
            <h2 style="color: {cor_anim}; font-family: 'Montserrat', sans-serif; font-weight: 900; letter-spacing: 1px; margin: 0; font-size: 1rem;">STATUS DA OPERAÇÃO</h2>
            <h1 style="color: {cor_anim}; font-family: 'Montserrat', sans-serif; font-size: 2.5rem; font-weight: 900; margin: 5px 0; text-shadow: 0px 0px 10px {sombra_anim};">NOTA {nota_empresa}</h1>
            <h3 style="color: #FFFFFF; font-family: 'Montserrat', sans-serif; font-weight: 600; margin: 5px 0; font-size: 1rem;">{simbolo} | {crescimento:+.1f}%</h3>
            <p style="color: #A0A0A0; font-family: 'Montserrat', sans-serif; font-size: 0.75rem; margin-bottom: 0;">Comparativo 7d vs semana anterior.</p>
        </div>
        <style>@keyframes pulse-cor {{ 0% {{ box-shadow: 0 0 5px {sombra_anim}; transform: scale(1); }} 50% {{ box-shadow: 0 0 20px {cor_anim}; transform: scale(1.02); }} 100% {{ box-shadow: 0 0 5px {sombra_anim}; transform: scale(1); }} }}</style>
        """, unsafe_allow_html=True)

# ==========================================================
# 10. MOTOR DE ELITE (DISCIPLINA) - PARA TODOS OS USUÁRIOS
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🧠 Motor de Elite: Disciplina & Expansão</h3>", unsafe_allow_html=True)

agora_brasil = datetime.utcnow() - timedelta(hours=3)
dia_do_ano = agora_brasil.timetuple().tm_yday

frases = ["O sucesso é a soma de pequenos esforços repetidos.", "Grave aquele vídeo agora!", "A constância abre a porta da escala.", "Seu próximo vídeo pode ser viral.", "Feito é melhor que perfeito."]
missoes = ["Gravar 5 vídeos originais com gancho forte.", "Analisar 3 produtos novos no TikTok.", "Gravar 3 vídeos review do Produto Campeão.", "Revisar o vídeo mais vendido e replicar estilo."]
dicas = ["Invista 20% do lucro no negócio.", "Construa caixa de guerra.", "Impulsione o vídeo que vendeu bem orgânico.", "Diversifique faturando fora do TikTok."]

@st.cache_data(ttl=86400)
def buscar_oportunidade_do_dia(dt_cache):
    try:
        sys_op = "Estrategista de Negócios Sênior em Afiliados. Responda em JSON."
        pmt_op = "Gere uma tática de expansão digital (TikTok, YT Shorts, UGC, etc). Retorne JSON: {'titulo': '...', 'pitch': '...', 'passos': '1. Passo um... \\n2. Passo dois...'}"
        resp = cliente_openai.chat.completions.create(model="gpt-4o-mini", response_format={"type":"json_object"}, messages=[{"role":"system","content":sys_op},{"role":"user","content":pmt_op}], temperature=0.85)
        import json; return json.loads(resp.choices[0].message.content)
    except: return {"titulo": "Shopee Video", "pitch": "Reaproveite roteiros lá para segunda fonte.", "passos": "1. Crie conta afiliado.\n2. Suba o vídeo."}

op_hoje = buscar_oportunidade_do_dia(agora_brasil.strftime("%Y-%m-%d"))

col_m1, col_m2 = st.columns([1, 1])
with col_m1:
    st.info(f"💎 **Visão de Águia:** {frases[dia_do_ano % len(frases)]}")
    st.warning(f"📈 **Dica Financeira:** {dicas[dia_do_ano % len(dicas)]}")
    
    with st.container(border=True):
        st.markdown(f"**🚀 Oportunidade Oculta: {op_hoje.get('titulo', 'Nova Oportunidade')}**")
        st.markdown(f"<p style='font-size: 0.9em; color: #A0A0A0;'>{op_hoje.get('pitch', '')}</p>", unsafe_allow_html=True)
        with st.expander("🛠️ Ver Passo a Passo de Execução", expanded=False):
            st.markdown(f"**Como aplicar agora:**\n\n{op_hoje.get('passos', '')}")

if f"missao_{agora_brasil.strftime('%Y-%m-%d')}" not in st.session_state: st.session_state[f"missao_{agora_brasil.strftime('%Y-%m-%d')}"] = False

with col_m2:
    st.markdown(f"🎯 **Sua Missão de Hoje:** {missoes[dia_do_ano % len(missoes)]}")
    if not st.session_state[f"missao_{agora_brasil.strftime('%Y-%m-%d')}"]:
        if st.button("✅ CONCLUIR MISSÃO DE HOJE", type="primary", use_container_width=True):
            st.session_state[f"missao_{agora_brasil.strftime('%Y-%m-%d')}"] = True
            st.success("🔥 SENSACIONAL! Missão cravada."); st.balloons()
            if E_O_CEO and 'link_planilha_ativa' in globals() and link_planilha_ativa and robo_sheets:
                try:
                    aba = robo_sheets.open_by_key(extrair_id_planilha(link_planilha_ativa)).worksheet("Historico_Missoes")
                    if agora_brasil.strftime("%d/%m/%Y") not in aba.col_values(1): aba.append_row([agora_brasil.strftime("%d/%m/%Y"), "Concluída"])
                except Exception: pass
            time.sleep(2); st.rerun()
    else: st.success("Missão de Hoje Cumprida! 🦅")
# ==========================================================
# 11 a 13. FERRAMENTAS DE CRIAÇÃO E VISÃO (CEO E NOVATOS)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00E5FF;'>🔮 Radar de Tendências da Aurora</h3>", unsafe_allow_html=True)
if st.button("🔍 Buscar Tendência Oculta de Beleza (TikTok Shop)", type="primary", use_container_width=True):
    with st.spinner("Minerando produtos ocultos com a Aurora..."):
        try:
            res_rad = chamar_ia_global("Recomende 1 produto bombando. Porquê vende? Pitch sensorial de 9s. 3 Palavras-chave. Feche: 'Corre no carrinho!'", "Você é Aurora, especialista fofoqueira em TikTok Shop (Beleza).")
            st.success("✨ Radar captou sinal!")
            st.markdown(res_rad)
        except Exception: st.error("Erro no Radar.")

st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🔬 Laboratório de Insights e Conversão</h3>", unsafe_allow_html=True)
c_conv, c_feed = st.columns(2)
with c_conv:
    with st.container(border=True):
        st.markdown("<h4 style='color: #00FFFF;'>📈 Simulador de CTR</h4>", unsafe_allow_html=True)
        vw = st.number_input("👁️ Views", min_value=0, step=100)
        cq = st.number_input("🖱️ Cliques", min_value=0, step=10)
        vd = st.number_input("🛍️ Vendas", min_value=0, step=1)
        if vw > 0 and cq > 0:
            st.session_state["ultima_taxa_conversao"] = (vd / cq) * 100
            st.metric("CTR", f"{(cq / vw) * 100:.2f}%")
            st.metric("Conversão", f"{st.session_state['ultima_taxa_conversao']:.2f}%")
with c_feed:
    with st.container(border=True):
        st.markdown("<h4 style='color: #00FFFF;'>🗣️ Mente do Cliente</h4>", unsafe_allow_html=True)
        pd_alvo = st.text_input("📦 Nome do Produto em Análise:", placeholder="Máscara Novex")
        txt_cmt = st.text_area("Cole comentários:", height=100)
        if st.button("🧠 Hackear Sentimento", use_container_width=True):
            if txt_cmt:
                with st.spinner("Analisando dor..."):
                    res_fd = chamar_ia_global(f"Prod: {pd_alvo}. Coment: {txt_cmt}. Dê: MAIOR DESEJO, PRINCIPAL OBJEÇÃO e GANCHO MATADOR (1 linha cada).", "Analista Comportamental TikTok")
                    st.session_state["ultimo_feedback_analisado"] = res_fd
                    st.success("Hackeado!")
            else: st.warning("Cole os comentários.")
        if "ultimo_feedback_analisado" in st.session_state: st.markdown(st.session_state["ultimo_feedback_analisado"])

st.divider()
st.markdown("<h3 style='text-align: center; color: #00E5FF;'>🎬 Máquina de Roteiros (Geração via Texto)</h3>", unsafe_allow_html=True)
if st.button("⚡ GERAR 3 ROTEIROS DE 9s (Estratégia)", type="primary", use_container_width=True):
    with st.spinner("Forjando roteiros de elite..."):
        fd = st.session_state.get("ultimo_feedback_analisado", "Dores capilares.")
        st.markdown(chamar_ia_global(f"Crie 3 roteiros TikTok de 9s. Público: Feminino Buscadora de Atalhos. Produto principal. Objeção para usar no roteiro 3: {fd}. PROIBIDO falar de cura e milagre. Tom: Amiga fofoqueira (Aurora).", "Copywriter TikTok Shop"))

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

# ==========================================
# 🧠 BANCO DE MEMÓRIA PERMANENTE INVISÍVEL
# ==========================================
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
    except Exception as e:
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

# ==========================================================
# 🔥 CSS VIP 3D: CONSOLE NEUMÓRFICO E ÁGUIA REATIVA
# ==========================================================
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

audio_gravado = st.audio_input(" ", label_visibility="collapsed")

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

                        # ==========================================
                        # 📊 CÁLCULO DE 100% DO BANCO DE DADOS E APLICATIVO
                        # ==========================================
                        canal_ativo = nome_canal_ativo if 'nome_canal_ativo' in globals() else "Conta Geral"

                        # 1. Contar Usuários Cadastrados
                        total_usuarios = 0
                        bd_users = conectar_banco_usuarios("ler")
                        if bd_users is not None:
                            total_usuarios = len(bd_users)

                        # 2. Dados Financeiros
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
                        
                        # 3. Puxar a NOTA DA OPERAÇÃO exata
                        estado_atual = simbolo if 'simbolo' in globals() else "Desconhecido"
                        nota_atual = nota_empresa if 'nota_empresa' in globals() else "N/A"

                        missao_hoje_str = missao_hoje if 'missao_hoje' in globals() else "Nenhuma."
                        dias_concluidos_str = dias_cumpridos if 'dias_cumpridos' in globals() else 0
                        taxa_acerto_str = taxa_acerto if 'taxa_acerto' in globals() else 0.0

                        tendencia_atual = historico_radar[-1]['Conteudo'] if 'historico_radar' in globals() and historico_radar else "Nenhuma tendência."
                        funil_atual = historico_raiox[-1]["Funil"] if 'historico_raiox' in globals() and historico_raiox else "Nenhum funil mapeado."

                        conversao_atual = st.session_state.get("ultima_taxa_conversao", 0.0)
                        feedback_atual = st.session_state.get("ultimo_feedback_analisado", "Nenhum feedback mapeado.")

                        # 🔥 PROMPT ORIGINAL RESTAURADO: A AMIGA FOFOQUEIRA DO BEM E DIRETORA OMNISCIENTE
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

                        # ==========================================
                        # 🔥 PLANO A (ElevenLabs) e PLANO B (Voz Grátis)
                        # ==========================================
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
        const audio = document.getElementById('audio_aurora');
        const bars = document.querySelectorAll('.bar');
        audio.addEventListener('play', () => {{ bars.forEach(bar => bar.classList.add('playing')); }});
        audio.addEventListener('pause', () => {{ bars.forEach(bar => bar.classList.remove('playing')); }});
        audio.addEventListener('ended', () => {{ bars.forEach(bar => bar.classList.remove('playing')); }});
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
                if st.button("🚨 EXCLUIR", use_container_width=True, type="primary") and email_excluir:
                    if email_excluir.strip().lower() == EMAIL_MESTRE: st.error("O CEO não pode ser banido!")
                    else:
                        try:
                            a_bd = robo_sheets.open_by_key(re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE).group(1)).worksheet("Banco_Usuarios")
                            em_col = a_bd.col_values(1)
                            if email_excluir.lower() in [e.lower() for e in em_col]:
                                a_bd.delete_rows(next(i for i,e in enumerate(em_col) if e.lower() == email_excluir.lower())+1)
                                st.success("Banido!"); time.sleep(1); st.rerun()
                            else: st.warning("Não encontrado.")
                        except: pass

# ==========================================================
# 17. MÁQUINA DE CRIAÇÃO 360º (MATRIZ V9.2 + PETS DINÂMICOS - V31.1)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00BFA5;'>🎬 Máquina de Criação 360º (V31.1)</h3>", unsafe_allow_html=True)

if "roteiro_temporario" not in st.session_state: 
    st.session_state["roteiro_temporario"] = None

def carregar_ultimo_roteiro_salvo(email_usr):
    if not robo_sheets: return None
    try:
        match_id = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
        if match_id:
            planilha_mestre = robo_sheets.open_by_key(match_id.group(1))
            try: aba_hist = planilha_mestre.worksheet("Historico_Roteiros")
            except:
                aba_hist = planilha_mestre.add_worksheet(title="Historico_Roteiros", rows="1000", cols="3")
                aba_hist.append_row(["Email", "DataHora", "JsonRoteiro"])
                return None
            
            registros = aba_hist.get_all_records()
            usuario_regs = [r for r in registros if str(r.get("Email","")).strip().lower() == email_usr.strip().lower()]
            if usuario_regs:
                return usuario_regs[-1].get("JsonRoteiro", None)
    except Exception: pass
    return None

def salvar_roteiro_no_drive(email_usr, json_str):
    if not robo_sheets: return
    try:
        match_id = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
        if match_id:
            planilha_mestre = robo_sheets.open_by_key(match_id.group(1))
            try: aba_hist = planilha_mestre.worksheet("Historico_Roteiros")
            except:
                aba_hist = planilha_mestre.add_worksheet(title="Historico_Roteiros", rows="1000", cols="3")
                aba_hist.append_row(["Email", "DataHora", "JsonRoteiro"])
            
            agora_str = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")
            aba_hist.append_row([email_usr, agora_str, json_str])
    except Exception: pass

email_sessao = st.session_state.get("email_usuario", "anonimo")
if not st.session_state["roteiro_temporario"]:
    roteiro_salvo_nuvem = carregar_ultimo_roteiro_salvo(email_sessao)
    if roteiro_salvo_nuvem:
        st.session_state["roteiro_temporario"] = roteiro_salvo_nuvem

pode_gerar_roteiro = True
usos_feitos = 0
aba_limites = None

if not E_O_CEO and robo_sheets:
    try:
        match_id = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
        if match_id:
            planilha_mestre = robo_sheets.open_by_key(match_id.group(1))
            try: aba_limites = planilha_mestre.worksheet("Limites_Roteiros")
            except:
                aba_limites = planilha_mestre.add_worksheet(title="Limites_Roteiros", rows="1000", cols="2")
                aba_limites.append_row(["Email", "Gerou"])
            
            lista_usos = aba_limites.col_values(1)
            usos_feitos = lista_usos.count(email_sessao)
            if usos_feitos >= 3:
                pode_gerar_roteiro = False
    except Exception: pass

with st.container(border=True):
    col_img, col_dados = st.columns([1, 1])
    with col_img: 
        img_produto = st.file_uploader("📸 Foto do Produto", type=["png", "jpg", "jpeg"], key="img_produto_roteiro")
    with col_dados:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if not pode_gerar_roteiro:
            st.error("🚨 LIMITE ATINGIDO! Você já gerou os seus 3 roteiros gratuitos. Faça o upgrade para a conta CEO para uso ilimitado.")
            btn_gerar_roteiro = st.button("⚡ LER RÓTULO E GERAR ESTRUTURA", type="primary", use_container_width=True, disabled=True)
        else:
            txt_botao = "⚡ LER RÓTULO E GERAR (Ilimitado)" if E_O_CEO else f"⚡ LER RÓTULO E GERAR ({3 - usos_feitos} Restantes)"
            btn_gerar_roteiro = st.button(txt_botao, type="primary", use_container_width=True)

if btn_gerar_roteiro and img_produto and pode_gerar_roteiro:
    with st.spinner("🦅 Forjando estrutura (Manual V9.2 + Pets Dinâmicos) e salvando na nuvem..."):
        try:
            img_b64_roteiro = base64.b64encode(img_produto.getvalue()).decode('utf-8')
            
            instrucao_ouro = """
            Analise a imagem APENAS para ler o nome do produto, marca, volume aproximado e quantidade de itens (1 unidade ou Kit).
            REGRA ABSOLUTA: NÃO descreva cores, formato ou textos da embalagem, pois o gerador já tem a foto original.
            
            [REGRA DE ESCALA FÍSICA E TAMANHO]
            - Se for Frasco/Líquido/Spray (ex: 250ml/300ml): Use a trava de frasco compacto (1:1 scale, compact palm size).
            - Se for Pote/Máscara/Kit (ex: 400g): Use a trava de pote médio (1:1 scale, standard cosmetic jar, do not oversize).

            [MANUAL DE AMBIENTES E PETS DINÂMICOS V9.2]
            - Sorteie 1 dos 22 Ambientes V9.2 (Varanda Tropical, Banheiro com Tempestade, Quarto Minimalista, Cozinha Rústica, Varanda de Praia, Escritório Criativo, Quintal Arborizado, Sala de Estar, Banheiro Moderno, Área Gourmet, Varanda com Garoa, Quarto Boho, Terraço Urbano, Cantinho de Leitura, Cozinha Americana, Varanda de Inverno, Jardim Vertical, Casa de Campo, Ateliê, Varanda Ensolarada, Corredor Verde, Urban Jungle).
            - Fator Animal (Mascotes Variados): Sorteie ou inclua organicamente um mascote de fundo realista para dar vida ao vlog (ex: um gato preguiçoso dormindo na poltrona/estante, um vira-lata caramelo deitado no tapete, um passarinho na janela aberta, etc.). Nunca repita o mesmo pet em todas as cenas.
            - Baguncinha Temática: Adicione micro-detalhes de caos cotidiano (xícara de café, óculos, livros, panos de prato, carregador de celular).

            [EXEMPLO PRONTO 1 - MOLDE DE IMAGEM (Mínimo 1100 caracteres)]
            RAW photography, close-up POV handheld mobile phone shot. Extreme hyper-realism: detailed natural skin pores, peach fuzz, subtle moisture on skin, NO artificial flash. Photorealistic young Brazilian woman (Aurora: dark hair, subtle bangs, intense conspiratorial expression, incredibly shiny and healthy-looking hair). A small, discrete black wireless lapel microphone is visibly clipped to the neckline of her shirt. [DESCREVA O AMBIENTE V9.2 ESCOLHIDO, A BAGUNCINHA ORGÂNICA E O PET SORTEADO NO FUNDO]. [CRITICAL: 1:1 real-world scale, strictly realistic product size and proportions, exact match to reference, do not oversize]. The exact product(s) [NOME/QUANTIDADE] resting on the table or held MUST look compact, light, and perfectly proportioned. Unfiltered UGC vlog style, 8k resolution.

            [EXEMPLO PRONTO 2 - MOLDE DE VÍDEO UNIFICADO (Mínimo 1600 caracteres)]
            - Shot 1 (Macro Hook & Physics): [POV intensely erratic handheld mobile video, documentary chaos aesthetic. Extreme dynamic spatial movement. The camera violently tilts up from a wooden table where the product(s) rest. Starts with an aggressive Macro Zoom In exclusively on the EXACT reference product(s) from the uploaded image. [CRITICAL: 1:1 real-world scale, strictly realistic product size and proportions, exact match to reference, do not oversize] (se for kit, especifique: one unit is held firmly, while the other units rest neatly on the table in the background). The items remain perfectly solid with micro-reflections bouncing off the plastic as sunlight hits them. SINGLE MOTION TRICK (The Trigger Tap): Her free index finger performs a deliberate micro-tap on the lid/cap twice to emphasize it. NO pixel melting.]
            - Shot 2 (Whip Pan & Visceral Emotion): [0:03: WHIP PAN and brutal focus pull! The camera violently tilts up and snaps focus onto Aurora's face (microfone de lapela visível na gola da camisa, decoração do ambiente V9.2 e o pet ao fundo). VISCERAL EMOTION ACTIVE: She leans in aggressively towards the lens (The Gossip Lean), her chest heaving slightly with urgent breathing, flashing a breathless, intensely serious expression of pure warning.]
            - Interaction (3D CTA): [She aggressively points her free index finger downwards towards the bottom corner of the screen. At this precise second, a highly realistic 3D floating orange shopping bag object materializes in the air near her pointing finger, casting realistic shadows. It is a physical 3D element pointing towards the UI button location.]
            Áudio (Inglês): [Audio captured via a wireless lapel microphone. Micro-ASMR intro (sound of product tap). Authentic room acoustics. Urgent, breathless, conspiratorial voice, speaking as if revealing a highly guarded secret].
            Fala da AURORA (Português - 100% Blindada Contra o Robô):
            "[Crie uma fala de 40 a 45 palavras exatas seguindo este tom: 'Amiga, você viu isso? O segredo para (benefício sensorial) e deixar o cabelo com toque de seda acabou de liberar na vitrine! O estoque desse lote tá derretendo em minutos. Já garanti o meu, corre na sacolinha antes que esgote!']"
            Texto na Tela (Nativo TikTok - Foco na Dor):
            - "⚠️ [PROBLEMA PRINCIPAL DO CABELO]? 🛑"
            - "[EFEITO/BENEFÍCIO SENSORIAL] ✨"
            - "LOTE SECRETO LIBERADO 🛒👇"

            Retorne EXATAMENTE no formato JSON estrito:
            {
                "prompt_imagem": "...",
                "prompt_video_completo": "...",
                "titulo_geral": "Como [resolver a dor principal do produto] em casa.",
                "titulo_solucao": "[Nome Exato do Produto e Quantidade].",
                "titulo_marca": "[Nome do Produto e Marca] resenha."
            }
            NÃO use hashtags. NUNCA cite logotipos.
            """
            
            resp = cliente_openai.chat.completions.create(
                model="gpt-4o-mini",
                response_format={ "type": "json_object" },
                messages=[{"role": "system", "content": "Diretor de Criação de Elite do TikTok Shop. Responda em JSON estrito seguindo os moldes."}, {"role": "user", "content": [
                    {"type": "text", "text": instrucao_ouro},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64_roteiro}"}}
                ]}],
                max_tokens=3500, temperature=0.75
            )
            
            conteudo_json = resp.choices[0].message.content.strip()
            st.session_state["roteiro_temporario"] = conteudo_json
            
            salvar_roteiro_no_drive(email_sessao, conteudo_json)
            
            if not E_O_CEO and aba_limites is not None:
                try: aba_limites.append_row([email_sessao, "Sim"])
                except Exception: pass
                
            st.success("✅ Estrutura gerada com sucesso!")
            time.sleep(1); st.rerun()
        except Exception as e: st.error(f"Erro ao gerar: {e}")

if st.session_state["roteiro_temporario"]:
    try:
        dados_r = json.loads(st.session_state["roteiro_temporario"])
        with st.container(border=True):
            st.markdown("<h4 style='color:#D4AF37;'>📸 PROMPT DE IMAGEM</h4>", unsafe_allow_html=True)
            st.code(dados_r.get("prompt_imagem",""), language="text")
            
            st.markdown("<h4 style='color:#D4AF37;'>🎬 PROMPT DE VÍDEO COMPLETO E UNIFICADO</h4>", unsafe_allow_html=True)
            st.code(dados_r.get("prompt_video_completo",""), language="text")
            
            st.markdown("<h4 style='color:#00FFFF;'>🔑 TÍTULOS SEO (Separados)</h4>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1: 
                st.caption("🔍 Geral (Dor)")
                st.code(dados_r.get("titulo_geral",""), language="text")
            with c2: 
                st.caption("💡 Solução (Produto)")
                st.code(dados_r.get("titulo_solucao",""), language="text")
            with c3: 
                st.caption("🏷️ Marca (Resenha)")
                st.code(dados_r.get("titulo_marca",""), language="text")
                
        if st.button("🗑️ Limpar Roteiro Atual", use_container_width=True): 
            st.session_state["roteiro_temporario"] = None
            st.rerun()
    except Exception: 
        st.warning("Erro ao carregar o formato do roteiro.")
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
        
        duvida_gestao = st.text_input("Qual é o seu maior desafio de gestão ou rotina hoje?", placeholder="Ex: Como divido o meu tempo entre gravar vídeos e pesquisar produtos novos?")
        if st.button("Pedir Conselho de Gestão", use_container_width=True):
            if not duvida_gestao:
                st.warning("⚠️ Escreva a sua dúvida para a Diretoria analisar.")
            else:
                with st.spinner("🦅 A Aurora está a calcular a estratégia do seu império..."):
                    sys_gestao = "Você é Aurora, COO (Diretora de Operações) da ÉLÉVO e mentora de negócios do CEO. Seu tom é de estrategista implacável, focada em gestão de tempo, finanças e mentalidade milionária. Não use palavras clichês de autoajuda."
                    prompt_gestao = f"O nosso CEO está com o seguinte desafio de gestão na empresa: '{duvida_gestao}'. \nDê um conselho de negócio frio, direto e baseado em números. Forneça 3 passos de ação executáveis."
                    
                    resposta_mentoria = chamar_ia_global(prompt_gestao, sys_gestao)
                    
                    st.info("💡 **Parecer Executivo da Aurora:**")
                    st.markdown(resposta_mentoria)
