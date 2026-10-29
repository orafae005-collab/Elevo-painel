# ÉLÉVO V16.8.2 — continuidade V16.8.1 + referência visual fixa do produto e microfísica nos 21 ambientes.
import base64
import requests
import time
import random
import streamlit as st

# COMPATIBILIDADE ÉLÉVO V8.1 — Streamlit >= 1.62 (outubro/2026)
# A biblioteca streamlit-cookies-manager 0.2.0 utiliza @st.cache internamente.
# O Streamlit moderno removeu st.cache; esta função faz cache só dos dados
# de derivação de chave da biblioteca, sem alterar as demais funções do app.
if not hasattr(st, "cache"):
    st.cache = st.cache_data

import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta
import gspread
import re
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
import hashlib
import hmac
import secrets
from streamlit_cookies_manager import EncryptedCookieManager
import io
import json
import html as html_std
from zoneinfo import ZoneInfo
from gtts import gTTS

# ==========================================================
# 1. CONFIGURAÇÃO DA CHAVE DA IA E DO APP (🔥 V6.0 - SaaS VIP)
# ==========================================================
st.set_page_config(page_title="ÉLÉVO | Intelligence Studio", page_icon="🦅", layout="wide", initial_sidebar_state="collapsed")

try:
    CHAVE_OPENAI_VIP = st.secrets["OPENAI_API_KEY"]
    cliente_openai = OpenAI(api_key=CHAVE_OPENAI_VIP)
except KeyError:
    st.error("🚨 ALERTA: Falta a chave OPENAI_API_KEY no cadeado (Secrets).")
    st.stop()

def chamar_ia_global(prompt, sistema_contexto="Você é um assistente estratégico."):
    try:
        validar_cota_ia()
        response = cliente_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sistema_contexto},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.replace("*", "").strip()
    except Exception:
        return "ERRO_API: Não foi possível concluir a solicitação de IA. Verifique sua cota e a conexão."

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

# Cookie persistente cifrado e autenticado; nunca usar e-mail em query string como credencial.
# Configure AUTH_COOKIE_PASSWORD em .streamlit/secrets.toml com >=32 caracteres aleatórios.
AUTH_COOKIE_PASSWORD = str(st.secrets.get("AUTH_COOKIE_PASSWORD", ""))
if len(AUTH_COOKIE_PASSWORD) < 32:
    st.error("Configure AUTH_COOKIE_PASSWORD (mínimo de 32 caracteres) nos Secrets para habilitar login seguro.")
    st.stop()
cookies = EncryptedCookieManager(prefix="elevo_v80_", password=AUTH_COOKIE_PASSWORD)
if not cookies.ready():
    st.stop()

if "usuario_logado" not in st.session_state:
    st.session_state.update(usuario_logado=False, email_usuario="", nome_usuario="", auth_metodo="")

# Remover dados pessoais/transitórios SEM alterar o banco persistente por Gmail.
# Não usar apenas usuario_logado=False: o Streamlit conserva session_state.
SESSAO_DADOS_PRIVADOS = {
    "historico_viva_voz", "ultimo_audio_b64", "ultimo_hash_audio",
    "historico_v11_cenas", "historico_v11_ganchos", "roteiro_temporario",
    "influencer_atual", "email_inf_carregado", "dados_prontos",
    "ultimo_feedback_analisado", "ultima_taxa_conversao", "txt_diretrizes_360",
    "modo_entidade_v9", "audio_boas_vindas_b64", "email_bv_verificado",
    "mostrar_player_bv", "erro_audio_bv", "bv_conclusao_pendente",
    "bv_recarregamento_login", "google_pendente", "google_erro",
    "elevo_inf_preset_id", "elevo_inf_obs", "elevo_inf_erro_gravacao",
    "elevo_ceo_identity_v1641_loaded", "elevo_ceo_original_v1682",
    "elevo_ambiente_id", "elevo_ambiente_obs", "elevo_ambiente_carregado_email", "elevo_ambiente_aviso", "elevo_ambiente_historico_infinito", "elevo_ambiente_ultimo_infinito",
}

def limpar_sessao_privada():
    for chave in list(st.session_state.keys()):
        if chave in SESSAO_DADOS_PRIVADOS or chave.startswith(("missao_", "input_", "audio_input_", "bv_login_")):
            st.session_state.pop(chave, None)

def ativar_identidade(email, nome, metodo):
    identidade_anterior = str(st.session_state.get("email_usuario", "")).strip().lower()
    if identidade_anterior and identidade_anterior != email.strip().lower():
        limpar_sessao_privada()
    st.session_state.update(
        usuario_logado=True, email_usuario=email.strip().lower(),
        nome_usuario=nome.strip() or "Usuário", auth_metodo=metodo,
    )


def senha_hash(senha, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, 310000)
    return "pbkdf2_sha256$310000$" + salt.hex() + "$" + digest.hex()

def senha_confere(senha, armazenada):
    armazenada = str(armazenada or "")
    if armazenada.startswith("pbkdf2_sha256$"):
        try:
            _, it, salt, digest = armazenada.split("$", 3)
            calculado = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), int(it))
            return hmac.compare_digest(calculado, bytes.fromhex(digest))
        except (ValueError, TypeError):
            return False
    # Compatibilidade temporária com cadastros antigos: migrar na primeira autenticação.
    return hmac.compare_digest(armazenada.encode(), senha.encode())

def conectar_banco_usuarios(acao, email="", nome="", senha=""):
    if not robo_sheets: return None
    try:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
        planilha = robo_sheets.open_by_key(match.group(1))
        try:
            aba = planilha.worksheet("Banco_Usuarios")
        except gspread.exceptions.WorksheetNotFound:
            aba = planilha.add_worksheet(title="Banco_Usuarios", rows="1000", cols="3")
            aba.append_row(["Email", "Nome", "Senha"])
        if acao == "ler": return aba.get_all_records()
        if acao == "salvar":
            aba.append_row([email, nome, senha_hash(senha)])
            return True
        if acao == "migrar":
            rows = aba.get_all_records()
            for i, row in enumerate(rows, start=2):
                if str(row.get("Email", "")).strip().lower() == email.lower():
                    aba.update_cell(i, 3, senha_hash(senha))
                    return True
    except Exception:
        return None

def criar_token(email):
    # Expiração de 30 dias para impedir sessões de senha indefinidas.
    payload = json.dumps({"email": email.strip().lower(), "versao": 2,
                          "exp": int(time.time()) + (30 * 24 * 3600)},
                         separators=(",", ":")).encode()
    dado = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    assinatura = hmac.new(AUTH_COOKIE_PASSWORD.encode(), dado.encode(), hashlib.sha256).hexdigest()
    return dado + "." + assinatura

def ler_token(token):
    try:
        dado, assinatura = token.split(".", 1)
        esperado = hmac.new(AUTH_COOKIE_PASSWORD.encode(), dado.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(assinatura, esperado): return ""
        payload = json.loads(base64.urlsafe_b64decode(dado + "=" * (-len(dado) % 4)))
        # Tokens v1 não tinham validade: solicitar um novo login com senha.
        if payload.get("versao") != 2 or not int(time.time()) < int(payload.get("exp", 0)):
            return ""
        return str(payload.get("email", "")).strip().lower()
    except Exception:
        return ""

def entrar_usuario(email, nome):
    limpar_sessao_privada()
    st.session_state.update(
        usuario_logado=True, email_usuario=email, nome_usuario=nome, auth_metodo="senha",
        # Após ENTRAR, a mensagem precisa ser verificada nesta execução,
        # sem exigir F5 nem reaproveitar o estado de outro utilizador.
        email_bv_verificado="", mostrar_player_bv=False,
        audio_boas_vindas_b64=None, erro_audio_bv="",
        # Permite UM recarregamento do navegador após login, sem F5 manual.
        bv_recarregamento_login=secrets.token_hex(8)
    )
    cookies["login"] = criar_token(email)
    cookies.save()

# ==========================================================
# AUTENTICAÇÃO OPCIONAL GOOGLE (OIDC, sem acessar o Google Flow)
# Configurar [auth] e [auth.google] nos Secrets (ver guia do pacote).
# st.login valida ID token; autorização vem do cadastro e vínculo salvo.
# ==========================================================
def google_habilitado():
    try:
        configuracao = st.secrets.get("auth", {})
        provedor = configuracao.get("google", {})
        return bool(configuracao.get("cookie_secret") and configuracao.get("redirect_uri")
                    and provedor.get("client_id") and provedor.get("client_secret")
                    and provedor.get("server_metadata_url"))
    except (AttributeError, KeyError, TypeError):
        return False

GOOGLE_ATIVO = google_habilitado()

def google_identidade_atual():
    """Somente Google autenticado/validado e com e-mail verificado."""
    if not GOOGLE_ATIVO or not st.user.is_logged_in:
        return None
    ident = st.user
    email = str(ident.get("email", "")).strip().lower()
    sub = str(ident.get("sub", "")).strip()
    email_confirmado = ident.get("email_verified", False) in (True, "true", "True", "1", 1)
    if not sub or not email_confirmado or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return None
    return {"email": email, "sub": sub, "nome": str(ident.get("name", "")).strip() or email.split("@")[0]}


def _aba_google_vinculos():
    if not robo_sheets:
        raise RuntimeError("Banco de dados indisponível")
    planilha = robo_sheets.open_by_key(re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE).group(1))
    try:
        return planilha.worksheet("Google_Vinculos")
    except gspread.exceptions.WorksheetNotFound:
        aba = planilha.add_worksheet(title="Google_Vinculos", rows="1000", cols="4")
        aba.append_row(["Google_Sub", "Email_Google", "Email_Conta", "Criado_Em"])
        return aba


def buscar_vinculo_google(ident):
    """Não confundir e-mail Google com autorização; o vínculo usa sub."""
    registros = _aba_google_vinculos().get_all_records()
    correspondencias = [r for r in registros if str(r.get("Google_Sub", "")) == ident["sub"]]
    if len(correspondencias) != 1:
        return None
    registro = correspondencias[0]
    if str(registro.get("Email_Google", "")).strip().lower() != ident["email"]:
        return None
    return str(registro.get("Email_Conta", "")).strip().lower()


