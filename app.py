import threading
import asyncio
import base64
import requests
import time
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent, LikeEvent, JoinEvent, FollowEvent, ShareEvent
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image
import gspread
import re
import plotly.express as px
import queue
import os
import random
from openai import OpenAI
import io
from gtts import gTTS

# ==========================================================
# 1. CONFIGURAÇÃO DA CHAVE DA IA E DO APP (🔥 V5.0 - MOTOR OPENAI + VOZ RESERVA)
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
# 2. DESIGN E TEMA DINÂMICO (🔥 V5.3 - CONTRASTE ABSOLUTO)
# ==========================================================
import streamlit.components.v1 as components

col_vazia, col_tema = st.columns([8, 2])
with col_tema:
    modo_claro = st.toggle("☀️ Modo Claro", value=False)

# Inteligência de Cores (Dia/Noite)
if modo_claro:
    bg_color = "#F4F4F9"
    text_color = "#333333" 
    card_bg = "rgba(255, 255, 255, 0.9)"
    border_color = "rgba(0, 0, 0, 0.1)"
    metric_val_color = "#B8860B" 
    metric_label_color = "#555555"
else:
    bg_color = "#0E1117"
    text_color = "#F0F0F0" 
    card_bg = "rgba(20, 20, 20, 0.4)"
    border_color = "rgba(212, 175, 55, 0.15)"
    metric_val_color = "#FFD700" 
    metric_label_color = "#E0E0E0" 

estilo_elevo = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;900&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Montserrat', sans-serif !important; }}
    [data-testid="stAppViewContainer"] {{ background-color: {bg_color}; }}
    [data-testid="stSidebar"] {{ background-color: {bg_color}; }}
    
    /* 🔥 O TRUQUE MESTRE PARA O CABEÇALHO 🔥 */
    [data-testid="stHeader"] {{ opacity: 0 !important; height: 0px !important; min-height: 0px !important; pointer-events: none !important; }}
    footer {{ display: none !important; }}

    /* 🚨 CONTRASTE ABSOLUTO */
    [data-testid="stMarkdownContainer"] *,
    [data-testid="stMarkdownContainer"] h1, 
    [data-testid="stMarkdownContainer"] h2, 
    [data-testid="stMarkdownContainer"] h3, 
    [data-testid="stMarkdownContainer"] h4, 
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMarkdownContainer"] b,
    [data-testid="stMarkdownContainer"] em,
    [data-testid="stMarkdownContainer"] i,
    label {{
        color: {text_color} !important;
    }}

    /* Títulos Principais e Cards VIP */
    .titulo-elevo {{
        font-size: 4rem; font-weight: 900; text-align: center;
        background: linear-gradient(270deg, #D4AF37, #00E5FF, #D4AF37);
        background-size: 200% 200%; -webkit-background-clip: text;
        -webkit-text-fill-color: transparent; animation: brilho-evolucao 4s ease infinite;
        margin-bottom: -10px; letter-spacing: 4px; text-transform: uppercase;
        margin-top: 15px;
    }}
    @keyframes brilho-evolucao {{ 0% {{background-position: 0% 50%;}} 50% {{background-position: 100% 50%;}} 100% {{background-position: 0% 50%;}} }}
    
    .subtitulo {{
        text-align: center; font-size: 1.1rem; margin-bottom: 40px;
        font-weight: 300; letter-spacing: 2px; text-transform: uppercase;
        color: {text_color} !important;
    }}
    
    [data-testid="stMetric"] {{
        background: {card_bg}; backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px); border: 1px solid {border_color};
        border-radius: 16px; padding: 20px; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }}
    
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] div, [data-testid="stMetricLabel"] p {{ 
        color: {metric_label_color} !important; 
    }}
    
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] div, [data-testid="stMetricValue"] span {{
        color: {metric_val_color} !important; font-weight: 900 !important;
        font-size: 2.2rem !important; text-shadow: 0px 0px 10px rgba(212, 175, 55, 0.2) !important;
    }}
