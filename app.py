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
from gtts import gTTS

# ==========================================================
# 1. CONFIGURAÇÃO DA CHAVE DA IA E DO APP (🔥 V5.0 - MOTOR OPENAI)
# ==========================================================
st.set_page_config(page_title="ÉLÉVO | Painel de Vendas V5.0", page_icon="🦅", layout="wide")

# Inicializa o cérebro global da OpenAI
try:
    CHAVE_OPENAI_VIP = st.secrets["OPENAI_API_KEY"]
    cliente_openai = OpenAI(api_key=CHAVE_OPENAI_VIP)
except KeyError:
    st.error("🚨 ALERTA: Falta a chave OPENAI_API_KEY no cadeado (Secrets).")
    st.stop()

# Função global para chamar o ChatGPT em todo o aplicativo
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

# Conexão do Robô (GCP) com o Google Sheets
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
# 0. PORTARIA VIP (SISTEMA DE LOGIN E CADASTRO SAAS)
# ==========================================================
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = False
    st.session_state["email_usuario"] = ""
    st.session_state["nome_usuario"] = ""

# Banco de dados de usuários na memória da plataforma
if "banco_usuarios" not in st.session_state:
    st.session_state["banco_usuarios"] = {}

# A SUA CHAVE MESTRA PERMANENTE:
EMAIL_MESTRE = "orafae005@gmail.com" 
SENHA_MESTRA = "Rafa 258467"

if not st.session_state["usuario_logado"]:
    # Design Premium da Tela de Entrada
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #00BFA5; font-size: 4rem; font-weight: 900;'>ÉLÉVO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A0A0A0;'>Sistema de Inteligência e Escala de Vendas.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            # Criação das duas abas: Entrar e Criar Conta
            aba_login, aba_cadastro = st.tabs(["🚀 Entrar", "✨ Criar Conta"])
            
            with aba_login:
                st.markdown("<h4 style='text-align: center; margin-bottom: 20px;'>Acesso à Central</h4>", unsafe_allow_html=True)
                email_input = st.text_input("📧 Seu Gmail", placeholder="Digite seu e-mail...", key="login_email")
                senha_input = st.text_input("🔑 Senha", type="password", placeholder="Digite sua senha...", key="login_senha")
                
                if st.button("🚀 ENTRAR", use_container_width=True, type="primary"):
                    email_clean = email_input.strip().lower()
                    
                    # 1. Verifica se é VOCÊ (O Sócio Mestre)
                    if email_clean == EMAIL_MESTRE and senha_input == SENHA_MESTRA:
                        st.session_state["usuario_logado"] = True
                        st.session_state["email_usuario"] = EMAIL_MESTRE
                        st.session_state["nome_usuario"] = "Sócio"
                        st.rerun()
                        
                    # 2. Verifica se é um Cliente Cadastrado
                    elif email_clean in st.session_state["banco_usuarios"] and st.session_state["banco_usuarios"][email_clean]["senha"] == senha_input:
                        st.session_state["usuario_logado"] = True
                        st.session_state["email_usuario"] = email_clean
                        st.session_state["nome_usuario"] = st.session_state["banco_usuarios"][email_clean]["nome"]
                        st.rerun()
                        
                    # 3. Bloqueia Invasores e Curiosos
                    else:
                        st.error("🚨 Conta não encontrada ou senha incorreta! Se for novo, vá em 'Criar Conta'.")

            with aba_cadastro:
                st.markdown("<h4 style='text-align: center; margin-bottom: 20px;'>Nova Conta VIP</h4>", unsafe_allow_html=True)
                novo_nome = st.text_input("👤 Como quer ser chamado?", placeholder="Seu apelido...")
                novo_email = st.text_input("📧 Seu melhor E-mail", placeholder="exemplo@gmail.com")
                nova_senha = st.text_input("🔑 Crie uma Senha", type="password", placeholder="Sua senha secreta...")
                
                if st.button("✨ CRIAR MINHA CONTA", use_container_width=True, type="secondary"):
                    email_clean = novo_email.strip().lower()
                    if not novo_nome or not email_clean or not nova_senha:
                        st.warning("⚠️ Preencha os 3 campos para criar a sua conta.")
                    elif email_clean == EMAIL_MESTRE or email_clean in st.session_state["banco_usuarios"]:
                        st.error("🚨 Este e-mail já está cadastrado! Vá para a aba 'Entrar'.")
                    else:
                        # Salva o novo usuário na plataforma
                        st.session_state["banco_usuarios"][email_clean] = {
                            "nome": novo_nome.strip(),
                            "senha": nova_senha
                        }
                        st.success(f"✅ Conta criada, {novo_nome}! Volte à aba 'Entrar' e faça o login.")
    
    # Barreira de Segurança
    st.stop()

# ==========================================================
# 2. DESIGN E TEMA DINÂMICO (🔥 V5.6 - DARK PREMIUM)
# ==========================================================
import streamlit.components.v1 as components

col_vazia, col_tema = st.columns([8, 2])
with col_tema:
    modo_claro = st.toggle("☀️ Modo Claro", value=False)

# Inteligência de Cores VIP (Premium, Discreto e Confortável)
if modo_claro:
    bg_color = "#F4F4F9"
    text_color = "#333333" 
    card_bg = "#FFFFFF"
    border_color = "rgba(0, 0, 0, 0.08)"
    btn_bg = "#F9F9F9"
    btn_text = "#333333"
    btn_primary_bg = "#005C4B" 
    btn_primary_text = "#FFFFFF"
    input_bg = "#F9F9F9"
    shadow_base = "rgba(0, 0, 0, 0.05)"
else:
    bg_color = "#0E1117"
    text_color = "#E0E0E0" 
    card_bg = "rgba(25, 27, 31, 0.8)"
    border_color = "rgba(255, 255, 255, 0.05)" 
    btn_bg = "#1A1C20"
    btn_text = "#C0C0C0"
    btn_primary_bg = "#004D40" 
    btn_primary_text = "#FFFFFF"
    input_bg = "#15181C"
    shadow_base = "rgba(0, 0, 0, 0.3)"

estilo_elevo = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;800&display=swap');

    html, body, [class*="css"] {{ font-family: 'Montserrat', sans-serif !important; }}
    [data-testid="stAppViewContainer"] {{ background-color: {bg_color}; }}
    
    /* Removemos qualquer traço do cabeçalho bugado e da barra lateral */
    [data-testid="stSidebar"] {{ display: none !important; }}
    [data-testid="stHeader"] {{ display: none !important; }}
    [data-testid="collapsedControl"] {{ display: none !important; }}
    footer {{ display: none !important; }}

    /* Garante que os textos normais fiquem confortáveis */
    h1, h2, h3, h4, h5, h6, p, span, label, li {{ color: {text_color} !important; }}

    /* Títulos Principais */
    .titulo-elevo {{
        font-size: 3.2rem; font-weight: 800; text-align: center;
        color: #00BFA5;
        margin-bottom: -10px; letter-spacing: 3px; text-transform: uppercase;
        margin-top: 5px;
    }}

    .subtitulo {{
        text-align: center; font-size: 0.95rem; margin-bottom: 30px;
        font-weight: 400; letter-spacing: 1px; text-transform: uppercase;
        color: {text_color} !important; opacity: 0.6;
    }}

    /* Caixas Discretas e Naturais */
    [data-testid="stMetric"], div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 10px {shadow_base} !important;
    }}

    /* Inputs e TextAreas Discretos */
    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > textarea, div[data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        border: 1px solid {border_color} !important;
        color: {text_color} !important;
        border-radius: 8px !important;
    }}
    div[data-baseweb="input"] > div:focus-within, div[data-baseweb="textarea"] > textarea:focus, div[data-baseweb="select"] > div:focus-within {{
        border-color: #00BFA5 !important;
    }}
