import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import google.generativeai as genai
from PIL import Image
import gspread
import re

# ==========================================================
# 1. CONFIGURAÇÃO DA CHAVE DA IA E DO APP
# ==========================================================
st.set_page_config(page_title="ÉLÉVO | Painel de Vendas V3.0", page_icon="🦅", layout="wide")

CHAVE_ATIVACAO = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=CHAVE_ATIVACAO)

# 🚀 VERSÃO EXATA EXIGIDA PELO SERVIDOR DO GOOGLE
MODELO_ATIVO = 'gemini-3.8-flash'

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
# 2. DESIGN BLACK, GOLD & NEON
# ==========================================================
estilo_elevo = """
<style>
    .titulo-elevo {
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(270deg, #D4AF37, #00E5FF, #D4AF37);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: brilho-evolucao 4s ease infinite;
        margin-bottom: 5px;
        letter-spacing: 2px;
    }
    @keyframes brilho-evolucao {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .subtitulo {
        text-align: center;
        color: #A0A0A0;
        font-size: 1.2rem;
        margin-bottom: 30px;
        font-weight: 300;
        letter-spacing: 1px;
    }
    hr {
        border-top: 1px solid #D4AF37;
        opacity: 0.3;
    }
</style>
"""
st.markdown(estilo_elevo, unsafe_allow_html=True)

st.markdown('<div class="titulo-elevo">ÉLÉVO</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">SISTEMA DE INTELIGÊNCIA E ESCALA DE VENDAS</div>', unsafe_allow_html=True)

# ==========================================================
# 3. BARRA LATERAL (SELETOR DE CONTAS E LINK DINÂMICO)
# ==========================================================
st.sidebar.markdown("<h2 style='text-align: center; color: #D4AF37 !important;'>⚡ OPERAÇÃO</h2>", unsafe_allow_html=True)

# 🔐 COFRE DE LINKS (Ficam salvos para sempre no sistema)
COFRE_DE_LINKS = {
    "O Achado Secreto": "https://docs.google.com/spreadsheets/d/1J5UYfLCQ5rXUmUzxnE5hyG4AYtJEnXlJnN8jAEbH34Y/edit",
    "O Garimpo Chic": "" # Cole o link da planilha do Garimpo Chic aqui dentro das aspas
}

opcoes_canais = ["🟢 O Achado Secreto", "🟣 O Garimpo Chic", "➕ Adicionar Novo Canal"]
canal_selecionado = st.sidebar.selectbox("🎯 Selecione a Conta", opcoes_canais)

if canal_selecionado == "➕ Adicionar Novo Canal":
    nome_canal_ativo = st.sidebar.text_input("Nome do Novo Canal", placeholder="Ex: Meu Novo Projeto")
    link_planilha_ativa = st.sidebar.text_input("🔗 Link da Planilha do Google", placeholder="Cole o link de compartilhamento aqui")
else:
    nome_canal_ativo = canal_selecionado.replace("🟢 ", "").replace("🟣 ", "")
    
    # Verifica se o canal já tem um link salvo no cofre
    link_salvo = COFRE_DE_LINKS.get(nome_canal_ativo, "")
    
    if link_salvo != "":
        link_planilha_ativa = link_salvo
        st.sidebar.success("✅ Link carregado do cofre automaticamente!")
    else:
        link_planilha_ativa = st.sidebar.text_input(f"🔗 Link da Planilha ({nome_canal_ativo})", placeholder="Cole o link da planilha correspondente aqui")

filtro_periodo = st.sidebar.selectbox(
    "📅 Filtrar Período",
    ["Tudo", "Hoje", "Ontem", "Últimos 3 Dias", "Últimos 7 Dias", "Últimos 30 Dias"]
)