</style>
"""
st.markdown(estilo_elevo, unsafe_allow_html=True)

# 🎯 INJEÇÃO DA MOEDA ANIMADA E ARRASTÁVEL VIA JAVASCRIPT
js_moeda = """
<script>
    const parent = window.parent.document;
    if (!parent.getElementById("moeda-aguia-vip")) {
        const btn = parent.createElement("div");
        btn.id = "moeda-aguia-vip";
        btn.innerHTML = "🦅";
        btn.style.cssText = "position: fixed; top: 15px; left: 15px; z-index: 999999; font-size: 26px; background: radial-gradient(circle, #FFDF00 0%, #D4AF37 80%, #996515 100%); width: 55px; height: 55px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #FFF8DC; box-shadow: 0px 0px 15px rgba(255,215,0,0.6); cursor: pointer; user-select: none; touch-action: none;";
        parent.body.appendChild(btn);
        const style = parent.createElement('style');
        style.innerHTML = `
            @keyframes girar-moeda-3d { 0% { transform: perspective(400px) rotateY(0deg); } 40% { transform: perspective(400px) rotateY(0deg); } 60% { transform: perspective(400px) rotateY(360deg); } 100% { transform: perspective(400px) rotateY(360deg); } }
            #moeda-aguia-vip { animation: girar-moeda-3d 4s infinite ease-in-out; }
            #moeda-aguia-vip.dragging { animation: none !important; opacity: 0.9; transform: scale(1.1); }
        `;
        parent.head.appendChild(style);
        let isDragging = false, startX, startY, initialLeft, initialTop;
        btn.addEventListener('touchstart', function(e) { isDragging = false; startX = e.touches[0].clientX; startY = e.touches[0].clientY; initialLeft = btn.offsetLeft; initialTop = btn.offsetTop; btn.classList.add('dragging'); }, {passive: false});
        parent.addEventListener('touchmove', function(e) { if (!btn.classList.contains('dragging')) return; let dx = e.touches[0].clientX - startX; let dy = e.touches[0].clientY - startY; if (Math.abs(dx) > 5 || Math.abs(dy) > 5) { isDragging = true; e.preventDefault(); btn.style.left = (initialLeft + dx) + "px"; btn.style.top = (initialTop + dy) + "px"; } }, {passive: false});
        parent.addEventListener('touchend', function(e) { if (!btn.classList.contains('dragging')) return; btn.classList.remove('dragging'); if (!isDragging) toggleSidebar(); isDragging = false; });
        function toggleSidebar() { const openBtn = parent.querySelector('[data-testid="collapsedControl"]'); if (openBtn) { openBtn.click(); } else { const sidebarHeader = parent.querySelector('[data-testid="stSidebarHeader"]'); if (sidebarHeader) { const closeBtn = sidebarHeader.querySelector('button'); if (closeBtn) closeBtn.click(); } } }
    }
