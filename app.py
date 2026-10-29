# ÉLÉVO V16.3 — TikTok OAuth opcional + perfil e vídeos, mantendo Aurora e os demais módulos.
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
}

def limpar_sessao_privada():
    for chave in list(st.session_state.keys()):
        if chave in SESSAO_DADOS_PRIVADOS or chave.startswith(("missao_", "input_", "audio_input_", "bv_login_", "tt_cache_", "tt_oauth_")):
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
# ÉLÉVO V16.3 | TikTok — LOGIN KIT OFICIAL, LIGAÇÃO DE CONTA
# Mantém autenticação ÉLÉVO separada. Nunca solicita senha TikTok.
# Requer aprovação TikTok for Developers e Secrets; sem isso o módulo
# aparece como "aguardando configuração", sem fingir estar conectado.
# ==========================================================
from urllib.parse import urlencode, urlparse

_TT_AUTORIZAR = "https://www.tiktok.com/v2/auth/authorize/"
_TT_TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"
_TT_REVOKE = "https://open.tiktokapis.com/v2/oauth/revoke/"
_TT_PERFIL = "https://open.tiktokapis.com/v2/user/info/"
_TT_VIDEOS = "https://open.tiktokapis.com/v2/video/list/"
_TT_COLUNAS = ["Elevo_Email", "TikTok_Open_ID", "Nome_TikTok",
               "Escopos", "Credenciais_Cifradas", "Atualizado_Em"]


def tt_config():
    """Somente configuração autorizada do app (nunca dados de login pessoais)."""
    chave = str(st.secrets.get("TIKTOK_CLIENT_KEY", "")).strip()
    segredo = str(st.secrets.get("TIKTOK_CLIENT_SECRET", "")).strip()
    retorno = str(st.secrets.get("TIKTOK_REDIRECT_URI", "")).strip()
    cifra = str(st.secrets.get("TIKTOK_TOKEN_ENCRYPTION_KEY", "")).strip()
    escopos = str(st.secrets.get("TIKTOK_SCOPES", "user.info.basic")).strip()
    escopos_lista = [s.strip() for s in escopos.split(",") if s.strip()]
    if "user.info.basic" not in escopos_lista:
        escopos_lista.insert(0, "user.info.basic")
    parsed = urlparse(retorno)
    configurado = bool(chave and segredo and cifra and
                       parsed.scheme == "https" and parsed.netloc and
                       not parsed.query and not parsed.fragment and robo_sheets)
    return {"key": chave, "secret": segredo, "redirect": retorno,
            "encrypt": cifra, "scopes": ",".join(dict.fromkeys(escopos_lista)),
            "enabled": configurado}


def tt_fernet(config):
    from cryptography.fernet import Fernet
    return Fernet(config["encrypt"].encode("ascii"))


def tt_sheet():
    if not robo_sheets:
        raise RuntimeError("Google Sheets indisponível")
    planilha = robo_sheets.open_by_key(re.search(r"/d/([a-zA-Z0-9-_]+)", LINK_BANCO_MESTRE).group(1))
    try:
        return planilha.worksheet("TikTok_Vinculos")
    except gspread.exceptions.WorksheetNotFound:
        aba = planilha.add_worksheet(title="TikTok_Vinculos", rows="1000", cols="6")
        aba.append_row(_TT_COLUNAS)
        return aba


def tt_registros():
    return tt_sheet().get_all_records()


def tt_localizar(email):
    registros = [(i, r) for i, r in enumerate(tt_registros(), start=2)
                 if str(r.get("Elevo_Email", "")).strip().lower() == email]
    if len(registros) > 1:
        raise RuntimeError("Cadastro TikTok duplicado. Revisar a planilha antes de continuar.")
    return registros[0] if registros else (None, None)