prints_comissao = st.sidebar.file_uploader(
    "Suba os Prints do TikTok Shop (Até 20 arquivos)", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

# ==========================================================
# 4. EXTRATOR DE ID E CARREGAMENTO DE DADOS
# ==========================================================
def extrair_id_planilha(url):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else None

@st.cache_data(ttl=60)
def carregar_dados_dinamicos(url):
    if not url:
        return pd.DataFrame(columns=["Data", "Produto", "Canal", "Status", "Quantidade", "Comissao_R$"])
    
    sheet_id = extrair_id_planilha(url)
    if not sheet_id:
        return pd.DataFrame(columns=["Data", "Produto", "Canal", "Status", "Quantidade", "Comissao_R$"])
        
    url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        return pd.read_csv(url_csv)
    except Exception:
        return pd.DataFrame(columns=["Data", "Produto", "Canal", "Status", "Quantidade", "Comissao_R$"])

df = carregar_dados_dinamicos(link_planilha_ativa)

if not df.empty:
    if "Quantidade" in df.columns:
        df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce").fillna(0)
    else:
        df["Quantidade"] = 0

    if "Comissao_R$" in df.columns:
        df["Comissao_R$"] = pd.to_numeric(
            df["Comissao_R$"].astype(str).str.replace("R$", "", regex=False).str.replace(",", ".", regex=False).str.strip(), 
            errors="coerce"
        ).fillna(0)
    else:
        df["Comissao_R$"] = 0.0

    df["Data_Limpa"] = df["Data"].astype(str).apply(lambda x: x.split(" a ")[-1].strip() if " a " in x else x.strip())
    df["Data_Parsed"] = pd.to_datetime(df["Data_Limpa"], format="%d/%m/%Y", errors="coerce")

# ==========================================================
# 5. APLICAÇÃO DOS FILTROS DE PERÍODO NA BASE
# ==========================================================
df_filtrado = df.copy()
if not df_filtrado.empty and "Data_Parsed" in df_filtrado.columns:
    hoje = pd.Timestamp(datetime.now().date())
    if filtro_periodo == "Hoje":
        df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] == hoje]
    elif filtro_periodo == "Ontem":
        ontem = hoje - timedelta(days=1)
        df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] == ontem]
    elif filtro_periodo == "Últimos 3 Dias":
        limite = hoje - timedelta(days=3)
        df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] >= limite]
    elif filtro_periodo == "Últimos 7 Dias":
        limite = hoje - timedelta(days=7)
        df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] >= limite]
    elif filtro_periodo == "Últimos 30 Dias":
        limite = hoje - timedelta(days=30)
        df_filtrado = df_filtrado[df_filtrado["Data_Parsed"] >= limite]

if df_filtrado.empty and filtro_periodo != "Tudo":
    df_filtrado = df.copy()

# ==========================================================
# 6. DASHBOARD FINANCEIRO E GRÁFICO (VERSÃO 3.0)
# ==========================================================
if not link_planilha_ativa:
    st.info(f"👉 Cole o link da planilha na barra lateral para carregar os dados de '{nome_canal_ativo}'. O painel ficará branco até a planilha ser conectada.")
else:
    if not df_filtrado.empty:
        aprovado = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False)]["Comissao_R$"].sum()
        pendente = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("pendente", na=False)]["Comissao_R$"].sum()
        
        df_validos = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False)]
        if not df_validos.empty:
            df_campeao = df_validos.groupby("Produto")[["Quantidade", "Comissao_R$"]].sum().reset_index()
            df_campeao = df_campeao.sort_values(by=["Comissao_R$"], ascending=False)
            produto_campeao = df_campeao.iloc[0]["Produto"]
        else:
            df_campeao = pd.DataFrame()
            produto_campeao = "Nenhum"
    else:
        aprovado = 0.0
        pendente = 0.0
        df_campeao = pd.DataFrame()
        produto_campeao = "Nenhum"

    st.markdown(f"### 📊 Faturamento: {nome_canal_ativo} (Filtro: {filtro_periodo})")
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Lucro Aprovado", f"R$ {aprovado:,.2f}", "Sincronizado")
    col2.metric("⏳ Em Trânsito (Pendente)", f"R$ {pendente:,.2f}", "Aguardando entrega")
    col3.metric("🏆 Produto Campeão", str(produto_campeao), "Maior volume de lucro")

    if not df_campeao.empty:
        st.markdown("##### 📈 Top Produtos por Comissão (R$)")
        df_grafico = df_campeao.set_index("Produto")["Comissao_R$"]
        st.bar_chart(df_grafico, color="#D4AF37")