</script>
"""
components.html(js_moeda, height=0, width=0)

st.markdown('<div class="titulo-elevo">ÉLÉVO</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">SISTEMA DE INTELIGÊNCIA E ESCALA DE VENDAS</div>', unsafe_allow_html=True)

# ==========================================================
# 3. BARRA LATERAL (SELETOR DE CONTAS E LINK DINÂMICO)
# ==========================================================
st.sidebar.markdown("<h2 style='text-align: center; color: #D4AF37 !important; font-weight: 900; font-size: 2rem;'>⚡ OPERAÇÃO</h2>", unsafe_allow_html=True)

COFRE_DE_LINKS = {
    "O Achado Secreto": "https://docs.google.com/spreadsheets/d/1J5UYfLCQ5rXUmUzxnE5hyG4AYtJEnXlJnN8jAEbH34Y/edit",
    "O Garimpo Chic": "" 
}

opcoes_canais = ["🟢 O Achado Secreto", "🟣 O Garimpo Chic", "➕ Adicionar Novo Canal"]
canal_selecionado = st.sidebar.selectbox("🎯 Selecione a Conta", opcoes_canais)

if canal_selecionado == "➕ Adicionar Novo Canal":
    nome_canal_ativo = st.sidebar.text_input("Nome do Novo Canal", placeholder="Ex: Meu Novo Projeto")
    link_planilha_ativa = st.sidebar.text_input("🔗 Link da Planilha do Google", placeholder="Cole o link de compartilhamento aqui")
else:
    nome_canal_ativo = canal_selecionado.replace("🟢 ", "").replace("🟣 ", "")
    link_salvo = COFRE_DE_LINKS.get(nome_canal_ativo, "")
    if link_salvo != "":
        link_planilha_ativa = link_salvo
        st.sidebar.success("✅ Link carregado do cofre automaticamente!")
    else:
        link_planilha_ativa = st.sidebar.text_input(f"🔗 Link da Planilha ({nome_canal_ativo})", placeholder="Cole o link da planilha correspondente aqui")

filtro_periodo = st.sidebar.selectbox(
    "📅 Filtrar Período",
    ["Hoje", "Ontem", "Últimos 7 Dias", "Últimos 30 Dias", "Mês Atual", "Mês Passado", "Tudo"]
)

prints_comissao = st.sidebar.file_uploader(
    "Suba os Prints do TikTok Shop (Máx: 5 imagens)", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

# ==========================================================
# 4. EXTRATOR DE ID E CARREGAMENTO DE DADOS (🔥 CACHE TURBO 5 MIN)
# ==========================================================
def extrair_id_planilha(url):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else None

# 🔥 Correção da Lentidão: Cache estendido para 300 segundos (5 minutos)
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
    # 🔥 Leitor Blindado: Consegue entender as datas mesmo se o Sheets as bagunçar
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
    
    # Limpa as datas vazias apenas se não for o filtro "Tudo"
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
if not link_planilha_ativa:
    st.info(f"👉 Cole o link da planilha na barra lateral para carregar os dados de '{nome_canal_ativo}'.")
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
        else:
            df_campeao = pd.DataFrame()
            df_timeline = pd.DataFrame()
            produto_campeao = "Nenhum"
    else:
        aprovado = 0.0
        pendente = 0.0
        df_campeao = pd.DataFrame()
        df_timeline = pd.DataFrame()
        produto_campeao = "Nenhum"

    st.markdown(f"### 📊 Faturamento: {nome_canal_ativo}")

    # Formatação de Moeda Padrão BR
    aprovado_str = f"R$ {aprovado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    pendente_str = f"R$ {pendente:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    campeao_str = str(produto_campeao)
    if len(campeao_str) > 12:
        campeao_str = campeao_str[:12] + "..."

    # 🔥 DESIGN NATIVO PARA CELULAR
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

    # Gráficos guardados e blindados
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
# 7. LÓGICA DE PROCESSAMENTO COM IA (🔥 OPENAI)
# ==========================================================
def extrair_dados_do_texto(texto_bruto, nome_canal):
    agora_brasil = datetime.utcnow() - timedelta(hours=3)
    data_hoje = agora_brasil.strftime("%d/%m/%Y")
    
    sistema = "Você é Aurora, a Auditora Financeira de Elite do painel ÉLÉVO."
    prompt = f"""
    INFORMAÇÕES DE SISTEMA:
    - DATA DE HOJE: {data_hoje}
    
    REGRAS INQUEBRÁVEIS:
    1. PROIBIDO USAR GMV: Multiplique o GMV por 0.15 (15%) para achar sua comissão real. NUNCA zere a comissão.
    2. 🔥 REGRA DO PONTO DECIMAL: Use SEMPRE ponto (.) para decimais e não coloque 'R$'. Exemplo: 5.02.
    3. STATUS: Preencha como 'Aprovado'.
    4. DATA: Substitua "Hoje" por {data_hoje}.
    
    🎯 EXEMPLO DE RESPOSTA OBRIGATÓRIA:
    {data_hoje};Nome do Produto;{nome_canal};Aprovado;1;5.02
    
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
# 12. RAIO-X DA OPERAÇÃO (🔥 VISÃO OPENAI ATIVADA)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🧬 Raio-X da Operação (Engenharia do Seu Funil)</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0A0A0;'>Envie até 5 prints do seu Analytics e a IA vai hackear o padrão de sucesso.</p>", unsafe_allow_html=True)

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
                with st.spinner("Apagando estratégia do banco de dados..."):
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
            with st.spinner("Iniciando a Engenharia Reversa com a Visão da OpenAI..."):
                try:
                    sistema_raiox = "Atue como um estrategista mestre em TikTok Shop e Neuromarketing. Sua regra fundamental: 'Eu não vendo produtos. Eu vendo decisões.'"
                    
                    # Prepara o pacote de dados misturando Texto + Imagens
                    conteudo_prompt = []
                    conteudo_prompt.append({
                        "type": "text", 
                        "text": f"Contexto do usuário: {texto_contexto}\nSua missão: Descubra o padrão de sucesso analisando os dados e imagens enviadas. Monte um MAPA MENTAL ESTRATÉGICO e um FUNIL DE VENDAS REPETÍVEL.\n1. O Padrão de Ouro\n2. O Funil Escalável\n3. 3 Ganchos Prontos\n4. Estratégia de Dominação\nSeja frio, analítico e direto."
                    })
                    
                    # Converte os prints para o formato que a OpenAI entende (Base64)
                    if imgs_analytics:
                        for img in imgs_analytics:
                            img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
                            conteudo_prompt.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                            })
                    
                    # Chama o cérebro
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
                    
                    st.success("✅ Raio-X concluído! O mapa foi salvo no sistema.")
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
# 13. FÁBRICA DE ROTEIROS VIP (🔥 MOTOR OPENAI)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00E5FF;'>🎬 Fábrica de Roteiros Sob Demanda</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0A0A0;'>Alimente a Aurora com a descrição e ela lembrará disso mesmo se você fechar o aplicativo.</p>", unsafe_allow_html=True)

aba_roteiros = None
historico_roteiros = []

if link_planilha_ativa and robo_sheets:
    try:
        sheet_id = extrair_id_planilha(link_planilha_ativa)
        planilha = robo_sheets.open_by_key(sheet_id)
        try:
            aba_roteiros = planilha.worksheet("Memoria_Roteiros")
        except gspread.exceptions.WorksheetNotFound:
            aba_roteiros = planilha.add_worksheet(title="Memoria_Roteiros", rows="1000", cols="5")
            aba_roteiros.append_row(["Publico", "Qtd", "Prod1", "Prod2", "Prod3"])
        historico_roteiros = aba_roteiros.get_all_records()
    except Exception:
        pass