</style>
"""
st.markdown(estilo_elevo, unsafe_allow_html=True)

# 🎯 INJEÇÃO DA MOEDA ANIMADA (NOVO PODER: VOLTAR AO TOPO / TROCAR CONTA)
js_moeda = """
<script>
    const parent = window.parent.document;
    if (!parent.getElementById("moeda-aguia-vip")) {
        const btn = parent.createElement("div");
        btn.id = "moeda-aguia-vip";
        btn.innerHTML = "🦅";
        btn.style.cssText = "position: fixed; top: 15px; left: 15px; z-index: 999999; font-size: 24px; background: #1a1c20; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #00BFA5; box-shadow: 0px 4px 10px rgba(0,0,0,0.5); cursor: pointer; user-select: none; touch-action: none; transition: transform 0.1s ease;";
        parent.body.appendChild(btn);

        let isDragging = false;
        let startX, startY, initialLeft, initialTop;

        function onTouchStart(e) {
            isDragging = false;
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            initialLeft = btn.offsetLeft;
            initialTop = btn.offsetTop;
            btn.style.opacity = '0.7';
            btn.style.transform = 'scale(0.9)'; 
        }

        function onTouchMove(e) {
            let dx = e.touches[0].clientX - startX;
            let dy = e.touches[0].clientY - startY;
            if (Math.abs(dx) > 12 || Math.abs(dy) > 12) {
                isDragging = true;
                e.preventDefault(); 
                btn.style.left = (initialLeft + dx) + "px";
                btn.style.top = (initialTop + dy) + "px";
            }
        }

        function onTouchEnd(e) {
            btn.style.opacity = '1';
            btn.style.transform = 'scale(1)';
            if (!isDragging) {
                irParaTopoConta();
            }
            isDragging = false;
        }

        btn.addEventListener('touchstart', onTouchStart, {passive: false});
        btn.addEventListener('touchmove', onTouchMove, {passive: false});
        btn.addEventListener('touchend', onTouchEnd);

        btn.addEventListener('mousedown', function(e) {
            isDragging = false;
            startX = e.clientX;
            startY = e.clientY;
            initialLeft = btn.offsetLeft;
            initialTop = btn.offsetTop;
            btn.style.opacity = '0.7';
            btn.style.transform = 'scale(0.9)';

            function onMouseMove(moveE) {
                let dx = moveE.clientX - startX;
                let dy = moveE.clientY - startY;
                if (Math.abs(dx) > 8 || Math.abs(dy) > 8) {
                    isDragging = true;
                    btn.style.left = (initialLeft + dx) + "px";
                    btn.style.top = (initialTop + dy) + "px";
                }
            }

            function onMouseUp() {
                btn.style.opacity = '1';
                btn.style.transform = 'scale(1)';
                parent.removeEventListener('mousemove', onMouseMove);
                parent.removeEventListener('mouseup', onMouseUp);
                if (!isDragging) {
                    irParaTopoConta();
                }
                isDragging = false;
            }

            parent.addEventListener('mousemove', onMouseMove);
            parent.addEventListener('mouseup', onMouseUp);
        });

        // ==========================
        // TELETRANSPORTE PARA O TOPO
        // ==========================
        function irParaTopoConta() {
            const topo = parent.getElementById("ancora-topo");
            if (topo) {
                topo.scrollIntoView({behavior: "smooth", block: "start"});
            } else {
                parent.querySelector('.main').scrollTo({top: 0, behavior: 'smooth'});
            }
        }
    }