st.divider()

# ==========================================================
# 7. LÓGICA DE PROCESSAMENTO COM IA (MODELO 3.8-FLASH)
# ==========================================================
def extrair_dados_do_print(imagem_upload, nome_canal):
    modelo = genai.GenerativeModel(MODELO_ATIVO)
    imagem_pil = Image.open(imagem_upload)
    
    prompt = f"""
    Analise esta imagem do painel de dados ou produtos do TikTok Shop.
    Extraia as informações e retorne APENAS os dados brutos, sem markdown.
    Formato OBRIGATÓRIO (separado por ponto e vírgula):
    DD/MM/AAAA;Nome do Produto;{nome_canal};Status;Quantidade;ValorDaComissao
    """
    try:
        resposta = modelo.generate_content([prompt, imagem_pil])
        return resposta.text.replace("```csv", "").replace("```text", "").replace("```", "").strip()
    except Exception as e:
        return f"ERRO_API: {str(e)}"

def extrair_dados_do_texto(texto_bruto, nome_canal):
    modelo = genai.GenerativeModel(MODELO_ATIVO)
    prompt = f"""
    Analise o texto abaixo copiado de um painel de vendas.
    Extraia as informações e retorne APENAS os dados brutos, sem markdown.
    Formato OBRIGATÓRIO de cada linha (separado por ponto e vírgula):
    DD/MM/AAAA;Nome do Produto;{nome_canal};Status;Quantidade;ValorDaComissao
    
    Texto copiado:
    {texto_bruto}
    """
    try:
        resposta = modelo.generate_content(prompt)
        return resposta.text.replace("```csv", "").replace("```text", "").replace("```", "").strip()
    except Exception as e:
        return f"ERRO_API: {str(e)}"

# ==========================================================
# 8. AUDITORIA E INJEÇÃO DE DADOS (IMAGEM E TEXTO)
# ==========================================================
if "dados_prontos" not in st.session_state:
    st.session_state["dados_prontos"] = []

st.markdown("### 🤖 Motor de Auditoria e Injeção (IA)")

aba_imagem, aba_texto = st.tabs(["📸 Leitor de Prints", "📝 Leitor de Texto (Plano B)"])

with aba_imagem:
    if prints_comissao:
        if st.button("🚀 Extrair Dados das Imagens", type="primary"):
            st.session_state["dados_prontos"] = []
            barra_progresso = st.progress(0)
            
            with st.spinner(f"A IA ({MODELO_ATIVO}) está analisando as imagens..."):
                for idx, arquivo in enumerate(prints_comissao):
                    texto_ia = extrair_dados_do_print(arquivo, nome_canal_ativo)
                    time.sleep(3)
                    
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
                    barra_progresso.progress((idx + 1) / len(prints_comissao))

with aba_texto:
    st.write("Copie o relatório do TikTok Shop ou do WhatsApp e cole abaixo:")
    texto_copiado = st.text_area("Cole os dados brutos aqui:", height=150)
    
    if st.button("🚀 Extrair Dados do Texto", type="primary"):
        if texto_copiado.strip() == "":
            st.warning("⚠️ Cole algum texto antes de pedir para a IA ler!")
        else:
            st.session_state["dados_prontos"] = []
            barra_progresso_texto = st.progress(10)
            
            with st.spinner(f"A IA ({MODELO_ATIVO}) está organizando o texto copiado..."):
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
                        st.error("⚠️ A IA leu o texto, mas não encontrou os dados no formato correto. Verifique se copiou corretamente!")
                else:
                    st.error(f"⚠️ Erro na IA ao ler o texto: {texto_ia}")