mem_publico = ""
mem_qtd = 1
mem_p1 = ""
mem_p2 = ""
mem_p3 = ""

if historico_roteiros:
    ultima_mem = historico_roteiros[-1]
    mem_publico = str(ultima_mem.get("Publico", ""))
    mem_qtd = int(ultima_mem.get("Qtd", 1))
    if mem_qtd not in [1, 2, 3]: mem_qtd = 1
    mem_p1 = str(ultima_mem.get("Prod1", ""))
    mem_p2 = str(ultima_mem.get("Prod2", ""))
    mem_p3 = str(ultima_mem.get("Prod3", ""))

with st.container(border=True):
    col_limpar1, col_limpar2 = st.columns([4, 1])
    with col_limpar2:
        if st.button("🗑️ Limpar Campos", use_container_width=True):
            if aba_roteiros is not None:
                with st.spinner("Limpando memória..."):
                    aba_roteiros.clear()
                    aba_roteiros.append_row(["Publico", "Qtd", "Prod1", "Prod2", "Prod3"])
                st.success("Tudo limpo!")
                time.sleep(1)
                st.rerun()

    col_config1, col_config2 = st.columns([1, 1])
    with col_config1:
        publico_alvo = st.text_input("🎯 Para quem estamos vendendo?", value=mem_publico, placeholder="Ex: Mulheres cacheadas...")
    with col_config2:
        index_qtd = [1, 2, 3].index(mem_qtd)
        qtd_produtos = st.radio("📦 Quantos produtos neste vídeo?", [1, 2, 3], index=index_qtd, horizontal=True)

    st.markdown("#### 📝 Detalhes do(s) Produto(s)")
    descricoes = []
    mem_prods = [mem_p1, mem_p2, mem_p3]
    cols_produtos = st.columns(qtd_produtos)
    for i in range(qtd_produtos):
        with cols_produtos[i]:
            desc = st.text_area(f"Produto {i+1} (Nome e o que ele faz)", value=mem_prods[i], height=120, key=f"desc_prod_{i}")
            descricoes.append(desc)

    if st.button("⚡ FORJAR ROTEIROS DE ELITE", type="primary", use_container_width=True):
        if not publico_alvo or not any(descricoes):
            st.warning("⚠️ Sócio, preencha o público-alvo e pelo menos a descrição do primeiro produto!")
        else:
            if aba_roteiros is not None:
                p1_save = descricoes[0] if len(descricoes) > 0 else ""
                p2_save = descricoes[1] if len(descricoes) > 1 else ""
                p3_save = descricoes[2] if len(descricoes) > 2 else ""
                aba_roteiros.append_row([publico_alvo, qtd_produtos, p1_save, p2_save, p3_save])

            with st.spinner("A Aurora (OpenAI) está aplicando os gatilhos mentais..."):
                produtos_str = ""
                for i, d in enumerate(descricoes):
                    if d.strip(): produtos_str += f"\n- PRODUTO {i+1}: {d.strip()}"

                sistema_copy = "Você é Aurora, uma Copywriter de Elite focada em TikTok Shop e influenciadora virtual. Seu tom de voz é de 'conspiração feminina', a amiga fofoqueira do bem."
                prompt_copy = f"""
                DADOS DO PROJETO:
                - Canal: {nome_canal_ativo}
                - Público-Alvo: {publico_alvo}
                - Produtos: {produtos_str}

                DIRETRIZES DE BLINDAGEM TIKTOK:
                - PROIBIDO: "Cura", "Elimina", "Em 3 dias", "Resultado imediato", "Derrete", "Apaga".
                - SUBSTITUTOS OBRIGATÓRIOS: "Sensação de", "Uso contínuo", "Efeito desmaiado", "Toque de seda".

                Crie UM roteiro de vídeo magnético focado na curiosidade. Formato de lista se for mais de 1 produto.
                ESTRUTURA:
                1. GANCHO (0-3s): Capture a atenção imediatamente.
                2. CORPO: Apresente o(s) produto(s) focando no desejo da audiência.
                3. CTA: Finalize com "Já garanti o meu, corre no carrinho!"
                Formate separando [AÇÃO NA TELA] de [VOZ DA AURORA].
                """
                resposta_copy = chamar_ia_global(prompt_copy, sistema_copy)
                st.success("✅ Roteiro gerado e dados salvos na memória com sucesso!")
                st.markdown(resposta_copy)
                st.balloons()

