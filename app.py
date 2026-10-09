import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import google.generativeai as genai
from PIL import Image

# ==========================================================
# 1. CONFIGURAÇÃO DA CHAVE DA IA E DO APP
# ==========================================================
st.set_page_config(page_title="ÉLÉVO | Painel de Vendas", page_icon="🦅", layout="wide")

CHAVE_ATIVACAO = "AQ.Ab8RN6JrFhGGwCiPTi_KPsgrNX-ZggAivW_l1zeW9ln1bFZLNQ"
genai.configure(api_key=CHAVE_ATIVACAO)

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
# 3. CONEXÃO DIRETA COM O GOOGLE DRIVE (PLANILHA ONLINE)
# ==========================================================
SHEET_ID = "1J5UYfLCQ5rXUmUzxnE5hyG4AYtJEnXlJnN8jAEbH34Y"
url_google_sheets = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60)
def carregar_dados_drive():
    try:
        return pd.read_csv(url_google_sheets)
    except Exception:
        return pd.DataFrame(columns=["Data", "Produto", "Canal", "Status", "Quantidade", "Comissao_R$"])

df = carregar_dados_drive()

# Padroniza e limpa os dados da base
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

    # =================================================================
    # CORREÇÃO AQUI: Lógica inteligente para ler períodos na planilha!
    # Se ele achar "08/09 a 07/10/2026", ele pega só o "07/10/2026" para o cálculo matemático
    # =================================================================
    df["Data_Limpa"] = df["Data"].astype(str).apply(lambda x: x.split(" a ")[-1].strip() if " a " in x else x.strip())
    df["Data_Parsed"] = pd.to_datetime(df["Data_Limpa"], format="%d/%m/%Y", errors="coerce")# Padroniza e limpa os dados da base
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

    # =================================================================
    # CORREÇÃO AQUI: Lógica inteligente para ler períodos na planilha!
    # Se ele achar "08/09 a 07/10/2026", ele pega só o "07/10/2026" para o cálculo matemático
    # =================================================================
    df["Data_Limpa"] = df["Data"].astype(str).apply(lambda x: x.split(" a ")[-1].strip() if " a " in x else x.strip())
    df["Data_Parsed"] = pd.to_datetime(df["Data_Limpa"], format="%d/%m/%Y", errors="coerce")

# ==========================================================
# 4. BARRA LATERAL (FILTRO DE PERÍODO E UPLOAD DE PRINTS)
# ==========================================================
st.sidebar.markdown("<h2 style='text-align: center; color: #D4AF37 !important;'>⚡ OPERAÇÃO</h2>", unsafe_allow_html=True)

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

# Se o filtro retornar vazio por causa de datas em formato de período (ex: 08/09 a 07/10), exibe a base completa para não zerar a tela
if df_filtrado.empty and filtro_periodo != "Tudo":
    df_filtrado = df.copy()

