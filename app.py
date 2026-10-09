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

try:
    df = pd.read_csv(url_google_sheets)
except Exception:
    df = pd.DataFrame(columns=["Data", "Produto", "Canal", "Status", "Quantidade", "Comissao_R$"])

# Padroniza e limpa os dados da base
if not df.empty:
    # Garante que a coluna de quantidade seja numérica
    if "Quantidade" in df.columns:
        df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce").fillna(0)
    else:
        df["Quantidade"] = 0

    # Limpa formatações de moeda na coluna de comissão
    if "Comissao_R$" in df.columns:
        df["Comissao_R$"] = pd.to_numeric(
            df["Comissao_R$"].astype(str).str.replace("R$", "", regex=False).str.replace(",", ".", regex=False).str.strip(), 
            errors="coerce"
        ).fillna(0)
    else:
        df["Comissao_R$"] = 0.0

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
# 5. CÁLCULO INTELIGENTE DO PAINEL FINANCEIRO E PRODUTO CAMPEÃO
# ==========================================================
if not df.empty:
    aprovado = df[df["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False)]["Comissao_R$"].sum()
    pendente = df[df["Status"].astype(str).str.lower().str.contains("pendente", na=False)]["Comissao_R$"].sum()
    
    # Identifica o Produto Campeão cruzando a maior quantidade vendida ou maior comissão acumulada
    df_validos = df[df["Status"].astype(str).str.lower().str.contains("aprovado|estimado", na=False)]
    if not df_validos.empty:
        # Agrupa por produto somando quantidade e comissão para achar o verdadeiro líder
        df_campeao = df_validos.groupby("Produto")[["Quantidade", "Comissao_R$"]].sum().reset_index()
        df_campeao = df_campeao.sort_values(by=["Quantidade", "Comissao_R$"], ascending=False)
        produto_campeao = df_campeao.iloc[0]["Produto"] if not df_campeao.empty else "Nenhum"
    else:
        produto_campeao = "Nenhum"
else:
    aprovado = 0.0
    pendente = 0.0
    produto_campeao = "Nenhum"

st.markdown(f"### 📊 Faturamento do Mês (Filtro: {filtro_periodo})")
col1, col2, col3 = st.columns(3)
col1.metric("💰 Lucro Aprovado", f"R$ {aprovado:,.2f}", f"Sincronizado com o Drive")
col2.metric("⏳ Em Trânsito (Pendente)", f"R$ {pendente:,.2f}", "Aguardando entrega")
col3.metric("🏆 Produto Campeão", str(produto_campeao), "Maior volume de vendas")

st.divider()

# ==========================================================
# 6. LÓGICA DE PROCESSAMENTO COM IA (CALIBRADA PARA 6 COLUNAS)
# ==========================================================
def extrair_dados_do_print(imagem_upload):
    modelo = genai.GenerativeModel('gemini-3.8-flash')
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
# 7. GALERIA E BOTÃO DE ATIVAÇÃO DA IA
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
            
            with st.spinner("A IA está a auditar os prints e a atualizar a base..."):
                for idx, arquivo in enumerate(prints_comissao):
                    texto_ia = extrair_dados_do_print(arquivo)
                    time.sleep(4)  # Pausa de segurança anti-bloqueio de cota
                    
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
                df_novos = pd.DataFrame(novos_dados)
                df_atualizado = pd.concat([df, df_novos], ignore_index=True)
                df_atualizado.to_csv("dados_vendas.csv", index=False)
                st.success("✨ Auditoria concluída e sincronizada com sucesso!")
                st.rerun()
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
# 8. TABELA DA CURVA DE EVOLUÇÃO
# ==========================================================
st.markdown(f"### 🚀 Curva de Evolução dos Produtos ({filtro_periodo})")
if not df.empty:
    st.dataframe(df, use_container_width=True)
else:
    st.info("A planilha do Google Drive está vazia ou aguardando dados.")