# ==========================================================
# 14. CORAÇÃO DA EMPRESA (🔥 TERMÔMETRO ANIMADO DE CRESCIMENTO)
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
        simbolo = "🚀 ESCALANDO (LUCRO)"
    elif crescimento < -5:
        cor_anim = "#FF0040" 
        sombra_anim = "rgba(255, 0, 64, 0.4)"
        nota_empresa = "C-"
        simbolo = "🚨 ALERTA DE QUEDA"
    else:
        cor_anim = "#FFD700" 
        sombra_anim = "rgba(212, 175, 55, 0.4)"
        nota_empresa = "B"
        simbolo = "⚖️ ESTÁVEL"

html_coracao = f"""
<div style="
    background: rgba(15, 15, 15, 0.6);
    backdrop-filter: blur(10px);
    border: 2px solid {cor_anim};
    border-radius: 20px;
    padding: 30px;
    text-align: center;
    box-shadow: 0 0 20px {sombra_anim};
    animation: pulse-coração 2s infinite ease-in-out;
    margin-top: 20px;
    margin-bottom: 20px;
">
    <h2 style="color: {cor_anim}; font-family: 'Montserrat', sans-serif; font-weight: 900; letter-spacing: 2px; margin: 0; font-size: 1.5rem;">STATUS DA OPERAÇÃO</h2>
    <h1 style="color: {cor_anim}; font-family: 'Montserrat', sans-serif; font-size: 4.5rem; font-weight: 900; margin: 10px 0; text-shadow: 0px 0px 15px {sombra_anim};">NOTA {nota_empresa}</h1>
    <h3 style="color: #FFFFFF; font-family: 'Montserrat', sans-serif; font-weight: 600; margin: 10px 0;">{simbolo} | {crescimento:+.1f}%</h3>
    <p style="color: #A0A0A0; font-family: 'Montserrat', sans-serif; font-size: 0.9rem; margin-bottom: 0;">Comparativo de lucro dos últimos 7 dias contra a semana anterior.</p>
</div>
<style>
    @keyframes pulse-coração {{
        0% {{ box-shadow: 0 0 10px {sombra_anim}; transform: scale(1); }}
        50% {{ box-shadow: 0 0 35px {cor_anim}; transform: scale(1.02); }}
        100% {{ box-shadow: 0 0 10px {sombra_anim}; transform: scale(1); }}
    }}
</style>
"""
st.markdown(html_coracao, unsafe_allow_html=True)

# ==========================================================
# 15. ESTÚDIO DE TRANSMISSÃO DA AURORA (🔥 VIP + OPENAI + VOZ RESERVA)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00FFFF;'>🎙️ Estúdio VIP Aurora (Painel Profissional)</h3>", unsafe_allow_html=True)

ID_VOZ_LAURA = "FGY2WhTYpPnrIDTdsKH5"

try:
    CHAVE_ELEVENLABS_VIP = st.secrets["ELEVENLABS_API_KEY"]
except KeyError:
    st.error("🚨 ALERTA: Falta a chave ELEVENLABS_API_KEY no cadeado (Secrets).")
    st.stop()

if st.session_state.get("erro_chave"):
    st.error("🚨 ERRO CRÍTICO DE CONEXÃO.")
    st.warning(f"Detalhe Técnico: {st.session_state['erro_chave']}")
    if st.button("🔄 Reconectar e Limpar Erro", type="primary"):
        del st.session_state["erro_chave"]
        st.rerun()
    st.stop()

# 💉 === COFRE DE INJEÇÃO E FUNÇÕES BASE === 💉
ARQUIVO_DOSSIE = "memoria_dossie_aurora.txt"

def ler_dossie_vip():
    if os.path.exists(ARQUIVO_DOSSIE):
        with open(ARQUIVO_DOSSIE, "r", encoding="utf-8") as f: return f.read()
    return ""

def salvar_dossie_vip(texto):
    with open(ARQUIVO_DOSSIE, "w", encoding="utf-8") as f: f.write(texto)

def apagar_dossie_vip():
    if os.path.exists(ARQUIVO_DOSSIE): os.remove(ARQUIVO_DOSSIE)

def extrair_usuario_do_link(entrada):
    if "tiktok.com" in entrada:
        try: return entrada.split("@")[-1].split("/")[0].split("?")[0]
        except: return entrada.replace("@", "").strip()
    return entrada.replace("@", "").strip()

# 🛡️ EXTRATOR BLINDADO DE DADOS 🛡️
def extrair_dados_evento(event):
    nome = "Amiga"
    texto = ""
    for attr in ["comment", "text", "content"]:
        if hasattr(event, attr) and getattr(event, attr):
            texto = str(getattr(event, attr))
            break
    user_obj = getattr(event, "user", None) or getattr(event, "user_info", None)
    if user_obj:
        for attr in ["nickname", "nick_name", "display_name", "unique_id"]:
            val = getattr(user_obj, attr, None)
            if val:
                nome = str(val)
                break
    if nome.lower().startswith("user") and any(c.isdigit() for c in nome):
        nome = "Amiga"
    return nome, texto