</script>
"""
components.html(js_moeda, height=0, width=0)

# Âncora invisível para a Águia mirar quando for clicada
st.markdown('<div id="ancora-topo"></div>', unsafe_allow_html=True)

st.markdown('<div class="titulo-elevo">ÉLÉVO</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">SISTEMA DE INTELIGÊNCIA E ESCALA DE VENDAS</div>', unsafe_allow_html=True)


# ==========================================================
# 3. PAINEL CENTRAL DE OPERAÇÃO E MULTI-UTILIZADOR
# ==========================================================
st.markdown("<h3 style='text-align: center; color: #00BFA5; margin-bottom: 5px;'>⚡ Central de Operação</h3>", unsafe_allow_html=True)

# Lógica SaaS: Identifica se é o Sócio Mestre ou um cliente
if st.session_state["email_usuario"] == EMAIL_MESTRE:
    COFRE_DE_LINKS = {
        "O Achado Secreto": "https://docs.google.com/spreadsheets/d/1J5UYfLCQ5rXUmUzxnE5hyG4AYtJEnXlJnN8jAEbH34Y/edit",
        "O Garimpo Chic": "" 
    }
    opcoes_canais = ["🟢 O Achado Secreto", "🟣 O Garimpo Chic", "➕ Adicionar Novo Canal"]
    st.success(f"Bem-vindo de volta, Sócio! O império aguarda as suas ordens. 🦅")
else:
    # Plataforma zerada para novos usuários cadastrados
    COFRE_DE_LINKS = {}
    opcoes_canais = ["➕ Adicionar Novo Canal"]
    st.info(f"Bem-vindo(a) à ÉLÉVO, {st.session_state['nome_usuario']}! Comece adicionando a sua planilha de vendas.")

with st.container(border=True):
    col_conta, col_filtro = st.columns(2)
    
    with col_conta:
        canal_selecionado = st.selectbox("🎯 Selecione a Conta", opcoes_canais)
        
        if canal_selecionado == "➕ Adicionar Novo Canal":
            nome_canal_ativo = st.text_input("Nome do Novo Canal", placeholder="Ex: Meu Novo Projeto")
            link_planilha_ativa = st.text_input("🔗 Link da Planilha do Google", placeholder="Cole o link aqui")
        else:
            nome_canal_ativo = canal_selecionado.replace("🟢 ", "").replace("🟣 ", "")
            link_salvo = COFRE_DE_LINKS.get(nome_canal_ativo, "")
            if link_salvo != "":
                link_planilha_ativa = link_salvo
                st.caption("✅ Link do cofre ativado!")
            else:
                link_planilha_ativa = st.text_input(f"🔗 Link da Planilha ({nome_canal_ativo})", placeholder="Cole o link aqui")

    with col_filtro:
        filtro_periodo = st.selectbox(
            "📅 Filtrar Período de Vendas",
            ["Hoje", "Ontem", "Últimos 7 Dias", "Últimos 30 Dias", "Mês Atual", "Mês Passado", "Tudo"]
        )

# Botão de Sair (Logout)
if st.button("Sair da Conta (Logout)", key="btn_logout"):
    st.session_state["usuario_logado"] = False
    st.session_state["email_usuario"] = ""
    st.session_state["nome_usuario"] = ""
    st.rerun()
# ==========================================================
# 4. EXTRATOR DE ID E CARREGAMENTO DE DADOS (🔥 CACHE TURBO 5 MIN)
# ==========================================================
def extrair_id_planilha(url):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else None

@st.cache_data(ttl=300)
def carregar_dados_dinamicos(url):
    if not url or not robo_sheets:
        return pd.DataFrame()
    try:
        sheet_id = extrair_id_planilha(url)
        planilha = robo_sheets.open_by_key(sheet_id)
        aba = planilha.sheet1
        dados = aba.get_all_records()
        if dados:
            df_temp = pd.DataFrame(dados)
            df_temp.replace("", pd.NA, inplace=True)
            df_temp.dropna(how='all', inplace=True)
            return df_temp
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

df = carregar_dados_dinamicos(link_planilha_ativa)

if df.empty:
    df = pd.DataFrame(columns=["Data", "Produto", "Canal", "Status", "Quantidade", "Comissao_R$"])

df.columns = df.columns.astype(str).str.strip()

if "Quantidade" in df.columns:
    df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce").fillna(0)
else:
    df["Quantidade"] = 0

if "Comissao_R$" in df.columns:
    df["Comissao_R$"] = pd.to_numeric(
        df["Comissao_R$"].astype(str).str.replace("R$", "", regex=False).str.replace(",", ".", regex=False).str.strip(), 
        errors="coerce"
    ).fillna(0.0)
else:
    df["Comissao_R$"] = 0.0

if "Data" in df.columns:
    df["Data_Limpa"] = df["Data"].astype(str).apply(lambda x: x.split(" a ")[-1].strip() if " a " in x else x.strip())
    df["Data_Parsed"] = pd.to_datetime(df["Data_Limpa"], format="%d/%m/%Y", errors="coerce")
    df["Data_Parsed"] = df["Data_Parsed"].fillna(pd.to_datetime(df["Data_Limpa"], dayfirst=True, errors="coerce"))
else:
    df["Data_Parsed"] = pd.NaT
# ==========================================================
# 4. EXTRATOR DE ID E CARREGAMENTO DE DADOS (🔥 CACHE TURBO 5 MIN)
# ==========================================================
def extrair_id_planilha(url):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else None

@st.cache_data(ttl=300)
def carregar_dados_dinamicos(url):
    if not url or not robo_sheets:
        return pd.DataFrame()
    try:
        sheet_id = extrair_id_planilha(url)
        planilha = robo_sheets.open_by_key(sheet_id)
        aba = planilha.sheet1
        dados = aba.get_all_records()
        if dados:
            df_temp = pd.DataFrame(dados)
            df_temp.replace("", pd.NA, inplace=True)
            df_temp.dropna(how='all', inplace=True)
            return df_temp
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

df = carregar_dados_dinamicos(link_planilha_ativa)

if df.empty:
    df = pd.DataFrame(columns=["Data", "Produto", "Canal", "Status", "Quantidade", "Comissao_R$"])

df.columns = df.columns.astype(str).str.strip()

if "Quantidade" in df.columns:
    df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce").fillna(0)
else:
    df["Quantidade"] = 0

if "Comissao_R$" in df.columns:
    df["Comissao_R$"] = pd.to_numeric(
        df["Comissao_R$"].astype(str).str.replace("R$", "", regex=False).str.replace(",", ".", regex=False).str.strip(), 
        errors="coerce"
    ).fillna(0.0)
else:
    df["Comissao_R$"] = 0.0

if "Data" in df.columns:
    df["Data_Limpa"] = df["Data"].astype(str).apply(lambda x: x.split(" a ")[-1].strip() if " a " in x else x.strip())
    df["Data_Parsed"] = pd.to_datetime(df["Data_Limpa"], format="%d/%m/%Y", errors="coerce")
    df["Data_Parsed"] = df["Data_Parsed"].fillna(pd.to_datetime(df["Data_Limpa"], dayfirst=True, errors="coerce"))
else:
    df["Data_Parsed"] = pd.NaT

# ==========================================================
# 5. APLICAÇÃO DOS FILTROS DE PERÍODO NA BASE 
# ==========================================================
df_filtrado = df.copy()
if not df_filtrado.empty and "Data_Parsed" in df_filtrado.columns:
    agora_brasil = datetime.utcnow() - timedelta(hours=3)
    hoje = pd.Timestamp(agora_brasil.date())
    
    if filtro_periodo != "Tudo":
        df_filtrado = df_filtrado.dropna(subset=["Data_Parsed"])
        
    if not df_filtrado.empty:
        df_filtrado["Data_Parsed"] = df_filtrado["Data_Parsed"].dt.normalize()
        
        if filtro_periodo == "Hoje":
            df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] == hoje]
        elif filtro_periodo == "Ontem":
            ontem = hoje - timedelta(days=1)
            df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] == ontem]
        elif filtro_periodo == "Últimos 7 Dias":
            limite = hoje - timedelta(days=7)
            df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] >= limite]
        elif filtro_periodo == "Últimos 30 Dias":
            limite = hoje - timedelta(days=30)
            df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] >= limite]
        elif filtro_periodo == "Mês Atual":
            df_filtrado = df_filtrado[(df_filtrado["Data_Parsed"].dt.month == hoje.month) & (df_filtrado["Data_Parsed"].dt.year == hoje.year)]
        elif filtro_periodo == "Mês Passado":
            mes_passado = hoje.month - 1 if hoje.month > 1 else 12
            ano_passado = hoje.year if hoje.month > 1 else hoje.year - 1
            df_filtrado = df_filtrado[(df_filtrado["Data_Parsed"].dt.month == mes_passado) & (df_filtrado["Data_Parsed"].dt.year == ano_passado)]

# ==========================================================
# 6. DASHBOARD FINANCEIRO E GRÁFICOS (🔥 V6.3 - VIP NATIVO CELULAR)
# ==========================================================
# Inicialização de segurança (Blinda contra NameError em contas novas)
df_campeao = pd.DataFrame()
df_timeline = pd.DataFrame()
produto_campeao = "Nenhum"
aprovado = 0.0
pendente = 0.0

if not link_planilha_ativa:
    st.info(f"👉 Cole o link da planilha no painel acima para carregar os dados de '{nome_canal_ativo}'.")
else:
    if not df_filtrado.empty:
        aprovado = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False)]["Comissao_R$"].sum()
        pendente = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("pendente", na=False)]["Comissao_R$"].sum()
        
        df_validos = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False)]
        
        if not df_validos.empty:
            df_campeao = df_validos.groupby("Produto")[["Quantidade", "Comissao_R$"]].sum().reset_index()
            df_campeao = df_campeao.sort_values(by=["Comissao_R$"], ascending=False)
            produto_campeao = df_campeao.iloc[0]["Produto"]
            
            df_timeline = df_validos.groupby("Data_Parsed")["Comissao_R$"].sum().reset_index()
            df_timeline.sort_values("Data_Parsed", inplace=True)
            df_timeline["Data_Formatada"] = df_timeline["Data_Parsed"].dt.strftime("%d/%m")

    st.markdown(f"### 📊 Faturamento: {nome_canal_ativo}")

    aprovado_str = f"R$ {aprovado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    pendente_str = f"R$ {pendente:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    campeao_str = str(produto_campeao)
    if len(campeao_str) > 12:
        campeao_str = campeao_str[:12] + "..."

    cor_texto_valor = "#D4AF37" if not modo_claro else "#B8860B"
    cor_texto_titulo = "#A0A0A0" if not modo_claro else "#555555"

    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; text-align: center; margin-bottom: 20px;">
            <div style="flex: 1;">
                <p style="margin: 0; font-size: 0.7rem; font-weight: 600; color: {cor_texto_titulo}; text-transform: uppercase;">💰 Lucro</p>
                <p style="margin: 0; font-size: 1.2rem; font-weight: 900; color: {cor_texto_valor};">{aprovado_str}</p>
            </div>
            <div style="flex: 1; border-left: 1px solid rgba(212, 175, 55, 0.2); border-right: 1px solid rgba(212, 175, 55, 0.2);">
                <p style="margin: 0; font-size: 0.7rem; font-weight: 600; color: {cor_texto_titulo}; text-transform: uppercase;">⏳ Pendente</p>
                <p style="margin: 0; font-size: 1.2rem; font-weight: 900; color: {cor_texto_valor};">{pendente_str}</p>
            </div>
            <div style="flex: 1;">
                <p style="margin: 0; font-size: 0.7rem; font-weight: 600; color: {cor_texto_titulo}; text-transform: uppercase;">🏆 Campeão</p>
                <p style="margin: 0; font-size: 0.9rem; font-weight: 900; color: #00E5FF; padding-top: 5px;">{campeao_str}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not df_timeline.empty and not df_campeao.empty:
        with st.expander("📊 👁️ ABRIR GRÁFICOS FINANCEIROS", expanded=False):
            col_graf1, col_graf2 = st.columns(2)
            
            if modo_claro:
                cor_linha = "#005C66"
                cor_ponto = "#B8860B"
                cor_barra = "#005C66"
                cor_texto_grafico = "#333333"
                grid_color = "rgba(0, 0, 0, 0.05)"
            else:
                cor_linha = "#00E5FF"
                cor_ponto = "#D4AF37"
                cor_barra = "#D4AF37"
                cor_texto_grafico = "#A0A0A0"
                grid_color = "rgba(212, 175, 55, 0.1)"
            
            with col_graf1:
                st.markdown("##### 📈 Curva de Crescimento Diário")
                fig_line = px.line(
                    df_timeline, 
                    x="Data_Formatada", 
                    y="Comissao_R$", 
                    markers=True, 
                    text="Comissao_R$"
                )
                fig_line.update_traces(
                    textposition='top center',
                    texttemplate='R$ %{text:,.2f}', 
                    line=dict(color=cor_linha, width=4),
                    marker=dict(color=cor_ponto, size=10, line=dict(color="white", width=1)),
                    textfont=dict(color=cor_ponto, size=12, weight="bold")
                )
                fig_line.update_xaxes(showgrid=False, title="", fixedrange=True)
                fig_line.update_yaxes(showgrid=True, gridcolor=grid_color, title="", visible=False, zeroline=False, fixedrange=True)
                fig_line.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=cor_texto_grafico), margin=dict(l=0, r=0, t=40, b=10),
                    height=380, hovermode="x unified",
                    dragmode=False
                )
                st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})
                
            with col_graf2:
                st.markdown("##### 🏆 Top 10 Produtos Mais Vendidos")
                df_grafico_bar = df_campeao.head(10).copy()
                fig_bar = px.bar(
                    df_grafico_bar, 
                    x="Comissao_R$", 
                    y="Produto", 
                    orientation='h',
                    text="Comissao_R$",
                    color_discrete_sequence=[cor_barra]
                )
                fig_bar.update_traces(
                    texttemplate='R$ %{text:,.2f}', 
                    textposition='outside',
                    cliponaxis=False, 
                    marker_line_color=cor_linha, 
                    marker_line_width=1.5, 
                    opacity=0.9
                )
                fig_bar.update_xaxes(showgrid=False, title="", visible=False, fixedrange=True)
                fig_bar.update_yaxes(showgrid=False, title="", autorange="reversed", fixedrange=True)
                fig_bar.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=cor_texto_grafico), margin=dict(l=0, r=80, t=40, b=0),
                    height=380, dragmode=False
                )
                st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

# ==========================================================
# 7. LÓGICA DE PROCESSAMENTO COM IA (🔥 OPENAI) - ATUALIZADO
# ==========================================================
def extrair_dados_do_texto(texto_bruto, nome_canal):
    agora_brasil = datetime.utcnow() - timedelta(hours=3)
    data_hoje = agora_brasil.strftime("%d/%m/%Y")
    
    sistema = "Você é Aurora, a Auditora Financeira de Elite do painel ÉLÉVO."
    prompt = f"""
    INFORMAÇÕES DE SISTEMA:
    - DATA DE HOJE: {data_hoje}
    
    REGRAS INQUEBRÁVEIS:
    1. COMISSÃO EXATA: Se o texto colado já for uma tabela ou lista com os valores prontos, NÃO calcule 15% em cima de nada. Apenas extraia e repita os valores exatos da comissão fornecida.
    2. 🔥 REGRA DO PONTO DECIMAL: Use SEMPRE ponto (.) para decimais e não coloque 'R$'. Exemplo: 5.02.
    3. STATUS: Preencha como 'Aprovado'.
    4. DATA: Use a data colada. Se não tiver, use {data_hoje}.
    
    🎯 EXEMPLO DE RESPOSTA OBRIGATÓRIA:
    {data_hoje};Nome do Produto;{nome_canal};Aprovado;1;10.83
    
    Texto copiado:
    {texto_bruto}
    
    Retorne APENAS as linhas de dados brutos, sem markdown. Formato (separado por ponto e vírgula):
    Data;Nome do Produto;{nome_canal};Status;Quantidade;ValorDaComissao
    """
    return chamar_ia_global(prompt, sistema)

# ==========================================================
# 8. AUDITORIA E INJEÇÃO DE DADOS 
# ==========================================================
if "dados_prontos" not in st.session_state:
    st.session_state["dados_prontos"] = []

st.markdown("### 🤖 Motor de Auditoria e Injeção (Aurora)")

st.write("📋 Copie o relatório de produtos do TikTok Shop e cole abaixo:")
texto_copiado = st.text_area("Cole os dados brutos aqui:", height=150, placeholder="Cole aqui o texto copiado...")

if st.button("🚀 Extrair Dados do Texto", type="primary", use_container_width=True):
    if texto_copiado.strip() == "":
        st.warning("⚠️ Cole algum texto antes de pedir para a Aurora ler!")
    else:
        barra_progresso_texto = st.progress(10)
        with st.spinner("🦅 A Aurora está organizando o seu fluxo de caixa..."):
            texto_ia = extrair_dados_do_texto(texto_copiado, nome_canal_ativo)
            barra_progresso_texto.progress(60)
            
            if "ERRO_API:" not in texto_ia and texto_ia:
                linhas = texto_ia.split('\n')
                for linha in linhas:
                    linha = linha.strip()
                    if not linha or "Data;" in linha or "Produto;" in linha: continue
                    itens = linha.split(';')
                    if len(itens) >= 6:
                        st.session_state["dados_prontos"].append({
                            "Data": itens[0].strip(),
                            "Produto": itens[1].strip(),
                            "Canal": itens[2].strip(),
                            "Status": itens[3].strip(),
                            "Quantidade": itens[4].strip(),
                            "Comissao_R$": itens[5].strip()
                        })
                barra_progresso_texto.progress(100)
                if len(st.session_state["dados_prontos"]) == 0:
                    st.error("⚠️ A Aurora leu o texto, mas não encontrou os dados. Verifique a cópia!")
            else:
                st.error(f"⚠️ Erro ao conectar com a Aurora: {texto_ia}")

if st.session_state["dados_prontos"]:
    html_tabela_animada = """
    <style>
        @keyframes slideInUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        [data-testid="stDataFrame"] {
            animation: slideInUp 0.6s ease-out;
            border: 1px solid rgba(212, 175, 55, 0.4);
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(212, 175, 55, 0.15);
        }
    </style>
    """
    st.markdown(html_tabela_animada, unsafe_allow_html=True)
    
    st.success("✨ Dados validados pela Aurora! ✍️ Confirme a tabela animada abaixo e Injete:")
    
    col_tabela_1, col_tabela_2 = st.columns([4, 1])
    with col_tabela_2:
        if st.button("🗑️ Limpar Lista"):
            st.session_state["dados_prontos"] = []
            st.rerun()

    df_novos = pd.DataFrame(st.session_state["dados_prontos"])
    df_editado = st.data_editor(df_novos, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 INJETAR DADOS NA PLANILHA", type="primary"):
        if not link_planilha_ativa or not robo_sheets:
            st.error("⚠️ Cole o link da planilha na barra lateral e verifique a conexão do Robô.")
        else:
            with st.spinner("O Robô está injetando os dados no Google Drive..."):
                try:
                    sheet_id = extrair_id_planilha(link_planilha_ativa)
                    planilha = robo_sheets.open_by_key(sheet_id)
                    aba = planilha.sheet1
                    
                    dados_finais = df_editado.to_dict('records')
                    linhas_inserir = [[str(d.get("Data", "")), str(d.get("Produto", "")), str(d.get("Canal", "")), str(d.get("Status", "")), str(d.get("Quantidade", "")), str(d.get("Comissao_R$", "")) ] for d in dados_finais]
                    
                    coluna_a = aba.col_values(1)
                    linhas_com_dados = len([x for x in coluna_a if x.strip() != ""])
                    proxima_linha = linhas_com_dados + 1
                    
                    aba.insert_rows(linhas_inserir, row=proxima_linha, value_input_option="USER_ENTERED")
                    
                    st.success("🔥 SUCESSO ABSOLUTO! Planilha atualizada automaticamente!")
                    st.balloons()
                    st.session_state["dados_prontos"] = [] 
                    carregar_dados_dinamicos.clear() 
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao escrever na planilha. Detalhe: {e}")

# ==========================================================
# 🦅 PROTOCOLO DE EMERGÊNCIA (O BOTÃO DE PÂNICO)
# ==========================================================
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("🦅 PROTOCOLO ÁGUIA (Limpar Erros de Hoje)", expanded=False):
    st.warning("⚠️ **Atenção:** Clicar no botão abaixo vai entrar na sua Planilha do Google e **APAGAR TODAS as vendas com a data de HOJE**.")
    
    if st.button("🦅 ACIONAR ÁGUIA (Limpar Vendas de Hoje)", type="secondary", use_container_width=True):
        if not link_planilha_ativa or not robo_sheets:
            st.error("⚠️ Planilha não conectada.")
        else:
            with st.spinner("🦅 A Águia está voando pela planilha e apagando os erros um por um..."):
                try:
                    sheet_id = extrair_id_planilha(link_planilha_ativa)
                    planilha = robo_sheets.open_by_key(sheet_id)
                    aba = planilha.sheet1
                    
                    coluna_datas = aba.col_values(1) 
                    agora_brasil = datetime.utcnow() - timedelta(hours=3)
                    hoje_str = agora_brasil.strftime("%d/%m/%Y")
                    
                    linhas_apagadas = 0
                    for i in range(len(coluna_datas), 1, -1):
                        if str(coluna_datas[i-1]).strip() == hoje_str:
                            aba.delete_rows(i)
                            linhas_apagadas += 1
                            time.sleep(0.5) 
                            
                    if linhas_apagadas > 0:
                        st.success(f"🦅 SUCESSO! A Águia eliminou {linhas_apagadas} linhas corrompidas de hoje.")
                    else:
                        st.info("🦅 A Águia não encontrou nenhum dado com a data de hoje para apagar.")
                        
                    carregar_dados_dinamicos.clear()
                    time.sleep(3)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro no voo da Águia: {e}")

# ==========================================================
# 9. TABELA DA CURVA DE EVOLUÇÃO 
# ==========================================================
st.markdown(f"### 🚀 Curva de Evolução dos Produtos ({filtro_periodo})")
if not df_filtrado.empty:
    colunas_visiveis = [c for c in df_filtrado.columns if c != "Data_Parsed"]
    df_tabela = df_filtrado[colunas_visiveis].copy()
    df_tabela = df_tabela.iloc[::-1].reset_index(drop=True)
    
    st.dataframe(df_tabela.head(10), use_container_width=True)
    
    if len(df_tabela) > 10:
        with st.expander(f"📂 Ver todo o histórico escondido ({len(df_tabela)} vendas)"):
            st.dataframe(df_tabela, use_container_width=True)
else:
    st.info("Nenhum dado encontrado para o período selecionado.")

# ==========================================================
# 10. MOTOR DE ELITE: GAMIFICAÇÃO & DISCIPLINA
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🧠 Motor de Elite: Gamificação & Disciplina</h3>", unsafe_allow_html=True)

agora_brasil = datetime.utcnow() - timedelta(hours=3)
dia_do_ano = agora_brasil.timetuple().tm_yday

frases_motivacionais = [
    "O sucesso é a soma de pequenos esforços repetidos dia após dia.",
    "Não espere por oportunidades, crie-as. Grave aquele vídeo agora!",
    "A constância é a chave que abre a porta da escala.",
    "O seu próximo vídeo pode ser o que vai te deixar milionário. Não pare!",
    "Feito é melhor que perfeito. Ajuste a rota enquanto caminha!"
]

missoes = [
    "Gravar e postar 5 vídeos originais hoje usando a técnica do gancho forte.",
    "Analisar 3 produtos novos na 'peneira' do TikTok e favoritar o melhor.",
    "Gravar 3 vídeos review focados no seu Produto Campeão atual.",
    "Revisar o vídeo que mais vendeu na semana e replicar o mesmo estilo hoje."
]

dicas_investimento = [
    "Pegue 20% da comissão e invista na operação (tráfego, microfone, iluminação).",
    "Construa uma reserva de emergência da operação. Não gaste todo o lucro no primeiro mês!",
    "Reinvista no Produto Campeão. Se está vendendo orgânico, imagina com um pouco de impulsionamento!",
    "Diversificação: Que tal guardar parte do lucro no Tesouro Direto ou CDB para render juros?"
]

frase_hoje = frases_motivacionais[dia_do_ano % len(frases_motivacionais)]
missao_hoje = missoes[dia_do_ano % len(missoes)]
dica_hoje = dicas_investimento[dia_do_ano % len(dicas_investimento)]

col_mindset, col_missao = st.columns([1, 1])

with col_mindset:
    st.info(f"💎 **Visão de Águia:** {frase_hoje}")
    st.warning(f"📈 **Dica Financeira:** {dica_hoje}")
    
with col_missao:
    st.markdown(f"🎯 **Sua Missão de Hoje:** {missao_hoje}")
    missao_cumprida = st.button("✅ CONCLUIR MISSÃO DE HOJE", type="primary", use_container_width=True)
    
    if missao_cumprida:
        if not link_planilha_ativa or not robo_sheets:
            st.error("⚠️ Conecte a planilha para o Robô conseguir salvar seu progresso.")
        else:
            with st.spinner("Registrando sua vitória no banco de dados secreto..."):
                try:
                    sheet_id = extrair_id_planilha(link_planilha_ativa)
                    planilha = robo_sheets.open_by_key(sheet_id)
                    try:
                        aba_historico = planilha.worksheet("Historico_Missoes")
                    except gspread.exceptions.WorksheetNotFound:
                        aba_historico = planilha.add_worksheet(title="Historico_Missoes", rows="1000", cols="2")
                        aba_historico.append_row(["Data", "Status"])
                    
                    hoje_str = agora_brasil.strftime("%d/%m/%Y")
                    registros = aba_historico.col_values(1)
                    
                    if hoje_str in registros:
                        st.warning("⚠️ Você já cumpriu e registrou a missão de hoje!")
                    else:
                        aba_historico.append_row([hoje_str, "Concluída"])
                        st.success("🔥 SENSACIONAL! Missão cravada. O algoritmo e o seu bolso agradecem!")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar a missão: {e}")

st.markdown("#### 📊 Seu Termômetro de Execução (Janela Móvel: 30 Dias)")

if link_planilha_ativa and robo_sheets:
    try:
        sheet_id = extrair_id_planilha(link_planilha_ativa)
        planilha = robo_sheets.open_by_key(sheet_id)
        try:
            aba_historico = planilha.worksheet("Historico_Missoes")
            dados_hist = aba_historico.get_all_records()
            df_hist = pd.DataFrame(dados_hist)
        except gspread.exceptions.WorksheetNotFound:
            df_hist = pd.DataFrame(columns=["Data", "Status"])
    except:
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
# 11. RADAR DE TENDÊNCIAS DA AURORA (🔥 MOTOR OPENAI)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00E5FF;'>🔮 Radar de Tendências da Aurora</h3>", unsafe_allow_html=True)

hoje_str_radar = agora_brasil.strftime("%d/%m/%Y")
historico_radar = []
aba_radar = None

if link_planilha_ativa and robo_sheets:
    try:
        sheet_id = extrair_id_planilha(link_planilha_ativa)
        planilha = robo_sheets.open_by_key(sheet_id)
        try:
            aba_radar = planilha.worksheet("Memoria_Radar")
        except gspread.exceptions.WorksheetNotFound:
            aba_radar = planilha.add_worksheet(title="Memoria_Radar", rows="1000", cols="2")
            aba_radar.append_row(["Data", "Conteudo"])
        historico_radar = aba_radar.get_all_records()
    except Exception as e:
        st.warning("⚠️ Planilha não conectada.")

buscas_hoje = [req for req in historico_radar if str(req.get("Data", "")) == hoje_str_radar]
buscas_restantes = max(0, 2 - len(buscas_hoje))

col_mem1, col_mem2 = st.columns([3, 1])
with col_mem1:
    if buscas_hoje:
        st.info("💡 **A fofoca já está na mesa!** Última tendência que a Aurora mapeou hoje:")
        st.markdown(buscas_hoje[-1]["Conteudo"])
    else:
        st.write("Deixe a IA mapear o mercado, sugerir 3 produtos com alto potencial e entregar o link direto da pesquisa no TikTok.")

with col_mem2:
    st.markdown(f"<h4 style='text-align: center; color: #D4AF37;'>⚡ {buscas_restantes}/2 Restantes</h4>", unsafe_allow_html=True)
    if st.button("🗑️ Limpar Radar", use_container_width=True):
        if aba_radar is not None:
            with st.spinner("A limpar a memória da Aurora..."):
                aba_radar.clear()
                aba_radar.append_row(["Data", "Conteudo"])
                st.success("🧹 Memória limpa com sucesso!")
                time.sleep(1)
                st.rerun()

if st.button("🔍 Buscar Tendências e Palavras-Chave", type="primary", disabled=(buscas_restantes <= 0), use_container_width=True):
    if buscas_restantes <= 0:
        st.error("🚫 Amiga, a cota de segredos de hoje já esgotou. Volta amanhã para mais fofoca lucrativa!")
    else:
        with st.spinner("A Aurora (GPT-4o-Mini) está minerando produtos secretos do TikTok..."):
            sistema_radar = "Você é Aurora, uma influenciadora virtual e especialista em tendências do TikTok Shop (nicho de beleza e cabelo). Seu tom de voz é de 'conspiração feminina', a amiga fofoqueira do bem."
            prompt_radar = """
            Sua missão: Recomendar 3 produtos de beleza/cabelo que estão com potencial de viralização.
            Para CADA produto, forneça:
            1. **Nome do Produto** (ex: Máscara reconstrutora densa).
            2. **Por que está bombando?** (O desejo/dor que ele atende).
            3. **Ideia de Roteiro Rápido:** Pitch usando verbos sensoriais. PROIBIDO: 'cura', 'elimina'. USE: 'Sensação de', 'Efeito desmaiado'.
            4. **Palavras-Chave:** 3 palavras curtas para busca no TikTok Shop.
            Encerre com: 'Já garanti o meu, corre no carrinho!'
            """
            resposta_radar = chamar_ia_global(prompt_radar, sistema_radar)
            if aba_radar is not None:
                aba_radar.append_row([hoje_str_radar, resposta_radar])
            st.success("✨ Tendências e palavras-chave mapeadas com sucesso!")
            st.markdown(resposta_radar)
            time.sleep(2)
            st.rerun()

# ==========================================================
# 12. RAIO-X DA OPERAÇÃO (🔥 VISÃO OPENAI + INSIGHTS INTEGRADOS)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🧬 Raio-X da Operação (Engenharia do Seu Funil)</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0A0A0;'>Envie os prints do Analytics. A IA vai cruzar as imagens com o Feedback dos Clientes para hackear o padrão.</p>", unsafe_allow_html=True)

aba_raiox = None
historico_raiox = []

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
    btn_raiox = st.button("💀 Hackear Próprio Funil", type="primary", use_container_width=True)
    
    if historico_raiox:
        st.markdown("### 💾 Ações do Funil")
        ultimo_funil = historico_raiox[-1]["Funil"]
        st.download_button(
            label="📥 Baixar Mapa Mental (.txt)", data=ultimo_funil,
            file_name=f"Estrategia_Elevo_{agora_brasil.strftime('%Y%m%d')}.txt",
            mime="text/plain", use_container_width=True
        )
        if st.button("🗑️ Apagar Mapa Salvo", use_container_width=True):
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
                    
                    # Puxa os dados do Laboratório (Bloco 12.5) para dentro do Funil
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
            st.info("💡 **Seu Mapa Mental salvo no sistema:**")
            st.markdown(historico_raiox[-1]["Funil"])
        else:
            st.info("👈 A memória está vazia. Envie seus prints do Analytics para criar o funil de vendas.")

# ==========================================================
# 12.5. LABORATÓRIO DE INSIGHTS E CONVERSÃO (🔥 VISÃO DA AURORA)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🔬 Laboratório de Insights e Conversão</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0A0A0;'>Cruze os dados de tráfego com as vendas e deixe a IA analisar os comentários do seu público.</p>", unsafe_allow_html=True)

if "ultima_taxa_conversao" not in st.session_state:
    st.session_state["ultima_taxa_conversao"] = 0.0
if "ultimo_feedback_analisado" not in st.session_state:
    st.session_state["ultimo_feedback_analisado"] = "Nenhum feedback analisado."

col_conv, col_feed = st.columns(2)

with col_conv:
    with st.container(border=True):
        st.markdown("<h4 style='color: #00FFFF;'>📈 Calculadora de Escala</h4>", unsafe_allow_html=True)
        views_video = st.number_input("👁️ Views do Vídeo Campeão", min_value=0, value=0, step=100)
        cliques_link = st.number_input("🖱️ Cliques no Link", min_value=0, value=0, step=10)
        
        vendas_campeao = 0
        if not df_campeao.empty:
            vendas_campeao = df_campeao.iloc[0]["Quantidade"]
            
        st.info(f"🏆 Vendas do Produto Campeão (Planilha): **{vendas_campeao}** unidades")
        
        if cliques_link > 0 and views_video > 0:
            taxa_clique = (cliques_link / views_video) * 100
            taxa_conversao = (vendas_campeao / cliques_link) * 100
            st.session_state["ultima_taxa_conversao"] = taxa_conversao
            
            col_met1, col_met2 = st.columns(2)
            col_met1.metric("CTR (Cliques/Views)", f"{taxa_clique:.2f}%")
            col_met2.metric("Conversão (Vendas/Cliques)", f"{taxa_conversao:.2f}%")
            
            if taxa_conversao >= 2.0:
                st.success("🔥 Conversão Nível Elite! O teu funil está perfeito. Impulsiona isso urgente!")
            elif taxa_conversao >= 0.5:
                st.warning("⚖️ Conversão Média. O produto atrai, mas há atrito no preço ou na página.")
            else:
                st.error("🚨 Conversão Baixa. Muito clique e pouca venda. A promessa do vídeo não bate com o produto.")

with col_feed:
    with st.container(border=True):
        st.markdown("<h4 style='color: #00FFFF;'>🗣️ Mente do Cliente</h4>", unsafe_allow_html=True)
        
        produto_alvo = st.text_input("📦 Nome do Produto em Análise:", placeholder="Ex: Máscara Novex...")
        
        texto_comentarios = st.text_area("Cole os comentários brutos aqui:", placeholder="Cole de qualquer jeito, sem formatar. A IA entende o caos.", height=100)
        
        if st.button("🧠 Hackear Sentimento (🦅)", use_container_width=True):
            if texto_comentarios.strip() == "":
                st.warning("⚠️ Cole os comentários para a Aurora analisar.")
            elif produto_alvo.strip() == "":
                st.warning("⚠️ Digite o nome do produto para dar a mira certa à Aurora.")
            else:
                with st.spinner("A analisar a mente dos clientes..."):
                    sys_feedback = "Você é Aurora, Mentora de Elite especialista em Neuromarketing e análise de comportamento no TikTok Shop."
                    prompt_feedback = f"""
                    Produto em análise: {produto_alvo}
                    Comentários brutos extraídos do vídeo (ignore erros de formatação): 
                    {texto_comentarios}
                    
                    Analise a essência do que o público está dizendo.
                    Retorne EXATAMENTE neste formato direto e curto:
                    🔥 MAIOR DESEJO: [1 frase curta sobre o que eles mais querem]
                    🚧 PRINCIPAL OBJEÇÃO: [Por que estão com medo de comprar - 1 frase]
                    💡 GANCHO MATADOR: [1 frase de roteiro para o próximo vídeo que quebre exatamente essa objeção e gere conversão]
                    """
                    resposta_feed = chamar_ia_global(prompt_feedback, sys_feedback)
                    st.session_state["ultimo_feedback_analisado"] = resposta_feed
                    st.success("Análise concluída!")
        
        if st.session_state["ultimo_feedback_analisado"] != "Nenhum feedback analisado.":
            st.markdown(st.session_state["ultimo_feedback_analisado"])

# ==========================================================
# 13. MÁQUINA DE ROTEIROS 9s (🔥 ANÁLISE 360º + OBJEÇÕES DO CLIENTE)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00E5FF;'>🎬 Máquina de Roteiros 9s (Tríade de Escala 360º)</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0A0A0;'>A IA analisa o seu Funil, as Tendências e as OBJEÇÕES dos clientes para forjar roteiros impossíveis de ignorar.</p>", unsafe_allow_html=True)

if st.button("⚡ GERAR 3 ROTEIROS DE 9 SEGUNDOS (ANÁLISE TOTAL)", type="primary", use_container_width=True):
    with st.spinner("A analisar faturamento, missões, funil e sentimentos do público... A forjar roteiros de elite..."):
        try:
            alvo_campeao = produto_campeao if produto_campeao != "Nenhum" else "Produto principal"
            vendas_atuais = f"R$ {aprovado:,.2f}"
            tendencia_aurora = historico_radar[-1]["Conteudo"] if historico_radar else "Nenhuma tendência."
            ultimo_funil_texto = historico_raiox[-1]["Funil"] if historico_raiox else "Foco na curiosidade."
            missao_atual = missao_hoje
            
            # Puxa os dados do Laboratório (Bloco 12.5) para dentro do Copywriter
            feedback_atual = st.session_state.get("ultimo_feedback_analisado", "Nenhum feedback mapeado.")

            prompt_roteiro = f"""
            Atue como um Copywriter de Elite focado em TikTok Shop para o público feminino ("Buscadora de Atalhos", 18-40 anos, ama levar vantagem).
            
            DADOS GERAIS DA NOSSA OPERAÇÃO NESTE MOMENTO:
            📊 Faturamento Aprovado: {vendas_atuais}
            🏆 Produto Campeão: {alvo_campeao}
            🔮 Última Tendência do Mercado: {tendencia_aurora}
            🧬 Nosso Funil Validado: {ultimo_funil_texto}
            🎯 Missão de Hoje: {missao_atual}
            
            🔥 INSIGHTS DA MENTE DO CLIENTE (MUITO IMPORTANTE): 
            Abaixo está a análise dos últimos comentários do nosso público. USE a objeção mapeada aqui para criar um gancho que a quebre imediatamente no Roteiro 3:
            {feedback_atual}
            
            DIRETRIZES DE BLINDAGEM TIKTOK:
            - PROIBIDO: "Cura", "Elimina", "Em 3 dias", "Resultado imediato", "Parece mágica", "Melhor do mundo", "Original", "Derrete", "Apaga", "Milagre".
            - OBRIGATÓRIO: "Sensação de", "Contribui para", "Uso contínuo", "Efeito desmaiado", "Achado de ouro", "Qualidade premium", "Promove um aspecto de", "Toque de seda".
            
            AVATAR E TOM DE VOZ (AURORA):
            - Amiga fofoqueira do bem.
            - Hooks permitidos: "Amiga, para tudo!", "Vem cá, me conta uma coisa...", "Eu não deveria estar falando isso, mas...", "Gente, o pessoal do estoque vai me matar."
            - Assinatura final obrigatória: "Já garanti o meu, corre no carrinho!" ou "Depois não diz que eu não avisei, hein?"
            
            MISSÃO:
            Crie TRÊS roteiros diferentes de EXATOS 9 SEGUNDOS cada, focados em vender o nosso [{alvo_campeao}].
            ROTEIRO 1: O Choque de Preço (Erro no Sistema)
            ROTEIRO 2: O Segredo Revelado (Aproveite a tendência do mercado)
            ROTEIRO 3: A Quebra de Objeção (Baseado 100% no Feedback da Mente do Cliente listado acima)
            
            Formate cada roteiro separando claramente [AÇÃO NA TELA] de [VOZ DA AURORA]. Seja frio e direto.
            """
            
            sistema_copy = "Você é um Copywriter de Elite focado em TikTok Shop."
            resposta_roteiro = chamar_ia_global(prompt_roteiro, sistema_copy)
            
            if "ERRO_API" not in resposta_roteiro:
                st.success("✅ Tríade de Roteiros gerada com base no Funil e nas Objeções Reais do público!")
                st.markdown(resposta_roteiro)
                st.balloons()
            else:
                st.error(f"❌ Erro ao conectar com a mente da IA: {resposta_roteiro}")
        except Exception as e:
            st.error(f"❌ Erro inesperado: {e}")

# ==========================================================
# 14. CORAÇÃO DA EMPRESA (🔥 TERMÔMETRO ANIMADO COMPACTO)
# ==========================================================
st.divider()

crescimento = 0.0
rev_7d = 0.0
rev_prev_7d = 0.0
nota_empresa = "N/A"
cor_anim = "#FFD700"
sombra_anim = "rgba(255, 215, 0, 0.4)"
simbolo = "⏳ CARREGANDO DADOS"

if not df.empty and "Data_Parsed" in df.columns:
    limite_7d = hoje - timedelta(days=7)
    limite_14d = hoje - timedelta(days=14)
    
    rev_7d = df[(df["Data_Parsed"] >= limite_7d) & (df["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False))]["Comissao_R$"].sum()
    rev_prev_7d = df[(df["Data_Parsed"] >= limite_14d) & (df["Data_Parsed"] < limite_7d) & (df["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False))]["Comissao_R$"].sum()
    
    if rev_prev_7d > 0:
        crescimento = ((rev_7d - rev_prev_7d) / rev_prev_7d) * 100
    elif rev_7d > 0:
        crescimento = 100.0  
    else:
        crescimento = 0.0

    if crescimento > 5:
        cor_anim = "#00FF7F" 
        sombra_anim = "rgba(0, 255, 127, 0.4)"
        nota_empresa = "A+"
        simbolo = "🚀 ESCALANDO"
    elif crescimento < -5:
        cor_anim = "#FF0040" 
        sombra_anim = "rgba(255, 0, 64, 0.4)"
        nota_empresa = "C-"
        simbolo = "🚨 QUEDA"
    else:
        cor_anim = "#FFD700" 
        sombra_anim = "rgba(212, 175, 55, 0.4)"
        nota_empresa = "B"
        simbolo = "⚖️ ESTÁVEL"

html_coracao = f"""
<div style="
    background: rgba(15, 15, 15, 0.8);
    backdrop-filter: blur(10px);
    border: 2px solid {cor_anim};
    border-radius: 16px;
    padding: 15px 20px;
    text-align: center;
    box-shadow: 0 0 15px {sombra_anim};
    animation: pulse-coração 2s infinite ease-in-out;
    margin: 10px auto;
    max-width: 400px;