if st.session_state["dados_prontos"]:
    st.success("✨ Dados lidos com sucesso! ✍️ Pode EDITAR as células na tabela abaixo antes de enviar:")
    df_novos = pd.DataFrame(st.session_state["dados_prontos"])
    
    df_editado = st.data_editor(df_novos, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 INJETAR DADOS NA PLANILHA", type="primary"):
        if not link_planilha_ativa:
            st.error("⚠️ Cole o link da planilha na barra lateral primeiro!")
        elif not robo_sheets:
            st.error("⚠️ Robô não conectado. Verifique os Secrets.")
        else:
            with st.spinner("O Robô está injetando os dados no Google Drive..."):
                try:
                    sheet_id = extrair_id_planilha(link_planilha_ativa)
                    planilha = robo_sheets.open_by_key(sheet_id)
                    aba = planilha.sheet1
                    
                    dados_finais = df_editado.to_dict('records')
                    linhas_inserir = [[str(d["Data"]), str(d["Produto"]), str(d["Canal"]), str(d["Status"]), str(d["Quantidade"]), str(d["Comissao_R$"])] for d in dados_finais]
                    
                    aba.append_rows(linhas_inserir, value_input_option="USER_ENTERED")
                    
                    st.success("🔥 SUCESSO ABSOLUTO! Planilha atualizada automaticamente!")
                    st.balloons()
                    st.session_state["dados_prontos"] = [] 
                except Exception as e:
                    st.error(f"❌ Erro ao escrever na planilha. Detalhe: {e}")

# ==========================================================
# 9. TABELA DA CURVA DE EVOLUÇÃO
# ==========================================================
st.markdown(f"### 🚀 Curva de Evolução dos Produtos ({filtro_periodo})")
if not df_filtrado.empty:
    colunas_visiveis = [c for c in df_filtrado.columns if c != "Data_Parsed"]
    st.dataframe(df_filtrado[colunas_visiveis], use_container_width=True)
else:
    st.info("Nenhum dado encontrado para o período selecionado.")

# ==========================================================
# 10. MINDSET MILIONÁRIO & MISSÃO DO DIA (GAMIFICAÇÃO)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🧠 Mindset & Missão Diária</h3>", unsafe_allow_html=True)

dia_do_ano = datetime.now().timetuple().tm_yday

frases_motivacionais = [
    "O sucesso é a soma de pequenos esforços repetidos dia após dia.",
    "Não espere por oportunidades, crie-as. Grave aquele vídeo agora!",
    "A constância é a chave que abre a porta da escala.",
    "O seu próximo vídeo pode ser o que vai te deixar milionário. Não pare!",
    "Feito é melhor que perfeito. Ajuste a rota enquanto caminha!",
    "Se você não construir o seu sonho, alguém vai te contratar para construir o dele.",
    "Foco no processo. O resultado é só uma consequência natural."
]

missoes = [
    "Gravar e postar 5 vídeos originais hoje usando a técnica do gancho forte.",
    "Analisar 3 produtos novos na 'peneira' do TikTok e favoritar o melhor.",
    "Gravar 3 vídeos review focados no seu Produto Campeão atual.",
    "Revisar o vídeo que mais vendeu na semana e replicar o mesmo estilo hoje.",
    "Responder a 10 comentários de seguidores para engajar o algoritmo.",
    "Fazer 1 vídeo longo detalhado (mais de 1 minuto) sobre os benefícios de um produto.",
    "Passar 30 minutos estudando vídeos gringos para pegar referências novas."
]

dicas_investimento = [
    "Pegue 20% da comissão e invista na operação (tráfego, microfone, iluminação).",
    "Construa uma reserva de emergência da operação. Não gaste todo o lucro no primeiro mês!",
    "Reinvista no Produto Campeão. Se está vendendo orgânico, imagina com um pouco de impulsionamento!",
    "Diversificação: Que tal guardar parte do lucro no Tesouro Direto ou CDB para render juros?",
    "O melhor investimento no começo é em conhecimento. Estude copy e retenção de público.",
    "Separe o dinheiro da pessoa física do dinheiro da empresa (operação TikTok).",
    "Não aumente seu custo de vida só porque as primeiras comissões entraram. Tenha visão de longo prazo."
]

frase_hoje = frases_motivacionais[dia_do_ano % len(frases_motivacionais)]
missao_hoje = missoes[dia_do_ano % len(missoes)]
dica_hoje = dicas_investimento[dia_do_ano % len(dicas_investimento)]

col_mindset, col_missao = st.columns(2)

with col_mindset:
    st.info(f"💎 **Visão de Águia:** {frase_hoje}")
    st.warning(f"📈 **Dica Financeira:** {dica_hoje}")
    
with col_missao:
    st.markdown(f"🎯 **Sua Missão de Hoje:** {missao_hoje}")
    
    missao_cumprida = st.checkbox("✅ Marcar missão de hoje como cumprida!")
    
    if missao_cumprida:
        st.success("🔥 SENSACIONAL! Missão Cumprida! O algoritmo agradece e o seu bolso também. Continue empilhando vitórias!")
        st.balloons()

# ==========================================================
# 11. RADAR DE TENDÊNCIAS DA AURORA (INTELIGÊNCIA DE MERCADO)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #00E5FF;'>🔮 Radar de Tendências da Aurora</h3>", unsafe_allow_html=True)
st.write("Deixe a IA mapear o mercado e sugerir os 3 produtos de beleza/cabelo com maior potencial de viralização no TikTok nesta semana.")

if st.button("🔍 Buscar Top 3 Produtos em Alta", type="primary"):
    with st.spinner(f"A Aurora (usando o modelo {MODELO_ATIVO}) está vasculhando as tendências do TikTok..."):
        try:
            modelo_radar = genai.GenerativeModel(MODELO_ATIVO)
            prompt_radar = """
            Atue como Aurora, uma influenciadora virtual e especialista em tendências do TikTok Shop (focada no nicho de beleza, cabelo e achados femininos).
            Seu tom de voz é de 'conspiração feminina', a amiga fofoqueira do bem. Você não vende, você conta segredos.
            Comece o texto com um hook forte de voz, como: 'Amiga, para tudo!', 'Vem cá, me conta uma coisa...', 'Eu não deveria estar falando isso, mas...' ou 'Gente, o pessoal do estoque vai me matar.'
            
            Sua missão: Recomendar 3 tipos de produtos de beleza ou cabelo que estão com alto potencial de viralização nesta semana.
            Para cada produto, forneça:
            1. **Nome/Tipo do Produto** (ex: Máscara reconstrutora densa, Óleo capilar premium).
            2. **Por que está bombando?** (O desejo/dor que ele atende na Buscadora de Atalhos).
            3. **Ideia de Roteiro Rápido:** Crie um pitch de vendas curto usando verbos de experiência sensorial. 
            REGRA CRÍTICA PARA O ROTEIRO: É totalmente proibido usar palavras de cura ou milagre (nada de 'cura', 'elimina', 'resultado imediato', 'conserta'). Substitua obrigatoriamente por 'Sensação de', 'Promove um aspecto de', 'Auxilia na redução do aspecto de', 'Efeito desmaiado', 'Toque de seda' ou 'Achado de ouro'.
            
            Encerre com uma assinatura do tipo: 'Já garanti o meu, corre no carrinho!' ou 'Depois não diz que eu não avisei, hein?'
            """
            resposta_radar = modelo_radar.generate_content(prompt_radar)
            st.success("✨ Tendências mapeadas com sucesso! Olha o que a Aurora descobriu:")
            st.markdown(resposta_radar.text)
        except Exception as e:
            st.error(f"Erro ao buscar tendências: {e}")