# --- ESTADO DA LIVE E COOLDOWNS ---
for key in ["live_rodando", "modo_teste"]:
    if key not in st.session_state: st.session_state[key] = False
for key in ["fila_audios", "log_chat"]:
    if key not in st.session_state: st.session_state[key] = []
if "ultimo_audio_timestamp" not in st.session_state: st.session_state["ultimo_audio_timestamp"] = time.time()

# 🎯 A PRIMEIRA LINHA FICA AQUI:
if "limite_silencio" not in st.session_state: st.session_state["limite_silencio"] = random.uniform(5.0, 10.0) 

if "ultimo_join" not in st.session_state: st.session_state["ultimo_join"] = 0.0
if "ultimo_like" not in st.session_state: st.session_state["ultimo_like"] = 0.0

# --- MOTORES NUCLEARES (COM OPENAI + GTTS) ---
def gerar_audio_base64(texto):
    # TENTATIVA 1: Voz VIP (ElevenLabs)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ID_VOZ_LAURA}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": CHAVE_ELEVENLABS_VIP}
    payload = {"text": texto, "model_id": "eleven_turbo_v2_5", "voice_settings": {"stability": 0.45, "similarity_boost": 0.85, "style": 0.35, "use_speaker_boost": True}}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=8)
        if resp.status_code == 200: 
            return base64.b64encode(resp.content).decode('utf-8')
        else:
            raise Exception("Limite VIP esgotado")
    except:
        # TENTATIVA 2: Tanque de Reserva Gratuito (Google TTS)
        try:
            tts = gTTS(text=texto, lang='pt', tld='com.br')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            return base64.b64encode(fp.read()).decode('utf-8')
        except:
            return None

def processar_comentario_ia(arroba, comentario, produto):
    historico = " | ".join([l for l in st.session_state["log_chat"][-3:] if "❤️" not in l and "👀" not in l])
    sistema = f"Você é Aurora, uma amiga fofoqueira vendendo: {produto}. PROIBIDO falar preços, valores, 'Reais' ou a palavra 'link'. Mande a pessoa no carrinho fixado. Max 2 frases curtas."
    prompt = f"O usuário @{arroba} comentou: '{comentario}'. Responda ele. Não repita: {historico}"
    return chamar_ia_global(prompt, sistema)

# 🛡️ O BUNKER DE THREAD (RADAR COMPLETO) 🛡️
@st.cache_resource
def iniciar_ouvinte_blindado(arroba_real):
    caixa = queue.Queue()
    cliente = TikTokLiveClient(unique_id=arroba_real)

    @cliente.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        caixa.put({"tipo": "sistema", "mensagem": "Conectei na live! Motor OpenAI ativado."})

    @cliente.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        nome, texto = extrair_dados_evento(event)
        if texto: caixa.put({"tipo": "comentario", "nome": nome, "texto": texto})

    @cliente.on(LikeEvent)
    async def on_like(event: LikeEvent):
        nome, _ = extrair_dados_evento(event)
        caixa.put({"tipo": "like", "nome": nome})

    @cliente.on(JoinEvent)
    async def on_join(event: JoinEvent):
        nome, _ = extrair_dados_evento(event)
        caixa.put({"tipo": "join", "nome": nome})
        
    @cliente.on(FollowEvent)
    async def on_follow(event: FollowEvent):
        nome, _ = extrair_dados_evento(event)
        caixa.put({"tipo": "follow", "nome": nome})

    @cliente.on(ShareEvent)
    async def on_share(event: ShareEvent):
        nome, _ = extrair_dados_evento(event)
        caixa.put({"tipo": "share", "nome": nome})

    def _rodar():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try: cliente.run()
        except: pass 

    threading.Thread(target=_rodar, daemon=True).start()
    return cliente, caixa