# ==========================================================
# 6. CÁLCULO INTELIGENTE DO PAINEL FINANCEIRO E PRODUTO CAMPEÃO
# ==========================================================
if not df_filtrado.empty:
    aprovado = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False)]["Comissao_R$"].sum()
    pendente = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("pendente", na=False)]["Comissao_R$"].sum()
    
    df_validos = df_filtrado[df_filtrado["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False)]
    if not df_validos.empty:
        df_campeao = df_validos.groupby("Produto")[["Quantidade", "Comissao_R$"]].sum().reset_index()
        df_campeao = df_campeao.sort_values(by=["Quantidade", "Comissao_R$"], ascending=False)
        produto_campeao = df_campeao.iloc[0]["Produto"] if not df_campeao.empty else "Nenhum"
    else:
        produto_campeao = "Nenhum"
else:
    aprovado = 0.0
    pendente = 0.0
    produto_campeao = "Nenhum"

st.markdown(f"### 📊 Faturamento do Período (Filtro: {filtro_periodo})")
col1, col2, col3 = st.columns(3)
col1.metric("💰 Lucro Aprovado", f"R$ {aprovado:,.2f}", f"Sincronizado com o Drive")
col2.metric("⏳ Em Trânsito (Pendente)", f"R$ {pendente:,.2f}", "Aguardando entrega")
col3.metric("🏆 Produto Campeão", str(produto_campeao), "Maior volume de vendas")

st.divider()

# ==========================================================
# 7. LÓGICA DE PROCESSAMENTO COM IA (CALIBRADA PARA 6 COLUNAS)
# ==========================================================
def extrair_dados_do_print(imagem_upload):
    # CORREÇÃO APLICADA: Nome do modelo oficial para leitura rápida de imagens
    modelo = genai.GenerativeModel('gemini-1.5-flash')
    imagem_pil = Image.open(imagem_upload)
    
    prompt = """
    Analise esta imagem do painel de dados ou produtos do TikTok Shop.
    Extraia as informações e retorne APENAS os dados brutos, sem markdown, sem cabeçalhos e sem formatação.
    Formato OBRIGATÓRIO de cada linha separada por ponto e vírgula:
    DD/MM/AAAA;Nome do Produto;TikTok;Status;Quantidade;ValorDaComissao
    
    Exemplo exato do que você deve retornar (e nada mais):
    08/10/2026;Reconstrutor Novex Max Keratin;TikTok;Aprovado;240;450.00
    """
    try:
        resposta = modelo.generate_content([prompt, imagem_pil])
        texto_limpo = resposta.text.replace("```csv", "").replace("```text", "").replace("```", "").strip()
        return texto_limpo
    except Exception as e:
        return f"ERRO_API: {str(e)}"

# ==========================================================
# 8. GALERIA E BOTÃO DE ATIVAÇÃO DA IA
# ==========================================================
st.markdown("### 🖼️ Auditoria de Comissões por IA")
if prints_comissao:
    if len(prints_comissao) > 20:
        st.error("⚠️ Máximo de 20 prints por vez!")
    else:
        st.success(f"📸 {len(prints_comissao)} print(s) na fila.")
        
        if st.button("🚀 Processar Prints", type="primary"):
            novos_dados = []
            erros_encontrados = False
            
            barra_progresso = st.progress(0)
            total_arquivos = len(prints_comissao)
            
            with st.spinner("A IA está a auditar os prints... (Lembre-se de colar os novos dados na planilha do Google Drive para fixar na base oficial)"):
                for idx, arquivo in enumerate(prints_comissao):
                    texto_ia = extrair_dados_do_print(arquivo)
                    time.sleep(4)
                    
                    if "ERRO_API:" in texto_ia:
                        st.error(f"❌ Erro no print '{arquivo.name}': {texto_ia}")
                        erros_encontrados = True
                        continue
                    
                    if texto_ia:
                        linhas = texto_ia.split('\n')
                        for linha in linhas:
                            linha = linha.strip()
                            if not linha or "Data;" in linha or "Produto;" in linha:
                                continue
                                
                            itens = linha.split(';')
                            if len(itens) >= 6:
                                novos_dados.append({
                                    "Data": itens[0].strip(),
                                    "Produto": itens[1].strip(),
                                    "Canal": itens[2].strip(),
                                    "Status": itens[3].strip(),
                                    "Quantidade": itens[4].strip(),
                                    "Comissao_R$": itens[5].strip()
                                })
                    
                    barra_progresso.progress((idx + 1) / total_arquivos)
                
            if novos_dados:
                st.success("✨ Prints auditados com sucesso pela IA! Copie as linhas geradas abaixo e cole na sua planilha do Google Drive:")
                df_novos = pd.DataFrame(novos_dados)
                st.dataframe(df_novos, use_container_width=True)
            elif not erros_encontrados:
                st.warning("A IA processou as imagens, mas não encontrou o padrão exato de comissão.")

        cols = st.columns(4)
        for i, arquivo in enumerate(prints_comissao):
            with cols[i % 4]:
                st.image(arquivo, caption=f"Print {i+1}", use_container_width=True)
else:
    st.info("Envie os teus prints na barra lateral para começar a auditoria automática.")

st.divider()

# ==========================================================
# 9. TABELA DA CURVA DE EVOLUÇÃO
# ==========================================================
st.markdown(f"### 🚀 Curva de Evolução dos Produtos ({filtro_periodo})")
if not df_filtrado.empty:
    # Exibe a tabela sem a coluna auxiliar de data parseada
    colunas_visiveis = [c for c in df_filtrado.columns if c != "Data_Parsed"]
    st.dataframe(df_filtrado[colunas_visiveis], use_container_width=True)
else:
    st.info("Nenhum dado encontrado para o período selecionado.")

# ==========================================================
# 10. MINDSET MILIONÁRIO & MISSÃO DO DIA (GAMIFICAÇÃO)
# ==========================================================
st.divider()
st.markdown("<h3 style='text-align: center; color: #D4AF37;'>🧠 Mindset & Missão Diária</h3>", unsafe_allow_html=True)

# Pega o dia do ano para rotacionar as frases/missões automaticamente sem repetir logo
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

# Seleciona o conteúdo baseado no dia 
frase_hoje = frases_motivacionais[dia_do_ano % len(frases_motivacionais)]
missao_hoje = missoes[dia_do_ano % len(missoes)]
dica_hoje = dicas_investimento[dia_do_ano % len(dicas_investimento)]

col_mindset, col_missao = st.columns(2)

with col_mindset:
    st.info(f"💎 **Visão de Águia:** {frase_hoje}")
    st.warning(f"📈 **Dica Financeira:** {dica_hoje}")
    
with col_missao:
    st.markdown(f"🎯 **Sua Missão de Hoje:** {missao_hoje}")
    
    # Caixa de seleção para cumprir a missão
    missao_cumprida = st.checkbox("✅ Marcar missão de hoje como cumprida!")
    
    if missao_cumprida:
        st.success("🔥 SENSACIONAL! Missão Cumprida! O algoritmo agradece e o seu bolso também. Continue empilhando vitórias!")
        st.balloons() # Solta animação de balões na tela!