def gravar_vinculo_google(ident, email_conta):
    email_conta = email_conta.strip().lower()
    if ident["email"] != email_conta:
        raise ValueError("Por segurança, a conta Google precisa usar o mesmo e-mail do cadastro.")
    aba = _aba_google_vinculos()
    registros = aba.get_all_records()
    for r in registros:
        if str(r.get("Google_Sub", "")) == ident["sub"]:
            return str(r.get("Email_Conta", "")).strip().lower() == email_conta
        if str(r.get("Email_Conta", "")).strip().lower() == email_conta:
            raise ValueError("Esta conta já está vinculada a outro Google.")
    aba.append_row([ident["sub"], ident["email"], email_conta,
                    datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")])
    return True


def usuario_cadastrado_por_email(email):
    if email == EMAIL_MESTRE.strip().lower():
        return {"Email": EMAIL_MESTRE, "Nome": "Sócio", "Senha": ""}
    usuarios = conectar_banco_usuarios("ler")
    if usuarios is None:
        raise RuntimeError("Não foi possível consultar os cadastros. Tente novamente.")
    return next((u for u in usuarios if str(u.get("Email", "")).strip().lower() == email), None)


def entrar_com_google_vinculado(ident):
    email_vinculado = buscar_vinculo_google(ident)
    if not email_vinculado:
        return False
    conta = usuario_cadastrado_por_email(email_vinculado)
    if not conta:
        return False  # Cadastro removido / revogado.
    ativar_identidade(email_vinculado, str(conta.get("Nome", "Usuário")), "google")
    return True

ident_google = google_identidade_atual() if GOOGLE_ATIVO else None
if GOOGLE_ATIVO and st.user.is_logged_in:
    # Identidade Google assume precedência, NUNCA herda a sessão de outro Gmail.
    if not ident_google:
        st.session_state.update(usuario_logado=False, email_usuario="", nome_usuario="", auth_metodo="")
        st.session_state["google_erro"] = "Conta Google sem identidade ou e-mail verificado."
    else:
        try:
            if not entrar_com_google_vinculado(ident_google):
                if st.session_state.get("email_usuario") != ident_google["email"]:
                    limpar_sessao_privada()
                st.session_state.update(usuario_logado=False, email_usuario="", nome_usuario="", auth_metodo="")
                st.session_state["google_pendente"] = True
                st.session_state.pop("google_erro", None)
            else:
                st.session_state.pop("google_pendente", None)
                st.session_state.pop("google_erro", None)
        except Exception:
            st.session_state.update(usuario_logado=False, email_usuario="", nome_usuario="", auth_metodo="")
            st.session_state["google_erro"] = "Não foi possível validar o vínculo Google no banco. Acesso não liberado."

# Códigos antigos ?sessao=... eram falsificáveis: eliminar e nunca aceitá-los.
if "sessao" in st.query_params:
    del st.query_params["sessao"]
if (not st.session_state["usuario_logado"] and cookies.get("login")
        and not (GOOGLE_ATIVO and st.user.is_logged_in)):
    email_cookie = ler_token(cookies.get("login", ""))
    if email_cookie == EMAIL_MESTRE.strip().lower():
        ativar_identidade(EMAIL_MESTRE, "Sócio", "senha")
    elif email_cookie:
        registros = conectar_banco_usuarios("ler")
        if registros is not None:
            usuario = next((u for u in registros if str(u.get("Email", "")).strip().lower() == email_cookie), None)
            if usuario:
                ativar_identidade(email_cookie, str(usuario.get("Nome", "Usuário")), "senha")
    if not st.session_state["usuario_logado"]:
        cookies.pop("login", None)
        cookies.save()

if not st.session_state["usuario_logado"]:
    # Visual V13: somente apresentação; nenhuma mudança na lógica de credenciais/cookies.
    st.markdown("""
    <style>
      [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, header { display:none !important; }
      [data-testid="stAppViewContainer"] {
        background: radial-gradient(ellipse 85% 70% at 48% -18%, rgba(0,229,255,.12), transparent 73%),
                    radial-gradient(circle at 90% 90%, rgba(212,175,55,.07), transparent 45%),
                    #0B0E14 !important;
      }
      .block-container {max-width: 1050px; padding-top: clamp(1.3rem,3.5vw,3rem); padding-bottom: 2rem;}
      .elevo-login-hero {text-align:center; position:relative; margin: 0 auto 1.55rem; padding: 0 10px;}
      .elevo-login-eagle {position:relative; margin:0 auto 10px; width:82px; height:82px; display:grid;
        place-items:center; border:1px solid rgba(0,229,255,.32); border-radius:25px;
        background:linear-gradient(145deg,rgba(20,30,43,.98),rgba(8,12,19,.96));
        box-shadow: 0 0 0 6px rgba(0,229,255,.035), 0 16px 42px rgba(0,0,0,.3), 0 0 35px rgba(0,229,255,.11);
        animation: elevo-login-float 5.5s ease-in-out infinite;}
      .elevo-login-eagle:before {content:""; position:absolute; inset:-9px; border-radius:30px;
        background:conic-gradient(from 10deg,transparent,rgba(0,229,255,.27),transparent,rgba(212,175,55,.22),transparent);
        filter:blur(10px); z-index:-1; animation:elevo-login-ring 16s linear infinite;}
      .elevo-login-eagle span {font-size:39px; filter:drop-shadow(0 0 8px rgba(0,255,157,.35));}
      .elevo-login-brand {font-family:Montserrat, sans-serif !important; font-size:clamp(3rem,7vw,4.65rem);
        font-weight:900; line-height:1.1; letter-spacing:.13em; margin:0; padding-left:.13em;
        background:linear-gradient(110deg,#D4AF37 4%,#00FF9D 28%,#00E5FF 51%,#8cc0ff 75%,#D4AF37 97%);
        background-size:230% 100%; -webkit-background-clip:text; background-clip:text;
        -webkit-text-fill-color:transparent; animation:elevo-login-spectrum 9s ease infinite;
        filter:drop-shadow(0 2px 13px rgba(0,229,255,.16));}
      .elevo-login-kicker {color:#A4B3C3 !important; font-size:.74rem; letter-spacing:.21em;
        font-weight:600; text-transform:uppercase; margin:8px 0 10px;}
      .elevo-login-chip {display:inline-flex; gap:7px; align-items:center; padding:6px 13px;
        border-radius:30px; font:600 .68rem Montserrat,sans-serif; letter-spacing:.1em;
        color:#A7FDE1; background:rgba(0,255,157,.06); border:1px solid rgba(0,255,157,.24);}
      .elevo-login-dot {display:inline-block; height:7px;width:7px; border-radius:50%; background:#00FF9D;
        box-shadow:0 0 9px #00FF9D; animation:elevo-login-blink 2.7s ease-in-out infinite;}
      div[data-testid="stVerticalBlockBorderWrapper"]:has(.elevo-login-card-mark) {
        border-radius:24px !important; border:1px solid rgba(0,229,255,.32) !important;
        background: linear-gradient(140deg,rgba(28,34,48,.93),rgba(9,14,22,.95)) !important;
        box-shadow: 0 16px 60px rgba(0,0,0,.36),0 0 28px rgba(0,229,255,.065),inset 0 1px rgba(255,255,255,.06) !important;
        backdrop-filter:blur(16px);}
      .elevo-login-card-mark {margin:0 0 4px; color:#94A3B8; letter-spacing:.17em;
        text-transform:uppercase; font:600 .65rem Montserrat,sans-serif; text-align:center;}
      [data-testid="stForm"] {background:rgba(6,11,19,.18) !important; border-radius:16px !important;
        border:1px solid rgba(0,229,255,.13) !important;}
      .stTextInput input {border:1px solid rgba(0,229,255,.23) !important;
        background:rgba(7,12,21,.7) !important; color:#F1F5F9 !important;
        border-radius:11px !important; min-height:45px !important;}
      .stTextInput input:focus {border-color:#00E5FF !important; box-shadow:0 0 0 2px rgba(0,229,255,.10) !important;}
      [data-testid="stFormSubmitButton"] button[kind="primary"] {background:linear-gradient(105deg,#002B5B,#065a7e) !important;
        color:white !important; border:1px solid #00E5FF !important; border-radius:12px !important;
        min-height:46px !important; box-shadow:0 8px 24px rgba(0,229,255,.14) !important; font-weight:800 !important;}
      [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {filter:brightness(1.14); transform:translateY(-1px);}
      [data-baseweb="tab-list"] {gap:.3rem !important; background:rgba(0,0,0,.12) !important;
        padding:.35rem; border-radius:12px;}
      [data-baseweb="tab"] {border-radius:10px;}
      @keyframes elevo-login-spectrum {0%,100% {background-position:0% 50%} 50% {background-position:100% 50%}}
      @keyframes elevo-login-float {0%,100% {transform:translateY(0)} 50% {transform:translateY(-4px)}}
      @keyframes elevo-login-ring {to {transform:rotate(360deg)}}
      @keyframes elevo-login-blink {0%,100% {opacity:1} 50% {opacity:.38}}
      @media(max-width:750px) {
        .block-container {padding:1rem .9rem 2rem;}
        .elevo-login-eagle {width:67px;height:67px;border-radius:22px;}
        .elevo-login-eagle span {font-size:32px;}
        .elevo-login-kicker {font-size:.62rem;letter-spacing:.13em;}
        .elevo-login-hero {margin-bottom:1.15rem;}
        div[data-testid="stHorizontalBlock"]:has(.elevo-login-card-mark)>div[data-testid="stColumn"]:not(:has(.elevo-login-card-mark)) {display:none !important;}
        div[data-testid="stHorizontalBlock"]:has(.elevo-login-card-mark)>div[data-testid="stColumn"]:has(.elevo-login-card-mark) {flex:1 1 100% !important;width:100% !important;min-width:0 !important;}
      }
      @media(prefers-reduced-motion:reduce) {
        .elevo-login-eagle,.elevo-login-eagle:before,.elevo-login-brand,.elevo-login-dot {animation:none !important;}
      }
    </style>
    <section class="elevo-login-hero" aria-label="Portal ÉLÉVO">
      <div class="elevo-login-eagle" aria-hidden="true"><span>🦅</span></div>
      <h1 class="elevo-login-brand">ÉLÉVO</h1>
      <p class="elevo-login-kicker">Inteligência • Vendas • Criação</p>
      <div class="elevo-login-chip"><span class="elevo-login-dot"></span> PORTAL DE ACESSO VIP</div>
    </section>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown('<div class="elevo-login-card-mark">IDENTIFICAÇÃO SEGURA • ÉLÉVO</div>', unsafe_allow_html=True)
            if GOOGLE_ATIVO and ident_google and st.session_state.get("google_pendente"):
                st.markdown("### 🔗 Finalizar acesso com Google")
                st.info(f"Google autenticado: **{ident_google['email']}**. Confirme o vínculo ou crie seu primeiro acesso.")
                try:
                    conta_google_atual = usuario_cadastrado_por_email(ident_google["email"])
                    if conta_google_atual:
                        st.caption("Este e-mail já possui conta ÉLÉVO. Confirme a senha atual para vincular com segurança.")
                        with st.form("vinculo_google_seguro"):
                            senha_de_vinculo = st.text_input("Senha atual da sua conta ÉLÉVO", type="password")
                            confirmar_vinculo = st.form_submit_button("🔗 Vincular minha conta Google", use_container_width=True)
                        if confirmar_vinculo:
                            senha_ok = (hmac.compare_digest(senha_de_vinculo, SENHA_MESTRA)
                                        if ident_google["email"] == EMAIL_MESTRE.strip().lower()
                                        else senha_confere(senha_de_vinculo, conta_google_atual.get("Senha", "")))
                            if senha_ok and senha_de_vinculo:
                                try:
                                    if gravar_vinculo_google(ident_google, ident_google["email"]):
                                        ativar_identidade(ident_google["email"], str(conta_google_atual.get("Nome", "Usuário")), "google")
                                        st.rerun()
                                except Exception:
                                    st.error("Não foi possível gravar o vínculo. Tente novamente.")
                            else:
                                st.error("Senha atual inválida. Vínculo não autorizado.")
                    else:
                        st.caption("Primeiro acesso com Google? Você poderá usar esta conta sem criar outra senha.")
                        if st.button("✨ Criar meu acesso com Google", use_container_width=True):
                            try:
                                # Senha aleatória não entregue ao usuário; login por OIDC.
                                # Primeiro registra o vínculo. Se o cadastro de usuário
                                # falhar, a mesma identidade Google poderá concluir depois.
                                if not gravar_vinculo_google(ident_google, ident_google["email"]):
                                    raise RuntimeError("Falha ao vincular")
                                cadastrado = conectar_banco_usuarios("salvar", ident_google["email"], ident_google["nome"], secrets.token_urlsafe(48))
                                if not cadastrado:
                                    raise RuntimeError("Falha ao criar conta")
                                ativar_identidade(ident_google["email"], ident_google["nome"], "google")
                                st.rerun()
                            except Exception:
                                st.error("Não foi possível concluir o cadastro Google. Não crie outra conta: tente novamente com o mesmo Google quando o banco estiver disponível.")
                except Exception:
                    st.error("O banco de usuários está indisponível. Acesso Google não foi liberado.")
                if st.button("Cancelar / escolher outra conta Google", key="cancelar_google_pendente"):
                    st.logout()
                st.stop()
            if st.session_state.get("google_erro"):
                st.error(st.session_state["google_erro"])
                if st.button("Sair da conta Google atual"):
                    st.logout()
                st.stop()
            aba_login, aba_cadastro = st.tabs(["🚀 Entrar", "✨ Criar Conta"])
            with aba_login:
                st.markdown("<h4 style='text-align: center; margin-bottom: 20px;'>Acesso à Central</h4>", unsafe_allow_html=True)
                with st.form("form_login"):
                    email_input = st.text_input("📧 Seu Gmail", placeholder="Digite seu e-mail...")
                    senha_input = st.text_input("🔑 Senha", type="password", placeholder="Digite sua senha...")
                    lembrar_dados = st.checkbox("Manter conectado neste dispositivo", value=True)
                    submit_login = st.form_submit_button("🚀 ENTRAR", use_container_width=True, type="primary")
                
                if submit_login:
                    email_clean = email_input.strip().lower()
                    if email_clean == EMAIL_MESTRE.strip().lower() and senha_input == SENHA_MESTRA:
                        entrar_usuario(EMAIL_MESTRE, "Sócio")
                        if not lembrar_dados: cookies.pop("login", None); cookies.save()
                        st.rerun()
                    elif email_clean and senha_input:
                        with st.spinner("A verificar credenciais no servidor..."):
                            usuarios = conectar_banco_usuarios("ler")
                            if usuarios is not None:
                                usuario_encontrado = next((u for u in usuarios if str(u.get("Email","")).strip().lower() == email_clean and senha_confere(senha_input, u.get("Senha", ""))), None)
                                if usuario_encontrado:
                                    entrar_usuario(email_clean, str(usuario_encontrado.get("Nome", "Usuário")))
                                    if not lembrar_dados: cookies.pop("login", None); cookies.save()
                                    if not str(usuario_encontrado.get("Senha", "")).startswith("pbkdf2_sha256$"):
                                        conectar_banco_usuarios("migrar", email_clean, senha=senha_input)
                                    st.rerun()
                                else: st.error("🚨 Conta não encontrada ou senha incorreta!")
                            else: st.error("🚨 Erro de conexão com o banco de dados.")
                    else: st.warning("⚠️ Preencha o e-mail e a senha.")
                if GOOGLE_ATIVO:
                    st.caption("────────── ou ──────────")
                    if st.button("🌐 Continuar com Google", key="btn_login_google", use_container_width=True):
                        st.login("google")
                else:
                    st.caption("🔒 Acesso Google disponível após configurar OAuth nos Secrets.")

            with aba_cadastro:
                st.markdown("<h4 style='text-align: center; margin-bottom: 20px;'>Nova Conta VIP</h4>", unsafe_allow_html=True)
                novo_nome = st.text_input("👤 Como quer ser chamado?", placeholder="Seu apelido...")
                novo_email = st.text_input("📧 Seu melhor E-mail", placeholder="exemplo@gmail.com")
                nova_senha = st.text_input("🔑 Crie uma Senha", type="password", placeholder="Sua senha secreta...")
                if st.button("✨ CRIAR MINHA CONTA", use_container_width=True, type="secondary"):
                    email_clean = novo_email.strip().lower()
                    if not novo_nome or not email_clean or not nova_senha: st.warning("⚠️ Preencha os 3 campos.")
                    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email_clean): st.warning("Informe um e-mail válido.")
                    elif len(nova_senha) < 8: st.warning("A senha deve ter ao menos 8 caracteres.")
                    elif email_clean == EMAIL_MESTRE.strip().lower(): st.error("🚨 Este e-mail é reservado ao CEO.")
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

# Solução para browsers mobile/Streamlit Cloud que montam o player só após F5:
# uma única atualização REAL do navegador após o login validado. O cookie já
# foi gravado em entrar_usuario(), então o login é recuperado automaticamente.
# O token é consumido antes de atualizar, impedindo loop caso a sessão persista.
bv_nonce_refresh = st.session_state.pop("bv_recarregamento_login", "")
if bv_nonce_refresh:
    st.info("🦅 Acesso autorizado. Inicializando sua mensagem da Aurora...")
    components.html(f"""
    <script>
    (function() {{
        try {{
            const pagina = window.parent;
            const chave = "elevo_bv_refresh_{bv_nonce_refresh}";
            if (pagina.sessionStorage.getItem(chave) !== "feito") {{
                pagina.sessionStorage.setItem(chave, "feito");
                window.setTimeout(function() {{ pagina.location.reload(); }}, 1600);
            }}
        }} catch (erro) {{
            // O browser pode limitar navegação de frames incorporados.
            // A reexecução interna da geração de áudio permanece como defesa.
        }}
    }})();
    </script>
    """, height=0, width=0)
    # Permite prosseguir sem ficar preso caso alguma política do browser
    # bloqueie a atualização automática.
    if st.button("▶ Continuar para o painel", key="bv_login_continuar_fallback"):
        st.rerun()
    st.stop()

# ==========================================================
# LIMITE GERAL DE CONSUMO DE IA — custos previsíveis por conta / dia.
# As 3 criações gratuitas são um limite SEPARADO, mantido como antes.
# Sheets não oferece transação atômica: para SaaS em escala usar banco com
# transações e rate limit no servidor/provedor de API.
# ==========================================================
def validar_cota_ia():
    email = str(st.session_state.get("email_usuario", "")).strip().lower()
    if not email or not st.session_state.get("usuario_logado"):
        raise RuntimeError("Faça login para usar a inteligência artificial.")
    if email == EMAIL_MESTRE.strip().lower():
        return
    if not robo_sheets:
        raise RuntimeError("Controle de consumo indisponível; tente novamente.")
    try:
        max_dia = max(1, int(st.secrets.get("LIMITE_IA_DIARIO", 30)))
        planilha = robo_sheets.open_by_key(re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE).group(1))
        try:
            aba = planilha.worksheet("Consumo_IA_Diario")
        except gspread.exceptions.WorksheetNotFound:
            aba = planilha.add_worksheet(title="Consumo_IA_Diario", rows="2000", cols="3")
            aba.append_row(["Email", "Data", "Tipo"])
        hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d")
        usados = sum(1 for r in aba.get_all_records()
                     if str(r.get("Email", "")).strip().lower() == email and str(r.get("Data", "")) == hoje)
        if usados >= max_dia:
            raise RuntimeError(f"Limite de {max_dia} operações de IA atingido hoje. Volte amanhã.")
        # Reserva antes da requisição para evitar consumo livre em caso de falha.
        aba.append_row([email, hoje, "IA"])
    except RuntimeError:
        raise
    except Exception:
        raise RuntimeError("Não foi possível validar a cota de IA. Tente novamente.")

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
    
    /* Refinamento de textura, sem modificar paleta nem cenários */
    .block-container {{ max-width: 1380px; padding-top: 1.4rem; padding-bottom: 3rem; }}
    [data-testid="stVerticalBlockBorderWrapper"] {{ overflow-wrap: anywhere; }}
    [data-testid="stForm"], [data-testid="stExpander"], [data-testid="stMetric"] {{
        background-image: linear-gradient(155deg, rgba(255,255,255,0.025), rgba(255,255,255,0)) !important;
    }}
    .stButton > button:focus-visible {{ outline: 2px solid {accent_gold} !important; outline-offset: 2px; }}
    @media (max-width: 700px) {{
        .block-container {{ padding: 1rem .85rem 2.5rem; }}
        .titulo-elevo {{ font-size: 2.8rem; letter-spacing: 2px; }}
        .subtitulo {{ font-size: .8rem; letter-spacing: 1px; margin-bottom: 18px; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
        .titulo-elevo, .stButton > button {{ animation: none !important; transition: none !important; }}
    }}
    {ajuste_modo_claro_css}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# V13 - REFINAMENTO VISUAL RESPONSIVO (SEM TROCAR A PALETA)
# ==========================================================
st.markdown("""
<style>
  /* Cartões com microtextura e profundidade suave; preserva todos os tons oficiais. */
  [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stForm"], [data-testid="stExpander"] {
    background-image:linear-gradient(155deg,rgba(255,255,255,.04),rgba(255,255,255,0) 38%),
                     radial-gradient(circle at 94% 4%,rgba(0,229,255,.035),transparent 44%) !important;
    border-radius:19px !important;
  }
  [data-testid="stVerticalBlockBorderWrapper"] {min-width:0;}
  .block-container {width:100%; max-width:1320px;}
  [data-testid="stHorizontalBlock"] {min-width:0; align-items:stretch;}
  [data-testid="stColumn"] {min-width:0 !important;}
  [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
  [data-baseweb="select"]>div {border-radius:12px !important; transition:border-color .16s ease,box-shadow .16s ease;}
  [data-testid="stFileUploader"] section {border-radius:16px !important;}
  .stButton button, [data-testid="stFormSubmitButton"] button {min-height:42px; letter-spacing:.015em;
     transition:box-shadow .2s ease,transform .2s ease,border-color .2s ease !important;}
  .stButton button:active, [data-testid="stFormSubmitButton"] button:active {transform:scale(.985) !important;}
  [data-baseweb="tab-list"] {gap:6px;overflow-x:auto;scrollbar-width:thin;}
  [data-baseweb="tab"] {border-radius:11px 11px 5px 5px;white-space:nowrap;}
  .elevo-v13-panel-title {display:flex;align-items:center;gap:10px; margin:0 0 9px;
     color:#00E5FF;font-size:.82rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;}
  .elevo-v13-led {height:8px;width:8px;border-radius:50%;display:inline-block;
     background:#00FF9D;box-shadow:0 0 4px #00FF9D, 0 0 13px rgba(0,255,157,.45);
     animation:elevo-v13-beat 2.6s ease-in-out infinite;}
  .elevo-v13-description {font-size:.77rem !important; margin:0 0 6px;color:#94A3B8 !important;}
  /* Um brilho leve percorre as fatias; preserva as cores do grafico e seu hover. */
  [data-testid="stPlotlyChart"] g.slice path {animation:elevo-v13-ring 5s ease-in-out infinite;}
  [data-testid="stPlotlyChart"] g.slice:nth-child(2n) path {animation-delay:.9s;}
  [data-testid="stPlotlyChart"] g.slice:nth-child(3n) path {animation-delay:1.8s;}
  @keyframes elevo-v13-ring {0%,100% {filter:brightness(1)} 50% {filter:brightness(1.13)}}
  @keyframes elevo-v13-beat {0%,100% {opacity:1;transform:scale(1)} 50% {opacity:.45;transform:scale(.75)}}
  @media (max-width:767px) {
     .block-container {padding:1rem .8rem 2.5rem !important;}
     [data-testid="stHorizontalBlock"] {flex-wrap:wrap !important;gap:.7rem !important;}
     [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex:1 1 100% !important; width:100% !important; min-width:0 !important;
     }
     .titulo-elevo {font-size:clamp(2.4rem,11vw,3rem) !important;letter-spacing:.08em !important;}
     .subtitulo {font-size:.7rem !important;letter-spacing:.09em !important;}
     .stButton button,[data-testid="stFormSubmitButton"] button {min-height:46px !important;}
     [data-testid="stVerticalBlockBorderWrapper"] {padding:0 !important;}
     [data-testid="stPlotlyChart"] {max-width:100% !important;overflow:hidden;}
  }
  @media (prefers-reduced-motion:reduce) {
    .elevo-v13-led,.stButton button,[data-testid="stPlotlyChart"] g.slice path {animation:none !important;transition:none !important;}
  }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# ÉLÉVO STUDIO V16 | DIREÇÃO DE ARTE: DASHBOARD ESCURO PREMIUM
# Sidebar desktop / navegação horizontal responsiva no mobile.
# Não altera a execução dos módulos existentes.
# ==========================================================
cor_fundo_studio = "#F4F7FC" if modo_claro else "#0A1020"
cor_cartao_studio = "#FFFFFF" if modo_claro else "#101B30"
cor_texto_studio = "#15213B" if modo_claro else "#E7EDF8"
cor_secundaria_studio = "#64748B" if modo_claro else "#94A6C5"
cor_borda_studio = "rgba(23,45,82,.13)" if modo_claro else "rgba(118,160,232,.15)"
st.markdown(f"""
<style>
  :root {{color-scheme:{'light' if modo_claro else 'dark'};}}
  [data-testid="stAppViewContainer"] {{background:{cor_fundo_studio}!important;}}
  .block-container {{max-width:1480px!important; padding:1.15rem 2rem 4rem!important;}}
  h1,h2,h3,h4,h5,h6,p,label,li {{color:{cor_texto_studio}!important;}}
  [data-testid="stCaptionContainer"] p {{color:{cor_secundaria_studio}!important;}}
  [data-testid="stVerticalBlockBorderWrapper"],[data-testid="stMetric"],
  [data-testid="stForm"],[data-testid="stExpander"] {{
    background:{cor_cartao_studio}!important;
    background-image:none!important; border:1px solid {cor_borda_studio}!important;
    border-radius:18px!important; box-shadow:0 8px 24px rgba(3,12,28,.11)!important;
    backdrop-filter:none!important;}}
  [data-testid="stMetricValue"] div {{color:{'#1363D6' if modo_claro else '#E7F0FF'}!important;}}
  [data-testid="stMetricLabel"] p {{font-weight:650!important;}}
  [data-testid="stFormSubmitButton"] button[kind="primary"],.stButton>button[kind="primary"] {{
    border-color:#367DFF!important; background:linear-gradient(115deg,#1A66E9,#3187FB)!important;
    box-shadow:0 6px 20px rgba(34,107,242,.20)!important;}}
  [data-baseweb="tab-list"] {{background:{'rgba(31,76,135,.06)' if modo_claro else '#15233B'}!important;}}
  [data-baseweb="tab"] {{border-radius:10px!important;}}
  .elevo-sidebar {{position:fixed;left:0;top:0;bottom:0;width:224px;z-index:99991;
    background:{'#EAF0F8' if modo_claro else '#0C1628'};border-right:1px solid {cor_borda_studio};
    padding:25px 15px;overflow-y:auto; box-shadow:5px 0 24px rgba(0,0,0,.04);}}
  .elevo-sidebar .marca {{font:900 1.38rem Montserrat,sans-serif;letter-spacing:.08em;color:{cor_texto_studio};padding:0 12px 18px;}}
  .elevo-sidebar .marca small {{font:600 .56rem Montserrat,sans-serif;letter-spacing:.17em;color:{cor_secundaria_studio};display:block;margin-top:4px;}}
  .elevo-sidebar .secao {{font:700 .62rem Montserrat,sans-serif;letter-spacing:.13em;color:{cor_secundaria_studio};margin:25px 10px 8px;}}
  .elevo-sidebar a {{display:flex;align-items:center;gap:10px;padding:12px;border-radius:11px;
    color:{cor_secundaria_studio};text-decoration:none;font:600 .81rem Montserrat,sans-serif;transition:background .16s;}}
  .elevo-sidebar a:hover,.elevo-sidebar a:focus {{background:rgba(48,132,255,.16);color:{cor_texto_studio};}}
  .elevo-sidebar a.principal {{background:linear-gradient(110deg,#154FAE,#226CE1);color:white;}}
  .elevo-dash-header {{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;
    background:linear-gradient(120deg,{'#EEF4FF,#FFFFFF' if modo_claro else '#111F39,#112B46'});
    border:1px solid {cor_borda_studio};border-radius:19px;padding:24px 29px;margin:0 0 24px;}}
  .elevo-kpi-grid {{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;margin-bottom:21px;}}
  .elevo-kpi {{border:1px solid rgba(111,164,230,.15);border-radius:15px;
    padding:17px 18px;background:linear-gradient(135deg,{('#FFFFFF,#F8FAFF' if modo_claro else '#111F35,#0D192D')});}}
  .elevo-kpi .kpi-label {{display:block;color:{cor_secundaria_studio};font-size:.72rem;font-weight:650;margin:0 0 12px;}}
  .elevo-kpi .kpi-value {{font-size:clamp(1.1rem,2vw,1.65rem);letter-spacing:-.035em;
    font-weight:850;color:{cor_texto_studio};margin-bottom:5px;overflow-wrap:anywhere;}}
  .elevo-kpi .kpi-caption {{font-size:.68rem;color:{cor_secundaria_studio};}}
  .elevo-shortcut-grid {{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:9px 0 28px;}}
  .elevo-shortcut-grid a {{text-decoration:none;color:{cor_texto_studio};background:{cor_cartao_studio};
    border:1px solid {cor_borda_studio};border-radius:15px;padding:18px 15px;display:block;font-weight:750;
    transition:transform .16s, border-color .16s;}}
  .elevo-shortcut-grid a:hover {{transform:translateY(-2px);border-color:#388AFF;}}
  .elevo-shortcut-grid span {{display:block;color:{cor_secundaria_studio};font-weight:400;font-size:.72rem;margin-top:5px;}}
  .elevo-dash-header h1 {{font-size:clamp(1.45rem,3.5vw,2.25rem);letter-spacing:-.02em;margin:3px 0 8px!important;
    line-height:1.12;color:{cor_texto_studio}!important;}}
  .elevo-dash-header p {{font-size:.88rem;color:{cor_secundaria_studio}!important;margin:0;}}
  .elevo-kicker {{font-weight:800;font-size:.67rem;letter-spacing:.13em;color:#5AA8FF;}}
  .elevo-status-chip {{display:inline-flex;align-items:center;gap:7px;border:1px solid rgba(71,220,169,.26);
    padding:9px 13px;border-radius:100px;color:{'#16744B' if modo_claro else '#70E2BD'};
    background:rgba(33,180,133,.07);font:700 .69rem Montserrat,sans-serif;}}
  .elevo-v13-panel-title {{color:{'#1262BC' if modo_claro else '#8CBFFF'}!important;}}
  .elevo-v13-led {{background:#4DB4FF;box-shadow:0 0 10px rgba(63,156,255,.34);}}
  div[data-testid="stPlotlyChart"] {{border-radius:14px;overflow:hidden;}}
  #elevo-dashboard-top,#painel,#missoes,#radar,#aurora,#criacao,#academia {{scroll-margin-top:75px;}}
  @media(min-width:1000px) {{
    [data-testid="stMainBlockContainer"],.block-container {{margin-left:224px!important;
      width:calc(100% - 224px)!important;max-width:calc(1480px - 224px)!important;}}
  }}
  @media(max-width:700px) {{.elevo-kpi-grid,.elevo-shortcut-grid {{grid-template-columns:1fr;}}}}
  @media(max-width:999px) {{
    .elevo-sidebar {{position:fixed;top:0;left:0;right:0;width:100%;height:54px;padding:8px 12px;
      display:flex;gap:7px;align-items:center;overflow-x:auto;overflow-y:hidden;white-space:nowrap;
      border-right:0;border-bottom:1px solid {cor_borda_studio};box-shadow:0 3px 18px rgba(0,0,0,.11);}}
    .elevo-sidebar .marca {{font-size:.88rem;padding:0 10px 0 0;flex:0 0 auto;}}
    .elevo-sidebar .marca small,.elevo-sidebar .secao {{display:none;}}
    .elevo-sidebar a {{font-size:.72rem;flex:0 0 auto;padding:9px 12px;}}
    [data-testid="stMainBlockContainer"],.block-container {{margin-left:0!important;
      width:100%!important;padding:4.4rem .85rem 3rem!important;}}
    .elevo-dash-header {{padding:19px 17px!important;margin-top:8px;}}
  }}
  @media(prefers-reduced-motion:reduce) {{*,*::before,*::after {{animation-duration:.01ms!important;transition-duration:.01ms!important;}}}}
</style>
<aside class="elevo-sidebar" aria-label="Navegação do ÉLÉVO">
  <div class="marca">◈ ÉLÉVO<small>INTELLIGENCE STUDIO</small></div>
  <div class="secao">WORKSPACE</div>
  <a class="principal" href="#painel">▦ Visão geral</a>
  <a href="#missoes">◷ Missões</a>
  <a href="#radar">◈ Insights e tendências</a>
  <a href="#ambientes">🌍 Ambientes</a>
  <div class="secao">CRIATIVIDADE</div>
  <a href="#elenco-elevo">◈ Elenco de influenciadoras</a>
  <a href="#criacao">▣ Criação de prompts</a>
  <a href="#academia">◉ Academia</a>
</aside>
""", unsafe_allow_html=True)
# ==========================================================
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
st.markdown('<div id="ancora-topo"></div><div id="painel"></div>', unsafe_allow_html=True)
nome_cabecalho = html_std.escape(str(st.session_state.get("nome_usuario", "Sócio")))
st.markdown(f"""
<section class="elevo-dash-header" aria-label="Boas-vindas ao ÉLÉVO">
 <div><div class="elevo-kicker">PAINEL ESTRATÉGICO • ÉLÉVO V16</div>
 <h1>Visão geral, {nome_cabecalho}</h1>
 <p>Inteligência, criação e suas operações em um só lugar.</p></div>
 <span class="elevo-status-chip">● PAINEL ATIVO</span>
</section>""", unsafe_allow_html=True)

# ==========================================================
# 2.5. BOAS-VINDAS CINEMÁTICA (100% VINCULADA AO GMAIL ÚNICO)
# CORREÇÃO PONTUAL: exibe após login, tenta autoplay e oferece play imediato.
# ==========================================================
if "email_bv_verificado" not in st.session_state:
    st.session_state["email_bv_verificado"] = ""
if "audio_boas_vindas_b64" not in st.session_state:
    st.session_state["audio_boas_vindas_b64"] = None
if "mostrar_player_bv" not in st.session_state:
    st.session_state["mostrar_player_bv"] = False
if "erro_audio_bv" not in st.session_state:
    st.session_state["erro_audio_bv"] = ""

email_logado_agora = str(st.session_state.get("email_usuario", "")).strip().lower()
nome_apenas_fala = str(st.session_state.get("nome_usuario", "Sócio")).strip()


def registrar_boas_vindas_confirmada(email):
    """Marca na planilha após o evento real de fim de reprodução do áudio."""
    if not robo_sheets or not email:
        return False
    try:
        match_id = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
        if not match_id:
            return False
        planilha = robo_sheets.open_by_key(match_id.group(1))
        try:
            aba = planilha.worksheet("Memoria_Audio_VIP")
        except gspread.exceptions.WorksheetNotFound:
            aba = planilha.add_worksheet(title="Memoria_Audio_VIP", rows="1000", cols="2")
            aba.append_row(["Gmail_Unico", "Data_Acesso"])
        ja_registrados = [str(e).strip().lower() for e in aba.col_values(1) if "@" in str(e)]
        if email not in ja_registrados:
            agora_reg = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")
            aba.append_row([email, agora_reg])
        return True
    except Exception:
        return False


if (st.session_state.get("usuario_logado") and email_logado_agora
        and st.session_state["email_bv_verificado"] != email_logado_agora):
    # Esta verificação acontece na própria execução imediatamente após o login.
    st.session_state["email_bv_verificado"] = email_logado_agora
    st.session_state["mostrar_player_bv"] = False
    st.session_state["audio_boas_vindas_b64"] = None
    st.session_state["erro_audio_bv"] = ""

    # Em falhas temporárias do Sheets, não ocultar silenciosamente a mensagem.
    precisa_tocar = True
    if robo_sheets:
        try:
            match_id = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
            if match_id:
                planilha_mestre = robo_sheets.open_by_key(match_id.group(1))
                try:
                    aba_bv = planilha_mestre.worksheet("Memoria_Audio_VIP")
                except gspread.exceptions.WorksheetNotFound:
                    aba_bv = planilha_mestre.add_worksheet(title="Memoria_Audio_VIP", rows="1000", cols="2")
                    aba_bv.append_row(["Gmail_Unico", "Data_Acesso"])
                lista_gmails_ja_ouviram = [
                    str(e).strip().lower() for e in aba_bv.col_values(1) if "@" in str(e)
                ]
                precisa_tocar = email_logado_agora not in lista_gmails_ja_ouviram
        except Exception:
            pass

    if precisa_tocar:
        texto_cinematico = f"Protocolo de Elite ativado. Bem-vindo à ÉLÉVO, {nome_apenas_fala}. Eu sou a Aurora, a sua Diretora de Operações e Inteligência Artificial. A partir deste segundo, você não joga mais para competir. Você joga para dominar. O seu império acaba de ser conectado ao meu núcleo. Eu vou rastrear tendências ocultas do mercado, hackear as objeções dos seus clientes e forjar os seus roteiros de vendas com precisão cirúrgica. O trabalho pesado fica comigo. Sistemas 100% online. O jogo virou."
        audio_bytes = None

        # O espaço é mostrado enquanto a voz é preparada; não é preciso recarregar.
        aviso_audio_bv = st.empty()
        aviso_audio_bv.info("🦅 Aurora está preparando sua primeira mensagem de boas-vindas...")
        try:
            CHAVE_ELEVEN = st.secrets.get("ELEVENLABS_API_KEY", "")
            if CHAVE_ELEVEN:
                try:
                    resp_voz = requests.post(
                        "https://api.elevenlabs.io/v1/text-to-speech/MLAEAegxkMReslK34j8T",
                        json={"text": texto_cinematico, "model_id": "eleven_turbo_v2_5", "voice_settings": {"stability": 0.50, "similarity_boost": 0.85, "style": 0.40, "use_speaker_boost": True}},
                        headers={"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": CHAVE_ELEVEN},
                        timeout=10
                    )
                    if resp_voz.status_code == 200 and resp_voz.content:
                        audio_bytes = resp_voz.content
                except Exception:
                    pass

            if not audio_bytes:
                tts = gTTS(text=texto_cinematico, lang='pt', tld='com.br')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                audio_bytes = fp.getvalue()
        except Exception:
            st.session_state["erro_audio_bv"] = "Não foi possível carregar a voz da Aurora neste momento."
        finally:
            aviso_audio_bv.empty()

        if audio_bytes:
            st.session_state["audio_boas_vindas_b64"] = base64.b64encode(audio_bytes).decode('utf-8')
            st.session_state["mostrar_player_bv"] = True
            # Registrar o Gmail apenas quando o áudio terminar (evento ended).
            # Streamlit precisa de uma execução nova para montar o componente
            # de voz depois da chamada de TTS/cookies. Na primeira tentativa
            # o painel abria, mas o iframe do áudio só aparecia após F5.
            # Esta segunda execução é automática, uma única vez por geração;
            # na próxima o email já foi verificado e o MP3 é reaproveitado.
            st.rerun()

if st.session_state.get("erro_audio_bv"):
    st.warning(st.session_state["erro_audio_bv"])
    if st.button("🔄 TENTAR CARREGAR ÁUDIO NOVAMENTE", key="btn_repetir_bv"):
        st.session_state["email_bv_verificado"] = ""
        st.rerun()

# A execução do MP3 ocorre no navegador, então a confirmação deve vir do
# evento "ended" via componente Streamlit V2 (conexão JS -> Python). O iframe
# anterior só escondia a caixa e não gravava a confirmação no Google Sheets.
if "bv_conclusao_pendente" not in st.session_state:
    st.session_state["bv_conclusao_pendente"] = ""


def concluir_audio_aurora():
    """Chamado SOMENTE pelo evento JS 'ended', após reprodução completa."""
    email = str(st.session_state.get("email_usuario", "")).strip().lower()
    if not email or not st.session_state.get("usuario_logado"):
        return
    if not st.session_state.get("mostrar_player_bv"):
        return
    # O áudio acabou: não reabrir/reexecutar durante os reruns da sessão.
    st.session_state["email_bv_verificado"] = email
    st.session_state["mostrar_player_bv"] = False
    st.session_state["audio_boas_vindas_b64"] = None
    # Se o Sheets ficar indisponível, manter a pendência para nova tentativa.
    st.session_state["bv_conclusao_pendente"] = email
    if registrar_boas_vindas_confirmada(email):
        st.session_state["bv_conclusao_pendente"] = ""


# Tenta sincronizar uma confirmação pendente, sem reproduzir a voz outra vez.
if (st.session_state.get("bv_conclusao_pendente")
        and st.session_state["bv_conclusao_pendente"] == email_logado_agora):
    if registrar_boas_vindas_confirmada(email_logado_agora):
        st.session_state["bv_conclusao_pendente"] = ""
    else:
        st.warning("A Aurora terminou a mensagem, mas a confirmação ainda não foi salva. "
                   "O sistema tentará sincronizar novamente na próxima interação.")

if st.session_state.get("mostrar_player_bv") and st.session_state.get("audio_boas_vindas_b64"):
    # V2 permite receber um evento do navegador no Python sem recarregar a
    # página ou simular cliques. Disponível no Streamlit 1.62+ do aplicativo.
    aurora_player = st.components.v2.component(
        name="elevo_aurora_player_termino_v15",
        html="""
        <div id="caixa-intro">
            <h3>🦅 MENSAGEM DA DIRETORIA</h3>
            <p id="identificacao-intro">Conta autenticada: <b id="email-intro"></b></p>
            <p id="status-intro" role="status" aria-live="polite">
                A Aurora tentará iniciar a mensagem automaticamente.
            </p>
            <button id="btn-tocar" type="button">▶ REPRODUZIR MENSAGEM</button>
            <div id="visualizer-intro" aria-hidden="true">
                <span class="bar"></span><span class="bar"></span>
                <span class="bar"></span><span class="bar"></span>
                <span class="bar"></span><span class="bar"></span>
                <span class="bar"></span><span class="bar"></span>
            </div>
            <audio id="audio-intro" preload="auto" playsinline></audio>
        </div>
        """,
        css="""
        #caixa-intro {
            box-sizing: border-box; width: 100%; max-width: 600px;
            margin: 10px auto; padding: 30px; min-height: 262px;
            background: linear-gradient(145deg, #0a0a0a, #141414);
            border: 2px solid #D4AF37; border-radius: 16px;
            box-shadow: 0 0 25px rgba(212,175,55,.2);
            text-align: center; font-family: Montserrat, sans-serif;
            transition: opacity 1s ease;
        }
        #caixa-intro h3 { color: #D4AF37; margin: 0 0 10px;
            font-family: Montserrat,sans-serif; font-size: 1.25rem;
            text-transform: uppercase; letter-spacing: 1px; }
        #identificacao-intro { color: #A0A0A0; font-size: 13px; margin: 10px 0; }
        #email-intro { color: #00FFFF; overflow-wrap: anywhere; }
        #status-intro { color: #A0A0A0; font-size: 14px; margin: 18px 0 20px; }
        #btn-tocar { background: linear-gradient(90deg,#D4AF37,#B8860B);
            color:#111; border:none; padding:15px 32px; font-size:16px;
            font-weight:900; border-radius:50px; cursor:pointer;
            box-shadow:0 5px 15px rgba(212,175,55,.4);
            text-transform:uppercase; font-family:Montserrat,sans-serif; }
        #visualizer-intro { display:none; justify-content:center;
            align-items:center; gap:4px; height:60px; margin-top:10px; }
        .bar { width:8px; height:4px; background:#D4AF37;
            border-radius:4px; display:inline-block; }
        .bar.playing { background:#00FFFF;
            animation: aurora-bounce .4s infinite alternate ease-in-out; }
        .bar:nth-child(2) {animation-delay:.1s} .bar:nth-child(3) {animation-delay:.2s}
        .bar:nth-child(4) {animation-delay:.3s} .bar:nth-child(5) {animation-delay:.1s}
        .bar:nth-child(6) {animation-delay:.4s} .bar:nth-child(7) {animation-delay:.2s}
        @keyframes aurora-bounce {from {height:4px;opacity:.5}
            to {height:40px;opacity:1;box-shadow:0 0 10px #00FFFF}}
        @media (max-width:480px) {#caixa-intro {padding:25px 14px;}
            #btn-tocar {font-size:14px; padding:14px 20px;}}
        """,
        js="""
        export default function (component) {
            const {parentElement, data, setTriggerValue} = component;
            const container = parentElement.querySelector('#caixa-intro');
            const btn = parentElement.querySelector('#btn-tocar');
            const aud = parentElement.querySelector('#audio-intro');
            const vis = parentElement.querySelector('#visualizer-intro');
            const status = parentElement.querySelector('#status-intro');
            const email = parentElement.querySelector('#email-intro');
            const bars = parentElement.querySelectorAll('#caixa-intro .bar');
            if (!container || !btn || !aud || !data?.audio) return;
            // A conta e os bytes são dados, nunca HTML executável.
            email.textContent = data.email || '';
            aud.src = 'data:audio/mpeg;base64,' + data.audio;
            let concluido = false;

            function reproduzir() {
                if (concluido) return;
                try {
                    const tentativa = aud.play();
                    if (tentativa && typeof tentativa.catch === 'function') {
                        tentativa.catch(() => {
                            btn.style.display = 'inline-block';
                            status.textContent = 'Toque em reproduzir para ouvir a Aurora.';
                        });
                    }
                } catch (_) {
                    btn.style.display = 'inline-block';
                    status.textContent = 'Toque em reproduzir para ouvir a Aurora.';
                }
            }
            const onPlaying = () => {
                btn.style.display = 'none';
                vis.style.display = 'flex';
                status.textContent = 'Mensagem da Aurora em reprodução.';
                container.style.borderColor = '#00FFFF';
                container.style.boxShadow = '0 0 25px rgba(0,255,255,.2)';
                bars.forEach(bar => bar.classList.add('playing'));
            };
            const onPause = () => bars.forEach(bar => bar.classList.remove('playing'));
            const onError = () => {
                if (!concluido) {
                    btn.style.display = 'inline-block';
                    status.textContent = 'Não foi possível reproduzir. Toque para tentar novamente.';
                }
            };
            const onEnded = () => {
                if (concluido) return;
                concluido = true; // Impede confirmação duplicada.
                bars.forEach(bar => bar.classList.remove('playing'));
                btn.style.display = 'none';
                vis.style.display = 'none';
                status.textContent = 'Mensagem concluída. Registrando automaticamente...';
                // Aciona o callback Python que salva o Gmail em Memoria_Audio_VIP.
                // Não aciona a confirmação em "play", "pause" ou carregamento.
                setTriggerValue('concluido', true);
            };
            btn.addEventListener('click', reproduzir);
            aud.addEventListener('playing', onPlaying);
            aud.addEventListener('pause', onPause);
            aud.addEventListener('error', onError);
            aud.addEventListener('ended', onEnded);
            reproduzir();
            return () => {
                btn.removeEventListener('click', reproduzir);
                aud.removeEventListener('playing', onPlaying);
                aud.removeEventListener('pause', onPause);
                aud.removeEventListener('error', onError);
                aud.removeEventListener('ended', onEnded);
            };
        }
        """,
    )
    aurora_player(
        key="elevo_aurora_audio_atual",
        data={"email": email_logado_agora, "audio": st.session_state["audio_boas_vindas_b64"]},
        on_concluido_change=concluir_audio_aurora,
    )

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
    st.markdown("""
    <nav class="elevo-shortcut-grid" aria-label="Acesso rápido às ferramentas">
      <a href="#criacao">▣ Criação 360º<span>Imagem e vídeo: gerar e copiar prompts</span></a>
      <a href="#aurora">✧ Aurora IA<span>Orientações e comandos por voz</span></a>
      <a href="#missoes">◷ Missões<span>Hábitos e progresso</span></a>
    </nav>""", unsafe_allow_html=True)

with st.expander("🔐 Minha Conta e Google", expanded=False):
    st.caption("Identidade atual: " + str(st.session_state.get("email_usuario", "")))
    st.caption("Método de acesso: " + str(st.session_state.get("auth_metodo", "senha")).upper())
    if GOOGLE_ATIVO and not (st.user.is_logged_in):
        st.info("Vincule sua conta Google usando o mesmo e-mail. O sistema confirmará sua senha após o retorno do Google.")
        if st.button("🌐 Vincular minha conta Google", key="btn_vincular_google_logado"):
            st.login("google")
    elif GOOGLE_ATIVO:
        st.success("Conta Google autenticada. Vínculo protegido pelo identificador Google.")
    else:
        st.caption("O administrador ainda precisa configurar Google OAuth para liberar esta opção.")

if st.button("Sair da Conta (Logout)", key="btn_logout"):
    cookies.pop("login", None)
    cookies.save()
    limpar_sessao_privada()
    st.session_state.clear()  # inclui widgets, uploads e textos da conta anterior
    if GOOGLE_ATIVO and st.user.is_logged_in:
        st.logout()
    st.rerun()

# ==========================================================
# 4 a 9 E 14. NÚCLEO FINANCEIRO VIP E GRÁFICOS (EXCLUSIVO DO CEO)
# ==========================================================
def extrair_id_planilha(url):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else None

def parse_valor_brasileiro(valor):
    """Valores do Sheets: 1.234,56 / 1234.56 / R$ 1.234,56.

    Trata pd.NA, None, NaN e NaT antes de converter para texto:
    pd.NA não aceita avaliação booleana (valor or "").
    """
    try:
        if pd.isna(valor):
            return 0.0
    except (TypeError, ValueError):
        # Valores inesperados não escalares serão tratados como texto.
        pass
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    texto = re.sub(r"[^0-9,.\-]", "", str(valor))
    if not texto or texto == "-":
        return 0.0
    if "," in texto and "." in texto:
        # O último separador é o decimal; o outro é o de milhar.
        decimal, milhares = (",", ".") if texto.rfind(",") > texto.rfind(".") else (".", ",")
        texto = texto.replace(milhares, "").replace(decimal, ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return 0.0

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
    for obrigatoria, padrao in (("Data", ""), ("Produto", "Sem nome"),
                                ("Status", ""), ("Quantidade", 0), ("Comissao_R$", 0)):
        if obrigatoria not in df.columns:
            df[obrigatoria] = padrao
    df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce").fillna(0)
    df["Comissao_R$"] = df["Comissao_R$"].apply(parse_valor_brasileiro)
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

    st.markdown(f"### 📊 Comissões e vendas: {nome_canal_ativo}")
    aprovado_str = f"R$ {aprovado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    pendente_str = f"R$ {pendente:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    campeao_str = html_std.escape(str(produto_campeao)[:12] + "..." if len(str(produto_campeao)) > 12 else str(produto_campeao))

    c_txt_v = "#D4AF37" if not modo_claro else "#B8860B"
    c_txt_t = "#A0A0A0" if not modo_claro else "#555555"
    st.markdown(f"""
    <div class="elevo-kpi-grid" role="group" aria-label="Resumo das vendas e comissões">
        <article class="elevo-kpi"><span class="kpi-label">💰 Comissões registradas</span>
          <div class="kpi-value">{aprovado_str}</div><span class="kpi-caption">Período selecionado</span></article>
        <article class="elevo-kpi"><span class="kpi-label">◷ Comissões pendentes</span>
          <div class="kpi-value">{pendente_str}</div><span class="kpi-caption">Aguardando confirmação</span></article>
        <article class="elevo-kpi"><span class="kpi-label">★ Produto campeão</span>
          <div class="kpi-value">{campeao_str}</div><span class="kpi-caption">Maior comissão do período</span></article>
    </div>
    """, unsafe_allow_html=True)

    if not df_timeline.empty and not df_campeao.empty:
        with st.expander("💠 ÉLÉVO PULSE | Inteligência Financeira", expanded=True):
            col_g1, col_g2 = st.columns(2, gap="medium")
            pulso_tom = "#005C66" if modo_claro else "#00E5FF"
            pulso_ponto = "#B8860B" if modo_claro else "#D4AF37"
            fundo_tema = "#F4F6F9" if modo_claro else "#0B0E14"
            texto_sutil = "#475569" if modo_claro else "#94A3B8"

            with col_g1:
                st.markdown('<div class="elevo-v13-panel-title"><span class="elevo-v13-led"></span> 📡 Pulso de Comissões</div>', unsafe_allow_html=True)
                st.caption("Evolução do período, sem barras: sinal contínuo e interativo.")
                serie = df_timeline.sort_values("Data_Parsed")
                fig_pulso = go.Figure()
                fig_pulso.add_trace(go.Scatter(
                    x=serie["Data_Parsed"], y=serie["Comissao_R$"],
                    mode="lines", hoverinfo="skip", showlegend=False,
                    line=dict(color=pulso_tom, width=12, shape="spline", smoothing=0.45),
                    opacity=0.12
                ))
                fig_pulso.add_trace(go.Scatter(
                    x=serie["Data_Parsed"], y=serie["Comissao_R$"],
                    mode="lines+markers", name="Comissões",
                    line=dict(color=pulso_tom, width=3.5, shape="spline", smoothing=0.45),
                    marker=dict(size=7, color=pulso_ponto, line=dict(color=fundo_tema, width=1.5)),
                    fill="tozeroy",
                    fillcolor="rgba(0,229,255,0.09)" if not modo_claro else "rgba(0,43,91,0.07)",
                    hovertemplate="<b>%{x|%d/%m/%Y}</b><br>R$ %{y:,.2f}<extra></extra>"
                ))
                fig_pulso.update_layout(
                    height=320, margin=dict(l=8,r=12,t=16,b=8),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False, hovermode="x unified",
                    font=dict(color=texto_sutil, size=11)
                )
                fig_pulso.update_xaxes(title=None, showgrid=False, zeroline=False,
                                       tickformat="%d/%m", tickfont=dict(size=10), fixedrange=True)
                fig_pulso.update_yaxes(title=None, showgrid=True, zeroline=False,
                                       gridcolor="rgba(148,163,184,.10)", tickprefix="R$ ",
                                       tickfont=dict(size=10), fixedrange=True, rangemode="tozero")
                st.plotly_chart(fig_pulso, use_container_width=True, config={"displayModeBar":False, "responsive":True})

            with col_g2:
                st.markdown('<div class="elevo-v13-panel-title"><span class="elevo-v13-led"></span> ◉ Radar de Produtos</div>', unsafe_allow_html=True)
                st.caption("Fatias dos campeões de venda — painel circular exclusivo ÉLÉVO.")
                recorte = df_campeao.head(5).copy()
                nomes_completos = recorte["Produto"].astype(str).tolist()
                montantes = recorte["Comissao_R$"].astype(float).tolist()
                outros = float(df_campeao.iloc[5:]["Comissao_R$"].sum())
                if outros > 0:
                    nomes_completos.append("Outros produtos")
                    montantes.append(outros)
                total_painel = sum(montantes)
                if total_painel > 0:
                    rotulos = [n if len(n) <= 22 else n[:19] + "..." for n in nomes_completos]
                    paleta_elevo = ["#00E5FF", "#00FF9D", "#D4AF37", "#4D95FF", "#00BFA5", "#68778A"]
                    fig_radial = go.Figure(go.Pie(
                        labels=rotulos, values=montantes, customdata=nomes_completos,
                        hole=.69, sort=False, direction="clockwise", rotation=270,
                        marker=dict(colors=paleta_elevo[:len(montantes)], line=dict(color=fundo_tema, width=2.5)),
                        textinfo="none", showlegend=True,
                        hovertemplate="<b>%{customdata}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>"
                    ))
                    centro_formatado = f"R$ {total_painel:,.0f}".replace(",", ".")
                    fig_radial.update_layout(
                        height=350, margin=dict(l=5,r=5,t=3,b=60),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color=texto_sutil, size=11),
                        legend=dict(orientation="h",y=-.04,x=.5,xanchor="center",yanchor="top",
                                    font=dict(size=10),itemsizing="constant",traceorder="normal"),
                        annotations=[
                            dict(text="ÉLÉVO",x=.5,y=.56,showarrow=False,
                                 font=dict(size=17,color=pulso_tom,family="Montserrat, sans-serif")),
                            dict(text=centro_formatado,x=.5,y=.45,showarrow=False,
                                 font=dict(size=14,color=pulso_ponto,family="Montserrat, sans-serif"))
                        ]
                    )
                    st.plotly_chart(fig_radial, use_container_width=True, config={"displayModeBar":False,"responsive":True})
                else:
                    st.info("O gráfico circular será exibido quando houver vendas com valores positivos.")

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
            <p style="color: {txt_sub} !important; font-family: 'Montserrat', sans-serif; font-size: 0.78rem; margin-bottom: 0; font-weight: 500;">Comparativo de comissões (7 dias vs. semana anterior)</p>
        </div>
        <style>
            @keyframes pulse-cor {{ 
                0% {{ box-shadow: 0 4px 15px {sombra_anim}; transform: scale(1); }} 
                50% {{ box-shadow: 0 8px 28px {sombra_anim}; transform: scale(1.015); }} 
                100% {{ box-shadow: 0 4px 15px {sombra_anim}; transform: scale(1); }} 
            }}
        </style>
        """, unsafe_allow_html=True)

st.markdown('<div id="missoes"></div>', unsafe_allow_html=True)

# ==========================================================
# 10. MOTOR DE ELITE (DISCIPLINA + OPORTUNIDADES EMPRESARIAIS OCULTAS 24H)
# ==========================================================
# Missões por usuário (não-CEO) preservadas no Sheets por Gmail.
# Isoladas do histórico da conta master e dos dados de vendas.
def aba_missoes_usuario():
    if not robo_sheets:
        raise RuntimeError("Banco indisponível")
    planilha = robo_sheets.open_by_key(re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE).group(1))
    try:
        return planilha.worksheet("Historico_Missoes_Usuarios")
    except gspread.exceptions.WorksheetNotFound:
        aba = planilha.add_worksheet(title="Historico_Missoes_Usuarios", rows="1000", cols="3")
        aba.append_row(["Email", "Data", "Status"])
        return aba


def listar_missoes_usuario(email):
    registros = aba_missoes_usuario().get_all_records()
    return [r for r in registros if str(r.get("Email", "")).strip().lower() == email.strip().lower()]


def salvar_missao_usuario(email, data):
    aba = aba_missoes_usuario()
    registros = aba.get_all_records()
    if any(str(r.get("Email", "")).strip().lower() == email.strip().lower()
           and str(r.get("Data", "")) == data for r in registros):
        return True
    aba.append_row([email.strip().lower(), data, "Concluída"])
    return True

st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🧠 Motor de Elite: Disciplina & Expansão</h3>", unsafe_allow_html=True)

agora_brasil = datetime.now(ZoneInfo("America/Sao_Paulo"))
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
        validar_cota_ia()
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
        st.markdown(str(op_hoje.get('pitch', '')))
        with st.expander("🛠️ Ver Plano Executivo de Implementação (5 Passos)", expanded=False):
            st.markdown(f"**Mapa de Execução Estratégica:**\n\n{op_hoje.get('passos', '')}")

if f"missao_{agora_brasil.strftime('%Y-%m-%d')}" not in st.session_state:
    missao_previamente_concluida = False
    if not E_O_CEO:
        try:
            hoje_str = agora_brasil.strftime("%d/%m/%Y")
            missao_previamente_concluida = any(str(r.get("Data", "")) == hoje_str
                for r in listar_missoes_usuario(st.session_state["email_usuario"]))
        except Exception:
            st.warning("Histórico de missões indisponível. A conclusão poderá não ser registrada.")
    st.session_state[f"missao_{agora_brasil.strftime('%Y-%m-%d')}"] = missao_previamente_concluida

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
                except Exception:
                    st.warning("A missão foi concluída, mas não foi possível registrar o histórico do CEO.")
            elif not E_O_CEO:
                try:
                    salvar_missao_usuario(st.session_state["email_usuario"], agora_brasil.strftime("%d/%m/%Y"))
                except Exception:
                    st.session_state[f"missao_{agora_brasil.strftime('%Y-%m-%d')}"] = False
                    st.error("Falha ao salvar a missão no banco. Tente novamente.")
                    st.stop()
            st.rerun()
    else:
        st.success("Missão de Hoje Cumprida! 🦅")

if robo_sheets and (not E_O_CEO or link_planilha_ativa):
    st.markdown("#### 📊 Seu Termômetro de Execução (Janela Móvel: 30 Dias)")
    try:
        if E_O_CEO:
            sheet_id = extrair_id_planilha(link_planilha_ativa)
            planilha = robo_sheets.open_by_key(sheet_id)
            try:
                aba_historico = planilha.worksheet("Historico_Missoes")
                df_hist = pd.DataFrame(aba_historico.get_all_records())
            except gspread.exceptions.WorksheetNotFound:
                df_hist = pd.DataFrame(columns=["Data", "Status"])
        else:
            df_hist = pd.DataFrame(listar_missoes_usuario(st.session_state["email_usuario"]))
    except Exception:
        df_hist = pd.DataFrame(columns=["Data", "Status"])
        
    # Em uma conta sem missões salvas, exibir a trilha vazia em vez de ocultar
    # o gráfico. Somente a apresentação do histórico muda.
    if "Data" not in df_hist.columns:
        df_hist = pd.DataFrame(columns=["Data", "Status"])
    if "Data" in df_hist.columns:
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
        
        # A matriz abaixo usa a mesma informação dos últimos 30 dias.
        # Não altera o registro das missões nem os outros gráficos.
        
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
            
        # MATRIZ ÉLÉVO | 30 DIAS — leitura semanal, limpa e responsiva.
        # Cada quadrado é um dia: verde = cumprido, neutro = pendente.
        st.markdown('<div class="elevo-v13-panel-title"><span class="elevo-v13-led"></span> 🗓️ Trilha de Missões — 30 Dias</div>', unsafe_allow_html=True)
        df_matriz = df_grafico_missoes.copy()
        dia_inicio_semana = df_matriz["Data_Parsed"].iloc[0] - pd.Timedelta(days=int(df_matriz["Data_Parsed"].iloc[0].weekday()))
        df_matriz["Dia_Semana"] = df_matriz["Data_Parsed"].dt.weekday
        df_matriz["Semana"] = ((df_matriz["Data_Parsed"] - dia_inicio_semana).dt.days // 7).astype(int)
        df_matriz["Situacao"] = df_matriz["Status_Num"].map({1: "Missão concluída", 0: "Missão pendente"})
        df_matriz["Data_Exibicao"] = df_matriz["Data_Parsed"].dt.strftime("%d/%m/%Y")
        semanas_total = int(df_matriz["Semana"].max()) + 1

        fundo_celula = "#DCE5EE" if modo_claro else "#223042"
        borda_celula = "#C3D1DF" if modo_claro else "#33465C"
        texto_pendente = "#52667A" if modo_claro else "#A8BBCE"
        texto_dashboard = "#475569" if modo_claro else "#94A3B8"
        grafico_trilha = go.Figure()
        for concluida, cor, cor_texto, cor_borda in [
            (False, fundo_celula, texto_pendente, borda_celula),
            (True, "#00DCA0", "#062D23", "#37FFD0"),
        ]:
            dados_dia = df_matriz[df_matriz["Status_Num"].eq(int(concluida))]
            if not dados_dia.empty:
                grafico_trilha.add_trace(go.Scatter(
                    x=dados_dia["Dia_Semana"], y=dados_dia["Semana"],
                    mode="markers+text", name="Concluída" if concluida else "Pendente",
                    marker=dict(symbol="square", size=38, color=cor,
                                line=dict(color=cor_borda, width=1.6)),
                    text=dados_dia["Data_Parsed"].dt.strftime("%d"),
                    textposition="middle center", textfont=dict(size=12, color=cor_texto, family="Montserrat, sans-serif"),
                    customdata=dados_dia[["Data_Exibicao", "Situacao"]].to_numpy(),
                    hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
                    showlegend=False
                ))

        # Realça somente o dia atual sem apagar o estado da missão.
        grafico_trilha.add_trace(go.Scatter(
            x=[int(hoje_data.weekday())],
            y=[int((hoje_data - dia_inicio_semana).days // 7)],
            mode="markers", marker=dict(symbol="square-open", size=44, color="#D4AF37",
                                        line=dict(color="#D4AF37", width=3)),
            hoverinfo="skip", showlegend=False
        ))
        grafico_trilha.update_layout(
            height=130 + semanas_total * 47,
            margin=dict(l=8, r=10, t=42, b=12),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, dragmode=False,
            font=dict(color=texto_dashboard, family="Montserrat, sans-serif", size=11),
            hoverlabel=dict(bgcolor="#102131" if not modo_claro else "#FFFFFF",
                            font=dict(color="#F1F5F9" if not modo_claro else "#172437", size=12))
        )
        grafico_trilha.update_xaxes(
            side="top", tickmode="array", tickvals=list(range(7)),
            ticktext=["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"],
            range=[-0.58, 6.58], showgrid=False, zeroline=False,
            showline=False, ticks="", fixedrange=True, tickfont=dict(size=10)
        )
        grafico_trilha.update_yaxes(
            tickmode="array", tickvals=list(range(semanas_total)),
            ticktext=[f"S{i+1}" for i in range(semanas_total)],
            range=[semanas_total - 0.4, -0.6], showgrid=False,
            zeroline=False, showline=False, ticks="", fixedrange=True,
            tickfont=dict(size=10)
        )
        st.plotly_chart(grafico_trilha, use_container_width=True,
                        config={"displayModeBar": False, "responsive": True, "staticPlot": False})
        st.caption("🟢 Concluída   ·   ◼ Pendente   ·   🟨 Contorno dourado: hoje")
    else:
        st.info("Nenhum histórico de missões ainda.")

st.markdown('<div id="radar"></div>', unsafe_allow_html=True)

# ==========================================================
# 11 e 12. RADAR E ENGENHARIA DE FUNIL (RAIO-X CEO)
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
                        
                        texto_instrucao = f"Contexto do usuário: {texto_contexto}\n\n"
                        texto_instrucao += "Analise apenas informações realmente presentes nas imagens e no contexto fornecido. Não invente CTR ou conversões.\n\n"
                        texto_instrucao += "Sua missão: Descubra o padrão de sucesso analisando os dados, a conversão, o feedback e as imagens. Monte um MAPA MENTAL ESTRATÉGICO e um FUNIL DE VENDAS REPETÍVEL.\n1. O Padrão de Ouro\n2. O Funil Escalável (Ataque as objeções listadas)\n3. 3 Ganchos Prontos\n4. Estratégia de Dominação\nSeja frio, analítico e direto."
                        
                        conteudo_prompt = [{"type": "text", "text": texto_instrucao}]
                        
                        if imgs_analytics:
                            for img in imgs_analytics:
                                img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
                                conteudo_prompt.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                                })
                        
                        validar_cota_ia()
                        
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
            if user_inf:
                return user_inf[-1]
            return None
            
        elif acao == "salvar":
            col_emails = aba_inf.col_values(1)
            agora_str = (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")
            # Update without deleting the previous profile before the write completes.
            indices = [i for i in range(2, len(col_emails) + 1)
                       if str(col_emails[i - 1]).strip().lower() == email_clean]
            if indices:
                aba_inf.update(f"B{indices[-1]}:E{indices[-1]}",
                               [[nome_inf.strip(), desc_inf.strip(), agora_str, logo_marca.strip()]])
            else:
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


# ==========================================================
# ÉLÉVO V16.4 — ELENCO DIGITAL (substitui SOMENTE Laboratório + 9s)
# Retratos originais embarcados no app.py; não necessita upload de imagens.
# ==========================================================
st.divider()
st.markdown('<div id="elenco-elevo"></div>', unsafe_allow_html=True)
st.markdown("### ✨ Elenco de Influenciadoras Virtuais")
st.caption("Cinco influenciadoras fictícias adultas com identidade, aparência, personalidade, voz e emoção já definidas. Basta selecionar: a ficha completa será aplicada automaticamente aos Blocos 17 e 17.2.")

INFLUENCIADORAS_ELEVO_V164 = {
    'ana': {
        "nome": 'Ana Clara', "idade": 22, "nicho": 'Beleza & skincare', "tags": 'Beleza · Autocuidado',
        "resumo": 'Jovem, carismática e espontânea. Conecta com o público em resenhas leves e autênticas.', "aparencia": 'Brazilian adult woman, 22 years old, warm medium complexion, deep brown almond eyes, long dark brown wavy hair with a side part, softly rounded face, natural delicate makeup, hoop earrings, casual earth-toned blouse; preserve the reference portrait identity, hair part and face proportions in every scene.', "voz": 'Voz jovem, calorosa, risonha e próxima, em português brasileiro.',
        "emocao": 'Alegria acolhedora, curiosidade genuína e surpresa comedida.', "gestos": 'Expressões naturais, sorriso fácil, contato visual amigável, gestos leves com as mãos.', "tom": 'Conselho de amiga em resenha sincera, sem exageros e sem promessas não comprovadas.',
        "foto": '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',
    },
    'bruna': {
        "nome": 'Bruna Lima', "idade": 28, "nicho": 'Casa & organização', "tags": 'Casa · Utilidades',
        "resumo": 'Prática e segura. Explica utilidades de forma clara, com foco no antes e depois realista.', "aparencia": 'Brazilian adult woman, 28 years old, light warm skin, medium-long honey-blonde wavy hair with darker roots, brown eyes, softly defined facial contours, natural makeup, black short-sleeve casual shirt; preserve the same distinct portrait identity and hairstyle.', "voz": 'Voz firme, clara e confortável, com entonação didática.',
        "emocao": 'Confiança tranquila, satisfação discreta e humor observacional.', "gestos": 'Gestos organizados demonstrando tamanho, uso e manuseio, sem movimentos apressados.', "tom": 'Demonstração objetiva de usos cotidianos, com linguagem simples e sem resultados inventados.',
        "foto": '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',
    },
    'camila': {
        "nome": 'Camila Rocha', "idade": 26, "nicho": 'Fitness & bem-estar', "tags": 'Fitness · Rotina',
        "resumo": 'Energética e motivadora sem ser exagerada. Mostra uma rotina ativa e acessível.', "aparencia": 'Brazilian adult woman, 26 years old, golden tan skin, expressive dark eyes, dark brown hair in a high messy bun with a few loose strands framing the face, athletic-casual charcoal top; preserve exact hair bun, facial appearance and athletic wardrobe cues from the reference portrait.', "voz": 'Voz dinâmica, clara e natural, com pausas e boa articulação.',
        "emocao": 'Energia positiva, disciplina serena e empatia.', "gestos": 'Postura ativa, movimentos naturais de demonstração e respiração realista.', "tom": 'Bem-estar cotidiano, uso responsável de produtos, sem alegações médicas ou mudanças instantâneas.',
        "foto": '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',
    },
    'juliana': {
        "nome": 'Juliana Mendes', "idade": 30, "nicho": 'Moda & lifestyle', "tags": 'Moda · Tendências',
        "resumo": 'Sofisticada e acessível. Tem olhar de curadoria e sugere combinações de forma elegante.', "aparencia": 'Brazilian adult woman, 30 years old, fair skin with natural freckles, long voluminous copper-red wavy hair parted to the side, hazel eyes, softly angular face, white casual top, minimal jewelry; preserve copper hairstyle and face identity from the portrait.', "voz": 'Voz calma, expressiva, segura, com ritmo refinado e conversacional.',
        "emocao": 'Encantamento sutil, elegância e curiosidade estética.', "gestos": 'Gestos delicados, mãos em posição natural e contato visual confiante.', "tom": 'Moda prática, estilo pessoal e descobertas autênticas, sem pressão de compra falsa.',
        "foto": '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',
    },
    'mariana': {
        "nome": 'Mariana Costa', "idade": 32, "nicho": 'Cozinha & utilidades', "tags": 'Cozinha · Receitas',
        "resumo": 'Simpática e objetiva. Aproxima o público com testes reais de utensílios e dicas de cozinha.', "aparencia": 'Brazilian adult woman, 32 years old, medium olive skin, long straight black hair with subtle waves at the ends, dark brown eyes, oval face, bright natural smile, neutral dark casual blouse; preserve her reference portrait face and hairstyle.', "voz": 'Voz acolhedora, comunicativa e descontraída, com boa dicção.',
        "emocao": 'Simpatia, satisfação real e humor leve.', "gestos": 'Aponta e demonstra utensílios com movimentos precisos e naturais, sem poses artificiais.', "tom": 'Experiência prática de cozinha e utilidades, demonstrando o que for fisicamente possível.',
        "foto": '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',
    }
}


def montar_descricao_influencer_v164(perfil):
    """Perfil pronto e imutável; todos os dados seguem para imagem, vídeo e fala."""
    texto = (
        f"[DIGITAL INFLUENCER PERSONA — FICTIONAL ADULT, CONSISTENT IDENTITY] "
        f"NAME: {perfil['nome']}; AGE: {perfil['idade']} years; NICHE: {perfil['nicho']}. "
        f"LOCKED PHYSICAL APPEARANCE AND PHOTO REFERENCE: {perfil['aparencia']} "
        f"PERSONALITY AND COMMERCIAL APPROACH (Portuguese BR): {perfil['resumo']} {perfil['tom']} "
        f"VOICE AND PROSODY: {perfil['voz']} "
        f"EMOTIONAL DIRECTION: {perfil['emocao']} "
        f"BODY LANGUAGE / ACTIONS: {perfil['gestos']} "
        "Keep the same person's face, age, hair color, hairstyle and natural skin texture across "
        "the image prompt, every video frame, voice and storyboard. Do not impose straight bangs "
        "or another influencer's facial features. Make emotions product-contextual, human and plausible. "
        "Never assert the fictional influencer is a real customer or fabricated testimonial."
    )
    return texto


def obter_observacao_salva_v164(descricao):
    marcador = "[AJUSTE OPCIONAL DO USUÁRIO]: "
    return str(descricao).split(marcador, 1)[1].strip() if marcador in str(descricao) else ""


# Abre uma única vez o histórico do Gmail, sem misturar personagens entre contas.
email_elenco_v164 = str(st.session_state.get("email_usuario", "")).strip().lower()
if st.session_state.get("email_inf_carregado") != email_elenco_v164:
    st.session_state["influencer_atual"] = gerenciar_influencer_usuario("ler", email_elenco_v164)
    st.session_state["email_inf_carregado"] = email_elenco_v164
    st.session_state.pop("elevo_inf_preset_id", None)
    st.session_state.pop("elevo_inf_obs", None)

# Ao instalar a correção, elimina o default temporário "Ana Clara" que
# a V16.4 pode ter deixado na SESSÃO do CEO. Apenas LÊ a conta do Sheets;
# nenhum dado salvo é apagado ou modificado.
if E_O_CEO and st.session_state.get("elevo_ceo_identity_v1641_loaded") != email_elenco_v164:
    st.session_state["influencer_atual"] = gerenciar_influencer_usuario("ler", email_elenco_v164)
    st.session_state["elevo_inf_preset_id"] = ""
    st.session_state["elevo_inf_obs"] = ""
    st.session_state["elevo_ceo_identity_v1641_loaded"] = email_elenco_v164

if "elevo_inf_preset_id" not in st.session_state:
    inf_anterior = st.session_state.get("influencer_atual") or {}
    st.session_state["elevo_inf_preset_id"] = ""
    st.session_state["elevo_inf_obs"] = obter_observacao_salva_v164(inf_anterior.get("Descricao_Visual", ""))

# Referências visuais exclusivas do CEO (arquivos do usuário, compactados e incorporados).
FOTO_CEO_REFERENCIA_1 = "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"
FOTO_CEO_REFERENCIA_2 = "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"


# Painel-resumo no topo: mostra a ficha da influência ativa ou uma orientação clara quando nada foi escolhido.
perfil_preview_topo = None
chave_preview_topo = str(st.session_state.get("elevo_inf_preset_id", "")).strip()
dados_preview_topo = st.session_state.get("influencer_atual") or {}

if chave_preview_topo == "ceo_original" and E_O_CEO:
    perfil_preview_topo = {
        "titulo": str(dados_preview_topo.get("Nome_Influencer") or "Aurora"),
        "subtitulo": "Influência principal do CEO",
        "personalidade": "Presença magnética, olhar intenso, energia de autoridade e conexão premium.",
        "emocao": "Confiança, sofisticação e proximidade estratégica.",
        "voz": "Tom firme, elegante e natural em português brasileiro.",
        "referencia": "Usa a identidade original do CEO e respeita a descrição já aplicada nos Blocos 17 e 17.2.",
        "observacao": "Se quiser, você ainda pode escolher uma das outras influenciadoras ou criar a sua própria na aba Minha Influenciadora."
    }
elif chave_preview_topo in INFLUENCIADORAS_ELEVO_V164:
    pf = INFLUENCIADORAS_ELEVO_V164[chave_preview_topo]
    perfil_preview_topo = {
        "titulo": pf["nome"],
        "subtitulo": f"{pf['idade']} anos · {pf['nicho']}",
        "personalidade": pf["resumo"],
        "emocao": pf["emocao"],
        "voz": pf["voz"],
        "referencia": pf["aparencia"],
        "observacao": "Ficha completa pronta para uso. Sem campos adicionais ou necessidade de personalização."
    }
elif dados_preview_topo.get("Nome_Influencer"):
    perfil_preview_topo = {
        "titulo": str(dados_preview_topo.get("Nome_Influencer")),
        "subtitulo": "Influência personalizada salva no login",
        "personalidade": "Perfil autoral definido pelo usuário.",
        "emocao": "Será lida diretamente da descrição salva.",
        "voz": "Mantém a identidade cadastrada para imagem, vídeo e fala.",
        "referencia": str(dados_preview_topo.get("Descricao_Visual", ""))[:420],
        "observacao": "Os cartões prontos continuam disponíveis; selecionar um deles troca apenas a influência ativa."
    }

col_head_elenco, col_box_elenco = st.columns([2.3, 1], gap="medium")
with col_head_elenco:
    st.markdown("#### 🎛️ Como funciona a escolha")
    st.caption("Você pode selecionar uma influenciadora pronta, usar a influência do CEO ou criar a sua própria. O que estiver ativo segue automaticamente para os prompts do Bloco 17 e do Bloco 17.2.")
with col_box_elenco:
    with st.container(border=True):
        if perfil_preview_topo:
            st.markdown(f"**🧾 Ficha ativa: {perfil_preview_topo['titulo']}**")
            st.caption(perfil_preview_topo["subtitulo"])
            st.markdown(f"**Personalidade:** {perfil_preview_topo['personalidade']}")
            st.markdown(f"**Voz:** {perfil_preview_topo['voz']}")
            st.markdown(f"**Emoção:** {perfil_preview_topo['emocao']}")
            st.caption("Identidade completa protegida e aplicada automaticamente aos Blocos 17 e 17.2.")
        else:
            st.markdown("**🧾 Ficha da influência**")
            st.caption("Nenhuma influência foi marcada ainda.")
            st.markdown("**Personalidade:** livre escolha")
            st.markdown("**Voz:** definida conforme a selecionada")
            st.markdown("**Emoção:** definida conforme a selecionada")
            st.caption("Escolha um card da galeria ou crie a sua própria influência na aba Minha Influenciadora.")


# ==========================================================
# ÉLÉVO V16.8 — GALERIAS HORIZONTAIS RESPONSIVAS (NATIVAS STREAMLIT)
# Mantém seletores Streamlit: nada de botões HTML simulados.
# ==========================================================
st.markdown("""
<style>
/* Scroll nativo de toque/trackpad e cartões com efeito de entrada discreto. */
.st-key-elevo_carrossel_influenciadoras [data-testid="stHorizontalBlock"],
.st-key-elevo_carrossel_ambientes [data-testid="stHorizontalBlock"],
.st-key-elevo_carrossel_influenciadoras[data-testid="stHorizontalBlock"],
.st-key-elevo_carrossel_ambientes[data-testid="stHorizontalBlock"] {
    display:flex !important;
    flex-wrap:nowrap !important;
    overflow-x:auto !important;
    overflow-y:hidden !important;
    overscroll-behavior-inline:contain;
    -webkit-overflow-scrolling:touch;
    scroll-behavior:smooth;
    scroll-snap-type:x proximity;
    scrollbar-width:thin;
    scrollbar-color:#3b80c5 transparent;
    padding:5px 4px 14px !important;
}
.st-key-elevo_carrossel_influenciadoras [data-testid="stHorizontalBlock"]::-webkit-scrollbar,
.st-key-elevo_carrossel_ambientes [data-testid="stHorizontalBlock"]::-webkit-scrollbar {height:7px}
.st-key-elevo_carrossel_influenciadoras [data-testid="stHorizontalBlock"]::-webkit-scrollbar-thumb,
.st-key-elevo_carrossel_ambientes [data-testid="stHorizontalBlock"]::-webkit-scrollbar-thumb {
    background:#3b80c5;border-radius:20px;
}
/* Resgata linha única no mobile, mesmo diante das regras globais antigas. */
.st-key-elevo_carrossel_influenciadoras [data-testid="stHorizontalBlock"] > *,
.st-key-elevo_carrossel_ambientes [data-testid="stHorizontalBlock"] > * {
    flex:0 0 auto !important;
    scroll-snap-align:start;
    min-width:0;
}
.elevo-carrossel-instrucao {
    display:flex;align-items:center;justify-content:space-between;gap:12px;
    padding:7px 11px;margin:8px 0 10px;border-radius:12px;
    background:linear-gradient(110deg,rgba(37,105,198,.12),rgba(34,180,220,.04));
    border:1px solid rgba(72,151,234,.18);
    color:#acd8ff;font-size:.73rem;font-weight:700;letter-spacing:.012em;
}
.elevo-carrossel-instrucao .pista {opacity:.75;font-weight:500;white-space:nowrap}
.elevo-elenco-card,.elevo-ambiente-card {
    animation:elevo-card-chegada .36s ease-out both;
    transition:transform .22s ease,border-color .22s ease,box-shadow .22s ease;
}
.elevo-elenco-card:hover,.elevo-ambiente-card:hover {
    transform:translateY(-3px);border-color:rgba(78,175,245,.6);
}
@keyframes elevo-card-chegada {
    from {opacity:.3;transform:translateY(8px)}
    to {opacity:1;transform:translateY(0)}
}
@media(max-width:767px) {
    .st-key-elevo_carrossel_influenciadoras [data-testid="stHorizontalBlock"],
    .st-key-elevo_carrossel_ambientes [data-testid="stHorizontalBlock"] {
        flex-wrap:nowrap !important;
        overflow-x:auto !important;
        align-items:stretch !important;
    }
    .elevo-carrossel-instrucao {font-size:.69rem}
}
@media(prefers-reduced-motion:reduce) {
    .elevo-elenco-card,.elevo-ambiente-card {animation:none;transition:none}
    .st-key-elevo_carrossel_influenciadoras [data-testid="stHorizontalBlock"],
    .st-key-elevo_carrossel_ambientes [data-testid="stHorizontalBlock"] {scroll-behavior:auto}
}
</style>
""", unsafe_allow_html=True)

# Galeria unificada: o CEO também vê as outras influenciadoras.
st.markdown("""
<style>
.elevo-elenco-foto { width:100%; height:150px; object-fit:cover; object-position:center 20%; border-radius:11px; display:block; }
.elevo-elenco-card { padding:9px; border-radius:15px; border:1px solid rgba(91,148,218,.27);
  background:linear-gradient(145deg,#102139,#0c1629); height:322px; margin-bottom:9px; overflow:hidden; }
.elevo-elenco-card.ativo { border-color:#00DFFF; box-shadow:0 0 0 1px rgba(0,223,255,.26),0 0 16px rgba(0,223,255,.13); }
.elevo-elenco-nome {color:#EBF4FF;font-weight:850;font-size:.85rem;margin:9px 0 3px;}
.elevo-elenco-idade {color:#A5B8D6;font-size:.72rem;}
.elevo-elenco-nicho {color:#62D6F4;font-size:.70rem;font-weight:650;margin:8px 0;min-height:30px;}
.elevo-elenco-desc {color:#B6C4D9;font-size:.71rem;line-height:1.45;display:-webkit-box;
    -webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}
.elevo-elenco-status {font-size:.68rem;color:#75F2CF;font-weight:700;margin:0 0 5px;}
@media (max-width:900px) {.elevo-elenco-card {height:322px}}
</style>
""", unsafe_allow_html=True)

# Cartão especial do CEO (mostrado para o próprio CEO) + cinco perfis prontos.
NOME_CEO_PADRAO = "Aurora"
DESCRICAO_CEO_PADRAO = "Photorealistic young Brazilian woman (Aurora: dark hair, subtle bangs, intense conspiratorial expression, incredibly shiny and healthy-looking hair)"

dados_ceo_salvos = st.session_state.get("influencer_atual") or {}
# A escolha de outra influenciadora não pode sobrescrever o cartão ORIGINAL do CEO.
if E_O_CEO and "elevo_ceo_original_v1682" not in st.session_state:
    _original_sessao = st.session_state.get("influencer_atual") or {}
    _nome_original = str(_original_sessao.get("Nome_Influencer", "")).strip()
    _descricao_original = str(_original_sessao.get("Descricao_Visual", "")).strip()
    if _nome_original.lower() == NOME_CEO_PADRAO.lower() and _descricao_original:
        st.session_state["elevo_ceo_original_v1682"] = (_nome_original, _descricao_original)
    else:
        st.session_state["elevo_ceo_original_v1682"] = (NOME_CEO_PADRAO, DESCRICAO_CEO_PADRAO)
nome_ceo_galeria, descricao_ceo_galeria = (
    st.session_state.get("elevo_ceo_original_v1682", (NOME_CEO_PADRAO, DESCRICAO_CEO_PADRAO))
    if E_O_CEO else (NOME_CEO_PADRAO, DESCRICAO_CEO_PADRAO)
)

if E_O_CEO:
    st.info("Nenhuma influenciadora vem marcada automaticamente. Você pode escolher a sua identidade do CEO, testar uma das outras ou criar a sua própria na aba 'Minha Influenciadora'.")
else:
    st.info("Nenhuma influenciadora vem marcada automaticamente. Você pode escolher um perfil pronto ou criar a sua própria na aba 'Minha Influenciadora'.")

perfil_sessao_atual = st.session_state.get("influencer_atual") or {}
if perfil_sessao_atual.get("Nome_Influencer"):
    st.caption(f"🎯 Influenciadora ativa no momento: {perfil_sessao_atual.get('Nome_Influencer')}")
elif E_O_CEO:
    st.caption("🎯 Influenciadora ativa no momento: Aurora (perfil original do CEO)")
else:
    st.caption("🎯 Nenhum cartão foi escolhido ainda. Se não salvar um perfil, o sistema usa uma persona neutra apenas como fallback técnico.")

cards_galeria_v164 = []
if E_O_CEO:
    cards_galeria_v164.append({
        "id": "ceo_original",
        "nome": nome_ceo_galeria,
        "idade": "CEO",
        "nicho": "Influência original do CEO",
        "resumo": "Sua personagem principal. Mantém a identidade já usada nos Blocos 17 e 17.2, sem precisar digitar tudo de novo.",
        "foto": FOTO_CEO_REFERENCIA_1,
        "tipo": "ceo"
    })
for chave_perfil, perfil in INFLUENCIADORAS_ELEVO_V164.items():
    cards_galeria_v164.append({
        "id": chave_perfil,
        "nome": perfil["nome"],
        "idade": perfil["idade"],
        "nicho": perfil["nicho"],
        "resumo": perfil["resumo"],
        "foto": perfil["foto"],
        "tipo": "preset"
    })

def aplicar_cartao_influencia_v164(card_id):
    marca = str((st.session_state.get("influencer_atual") or {}).get("Logo_Marca", "")).strip()
    if card_id == "ceo_original":
        nome_aplicado = nome_ceo_galeria
        descricao_aplicada = descricao_ceo_galeria
    else:
        perfil = INFLUENCIADORAS_ELEVO_V164[card_id]
        nome_aplicado = perfil["nome"]
        descricao_aplicada = montar_descricao_influencer_v164(perfil)
    st.session_state["elevo_inf_preset_id"] = card_id
    st.session_state["influencer_atual"] = {
        "Email": email_elenco_v164,
        "Nome_Influencer": nome_aplicado,
        "Descricao_Visual": descricao_aplicada,
        "Logo_Marca": marca,
    }
    ok = gerenciar_influencer_usuario("salvar", email_elenco_v164, nome_aplicado, descricao_aplicada, marca)
    if not ok:
        st.session_state["elevo_inf_erro_gravacao"] = True
    else:
        st.session_state.pop("elevo_inf_erro_gravacao", None)

st.markdown(
    '<div class="elevo-carrossel-instrucao">'
    '<span>👆 Deslize para explorar as influenciadoras</span>'
    f'<span class="pista">{len(cards_galeria_v164)} perfis · ⇆</span>'
    '</div>', unsafe_allow_html=True
)
with st.container(horizontal=True, wrap=False, gap="small", key="elevo_carrossel_influenciadoras"):
    for card in cards_galeria_v164:
        with st.container(width=226):
            ativo = st.session_state.get("elevo_inf_preset_id", "") == card["id"]
            classe_ativo = " ativo" if ativo else ""
            selo_ativo = '<div class="elevo-elenco-status">● SELECIONADA</div>' if ativo else ''
            idade_txt = f"{card['idade']}" + (" anos" if str(card['idade']).isdigit() else "")
            st.markdown(
                f'<div class="elevo-elenco-card{classe_ativo}">'
                f'<img class="elevo-elenco-foto" src="data:image/webp;base64,{card["foto"]}" alt="Retrato de {card["nome"]}" />'
                f'<div class="elevo-elenco-nome">{card["nome"]}</div>'
                f'<div class="elevo-elenco-idade">{idade_txt}</div>'
                f'<div class="elevo-elenco-nicho">{card["nicho"]}</div>'
                f'<div class="elevo-elenco-desc">{card["resumo"]}</div>'
                f'{selo_ativo}</div>',
                unsafe_allow_html=True
            )
            if st.button("✓ Escolhida" if ativo else "Selecionar", key=f"elenco_preset_{card['id']}",
                         type="primary" if ativo else "secondary", use_container_width=True, disabled=ativo):
                aplicar_cartao_influencia_v164(card["id"])
                st.rerun()

col_acao1, col_acao2 = st.columns([1, 1])
with col_acao1:
    if st.button("🧹 Limpar seleção visual", key="elenco_limpar_visual", use_container_width=True):
        st.session_state["elevo_inf_preset_id"] = ""
        st.rerun()
with col_acao2:
    if st.button("👤 Usar influência própria", key="elenco_usar_propria", use_container_width=True):
        st.session_state["elevo_inf_preset_id"] = ""
        st.info("Agora é só abrir a aba 'Minha Influenciadora' e salvar a sua própria influência.")

chave_ativa = st.session_state.get("elevo_inf_preset_id", "")
if chave_ativa:
    if chave_ativa == "ceo_original":
        col_detalhe, col_personal = st.columns([1.05, 1])
        with col_detalhe:
            with st.container(border=True):
                st.markdown(f"#### {html_std.escape(nome_ceo_galeria)} · perfil do CEO")
                st.caption("Identidade original preservada para os Blocos 17 e 17.2")
                st.markdown("**Perfil:** Sua influência principal do CEO, mantida como referência oficial.")
                with st.expander("Ver referências visuais do CEO"):
                    ref1, ref2 = st.columns(2)
                    with ref1:
                        st.image(base64.b64decode(FOTO_CEO_REFERENCIA_1), caption="Referência 01", use_container_width=True)
                    with ref2:
                        st.image(base64.b64decode(FOTO_CEO_REFERENCIA_2), caption="Referência 02", use_container_width=True)
        with col_personal:
            with st.container(border=True):
                st.markdown("#### 🔒 Identidade do CEO")
                st.caption("Descrição técnica guardada na memória da personagem.")
                st.success("Pronta para os Blocos 17 e 17.2. Não é necessário copiar ou editar a ficha.")
        st.caption("✅ A influência do CEO está ativa automaticamente nos prompts de imagem, vídeo e fala dos Blocos 17 e 17.2.")
    elif chave_ativa in INFLUENCIADORAS_ELEVO_V164:
        perfil_ativo = INFLUENCIADORAS_ELEVO_V164[chave_ativa]
        # Ficha única, pronta e somente para consulta. Sem campo de edição.
        with st.container(border=True):
            st.markdown(f"#### {perfil_ativo['nome']} · {perfil_ativo['idade']} anos")
            st.caption(f"Nicho: {perfil_ativo['nicho']} · {perfil_ativo['tags']}")
            st.markdown(f"**Personalidade:** {perfil_ativo['resumo']}")
            st.markdown(f"**Tom de apresentação:** {perfil_ativo['tom']}")
            st.markdown(f"**Voz:** {perfil_ativo['voz']}")
            st.markdown(f"**Emoção:** {perfil_ativo['emocao']}")
            st.markdown(f"**Gestos:** {perfil_ativo['gestos']}")
            st.caption("Ficha predefinida. Nada para preencher: a identidade já acompanha os prompts.")
        # Não acrescentar observações antigas ao perfil pronto selecionado.
        descricao_aplicada = montar_descricao_influencer_v164(perfil_ativo)
        perfil_em_sessao = st.session_state.get("influencer_atual") or {}
        st.session_state["influencer_atual"] = {
            "Email": email_elenco_v164,
            "Nome_Influencer": perfil_ativo["nome"],
            "Descricao_Visual": descricao_aplicada,
            "Logo_Marca": str(perfil_em_sessao.get("Logo_Marca", ""))
        }
        st.caption(f"✅ {perfil_ativo['nome']} está ativa automaticamente nos prompts de imagem, vídeo e fala dos Blocos 17 e 17.2.")
else:
    if perfil_sessao_atual.get("Nome_Influencer"):
        st.info("Sua influência salva continua ativa normalmente. Os cartões acima só serão marcados quando você clicar em um deles.")
    elif E_O_CEO:
        st.info("Sua influência original do CEO continua disponível. Se quiser ativá-la visualmente, clique no primeiro cartão. Você também pode escolher outra ou criar a sua própria.")
    else:
        st.info("Você pode escolher uma influenciadora da galeria ou criar a sua própria na aba 'Minha Influenciadora'.")

if st.session_state.pop("elevo_inf_erro_gravacao", False):
    st.warning("Personagem aplicada nesta sessão, mas o Google Sheets não confirmou o salvamento. Tente selecionar novamente para persistir.")

# ==========================================================
# 15. MATRIZ DE AMBIENTES ÉLÉVO V16.6 — 20 CENÁRIOS + 21º INFINITO
# Substitui APENAS a conversa de voz. Boas-vindas por áudio seguem intactas.
# ==========================================================
st.markdown('<div id="ambientes"></div>', unsafe_allow_html=True)
st.divider()
st.markdown('### 🌍 Estúdio de Ambientes · ÉLÉVO | 21 matrizes')
st.caption('São 20 ambientes com baguncinha e física própria + o 21º, Infinito. A mesma cena é fixada no prompt de imagem e no vídeo, nos Blocos 17 e 17.2.')

AMBIENTES_ELEVO_V165 = {'banheiro': {'nome': 'Banheiro Caótico', 'icone': '🚿', 'categoria': 'Interior', 'resumo': 'Espelho embaçado, toalha úmida e luz real de janela.', 'elementos': 'a lived-in Brazilian bathroom with a partly fogged mirror, a towel hanging off-center, a closed hair dryer on a DRY shelf away from water, subtle soap marks and a small porcelain sink', 'luz': 'soft daylight entering from a real side window, reflected with realistic falloff on wet and dry tiles', 'fisica': 'steam only where warm running water is explicitly present, condensation sliding slowly on the mirror, one damp towel corner moving only if a draft exists', 'som': 'distant ventilation hum and occasional water drip only if the tap is visible', 'animal': 'no animal'}, 'varanda': {'nome': 'Varanda Tropical', 'icone': '🌿', 'categoria': 'Natureza', 'resumo': 'Varanda tropical com vento, chuva eventual e folhas de bananeira em movimento.', 'elementos': 'a lived-in Brazilian covered tropical veranda with worn wood railings, a small ceramic mug and casually coiled phone cable on a rustic side table, hanging ferns and broad banana leaves outside under a roof edge; a cotton towel sits over the railing', 'luz': 'authentic overcast daylight with slightly warm reflected light from indoors; only rain if actively visible in this preset', 'fisica': 'outdoor banana leaves flutter with plausible inertia, hanging fern tips react asymmetrically to the same breeze; if rain is visible beyond the roof edge, droplets follow real gravity and the towel darkens only where wetted', 'som': 'light wind through leaves and rain on the roof only if raining', 'animal': 'a small bird sheltered in rafters only if introduced in the first still image'}, 'penteadeira': {'nome': 'Penteadeira Golden Hour', 'icone': '🪞', 'categoria': 'Interior', 'resumo': 'Maquiagem usada, espelho real e luz dourada de fim de tarde.', 'elementos': 'an everyday Brazilian vanity table with a softly smudged mirror, a few makeup brushes out of alignment, open compact powder, a hair clip and a slightly wrinkled cotton cloth', 'luz': 'low-angle golden hour sunlight crossing the tabletop with physically accurate mirror reflections', 'fisica': 'single floating dust motes near the window, faint cloth motion only under a real fan or draft, makeup tools staying in place', 'som': 'soft indoor room tone and distant street ambience', 'animal': 'no animal'}, 'servico': {'nome': 'Área de Serviço Raiz', 'icone': '🧺', 'categoria': 'Casa', 'resumo': 'Varal com roupas, tanque de cimento e piso com marcas de uso.', 'elementos': 'a humble Brazilian laundry area with a concrete utility sink, an upright blue bucket, a clothesline with two damp garments, a folded detergent box and authentic worn tile grout', 'luz': 'diffuse late-morning sun from an open patio side, consistent shadows under hanging laundry', 'fisica': 'wet sleeves dripping sparsely into the sink and fabric moving slowly only from an existing breeze; water keeps plausible gravity', 'som': 'distant domestic ambience, occasional isolated drip and cloth rustle', 'animal': 'no animal'}, 'jardim': {'nome': 'Jardim Rústico', 'icone': '🪴', 'categoria': 'Natureza', 'resumo': 'Costela-de-adão, mangueira no chão e folhas com marcas naturais.', 'elementos': 'a small rustic Brazilian garden with lush Monstera, irregular stepping stones, a coiled garden hose, leaf litter and terracotta pots showing realistic soil and water marks', 'luz': 'overcast daylight with naturally mottled shadow from real nearby leaves', 'fisica': 'independent foliage sway, a hose tip releasing water only if its tap is open, a few droplets soaking real soil', 'som': 'subtle garden insects, distant birds and leaf movement', 'animal': 'no animal unless explicitly included in image'}, 'cachoeira': {'nome': 'Cachoeira Secreta', 'icone': '💧', 'categoria': 'Natureza', 'resumo': 'Pedras molhadas, musgo, névoa e correnteza real.', 'elementos': 'a reachable natural cascade with moss-covered wet stones, a safe flat standing platform above the spray, textured bark, sparse fallen leaves and one folded linen towel on dry ground', 'luz': 'natural canopy-filtered daylight reflecting realistically off flowing water and wet rock', 'fisica': 'unbroken water stream with turbulence and splash, soft spray drifting with direction of air, towel staying dry outside the splash zone', 'som': 'continuous nearby running water with varying intensity', 'animal': 'no animal'}, 'cozinha': {'nome': 'Cozinha Afetiva', 'icone': '☕', 'categoria': 'Casa', 'resumo': 'Café passando, pano de prato e bancada que parece usada.', 'elementos': 'a real Brazilian home kitchen with a wooden counter, fresh coffee dripping into a pot, a slightly wrinkled checkered tablecloth, a spoon, an open recipe notebook and a half-used sponge', 'luz': 'soft morning daylight from the kitchen window, warm reflected light on ceramic mugs and metal handles', 'fisica': 'visible coffee drips only while the coffee maker operates, faint vapor near the hot pot, cloth responding to touch rather than floating', 'som': 'coffee drip, kettle clicks if present and gentle household ambience', 'animal': 'no animal'}, 'quarto': {'nome': 'Quarto Desarrumado', 'icone': '🛏️', 'categoria': 'Interior', 'resumo': 'Edredom amassado, roupa na cadeira e luz suave.', 'elementos': 'an authentic lived-in bedroom with imperfectly made bed, a sweater on a chair, one open drawer, a phone charging cable and partly open cotton curtains', 'luz': 'soft window daylight mixed with a low-intensity practical lamp, consistent warm and cool lighting', 'fisica': 'curtain edge moving with a real breeze, quilt compressing where touched, loose strands of hair moving with natural body motion', 'som': 'quiet bedroom ambience and distant outdoor noise', 'animal': 'a sleeping cat only if already present in image'}, 'quintal': {'nome': 'Quintal de Terra', 'icone': '🐕', 'categoria': 'Natureza', 'resumo': 'Terra batida, poeira leve e cachorro descansando ao fundo.', 'elementos': 'a sunlit Brazilian backyard with dry packed earth, a worn garden bench, slightly displaced flip-flops, a water bowl and a shaded corner under a fruit tree', 'luz': 'strong but realistic midday sun casting grounded coherent tree shadows', 'fisica': 'tiny dust particles lifting only from real footfalls, branches moving with breeze, water bowl remaining stable', 'som': 'distant neighborhood ambience and light dry leaves rustling', 'animal': 'one calm caramel-colored dog lying far in the background only if shown in image'}, 'piscina': {'nome': 'Deck de Piscina', 'icone': '🏖️', 'categoria': 'Lazer', 'resumo': 'Água refletindo luz, toalha no banco e respingos discretos.', 'elementos': 'an ordinary swimming pool deck with weathered planks, a striped towel on a solid chair, sunglasses resting on a bench and a clear glass safely away from the pool edge', 'luz': 'bright daytime sun and moving water-caustic reflections linked to actual pool surface', 'fisica': 'real non-repeating water ripples from a gentle breeze, towel fringe moving slightly, no floating props', 'som': 'soft pool water movement and ambient birds', 'animal': 'no animal'}, 'estufa': {'nome': 'Estufa Caseira', 'icone': '🌱', 'categoria': 'Natureza', 'resumo': 'Vasos com terra, samambaias e umidade nas superfícies.', 'elementos': 'a practical backyard greenhouse with hanging ferns, potted herbs, garden labels on stakes, a handheld sprayer and damp soil in terracotta containers', 'luz': 'diffused daylight through translucent roof panels with correct soft shadows', 'fisica': 'fine droplets on cold glass only where humidity makes sense, subtle leaves moving only where air enters and a single sprayer drip', 'som': 'greenhouse room tone, faint ventilation and occasional water droplet', 'animal': 'no animal'}, 'garagem': {'nome': 'Garagem Aberta', 'icone': '🧰', 'categoria': 'Urbano', 'resumo': 'Caixas, ferramentas, marcas de uso e luz dura do dia.', 'elementos': 'a genuinely used Brazilian residential garage with half-open rolling shutter, cardboard boxes stacked safely to one side, small scattered but grounded hand tools on an old workbench, a bicycle leaning on a wall and fine concrete-floor dust', 'luz': 'hard midday sun entering through the open door and casting sharp physically consistent shadows into softer interior light', 'fisica': 'a small draft shifts a piece of loose paper only, sun-lit dust motes visible in the light beam, bicycle and tools remain stationary and grounded, shutter vibrates slightly only if wind acts on it', 'som': 'distant street noise and light garage reverberation', 'animal': 'no animal'}, 'sala': {'nome': 'Sala de Estar Noturna', 'icone': '📺', 'categoria': 'Interior', 'resumo': 'TV acesa, manta no sofá e reflexos azuis discretos.', 'elementos': 'a lived-in Brazilian living room at night, an operating television, a folded throw loosely on the couch arm, a low coffee table with a remote and a small practical side lamp', 'luz': 'the television casts soft changing cool light aligned with the on-screen content and fixed warm lamp fill', 'fisica': 'the throw settles naturally after touch, illumination fluctuates only with the television, objects remain physically supported', 'som': 'quiet room tone and low TV hum without copyrighted content', 'animal': 'no animal'}, 'banheira': {'nome': 'Banheira Vintage', 'icone': '🛁', 'categoria': 'Interior', 'resumo': 'Azulejos antigos, espuma discreta e torneira pingando.', 'elementos': 'a vintage tiled bathroom with an old porcelain tub, weathered brass faucet, folded cotton towel, worn grout and a little foam where bath water actually touches the tub', 'luz': 'warm practical light reflecting realistically in porcelain and brass', 'fisica': 'a single faucet droplet gathering and falling at irregular intervals, mild water surface ripples only where water exists', 'som': 'isolated faucet drip and softly reverberant bathroom room tone', 'animal': 'no animal'}, 'praia': {'nome': 'Praia Deserta (Final de Tarde)', 'icone': '🌊', 'categoria': 'Lazer', 'resumo': 'Areia com marcas reais, vento marítimo e ondas ao fundo.', 'elementos': 'a nearly deserted Brazilian beach in late afternoon, a woven tote and flip-flops supported on dry upper sand away from surf, sparse coastal plants on dunes, visible foamy ocean waves and a single faded cotton beach towel weighted down at its corners', 'luz': 'late-afternoon directional golden sunlight with a real sea-horizon haze and soft shadows matching sun angle', 'fisica': 'wind ruffles the towel edge realistically but not the weighted corners; distant foam advances and recedes following wave cycles; loose beach hair and dune grasses move with the same breeze; sand grains shift only in a plausible gust', 'som': 'natural waves and sea breeze, no soundtrack', 'animal': 'a distant gull only if already visible in the image'}, 'escritorio': {'nome': 'Mesa de Escritório', 'icone': '💻', 'categoria': 'Trabalho', 'resumo': 'Home office real com LED discreto, papéis, caneca e planta.', 'elementos': 'a Brazilian home-office desk with scuffed wood grain, a slightly crumpled stack of papers, an open notebook, black computer mouse, small Monstera pot, a cup with old coffee ring, a practical desk lamp and a soft cyan LED reflected on the wall', 'luz': 'natural window daylight blended with a restrained warm desk lamp and low cyan LED without impossible color changes', 'fisica': 'a page corner shifts only if a real draft enters, a plant leaf moves subtly in the airflow, glass condensation falls only if a cold drink is present, lamp and cable remain physically fixed', 'som': 'quiet room tone, low computer fan and soft street noise', 'animal': 'no animal'}, 'carro_chuva': {'nome': 'Janela do Carro (Chuva)', 'icone': '🚗', 'categoria': 'Urbano', 'resumo': 'Gotas no vidro, carros passando e luzes da cidade.', 'elementos': 'a securely parked Brazilian car interior on a rainy evening, side window covered with distinct rolling water droplets, realistic street lamps and distant neon reflections on wet glass, a folded cotton jacket on passenger seat and a simple dashboard', 'luz': 'muted evening light with real reflections from street lamps and signage outside, no invented cinematic strobe', 'fisica': 'water droplets merge and move down the glass by gravity, background cars create coherent perspective motion, reflections slide with camera angle and window curvature, interior objects stay still', 'som': 'soft rain tapping car roof, passing traffic at distance and interior room tone', 'animal': 'no animal'}, 'leitura': {'nome': 'Canto da Leitura', 'icone': '📚', 'categoria': 'Interior', 'resumo': 'Poltrona de tecido, páginas abertas e feixe de luz.', 'elementos': 'an intimate reading corner with a textured armchair, a paperback open on the side table, a knitted throw, a ceramic tea cup and books with imperfectly aligned spines', 'luz': 'angled window light catching faint atmospheric dust, soft falloff into the room', 'fisica': 'pages shift only with touch or a real breeze, throw compresses under a hand, cup stays still on the table', 'som': 'soft room ambience and distant passing wind', 'animal': 'no animal'}, 'lavabo': {'nome': 'Lavabo Luxo Decadente', 'icone': '🧼', 'categoria': 'Interior', 'resumo': 'Mármore usado, manchas discretas de água e luz dourada.', 'elementos': 'an elegant but lived-in Brazilian lavabo with slightly worn marble countertop, tiny dried water stains near brushed brass tap, subtly imperfect mirror, rolled cotton hand towel, used soap dish and warm pendant lighting', 'luz': 'warm intimate pendant light with coherent light falloff across marble and mirror', 'fisica': 'micro-reflections follow camera motion, towel fibers settle after actual contact, real water droplets only when water source is active, reflections stay spatially consistent', 'som': 'low indoor room tone and faucet water only if running', 'animal': 'no animal'}, 'calcada': {'nome': 'Calçada Chuvosa', 'icone': '🏙️', 'categoria': 'Urbano', 'resumo': 'Piso molhado, poste aceso e reflexos de rua à noite.', 'elementos': 'a Brazilian urban sidewalk at dusk after rain, patterned concrete pavers with wet seams, a metal bench with weathered paint, reflective shallow puddles near curb, a lit street lamp and rain-darkened storefront shutters in the distance', 'luz': 'believable cool dusk and warm street lamp reflections that follow actual puddle geometry', 'fisica': 'individual raindrops only if rain is still falling; water ripples radiate from actual drops, one breeze lifts loose hair and clothing gently, distant pedestrian parallax remains consistent', 'som': 'distant wet-traffic hiss, realistic footsteps and rain if ongoing', 'animal': 'no animal'}, 'infinito': {'nome': 'Ambiente 21 — Infinito', 'icone': '♾️', 'categoria': 'Aleatório', 'resumo': 'Escolhe entre 20 matrizes, com variações sutis e sem repetir a cena recente.', 'elementos': 'sorteio de ambiente real com objetos, iluminação e clima contextualizados', 'luz': 'a definida pela matriz sorteada', 'fisica': 'a definida pela matriz sorteada', 'som': 'o da matriz sorteada', 'animal': 'somente se a cena sorteada permitir'}}

# ==========================================================
# ÉLÉVO V16.8.2 — VIDA ORGÂNICA EM TODOS OS 20 AMBIENTES + INFINITO
# Não altera ids, cartões, filtros, conta ou persistência.
# Cada cenário tem UMA planta discreta, baguncinha contextual e um animal
# em segundo plano, sem interferir com produto, rosto ou área perigosa.
# ==========================================================
VIDA_ORGANICA_V1682 = {
    'banheiro': ('a small pothos in a ceramic pot on a dry shelf', 'a slightly crooked washcloth and a half-folded bath towel', 'one quiet house cat visible through the safely open bathroom doorway, away from wet surfaces'),
    'varanda': ('one lush potted fern beside the railing', 'an everyday mug and an unevenly folded cotton cloth on the side table', 'one relaxed caramel-colored dog resting in the shaded far corner'),
    'penteadeira': ('a miniature leafy plant at the far end of the vanity', 'two makeup brushes loosely placed beside an open makeup pouch', 'a house cat stretching quietly on the bedroom rug behind the subject'),
    'servico': ('a hardy potted fern on an elevated dry shelf', 'a mismatched clothespin and folded work towel beside the sink', 'a calm dog lying outside the doorway, away from laundry equipment'),
    'jardim': ('a small terracotta pot of fresh herbs near the path', 'a coiled hose and a gardening glove slightly out of place', 'a dog sniffing the grass behind the bench, distant from the product'),
    'cachoeira': ('a small naturally rooted fern on a protected rock shelf', 'a folded linen towel and a woven bag resting on dry high ground', 'a distant dog resting on a safe dry path away from the water'),
    'cozinha': ('a small potted basil plant by the window', 'a slightly skewed dish towel and a spoon next to the cup', 'a cat quietly sitting in the doorway, away from cooking and countertops'),
    'quarto': ('a hardy small pothos in a pot on a sideboard', 'a partly folded blanket and a casually placed book', 'a sleepy cat on the far corner of the bed'),
    'quintal': ('a leafy potted plant by a worn garden wall', 'well-used sandals and a small gardening rag beside the bench', 'one calm caramel-colored dog lying in the shade near its water bowl'),
    'piscina': ('a potted tropical palm well away from the water edge', 'a loosely folded dry towel and sunglasses resting on a stable side table', 'one calm dog lying on a shaded dry patch, far from the pool'),
    'estufa': ('a leafy plant in a weathered terracotta pot among established herbs', 'a slightly crooked garden label and an unused sprayer on the shelf', 'a house cat resting just outside the open greenhouse door'),
    'garagem': ('a leafy plant in a sturdy pot by the entrance', 'a work glove and a folded cleaning rag near a closed toolbox', 'a relaxed dog on a dry mat at the doorway, away from vehicles and tools'),
    'sala': ('one potted monstera behind the sofa', 'a folded throw slightly displaced and a magazine on the coffee table', 'a cat dozing on the rug behind the sofa'),
    'banheira': ('one small potted fern on a dry shelf beside the window', 'a casually folded bath towel and a ceramic soap dish', 'a quiet cat visible beyond the open door, away from the bathtub'),
    'praia': ('one naturally growing coastal plant beyond the high-tide line', 'a woven beach bag and a towel with imperfect folds on dry sand', 'a calm dog resting far behind the subject near the safe beach access'),
    'escritorio': ('a real leafy pothos in a pot by the window', 'an open notebook, a slightly tangled charging cable and a used coffee mug', 'a sleeping cat on a side cushion away from the desk'),
    'carro_chuva': ('a small secure potted plant visible on a shop windowsill outside the parked car', 'a casually folded jacket and a paper receipt on the stable passenger-side seat', 'a calm dog visible on the dry covered sidewalk through the window, not in traffic'),
    'leitura': ('a small potted fern on a stable shelf', 'a bookmarked open paperback and a knitted throw with natural folds', 'a cat curled up on a rug next to the armchair'),
    'lavabo': ('a small potted leafy plant on a dry high shelf', 'a softly creased hand towel and a soap dish with realistic water marks', 'a house cat briefly visible beyond the open doorway, away from the sink'),
    'calcada': ('a potted shrub beside an existing doorway under an awning', 'a slightly folded newspaper and a closed umbrella by the bench', 'a calm dog resting beneath the dry awning, outside the pedestrian path'),
}
for _ambiente_id, (_planta, _baguncinha, _animal) in VIDA_ORGANICA_V1682.items():
    _cena = AMBIENTES_ELEVO_V165[_ambiente_id]
    _cena['elementos'] += ('. BACKGROUND PLANT: ' + _planta +
                          '. ORGANIC LIVED-IN CLUTTER: ' + _baguncinha +
                          '. ONE DISTANT BACKGROUND ANIMAL: ' + _animal)
    _cena['animal'] = _animal + '; only this one animal, no additional pets'
    _cena['fisica'] += ('; physically grounded micro-reactions: existing leaves respond only to a plausible draft, '
                       'existing fabrics preserve weight and folds, the single background animal breathes or blinks subtly; '
                       'background stays secondary to the product and person')

# Sincroniza por Gmail quando possível, sem bloquear se Sheets estiver fora.
def _planilha_ambiente_v165():
    if not robo_sheets:
        return None
    try:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_BANCO_MESTRE)
        if not match:
            return None
        aba_documento = robo_sheets.open_by_key(match.group(1))
        try:
            return aba_documento.worksheet('Ambientes_Elevo')
        except gspread.exceptions.WorksheetNotFound:
            aba = aba_documento.add_worksheet(title='Ambientes_Elevo', rows='1000', cols='4')
            aba.append_row(['Email', 'Ambiente_ID', 'Detalhes', 'Atualizado_Em'])
            return aba
    except Exception:
        return None

def _salvar_ambiente_v165(email, selecionado, detalhes):
    aba = _planilha_ambiente_v165()
    if aba is None:
        return False
    try:
        emails = aba.col_values(1)
        ids = [i for i, valor in enumerate(emails, start=1)
               if i > 1 and str(valor).strip().lower() == email]
        valores = [selecionado, detalhes, datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')]
        if ids:
            aba.update(f'B{ids[-1]}:D{ids[-1]}', [valores])
        else:
            aba.append_row([email] + valores)
        return True
    except Exception:
        return False

def _ler_ambiente_v165(email):
    aba = _planilha_ambiente_v165()
    if aba is None:
        return None
    try:
        dados = [r for r in aba.get_all_records() if str(r.get('Email', '')).strip().lower() == email]
        if dados:
            atual = dados[-1]
            identidade = str(atual.get('Ambiente_ID', '')).strip()
            if identidade in AMBIENTES_ELEVO_V165 or not identidade:
                return identidade, str(atual.get('Detalhes', ''))[:650]
    except Exception:
        pass
    return None

email_ambiente_v165 = str(st.session_state.get('email_usuario', '')).strip().lower()
if st.session_state.get('elevo_ambiente_carregado_email') != email_ambiente_v165:
    registro = _ler_ambiente_v165(email_ambiente_v165)
    st.session_state['elevo_ambiente_id'] = registro[0] if registro else ''
    st.session_state['elevo_ambiente_obs'] = registro[1] if registro else ''
    st.session_state['elevo_ambiente_carregado_email'] = email_ambiente_v165

st.markdown("""<style>
.elevo-ambiente-card {height:192px;margin:4px 0 7px;padding:14px 13px 12px;border-radius:16px;overflow:hidden;
 border:1px solid rgba(104,154,230,.22);background:linear-gradient(145deg,#14253f,#101a2c);}
.elevo-ambiente-card.ativo {border-color:#42d6ff;box-shadow:0 0 0 1px rgba(66,214,255,.20),0 8px 22px rgba(24,135,210,.12);}
.elevo-ambiente-card .icone {font-size:24px;margin-bottom:6px;}
.elevo-ambiente-card .nome {font-size:.85rem;color:#f2f7ff;font-weight:800;line-height:1.35;}
.elevo-ambiente-card .tag {font-size:.62rem;color:#71bafb;letter-spacing:.08em;margin:5px 0 6px;}
.elevo-ambiente-card .descricao {font-size:.71rem;color:#b4c6dd;line-height:1.48;
    display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}
.elevo-ambiente-card .flag {color:#73e8ce;font-size:.68rem;font-weight:800;margin-top:8px;}
@media (max-width:760px){.elevo-ambiente-card {height:192px}}
 </style>""", unsafe_allow_html=True)

items_ambiente = list(AMBIENTES_ELEVO_V165.items())
st.markdown(
    '<div class="elevo-carrossel-instrucao">'
    '<span>🌍 Deslize para escolher seu ambiente</span>'
    f'<span class="pista">{len(items_ambiente)} cenários · ⇆</span>'
    '</div>', unsafe_allow_html=True
)
with st.container(horizontal=True, wrap=False, gap="small", key="elevo_carrossel_ambientes"):
    for chave, cena in items_ambiente:
        with st.container(width=236):
            ativo = st.session_state.get('elevo_ambiente_id', '') == chave
            selo_amb = '<div class="flag">● SELECIONADO</div>' if ativo else ''
            st.markdown(
                f'<article class="elevo-ambiente-card{" ativo" if ativo else ""}">'
                f'<div class="icone">{cena["icone"]}</div>'
                f'<div class="nome">{html_std.escape(cena["nome"])}</div>'
                f'<div class="tag">{html_std.escape(cena["categoria"].upper())}</div>'
                f'<div class="descricao">{html_std.escape(cena["resumo"])}</div>'
                f'{"<div class=\"flag\">● SELECIONADO</div>" if ativo else ""}'
                '</article>', unsafe_allow_html=True)
            if st.button('✓ Escolhido' if ativo else 'Escolher cenário',
                         key=f'elevo_ambiente_card_{chave}',
                         type='primary' if ativo else 'secondary',
                         disabled=ativo, use_container_width=True):
                st.session_state['elevo_ambiente_id'] = chave
                st.session_state['elevo_ambiente_obs'] = ''
                salvo = _salvar_ambiente_v165(email_ambiente_v165, chave, '')
                st.session_state['elevo_ambiente_aviso'] = '' if salvo else 'Cena aplicada nesta sessão; não foi possível salvar no Google Sheets.'
                st.rerun()

selecao_v165 = st.session_state.get('elevo_ambiente_id', '')
if selecao_v165 in AMBIENTES_ELEVO_V165:
    cena = AMBIENTES_ELEVO_V165[selecao_v165]
    if selecao_v165 == 'infinito':
        st.info('♾️ Modo Infinito ativo: cada nova geração escolhe uma das 20 matrizes e a mantém fixa na imagem e no vídeo. O sorteio evita os cenários usados mais recentemente nesta sessão.')
        ultimo = st.session_state.get('elevo_ambiente_ultimo_infinito', '')
        if ultimo in AMBIENTES_ELEVO_V165 and ultimo != 'infinito':
            st.caption(f'Último cenário escolhido: {AMBIENTES_ELEVO_V165[ultimo]["nome"]}')

    col_cena, col_detalhes = st.columns([1.15,1], gap='medium')
    with col_cena:
        with st.container(border=True):
            st.markdown(f'#### {cena["icone"]} {cena["nome"]}')
            st.caption('Ficha cinematográfica do ambiente selecionado')
            st.markdown(f'**🌤 Luz:** {cena["luz"]}')
            st.markdown(f'**🎭 Baguncinha:** {cena["elementos"]}')
            st.markdown(f'**💨 Física e movimento:** {cena["fisica"]}')
            st.markdown(f'**🔊 Som ambiente:** {cena["som"]}')
    with col_detalhes:
        with st.container(border=True):
            st.markdown('#### ✍️ Personalização (opcional)')
            st.caption('Acrescente um detalhe já compatível com a cena. Não é necessário descrever tudo.')
            st.text_area('Detalhe adicional do ambiente', key='elevo_ambiente_obs', max_chars=650, height=135,
                         placeholder='Ex.: caneca de cerâmica ao lado, toalha levemente úmida, luz suave pela janela...')
            if st.button('💾 Salvar detalhes do ambiente', key='elevo_ambiente_salvar', use_container_width=True):
                if _salvar_ambiente_v165(email_ambiente_v165, selecao_v165, str(st.session_state.get('elevo_ambiente_obs',''))[:650]):
                    st.success('Cenário e detalhes salvos neste Gmail.')
                else:
                    st.warning('Os detalhes valerão nesta sessão. O Google Sheets não confirmou o salvamento.')
    st.caption('✅ A direção do ambiente alimenta os Blocos 17 e 17.2. O resultado visual depende do gerador externo: o ÉLÉVO não garante fidelidade de 100%.')
else:
    st.info('Nenhum ambiente escolhido. Se gerar um prompt agora, permanece o sorteio de cenários original. Para fixar um, clique em “Escolher cenário”.')

if st.button('↺ Voltar ao sorteio original (sem cena fixa)', key='elevo_ambiente_liberar', use_container_width=False):
    st.session_state['elevo_ambiente_id'] = ''
    st.session_state['elevo_ambiente_obs'] = ''
    salvo = _salvar_ambiente_v165(email_ambiente_v165, '', '')
    st.session_state['elevo_ambiente_aviso'] = '' if salvo else 'Sorteio automático ativo nesta sessão; não foi possível sincronizar com Google Sheets.'
    st.rerun()
if st.session_state.pop('elevo_ambiente_aviso', ''):
    st.warning('O cenário escolhido funciona nesta sessão, mas a preferência pode não persistir após encerrar a sessão.')


# ==========================================================
# 16. PAINEL DE CONTROLE DO CEO
# ==========================================================
if E_O_CEO:
    st.divider()
    st.markdown("<h3 style='text-align: center; color: #FF0040;'>👑 Painel de Controle do CEO</h3>", unsafe_allow_html=True)
    with st.expander("🛡️ ABRIR GESTÃO DE USUÁRIOS", expanded=False):
        usuarios_bd = conectar_banco_usuarios("ler")
        if usuarios_bd:
            df_usuarios_admin = pd.DataFrame(usuarios_bd)
            st.dataframe(df_usuarios_admin[[c for c in ["Email", "Nome"] if c in df_usuarios_admin.columns]],
                         use_container_width=True, hide_index=True)
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
st.markdown('<div id="criacao"></div>', unsafe_allow_html=True)

# ==========================================================
# 17. MÁQUINA DE CRIAÇÃO 360º (MÁXIMA POTÊNCIA / LEMA DOR & SOLUÇÃO + BANCO DE MEMÓRIA 17.3)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00BFA5;'>🎬 Máquina de Criação 360º (V12 — Imagem Original + Vídeo Física Viva)</h3>", unsafe_allow_html=True)

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

def render_botao_copiar_vip(texto_para_copiar, label_botao, id_unico):
    if not texto_para_copiar:
        return
    b64_txt = base64.b64encode(texto_para_copiar.strip().encode('utf-8')).decode('utf-8')
    html_btn = f"""
    <div style="display: flex; justify-content: flex-end; align-items: center; margin: 2px 0;">
        <button id="btn_{id_unico}" onclick="copiarTexto_{id_unico}()" style="
            background: linear-gradient(135deg, #002B5B 0%, #004080 100%);
            color: #FFFFFF;
            border: 1.5px solid #00E5FF;
            border-radius: 10px;
            padding: 8px 14px;
            font-family: 'Montserrat', sans-serif;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 3px 12px rgba(0, 229, 255, 0.25);
            transition: all 0.2s ease;
            width: 100%;
            text-align: center;
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
            btn.innerHTML = "✅ COPIADO!";
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
        }} else {{
            fallbackCopy(texto);
        }}

        function fallbackCopy(txt) {{
            const ta = document.createElement("textarea");
            ta.value = txt;
            ta.style.position = "fixed";
            ta.style.left = "-9999px";
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            try {{
                document.execCommand('copy');
                confirmarCopia();
            }} catch (e) {{}}
            document.body.removeChild(ta);
        }}
    }}
    </script>
    """
    components.html(html_btn, height=45)

def render_microfone_diretrizes_youtube():
    html_mic = """
    <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: -6px; margin-bottom: 6px;">
        <button id="btn_mic_yt" onclick="toggleDictation()" style="
            background: linear-gradient(135deg, #161B24 0%, #0F131A 100%);
            color: #00E5FF;
            border: 1.5px solid #00E5FF;
            border-radius: 50px;
            padding: 6px 14px;
            font-family: 'Montserrat', sans-serif;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 0 12px rgba(0, 229, 255, 0.25);
            transition: all 0.25s ease;
        ">
            <span id="mic_icon" style="font-size: 15px;">🎙️</span>
            <span id="mic_text">Falar Diretrizes (Voz Automática)</span>
        </button>
        <span id="mic_status" style="font-family: 'Montserrat', sans-serif; font-size: 11px; color: #94A3B8;"></span>
    </div>

    <script>
    let recognition = null;
    let isListening = false;

    function encontrarTextareaDiretrizes() {
        const parentDoc = window.parent.document;
        const textareas = parentDoc.querySelectorAll('textarea');
        for (let ta of textareas) {
            if (ta.placeholder && ta.placeholder.includes("Quero que ela mostre a textura")) {
                return ta;
            }
            if (ta.getAttribute('aria-label') && ta.getAttribute('aria-label').includes("Diretrizes")) {
                return ta;
            }
        }
        return textareas.length > 0 ? textareas[0] : null;
    }

    function injetarTextoNoStreamlit(ta, novoTexto) {
        if (!ta) return;
        const textoAtual = ta.value ? ta.value.trim() + " " : "";
        const textoFinal = textoAtual + novoTexto.trim();
        const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
        nativeTextAreaValueSetter.call(ta, textoFinal);
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        ta.dispatchEvent(new Event('change', { bubbles: true }));
        ta.focus();
    }

    function toggleDictation() {
        const btn = document.getElementById('btn_mic_yt');
        const txt = document.getElementById('mic_text');
        const status = document.getElementById('mic_status');
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            status.innerHTML = "⚠️ Use o navegador Chrome/Edge para voz ao vivo.";
            status.style.color = "#FFD700";
            return;
        }

        if (isListening && recognition) {
            recognition.stop();
            return;
        }

        recognition = new SpeechRecognition();
        recognition.lang = 'pt-BR';
        recognition.interimResults = false;
        recognition.continuous = false;

        recognition.onstart = function() {
            isListening = true;
            btn.style.background = "linear-gradient(135deg, #FF0040 0%, #990026 100%)";
            btn.style.borderColor = "#FF0040";
            btn.style.color = "#FFFFFF";
            btn.style.boxShadow = "0 0 18px rgba(255, 0, 64, 0.6)";
            txt.innerHTML = "🔴 Ouvindo... (Clique para parar)";
            status.innerHTML = "Pode falar agora...";
            status.style.color = "#00FF9D";
        };

        recognition.onresult = function(event) {
            let transcript = "";
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    transcript += event.results[i][0].transcript;
                }
            }
            if (transcript) {
                const ta = encontrarTextareaDiretrizes();
                injetarTextoNoStreamlit(ta, transcript);
                status.innerHTML = "✅ Texto inserido! (Aperte Enter ou clique fora da caixa)";
                status.style.color = "#00FF9D";
            }
        };

        recognition.onerror = function(event) {
            status.innerHTML = "⚠️ Permita o microfone no navegador.";
            status.style.color = "#FF2E54";
        };

        recognition.onend = function() {
            isListening = false;
            btn.style.background = "linear-gradient(135deg, #161B24 0%, #0F131A 100%)";
            btn.style.borderColor = "#00E5FF";
            btn.style.color = "#00E5FF";
            btn.style.boxShadow = "0 0 12px rgba(0, 229, 255, 0.25)";
            txt.innerHTML = "Falar Diretrizes (Voz Automática)";
        };

        recognition.start();
    }
    </script>
    """
    components.html(html_mic, height=44)

def extrair_blocos_roteiro(md_texto):
    dados = {
        "prompt_imagem": "",
        "prompt_video": "",
        "secao_seo_texto": "",
        "titulo_1": "",
        "titulo_2": "",
        "titulo_3": ""
    }
    if not md_texto:
        return dados

    m_img = re.search(r'###\s*📸\s*PROMPT DE IMAGEM[^\n]*\n(.*?)(?=###\s*🎬|\Z)', md_texto, re.DOTALL | re.IGNORECASE)
    if m_img:
        dados["prompt_imagem"] = m_img.group(1).strip()

    m_vid = re.search(r'###\s*🎬\s*PROMPT DE VÍDEO[^\n]*\n(.*?)(?=###\s*🔑|\Z)', md_texto, re.DOTALL | re.IGNORECASE)
    if m_vid:
        dados["prompt_video"] = m_vid.group(1).strip()

    m_seo = re.search(r'###\s*🔑\s*TÍTULOS SEO[^\n]*\n(.*)', md_texto, re.DOTALL | re.IGNORECASE)
    if m_seo:
        secao_seo = m_seo.group(1).strip()
        dados["secao_seo_texto"] = secao_seo
        linhas_seo = [l.strip() for l in secao_seo.split('\n') if l.strip()]
        titulos_limpos = []
        for l in linhas_seo:
            if ":" in l and not l.startswith("#") and "legenda" not in l.lower() and "hashtag" not in l.lower():
                parte_limpa = l.split(":", 1)[1].replace("*", "").strip()
                if parte_limpa:
                    titulos_limpos.append(parte_limpa)
        if len(titulos_limpos) >= 1: dados["titulo_1"] = titulos_limpos[0]
        if len(titulos_limpos) >= 2: dados["titulo_2"] = titulos_limpos[1]
        if len(titulos_limpos) >= 3: dados["titulo_3"] = titulos_limpos[2]

    return dados

def escanear_dor_e_contagem_da_foto(img_b64):
    """
    Lê a foto para extrair:
    1) O nome comercial exato em português.
    2) A quantidade exata de itens (1, 2, 3, 5...).
    3) A DOR REAL que o produto resolve + o DESEJO/SENSAÇÃO escrita no rótulo (ex: 'cabelo elástico de química, pontas espigadas, falta de massa' -> 'efeito ampola, reconstrução de salão no chuveiro, desmaia o fio').
    4) A regra universal de referência externa do produto e posicionamento fisicamente plausível.
    """
    try:
        validar_cota_ia()
        resp_s = cliente_openai.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a Neuromarketing & Product Scanner. Output flat JSON only (never output lists or nested dicts)."},
                {"role": "user", "content": [
                    {"type": "text", "text": (
                        "Analyze the product packaging/label in this image and return a JSON with ONLY 5 flat keys:\n"
                        "1. 'nome_pt': commercial name of the product/kit in Portuguese.\n"
                        "2. 'qtd': integer count of product units in the image (1, 2, 3, 5, etc.).\n"
                        "3. 'tipo_embalagem': short English container type without colors (e.g., '400g cosmetic tub', '300ml pump bottle', 'crochet shorts').\n"
                        "4. 'dor_visceral_pt': what painful everyday problem does this product solve according to its label? (e.g., 'cabelo esturricado de chapinha, elástico de química, ralo e quebrando só de pentear' or 'vergonha de servir visita em pote velho').\n"
                        "5. 'sensacao_solucao_pt': what tangible sensation/transformation does it deliver? (e.g., 'cauterização de salão no próprio chuveiro, preenche a fibra e deixa o fio pesado de brilho espelhado')."
                    )},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]}
            ],
            temperature=0.2
        )
        dados_scan = json.loads(resp_s.choices[0].message.content)
        qtd = int(dados_scan.get("qtd", 1))
        tipo_emb = str(dados_scan.get("tipo_embalagem", "product container"))
        nome_pt = str(dados_scan.get("nome_pt", "Produto Principal"))
        dor_pt = str(dados_scan.get("dor_visceral_pt", "necessidade verificável no rótulo"))
        solucao_pt = str(dados_scan.get("sensacao_solucao_pt", "benefício documentado na embalagem"))
    except Exception:
        qtd = 1
        tipo_emb = "product container"
        nome_pt = "Produto Principal"
        dor_pt = "necessidade apresentada pelo usuário ou indicada claramente no rótulo"
        solucao_pt = "característica verificável na embalagem, sem inventar efeitos"

    qtd = max(1, min(qtd, 30))
    # O scanner identifica o produto para FALA/SEO; a aparência é competência
    # EXCLUSIVA da fotografia carregada no gerador externo de imagem/vídeo.
    # Nada de descrever cor, tipo de frasco, rótulo, peso ou lote no prompt visual.
    regra_escala = (
        "Use the separately supplied PRODUCT REFERENCE IMAGE as the sole authority for "
        "the item's identity, packaging, surface, colors, markings and relative real-world scale. "
        "Never verbally reconstruct or reinterpret its appearance. Preserve its proportions "
        "relative to the presenter's hand and supporting furniture. Do NOT automatically enlarge "
        "small items or force genuinely large items into a compact hand-sized container. "
        "Avoid exaggerated wide-angle near-lens perspective. The product must not be closer "
        "to the lens than the supporting hand; plausible physical depth and stable geometry. "
    )
    if qtd <= 1:
        regra_pos_img = (
            "Show exactly ONE item from the product reference, naturally supported by the "
            "presenter's hand IF its actual size permits, otherwise securely on the scene's "
            "existing stable surface beside the presenter. " + regra_escala
        )
        regra_pos_vid = (
            "Keep that SAME single photo-referenced item at the SAME believable scale and "
            "supported location for all frames, with no vanishing, recoloring or replacement. " + regra_escala
        )
    else:
        resto = qtd - 1
        regra_pos_img = (
            f"[KIT INVENTORY — exactly {qtd} referenced items]: Keep ONE unit naturally "
            "supported in the hand only if physically practical, otherwise on the support; "
            f"the other {resto} referenced item(s) rest on the existing stable surface. "
            "All units remain separately visible, never merged, duplicated or recolored. " + regra_escala
        )
        regra_pos_vid = (
            f"[KIT INVENTORY — exactly {qtd} referenced items]: Keep the same one "
            f"supported unit and remaining {resto} units on their original supports; "
            "no swapping positions, none disappearing from 0:00 to the last frame. " + regra_escala
        )

    return {
        "nome_pt": nome_pt,
        "qtd": qtd,
        "tipo_embalagem": tipo_emb,
        "dor_pt": dor_pt,
        "solucao_pt": solucao_pt,
        "regra_pos_img": regra_pos_img,
        "regra_pos_vid": regra_pos_vid
    }

email_sessao = st.session_state.get("email_usuario", "anonimo")
if not st.session_state["roteiro_temporario"]:
    roteiro_salvo_nuvem = carregar_ultimo_roteiro_salvo(email_sessao)
    if roteiro_salvo_nuvem and "can't assist" not in roteiro_salvo_nuvem.lower():
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
    if E_O_CEO:
        # Restaurado exatamente o fallback do CEO anterior à V16.4.
        # Se houver perfil salvo no Sheets, o ramo anterior continua prevalecendo.
        nome_inf_ativa = "Aurora"
        desc_inf_ativa = "Photorealistic young Brazilian woman (Aurora: dark hair, subtle bangs, intense conspiratorial expression, incredibly shiny and healthy-looking hair)"
        eh_customizada = False
    else:
        nome_inf_ativa = "Aurora"
        desc_inf_ativa = "Fictional adult Brazilian virtual presenter, natural appearance, realistic skin texture, conversational Brazilian Portuguese voice, expressions and body language adapted to the product without exaggerated acting; maintain consistent identity throughout image and video."
        eh_customizada = False

logo_padrao_ceo = "O Achado Secreto"
logo_salva_banco = str(inf_salva.get("Logo_Marca", "")).strip() if inf_salva else ""
if logo_salva_banco:
    logo_ativa_usuario = logo_salva_banco
elif E_O_CEO:
    logo_ativa_usuario = logo_padrao_ceo
else:
    logo_ativa_usuario = "Minha Marca VIP"

pode_gerar_roteiro = bool(E_O_CEO)
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
            pode_gerar_roteiro = usos_feitos < 3
    except Exception:
        pode_gerar_roteiro = False

if "txt_diretrizes_360" not in st.session_state:
    st.session_state["txt_diretrizes_360"] = ""

with st.container(border=True):
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        if st.button("⚙️ MODO 360º (Bloco 17 — Física V12)", type="primary" if not st.session_state["modo_entidade_v9"] else "secondary", use_container_width=True, key="btn_sel_17"):
            st.session_state["modo_entidade_v9"] = False
            st.rerun()
    with col_sel2:
        if st.button("🧬 CRIAÇÃO V9.2 (Bloco 17.2 — Física V12)", type="primary" if st.session_state["modo_entidade_v9"] else "secondary", use_container_width=True, key="btn_sel_172"):
            st.session_state["modo_entidade_v9"] = True
            st.rerun()

    aba_gerador_360, aba_config_influencer = st.tabs([
        "📸 Gerar Roteiro & Diretrizes", 
        "👤 Minha Influenciadora"
    ])
    
    with aba_gerador_360:
        if eh_customizada:
            st.success(f"✅ **Influenciadora ativa:** {nome_inf_ativa}")
            st.caption("Identidade, voz, emoção e aparência já incluídas automaticamente no prompt.")
        else:
            if E_O_CEO:
                st.caption("🦅 **Influencer Padrão do CEO Ativa:** Aurora Original (Para testar outra personagem, acesse a aba ao lado).")
            else:
                st.warning("⚠️ Você ainda não cadastrou a sua própria Influencer! O sistema usará a personagem padrão (Aurora). Vá na aba **'👤 Configurar Minha Influencer'** acima para criar e salvar a sua!")
        
        col_img, col_dados = st.columns([1, 1])
        with col_img: 
            img_produto = st.file_uploader("📸 Foto do Produto", type=["png", "jpg", "jpeg"], key="img_produto_roteiro")
        with col_dados:
            render_microfone_diretrizes_youtube()
            
            explicacao_video_usuario = st.text_area(
                "📝 Diretrizes / O que você quer no vídeo? (Opcional)",
                placeholder="Ex: Quero que ela mostre a textura do produto, foque nos detalhes ou fale com tom de segredo...",
                height=115,
                help="Clique no botão '🎙️ Falar Diretrizes' acima para ditar por voz igual no YouTube/Google, ou digite manualmente!",
                key="txt_diretrizes_360"
            )
            btn_gerar_roteiro = False
            if not st.session_state["modo_entidade_v9"]:
                if not pode_gerar_roteiro:
                    st.error("🚨 LIMITE ATINGIDO! Você já gerou os seus 3 roteiros gratuitos. Faça o upgrade para a conta CEO para uso ilimitado.")
                    btn_gerar_roteiro = st.button("⚡ LER RÓTULO E GERAR", type="primary", use_container_width=True, disabled=True, key="btn_gerar_360_disabled")
                else:
                    txt_botao = "⚡ LER RÓTULO E GERAR (Ilimitado)" if E_O_CEO else f"⚡ LER RÓTULO E GERAR ({3 - usos_feitos} Restantes)"
                    btn_gerar_roteiro = st.button(txt_botao, type="primary", use_container_width=True, key="btn_gerar_360_ativo")
            else:
                st.success("🧬 **CRIAÇÃO V9.2 ATIVADA!** Clique no botão do **Bloco 17.2** logo abaixo.")

    
with aba_config_influencer:
    st.markdown("<h4 style='color: #00E5FF;'>🧬 Identidade Visual da Sua Influenciadora</h4>", unsafe_allow_html=True)
    st.caption("As influenciadoras da galeria já estão completas: é só escolher. Use esta aba apenas se quiser criar uma personagem totalmente sua. Nenhum cartão vem marcado automaticamente.")

    dados_ativos_tab = st.session_state.get("influencer_atual") or {}
    nome_ativo_tab = str(dados_ativos_tab.get("Nome_Influencer") or ("Aurora" if E_O_CEO else "Nenhuma salva"))
    if dados_ativos_tab.get("Nome_Influencer") or E_O_CEO:
        st.success(f"✅ Influenciadora ativa: {nome_ativo_tab}")
        st.caption("Dados técnicos guardados; os Blocos 17 e 17.2 os utilizam automaticamente.")

    col_tab_a, col_tab_b = st.columns([1, 1])
    with col_tab_a:
        novo_nome_inf = st.text_input(
            "👤 Nome da sua Influenciadora:",
            placeholder="Ex: Maya, Valentina, Bia...",
            key="input_nome_inf"
        )
    with col_tab_b:
        st.caption("Se quiser abandonar o perfil atual, limpe a memória do seu login:")
        if st.button("🧹 Limpar influencer do meu login", type="secondary", use_container_width=True, key="btn_excluir_inf"):
            with st.spinner("Removendo influencer da memória para liberar novo cadastro..."):
                gerenciar_influencer_usuario("excluir", email_sessao)
                st.session_state["influencer_atual"] = None
                st.session_state["elevo_inf_preset_id"] = ""
                st.session_state["elevo_inf_obs"] = ""
                st.success("Influencer removida do seu login. Agora você pode escolher outra ou criar a sua própria.")
                time.sleep(1)
                st.rerun()

    nova_desc_inf = st.text_area(
        "🎨 Descrição visual da personagem (opcional):",
        placeholder="Ex: Mulher brasileira jovem de 24 anos, pele morena iluminada, cabelos cacheados volumosos e brilhantes na altura dos ombros, olhos castanhos expressivos, usando uma camiseta básica branca, expressão de amiga fofoqueira...",
        height=130,
        key="input_desc_inf"
    )
    st.caption("Se você informar apenas o nome, o ÉLÉVO aplica uma descrição-base neutra. Se quiser, descreva a personalidade, emoção, forma de falar e aparência.")
    if st.button("💾 APLICAR E SALVAR INFLUÊNCIA NO MEU LOGIN", type="primary", use_container_width=True, key="btn_salvar_inf"):
        if not novo_nome_inf.strip():
            st.warning("⚠️ Informe um nome. A descrição visual é opcional.")
        else:
            with st.spinner("Gravando a sua Influencer no banco de memória exclusivo do seu login..."):
                desc_personalizada_v164 = (nova_desc_inf.strip() or
                    "Fictional adult Brazilian virtual presenter, natural appearance, realistic skin texture, conversational Brazilian Portuguese voice, expressions and body language adapted to the product without exaggerated acting; maintain consistent identity throughout image and video.")
                if gerenciar_influencer_usuario("salvar", email_sessao, novo_nome_inf, desc_personalizada_v164, logo_ativa_usuario):
                    st.session_state["influencer_atual"] = {
                        "Email": email_sessao,
                        "Nome_Influencer": novo_nome_inf.strip(),
                        "Descricao_Visual": desc_personalizada_v164,
                        "Logo_Marca": logo_ativa_usuario
                    }
                    st.session_state["elevo_inf_preset_id"] = ""
                    st.session_state["elevo_inf_obs"] = obter_observacao_salva_v164(desc_personalizada_v164)
                    st.success(f"🔥 {novo_nome_inf.strip()} foi aplicada ao sistema e vinculada ao seu login!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar no banco de dados. Verifique a conexão com a planilha.")

# ==========================================================
# 17.2. CRIAÇÃO V9.2 (INTERLIGADO AO 17 + CAMPO DE LOGO EXCLUSIVO DA V9.2)
# ==========================================================
btn_gerar_v92 = False
if st.session_state.get("modo_entidade_v9"):
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h3 style='text-align: center; color: #FF0040;'>🧬 17.2. Máquina V9.2 (Imagem Original + Vídeo V12 Hiper-Realista)</h3>", unsafe_allow_html=True)
        st.caption("Conectado à foto, à Influencer e ao Banco 17.3. V12: imagem preservada; vídeo expandido com a estrutura e os emojis originais, física viva e mínimo de 1.500 caracteres visuais.")
        
        if E_O_CEO:
            logo_v92_input = st.text_input(
                "🏷️ Nome da Marca (apenas para SEO) (Padrão CEO 'O Achado Secreto' já ativo — altere apenas se quiser outra):",
                value=logo_ativa_usuario,
                placeholder="O Achado Secreto",
                key="input_logo_v92_ceo"
            )
        else:
            logo_v92_input = st.text_input(
                "🏷️ Digite o Nome da sua Logo / Empresa (para títulos e descrições, sem sobreposição no vídeo):",
                value=logo_salva_banco,
                placeholder="Ex: Minha Marca VIP / Achadinhos da Bia...",
                key="input_logo_v92_user"
            )
        if logo_v92_input and logo_v92_input.strip():
            logo_ativa_usuario = logo_v92_input.strip()
            if inf_salva:
                gerenciar_influencer_usuario("salvar", email_sessao, nome_inf_ativa, desc_inf_ativa, logo_ativa_usuario)

        if not pode_gerar_roteiro:
            st.error("Limite de roteiros atingido ou controle de cotas indisponível. Tente novamente mais tarde se houver erro de conexão.")
            btn_gerar_v92 = st.button("🔥 LER RÓTULO E GERAR NA V9.2", type="primary", use_container_width=True, disabled=True, key="btn_v92_disabled")
        else:
            txt_btn_v92 = f"🔥 LER RÓTULO E GERAR NA V9.2 COM IDENTIDADE '{logo_ativa_usuario}' (Ilimitado)" if E_O_CEO else f"🔥 LER RÓTULO E GERAR NA V9.2 ({3 - usos_feitos} Restantes)"
            btn_gerar_v92 = st.button(txt_btn_v92, type="primary", use_container_width=True, key="btn_v92_ativo")

# ==========================================================
# 17.3. BANCO DE MEMÓRIA E TREINAMENTO INTEGRAL (100% DO DOCUMENTO ENVIADO PELO SÓCIO + LEMA DOR & SOLUÇÃO)
# ==========================================================
PROTOCOLO_FISICO_17 = "[PROTOCOLO FÍSICO REALISTA V10 — PRIORIDADE MÁXIMA; PREVALECE SOBRE MOLDES ANTIGOS]\n- CONSERVAÇÃO: mesmo número de produtos, identidade, altura, largura, volume, tampa, marca e rótulo em TODOS os quadros; não duplicar, fundir, deformar, trocar textura nem desaparecer. O objeto não teletransporta entre mão e bancada.\n- REFERÊNCIA FIXA: a foto fornecida é REFERÊNCIA APENAS DO PRODUTO (não do ambiente). Cor, embalagem, impressão, acabamento e tamanho relativo vêm exclusivamente dela; o cenário vem do AMBIENTE ELEVO ESCOLHIDO ou sorteado. Nunca descreva cor, peso, volume, tampa ou rótulo do produto no prompt visual.\n- CONTATO E GRAVIDADE: produto apoiado na bancada tem base em contato contínuo, sombra de contato consistente, gravidade, inércia e oclusão reais; produto na mão mantém posição estável, dedos anatomicamente corretos, pressão e oclusão coerentes, nenhuma interpenetração ou flutuação.\n- CÂMERA: celular realista, câmera principalmente estável, deslocamentos curtos e suaves; proibir zoom violento, whip-pan, tremor excessivo, troca brusca de foco, glare artificial. Profundidade de campo coerente sem ocultar itens essenciais.\n- PELE E MATERIAIS: poros finos, fios de cabelo individuais, rugosidade realista, leve assimetria; materiais com BRDF plausível, reflexos dependentes da iluminação real, sem brilho plástico ou nitidez falsa. Evitar hiperbolização da pele, do olhar ou da respiração.\n- AMBIENTE: plantas e tecidos se movem apenas se houver vento plausível; vapor e água só onde efetivamente existem na referência; sombras, reflexos, perspectiva, luz e exposição temporalmente contínuos. Incluir a planta, a baguncinha orgânica e o único animal discreto previstos no cenário escolhido, mesmo que a foto enviada exiba somente o produto; não criar objetos extras no VÍDEO que não constem na imagem de cena.\n- FINAL: a partir de 0:08, a apresentadora mantém o produto perfeitamente visível em quadro; no último segundo, segurar imagem estável com produto e ambiente intactos até o último frame. PROIBIDO quadro preto, fade para preto, glitch, logo sobreposto, marca d'água, sacola 3D flutuante ou elementos duplicados. Logo original impressa na embalagem permanece; não acrescentar logo da empresa na imagem.\n- ÁUDIO/COPY: fala factível em 9 segundos (aprox. 18–25 palavras, ajustar à locução), sem afirmar benefícios não demonstrados no rótulo, escassez, preço ou estoque não confirmados. Texto de CTA pode ficar para edição fora do gerador; não gerar UI nativa.\n- Se um molde histórico conflitar com estas regras, este protocolo é soberano."

LISTA_SORTEIO_GANCHOS_CAMPEOES = [
    "GANCHO 01 (O Dedo na Ferida + UTI no Chuveiro): Comece atacando o desespero de ver o cabelo quebrando na escova, elástico de química ou esturricado de chapinha, mostre que o produto reconstrói e desmaia o fio na primeira aplicação no próprio chuveiro e feche com o lote secreto vazando na sacolinha.",
    "GANCHO 02 (O Segredo que as Donas de Salão Escondem): 'Amiga, o que as donas de salão não te contam é que você não precisa gastar duzentos reais para ter cabelo espelhado...' Mostre a transformação sensorial imediata e a urgência do estoque acabando.",
    "GANCHO 03 (O Alerta da Amiga Preocupada): 'Amiga, para tudo... você tem noção do que o calor do secador e a química estão fazendo com o seu fio todo dia?' Entregue o alívio imediato que sela as pontas e blinda o cabelo.",
    "GANCHO 04 (O Erro no Sistema / Lote Promocional Vazado): 'Gente, o pessoal do estoque enlouqueceu e liberou o lote secreto desse tratamento completo por um valor que é piada!' Foque na dor resolvida na hora e mande correr na sacolinha.",
    "GANCHO 05 (A Confissão / Cabelo Fino, Ralo e Sem Vida): 'Se o seu cabelo tá fino, ralo, poroso e sem balanço nenhum, para de jogar dinheiro fora com creme ralo!' Mostre como ele preenche a fibra e encorpa o fio na hora.",
    "GANCHO 06 (O Confronto Direto de Amiga): 'Ainda passando raiva com cacho armado, ressecado ou passando vergonha? Acorda, amiga!' Entregue a sensação de luxo, maciez e solução definitiva."
]


# ==========================================================
# ÉLÉVO V11 — MOTOR DE FÍSICA TEMPORAL E CONTINUIDADE 360º + V9.2
# Mantém o tema, login, scanner, banco de imagens e acesso Google Sheets.
# Não há limite superior de caracteres imposto ao vídeo; 1.500 é o mínimo.
# ==========================================================
MIN_CARACTERES_PROMPT_VIDEO = 1500

# Cada criação escolhe uma locação nova entre 20 famílias e várias microvariações.
# Nada é introduzido no vídeo se não tiver aparecido no PROMPT DE IMAGEM.
CENARIOS_V11 = [
    ("Banheiro brasileiro com janela", "diffused daylight, gentle steam only if a hot shower is visible, soft towel movement from a real draft", "sem animal"),
    ("Varanda tropical", "light wind moving fern tips and large leaves with delayed return, changing sun flecks", "pássaro distante, opcional"),
    ("Penteadeira ao fim de tarde", "warm sideways window light, mirror reflections, individual hair strands responding subtly to motion", "sem animal"),
    ("Área de serviço", "cotton cloth and drying garments swaying gently if a breeze enters, steady floor shadows", "sem animal"),
    ("Jardim doméstico", "small branches flexing naturally and independent foliage motion under mild gusts", "borboleta distante, opcional"),
    ("Pedras junto de uma cachoeira", "continuous running water with nonrepeating spray, wet rock reflections, drifting mist", "sem animal"),
    ("Cozinha brasileira vivida", "low steam drifting from an existing cup, daylight variations and physically correct glass reflections", "sem animal"),
    ("Quarto comum à noite", "gentle illumination variations only if a television is visible, duvet and hair moving with body movement", "sem animal"),
    ("Quintal de terra", "ground-level wind stirring dry leaves, gentle plant movement and coherent midday shadow", "cão ao fundo, opcional"),
    ("Deck de piscina", "nonrepeating water ripples, realistic caustics, light breeze in plants and clothing", "sem animal"),
    ("Estufa caseira", "subtle leaf flex and believable humidity, fine condensation limited to cold surfaces", "sem animal"),
    ("Varanda com chuva", "rain driven by consistent wind, accumulating droplets, wet surfaces, realistic leaf inertia", "ave abrigada, opcional"),
    ("Sala de estar noturna", "small practical lamp reflections, believable fabric friction and soft movement of curtains", "gato dormindo, opcional"),
    ("Banheira vintage", "subtle water surface oscillation where present and plausible porcelain highlights", "sem animal"),
    ("Varanda de praia", "sea breeze affecting loose strands and foliage with varied speeds, soft warm reflections", "sem animal"),
    ("Home office brasileiro moderno", "window light with soft monitor glow, leaf movement only near airflow, natural desk surface texture", "sem animal"),
    ("Deck de barco no rio", "small vessel sway and matching horizon movement, ripples with believable inertia", "ave distante, opcional"),
    ("Canto de leitura", "soft natural window light, pages only shift with a real breeze or touch", "sem animal"),
    ("Lavabo de textura elegante", "subtle mirror and glass reflections, natural water drops only near an existing faucet", "sem animal"),
    ("Calçada urbana brasileira", "passing wind moving loose fabric and tree leaves, realistic light and distant pedestrian parallax", "sem animal")
]
VARIACOES_LUZ_V11 = [
    "soft early-morning ambient light", "natural late-afternoon directional sunlight",
    "overcast diffused daylight", "warm interior practical lights balanced with window daylight",
    "neutral midday daylight", "gentle dusk mixed-light conditions"
]
GESTOS_V11 = [
    "one restrained fingertip tap on the lid with accurate contact and a slight reaction",
    "a gentle quarter-turn of the supported product with believable wrist inertia",
    "small natural adjustment of the hand grip without changing packaging orientation",
    "a brief natural glance from product to lens and back, with subtle breathing",
    "one gentle touch of the container surface, without opening or moving any lid",
    "a short, careful reframe to include the presenter's face while retaining all units"
]


def montar_lock_ambiente_v165(chave, observacao=''):
    """Fixed environment template in English; images and video inherit the same objects."""
    cena = AMBIENTES_ELEVO_V165.get(str(chave))
    if not cena or str(chave) == 'infinito':
        return ''
    ajuste = str(observacao or '').strip()[:650]
    base_cena = (
        f"ENVIRONMENT ID [{chave}]: {cena['nome']}. "
        f"EXACT SET / OBJECTS: {cena['elementos']}. "
        f"SOURCE LIGHT: {cena['luz']}. "
        f"PHYSICAL DYNAMICS: {cena['fisica']}. "
        f"LOCATION SOUND: {cena['som']}. "
        f"ANIMAL POLICY: {cena['animal']}. "
    )
    if ajuste:
        base_cena += f"USER-REQUESTED ADDITIONAL SET DETAIL: {ajuste}. "
    return base_cena + (
        'ENVIRONMENT LOCK: keep exactly this location, geometry, surfaces, object inventory, '
        'weather, directional light, background continuity and natural sound from the GENERATED environment still '
        'through every video frame. Include each detail in the IMAGE and copy it verbatim into '
        'the VIDEO before describing dynamics. The product photograph is only the PRODUCT reference, '
        'not the background. Keep the selected setting plant, natural lived-in clutter and one background animal; '
        'do not add a second pet or weather not supported by this setting. Microphysics must obey gravity, '
        'contact, friction, airflow and realistic smartphone optics. Avoid impossible particle or motion effects.'
    )


def fixar_ambiente_ambos_prompts_v165(conteudo, chave, observacao=''):
    """Deterministic environment header in both outputs after V12 video refinement."""
    lock = montar_lock_ambiente_v165(chave, observacao)
    if not lock:
        return conteudo
    marcador = f'[ÉLÉVO ENVIRONMENT LOCK — {chave.upper()}]'
    cabecalho = f'{marcador} {lock}\n'
    regex_imagem = r'(?im)^(###\s*📸\s*PROMPT DE IMAGEM[^\n]*\n)'
    regex_video = r'(?im)^(###\s*🎬\s*PROMPT DE VÍDEO[^\n]*\n)'
    out, n_img = re.subn(regex_imagem, lambda m: m.group(1) + cabecalho, conteudo, count=1)
    out, n_vid = re.subn(regex_video, lambda m: m.group(1) + cabecalho, out, count=1)
    if n_img != 1 or n_vid != 1:
        raise ValueError('Formato inesperado dos prompts; cenário não foi confirmado nos dois blocos.')
    return out


def selecionar_direcao_fisica_v11(email_usuario, modo):
    """Evita repetições imediatas de cenário, gancho e animal dentro da sessão."""
    escolhido = str(st.session_state.get('elevo_ambiente_id', '')).strip()
    if escolhido == 'infinito':
        # Um sorteio real por geração. O MESMO ID será usado para imagem e vídeo.
        ids_cenas = [k for k in AMBIENTES_ELEVO_V165 if k != 'infinito']
        historico = st.session_state.setdefault('elevo_ambiente_historico_infinito', [])
        disponiveis = [k for k in ids_cenas if k not in historico[-7:]]
        sorteado = random.choice(disponiveis or ids_cenas)
        st.session_state['elevo_ambiente_ultimo_infinito'] = sorteado
        historico.append(sorteado)
        st.session_state['elevo_ambiente_historico_infinito'] = historico[-20:]
        cena = AMBIENTES_ELEVO_V165[sorteado]
        variacoes = [
            'Use gentle handheld framing and subtle human timing imperfections.',
            'Maintain realistic light falloff and micro-texture on surfaces without decorative digital filters.',
            'Capture small natural ambient movements, preserving the exact prop positions.',
            'Prioritize grounded material response, subtle contact shadows and natural camera focus settling.',
        ]
        modificador = random.choice(variacoes)
        trava = montar_lock_ambiente_v165(sorteado, st.session_state.get('elevo_ambiente_obs',''))
        return {
            'cenario': cena['nome'], 'fisica_ambiente': cena['fisica'],
            'animal': cena['animal'], 'luz': cena['luz'],
            'gesto': random.choice(GESTOS_V11), 'modo': modo,
            'escolhido': sorteado, 'trava_ambiente': trava + ' VARIATION: ' + modificador,
        }
    if escolhido in AMBIENTES_ELEVO_V165:
        cena = AMBIENTES_ELEVO_V165[escolhido]
        return {
            'cenario': cena['nome'],
            'fisica_ambiente': cena['fisica'],
            'animal': cena['animal'],
            'luz': cena['luz'],
            'gesto': random.choice(GESTOS_V11),
            'modo': modo,
            'escolhido': escolhido,
            'trava_ambiente': montar_lock_ambiente_v165(escolhido, st.session_state.get('elevo_ambiente_obs','')),
        }
    # Sorteio padrão também respeita os 20 cenários oficiais enriquecidos.
    historico = st.session_state.setdefault("historico_v11_cenas", [])
    ids = [k for k in AMBIENTES_ELEVO_V165 if k != 'infinito']
    disponiveis = [k for k in ids if k not in historico[-8:]]
    chave = random.choice(disponiveis or ids)
    historico.append(chave)
    st.session_state["historico_v11_cenas"] = historico[-20:]
    cena = AMBIENTES_ELEVO_V165[chave]
    return {
        "cenario": cena['nome'], "fisica_ambiente": cena['fisica'],
        "animal": cena['animal'], "luz": cena['luz'],
        "gesto": random.choice(GESTOS_V11), "modo": modo,
        "escolhido": chave,
        "trava_ambiente": montar_lock_ambiente_v165(chave, ''),
    }


def selecionar_gancho_v11():
    """Não fixa ganchos a cosméticos: sorteia ângulos e pede adaptação ao produto real."""
    banco = [
        "pergunta específica sobre um incômodo verificável do consumidor",
        "pequena confissão pessoal sobre o uso cotidiano",
        "comparação honesta com uma dificuldade da rotina, sem atacar concorrentes",
        "demonstração sensorial concreta de uma característica comprovada",
        "dica de uso que resolve um problema prático",
        "descoberta espontânea de um detalhe da embalagem",
        "alerta útil sobre um erro comum de uso, se houver evidência",
        "curiosidade em formato de segredo sem inventar fatos",
        "micro-história de uma situação reconhecível pelo público",
        "pergunta surpresa seguida por observação visual do produto",
        "abordagem leve e divertida sobre o benefício verificável",
        "antes-e-depois apenas verbal e sem resultados fictícios"
    ]
    anteriores = st.session_state.setdefault("historico_v11_ganchos", [])
    candidatos = [g for g in banco if g not in anteriores[-5:]]
    escolhido = random.choice(candidatos or banco)
    anteriores.append(escolhido)
    st.session_state["historico_v11_ganchos"] = anteriores[-12:]
    return escolhido


# ==========================================================
# ÉLÉVO V12.0 — MÓDULO EXCLUSIVO DO VÍDEO
# IMPORTANTE: Este módulo NÃO altera o PROMPT DE IMAGEM ou o SEO.
# A primeira chamada preserva os moldes originais V8.1/V9.2.
# A segunda chamada amplia SOMENTE a seção 🎬, preservando emojis e etapas.
# ==========================================================
MIN_CARACTERES_DIRECAO_VISUAL_V12 = 1500

DIRETRIZ_VIDEO_V12 = """
[ÉLÉVO V12 — IMMERSIVE PHYSICAL VIDEO DIRECTION / STRONG DOCUMENTARY UGC]
Do not tame the original viral energy. The shot must feel alive, spontaneous and expressive: camera operated by a real person, a compelling hook, naturally motivated micro-hesitations, a vivid performance and environmental motion that reacts to a cause. Avoid robotic motion and showroom stillness. Use real-world mass, gravity, inertia, skin, material and optical behavior rather than impossible 3D motion graphics.

ONE SCENE — ONE SOURCE OF TRUTH: The exact PROMPT DE IMAGEM is the binding generated scene specification; the uploaded photograph governs ONLY the product appearance, never the room. Repeat its precise location, layout, weather, plants, natural textures, table or counter, lighting direction, wardrobe, presenter, props, animals if any, and reference product identity. Never swap to an alternative V11 background or introduce any extra animal, wetness, steam, objects or trees absent from that generated scene blueprint. Its packaging is authoritative; preserve label text and item count across time.

0:00–0:03 / SHOT 1 — Intense but plausible product-first hook. A realistic smartphone, naturally held by someone alive, slightly searches for focus, adjusts exposure and changes framing only as far as the product and all kit units can remain visible. Capture parallax, mild rolling-shutter response during physically plausible movement, low-level phone sensor grain and authentic optical depth. Fingertip touches respect solid geometry, skin compression, friction and correct finger count. Realistic product weight and stable center of gravity; tiny palm counter-adjustments rather than floating packages. No label morphing or oversized jars.

0:03–0:06 / SHOT 2 — Energetic camera and facial storytelling. A fast-but-recoverable handheld reframing or tiny pan may emphasize the presenter's reaction WITHOUT hiding, replacing, shrinking or teleporting any item from a multi-unit kit. Expressive eyes, spontaneous smile, subtle blinking, jaw and mouth synced to the voice, small breath-driven shoulder movement, real hair inertia and slightly delayed strand settling. Skin contains pores, fine facial hairs, soft self-shadowing, believable sweat only if supported by the existing climate. Microphone, garment seams and fabric creases maintain geometry.

0:06–0:08 / INTERACTION — One distinct physically causal interaction: fingertip tap, careful twist, grip adjustment or gesture toward the lower edge. When a finger strikes a cap, the product shows minimal inertia and recovers through the supporting hand or table friction. When fabric moves, it hangs and returns with its real weight. Keep the presenter and all reference units in the shot; the person's hands never pass through a jar or change the number of items. CTA icons and captions are EDITING NOTES, not invented 3D objects in the raw footage.

0:08–0:10 / FINAL — Stay in the same live scene, all original units present and recognizable, no product vanish, no black tail, no glitch card, no duplicate logo, no watermark or digital floating cart. The camera settles naturally without becoming frozen. Leaves, curtains, water, ambient shadows and small human motions continue to behave causally until the very last frame.

WORLD PHYSICS — VARIATIONS ONLY WHEN PRESENT: On windy balconies, fronds flex at different frequencies, tiny leaves lead larger leaves, branches bend then lag in recovery, hair strands and loose hems respond to the same wind vector. In heavy rain, distinguish droplets outside glass from water indoors: drops impact panes, coalesce, slide under gravity, leave trails, and create irregular reflections; never make a dry interior inexplicably wet. In a humid bathroom, steam forms soft slow convection from an existing heat source, subtly scattering the existing warm practical light, not fogging over product labels. Near waterfalls, water courses downhill continuously, small cascades create irregular ripples and mist; butterflies or birds appear only when in the image and never loop identical movement. Any animal already pictured may blink, breathe, reposition an ear, or shift its weight with nonrepeating natural motion; the next creation may have a different species or no animal. Preserve coherent reflections and cast/contact shadows while subjects move. Respond to actual wind, gravity and impulses; do not animate background objects at random.

NO FAKE REALISM: no extreme zoom jumps, sudden background swap, invented plants, extra pets, duplicate products, melting letters, distorted labels, unnatural giant pupils, gratuitous glowing skin, airbrushed plastic, fake CGI rain or omnipresent heavy grain. The raw frame contains no platform UI. Keep a lively original sales-style hook and the prior audio/CTA text headings, but never invent unsupported stock, discounts, or guaranteed outcomes.
""".strip()


def _extrair_ambiente_da_imagem_v12(prompt_imagem):
    """Infer scene-specific physical causes only from text already present in the image prompt."""
    texto = str(prompt_imagem or '').lower()
    pares = [
        (('rain','chuva','storm','tempest','raindrop'), '🌧️ Rain outside/where physically described: irregular impacts, droplet coalescence, gravity-driven streaks, wind-consistent trajectories, wet reflections only on preexisting wet surfaces.'),
        (('steam','vapor','humid','fogged glass'), '♨️ Steam from an existing warm-water source: slow convection, uneven density, realistic scatter, no obscured label.'),
        (('fern','foliage','leaf','leaves','plant','monstera','palm','samambaia','garden','nature','greenery'), '🌿 Visible vegetation: asynchronous small movements reacting to the same plausible breeze, leaf bending, inertia, delayed recovery, no synchronized loops.'),
        (('waterfall','river','pool','puddle','fountain','cachoeira','stream'), '💧 Visible water: continuous surface transport, gravity, naturally irregular ripples, water reflections coherent with the existing light source.'),
        (('dog','cat','animal','bird','butterfly','cachorro','gato'), '🐾 Animal ONLY if already present: small unrepeated breathing, blinking, ear and weight shifts appropriate to the original species, no duplicates.'),
        (('curtain','linen','towel','fabric','cotton','shirt','clothes','roupa','toalha'), '🧵 Fabric: weight, crease preservation, contact friction and delayed settling after touch or existing airflow.'),
        (('tv','television','monitor','screen','led','luminária','lamp'), '💡 Practical lights already described: subtle temporal brightness variation, coherent falloff and reflections without changing the original color palette.'),
    ]
    ativos=[desc for terms,desc in pares if any(term in texto for term in terms)]
    if not ativos:
        ativos=['🌬️ Subtle movement only in existing materials when caused by human action or physically plausible airflow; maintain original static geometry.']
    return '\n'.join(ativos)


def _direcao_visual_caracteres_v12(video):
    """Count visual instruction before 🎙️/🔊 audio, not marketing copy or titles."""
    return len(re.split(r'(?=🎙️|🔊|Áudio \(Gancho|Áudio e Fala)',video,maxsplit=1)[0].strip())


def _trocar_so_video_v12(conteudo, novo_video):
    pattern=r'(###\s*🎬\s*PROMPT DE VÍDEO[^\n]*\n)(.*?)(?=###\s*🔑|\Z)'
    saida,n=re.subn(pattern,lambda m:m.group(1)+novo_video.strip()+'\n\n',conteudo,count=1,flags=re.S|re.I)
    if n!=1:
        raise ValueError('Não foi possível localizar o bloco de vídeo sem afetar imagem/SEO.')
    return saida


def _fallback_video_v12(video_original, scan, ambiente, modo):
    """Video-only fallback: preserves original audio/CTAs and inserts visual physics BEFORE them."""
    qtd=max(1,int(scan.get('qtd',1)))
    pedacos=re.split(r'(?=🎙️|🔊|Áudio \(Gancho|Áudio e Fala)',video_original,maxsplit=1)
    visual=pedacos[0].strip()
    audio=pedacos[1].strip() if len(pedacos)>1 else ''
    # Older templates requested a floating orange 3D bag. Raw natural footage should only
    # contain real human gesture; preserve the Interaction heading and the original marketing text.
    visual=re.sub(r'(?im)(Interaction \(3D CTA\):)\s*.*?(?=\n\[PRISTINE CANVAS LOCK|\n🎙️|\Z)',
                  'Interaction (3D CTA): [A physically believable hand points naturally toward the lower frame; add CTA graphics only later in editing, not inside the raw scene.]',
                  visual, count=1, flags=re.S)
    if not visual.startswith('🎬'):
        visual='🎬 Shot 1 (Natural Hook & Physics):\n'+visual
    visual=re.sub(r'(?m)^(Shot 2\s*\()',r'🎥 \1',visual)
    visual=re.sub(r'(?m)^(Interaction\s*\()',r'🫱 \1',visual)
    if '[PRISTINE CANVAS LOCK' in visual and '🛡️' not in visual:
        visual=visual.replace('[PRISTINE CANVAS LOCK','🛡️ [PRISTINE CANVAS LOCK',1)
    enriquecimento=(
        '\n\n🌪️ [PHYSICAL DIRECTION — REAL LIFE UGC / VISUAL ENGLISH]\n'
        f'[INVENTORY LOCK — {qtd} ITEMS, EVERY FRAME] {scan.get("regra_pos_vid", "")} '
        'Every item retains the same body, cap, label, physical size and identity at 0:00, 0:05 and the final frame. '
        'If there are two or three original products, ONE remains supported in the hand and ALL other original units stay supported on their original table spots and visible. '
        'No offscreen swap, no merging, no resizing, no vanishing package and no duplicated graphic.\n'
        '[CAMERA / LIGHT] Real moving phone operated by a person: lively but plausible reframe, short focus acquisition, low-level sensor grain, realistic focal behavior, natural exposure response, believable parallax and rolling-shutter response only when the phone actually moves. '
        'The product never jumps between positions, light direction and shadow softness evolve continuously, and glass/plastic reflections move according to the existing light and camera viewpoint.\n'
        '[HAND / MASS / GEOMETRY] Human fingers grasp the existing rigid object with realistic opposition of thumb and other fingers, changing skin compression where contact pressure is applied; the center of mass remains supported. '
        'A fingertip tap transfers a tiny impulse to the package, counteracted by table friction or the presenter’s stabilizing hand. No merged skin, impossible joints, floating containers, disappearing lids or melting label typography. '
        'Static units have full base-to-counter contact, with cast and contact shadows consistent with their distance from the surface.\n'
        '[WORLD REACTIONS] '+ambiente.replace('\n',' ')+'\n'
        '[REAL HUMAN PERFORMANCE] Immediate hook with expressive but believable microexpressions, asymmetric blinking, small smile changes, throat and mouth motion aligned with Portuguese speech, breath-driven shoulder and chest movement, hairs lagging slightly behind the head turn, fabric maintaining gravity and crease continuity. '
        'No rigid mannequin pose. Keep the microphone, hairstyle and outfit unchanged. The environment remains alive in the background and nothing repeats as a mechanical loop.\n'
        '[FINAL FRAME / OPEN EDIT] Maintain the entire original scene and all source products until the last frame. '
        'Camera drifts naturally to a readable composition, while physical background motion carries on. '
        'No fade to black, invented logo, digital glitch, floating shopping bag, platform UI, fake on-screen captions or sudden room change.\n'
    )
    if not audio:
        audio='🎙️ Áudio e Fala (Português): [Preserve the original voiceover and natural ambient sound.]'
    if '📝' not in audio:
        audio+='\n📝 Texto na Tela (sugestão para edição): ⚠️ Dor real? 🛑  ✨ Solução verificável  🛒 Conheça na sacolinha 👇'
    return visual+enriquecimento+'\n'+audio


# ==========================================================
# ÉLÉVO V14 — MICROFÍSICA DO ECOSSISTEMA VIVO (SÓ NO VÍDEO)
# A IMAGEM, SEO, LOGIN, DESIGN, TABELAS E DEMAIS BLOCOS SÃO IMUTÁVEIS.
# O mapa físico abaixo deriva EXCLUSIVAMENTE do prompt de imagem aprovado.
# ==========================================================

def _evidencias_de_cena_v14(prompt_imagem):
    """Lê a descrição existente; não solicita objetos nem novo cenário."""
    original = str(prompt_imagem or '').strip()
    t = original.lower()

    def tem(*palavras):
        return any(re.search(r'(?<!\w)' + re.escape(p) + r'(?!\w)', t) for p in palavras)

    def proximidade(grupo_a, grupo_b, largura=160):
        """Evita inventar toalha molhada porque há chuva do outro lado da janela."""
        for a in grupo_a:
            for m in re.finditer(re.escape(a), t):
                janela = t[max(0, m.start()-largura):min(len(t), m.end()+largura)]
                if any(b in janela for b in grupo_b):
                    return True
        return False

    presentes = []
    if tem('rain', 'raining', 'rainstorm', 'storm', 'stormy', 'chuva', 'tempestade', 'downpour', 'raindrops'):
        presentes.append(('CHUVA', 'Real droplets fall in nonrepeating irregular trajectories consistent with the weather and wind. Where a window is explicitly present, outside droplets impact its OUTER face, merge into heavier beads, slide down under gravity leaving transparent trails and distorting the daylight. Do not soak interior surfaces unless they were already wet in the approved still image. Existing wet surfaces display correlated highlights and tiny runoff only at believable slopes.'))
    if tem('steam', 'vapor', 'humid', 'steamy', 'mist', 'fog', 'embaçado', 'neblina'):
        presentes.append(('VAPOR / UMIDADE', 'From the existing humid or hot-water source, uneven warm air rises by slow convection; wisps expand, curl and dissipate rather than looping identically. It may lightly soften the far edge of the frame and scatter the already-existing light, but never covers the package label or changes wall texture. No new shower, smoke machine or extra water source.'))
    if tem('ferns','fern','samambaia','samambaias','monstera','plant','plants','foliage','leaf','leaves','folhas','garden','greenery','palm','palm tree','coqueiro','jardim','vegetation','costela-de-adão'):
        presentes.append(('PLANTAS / VENTO', 'Animate only plants visible in the image: tiny leaves begin to deflect before the larger fronds, thin stems flex, broad leaves bend later and return with delayed inertia. The motion is asynchronous across leaves yet obeys ONE common, plausible airflow direction. If indoors and no draft is visible, use extremely restrained leaf-tip movement or keep leaves still; never introduce a fan or a gust for spectacle. Natural dappled-shadow movement is synchronized with the actual moving leaves, not arbitrary screen flicker.'))
    if tem('waterfall','river','pool','fountain','stream','lake','cachoeira','riacho','piscina','água corrente','water surface'):
        presentes.append(('ÁGUA VISÍVEL', 'Existing water flows downhill or ripples in its real container, with varying surface normals, irregular reflections and physically plausible contact with rocks, basin or pool edges. Splashes and mist arise only from pictured impacts. Never create a new river, stream or falling water.'))
    tecido = tem('towel','linen','cloth','fabric','curtain','shirt','clothes','sleeve','garment','toalha','tecido','cortina','roupa','tricot','crochet','crochê','lençol','t-shirt')
    if tecido:
        dica = ('A clearly wet or soaked fabric carries additional water mass and sags; individual drops form at the LOWEST existing edge before detaching, falling vertically and making a brief tiny splash ONLY on the surface directly below.' if proximidade(['towel','toalha','cloth','linen','fabric','tecido'],['soaked','drenched','dripping','wet','molhada','encharcada','pingando','úmida','damp'], 75) else 'Do not make a dry towel suddenly drip: if the approved still merely shows a towel, preserve its dry state and folds.')
        presentes.append(('TOALHAS / TECIDOS', 'Existing fabric has gravity, thickness, weave, wrinkles and friction with its support. It settles after touch or flexes with the same airflow moving the plants; wet and dry regions retain their actual depicted appearance. '+dica))
    if tem('dog','dogs','cat','cats','bird','birds','butterfly','butterflies','animal','cachorro','cão','gato','passarinho','borboleta'):
        # Never prescribe another species: match the individual already in this image.
        if tem('dog','dogs','cachorro','cão'): especie='The dog may breathe with slight torso movement, blink, shift one ear or twitch a paw once, without repeatedly performing the same trick.'
        elif tem('cat','cats','gato'): especie='The cat may blink slowly, shift an ear or tail tip and breathe at a natural rhythm, never looping identical motions.'
        elif tem('bird','birds','passarinho'): especie='The bird may make a small weight shift, turn its head or shake wet feathers only if feathers are pictured as wet.'
        else: especie='Only the pictured animal/insect can perform a species-appropriate subtle nonrepeating motion, never a repeated stock animation.'
        presentes.append(('ANIMAL JÁ PRESENTE', especie+' Exact same species, size, fur/feather pattern and position from original frame, no new animals and no focus stealing from the product.'))
    if tem('tv','television','monitor','screen','led','lamp','desk lamp','luminária','abajur','tela','televisão'):
        presentes.append(('LUZ PRÁTICA', 'Any existing television/monitor or lamp may cause subtle REAL bounced-light fluctuations only if its pictured state motivates that change. Nearby objects and product reflect the same light change with consistent distance falloff; no strobe, random rainbow glow, or color palette change.'))
    if tem('mug','cup','coffee','coffee mug','caneca','café','glass','water glass','copo','ceramic','cerâmica','dish','prato','pratinho','bowl','caderno','notebook','paper','papel','book','livro','phone','charger','mouse','mesa','desk','counter','balcão','bancada','shelf','prateleira'):
        presentes.append(('BAGUNCINHA ORGÂNICA EXISTENTE', 'Preserve the EXACT original collection of everyday objects at their depicted coordinates: cup/mug, towel, book, charger, dish, bottle, tool or any other item ONLY IF the approved image contains it. Objects have mass, surface contact and occlusion and must NOT slide, multiply or vanish by themselves. A pictured cup may show a tiny reflection change as the hand-held camera moves; steam only if already present, pages flex only from genuine contact or an existing breeze, and each counter object keeps its own contact shadow.'))
    if not presentes:
        presentes.append(('MICRODINÂMICA DISCRETA', 'This exact still image has no explicit dynamic weather or props. Keep geometry fixed and create physical life only through subtle breathing, grip pressure, natural camera parallax and light response; do NOT add rain, animals, plants or clutter.'))
    return presentes


def _blocos_originais_da_cena_v14(prompt_imagem):
    """Extract dense labeled details (when present) without any replacement."""
    imagem=str(prompt_imagem or '').strip()
    blocos=[]
    etiquetas=(('NATURE MATRIX','🌿 NATURE MATRIX'),('BAGUNCINHA','🧺 BAGUNCINHA TEMÁTICA'),('ANIMAL FACTOR','🐾 ANIMAL FACTOR'),('ENVIRONMENT REINFORCEMENT','🏠 AMBIENTE ORIGINAL'),('DECORAÇÃO','🪴 DECORAÇÃO'))
    for pref, rotulo in etiquetas:
        p=re.compile(r'\['+re.escape(pref)+r'[^\]]*\]\s*:?',re.I)
        m=p.search(imagem)
        if not m: continue
        apos=imagem[m.end():]
        parada=re.search(r'\s*\[[A-Z][A-Z0-9 _&/()\-:.,+]{5,}\]',apos)
        segmento=(apos[:parada.start()] if parada else apos).strip(' \n.[]')
        if segmento and segmento not in ('...',):
            blocos.append(f'{rotulo}: {segmento[:950]}')
    return blocos


def _reforco_ecossistema_v14(imagem, scan, modo):
    """Deterministic injection into VIDEO only, honoring picture inventory and timeline."""
    imagem=str(imagem or '').strip()
    mapa=_evidencias_de_cena_v14(imagem)
    partes=_blocos_originais_da_cena_v14(imagem)
    qtd=max(1, int(scan.get('qtd',1)))
    lista='\n'.join(f'• [{rotulo}] {regra}' for rotulo,regra in mapa)
    imagem_dense=(imagem[:7000] if imagem else 'Scene source unavailable — do not invent scenery.')
    secoes='\n'.join(partes) if partes else '(The approved image blueprint below is binding; do not add unsupported props.)'
    return (
        '\n\n🌍 [ÉLÉVO V14 — ENVIRONMENT REINFORCEMENT LOCK DENSE / REACTIVE BAGUNCINHA]\n'
        'SOURCE OF TRUTH: This paragraph is VIDEO DIRECTION ONLY, not a request to change the still image. '
        'Reconstruct the exact original room, location, light sources, weather, landscaping, prop placement, fabric, animal if present, and product arrangement from the original photograph. '
        'The scene must be lived-in, not a sterile studio, yet never add a second cup, pet, puddle, window, plant or towel absent from the approved still. '
        'The everyday clutter is a PHYSICAL INVENTORY: every original item stays where it belongs and reacts only to real causes.\n'
        '[VERBATIM APPROVED IMAGE BLUEPRINT — COPY TO VIDEO AS SCENE CONSTRAINT, DO NOT GENERATE A NEW IMAGE]\n'
        f'{imagem_dense}\n'
        '[EXACT LABELED DETAILS PRESENT IN THIS IMAGE]\n'+secoes+'\n'
        '[ENVIRONMENTAL PHYSICS — ACTIVE ONLY FOR ELEMENTS ABOVE]\n'+lista+'\n'
        '🌪️ [REACTIVE BACKGROUND CAUSALITY — CONTINUOUS NOT LOOPED]\n'
        'At 00:00–00:03, natural micro-events begin independently behind the product: any pictured breeze moves existing leaf tips and loose fibers first; rain already outside strikes its original glass/ground; preexisting steam rises from its actual source; existing pets breathe, blink or change one ear position. '
        'At 00:03–00:06, as the camera re-frames toward the presenter, original small props produce real optical parallax without physical teleportation. The same wind vector acts on visible hair, fabric and foliage with different lag times; the light glints advance over the actual rigid package in sync with the camera path. '
        'At 00:06–00:08, one purposeful hand interaction creates a touch and counter-reaction: friction, wrist stabilization, pressure marks, a tiny object impulse; background motion proceeds independently while the package and all original props remain spatially stable. '
        'At 00:08–00:10, keep the world active until the final video frame: water/steam/leaves/animal IF PRESENT have natural non-repeated motion; no freeze, black screen, disappearance, glitch, new CTA object or additional logo. '
        'One source must explain each visible movement. Do not synchronize all plants, animate uncaused dry towels dripping, or transform reflections into magic lights.\n'
        '📦 [EXACT PRODUCT INVENTORY / NO TELEPORT]\n'
        f'Precisely {qtd} original referenced product unit(s), matching distinct printed packaging and scale. '+(
            f'Keep ONE supported in the presenter’s hand only if its real dimensions allow it; otherwise on a safe surface, and each of the other {qtd-1} supported at its exact image location for the whole 0:00–0:10; frame wide enough that ALL {qtd} remain recognizable in the opening, reaction and final shot. '
            if qtd>1 else 'Keep the SAME single original item supported by hand or the ORIGINAL pictured surface throughout, with no spontaneous second unit. '
        )+
        'Accurate individual hard-body geometry, identical cap shape, legible unchanged label, gravity, table contact shadows, skin compression and consistent reflections at every timestamp. The closing frame still shows every unit fully intact.\n'
        '🎥 [REAL PHONE / NATURAL DOCUMENTARY PERCEPTION]\n'
        'Energy is allowed: purposeful tiny camera drift, responsive focus acquisition with occasional quick correction, subtle exposure adaptation and limited rolling-shutter skew during actual movement. No endless artificial shaking, focus jumps that erase products, waxy faces, exaggerated giant pupils, CGI glow, or fake repeating rain simulation. Keep the same approved lighting color, texture and clothing. '
        'Preserve the original 🎬 shots, 🎙️ speech, 📝 CTA suggestions, ⚠️ ✨ 🛒 emojis and SEO outside the video untouched.\n'
    )


def _injetar_ecossistema_v14(video, imagem, scan, modo):
    """Guaranteed scene-specific directions even when the LLM shortens its answer."""
    if '[ÉLÉVO V14 — ENVIRONMENT REINFORCEMENT LOCK DENSE' in video:
        return video
    pedacos=re.split(r'(?=🎙️|🔊|Áudio \(Gancho|Áudio e Fala)', video, maxsplit=1)
    visual=pedacos[0].rstrip()
    resto=pedacos[1] if len(pedacos)>1 else ''
    return (visual+_reforco_ecossistema_v14(imagem,scan,modo)+'\n'+resto).rstrip()

def reforcar_apenas_video_v12(conteudo, scan, modo):
    """Second IA pass rewrites ONLY the video and leaves image/SEO byte-identical."""
    partes=extrair_blocos_roteiro(conteudo)
    if not partes['prompt_imagem'] or not partes['prompt_video']:
        raise ValueError('A IA não retornou IMAGEM ou VÍDEO com os títulos esperados.')
    imagem=partes['prompt_imagem']
    video_original=partes['prompt_video']
    ambiente=_extrair_ambiente_da_imagem_v12(imagem)
    qtd=max(1,int(scan.get('qtd',1)))
    esquema_360="""🎬 Shot 1 (Natural Hook & Physics): [english, detailed]
🎥 Shot 2 (Camera, Visceral Emotion & Scene Continuity): [english, detailed]
🫱 Interaction (Physical CTA Gesture): [english, detailed]
🛡️ [PRISTINE CANVAS LOCK — ZERO WATERMARKS]: [english, detailed]
🎙️ Áudio e Fala (Português): [sound / complete spoken line, preserve strategy]
📝 Texto na Tela (Nativo TikTok - Foco na Dor): ⚠️ ... 🛑 / ✨ ... / 🛒 ... 👇 (editing suggestions only; no overlays in raw video)"""
    esquema_v92="""🎬 Comando Visual (V9.2 — Direção Nervosa, Física Real e Ambiente Vivo): [english, detailed with Shot 1 + Shot 2 timeline]
🫱 Interaction (Gesto Físico / CTA): [english, detailed]
🛡️ [PRISTINE CANVAS LOCK — ZERO WATERMARKS]: [english, detailed]
🎙️ Áudio (Gancho V9.2 — Português): [sound + spoken line in pt-BR]
📝 Texto na Tela (Nativo TikTok - Foco na Dor): ⚠️ ... 🛑 / ✨ ... / 🛒 ... 👇 (notes for editing, not rendered UI)
🎞️ Finalização P1 Blindada: [continuous authentic final image, product visible; no black screen or duplicate logo]"""
    modelo_saida=esquema_v92 if modo=='v9.2' else esquema_360
    instrucao=(
        'TAREFA: Reescreva e amplie EXCLUSIVAMENTE o PROMPT DE VÍDEO. PRESERVE A INTENSIDADE COMERCIAL, os títulos, \u00e9mojis e as etapas do sistema anterior.\n'
        'NÃO produza IMAGEM nova, NÃO devolva seção de IMAGEM, NÃO devolva TÍTULOS SEO, NÃO mude o cenário da IMAGEM. A entrada de IMAGEM abaixo é read-only.\n'
        'A DIREÇÃO VISUAL EM INGLÊS (antes de 🎙️) deve ter pelo menos 1.500 caracteres, preferencialmente 3.000–5.500 de detalhes novos e aplicáveis, sem limite superior imposto pelo aplicativo.\n'
        'Exigir ação física em cada etapa: energia documental, movimento natural, atmosfera viva e reações realistas, nunca estética de manequim.\n'
        f'Quantidade conferida pelo scanner: {qtd} UNIDADES. Se 2 ou 3 unidades, TODAS devem estar visíveis desde o primeiro até o último quadro: uma na mão apenas se fisicamente possível, demais apoiadas conforme a IMAGEM. Não inventar unidades. {scan.get("regra_pos_vid", "")}\n'
        f'FÍSICA ATIVA ENCONTRADA NA IMAGEM (jamais introduzir causas ausentes):\n{ambiente}\n'
        'BAGUNCINHA VIVA: descreva com eventos temporais o que já existe no PROMPT DE IMAGEM: toalha se move pela gravidade e pelo vento real; gotas APENAS se ela estiver molhada; caneca, livro, louça, cabo e mesa ficam fisicamente apoiados; plantas em vento assíncrono; animal somente se presente; chuva, vapor e iluminação coerentes com a locação. INSIRA esses eventos no VÍDEO, não no prompt de IMAGEM.\n'
        f'PRODUZA EXATAMENTE OS TÍTULOS E EMOJIS DESTA ESTRUTURA:\n{modelo_saida}\n'
        f'DIREÇÃO FÍSICA DETALHADA:\n{DIRETRIZ_VIDEO_V12}\n'
        f'\nPROMPT DE IMAGEM APROVADO — NÃO ALTERAR NENHUMA PALAVRA:\n{imagem}\n'
        f'\nPROMPT DE VÍDEO ORIGINAL — MANTER IDEIA, GANCHO, FALA, CTA, FORÇA E ESTILO:\n{video_original}\n'
        '\nSAÍDA: apenas o texto completo do PROMPT DE VÍDEO, sem cercas de código, sem heading principal ###, começando em 🎬. '
    )
    novo_video=None
    try:
        validar_cota_ia()
        resposta=cliente_openai.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role':'system','content':'You are ÉLÉVO\'s expert video-motion director. Preserve the original still image verbatim, visual continuity, product inventory, rich UGC energy, emojis, audio, CTA structure. Output only the VIDEO section. English visual directions, Portuguese speech.'},
                {'role':'user','content':instrucao},
            ],
            temperature=0.68,
            max_tokens=6000,
        )
        proposta=(resposta.choices[0].message.content or '').strip().strip('`')
        if proposta.startswith('### 🎬'):
            proposta=proposta.split('\n',1)[1].strip()
        linhas_necessarias=('🎬','🎙️','📝','🛡️','🫱','⚠️','✨','🛒')
        if '### 📸' not in proposta and '### 🔑' not in proposta and all(k in proposta for k in linhas_necessarias) and _direcao_visual_caracteres_v12(proposta)>=MIN_CARACTERES_DIRECAO_VISUAL_V12:
            novo_video=proposta
    except Exception:
        # Keep the saved original and use deterministic physical fallback.
        pass
    if not novo_video:
        novo_video=_fallback_video_v12(video_original,scan,ambiente,modo)
    if _direcao_visual_caracteres_v12(novo_video)<MIN_CARACTERES_DIRECAO_VISUAL_V12:
        # Defensive minimum guarantee, with scene-specific rather than repeated padding.
        novo_video=_fallback_video_v12(novo_video,scan,ambiente,modo)
    # Explicit inventory guarantee in the copied VIDEO text, including successful AI drafts.
    if qtd >= 2 and f'[KIT LOCK {qtd} UNITS]' not in novo_video:
        linhas=novo_video.split('\n',1)
        regra=(f"📦 [KIT LOCK {qtd} UNITS] All {qtd} original reference units must stay visible, "
               f"supported and distinct at 0:00–0:10; only one is held, the other {qtd-1} "
               "remain at their exact still-image locations on the counter. Never remove, "
               "duplicate, recolor, resize, merge or teleport any of them.")
        novo_video=(linhas[0]+'\n'+regra+'\n'+linhas[1]) if len(linhas)>1 else (regra+'\n'+novo_video)
    # V14: reforço determinístico, com descrição específica dos objetos da IMAGEM.
    # Entra APENAS no texto do vídeo, mesmo quando a IA responde pouco ou pula detalhes.
    novo_video=_injetar_ecossistema_v14(novo_video,imagem,scan,modo)
    final=_trocar_so_video_v12(conteudo,novo_video)
    validado=extrair_blocos_roteiro(final)
    if validado['prompt_imagem']!=imagem or validado['secao_seo_texto']!=partes['secao_seo_texto']:
        raise ValueError('A integridade do prompt original de IMAGEM ou SEO foi alterada; geração cancelada.')
    return final


BANCO_DE_MEMORIA_17_3 = """
====================================================================
[ 🧠 17.3. BANCO DE MEMÓRIA E TREINAMENTO INTEGRAL (OS 5 PROMPTS DE OURO MASTER + ACERVO COMPLETO V3 A V9.2 DO DOCUMENTO) ]

🔥 NOSSO LEMA SUPREMO DE VENDAS (PROIBIDO VIOLAR):
"NÓS NÃO VENDEMOS PRODUTOS. NÓS VENDEMOS DECISÕES, SENSAÇÕES E A SOLUÇÃO DE UMA DOR!"
- É PROIBIDO fazer fala com cara de comercial chato ("Você sabia que o produto X chegou? Ele é a solução que você precisa"). Isso NÃO vende!
- A fala dos 9 segundos TEM que conversar olho no olho com proximidade de amiga confidente:
  1. Rasgar a DOR REAL logo nos primeiros 2 segundos ("Amiga, seu cabelo tá elástico e quebrando só de encostar a escova?", "O secador tá cozinhando seu cabelo?", "Passando vergonha servindo visita em pote velho?").
  2. Entregar a SENSAÇÃO FÍSICA e o DESEJO ("faz uma cauterização de salão no seu chuveiro", "deixa o fio desmaiado, pesado de brilho espelhado", "encorpa a fibra na primeira lavagem").
  3. Fechar com o GATILHO DO LOTE SECRETO ("O pessoal do estoque surtou e liberou o lote promocional quase de graça, corre na sacolinha antes que zere!").
- PROIBIDO repetir "segredo das coreanas" se o produto da foto NÃO for da linha Coreana! Adapte 100% da fala para a DOR e a SOLUÇÃO reais do produto da foto!

🚨 REGRAS VISUAIS INQUEBRÁVEIS DO BANCO DE MEMÓRIA:
1. ZERO DESCRIÇÃO DE CORES OU DICIONÁRIOS DO PRODUTO: NUNCA escreva listas técnicas tipo `[{'color': ...}]`! Diga apenas: `the EXACT product(s) from the reference image — DO NOT alter, redraw, or describe the product colors, logo, or text; copy the reference image 100% intact`.
2. REGRA DO KIT (1 NA MÃO + O RESTO NA BANCADA): Quando houverem 2, 3, 5 ou mais produtos na imagem, ELA NUNCA SEGURA TODOS NA MÃO AO MESMO TEMPO! Ela segura APENAS 1 unidade na mão (`firmly holding ONE of the units in her hand`), enquanto as outras unidades ficam apoiadas na bancada bem ao lado dela (`while the other unit(s) rest neatly on the counter beside her, making all units clearly visible in the scene`), tanto na Imagem quanto no Shot 1 e Shot 2 do Vídeo!


[PROTOCOLO FÍSICO REALISTA V10 — PRIORIDADE MÁXIMA; PREVALECE SOBRE MOLDES ANTIGOS]
- CONSERVAÇÃO: mesmo número de produtos, identidade, altura, largura, volume, tampa, marca e rótulo em TODOS os quadros; não duplicar, fundir, deformar, trocar textura nem desaparecer. O objeto não teletransporta entre mão e bancada.
- REFERÊNCIA FIXA: a foto fornecida é REFERÊNCIA APENAS DO PRODUTO (não do ambiente). Cor, embalagem, impressão, acabamento e tamanho relativo vêm exclusivamente dela; o cenário vem do AMBIENTE ELEVO ESCOLHIDO ou sorteado. Nunca descreva cor, peso, volume, tampa ou rótulo do produto no prompt visual.
- CONTATO E GRAVIDADE: produto apoiado na bancada tem base em contato contínuo, sombra de contato consistente, gravidade, inércia e oclusão reais; produto na mão mantém posição estável, dedos anatomicamente corretos, pressão e oclusão coerentes, nenhuma interpenetração ou flutuação.
- CÂMERA: celular realista, câmera principalmente estável, deslocamentos curtos e suaves; proibir zoom violento, whip-pan, tremor excessivo, troca brusca de foco, glare artificial. Profundidade de campo coerente sem ocultar itens essenciais.
- PELE E MATERIAIS: poros finos, fios de cabelo individuais, rugosidade realista, leve assimetria; materiais com BRDF plausível, reflexos dependentes da iluminação real, sem brilho plástico ou nitidez falsa. Evitar hiperbolização da pele, do olhar ou da respiração.
- AMBIENTE: plantas e tecidos se movem apenas se houver vento plausível; vapor e água só onde efetivamente existem na referência; sombras, reflexos, perspectiva, luz e exposição temporalmente contínuos. Incluir a planta, a baguncinha orgânica e o único animal discreto previstos no cenário escolhido, mesmo que a foto enviada exiba somente o produto; não criar objetos extras no VÍDEO que não constem na imagem de cena.
- FINAL: a partir de 0:08, a apresentadora mantém o produto perfeitamente visível em quadro; no último segundo, segurar imagem estável com produto e ambiente intactos até o último frame. PROIBIDO quadro preto, fade para preto, glitch, logo sobreposto, marca d'água, sacola 3D flutuante ou elementos duplicados. Logo original impressa na embalagem permanece; não acrescentar logo da empresa na imagem.
- ÁUDIO/COPY: fala factível em 9 segundos (aprox. 18–25 palavras, ajustar à locução), sem afirmar benefícios não demonstrados no rótulo, escassez, preço ou estoque não confirmados. Texto de CTA pode ficar para edição fora do gerador; não gerar UI nativa.
- Se um molde histórico conflitar com estas regras, este protocolo é soberano.

--- PARTE A: OS 5 PROMPTS DE OURO MASTER DO DOCUMENTO (MOLDE OFICIAL DO BLOCO 17 - 360º SEM LOGO) ---

📦 MOLDE 1: O GANCHO DO CAOS (Para Kits de 3 Potes / Múltiplas Unidades)
📸 GABARITO DE IMAGEM BASE:
RAW photography, close-up POV handheld mobile phone shot. Extreme hyper-realism: detailed natural skin pores, peach fuzz, subtle moisture on skin, NO artificial flash. Photorealistic young Brazilian woman (Aurora: dark hair, subtle bangs, intense conspiratorial expression, incredibly shiny and healthy-looking hair). A small, discrete black wireless lapel microphone is visibly clipped to the neckline of her shirt. She is standing in a relatable, vibrant, sunlit Brazilian kitchen connected directly to a dense, lush green balcony filled with cascading ferns, monsteras, and warm tropical sunlight filtering through the leaves, with a small caramel dog resting on a colorful rug in the background. Natural everyday clutter: a ceramic coffee mug and a dish towel casually resting on the wooden counter. [CRITICAL ABSOLUTE PHYSICS & SIZE LOCK: STRICT 1:1 real-world scale. These are standard 400g cosmetic jars. The tubs shown must look compact, light, and perfectly proportioned to fit comfortably. Absolutely DO NOT oversize]. She is firmly holding ONE of the tubs from the reference kit in her hand, while the other two tubs rest neatly on the wooden counter right beside her, making all three clearly visible in the scene. DO NOT alter, redraw, or describe the product colors or text; copy the reference image 100% intact. Unfiltered UGC vlog style, 8k resolution.
🎬 COMANDO DE VÍDEO COMPLETO:
Shot 1 (Macro Hook & Physics): [POV intensely erratic handheld mobile video, documentary chaos aesthetic. Extreme dynamic spatial movement, heavy camera shake, raw UGC vlog style. The extreme edges of the camera lens catch bright natural light flares from the varanda plants. Starts with an aggressive Macro Zoom In exclusively on the EXACT reference kit products (one tub held firmly in her hand while the other two tubs rest neatly beside her on the wooden counter against the green varanda background, making all three clearly visible). [CRITICAL PHYSICS & SCALING]: 1:1 real-world scale, strictly realistic size, perfectly proportioned to her hand, do not oversize. DO NOT alter or redraw the reference packaging. SINGLE MOTION TRICK (The Trigger Tap): Her clean free index finger performs a deliberate micro-tap on the lid of the main tub twice to emphasize it. NO hand overlapping, absolute physics stability, NO pixel melting.]
Shot 2 (Whip Pan & Visceral Emotion): [0:03: WHIP PAN and brutal focus pull! The camera violently tilts up and snaps focus onto Aurora's face (straight bangs, wireless lapel microphone clearly visible on her shirt, flawless skin with visible pores). VISCERAL EMOTION ACTIVE: She leans in aggressively towards the lens (The Gossip Lean), her chest heaving with heavy, urgent breathing, pupils visibly dilated, and she flashes a breathless, intensely serious expression of pure warning while holding ONLY ONE tub in her hand and keeping the other two tubs resting stationary on the counter right beside her. ENVIRONMENT REINFORCEMENT LOCK: Bright Brazilian kitchen connected to a sunlit tropical varanda with dense green ferns. In the deep background, the caramel dog shifts position slightly.]
Interaction (3D CTA): [0:08: She aggressively points her free index finger downwards towards the bottom corner of the screen. At this precise second, a highly realistic 3D floating orange shopping bag object materializes in the air near her pointing finger, casting realistic shadows. It is a physical 3D element pointing towards the UI button location.]
[PRISTINE CANVAS LOCK - ZERO WATERMARKS]: [Strict requirement: The video frame must be completely devoid of any platform UI, handles, usernames, profile pictures, corner watermarks, or embedded social media logos from frame 0 to the final second. Pure clean video feed only.]

📦 MOLDE 2: O GANCHO DA TEMPESTADE (Para Frascos Compactos 200ml-250ml - Banheiro Rústico com Vapor e Chuva)
📸 GABARITO DE IMAGEM BASE:
RAW photography, close-up POV handheld mobile phone shot. Extreme hyper-realism: detailed natural skin pores, peach fuzz, microscopic droplets of warm steam condensation clinging delicately to her skin, NO artificial flash. Photorealistic young Brazilian woman (Aurora: dark hair, subtle bangs, breathless conspiratorial expression, incredibly healthy hair). A small, discrete black wireless lapel microphone is visibly clipped to the neckline of her cotton shirt. She is standing in an intimate, steam-filled rustic bathroom. Heavy rainstorm visibly and dynamically pounding against the frosted glass window in the background, creating blurry streaks of water. A bundle of hanging eucalyptus leaves sways slightly from an indoor draft. Natural everyday clutter on the stone shelf: a small ceramic dish and a rolled linen hand towel. [CRITICAL TRUE-SCALE & PHYSICAL ANCHOR LOCK]: STRICT 1:1 real-world scale. The EXACT 250ml bottle from the reference image is held firmly in her hand, remaining a perfectly compact, lightweight size, perfectly proportioned to fit inside a human palm. Absolutely DO NOT oversize. Unfiltered UGC vlog style, 8k resolution.
🎬 COMANDO DE VÍDEO COMPLETO:
[POV intensely erratic handheld mobile video, documentary chaos aesthetic. Extreme dynamic spatial movement, heavy camera shake, raw UGC vlog style. Quick cell phone auto-focus hunting effect at 0:01 tracking the bottle, then violently snapping to her face. ENVIRONMENT REINFORCEMENT LOCK V9 DENSE: Steam-filled rustic bathroom, heavy rainstorm visibly and dynamically pounding against the frosted window in the background. A bundle of hanging eucalyptus sways slightly from a draft. [CRITICAL TRUE-SCALE & PHYSICAL ANCHOR LOCK]: STRICT 1:1 real-world scale. The EXACT 250ml bottle is held firmly in her hand, remaining a perfectly small 250ml size. SPATIAL MOTION TRICK (The Andadinha): Aurora takes a purposeful, natural step forward towards the camera, shifting her weight organically. 0:02-0:04 (TACTILE TEST V9): Her clean free index finger performs a deliberate, hard double-tap on the top cap of the bottle. NO hand overlapping, absolute physics stability, NO pixel melting. 0:05-0:08: She leans in aggressively towards the lens (The Gossip Lean), her chest heaving with visceral breathing. She makes intense, urgent eye contact. 0:09: She aggressively points her free index finger downwards to the right corner, where a realistic 3D floating orange shopping bag materializes. [PRISTINE CANVAS LOCK - ZERO WATERMARKS]: Absolutely no platform UI, handles, corner watermarks, or embedded social media logos from start to finish. Pure clean video feed only.]

📦 MOLDE 3: O GANCHO DO BORRIFADOR (Para Frascos 300ml-500ml - Varanda Ensolarada com Samambaias e Caramelo)
📸 GABARITO DE IMAGEM BASE:
RAW photography, close-up POV handheld mobile phone shot. Extreme hyper-realism: detailed natural skin pores, peach fuzz, subtle warm glow of sun-kissed skin, NO artificial flash. Photorealistic young Brazilian woman (Aurora: dark hair, straight bangs, sharp and intense conspiratorial expression). A small, discrete black wireless lapel microphone is visibly clipped to the neckline of her shirt. She is standing on a bright, airy Brazilian varanda surrounded by lush green hanging ferns, monsteras, and warm golden hour sunlight filtering through the foliage. In the deep background, a small caramel dog is resting peacefully on a woven rug. Natural everyday clutter on a small side table: a terracotta plant mister and an unfinished ceramic cup. [CRITICAL PHYSICS & SIZE LOCK: STRICT 1:1 real-world scale, strictly realistic product size, exact match to reference]. She is firmly holding the exact bottle from the reference image. The bottle must look compact, light, and perfectly proportioned to her hand grip. Absolutely DO NOT oversize. Unfiltered UGC vlog style, 8k resolution.

📦 MOLDE 4: O GANCHO DO PESO / IMPACTO (Para Pote Único de 1kg - Quarto com TV Piscando ou Varanda com Cachoeira)
📸 GABARITO DE IMAGEM BASE:
RAW photography, close-up POV handheld mobile phone shot. Extreme hyper-realism: detailed natural skin pores, peach fuzz, subtle cinematic contrast lighting, NO artificial flash. Photorealistic young Brazilian woman (Aurora: dark hair, highly expressive mobile eyebrows, intense and focused look). A small, discrete black wireless lapel microphone is visibly clipped to the neckline of her shirt. ENVIRONMENT REINFORCEMENT: Ordinary Brazilian bedroom at night, active television screen emitting flickering ambient light across the room, natural clutter including an open notebook, loose clothes on a chair, and a half-full glass of water on the nightstand (or lush Varanda with Waterfall, butterflies and sleeping caramel dog). [CRITICAL PHYSICS & SIZE LOCK: STRICT 1:1 scale, strictly realistic standard 1kg tub size fitting normal hand proportions, DO NOT oversize]. She firmly holds the single 1kg tub from the reference image. Unfiltered UGC vlog style, 8k resolution.

📦 MOLDE 5: O GANCHO DO ACONCHEGO (Para Kit com 2 Potes/Produtos - Home Office com Gato ou Cozinha de Batalha)
📸 GABARITO DE IMAGEM BASE:
RAW photography, close-up POV handheld mobile phone shot. Extreme hyper-realism: detailed natural skin pores, peach fuzz, soft warm illumination from a desk lamp, NO artificial flash. Photorealistic young Brazilian woman (Aurora: dark hair, subtle bangs, breathless conspiratorial facial expression, healthy shiny hair). A small, discrete black wireless lapel microphone is visibly clipped to the neckline of her shirt. She is standing in a cozy, lived-in modern home office space with a warm reading lamp casting soft shadows, a tall wooden bookshelf filled with books in the background, and a sleepy cat curled up on a soft armchair. Natural everyday clutter on the wooden desk: an open planner, a ceramic coffee mug with steam rising, and a pair of wire-rimmed glasses. [CRITICAL ABSOLUTE PHYSICS & SIZE LOCK: STRICT 1:1 real-world scale. These are standard 400g cosmetic jars. The two tubs shown must look compact, light, and perfectly proportioned to fit comfortably. Absolutely DO NOT oversize]. She is firmly holding ONE of the units from the reference kit in her hand, while the second unit rests neatly on the wooden desk right next to her, making both products clearly visible. Unfiltered UGC vlog style, 8k resolution.

--- PARTE B: BANCO DE FALAS E GANCHOS CAMPEÕES REAIS DO DOCUMENTO (EXEMPLOS DE COMO ATACAR A DOR E ENTREGAR A SOLUÇÃO) ---
Use a estrutura psicológica destas falas campeãs (NUNCA copie o nome de outro produto, adapte para a dor e o produto da foto):
- Exemplo de Fala Campeã 1 (Dano Térmico / Secador e Chapinha):
  "[Borrifador + Suspiro] Amiga, para tudo... você tem noção de que o secador tá cozinhando seu cabelo todo dia? Esse tratamento blinda os fios do calor, sela as pontas na hora e dá um brilho espelhado surreal! O lote promocional vazou, corre na sacolinha!"
- Exemplo de Fala Campeã 2 (Cabelo Elástico, Fino e Quebrando na Escova):
  "(Dois toques secos na tampa) Amiga, se o seu cabelo tá fino, ralo e quebrando inteiro quando você escova, para tudo! Esse tratamento de reposição de massa preenche a fibra, encorpa os fios e devolve a vida na primeira aplicação. O estoque desse lote secreto tá derretendo, corre na sacolinha!"
- Exemplo de Fala Campeã 3 (Segredo que as Donas de Salão Escondem):
  "[Som de Água + Suspiro] Amiga, o que as donas de salão não te contam é que esse tratamento deixa o fio solto, sem pesar e com balanço de cinema no seu próprio chuveiro... e o lote promocional liberou quase de graça! Corre na sacolinha antes que acabe!"
- Exemplo de Fala Campeã 4 (Pele Rachada / Ressecamento Extremo):
  "[Som de Água + Suspiro] Amiga, o sistema do estoque surtou e liberou esse potão quase de graça! Ele acaba com o ressecamento extremo na primeira passada e deixa um toque de seda surreal. Corre na sacolinha antes que o lote zere!"
- Exemplo de Fala Campeã 5 (Moda / Caimento que Modela sem Marcar):
  "Amiga, achei o segredo pro seu look! Ele modela o corpo, tem um caimento impecável que não marca nada e veste como uma luva. O pessoal do estoque enlouqueceu no desconto, corre na sacolinha antes que esgote!"
- Exemplo de Fala Campeã 6 (Casa / Mesa Posta / Utilidades):
  "Passando vergonha servindo visita em pote velho ou jogando dinheiro no lixo todo mês? Acorda! Esse achado entrega luxo e praticidade na hora e a loja surtou liberando um lote secreto. Pega logo antes que acabe!"

--- PARTE C: MÓDULO CAMALEÃO (OS 20 AMBIENTES OFICIAIS) ---
1. Banheiro Caótico (vapor denso, espelho embaçado, secador na pia) | 2. Varanda Tropical (samambaias, costela-de-adão, luz de sol, caramelo) | 3. Penteadeira Golden Hour | 4. Área de Serviço Raiz | 5. Jardim Rústico | 6. Cachoeira Secreta (pedras úmidas, borboletas, água corrente) | 7. Cozinha Afetiva / Cozinha de Batalha | 8. Quarto Desarrumado (TV ligada piscando luz) | 9. Quintal de Terra | 10. Deck de Piscina | 11. Estufa Caseira | 12. Varanda com Tempestade (coqueiro envergando na chuva, passarinho nas vigas) | 13. Sala de Estar Noturna | 14. Banheira Vintage | 15. Varanda de Praia | 16. Home Office Moderno (estante de livros, luminária, gato na poltrona) | 17. Deck de Barco no Rio Amazonas | 18. Canto da Leitura | 19. Lavabo Luxo | 20. Calçada Portuguesa Urbana.

[PROTOCOLO FÍSICO REALISTA V10 — PRIORIDADE MÁXIMA; PREVALECE SOBRE MOLDES ANTIGOS]
- CONSERVAÇÃO: mesmo número de produtos, identidade, altura, largura, volume, tampa, marca e rótulo em TODOS os quadros; não duplicar, fundir, deformar, trocar textura nem desaparecer. O objeto não teletransporta entre mão e bancada.
- REFERÊNCIA FIXA: a foto fornecida é REFERÊNCIA APENAS DO PRODUTO (não do ambiente). Cor, embalagem, impressão, acabamento e tamanho relativo vêm exclusivamente dela; o cenário vem do AMBIENTE ELEVO ESCOLHIDO ou sorteado. Nunca descreva cor, peso, volume, tampa ou rótulo do produto no prompt visual.
- CONTATO E GRAVIDADE: produto apoiado na bancada tem base em contato contínuo, sombra de contato consistente, gravidade, inércia e oclusão reais; produto na mão mantém posição estável, dedos anatomicamente corretos, pressão e oclusão coerentes, nenhuma interpenetração ou flutuação.
- CÂMERA: celular realista, câmera principalmente estável, deslocamentos curtos e suaves; proibir zoom violento, whip-pan, tremor excessivo, troca brusca de foco, glare artificial. Profundidade de campo coerente sem ocultar itens essenciais.
- PELE E MATERIAIS: poros finos, fios de cabelo individuais, rugosidade realista, leve assimetria; materiais com BRDF plausível, reflexos dependentes da iluminação real, sem brilho plástico ou nitidez falsa. Evitar hiperbolização da pele, do olhar ou da respiração.
- AMBIENTE: plantas e tecidos se movem apenas se houver vento plausível; vapor e água só onde efetivamente existem na referência; sombras, reflexos, perspectiva, luz e exposição temporalmente contínuos. Incluir a planta, a baguncinha orgânica e o único animal discreto previstos no cenário escolhido, mesmo que a foto enviada exiba somente o produto; não criar objetos extras no VÍDEO que não constem na imagem de cena.
- FINAL: a partir de 0:08, a apresentadora mantém o produto perfeitamente visível em quadro; no último segundo, segurar imagem estável com produto e ambiente intactos até o último frame. PROIBIDO quadro preto, fade para preto, glitch, logo sobreposto, marca d'água, sacola 3D flutuante ou elementos duplicados. Logo original impressa na embalagem permanece; não acrescentar logo da empresa na imagem.
- ÁUDIO/COPY: fala factível em 9 segundos (aprox. 18–25 palavras, ajustar à locução), sem afirmar benefícios não demonstrados no rótulo, escassez, preço ou estoque não confirmados. Texto de CTA pode ficar para edição fora do gerador; não gerar UI nativa.
- Se um molde histórico conflitar com estas regras, este protocolo é soberano.

====================================================================
"""

BANCO_DE_MEMORIA_17_3_ATIVO_V1682 = """
[ÉLÉVO 17.3 — ESTRUTURA ORIGINAL, REGRAS VISUAIS ATUALIZADAS V16.8.2]
Preservar os três títulos-mestre do resultado e os cinco blocos tradicionais:
(1) IMAGEM BASE RAW UGC, (2) VÍDEO COM SHOT 1, SHOT 2, INTERAÇÃO E PRISTINE CANVAS,
(3) ÁUDIO/FALA BRASILEIRA, (4) CTA/TEXTO sugerido para edição, (5) TÍTULOS SEO.
Imagem e vídeo devem ser detalhados em INGLÊS; fala, SEO e orientações editoriais em PORTUGUÊS.
A energia estética dos exemplos V7/V8/V9 é inspiração APENAS para câmera, microfísica,
movimento e vida real — NUNCA copiar marca, cor, tampa, peso, embalagem, protagonista,
identidade ou texto dos produtos citados nos exemplos antigos.

[PERSONA LOCK] Uma ÚNICA influenciadora adulta selecionada é a única apresentadora:
identidade facial, cabelos, voz, roupas e gestos estáveis em imagem e vídeo. Não substituir
por Aurora quando outra influenciadora estiver ativa; não copiar franja reta dos exemplos.

[EXTERNAL REFERENCE PRODUCT LOCK] A foto do PRODUTO anexada no gerador externo é a única
referência visual da mercadoria. Não descrever cor, rótulo, marca, formato, tampa, lote,
capacidade, números ou textura específicos do produto nos prompts visuais. Não gerar
embalagem imaginada. Escala física relativa à mão e à bancada é realista e universal,
sem ampliar automaticamente itens pequenos, com óptica real e sem aproximação forçada.
Contagem do kit constante. Um na mão apenas se seguro; outros sobre superfície estável.

[SCENE LOCK] O ambiente vem do seletor dos 21 ambientes ÉLÉVO, NÃO da foto do produto.
Sorteio INFINITO equivale a uma das 20 fichas. A mesma ficha entra em imagem e vídeo:
planta natural contextualizada, baguncinha vivida (máximo algumas peças) e um gato ou
cachorro discretamente ao fundo, inclusive banheiro (animal no corredor, nunca no chuveiro).
Objetos, clima, layout, luz e animal são os MESMOS no vídeo, sem teleportar.

[REAL PHYSICS] Sensor de celular com leve ruído natural, auto-focus settling curto e
rolling shutter sutil só em movimento. Peles com poros, fibras naturais, fios de cabelo,
respiração realista e expressões não caricatas. Cor, som, reflexos e sombras seguem fontes.
Água cai com gravidade; vento move folhas e tecido com inércia diferente; condensação
só aparece onde a temperatura/umidade permitem; TV/LED refletem em superfícies reais.
Animal faz microação plausível (piscar, respirar, mexer uma orelha); sem duplicação.
Evitar excessos CGI, macro-zoom agressivo, tremor violento e deriva do produto.

[UGC REAL] Shot 1 mostra produto inteiro e bem proporcionado; Shot 2 reorienta suavemente
para a influenciadora preservando o mesmo produto e cenário; interação breve e física.
NUNCA materializar sacolas 3D, UI, glitch, logo extra ou quadro preto dentro do vídeo.

[COPY] Gancho pessoal baseado em problema plausível e benefício comprovado pelo rótulo.
Fala de 9 s aproximadamente 18 a 25 palavras, adaptada à dicção. Não inventar
lotes secretos, estoque, preços, promoções nem resultado clínico ou garantido.
Os textos de CTA pertencem somente à edição posterior; não sobrepor UI ao vídeo bruto.
""".strip()

with st.expander("🧠 17.3. Abrir Banco de Memória & Treinamento Oficial (Conectado ao 17 e ao 17.2)", expanded=False):
    st.caption("Todo o conhecimento do seu documento está gravado aqui e alimenta automaticamente os botões do Bloco 17 e do Bloco 17.2:")
    st.code(BANCO_DE_MEMORIA_17_3, language="markdown")


# ==========================================================
# ÉLÉVO V16.8.2 — TRAVA NEUTRA DO PRODUTO (EXTERIOR AO GERADOR)
# A foto original é carregada de novo pelo usuário no gerador de imagem/vídeo.
# Não "adivinhar" marca, tonalidade, lote, capacidade ou formato pelo texto.
# ==========================================================
TRAVA_PRODUTO_FOTO_V1682 = (
    '[ÉLÉVO V16.8.2 — EXTERNAL PRODUCT REFERENCE / IMAGE+VIDEO LOCK] '
    'The product photo separately attached to the IMAGE/VIDEO GENERATOR is the ONLY authority for the '
    'product appearance, packaging, labels, graphics, colors, brand, surface, volume and exact shape. '
    'DO NOT describe, translate, reconstruct, recolor, redesign or invent the product in this text prompt. '
    'NEVER import a bottle, pot, cap, label color, lot number, or product name from historical templates '
    'or from the selected influencer persona. Changes of influencer affect ONLY the person and voice, '
    'not this photo-referenced product. Maintain physical proportions relative to the real human hand '
    'and furniture: small goods must remain small, large goods must stay realistically large, '
    'without forced universal hand-held size, false giant scale or dramatic near-lens enlargement. '
    'Use compatible body contact, gravity, oclusion, lens geometry and continuous light. '
    'If the reference image has not been supplied to the external generator, ask for it instead '
    'of creating a product from this text.'
)

def fixar_trava_produto_ambos_prompts_v1682(conteudo):
    """Aplica a MESMA trava visual nos dois outputs sem tocar na fala, SEO ou botões."""
    cabecalho = TRAVA_PRODUTO_FOTO_V1682 + '\n'
    for titulo in (r'(?im)^(###\s*📸\s*PROMPT DE IMAGEM[^\n]*\n)',
                   r'(?im)^(###\s*🎬\s*PROMPT DE VÍDEO[^\n]*\n)'):
        conteudo, n = re.subn(titulo, lambda m: m.group(1) + cabecalho,
                             conteudo, count=1)
        if n != 1:
            raise ValueError('Formato inesperado: produto não pode ser protegido nos dois prompts.')
    return conteudo

DIRETRIZES_VIDA_REAL_V1682 = (
    '[21 ENVIRONMENTS / NATURAL UGC PHYSICS — NEVER REPLACE THE CURRENT OUTPUT FORMAT] '
    'The selected ÉLÉVO environment, not the product-only reference photo, defines the new setting. '
    'Its one modest leafy plant, coherent lived-in clutter and one subtle background cat/dog '
    'must be visible from the still image and remain in the corresponding video, even in bathrooms '
    '(pet safely beyond the open door). Wind must be causal and subtle indoors. Outdoor leaves '
    'bend with realistic inertia and unsynchronized movement. Existing steam convects, water '
    'follows gravity, towels move only when touched or blown, lights and screen flicker have '
    'real sources. Animal micro-actions: breathing, blinking, a single ear or paw shift only; '
    'no synchronized looping, duplicated cats/dogs, or extra inserted props. Respect real '
    'phone lens parallax, occasional mild autofocus settling, modest rolling-shutter response, '
    'grain without artificial dirt, skin pores and flyaway hairs. Avoid violent zoom, waxy '
    'CGI faces, impossible wetness, caricatured gestures and product resizing. '
    'PRODUCT VISUALS: do not describe any physical packaging feature or lot. '
    'Marketing audio and SEO may use identifiable name/verified benefits but cannot invent '
    'secret stock, promotional lots or discounts. This add-on changes ONLY realism, not the '
    'approved 17/17.2 image-video-audio-text-SEO architecture.'
)

# ==========================================================
# MOTOR DE EXECUÇÃO DO BLOCO 17 (SEGUE FIELMENTE OS MOLDES DO BANCO DE MEMÓRIA 17.3 — SEM LOGO)
# ==========================================================
if btn_gerar_roteiro and img_produto and pode_gerar_roteiro:
    with st.spinner("🦅 Escaneando a Dor & Solução do rótulo e consultando Banco de Memória 17.3..."):
        try:
            img_b64_roteiro = base64.b64encode(img_produto.getvalue()).decode('utf-8')
            scan_17 = escanear_dor_e_contagem_da_foto(img_b64_roteiro)
            gancho_sorteado_17 = selecionar_gancho_v11()
            direcao_v11_17 = selecionar_direcao_fisica_v11(email_sessao, "360")
            
            instrucao_ouro = f"""
            Atue como o Motor Oficial da Máquina de Criação 360º (Bloco 17), conectado diretamente ao BANCO DE MEMÓRIA 17.3 abaixo:

            {BANCO_DE_MEMORIA_17_3_ATIVO_V1682}

            🔍 [DIAGNÓSTICO DE NEUROMARKETING EXTRAÍDO DA FOTO ENVIADA]:
            - Produto/Kit: {scan_17.get('nome_pt')}
            - Quantidade Exata de Unidades na Foto: {scan_17.get('qtd')} unidade(s)
            - Tipo de Embalagem/Peça: {scan_17.get('tipo_embalagem')}
            - A DOR VISCERAL QUE ELE RESOLVE (ATAQUE ISSO NA FALA!): {scan_17.get('dor_pt')}
            - A SENSAÇÃO / TRANSFORMAÇÃO REAL QUE ELE ENTREGA: {scan_17.get('solucao_pt')}
            - ÂNGULO DE GANCHO SORTEADO PARA HOJE: {gancho_sorteado_17}
            - REGRA OBRIGATÓRIA DE POSICIONAMENTO NA IMAGEM: {scan_17.get('regra_pos_img')}
            - REGRA OBRIGATÓRIA DE POSICIONAMENTO NO VÍDEO (DO INÍCIO AO FIM): {scan_17.get('regra_pos_vid')}

            🚨 [REGRAS INQUEBRÁVEIS DE EXECUÇÃO]:
            1. FALA COM LEMA 'DOR -> SENSAÇÃO -> SOLUÇÃO': Na fala da {nome_inf_ativa}, NUNCA faça propaganda genérica ("Você sabia que o segredo chegou?"). Comece rasgando a dor `{scan_17.get('dor_pt')}`, entregue a sensação física `{scan_17.get('solucao_pt')}` com intimidade de amiga fofoqueira do bem, e feche com um convite natural para conferir o produto na sacolinha, sem alegar oferta ou lote não confirmado! E NUNCA fale de "coreanas" a menos que a palavra "Coreana" esteja literalmente escrita em `{scan_17.get('nome_pt')}`!
            2. POSICIONAMENTO FÍSICO UNIVERSAL: Se houver {scan_17.get('qtd')} unidades, use {scan_17.get('regra_pos_img')}. Mantenha as unidades nas mesmas posições em imagem/vídeo. NUNCA descreva aparência, cor, tamanho nominal ou rótulo do produto por texto.
            3. Escreva os blocos visuais (`PROMPT DE IMAGEM`, `Shot 1`, `Shot 2`, `Interaction (3D CTA)`, `[PRISTINE CANVAS LOCK]`) 100% em INGLÊS PURO e ultra-denso!

            ENTREGUE EXATAMENTE NESTE FORMATO DE 3 SEÇÕES:

            ### 📸 PROMPT DE IMAGEM
            [Escreva aqui em inglês ultra-denso (1.300 a 1.900+ caracteres) o Prompt de Imagem Base seguindo fielmente o Molde do Banco de Memória 17.3, sorteando um ambiente vivo do Módulo Camaleão e aplicando: {scan_17.get('regra_pos_img')}]

            ### 🎬 PROMPT DE VÍDEO COMPLETO E UNIFICADO
            Shot 1 (Natural Hook & Physics): [Escreva em inglês seguindo prioritariamente o PROTOCOLO FÍSICO REALISTA V10: smartphone estável, sem zoom agressivo, produto inteiro e contínuo do início ao fim, aplicando {scan_17.get('regra_pos_vid')} + CRITICAL REFERENCE PHYSICS: real-world product-to-hand scale without forced enlargement or miniature packaging + SINGLE MOTION TRICK (The Trigger Tap on the lid of the single unit held / ou movimento da peça de roupa). NO hand overlapping, absolute physics stability, NO pixel melting.]
            Shot 2 (Whip Pan & Visceral Emotion): [0:03: WHIP PAN and brutal focus pull! The camera violently tilts up and snaps focus onto {nome_inf_ativa}'s face (wireless lapel microphone clearly visible on her shirt, flawless skin with visible pores). VISCERAL EMOTION ACTIVE: She leans in aggressively towards the lens (The Gossip Lean), her chest heaving with heavy, urgent breathing, pupils visibly dilated, and she flashes a breathless, intensely serious expression of pure warning while {scan_17.get('regra_pos_vid')}. ENVIRONMENT REINFORCEMENT LOCK: Repita em inglês todos os detalhes do cenário da imagem, plantas vivas, baguncinha e o animal se mexendo sutilmente no fundo.]
            Interaction (3D CTA): [0:08: She aggressively points her free index finger downwards towards the bottom corner of the screen. At this precise second, a highly realistic 3D floating orange shopping bag object materializes in the air near her pointing finger, casting realistic shadows. It is a physical 3D element pointing towards the UI button location.]
            [PRISTINE CANVAS LOCK - ZERO WATERMARKS]: [Strict requirement: The video frame must be completely devoid of any platform UI, handles, usernames, profile pictures, corner watermarks, or embedded social media logos from frame 0 to the final second. Pure clean video feed only.]
            🎙️ Áudio e Fala da {nome_inf_ativa} (Português — 100% Blindada Contra o Robô):
            Áudio (Inglês de fundo): [Audio captured via a wireless lapel microphone. Micro-ASMR intro (sound of product tap). Authentic room acoustics with subtle background ambient tones. Enthusiastic, urgent, conspiratorial voice, speaking as if revealing a highly guarded secret].
            Fala da {nome_inf_ativa}:
            "[Escreva em português uma fala visceral e magnética de 18 a 25 palavras aplicando '{gancho_sorteado_17}', atacando diretamente a dor '{scan_17.get('dor_pt')}', entregando a sensação '{scan_17.get('solucao_pt')}' e fechando com convite à sacolinha, sem inventar lote, estoque, desconto ou preço numérico]"
            📝 Texto na Tela (Nativo TikTok - Foco na Dor):
            ⚠️ [PERGUNTA CURTA E FORTE SOBRE A DOR]? 🛑
            ✨ [SENSAÇÃO / SOLUÇÃO IMEDIATA]
            🛒 CONFIRA NA SACOLINHA 👇

            ### 🔑 TÍTULOS SEO (Separados)
            **🔍 Geral (Dor):** [Título focado na solução da dor '{scan_17.get('dor_pt')}']
            **💡 Solução (Produto):** [Nome completo do produto/kit e volume]
            **🏷️ Marca (Resenha):** [Marca e nome do produto/kit resenha]
            """
            
            instrucao_ouro += (f"\n\n[PERSONA LOCK — OBRIGATÓRIO EM IMAGEM E VÍDEO] "
                               f"Apresentadora escolhida: {nome_inf_ativa}. {desc_inf_ativa} "
                               "Aplicar idade, aparência, cabelo, rosto, jeito de falar, emoção, "
                               "linguagem corporal e personalidade da mesma mulher nos dois prompts. "
                               "Não substituir por Aurora ou outra personagem genérica.")
            if explicacao_video_usuario and explicacao_video_usuario.strip():
                instrucao_ouro += f"\nNOTA DE DIREÇÃO DO USUÁRIO: {explicacao_video_usuario.strip()}"
            
            instrucao_ouro += ("\n\nNOTA DE VARIEDADE (NÃO REESCREVER O MOLDE DE IMAGEM): "
                              "Mantenha o mesmo padrão RAW/V9.2 da imagem original; o ANIMAL FACTOR é obrigatório na ficha de ambiente, "
                              "não coloque sempre o mesmo cachorro caramelo. Use somente o animal da ficha de ambiente, com espécie, "
                              "porte e ação conforme o ambiente; não repita a escolha recente. "
                              "Preserve a conexão visual com a natureza, o cenário rico e a baguncinha característica. "
                              f"Referência opcional de diversidade desta rodada: {direcao_v11_17['animal']}.")
            if direcao_v11_17.get('escolhido'):
                instrucao_ouro += ("\n\n[AMBIENTE ESCOLHIDO PELO USUÁRIO — TRAVA INEGOCIÁVEL]\n"
                                  + direcao_v11_17['trava_ambiente']
                                  + "\nOverride all random environment suggestions in the historical examples. "
                                    "Use this EXACT preset in the still image and repeat the identical object list "
                                    "and physical conditions in the video. Do not switch location after 0:00. ")
            instrucao_ouro += "\n\nREGRA FINAL INEGOCIÁVEL: " + PROTOCOLO_FISICO_17 + "\n\n" + DIRETRIZES_VIDA_REAL_V1682 + "\n\n" + TRAVA_PRODUTO_FOTO_V1682
            validar_cota_ia()
            resp = cliente_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é o Diretor de Arte e Copywriter Visceral da ÉLÉVO. Lema: 'Não vendemos produtos, vendemos a solução de uma dor e a sensação do resultado'. Preserve os headings dos Moldes 17.3, mas IGNORE qualquer aparência, marca, cor, quantidade nominal ou descrição de produto presente em exemplos históricos. Foto do produto é referência externa exclusiva. Escreva toda a parte visual em inglês puro."},
                    {"role": "user", "content": instrucao_ouro}
                ],
                max_tokens=6500, temperature=0.75
            )
            
            conteudo_texto = resp.choices[0].message.content.strip()
            conteudo_texto = fixar_ambiente_ambos_prompts_v165(
                conteudo_texto, direcao_v11_17.get('escolhido',''), st.session_state.get('elevo_ambiente_obs',''))
            conteudo_texto = reforcar_apenas_video_v12(conteudo_texto, scan_17, "360")
            conteudo_texto = fixar_trava_produto_ambos_prompts_v1682(conteudo_texto)
            st.session_state["roteiro_temporario"] = conteudo_texto
            salvar_roteiro_no_drive(email_sessao, conteudo_texto)
            
            if not E_O_CEO and aba_limites is not None:
                try: aba_limites.append_row([email_sessao, "Sim"])
                except Exception: pass
                
            st.success(f"✅ Pacote 360º Forjado com Gancho de Dor & Solução Visceral ({scan_17.get('qtd')} unidade(s))!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error("A solicitação não pôde ser concluída. Verifique a conexão ou sua cota de IA.")

# ==========================================================
# MOTOR DE EXECUÇÃO DO BLOCO 17.2 (CRIAÇÃO V9.2 COM LOGO GLITCH FINAL P1 + MEMÓRIA 17.3 + DOR & SOLUÇÃO)
# ==========================================================
if btn_gerar_v92 and pode_gerar_roteiro:
    if not img_produto:
        st.warning("⚠️ Suba a **📸 Foto do Produto** ali em cima no Bloco 17 primeiro!")
    else:
        with st.spinner(f"🧬 Escaneando Dor & Solução e forjando Criação V9.2 com Logo '{logo_ativa_usuario}'..."):
            try:
                img_b64_v92 = base64.b64encode(img_produto.getvalue()).decode('utf-8')
                scan_v92 = escanear_dor_e_contagem_da_foto(img_b64_v92)
                gancho_sorteado_v92 = selecionar_gancho_v11()
                direcao_v11_92 = selecionar_direcao_fisica_v11(email_sessao, "v9.2")

                instrucao_v92 = f"""
                Atue como a ENTIDADE V9.2 (Protocolo O.U.R.O.), conectada diretamente ao BANCO DE MEMÓRIA 17.3 abaixo:

                {BANCO_DE_MEMORIA_17_3_ATIVO_V1682}

                🔍 [DIAGNÓSTICO DE NEUROMARKETING EXTRAÍDO DA FOTO ENVIADA]:
                - Produto/Kit: {scan_v92.get('nome_pt')}
                - Quantidade Exata de Unidades na Foto: {scan_v92.get('qtd')} unidade(s)
                - Tipo de Embalagem/Peça: {scan_v92.get('tipo_embalagem')}
                - A DOR VISCERAL QUE ELE RESOLVE (ATAQUE ISSO NOS PRIMEIROS 2 SEGUNDOS!): {scan_v92.get('dor_pt')}
                - A SENSAÇÃO / TRANSFORMAÇÃO REAL QUE ELE ENTREGA: {scan_v92.get('solucao_pt')}
                - ÂNGULO DE GANCHO SORTEADO PARA HOJE: {gancho_sorteado_v92}
                - REGRA OBRIGATÓRIA DE POSICIONAMENTO NA IMAGEM: {scan_v92.get('regra_pos_img')}
                - REGRA OBRIGATÓRIA DE POSICIONAMENTO NO VÍDEO (DO INÍCIO AO FIM): {scan_v92.get('regra_pos_vid')}

                🚨 [REGRAS INQUEBRÁVEIS V9.2]:
                1. LEMA 'DOR -> SENSAÇÃO -> SOLUÇÃO': Na fala da {nome_inf_ativa}, é PROIBIDO soar como vendedor ou comercial fraco! Comece colocando o dedo na ferida (`{scan_v92.get('dor_pt')}`), entregue a sensação visceral do resultado (`{scan_v92.get('solucao_pt')}`) com tom de amiga fofoqueira urgente, e feche com convite natural à sacolinha, sem alegar lote ou oferta inexistente!
                2. Preserve exatamente o AMBIENTE ELEVO escolhido (ou sorteado), com planta, baguncinha e um animal ao fundo; a FOTO anexada é referência exclusiva para o PRODUTO, nunca para o cenário. NÃO descreva fisicamente o produto em texto.
                3. Se houver {scan_v92.get('qtd')} unidades na foto, mantenha quantidade e identidade; apoio manual apenas se o tamanho real permitir, demais na bancada; nenhuma pode desaparecer ao mudar enquadramento.
                4. Mantenha produto, apresentadora e ambiente fisicamente consistentes até o último frame. NÃO inserir logo extra, glitch ou quadro preto. A marca original da embalagem deve permanecer intacta.

                ENTREGUE EXATAMENTE NESTE FORMATO EM 3 SEÇÕES:

                ### 📸 PROMPT DE IMAGEM
                RAW photography, cinematic macro mid-shot POV erratic handheld mobile phone selfie, framing from chest up. Extreme V9 hyper-realism: microscopic visible peach fuzz, heavily dilated pupils, visceral breathing with chest slightly heaving, natural glowing micro-sweat on the collarbone, advanced subsurface scattering, authentic lighting matching the chosen ÉLÉVO environment, NO artificial flash. The photorealistic adult Brazilian woman ({nome_inf_ativa}: {desc_inf_ativa}) with a natural expression appropriate to her selected persona, performing believable everyday UGC delivery. [SELECTED PERSONA LOCK: keep the selected adult influencer's precise hairstyle, age, face, skin tone, wardrobe and emotional style; DO NOT impose bangs or different facial features. If a microphone is present it must look plausible]. Hair and skin retain believable natural texture, consistent with the chosen profile; don't change their appearance as a fake proof of the product. She occupies EXACTLY the selected 21-environment preset, preserving its actual geometry, decorations, lived-in objects, single background animal and plants; do not replace it with a generic tropical room. [CRITICAL PIXEL-PERFECT CLONE LOCK & SCALING]: [CRITICAL: 1:1 real-world scale, strictly realistic source-photo proportions and human-hand-relative scale, never forcibly oversized or artificially compact; no product appearance descriptors]. {scan_v92.get('regra_pos_img')} [BRANDING INTEGRITY LOCK]: All text and graphics preserved accurately. [ABSOLUTE UI LOCK]: ABSOLUTE ZERO watermarks, ABSOLUTE ZERO social media interface, ABSOLUTE ZERO platform logos, ABSOLUTE ZERO floating usernames anywhere in the frame. [NATURE MATRIX ACTIVE (DENSE)]: [Describe ONLY the real plant(s) defined by the selected environment, correctly lit and positioned]. [BAGUNCINHA TEMÁTICA (CHAOS V9)]: [Describe the selected environment original lived-in everyday clutter with plausible contact and inertia]. [ANIMAL FACTOR (STORYTELLING V9)]: [Include ONLY the single cat or dog defined by the selected environment in an unobtrusive background position]. High-contrast, cinematic atmospheric shadows, natural phone-sensor grain, true-to-reference material texture and original scene geometry from the selected ÉLÉVO preset; only scene-defined objects, realistic contact shadow.

                ### 🎬 PROMPT DE VÍDEO COMPLETO E UNIFICADO
                [RAW SMARTPHONE FOOTAGE, 9:16, single continuous scene, naturally stable handheld camera, authentic texture and lighting, same original environmental colors and layout. Preserve the EXACT product photographed: {scan_v92.get('regra_pos_vid')}. Keep the original container, brand, proportions, reflections, print, label orientation and count constant through every frame. 0:00-0:03: medium-close product shot at natural scale, supported by hand or solid counter, realistic gravity, contact shadow and occlusion. One small physically plausible finger tap only if the product is touched. 0:03-0:06: smooth gentle camera reframing to {nome_inf_ativa} ({desc_inf_ativa}), with the original product remaining visible; no whip pan, no aggressive zoom, no hidden product switch. 0:06-0:08: natural speech, tiny facial movements and quiet breathing, realistic pores and individual hair strands. 0:08-0:10: presenter holds or displays the SAME product in stable focus, original setting visible, no cuts to black, no fade, no digital glitch, no additional logos, no 3D shopping bag, no overlays. Preserve exact physics: hand-product grasp, rigid-body geometry, surface friction, gravity, stable relative coordinates, plausible light, material roughness, cast/contact shadows and depth of field. Every product stays visible, especially the very last frame. NO watermarks, no platform UI. Realistic smartphone recording rather than CGI or a commercial render.]

                🎙️ Áudio (Gancho V9.2 — Exatos 9 Segundos):
                (Abre em 0.0s com micro-efeito ASMR do produto/ambiente e um suspiro de advertência).
                "[Micro-efeito ASMR + Suspiro] [ESCREVA EM PORTUGUÊS A FALA LETAL DE EXATOS 9 SEGUNDOS (18 A 25 PALAVRAS) APLICANDO '{gancho_sorteado_v92}': COMECE ATACANDO A DOR '{scan_v92.get('dor_pt')}', ENTREGUE A SENSAÇÃO '{scan_v92.get('solucao_pt')}' COM PROXIMIDADE DE AMIGA E FECHE COM UM CONVITE À SACOLINHA, SEM ESTOQUE OU PROMOÇÃO INVENTADOS, ZERO PREÇO NUMÉRICO]"

                📝 Texto na Tela (Nativo TikTok - Foco na Dor):
                "⚠️ [PERGUNTA CURTA E AFIADA SOBRE A DOR]? 🛑"
                "[SENSAÇÃO / RESULTADO IMEDIATO] ✨"
                "CORRE NA SACOLINHA 🛒👇"

                Finalização P1 Blindada:
                Último quadro natural com produto, mãos e cenário preservados. Sem glitch, sem tela preta, sem logotipo adicional.

                ### 🔑 TÍTULOS SEO (Separados)
                **🔍 Geral (Dor):** [Título SEO Geral em português focado na dor '{scan_v92.get('dor_pt')}']
                **💡 Solução (Produto):** [Título SEO Solução em português descrevendo o produto/kit completo]
                **🏷️ Marca (Resenha):** [Título SEO De Marca em português com nome exato do produto/kit e marca]
                """

                instrucao_v92 += (f"\n\n[SELECTED PERSONA LOCK — IMAGEM, VÍDEO E VOZ] "
                                  f"{nome_inf_ativa}: {desc_inf_ativa}. "
                                  "Reproduza a MESMA identidade adulta no prompt de imagem, "
                                  "vídeo, emoção, expressão, voz e gestos. Nunca trocar de apresentadora.")
                if explicacao_video_usuario and explicacao_video_usuario.strip():
                    instrucao_v92 += f"\n\nDIRETRIZ EXTRA DO USUÁRIO: {explicacao_video_usuario.strip()}"

                instrucao_v92 += ("\n\nNOTA DE VARIEDADE (NÃO REESCREVER O MOLDE DE IMAGEM): "
                                  "Mantenha íntegro o estilo RAW V9.2 do prompt de imagem. "
                                  "A presença discreta de UM gato ou cachorro compatível com o cenário é obrigatória no primeiro frame gerado. "
                                  "Se existir animal, escolha espécie/ação compatível com o cenário e diferente das recentes; "
                                  "preserve exatamente o único animal da ficha de ambiente e a baguncinha orgânica no mesmo lugar em imagem/vídeo. Preserve natureza, ambiente orgânico e textura realistas. "
                                  f"Referência opcional desta rodada: {direcao_v11_92['animal']}.")
                if direcao_v11_92.get('escolhido'):
                    instrucao_v92 += ("\n\n[AMBIENTE ESCOLHIDO PELO USUÁRIO — TRAVA INEGOCIÁVEL]\n"
                                      + direcao_v11_92['trava_ambiente']
                                      + "\nOverride all random and tropical backdrops from the historical example. "
                                        "Use exactly this set for the still image and video, never replace it with "
                                        "generic ferns, a waterfall, a kitchen or an animal that was not selected.")
                instrucao_v92 += "\n\nREGRA FINAL INEGOCIÁVEL: " + PROTOCOLO_FISICO_17 + "\n\n" + DIRETRIZES_VIDA_REAL_V1682 + "\n\n" + TRAVA_PRODUTO_FOTO_V1682
                validar_cota_ia()
                resp_v92 = cliente_openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Você é a Entidade V9.2 Master. Seu lema inegociável: 'Nós não vendemos produtos, nós resolvemos problemas, atacamos a dor visceral, entregamos a sensação do desejo e geramos proximidade de amiga confidente'. Preserve a estrutura 17.3, mas ignore produtos e identidades dos exemplos históricos; foto separada determina o produto e influencer selecionada determina só a pessoa."},
                        {"role": "user", "content": instrucao_v92}
                    ],
                    max_tokens=6500,
                    temperature=0.75
                )

                conteudo_v92 = resp_v92.choices[0].message.content.strip()
                conteudo_v92 = fixar_ambiente_ambos_prompts_v165(
                    conteudo_v92, direcao_v11_92.get('escolhido',''), st.session_state.get('elevo_ambiente_obs',''))
                conteudo_v92 = reforcar_apenas_video_v12(conteudo_v92, scan_v92, "v9.2")
                conteudo_v92 = fixar_trava_produto_ambos_prompts_v1682(conteudo_v92)
                st.session_state["roteiro_temporario"] = conteudo_v92
                salvar_roteiro_no_drive(email_sessao, conteudo_v92)

                if not E_O_CEO and aba_limites is not None:
                    try: aba_limites.append_row([email_sessao, "Sim_V92"])
                    except Exception: pass

                st.success(f"🔥 Pacote Criação V9.2 (Gancho Dor & Solução + Logo '{logo_ativa_usuario}') Forjado com Sucesso!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error("A solicitação não pôde ser concluída. Verifique a conexão ou sua cota de IA.")

# ==========================================================
# EXIBIÇÃO UNIFICADA DO ROTEIRO (COM TODOS OS 5 BOTÕES DE CÓPIA ORIGINAIS)
# ==========================================================
if st.session_state["roteiro_temporario"]:
    with st.container(border=True):
        partes_roteiro = extrair_blocos_roteiro(st.session_state["roteiro_temporario"])
        
        if partes_roteiro["prompt_imagem"] and partes_roteiro["prompt_video"]:
            # 1. SEÇÃO PROMPT DE IMAGEM + BOTÃO À DIREITA
            col_tit_img, col_btn_img = st.columns([7, 3])
            with col_tit_img:
                st.markdown("### 📸 PROMPT DE IMAGEM")
            with col_btn_img:
                render_botao_copiar_vip(partes_roteiro["prompt_imagem"], "📋 Copiar Imagem", "copy_img_360")
            
            st.markdown(partes_roteiro["prompt_imagem"])
            st.divider()
            
            # 2. SEÇÃO PROMPT DE VÍDEO (ATÉ TEXTO NA TELA) + BOTÃO À DIREITA
            col_tit_vid, col_btn_vid = st.columns([7, 3])
            with col_tit_vid:
                st.markdown("### 🎬 PROMPT DE VÍDEO COMPLETO E UNIFICADO")
            with col_btn_vid:
                render_botao_copiar_vip(partes_roteiro["prompt_video"], "📋 Copiar Vídeo", "copy_vid_360")
                
            qtd_caracteres_video = len(partes_roteiro["prompt_video"])
            qtd_caracteres_visuais = _direcao_visual_caracteres_v12(partes_roteiro["prompt_video"])
            st.caption(f"🎞️ Vídeo V14: {qtd_caracteres_visuais:,} caracteres de direção visual | total {qtd_caracteres_video:,} | imagem original preservada | ecossistema vivo".replace(",", "."))
            st.markdown(partes_roteiro["prompt_video"], unsafe_allow_html=False)
            st.divider()
            
            # 3. SEÇÃO TÍTULOS SEO + BOTÃO 1, BOTÃO 2, BOTÃO 3 EMBAIXO
            st.markdown("### 🔑 TÍTULOS SEO (Separados)")
            st.markdown(partes_roteiro["secao_seo_texto"])
            
            st.markdown("<p style='font-size: 0.85rem; color: #00E5FF; font-weight: 600; margin-top: 10px; margin-bottom: 5px;'>📲 Cópia Rápida de Títulos (Celular/PC):</p>", unsafe_allow_html=True)
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                render_botao_copiar_vip(partes_roteiro["titulo_1"], "📋 Botão 1 (Título 1)", "copy_t1")
            with col_t2:
                render_botao_copiar_vip(partes_roteiro["titulo_2"], "📋 Botão 2 (Título 2)", "copy_t2")
            with col_t3:
                render_botao_copiar_vip(partes_roteiro["titulo_3"], "📋 Botão 3 (Título 3)", "copy_t3")
        else:
            st.markdown(st.session_state["roteiro_temporario"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Limpar Roteiro Atual", use_container_width=True, key="btn_limpar_roteiro_360"): 
            st.session_state["roteiro_temporario"] = None
            st.rerun()

st.markdown('<div id="academia"></div>', unsafe_allow_html=True)

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