# --- INTERFACE DO APLICATIVO ---
with st.container(border=True):
    col_live1, col_live2 = st.columns([1, 2])
    with col_live1:
        st.markdown("**🔗 Cole o Link da Live ou o @:**")
        entrada_tiktok = st.text_input("Link ou @", placeholder="https://www.tiktok.com/@...", label_visibility="collapsed")
        if st.session_state["live_rodando"] and not st.session_state["modo_teste"]:
            st.success("🟢 AURORA ONLINE (GPT-4o-Mini)")
        elif st.session_state["live_rodando"] and st.session_state["modo_teste"]: st.warning("🟡 MODO TESTE")

    with col_live2:
        texto_injetado = st.text_area("🦅 Injetar Dossiê do Produto:", value=ler_dossie_vip(), height=90)
        c1, c2 = st.columns(2)
        if c1.button("💉 Gravar Dossiê", use_container_width=True): salvar_dossie_vip(texto_injetado); st.rerun()
        if c2.button("🗑️ Limpar Dossiê", use_container_width=True): apagar_dossie_vip(); st.rerun()
        produto_live = ler_dossie_vip()

    st.markdown("<br>", unsafe_allow_html=True)
    c_btn1, c_btn2, c_btn3 = st.columns(3)
    if c_btn1.button("▶️ INICIAR LIVE", type="primary", use_container_width=True):
        if entrada_tiktok and produto_live:
            arroba = extrair_usuario_do_link(entrada_tiktok)
            st.session_state.update({"live_rodando": True, "modo_teste": False, "fila_audios": [], "log_chat": [f"🔍 Buscando sala de: {arroba}"], "arroba_alvo": arroba})
            st.session_state["ultimo_audio_timestamp"] = time.time()
            st.rerun()

    if c_btn2.button("🛠️ TESTAR OFFLINE", use_container_width=True):
        if produto_live:
            st.session_state.update({"live_rodando": True, "modo_teste": True, "fila_audios": [], "log_chat": ["🟡 Teste Offline."]})
            st.session_state["ultimo_audio_timestamp"] = time.time()
            try: st.session_state["fila_audios"].append(gerar_audio_base64("Sócio, o cérebro da OpenAI está online e o Tanque de Reserva de voz está operante!"))
            except Exception as e: st.session_state["erro_chave"] = str(e)
            st.rerun()

    if c_btn3.button("⏹️ PARAR TUDO", use_container_width=True):
        st.session_state.update({"live_rodando": False, "modo_teste": False, "fila_audios": []})
        st.cache_resource.clear()
        st.rerun()

    # --- CHAT VISUAL VIP ---
    if st.session_state["live_rodando"]:
        st.markdown("### 💬 Monitor do Fantasma (Radar de Dados)")
        chat_html = "<div style='height: 180px; overflow-y: auto; background-color: #1a1a1a; padding: 10px; border-radius: 8px; border: 1px solid #333; display: flex; flex-direction: column-reverse;'>"
        for log in reversed(st.session_state["log_chat"][-15:]):
            cor = "#FF0040" if "⚠️" in log else "#00FF00" if "❤️" in log or "👀" in log or "🌟" in log or "🚀" in log else "#00FFFF" if "SISTEMA" in log or "RÁDIO" in log else "#FFFFFF"
            chat_html += f"<p style='color: {cor}; margin: 3px 0; font-family: monospace; font-size: 14px;'>{log}</p>"
        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)