def tt_salvar(email, dados_token, perfil, config):
    """Tokens ficam cifrados no banco e nunca seguem para HTML / downloads."""
    open_id = str(dados_token.get("open_id", ""))
    if not open_id or not dados_token.get("access_token") or not dados_token.get("refresh_token"):
        raise RuntimeError("O TikTok não devolveu os dados necessários para manter o vínculo.")
    aba = tt_sheet()
    existentes = aba.get_all_records()
    for i, item in enumerate(existentes, start=2):
        outro_dono = str(item.get("Elevo_Email", "")).strip().lower()
        outro_id = str(item.get("TikTok_Open_ID", ""))
        if outro_id == open_id and outro_dono != email:
            raise RuntimeError("Esta conta TikTok já foi vinculada a outro usuário ÉLÉVO.")
        if outro_dono == email and outro_id and outro_id != open_id:
            raise RuntimeError("Desconecte a conta TikTok anterior antes de vincular outra.")
    payload = dict(dados_token)
    payload.setdefault("expires_in", 86400)
    payload["access_expires_at"] = int(time.time()) + int(payload["expires_in"])
    payload["refresh_expires_at"] = int(time.time()) + int(payload.get("refresh_expires_in", 0))
    token_cifrado = tt_fernet(config).encrypt(json.dumps(payload).encode("utf-8")).decode("ascii")
    linha = [email, open_id, str(perfil.get("display_name") or "Conta TikTok"),
             str(payload.get("scope", "")), token_cifrado,
             datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")]
    idx, _ = tt_localizar(email)
    if idx:
        aba.update(range_name=f"A{idx}:F{idx}", values=[linha])
    else:
        aba.append_row(linha)


def tt_token_request(config, parametros):
    resposta = requests.post(_TT_TOKEN, data={"client_key": config["key"],
                                   "client_secret": config["secret"], **parametros}, timeout=15)
    resposta.raise_for_status()
    dados = resposta.json()
    if dados.get("error") or not dados.get("access_token"):
        raise RuntimeError("TikTok não autorizou o token solicitado.")
    return dados


def tt_api(rota, token, campos, *, metodo="get", corpo=None):
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    params = {"fields": campos}
    if metodo == "post":
        resp = requests.post(rota, params=params, headers=headers, json=corpo or {}, timeout=15)
    else:
        resp = requests.get(rota, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    dados = resp.json()
    erro = dados.get("error", {})
    if isinstance(erro, dict) and erro.get("code") not in (None, "ok", 0):
        raise RuntimeError("O TikTok recusou a consulta. Revise as permissões do aplicativo.")
    return dados.get("data", {}) or {}


def tt_obter_token_valido(email, config):
    _, registro = tt_localizar(email)
    if not registro:
        return None, None
    pacote = json.loads(tt_fernet(config).decrypt(
        str(registro["Credenciais_Cifradas"]).encode("ascii")).decode("utf-8"))
    if int(pacote.get("access_expires_at", 0)) <= int(time.time()) + 120:
        if int(pacote.get("refresh_expires_at", 0)) <= int(time.time()) + 120:
            raise RuntimeError("A autorização TikTok expirou. Desconecte e vincule novamente.")
        antigo_id = str(pacote.get("open_id", ""))
        novo = tt_token_request(config, {"grant_type": "refresh_token",
                                         "refresh_token": pacote["refresh_token"]})
        if novo.get("open_id") != antigo_id:
            raise RuntimeError("A conta retornada pelo TikTok não corresponde ao vínculo salvo.")
        # TikTok pode rotacionar o refresh token: persistir o novo imediatamente.
        novo.setdefault("refresh_token", pacote["refresh_token"])
        novo.setdefault("refresh_expires_in", max(0, int(pacote.get("refresh_expires_at", 0)) - int(time.time())))
        tt_salvar(email, novo, {"display_name": registro.get("Nome_TikTok", "")}, config)
        pacote = {**novo, "access_expires_at": int(time.time()) + int(novo.get("expires_in", 86400)),
                  "refresh_expires_at": int(time.time()) + int(novo.get("refresh_expires_in", 0))}
    return pacote, registro


def tt_perfil(token, escopos):
    campos = ["open_id", "display_name", "avatar_url"]
    if "user.info.stats" in escopos:
        campos += ["follower_count", "likes_count", "video_count"]
    return tt_api(_TT_PERFIL, token, ",".join(campos)).get("user", {})


def tt_ultimos_videos(token):
    campos = "id,title,video_description,create_time,share_url,view_count,like_count,comment_count,share_count"
    dados = tt_api(_TT_VIDEOS, token, campos, metodo="post", corpo={"max_count": 20})
    return dados.get("videos", []) or []


def tt_link_autorizacao(email, config):
    # Mesmo navegador: state deve coincidir com nonce em cookie cifrado, com TTL.
    nonce = "tt_" + secrets.token_urlsafe(24)
    cookies["tt_oauth_pendente"] = json.dumps({"nonce": nonce,
                                               "email": email,
                                               "criado": int(time.time())})
    cookies.save()
    return _TT_AUTORIZAR + "?" + urlencode({
        "client_key": config["key"], "response_type": "code",
        "scope": config["scopes"], "redirect_uri": config["redirect"],
        "state": nonce,
    })


def tt_processar_retorno(config):
    estado = str(st.query_params.get("state", ""))
    if not estado.startswith("tt_"):
        return
    codigo = str(st.query_params.get("code", ""))
    erro = str(st.query_params.get("error", ""))
    # Remover código de uso único da URL imediatamente; não imprimir/logar tokens.
    for parametro in ("code", "state", "scopes", "error", "error_description"):
        if parametro in st.query_params:
            del st.query_params[parametro]
    pendente_json = cookies.get("tt_oauth_pendente", "")
    cookies.pop("tt_oauth_pendente", None)  # one-shot, inclusive após falha
    cookies.save()
    try:
        pendente = json.loads(pendente_json)
        if not config["enabled"] or not hmac.compare_digest(estado, str(pendente.get("nonce", ""))):
            raise RuntimeError("Autorização expirada ou iniciada em outro navegador.")
        if int(time.time()) - int(pendente.get("criado", 0)) not in range(0, 601):
            raise RuntimeError("A autorização expirou após 10 minutos. Tente novamente.")
        email_atual = str(st.session_state.get("email_usuario", "")).lower()
        if not st.session_state.get("usuario_logado") or email_atual != pendente.get("email"):
            raise RuntimeError("Faça login na mesma conta ÉLÉVO que iniciou a vinculação.")
        if erro or not codigo:
            raise RuntimeError("O TikTok não concedeu a autorização. Tente novamente.")
        token = tt_token_request(config, {"code": codigo,
                                            "grant_type": "authorization_code",
                                            "redirect_uri": config["redirect"]})
        perfil = tt_perfil(token["access_token"], set(str(token.get("scope", "")).split(",")))
        if not perfil.get("open_id") or perfil["open_id"] != token.get("open_id"):
            raise RuntimeError("A identidade retornada pelo TikTok não pôde ser validada.")
        tt_salvar(email_atual, token, perfil, config)
        for chave in ("tt_cache_email", "tt_cache_resultado", "tt_cache_instante"):
            st.session_state.pop(chave, None)
        st.session_state["tt_oauth_aviso"] = "✅ Conta TikTok vinculada com autorização oficial!"
    except Exception as e:
        # Erros técnicos podem conter informações sensíveis: não mostrar traceback.
        st.session_state["tt_oauth_aviso"] = "⚠️ Não foi possível vincular: " + str(e)[:180]


TT_CONFIG = tt_config()
# Callback exige sessão do ÉLÉVO autenticada; não cria login por conta própria.
tt_processar_retorno(TT_CONFIG)

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
  #elevo-dashboard-top,#painel,#missoes,#radar,#aurora,#criacao,#academia,#tiktok {{scroll-margin-top:75px;}}
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
  <a href="#tiktok">◈ Conectar TikTok</a>
  <a href="#aurora">✧ Aurora IA</a>
  <div class="secao">CRIATIVIDADE</div>
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
      <a href="#tiktok">◈ TikTok<span>Vincular e consultar desempenho</span></a>
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
# TIKTOK INTELLIGENCE — VINCULAR CONTA E IMPORTAR DADOS REAIS
# OAuth somente para CONECTAR TikTok ao ÉLÉVO, não substitui login ÉLÉVO.
# As APIs de perfil/vídeos NÃO expõem vendas e comissão de afiliados.
# ==========================================================
st.markdown('<div id="tiktok"></div>', unsafe_allow_html=True)
st.markdown("### ◈ TikTok Intelligence")
st.caption("Conecte a conta TikTok ao ÉLÉVO para consultar o perfil e os vídeos autorizados. "
           "Vendas e comissões do TikTok Shop exigem aprovação de uma API separada.")

tt_aba_conexao, tt_aba_desempenho, tt_aba_comercial = st.tabs(
    ["🔗 Vincular conta", "📊 Desempenho", "🛒 Vendas e comissões"])

tt_email = str(st.session_state.get("email_usuario", "")).strip().lower()
if "tt_oauth_aviso" in st.session_state:
    st.info(st.session_state.pop("tt_oauth_aviso"))

with tt_aba_conexao:
    if not TT_CONFIG["enabled"]:
        st.warning("Conexão TikTok aguardando configuração oficial pelo administrador.")
        st.markdown("**Necessário:** TikTok Login Kit, Client Key, Client Secret, "
                    "Redirect URI HTTPS e chave de criptografia nos Secrets do Streamlit.")
        st.caption("Não informe sua senha do TikTok no ÉLÉVO. A autorização ocorrerá no site oficial.")
        st.link_button("Abrir TikTok for Developers", "https://developers.tiktok.com/", use_container_width=False)
    else:
        try:
            tt_idx, tt_registro = tt_localizar(tt_email)
            if tt_registro:
                st.success("TikTok conectado a esta conta ÉLÉVO.")
                st.write("**Conta TikTok:** " + str(tt_registro.get("Nome_TikTok") or "Perfil vinculado"))
                st.caption("Permissões concedidas: " + str(tt_registro.get("Escopos") or "não informadas"))
                st.caption("Última autorização: " + str(tt_registro.get("Atualizado_Em") or "—"))
                if st.button("Desconectar TikTok", key="tt_btn_desconectar"):
                    try:
                        tt_pacote, _ = tt_obter_token_valido(tt_email, TT_CONFIG)
                        rev = requests.post(_TT_REVOKE, data={"client_key": TT_CONFIG["key"],
                                "client_secret": TT_CONFIG["secret"],
                                "token": tt_pacote["access_token"]}, timeout=15)
                        rev.raise_for_status()
                        if rev.text.strip():
                            retorno_rev = rev.json()
                            if retorno_rev.get("error"):
                                raise RuntimeError("TikTok não confirmou a revogação.")
                        tt_sheet().delete_rows(tt_idx)
                        for k in ("tt_cache_email", "tt_cache_resultado", "tt_cache_instante"):
                            st.session_state.pop(k, None)
                        st.success("Permissão revogada e vínculo removido.")
                        st.rerun()
                    except Exception:
                        st.error("Não foi possível revogar a autorização no TikTok. "
                                 "Tente novamente ou retire a permissão nas configurações da conta TikTok.")
            else:
                st.write("Autorize com sua conta TikTok usando o Login Kit oficial.")
                st.caption("Você será encaminhado ao TikTok e retornará ao ÉLÉVO após autorizar.")
                # Cookie cifrado para associar retorno ao navegador e à conta ÉLÉVO.
                try:
                    url_tt = tt_link_autorizacao(tt_email, TT_CONFIG)
                    st.link_button("◈ VINCULAR MINHA CONTA TIKTOK", url_tt,
                                   use_container_width=True, type="primary")
                except Exception:
                    st.error("Não foi possível iniciar a autorização. Revise a configuração do administrador.")
        except Exception:
            st.warning("O banco de vínculos do TikTok está indisponível. Tente novamente.")

with tt_aba_desempenho:
    if not TT_CONFIG["enabled"]:
        st.info("Os dados reais aparecerão após a configuração do aplicativo TikTok e a autorização da conta.")
    else:
        try:
            pacote, registro = tt_obter_token_valido(tt_email, TT_CONFIG)
            if not registro:
                st.info("Vincule primeiro sua conta na aba 'Vincular conta'.")
            else:
                autorizado = {p.strip() for p in str(pacote.get("scope", "")).split(",")}
                tem_videos = "video.list" in autorizado
                st.caption("Exibe somente o que as permissões oficiais liberam. "
                           "Sincroniza ao abrir e reutiliza dados por até 10 minutos nesta sessão.")
                forcar = st.button("↻ Sincronizar dados agora", key="tt_btn_sync")
                cache_ok = (st.session_state.get("tt_cache_email") == tt_email
                            and time.time() - st.session_state.get("tt_cache_instante", 0) < 600)
                if forcar or not cache_ok:
                    with st.spinner("Consultando TikTok oficial..."):
                        perfil_tt = tt_perfil(pacote["access_token"], autorizado)
                        videos_tt = tt_ultimos_videos(pacote["access_token"]) if tem_videos else []
                    st.session_state["tt_cache_email"] = tt_email
                    st.session_state["tt_cache_resultado"] = {"perfil": perfil_tt, "videos": videos_tt}
                    st.session_state["tt_cache_instante"] = time.time()
                tt_dados = st.session_state["tt_cache_resultado"]
                tt_per = tt_dados.get("perfil", {})
                st.markdown("**Perfil:** " + html_std.escape(str(tt_per.get("display_name") or registro.get("Nome_TikTok") or "TikTok")))
                if "follower_count" in tt_per:
                    st.metric("Seguidores", f'{int(tt_per.get("follower_count") or 0):,}'.replace(",", "."))
                if not tem_videos:
                    st.info("Perfil conectado. Para exibir vídeos e visualizações, o administrador "
                            "deve obter aprovação da permissão `video.list` e reconectar a conta.")
                else:
                    tt_vids = tt_dados.get("videos", [])
                    if not tt_vids:
                        st.info("Nenhum vídeo público foi retornado para esta consulta.")
                    else:
                        views = sum(int(v.get("view_count") or 0) for v in tt_vids)
                        likes = sum(int(v.get("like_count") or 0) for v in tt_vids)
                        compartilhamentos = sum(int(v.get("share_count") or 0) for v in tt_vids)
                        a, b, c = st.columns(3)
                        a.metric("Views (vídeos listados)", f"{views:,}".replace(",", "."))
                        b.metric("Curtidas", f"{likes:,}".replace(",", "."))
                        c.metric("Compartilhamentos", f"{compartilhamentos:,}".replace(",", "."))
                        st.caption("Totais limitados aos últimos 20 vídeos públicos retornados; "
                                   "não são o alcance total da conta nem o funil de vendas.")
                        linhas = [{"Vídeo": str(v.get("title") or v.get("video_description") or "Sem título")[:100],
                                   "Visualizações": int(v.get("view_count") or 0),
                                   "Curtidas": int(v.get("like_count") or 0),
                                   "Comentários": int(v.get("comment_count") or 0),
                                   "Compartilhamentos": int(v.get("share_count") or 0),
                                   "Link": str(v.get("share_url") or "")}
                                  for v in tt_vids]
                        df_tiktok = pd.DataFrame(linhas)
                        st.dataframe(df_tiktok, use_container_width=True, hide_index=True)
                        st.download_button("Baixar relatório dos vídeos (CSV)",
                             data=df_tiktok.to_csv(index=False).encode("utf-8-sig"),
                             file_name="elevo_tiktok_videos.csv", mime="text/csv",
                             key="tt_download_videos")
        except Exception:
            st.warning("Não foi possível consultar TikTok neste momento. "
                       "Revise a autorização, a conexão de rede e os Secrets.")

with tt_aba_comercial:
    st.info("Vendas, pedidos, cliques nos produtos e comissões de afiliados **não são fornecidos** "
            "pela API de perfil/vídeos do TikTok. Eles não serão inventados no ÉLÉVO.")
    st.markdown("Para sincronizar esses números de forma automática, será necessária "
                "aprovação específica da **TikTok Shop Affiliate API** e a autorização da conta "
                "TikTok Shop. Até lá, o painel financeiro do ÉLÉVO continua usando seus dados existentes.")
    st.link_button("Informações oficiais sobre TikTok Shop Affiliate API",
                   "https://partner.tiktokshop.com/docv2/page/affiliate-integration")

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

st.markdown('<div id="aurora"></div>', unsafe_allow_html=True)

# ==========================================================
# 15. AURORA VOICE CONSOLE V16.2 — REFINAMENTO VISUAL ISOLADO
# Mantém st.audio_input, Whisper, contexto da Aurora e TTS existentes.
# ==========================================================
st.divider()
st.markdown("<div class='aurora-section-marker'>CANAL DE VOZ · ÉLÉVO AI</div>", unsafe_allow_html=True)

ID_VOZ_LAURA = "MLAEAegxkMReslK34j8T"

# Sem ElevenLabs, a voz utiliza gTTS como alternativa; não bloquear o app inteiro.
CHAVE_ELEVENLABS_VIP = str(st.secrets.get("ELEVENLABS_API_KEY", ""))

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

# Estilos limitados ao contêiner com chave: não atingem os demais microfones,
# players ou cartões do aplicativo.
st.markdown("""
<style>
.aurora-section-marker {
  max-width: 780px; margin: 20px auto 11px;
  font-size: .68rem; letter-spacing: .24em; font-weight: 800;
  text-align: center; color: #789bb8 !important;
}
.st-key-aurora_voice_console {
  --av-cyan: #32e5ff; --av-blue: #3d89ff; --av-ink: #e6f3ff;
  --av-muted: #8ba5bb; --av-stroke: rgba(73,169,233,.26);
  width: 100%; max-width: 780px; margin: 0 auto 28px !important;
  border: 1px solid var(--av-stroke) !important;
  border-radius: 24px !important;
  padding: clamp(17px, 3vw, 27px) !important;
  background:
    radial-gradient(ellipse at 75% -15%,rgba(28,120,215,.13),transparent 58%),
    linear-gradient(155deg,#101c2c 0%,#0b1524 62%,#09121e 100%) !important;
  box-shadow: 0 15px 45px rgba(0,0,0,.18), inset 0 1px rgba(191,230,255,.055) !important;
  overflow: hidden;
}
.st-key-aurora_voice_console [data-testid="stVerticalBlockBorderWrapper"] {
  background: transparent !important; box-shadow: none !important;
  border: none !important;
}
.st-key-aurora_voice_console [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
}
.aurora-voice-top {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 17px;
}
.aurora-voice-identity {display:flex;align-items:center;gap:12px;min-width:0}
.aurora-voice-monogram {
  width: 45px;height:45px; flex:none; border-radius:15px;display:grid;place-items:center;
  background:linear-gradient(145deg,rgba(55,148,252,.20),rgba(13,32,53,.80));
  border:1px solid rgba(73,178,250,.32);
  box-shadow:inset 0 1px rgba(255,255,255,.065);
}
.aurora-voice-monogram svg {height:27px;width:27px;stroke:#6ceaff;fill:none;stroke-width:1.5}
.aurora-voice-name {color:#ecf8ff;font-size:1.15rem;font-weight:850;letter-spacing:.02em;line-height:1.25}
.aurora-voice-sub {color:#8daac2;font-size:.7rem;letter-spacing:.12em;margin-top:2px}
.aurora-voice-online {
  display:flex;align-items:center;gap:7px;color:#9ddcc9;flex:none;
  font-size:.69rem;font-weight:700;letter-spacing:.06em;
  background:rgba(39,189,144,.065);border:1px solid rgba(56,213,163,.18);
  padding:8px 11px;border-radius:99px;
}
.aurora-voice-led {width:7px;height:7px;border-radius:50%;background:#3ce7a5;box-shadow:0 0 10px rgba(60,231,165,.6)}
.aurora-voice-stage {
  background:radial-gradient(ellipse at 50% 110%,rgba(20,103,185,.10),transparent 75%),rgba(2,12,25,.42);
  border:1px solid rgba(62,151,225,.13);border-radius:16px;
  min-height:113px;padding:16px 14px 12px;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:10px;margin-bottom:12px;
}
.aurora-voice-wave {
  display:flex;align-items:center;justify-content:center;gap:4px;
  min-height:42px; width:100%;max-width:450px;
}
.aurora-voice-wave::before,.aurora-voice-wave::after {
  content:"";height:1px;flex:1;max-width:55px;
  background:linear-gradient(90deg,transparent,rgba(48,172,239,.40));
}
.aurora-voice-wave::after{transform:rotate(180deg)}
.aurora-voice-wave i {
  display:block;width:3px;flex:0 0 3px;border-radius:10px;
  height:var(--av-h);background:linear-gradient(180deg,#74eeff,#1389d9);
  box-shadow:0 0 9px rgba(30,189,248,.29);
  animation:aurora-wave-breathe 1.85s ease-in-out infinite alternate;
  animation-delay:var(--av-d);transform-origin:center;
}
@keyframes aurora-wave-breathe {from{transform:scaleY(.6);opacity:.5}to{transform:scaleY(1.28);opacity:1}}
.aurora-voice-stage-caption{color:#c4d9ec;font-size:.79rem;font-weight:650;letter-spacing:.025em;text-align:center}
.aurora-voice-stage-helper{color:#7f9bb2;font-size:.69rem;text-align:center;margin-top:-6px}
.st-key-aurora_voice_console [data-testid="stAudioInput"] {
  max-width:540px;margin:0 auto !important;
  padding:11px 13px 10px !important;
  border:1px solid rgba(70,157,233,.25) !important;
  background:linear-gradient(120deg,rgba(17,41,68,.77),rgba(12,29,49,.8)) !important;
  border-radius:15px !important;
  box-shadow:none !important;
}
.st-key-aurora_voice_console [data-testid="stAudioInput"]:focus-within {
  border-color:#48caff !important; box-shadow:0 0 0 2px rgba(52,186,249,.12) !important;
}
.st-key-aurora_voice_console [data-testid="stAudioInput"] button {
  min-height:43px !important;border-radius:13px !important;
  background:linear-gradient(125deg,#075caa,#138edb) !important;
  border:1px solid #58c6ff !important;color:#fff !important;
  box-shadow:0 4px 18px rgba(9,120,222,.21) !important;
  font-weight:800 !important;
}
.st-key-aurora_voice_console [data-testid="stAudioInput"] button:hover {
  filter:brightness(1.16);transform:none !important;
}
.st-key-aurora_voice_console [data-testid="stAudioInput"] audio {
  display:block !important; width:100%;max-width:100%; color-scheme:dark;
}
.st-key-aurora_voice_console [data-testid="stAudioInput"] audio::-webkit-media-controls-panel {
  background-color:#233d54;
}
.aurora-voice-foot {
  text-align:center;color:#7898b4 !important;font-size:.71rem;
  margin:10px auto 0;max-width:560px;line-height:1.6;
}
@media(max-width:650px){
 .st-key-aurora_voice_console{border-radius:19px !important;padding:15px !important}
 .aurora-voice-top{align-items:flex-start;gap:7px}
 .aurora-voice-monogram{width:41px;height:41px}
 .aurora-voice-name{font-size:1rem}
 .aurora-voice-sub{font-size:.58rem}
 .aurora-voice-online{font-size:.62rem;padding:7px 8px}
 .aurora-voice-wave{gap:3px}
 .aurora-voice-wave i{width:2px;flex-basis:2px}
 .aurora-voice-stage{min-height:106px}
}
@media(prefers-reduced-motion:reduce){.aurora-voice-wave i{animation:none !important}}
</style>
""", unsafe_allow_html=True)

# O Streamlit permanece responsável pela gravação (sem gravador paralelo).
aurora_console = st.container(border=True, key="aurora_voice_console")
with aurora_console:
    st.markdown("""
    <div class="aurora-voice-top">
      <div class="aurora-voice-identity">
        <div class="aurora-voice-monogram" aria-hidden="true">
          <svg viewBox="0 0 28 28" aria-hidden="true">
            <path d="M4 16 L8 12 L11 19 L15 6 L18 22 L21 12 L24 16"/>
            <path d="M3 24H25" opacity=".3"/>
          </svg>
        </div>
        <div><div class="aurora-voice-name">Aurora <span style="color:#49b6ed;font-weight:500">/ Voice</span></div>
        <div class="aurora-voice-sub">INTELIGÊNCIA OPERACIONAL</div></div>
      </div>
      <div class="aurora-voice-online"><span class="aurora-voice-led"></span> CANAL ATIVO</div>
    </div>
    <div class="aurora-voice-stage">
      <div class="aurora-voice-wave" aria-hidden="true">
      """ + "".join(
          f'<i style="--av-h:{h}px;--av-d:{(i % 11) * -0.16:.2f}s"></i>'
          for i, h in enumerate([4,7,10,7,12,18,11,24,13,20,28,14,23,37,21,30,43,23,35,17,26,40,18,29,14,24,16,12,20,11,16,8,12,7,4])
      ) + """
      </div>
      <div class="aurora-voice-stage-caption">Pronta para ouvir sua próxima ideia</div>
      <div class="aurora-voice-stage-helper">Toque no microfone para gravar. Toque novamente para concluir.</div>
    </div>
    """, unsafe_allow_html=True)
    audio_gravado = st.audio_input(
        "Gravar mensagem de voz para a Aurora", label_visibility="collapsed",
        key="audio_input_aurora_unico"
    )
    st.markdown('<div class="aurora-voice-foot">Sua mensagem será transcrita e respondida pela Aurora. O envio continua automático ao terminar a gravação.</div>', unsafe_allow_html=True)

if audio_gravado is not None:
    audio_bytes = audio_gravado.read()
    if audio_bytes:
        audio_hash = hashlib.md5(audio_bytes).hexdigest()

        if audio_hash != st.session_state["ultimo_hash_audio"]:
            st.session_state["ultimo_hash_audio"] = audio_hash 

            with st.spinner("🦅 A Aurora está a analisar 100% da plataforma (Finanças, Missões, Funil, Conversão e Banco de Dados)..."):
                try:
                    validar_cota_ia()
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
                        - Você tem total acesso e vigilância sobre o Banco de Dados secreto no Google Sheets, que registra e-mails e hashes de senha (não contém senhas em texto puro). Atualmente há {total_usuarios} usuários cadastrados na base de dados.
                        - Você sabe que a plataforma usa "Cofres Secretos" para isolar os dados de cada afiliado/cliente (como a conta: {canal_ativo}).
                        - O STATUS DO CORAÇÃO DA EMPRESA agora é: NOTA {nota_atual} com {estado_atual} (crescimento de {crescimento_pct:+.1f}% vs semana anterior).
                        
                        [STATUS EM TEMPO REAL DE '{nome_usuario_atual}']:
                        💰 FINANCEIRO: Comissões registradas R$ {fat_total_global:,.2f} | Nos últimos 7 Dias: R$ {fat_7d:,.2f} (Evolução de {crescimento_pct:+.1f}%). 
                        🏆 Top 3 Produtos que mais venderam: {top_produtos_str}.
                        🎯 Missão de Hoje do usuário: {missao_hoje_str} | Disciplina nos últimos 30 dias: {dias_concluidos_str}/30 ({taxa_acerto_str:.1f}%).
                        🧠 Tendência do Mercado captada pelo Radar: {tendencia_atual}.
                        🧬 A Estratégia de Funil ativa: {funil_atual}.
                        🔬 Insights Laboratoriais: A Taxa de Conversão está em {conversao_atual:.2f}%. O público quer/tem medo de: {feedback_atual}.
                        
                        REGRA DE OURO: Não repita os números feito um papagaio. Use as métricas acima para parecer uma deusa omnisciente. Analise friamente se o usuário está com os números bons ou péssimos e dê-lhe conselhos táticos. Se perguntar sobre banco de dados, responda o número de usuários cadastrados com orgulho.
                        """

                        mensagens_api = [{"role": "system", "content": sistema_mentor}]
                        mensagens_api.extend(st.session_state["historico_viva_voz"])

                        validar_cota_ia()

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
                    st.error("A solicitação não pôde ser concluída. Verifique a conexão ou sua cota de IA.")

# ==========================================================
# AURORA / RESPOSTA V16.2 — WAVEFORM AZUL + CONTROLES PRÓPRIOS
# Mesmos bytes de áudio ElevenLabs/gTTS; somente a apresentação foi alterada.
# ==========================================================
if st.session_state["ultimo_audio_b64"]:
    audio_tocar = st.session_state["ultimo_audio_b64"]
    hash_atual = str(st.session_state.get("ultimo_hash_audio") or "")
    # Nunca misturar a chave de uma conta com outra no browser.
    identificador_audio = hashlib.sha256(
        (str(st.session_state.get("email_usuario", "")) + ":" + hash_atual).encode("utf-8")
    ).hexdigest()[:30]

    html_resposta = r"""
<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
*{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent;font-family:Montserrat,system-ui,Arial,sans-serif;color:#e8f7ff}
.player{margin:5px auto 0;max-width:710px;padding:17px 18px;background:linear-gradient(130deg,rgba(10,41,68,.96),rgba(9,26,45,.95));border:1px solid rgba(69,189,251,.29);border-radius:15px}
.heading{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:13px}
.name{font-size:.71rem;font-weight:850;letter-spacing:.13em;color:#67d9ff;text-transform:uppercase}
.pill{font-size:.63rem;font-weight:750;color:#96b9d2;border:1px solid rgba(69,189,251,.18);border-radius:40px;padding:5px 9px}
.row{display:flex;align-items:center;gap:13px;width:100%}
.toggle{width:45px;height:45px;flex:none;cursor:pointer;display:grid;place-items:center;border-radius:14px;background:linear-gradient(135deg,#085fa8,#178de0);border:1px solid rgba(116,228,255,.64);box-shadow:0 5px 17px rgba(14,126,214,.23);color:#fff;font-weight:800;font-size:1.1rem}
.toggle:hover{filter:brightness(1.15)}.toggle:focus-visible{outline:2px solid white;outline-offset:2px}
.visual{min-width:0;flex:1;display:flex;flex-direction:column;justify-content:center;gap:9px}
.bars{height:40px;display:flex;align-items:center;justify-content:space-between;gap:2px;overflow:hidden}
.bar{flex:1 1 2px;max-width:6px;min-width:2px;height:3px;min-height:3px;border-radius:6px;background:linear-gradient(180deg,#7fefff,#168ce1);opacity:.66;transform-origin:center;transition:height .10s ease,opacity .14s ease;box-shadow:0 0 6px rgba(36,198,255,.12)}
.player.playing .bar{opacity:.9}
.status{display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:.7rem;color:#94b4cd}
.clock{font-variant-numeric:tabular-nums;color:#c2e5ff}
.progress{height:3px;background:rgba(79,160,217,.13);border-radius:4px;overflow:hidden;margin-top:7px}
.progress>div{height:100%;width:0;background:linear-gradient(90deg,#2189e4,#60edff);transition:width .16s linear}
audio{display:none!important}
@media(max-width:540px){.player{padding:14px 12px}.pill{font-size:.56rem}.heading{gap:6px}.name{letter-spacing:.08em}.row{gap:9px}}
@media(prefers-reduced-motion:reduce){.bar{transition:none}}
</style></head><body>
<section class="player" id="player" aria-label="Resposta em áudio da Aurora">
  <div class="heading"><div class="name">AURORA / RESPOSTA EM VOZ</div><div class="pill" id="badge">PRONTA</div></div>
  <div class="row">
    <button class="toggle" type="button" id="toggle" aria-label="Reproduzir a resposta">▶</button>
    <div class="visual">
      <div class="bars" id="bars" aria-hidden="true"></div>
      <div class="status"><span id="status" role="status" aria-live="polite">Resposta pronta para ouvir</span><span class="clock" id="clock">00:00</span></div>
      <div class="progress"><div id="progress"></div></div>
    </div>
  </div>
  <audio id="voice" preload="auto" playsinline src="data:audio/mpeg;base64,__AUDIO_B64__"></audio>
</section>
<script>
(()=>{
 'use strict';
 const player=document.getElementById('player');
 const audio=document.getElementById('voice');
 const toggle=document.getElementById('toggle');
 const bars=document.getElementById('bars');
 const badge=document.getElementById('badge');
 const status=document.getElementById('status');
 const clock=document.getElementById('clock');
 const progress=document.getElementById('progress');
 const key='elevo_aurora_voice_v162___AUDIO_ID__';
 const heights=[4,7,12,8,22,13,32,21,15,35,11,26,37,18,12,29,39,24,16,31,10,20,33,14,7,26,17,9,21,12,5,18,9,4];
 const elements=heights.map(h=>{const span=document.createElement('i');span.className='bar';span.style.height=h+'px';bars.appendChild(span);return span;});
 let ctx=null, analyser=null, frequency=null, frame=0;
 const reduced=window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
 const fmt=n=>{if(!Number.isFinite(n))return '00:00';const v=Math.floor(n);return String(Math.floor(v/60)).padStart(2,'0')+':'+String(v%60).padStart(2,'0');};
 function initAnalyser(){
   if(reduced||ctx||!window.AudioContext && !window.webkitAudioContext)return;
   try{const AC=window.AudioContext||window.webkitAudioContext;ctx=new AC();analyser=ctx.createAnalyser();analyser.fftSize=128;const src=ctx.createMediaElementSource(audio);src.connect(analyser);analyser.connect(ctx.destination);frequency=new Uint8Array(analyser.frequencyBinCount);}catch(e){analyser=null;}
 }
 function draw(){
   cancelAnimationFrame(frame);
   if(audio.paused || audio.ended){elements.forEach((el,i)=>el.style.height=(4+heights[i]*.45)+'px');return;}
   if(analyser && frequency && !reduced){
     analyser.getByteFrequencyData(frequency);
     elements.forEach((el,i)=>{
       const idx=Math.floor(i/elements.length * Math.min(frequency.length,40));
       const level=frequency[idx]/255;
       el.style.height=(4+Math.max(level,0.04)*35)+'px';
     });
   }else if(!reduced){
     const t=performance.now()/220;
     elements.forEach((el,i)=>el.style.height=(5+Math.abs(Math.sin(t+i*.65))*heights[i]*.85)+'px');
   }
   frame=requestAnimationFrame(draw);
 }
 function showPlay(){player.classList.remove('playing');toggle.textContent='▶';toggle.setAttribute('aria-label','Reproduzir a resposta');}
 function showPause(){player.classList.add('playing');toggle.textContent='Ⅱ';toggle.setAttribute('aria-label','Pausar a resposta');}
 function start(userInitiated=false){
   // Criar o AudioContext apenas com gesto do usuário: autoplay em Chrome mobile pode silenciar contextos suspensos.
   if(userInitiated){initAnalyser();if(ctx && ctx.state==='suspended')ctx.resume().catch(()=>{});}
   const result=audio.play();
   if(result&&typeof result.catch==='function')result.catch(()=>{showPlay();badge.textContent='TOQUE PARA OUVIR';status.textContent='Toque em reproduzir para ouvir a Aurora';});
 }
 toggle.addEventListener('click',()=>{if(audio.paused||audio.ended){if(audio.ended)audio.currentTime=0;start(true);}else audio.pause();});
 audio.addEventListener('play',()=>{showPause();badge.textContent='TRANSMITINDO';status.textContent='Aurora está falando';try{sessionStorage.setItem(key,'iniciado')}catch(e){}draw();});
 audio.addEventListener('pause',()=>{showPlay();if(!audio.ended){badge.textContent='PAUSADA';status.textContent='Resposta pausada';}draw();});
 audio.addEventListener('ended',()=>{showPlay();badge.textContent='CONCLUÍDA';status.textContent='Mensagem concluída · toque para ouvir novamente';try{sessionStorage.setItem(key,'concluido')}catch(e){}draw();});
 audio.addEventListener('timeupdate',()=>{clock.textContent=fmt(audio.currentTime)+' / '+fmt(audio.duration);progress.style.width=(audio.duration?Math.min(100,audio.currentTime/audio.duration*100):0)+'%';});
 audio.addEventListener('loadedmetadata',()=>{clock.textContent='00:00 / '+fmt(audio.duration);});
 audio.addEventListener('error',()=>{showPlay();badge.textContent='INDISPONÍVEL';status.textContent='Falha ao carregar áudio · tente novamente';});
 // Tenta uma vez para cada nova resposta; ao reexecutar o app não repete um áudio já iniciado.
 let already=false;try{already=!!sessionStorage.getItem(key)}catch(e){}
 if(!already)start();else{badge.textContent='DISPONÍVEL';status.textContent='Toque em reproduzir para ouvir novamente';}
 window.addEventListener('pagehide',()=>{cancelAnimationFrame(frame);if(ctx)ctx.close().catch(()=>{});},{once:true});
})();
</script>
</body></html>
""".replace("__AUDIO_B64__", audio_tocar).replace("__AUDIO_ID__", identificador_audio)

    with aurora_console:
        components.html(html_resposta, height=169, scrolling=False)

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
    4) A regra limpa de posicionamento (1 na mão + o resto parado na bancada, SEM descrever cores para não bugar o vídeo).
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
    if qtd <= 1:
        regra_pos_img = (
            f"She is firmly holding ONE product, the EXACT {tipo_emb} from the provided reference image, in one hand. "
            f"DO NOT alter, redraw, or describe the product colors, logo, or text — copy the source reference image 100% intact."
        )
        regra_pos_vid = (
            f"holding the EXACT single {tipo_emb} from the reference image in one hand (DO NOT alter or describe colors/labels, copy reference 100% intact)."
        )
    else:
        resto = qtd - 1
        regra_pos_img = (
            f"[MULTI-PRODUCT KIT LOCK — {qtd} UNITS TOTAL]: She is firmly holding ONLY ONE unit of the kit in her hand, "
            f"while the other {resto} unit(s) from the reference image rest neatly side-by-side on the counter surface right next to her, "
            f"making all {qtd} products from the reference image clearly visible in the scene. DO NOT alter, redraw, or describe the product colors — copy all {qtd} units from the reference image 100% intact."
        )
        regra_pos_vid = (
            f"[MULTI-PRODUCT KIT LOCK — {qtd} UNITS TOTAL]: All {qtd} units from the reference image are clearly visible from 0:00 to the end, "
            f"with ONLY ONE unit held in her hand while the other {resto} unit(s) remain resting stationary on the counter surface right beside her "
            f"(NEVER hold all {qtd} units in her hands at the same time, and DO NOT alter or redraw the reference packaging)."
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
    nome_inf_ativa = "Aurora"
    desc_inf_ativa = "Photorealistic young Brazilian woman (Aurora: dark hair, subtle bangs, intense conspiratorial expression, incredibly shiny and healthy-looking hair)"
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
        "👤 Configurar Minha Influencer"
    ])
    
    with aba_gerador_360:
        if eh_customizada:
            st.info(f"✨ **Influencer Ativa no seu Login:** `{nome_inf_ativa}` — *{desc_inf_ativa}*")
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
        st.markdown("<h4 style='color: #00E5FF;'>🧬 Identidade Visual da Sua Influencer</h4>", unsafe_allow_html=True)
        st.caption("Configure as características físicas da sua personagem. Ela ficará gravada exclusivamente no seu login para todos os seus próximos vídeos.")
        
        if eh_customizada:
            st.success(f"✅ **Influencer Salva na Memória:** {nome_inf_ativa}")
            st.markdown(f"**Descrição Visual Aplicada:**\n> *{desc_inf_ativa}*")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 Trocar / Excluir Influencer Atual", type="secondary", use_container_width=True, key="btn_excluir_inf"):
                with st.spinner("Removendo influencer da memória para liberar novo cadastro..."):
                    gerenciar_influencer_usuario("excluir", email_sessao)
                    st.session_state["influencer_atual"] = None
                    st.success("🧹 Influencer removida! Agora você pode cadastrar uma nova abaixo.")
                    time.sleep(1)
                    st.rerun()
        else:
            if E_O_CEO:
                st.info("👑 **Modo CEO:** A sua influencer padrão (Aurora) já está ativa nativamente. Se quiser testar uma nova influencer temporária ou fixa, preencha abaixo e aplique:")
            
            novo_nome_inf = st.text_input("👤 Nome da sua Influencer:", placeholder="Ex: Maya, Valentina, Bia...", key="input_nome_inf")
            nova_desc_inf = st.text_area(
                "🎨 Descrição Visual Completa (Cabelo, Pele, Idade, Estilo, Expressão):",
                placeholder="Ex: Mulher brasileira jovem de 24 anos, pele morena iluminada, cabelos cacheados volumosos e brilhantes na altura dos ombros, olhos castanhos expressivos, usando uma camiseta básica branca, expressão de amiga fofoqueira...",
                height=130,
                key="input_desc_inf"
            )
            if st.button("💾 APLICAR E SALVAR INFLUENCER NO MEU LOGIN", type="primary", use_container_width=True, key="btn_salvar_inf"):
                if not novo_nome_inf.strip() or not nova_desc_inf.strip():
                    st.warning("⚠️ Preencha o nome e a descrição visual completa da sua influencer para aplicar no sistema!")
                else:
                    with st.spinner("Gravando a sua Influencer no banco de memória exclusivo do seu login..."):
                        if gerenciar_influencer_usuario("salvar", email_sessao, novo_nome_inf, nova_desc_inf, logo_ativa_usuario):
                            st.session_state["influencer_atual"] = {
                                "Email": email_sessao,
                                "Nome_Influencer": novo_nome_inf.strip(),
                                "Descricao_Visual": nova_desc_inf.strip(),
                                "Logo_Marca": logo_ativa_usuario
                            }
                            st.success(f"🔥 {novo_nome_inf} foi aplicada ao sistema e vinculada ao seu login!")
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
PROTOCOLO_FISICO_17 = "[PROTOCOLO FÍSICO REALISTA V10 — PRIORIDADE MÁXIMA; PREVALECE SOBRE MOLDES ANTIGOS]\n- CONSERVAÇÃO: mesmo número de produtos, identidade, altura, largura, volume, tampa, marca e rótulo em TODOS os quadros; não duplicar, fundir, deformar, trocar textura nem desaparecer. O objeto não teletransporta entre mão e bancada.\n- REFERÊNCIA FIXA: a imagem fornecida determina cor, embalagem, acabamento e cenário. Manter materiais existentes e a direção da luz; melhorar somente microtextura, detalhe de superfície, rugosidade, reflexos e definição naturais, sem trocar a paleta, nem cenário nem objetos.\n- CONTATO E GRAVIDADE: produto apoiado na bancada tem base em contato contínuo, sombra de contato consistente, gravidade, inércia e oclusão reais; produto na mão mantém posição estável, dedos anatomicamente corretos, pressão e oclusão coerentes, nenhuma interpenetração ou flutuação.\n- CÂMERA: celular realista, câmera principalmente estável, deslocamentos curtos e suaves; proibir zoom violento, whip-pan, tremor excessivo, troca brusca de foco, glare artificial. Profundidade de campo coerente sem ocultar itens essenciais.\n- PELE E MATERIAIS: poros finos, fios de cabelo individuais, rugosidade realista, leve assimetria; materiais com BRDF plausível, reflexos dependentes da iluminação real, sem brilho plástico ou nitidez falsa. Evitar hiperbolização da pele, do olhar ou da respiração.\n- AMBIENTE: plantas e tecidos se movem apenas se houver vento plausível; vapor e água só onde efetivamente existem na referência; sombras, reflexos, perspectiva, luz e exposição temporalmente contínuos. Não adicionar animais, bagunça, objetos ou cenários que não estejam na referência enviada.\n- FINAL: a partir de 0:08, a apresentadora mantém o produto perfeitamente visível em quadro; no último segundo, segurar imagem estável com produto e ambiente intactos até o último frame. PROIBIDO quadro preto, fade para preto, glitch, logo sobreposto, marca d'água, sacola 3D flutuante ou elementos duplicados. Logo original impressa na embalagem permanece; não acrescentar logo da empresa na imagem.\n- ÁUDIO/COPY: fala factível em 9 segundos (aprox. 18–25 palavras, ajustar à locução), sem afirmar benefícios não demonstrados no rótulo, escassez, preço ou estoque não confirmados. Texto de CTA pode ficar para edição fora do gerador; não gerar UI nativa.\n- Se um molde histórico conflitar com estas regras, este protocolo é soberano."

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


def selecionar_direcao_fisica_v11(email_usuario, modo):
    """Evita repetições imediatas de cenário, gancho e animal dentro da sessão."""
    historico = st.session_state.setdefault("historico_v11_cenas", [])
    disponiveis = [i for i in range(len(CENARIOS_V11)) if i not in historico[-8:]]
    indice = random.choice(disponiveis or list(range(len(CENARIOS_V11))))
    historico.append(indice)
    st.session_state["historico_v11_cenas"] = historico[-20:]
    nome, dinamica, animal = CENARIOS_V11[indice]
    # Quando os cenários não pedem animal, jamais forçar cachorro ou gato.
    return {
        "cenario": nome,
        "fisica_ambiente": dinamica,
        "animal": animal,
        "luz": random.choice(VARIACOES_LUZ_V11),
        "gesto": random.choice(GESTOS_V11),
        "modo": modo,
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

ONE SCENE — ONE SOURCE OF TRUTH: The exact PROMPT DE IMAGEM is the binding scene specification. Repeat its precise location, layout, weather, plants, natural textures, table or counter, lighting direction, wardrobe, presenter, props, animals if any, and reference product identity. Never swap to an alternative V11 background or introduce animals, wetness, steam, objects or trees that are not in that image. Its packaging is authoritative; preserve label text and item count across time.

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
            f'Keep ONE firmly supported in the presenter’s hand and each of the other {qtd-1} supported at its exact image location for the whole 0:00–0:10; frame wide enough that ALL {qtd} remain recognizable in the opening, reaction and final shot. '
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
        f'Quantidade conferida pelo scanner: {qtd} UNIDADES. Se 2 ou 3 unidades, TODAS devem estar visíveis desde o primeiro até o último quadro: uma na mão, demais apoiadas conforme a IMAGEM. Não inventar unidades. {scan.get("regra_pos_vid", "")}\n'
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
- REFERÊNCIA FIXA: a imagem fornecida determina cor, embalagem, acabamento e cenário. Manter materiais existentes e a direção da luz; melhorar somente microtextura, detalhe de superfície, rugosidade, reflexos e definição naturais, sem trocar a paleta, nem cenário nem objetos.
- CONTATO E GRAVIDADE: produto apoiado na bancada tem base em contato contínuo, sombra de contato consistente, gravidade, inércia e oclusão reais; produto na mão mantém posição estável, dedos anatomicamente corretos, pressão e oclusão coerentes, nenhuma interpenetração ou flutuação.
- CÂMERA: celular realista, câmera principalmente estável, deslocamentos curtos e suaves; proibir zoom violento, whip-pan, tremor excessivo, troca brusca de foco, glare artificial. Profundidade de campo coerente sem ocultar itens essenciais.
- PELE E MATERIAIS: poros finos, fios de cabelo individuais, rugosidade realista, leve assimetria; materiais com BRDF plausível, reflexos dependentes da iluminação real, sem brilho plástico ou nitidez falsa. Evitar hiperbolização da pele, do olhar ou da respiração.
- AMBIENTE: plantas e tecidos se movem apenas se houver vento plausível; vapor e água só onde efetivamente existem na referência; sombras, reflexos, perspectiva, luz e exposição temporalmente contínuos. Não adicionar animais, bagunça, objetos ou cenários que não estejam na referência enviada.
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
- REFERÊNCIA FIXA: a imagem fornecida determina cor, embalagem, acabamento e cenário. Manter materiais existentes e a direção da luz; melhorar somente microtextura, detalhe de superfície, rugosidade, reflexos e definição naturais, sem trocar a paleta, nem cenário nem objetos.
- CONTATO E GRAVIDADE: produto apoiado na bancada tem base em contato contínuo, sombra de contato consistente, gravidade, inércia e oclusão reais; produto na mão mantém posição estável, dedos anatomicamente corretos, pressão e oclusão coerentes, nenhuma interpenetração ou flutuação.
- CÂMERA: celular realista, câmera principalmente estável, deslocamentos curtos e suaves; proibir zoom violento, whip-pan, tremor excessivo, troca brusca de foco, glare artificial. Profundidade de campo coerente sem ocultar itens essenciais.
- PELE E MATERIAIS: poros finos, fios de cabelo individuais, rugosidade realista, leve assimetria; materiais com BRDF plausível, reflexos dependentes da iluminação real, sem brilho plástico ou nitidez falsa. Evitar hiperbolização da pele, do olhar ou da respiração.
- AMBIENTE: plantas e tecidos se movem apenas se houver vento plausível; vapor e água só onde efetivamente existem na referência; sombras, reflexos, perspectiva, luz e exposição temporalmente contínuos. Não adicionar animais, bagunça, objetos ou cenários que não estejam na referência enviada.
- FINAL: a partir de 0:08, a apresentadora mantém o produto perfeitamente visível em quadro; no último segundo, segurar imagem estável com produto e ambiente intactos até o último frame. PROIBIDO quadro preto, fade para preto, glitch, logo sobreposto, marca d'água, sacola 3D flutuante ou elementos duplicados. Logo original impressa na embalagem permanece; não acrescentar logo da empresa na imagem.
- ÁUDIO/COPY: fala factível em 9 segundos (aprox. 18–25 palavras, ajustar à locução), sem afirmar benefícios não demonstrados no rótulo, escassez, preço ou estoque não confirmados. Texto de CTA pode ficar para edição fora do gerador; não gerar UI nativa.
- Se um molde histórico conflitar com estas regras, este protocolo é soberano.

====================================================================
"""

with st.expander("🧠 17.3. Abrir Banco de Memória & Treinamento Oficial (Conectado ao 17 e ao 17.2)", expanded=False):
    st.caption("Todo o conhecimento do seu documento está gravado aqui e alimenta automaticamente os botões do Bloco 17 e do Bloco 17.2:")
    st.code(BANCO_DE_MEMORIA_17_3, language="markdown")

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

            {BANCO_DE_MEMORIA_17_3}

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
            1. FALA COM LEMA 'DOR -> SENSAÇÃO -> SOLUÇÃO': Na fala da {nome_inf_ativa}, NUNCA faça propaganda genérica ("Você sabia que o segredo chegou?"). Comece rasgando a dor `{scan_17.get('dor_pt')}`, entregue a sensação física `{scan_17.get('solucao_pt')}` com intimidade de amiga fofoqueira do bem, e feche com a urgência do lote secreto na sacolinha! E NUNCA fale de "coreanas" a menos que a palavra "Coreana" esteja literalmente escrita em `{scan_17.get('nome_pt')}`!
            2. POSICIONAMENTO DOS PRODUTOS (1 NA MÃO + RESTO NA BANCADA): Se houverem {scan_17.get('qtd')} unidades, ela segura APENAS 1 unidade na mão e as outras ficam paradas na bancada ao lado dela tanto na Imagem quanto no Shot 1 e Shot 2 do Vídeo! Não descreva cores com colchetes técnicos.
            3. Escreva os blocos visuais (`PROMPT DE IMAGEM`, `Shot 1`, `Shot 2`, `Interaction (3D CTA)`, `[PRISTINE CANVAS LOCK]`) 100% em INGLÊS PURO e ultra-denso!

            ENTREGUE EXATAMENTE NESTE FORMATO DE 3 SEÇÕES:

            ### 📸 PROMPT DE IMAGEM
            [Escreva aqui em inglês ultra-denso (1.300 a 1.900+ caracteres) o Prompt de Imagem Base seguindo fielmente o Molde do Banco de Memória 17.3, sorteando um ambiente vivo do Módulo Camaleão e aplicando: {scan_17.get('regra_pos_img')}]

            ### 🎬 PROMPT DE VÍDEO COMPLETO E UNIFICADO
            Shot 1 (Natural Hook & Physics): [Escreva em inglês seguindo prioritariamente o PROTOCOLO FÍSICO REALISTA V10: smartphone estável, sem zoom agressivo, produto inteiro e contínuo do início ao fim, aplicando {scan_17.get('regra_pos_vid')} + CRITICAL PHYSICS & SCALING 1:1 compact hand-proportioned size + SINGLE MOTION TRICK (The Trigger Tap on the lid of the single unit held / ou movimento da peça de roupa). NO hand overlapping, absolute physics stability, NO pixel melting.]
            Shot 2 (Whip Pan & Visceral Emotion): [0:03: WHIP PAN and brutal focus pull! The camera violently tilts up and snaps focus onto {nome_inf_ativa}'s face (wireless lapel microphone clearly visible on her shirt, flawless skin with visible pores). VISCERAL EMOTION ACTIVE: She leans in aggressively towards the lens (The Gossip Lean), her chest heaving with heavy, urgent breathing, pupils visibly dilated, and she flashes a breathless, intensely serious expression of pure warning while {scan_17.get('regra_pos_vid')}. ENVIRONMENT REINFORCEMENT LOCK: Repita em inglês todos os detalhes do cenário da imagem, plantas vivas, baguncinha e o animal se mexendo sutilmente no fundo.]
            Interaction (3D CTA): [0:08: She aggressively points her free index finger downwards towards the bottom corner of the screen. At this precise second, a highly realistic 3D floating orange shopping bag object materializes in the air near her pointing finger, casting realistic shadows. It is a physical 3D element pointing towards the UI button location.]
            [PRISTINE CANVAS LOCK - ZERO WATERMARKS]: [Strict requirement: The video frame must be completely devoid of any platform UI, handles, usernames, profile pictures, corner watermarks, or embedded social media logos from frame 0 to the final second. Pure clean video feed only.]
            🎙️ Áudio e Fala da {nome_inf_ativa} (Português — 100% Blindada Contra o Robô):
            Áudio (Inglês de fundo): [Audio captured via a wireless lapel microphone. Micro-ASMR intro (sound of product tap). Authentic room acoustics with subtle background ambient tones. Enthusiastic, urgent, conspiratorial voice, speaking as if revealing a highly guarded secret].
            Fala da {nome_inf_ativa}:
            "[Escreva em português uma fala visceral e magnética de 38 a 46 palavras aplicando '{gancho_sorteado_17}', atacando diretamente a dor '{scan_17.get('dor_pt')}', entregando a sensação '{scan_17.get('solucao_pt')}' e fechando com o lote secreto na sacolinha, sem preço numérico]"
            📝 Texto na Tela (Nativo TikTok - Foco na Dor):
            ⚠️ [PERGUNTA CURTA E FORTE SOBRE A DOR]? 🛑
            ✨ [SENSAÇÃO / SOLUÇÃO IMEDIATA]
            🛒 LOTE SECRETO LIBERADO 👇

            ### 🔑 TÍTULOS SEO (Separados)
            **🔍 Geral (Dor):** [Título focado na solução da dor '{scan_17.get('dor_pt')}']
            **💡 Solução (Produto):** [Nome completo do produto/kit e volume]
            **🏷️ Marca (Resenha):** [Marca e nome do produto/kit resenha]
            """
            
            if eh_customizada:
                instrucao_ouro += f"\nNOTA DE ELENCO: Use a apresentadora {nome_inf_ativa} ({desc_inf_ativa})."
            if explicacao_video_usuario and explicacao_video_usuario.strip():
                instrucao_ouro += f"\nNOTA DE DIREÇÃO DO USUÁRIO: {explicacao_video_usuario.strip()}"
            
            instrucao_ouro += ("\n\nNOTA DE VARIEDADE (NÃO REESCREVER O MOLDE DE IMAGEM): "
                              "Mantenha o mesmo padrão RAW/V9.2 da imagem original; o ANIMAL FACTOR é opcional, "
                              "não coloque sempre o mesmo cachorro caramelo. Se houver um animal, varie espécie, "
                              "porte e ação conforme o ambiente; não repita a escolha recente. "
                              "Preserve a conexão visual com a natureza, o cenário rico e a baguncinha característica. "
                              f"Referência opcional de diversidade desta rodada: {direcao_v11_17['animal']}.")
            instrucao_ouro += "\n\nREGRA FINAL INEGOCIÁVEL: " + PROTOCOLO_FISICO_17
            validar_cota_ia()
            resp = cliente_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é o Diretor de Arte e Copywriter Visceral da ÉLÉVO. Lema: 'Não vendemos produtos, vendemos a solução de uma dor e a sensação do resultado'. Siga 100% os Moldes do Banco de Memória 17.3. Escreva toda a parte visual em inglês puro."},
                    {"role": "user", "content": instrucao_ouro}
                ],
                max_tokens=6500, temperature=0.75
            )
            
            conteudo_texto = resp.choices[0].message.content.strip()
            conteudo_texto = reforcar_apenas_video_v12(conteudo_texto, scan_17, "360")
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

                {BANCO_DE_MEMORIA_17_3}

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
                1. LEMA 'DOR -> SENSAÇÃO -> SOLUÇÃO': Na fala da {nome_inf_ativa}, é PROIBIDO soar como vendedor ou comercial fraco! Comece colocando o dedo na ferida (`{scan_v92.get('dor_pt')}`), entregue a sensação visceral do resultado (`{scan_v92.get('solucao_pt')}`) com tom de amiga fofoqueira urgente, e feche com o lote secreto vazado na sacolinha!
                2. Preserve exatamente o ambiente da imagem de referência. Não sorteie novos cenários, animais ou objetos; aplique apenas o refinamento natural de textura.
                3. Se houver {scan_v92.get('qtd')} unidades na foto, mantenha sempre a quantidade e a identidade de cada unidade (1 na mão, demais na bancada); nenhuma pode desaparecer ao mudar enquadramento.
                4. Mantenha produto, apresentadora e ambiente fisicamente consistentes até o último frame. NÃO inserir logo extra, glitch ou quadro preto. A marca original da embalagem deve permanecer intacta.

                ENTREGUE EXATAMENTE NESTE FORMATO EM 3 SEÇÕES:

                ### 📸 PROMPT DE IMAGEM
                RAW photography, cinematic macro mid-shot POV erratic handheld mobile phone selfie, framing from chest up. Extreme V9 hyper-realism: microscopic visible peach fuzz, heavily dilated pupils, visceral breathing with chest slightly heaving, natural glowing micro-sweat on the collarbone, advanced subsurface scattering, moody warm natural tropical sunlight filtering through greenery, NO flash. The photorealistic young Brazilian woman ({nome_inf_ativa}: {desc_inf_ativa}) with a deeply shocked, conspiratorial gossip micro-expression, acting as if she is sharing an urgent warning. [AVATAR LOCK: She MUST have perfectly cut straight bangs (franja reta) and a small black wireless lapel microphone clipped to her collar]. Her hair/skin is the ultimate proof of the product: ultra-hydrated, glowing, displaying an intense mirror-like shine and absolute zero frizz. She is standing inside [DESCREVA EM INGLÊS DENSO UM CENÁRIO INÉDITO DO BANCO DE MEMÓRIA 17.3]. [CRITICAL PIXEL-PERFECT CLONE LOCK & SCALING]: [CRITICAL: 1:1 real-world scale, strictly realistic compact product size and proportions fitting comfortably inside a human hand, exact match to reference, do not oversize]. {scan_v92.get('regra_pos_img')} [BRANDING INTEGRITY LOCK]: All text and graphics preserved accurately. [ABSOLUTE UI LOCK]: ABSOLUTE ZERO watermarks, ABSOLUTE ZERO social media interface, ABSOLUTE ZERO platform logos, ABSOLUTE ZERO floating usernames anywhere in the frame. [NATURE MATRIX ACTIVE (DENSE)]: [Plantas vivas, samambaias, monsteras, borboletas ou cachoeira em inglês]. [BAGUNCINHA TEMÁTICA (CHAOS V9)]: [Baguncinha reativa em inglês]. [ANIMAL FACTOR (STORYTELLING V9)]: [Vira-lata caramelo ou gato em ação no fundo em inglês]. High-contrast, cinematic atmospheric shadows, natural phone-sensor grain, true-to-reference material texture and original scene geometry; no new objects, realistic contact shadow.

                ### 🎬 PROMPT DE VÍDEO COMPLETO E UNIFICADO
                [RAW SMARTPHONE FOOTAGE, 9:16, single continuous scene, naturally stable handheld camera, authentic texture and lighting, same original environmental colors and layout. Preserve the EXACT product photographed: {scan_v92.get('regra_pos_vid')}. Keep the original container, brand, proportions, reflections, print, label orientation and count constant through every frame. 0:00-0:03: medium-close product shot at natural scale, supported by hand or solid counter, realistic gravity, contact shadow and occlusion. One small physically plausible finger tap only if the product is touched. 0:03-0:06: smooth gentle camera reframing to {nome_inf_ativa} ({desc_inf_ativa}), with the original product remaining visible; no whip pan, no aggressive zoom, no hidden product switch. 0:06-0:08: natural speech, tiny facial movements and quiet breathing, realistic pores and individual hair strands. 0:08-0:10: presenter holds or displays the SAME product in stable focus, original setting visible, no cuts to black, no fade, no digital glitch, no additional logos, no 3D shopping bag, no overlays. Preserve exact physics: hand-product grasp, rigid-body geometry, surface friction, gravity, stable relative coordinates, plausible light, material roughness, cast/contact shadows and depth of field. Every product stays visible, especially the very last frame. NO watermarks, no platform UI. Realistic smartphone recording rather than CGI or a commercial render.]

                🎙️ Áudio (Gancho V9.2 — Exatos 9 Segundos):
                (Abre em 0.0s com micro-efeito ASMR do produto/ambiente e um suspiro de advertência).
                "[Micro-efeito ASMR + Suspiro] [ESCREVA EM PORTUGUÊS A FALA LETAL DE EXATOS 9 SEGUNDOS (18 A 25 PALAVRAS) APLICANDO '{gancho_sorteado_v92}': COMECE ATACANDO A DOR '{scan_v92.get('dor_pt')}', ENTREGUE A SENSAÇÃO '{scan_v92.get('solucao_pt')}' COM PROXIMIDADE DE AMIGA E FECHE COM O LOTE SECRETO VAZADO NA SACOLINHA, ZERO PREÇO NUMÉRICO]"

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

                if explicacao_video_usuario and explicacao_video_usuario.strip():
                    instrucao_v92 += f"\n\nDIRETRIZ EXTRA DO USUÁRIO: {explicacao_video_usuario.strip()}"

                instrucao_v92 += ("\n\nNOTA DE VARIEDADE (NÃO REESCREVER O MOLDE DE IMAGEM): "
                                  "Mantenha íntegro o estilo RAW V9.2 do prompt de imagem. "
                                  "O exemplo de vira-lata caramelo/gato no molde não é obrigatório. "
                                  "Se existir animal, escolha espécie/ação compatível com o cenário e diferente das recentes; "
                                  "também são aceitas cenas sem animal. Preserve natureza, ambiente orgânico e textura viscerais. "
                                  f"Referência opcional desta rodada: {direcao_v11_92['animal']}.")
                instrucao_v92 += "\n\nREGRA FINAL INEGOCIÁVEL: " + PROTOCOLO_FISICO_17
                validar_cota_ia()
                resp_v92 = cliente_openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Você é a Entidade V9.2 Master. Seu lema inegociável: 'Nós não vendemos produtos, nós resolvemos problemas, atacamos a dor visceral, entregamos a sensação do desejo e geramos proximidade de amiga confidente'. Siga 100% o Banco de Memória 17.3."},
                        {"role": "user", "content": instrucao_v92}
                    ],
                    max_tokens=6500,
                    temperature=0.75
                )

                conteudo_v92 = resp_v92.choices[0].message.content.strip()
                conteudo_v92 = reforcar_apenas_video_v12(conteudo_v92, scan_v92, "v9.2")
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