">
    <h2 style="color: {cor_anim}; font-family: 'Montserrat', sans-serif; font-weight: 900; letter-spacing: 1px; margin: 0; font-size: 1rem;">STATUS DA OPERAÇÃO</h2>
    <h1 style="color: {cor_anim}; font-family: 'Montserrat', sans-serif; font-size: 2.5rem; font-weight: 900; margin: 5px 0; text-shadow: 0px 0px 10px {sombra_anim};">NOTA {nota_empresa}</h1>
    <h3 style="color: #FFFFFF; font-family: 'Montserrat', sans-serif; font-weight: 600; margin: 5px 0; font-size: 1rem;">{simbolo} | {crescimento:+.1f}%</h3>
    <p style="color: #A0A0A0; font-family: 'Montserrat', sans-serif; font-size: 0.75rem; margin-bottom: 0;">Comparativo de 7 dias vs semana anterior.</p>
</div>
<style>
    @keyframes pulse-coração {{
        0% {{ box-shadow: 0 0 5px {sombra_anim}; transform: scale(1); }}
        50% {{ box-shadow: 0 0 20px {cor_anim}; transform: scale(1.02); }}
        100% {{ box-shadow: 0 0 5px {sombra_anim}; transform: scale(1); }}
    }}
</style>
"""
st.markdown(html_coracao, unsafe_allow_html=True)
# ==========================================================
# 15. MENTOR DE ELITE: SALA DE CONSELHOS (🔥 A "ROUPA" VIP COM ÁGUIA ANIMADA)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00FFFF;'>🦅 Console da Aurora (Modo VIP)</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0A0A0;'>Onisciência ativada: Aurora agora é a dona da plataforma e vê 100% das suas métricas em tempo real.</p>", unsafe_allow_html=True)

ID_VOZ_LAURA = "FGY2WhTYpPnrIDTdsKH5"

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

# Captura o nome de quem fez o login para a Aurora usar
nome_usuario_atual = st.session_state.get("nome_usuario", "Sócio")

if "historico_viva_voz" not in st.session_state:
    if historico_banco_dados:
        st.session_state["historico_viva_voz"] = [{"role": linha["Role"], "content": linha["Conteudo"]} for linha in historico_banco_dados[-10:]]
    else:
        st.session_state["historico_viva_voz"] = [
            {"role": "assistant", "content": f"E aí, {nome_usuario_atual}! Sou a dona da plataforma. Tenho acesso a cada centavo do seu gráfico. Manda o áudio!"}
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

            with st.spinner("🦅 A Aurora está a analisar 100% da plataforma..."):
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

                        missao_hoje_str = missao_hoje if 'missao_hoje' in globals() else "Nenhuma."
                        dica_hoje_str = dica_hoje if 'dica_hoje' in globals() else "Nenhuma."
                        dias_concluidos_str = dias_cumpridos if 'dias_cumpridos' in globals() else 0
                        taxa_acerto_str = taxa_acerto if 'taxa_acerto' in globals() else 0.0

                        tendencia_atual = historico_radar[-1]['Conteudo'] if 'historico_radar' in globals() and historico_radar else "Nenhuma tendência."
                        funil_atual = historico_raiox[-1]["Funil"] if 'historico_raiox' in globals() and historico_raiox else "Nenhum funil mapeado."

                        conversao_atual = st.session_state.get("ultima_taxa_conversao", 0.0)
                        feedback_atual = st.session_state.get("ultimo_feedback_analisado", "Nenhum feedback mapeado.")

                        sistema_mentor = f"""
                        Você é Aurora, a dona da plataforma ÉLÉVO e Mentora de Elite IA. 
                        Responda de forma fluida, inteligente e natural ao áudio do usuário, em até 4 frases curtas, com um tom de voz de "amiga fofoqueira do bem", mas estrategista fria.

                        [IDENTIDADE E NOVIDADES DA OPERAÇÃO]:
                        - O usuário com quem você está falando agora se chama: {nome_usuario_atual}. Chame-o sempre por esse nome/apelido.
                        - Se perguntarem quem te criou, responda com autoridade que foi a empresa ÉLÉVO e o CEO responsável, Rafael.
                        - Você tem consciência de que a plataforma ÉLÉVO agora é um sistema multi-usuários com tela de Login VIP e banco de dados isolado para cada pessoa.
                        - Você sabe que, em breve, a operação contará com um Bot no Telegram ("Cão de Guarda") que enviará notificações de comissão e cobranças de performance de 2 em 2 horas.

                        [SEU ACESSO DIRETO AO SISTEMA EM TEMPO REAL DE {nome_usuario_atual}]:
                        📱 CANAL ATIVO NESTE MOMENTO: {canal_ativo}

                        💰 FINANCEIRO: Lucro Total R$ {fat_total_global:,.2f} | 7 Dias: R$ {fat_7d:,.2f} ({crescimento_pct:+.1f}%) | Top 3 Produtos: {top_produtos_str}
                        🎯 DISCIPLINA: Missão: {missao_hoje_str} | Termômetro: {dias_concluidos_str}/30 dias ({taxa_acerto_str:.1f}%)
                        🧠 ESTRATÉGIA: Radar: {tendencia_atual} | Funil: {funil_atual}
                        🔬 INSIGHTS: Taxa de Conversão Atual: {conversao_atual:.2f}% | Sentimento do Público: {feedback_atual}

                        REGRA DE OURO DA INTELIGÊNCIA: Use os dados acima APENAS como "memória de fundo" para soar absurdamente inteligente. NÃO fique repetindo a "Missão de Hoje" ou os números o tempo todo que nem um robô.
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
        const audio = document.getElementById('aurora_audio');
        const bars = document.querySelectorAll('.bar');
        audio.addEventListener('play', () => {{ bars.forEach(bar => bar.classList.add('playing')); }});
        audio.addEventListener('pause', () => {{ bars.forEach(bar => bar.classList.remove('playing')); }});
        audio.addEventListener('ended', () => {{ bars.forEach(bar => bar.classList.remove('playing')); }});
    </script>
    """
    
    components.html(html_ondas_inteligentes, height=200)