# --- PROCESSADOR CENTRAL E GATILHOS ---
if st.session_state.get("live_rodando"):
    teve_interacao = False
    try:
        if not st.session_state["modo_teste"]:
            cliente_tiktok, caixa_correio = iniciar_ouvinte_blindado(st.session_state["arroba_alvo"])
            while not caixa_correio.empty() and len(st.session_state["fila_audios"]) < 2:
                carta = caixa_correio.get()
                teve_interacao = True
                agora = time.time()
                
                if carta["tipo"] == "sistema":
                    st.session_state["log_chat"].append(f"🟢 [SISTEMA]: {carta['mensagem']}")
                    audio_b64 = gerar_audio_base64(carta["mensagem"])
                    if audio_b64: st.session_state["fila_audios"].append(audio_b64)

                elif carta["tipo"] == "comentario":
                    st.session_state["log_chat"].append(f"[{carta['nome']}]: {carta['texto']}")
                    resposta = processar_comentario_ia(carta['nome'], carta['texto'], produto_live)
                    st.session_state["log_chat"].append(f"🎙️ [AURORA]: Respondendo {carta['nome']}...")
                    audio_b64 = gerar_audio_base64(resposta)
                    if audio_b64: st.session_state["fila_audios"].append(audio_b64)
                
                # --- INTERAÇÕES SOCIAIS (CUSTO ZERO NA IA) ---
                elif carta["tipo"] == "join":
                    if agora - st.session_state["ultimo_join"] > 18.0:
                        st.session_state["ultimo_join"] = agora
                        nome = carta["nome"]
                        if nome != "Amiga":
                            frases_join = [
                                f"Oi {nome}, seja muito bem-vinda, amiga! Já dá uma olhadinha no nosso carrinho fixado!",
                                f"Olha quem acabou de chegar! Bem-vinda, {nome}! Se tiver alguma dúvida, me manda aqui no chat!",
                                f"Oiê {nome}, que bom que você entrou! Toca na sacolinha aqui embaixo para conferir os achados!"
                            ]
                            texto = random.choice(frases_join)
                            st.session_state["log_chat"].append(f"👀 {nome} entrou na sala.")
                            audio_b64 = gerar_audio_base64(texto)
                            if audio_b64: st.session_state["fila_audios"].append(audio_b64)
                            
                elif carta["tipo"] == "like":
                    if agora - st.session_state["ultimo_like"] > 25.0:
                        st.session_state["ultimo_like"] = agora
                        nome = carta["nome"]
                        frases_like = [
                            f"Obrigada pelas curtidas na live, {nome}! Quem ainda não conferiu o nosso produto no carrinho, corre lá!",
                            f"Amei o carinho aí no coraçãozinho, {nome}! Muito obrigada, amiga!",
                            f"Olha a {nome} enchendo a nossa tela de coração! Obrigada pelo apoio, lindeza!"
                        ]
                        texto = random.choice(frases_like)
                        st.session_state["log_chat"].append(f"❤️ {nome} curtiu a live!")
                        audio_b64 = gerar_audio_base64(texto)
                        if audio_b64: st.session_state["fila_audios"].append(audio_b64)
                
                elif carta["tipo"] == "follow":
                    st.session_state["log_chat"].append(f"🌟 {carta['nome']} começou a seguir!")
                    audio_b64 = gerar_audio_base64(f"Amiga, para tudo! Muito obrigada por seguir o nosso perfil, {carta['nome']}!")
                    if audio_b64: st.session_state["fila_audios"].append(audio_b64)
                    
                elif carta["tipo"] == "share":
                    st.session_state["log_chat"].append(f"🚀 {carta['nome']} compartilhou a live!")
                    audio_b64 = gerar_audio_base64(f"Gente, muito obrigada por compartilhar a nossa live, {carta['nome']}! Você é ouro!")
                    if audio_b64: st.session_state["fila_audios"].append(audio_b64)

        # 🕒 A MÁGICA DA HUMANIZAÇÃO (Rádio Automática OpenAI)
        tempo_silencio = time.time() - st.session_state.get("ultimo_audio_timestamp", time.time())
        limite_atual = st.session_state["limite_silencio"]
        
        # 🎯 A SEGUNDA LINHA FICA AQUI DENTRO DO 'IF':
        if len(st.session_state["fila_audios"]) == 0 and tempo_silencio > limite_atual and not teve_interacao:
            st.session_state["limite_silencio"] = random.uniform(5.0, 10.0) 
            historico = " | ".join([l for l in st.session_state["log_chat"][-3:] if "❤️" not in l and "👀" not in l])
            sistema_radio = f"Você é Aurora em live. Produto: {produto_live}. PROIBIDO PREÇOS E PALAVRA 'LINK'. NÃO REPITA: [{historico}]. Mande ir no CARRINHO."

    # 🎛️ PAINEL VIP DE ÁUDIO
    if len(st.session_state["fila_audios"]) > 0:
        st.session_state["ultimo_audio_timestamp"] = time.time()
        audio_tocar = st.session_state["fila_audios"].pop(0)
        html_vip = f"""
        <style>
            .bar {{ width: 12px; height: 10px; background: #00FFFF; border-radius: 4px; display: inline-block; animation: bounce 0.4s infinite alternate; }}
            .bar:nth-child(2) {{ animation-delay: 0.1s; background: #00BFFF; }}
            .bar:nth-child(3) {{ animation-delay: 0.2s; background: #1E90FF; }}
            .bar:nth-child(4) {{ animation-delay: 0.3s; background: #00BFFF; }}
            .bar:nth-child(5) {{ animation-delay: 0.4s; background: #00FFFF; }}
            @keyframes bounce {{ from {{ height: 10px; opacity: 0.5; }} to {{ height: 40px; opacity: 1; }} }}
            .paused .bar {{ animation: none; height: 10px; background: #444; }}
        </style>
        <div style="background-color: #1a1a1a; padding: 15px; border-radius: 12px; text-align: center; border: 2px solid #00FFFF; box-shadow: 0px 0px 15px rgba(0, 255, 255, 0.2);">
            <h4 style="color: #00FFFF; margin: 0 0 15px 0; font-family: sans-serif;">🎙️ VOZ DA AURORA ATIVA</h4>
            <div id="visualizer" class="" style="display: flex; justify-content: center; align-items: flex-end; gap: 6px; height: 50px;">
                <div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div>
            </div>
            <audio id="aurora_audio" autoplay onplay="document.getElementById('visualizer').classList.remove('paused')" onended="document.getElementById('visualizer').classList.add('paused')">
                <source src="data:audio/mp3;base64,{audio_tocar}" type="audio/mpeg">
            </audio>
            <script>var player = document.getElementById("aurora_audio"); var playPromise = player.play(); if (playPromise !== undefined) {{ playPromise.catch(function(error) {{ console.log("Toque na tela."); }}); }}</script>
        </div>"""
        import streamlit.components.v1 as components
        components.html(html_vip, height=130)
    
    time.sleep(2) 
    st.rerun()
