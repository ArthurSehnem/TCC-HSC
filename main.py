import streamlit as st
import base64
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import hashlib
import re

# -------------------
# Configurações e Constantes
# -------------------
st.set_page_config(
    page_title="Sistema de Manutenção | HSC",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações de estilo
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79, #2d5aa0);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f0f8ff;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f4e79;
        margin: 0.5rem 0;
    }
    .alert-card {
        background: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin: 0.5rem 0;
    }
    .success-card {
        background: #d4edda;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa, #e9ecef);
    }
</style>
""", unsafe_allow_html=True)

# Constantes
SETORES_PADRAO = [
    "Hemodiálise", 
    "Lavanderia", 
    "Instrumentais Cirúrgicos",
    "UTI",
    "Centro Cirúrgico", 
    "Radiologia",
    "Laboratório",
    "Emergência"
]

TIPOS_MANUTENCAO = [
    "Preventiva", 
    "Corretiva", 
    "Urgente", 
    "Calibração", 
    "Higienização",
    "Inspeção"
]

STATUS_EQUIPAMENTOS = ["Ativo", "Inativo", "Em manutenção", "Aguardando peças"]

# -------------------
# Sistema de Login Melhorado
# -------------------
ADMIN_EMAIL = st.secrets["login"]["email"]
ADMIN_PASSWORD = st.secrets["login"]["password"]

def hash_password(password: str) -> str:
    """Hash da senha para comparação segura"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email: str) -> bool:
    """Validação básica de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def login():
    st.markdown('<div class="main-header"><h1>🏥 Sistema HSC - Login</h1></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("⚠️ **Acesso Restrito**\n\nApenas profissionais autorizados do Hospital Santa Cruz podem acessar este sistema.")
        
        with st.form("login_form"):
            email = st.text_input("📧 Email", placeholder="seu.email@hsc.com.br")
            senha = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
            
            col_login, col_help = st.columns([1, 1])
            with col_login:
                submitted = st.form_submit_button("🔐 Entrar", use_container_width=True)
            with col_help:
                if st.form_submit_button("❓ Esqueci a senha", use_container_width=True):
                    st.info("Entre em contato com a TI do hospital para recuperar sua senha.")
        
        if submitted:
            if not email or not senha:
                st.error("⚠️ Por favor, preencha todos os campos.")
            elif not validate_email(email):
                st.error("⚠️ Formato de email inválido.")
            elif email == ADMIN_EMAIL and senha == ADMIN_PASSWORD:
                st.success("✅ Login realizado com sucesso!")
                st.session_state["user"] = email
                st.session_state["login_time"] = datetime.now()
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Email ou senha incorretos.")
                if "failed_attempts" not in st.session_state:
                    st.session_state["failed_attempts"] = 0
                st.session_state["failed_attempts"] += 1
                
                if st.session_state["failed_attempts"] >= 3:
                    st.warning("🚨 Muitas tentativas falharam. Aguarde alguns minutos.")

def check_session():
    """Verificar se a sessão ainda é válida"""
    if "user" in st.session_state and "login_time" in st.session_state:
        # Sessão expira em 8 horas
        if datetime.now() - st.session_state["login_time"] > timedelta(hours=8):
            st.session_state.clear()
            st.warning("⏰ Sessão expirada. Faça login novamente.")
            st.rerun()
        return True
    return False

def main_login():
    if not check_session():
        login()
        st.stop()

def logout():
    """Função de logout"""
    st.session_state.clear()
    st.success("✅ Logout realizado com sucesso!")
    st.rerun()

# -------------------
# Inicialização do Supabase (mantido original)
# -------------------
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["SUPABASE_URL"]
        key = st.secrets["supabase"]["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        return None

@st.cache_data(ttl=300)
def load_logo():
    try:
        with open("logo.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

# -------------------
# Funções auxiliares melhoradas
# -------------------
def show_sidebar():
    """Sidebar melhorada com informações do usuário"""
    encoded_logo = load_logo()
    if encoded_logo:
        st.sidebar.markdown(
            f"<div style='text-align:center; margin-bottom:20px;'>"
            f"<img src='data:image/png;base64,{encoded_logo}' width='120'></div>",
            unsafe_allow_html=True
        )
    
    # Informações do usuário
    if "user" in st.session_state:
        st.sidebar.success(f"👋 Bem-vindo!")
        st.sidebar.caption(f"📧 {st.session_state['user']}")
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            logout()
    
    st.sidebar.markdown("---")
    
    # Menu de navegação com ícones
    return st.sidebar.radio(
        "🧭 Navegação",
        ["🏠 Página Inicial", "⚙️ Equipamentos", "🔧 Manutenções", "📊 Dashboard", "📋 Relatórios"],
        index=0
    )

# Funções de banco de dados (mantidas originais)
def fetch_equipamentos(supabase) -> List[Dict]:
    try:
        response = supabase.table("equipamentos").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Erro ao carregar equipamentos: {e}")
        return []

def fetch_manutencoes(supabase) -> List[Dict]:
    try:
        response = supabase.table("manutencoes").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Erro ao carregar manutenções: {e}")
        return []

# Validações melhoradas
def validate_equipment_data(nome: str, setor: str, numero_serie: str) -> Optional[str]:
    """Validação robusta de dados do equipamento"""
    if not nome.strip():
        return "❌ Nome do equipamento é obrigatório"
    if not setor.strip():
        return "❌ Setor é obrigatório"
    if not numero_serie.strip():
        return "❌ Número de série é obrigatório"
    if len(nome.strip()) < 3:
        return "❌ Nome deve ter pelo menos 3 caracteres"
    if len(numero_serie.strip()) < 3:
        return "❌ Número de série deve ter pelo menos 3 caracteres"
    if not re.match(r'^[a-zA-Z0-9\s\-_.]+$', nome.strip()):
        return "❌ Nome contém caracteres inválidos"
    if not re.match(r'^[a-zA-Z0-9\-_.]+$', numero_serie.strip()):
        return "❌ Número de série contém caracteres inválidos"
    return None

def validate_maintenance_data(tipo: str, descricao: str) -> Optional[str]:
    """Validação de dados de manutenção"""
    if not tipo or tipo not in TIPOS_MANUTENCAO:
        return "❌ Tipo de manutenção inválido"
    if not descricao.strip():
        return "❌ Descrição é obrigatória"
    if len(descricao.strip()) < 10:
        return "❌ Descrição deve ter pelo menos 10 caracteres"
    return None

# Funções de inserção (mantidas originais)
def insert_equipment(supabase, nome: str, setor: str, numero_serie: str) -> bool:
    try:
        response = supabase.table("equipamentos").insert({
            "nome": nome.strip(),
            "setor": setor.strip(),
            "numero_serie": numero_serie.strip(),
            "status": "Ativo"
        }).execute()
        return bool(response.data)
    except Exception as e:
        st.error(f"Erro ao cadastrar equipamento: {e}")
        return False

def start_maintenance(supabase, equipamento_id: int, tipo: str, descricao: str) -> bool:
    try:
        manut_response = supabase.table("manutencoes").insert({
            "equipamento_id": equipamento_id,
            "tipo": tipo,
            "descricao": descricao.strip(),
            "data_inicio": datetime.now().isoformat(),
            "status": "Em andamento"
        }).execute()
        if manut_response.data:
            supabase.table("equipamentos").update({"status": "Em manutenção"}).eq("id", equipamento_id).execute()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao abrir manutenção: {e}")
        return False

def finish_maintenance(supabase, manut_id: int, equipamento_id: int) -> bool:
    try:
        manut_response = supabase.table("manutencoes").update({
            "data_fim": datetime.now().isoformat(),
            "status": "Concluída"
        }).eq("id", manut_id).execute()
        if manut_response.data:
            supabase.table("equipamentos").update({"status": "Ativo"}).eq("id", equipamento_id).execute()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao finalizar manutenção: {e}")
        return False

# -------------------
# Sistema de alertas melhorado
# -------------------
def calcular_metricas_avancadas(df_equip: pd.DataFrame, df_manut: pd.DataFrame) -> Dict:
    """Calcula métricas avançadas do sistema"""
    if df_equip.empty or df_manut.empty:
        return {}
    
    # Converter datas
    df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
    df_manut['data_fim'] = pd.to_datetime(df_manut['data_fim'], errors='coerce')
    
    # Métricas básicas
    total_equipamentos = len(df_equip)
    equipamentos_ativos = len(df_equip[df_equip['status'] == 'Ativo'])
    equipamentos_manutencao = len(df_equip[df_equip['status'] == 'Em manutenção'])
    
    # Disponibilidade geral
    disponibilidade_geral = (equipamentos_ativos / total_equipamentos * 100) if total_equipamentos > 0 else 0
    
    # Manutenções no último mês
    ultimo_mes = datetime.now() - timedelta(days=30)
    manut_ultimo_mes = len(df_manut[df_manut['data_inicio'] >= ultimo_mes])
    
    # Tempo médio de manutenção (apenas concluídas)
    manut_concluidas = df_manut[df_manut['status'] == 'Concluída'].copy()
    if not manut_concluidas.empty and not manut_concluidas['data_fim'].isna().all():
        manut_concluidas['duracao'] = (manut_concluidas['data_fim'] - manut_concluidas['data_inicio']).dt.days
        tempo_medio = manut_concluidas['duracao'].mean()
    else:
        tempo_medio = 0
    
    return {
        'total_equipamentos': total_equipamentos,
        'equipamentos_ativos': equipamentos_ativos,
        'equipamentos_manutencao': equipamentos_manutencao,
        'disponibilidade_geral': disponibilidade_geral,
        'manut_ultimo_mes': manut_ultimo_mes,
        'tempo_medio_manutencao': tempo_medio
    }

def gerar_alertas_melhorados(df_equip: pd.DataFrame, df_manut: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    """Gera alertas categorizados por prioridade"""
    if df_equip.empty or df_manut.empty:
        return [], [], []
    
    alertas_criticos = []
    alertas_importantes = []
    alertas_informativos = []
    
    # Converter datas
    df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
    
    # 1. ALERTAS CRÍTICOS
    
    # Equipamentos com muitas falhas (4+ em 3 meses)
    tres_meses = datetime.now() - timedelta(days=90)
    manut_3m = df_manut[df_manut['data_inicio'] >= tres_meses]
    contagem_equip = manut_3m.groupby('equipamento_id').size()
    equipamentos_criticos = contagem_equip[contagem_equip >= 4]
    
    for eq_id, qtd in equipamentos_criticos.items():
        eq_nome = df_equip[df_equip['id'] == eq_id]['nome'].values
        if len(eq_nome) > 0:
            alertas_criticos.append(f"🚨 CRÍTICO: {eq_nome[0]} teve {qtd} manutenções em 3 meses")
    
    # Manutenções urgentes há mais de 48h
    urgentes_abertas = df_manut[
        (df_manut['tipo'] == 'Urgente') & 
        (df_manut['status'] == 'Em andamento')
    ]
    
    for idx, row in urgentes_abertas.iterrows():
        horas = (datetime.now() - row['data_inicio']).total_seconds() / 3600
        if horas > 48:
            eq_nome = df_equip[df_equip['id'] == row['equipamento_id']]['nome'].values
            if len(eq_nome) > 0:
                alertas_criticos.append(f"🚨 URGENTE: {eq_nome[0]} em manutenção há {int(horas)}h")
    
    # 2. ALERTAS IMPORTANTES
    
    # Baixa disponibilidade por setor (<75%)
    dispo_setor = df_equip.groupby('setor')['status'].apply(
        lambda x: (x == 'Ativo').sum() / len(x) * 100
    )
    
    for setor, dispo in dispo_setor.items():
        if dispo < 75:
            alertas_importantes.append(f"⚠️ Baixa disponibilidade: {setor} ({dispo:.1f}% ativos)")
    
    # Equipamentos com padrão de falhas
    for eq_id, df_eq in df_manut.groupby('equipamento_id'):
        df_eq_sorted = df_eq.sort_values('data_inicio')
        tipos = df_eq_sorted['tipo'].tolist()
        
        # Verificar 3 manutenções consecutivas do mesmo tipo
        count = 1
        for i in range(1, len(tipos)):
            if tipos[i] == tipos[i-1]:
                count += 1
                if count >= 3:
                    eq_nome = df_equip[df_equip['id'] == eq_id]['nome'].values
                    if len(eq_nome) > 0:
                        alertas_importantes.append(f"⚠️ Padrão de falha: {eq_nome[0]} - {count} manutenções '{tipos[i]}' seguidas")
                    break
            else:
                count = 1
    
    # 3. ALERTAS INFORMATIVOS
    
    # Equipamentos que não tiveram manutenção preventiva em 6 meses
    seis_meses = datetime.now() - timedelta(days=180)
    preventivas_6m = df_manut[
        (df_manut['tipo'] == 'Preventiva') & 
        (df_manut['data_inicio'] >= seis_meses)
    ]['equipamento_id'].unique()
    
    equipamentos_sem_preventiva = df_equip[
        (~df_equip['id'].isin(preventivas_6m)) & 
        (df_equip['status'] == 'Ativo')
    ]
    
    for idx, row in equipamentos_sem_preventiva.iterrows():
        alertas_informativos.append(f"ℹ️ {row['nome']} sem manutenção preventiva há 6+ meses")
    
    # Setores com alta demanda de manutenção
    manut_por_setor = df_manut.merge(df_equip[['id', 'setor']], left_on='equipamento_id', right_on='id')
    manut_ultimo_mes = manut_por_setor[manut_por_setor['data_inicio'] >= datetime.now() - timedelta(days=30)]
    setores_alta_demanda = manut_ultimo_mes.groupby('setor').size()
    
    for setor, qtd in setores_alta_demanda.items():
        if qtd >= 5:
            alertas_informativos.append(f"ℹ️ Alto volume: {setor} teve {qtd} manutenções no último mês")
    
    return alertas_criticos, alertas_importantes, alertas_informativos

# -------------------
# Páginas melhoradas
# -------------------
def pagina_inicial(supabase):
    """Página inicial com dashboard resumido"""
    st.markdown('<div class="main-header"><h1>🏥 Sistema de Manutenção HSC</h1><p>Gestão inteligente de equipamentos críticos</p></div>', unsafe_allow_html=True)
    
    # Carregar dados
    df_equip = pd.DataFrame(fetch_equipamentos(supabase))
    df_manut = pd.DataFrame(fetch_manutencoes(supabase))
    
    if df_equip.empty:
        st.warning("📋 Nenhum equipamento cadastrado ainda. Comece adicionando equipamentos!")
        return
    
    # Métricas principais
    metricas = calcular_metricas_avancadas(df_equip, df_manut)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>⚙️ Total de Equipamentos</h3>
            <h1 style="color: #1f4e79;">{metricas.get('total_equipamentos', 0)}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        disponibilidade = metricas.get('disponibilidade_geral', 0)
        color = "#28a745" if disponibilidade >= 80 else "#ffc107" if disponibilidade >= 60 else "#dc3545"
        st.markdown(f"""
        <div class="metric-card">
            <h3>📊 Disponibilidade</h3>
            <h1 style="color: {color};">{disponibilidade:.1f}%</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🔧 Em Manutenção</h3>
            <h1 style="color: #1f4e79;">{metricas.get('equipamentos_manutencao', 0)}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        tempo_medio = metricas.get('tempo_medio_manutencao', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h3>⏱️ Tempo Médio</h3>
            <h1 style="color: #1f4e79;">{tempo_medio:.1f} dias</h1>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sistema de alertas
    if not df_manut.empty:
        alertas_criticos, alertas_importantes, alertas_informativos = gerar_alertas_melhorados(df_equip, df_manut)
        
        # Alertas críticos
        if alertas_criticos:
            st.markdown("### 🚨 Alertas Críticos")
            for alerta in alertas_criticos:
                st.markdown(f"""
                <div style="background: #f8d7da; padding: 1rem; border-radius: 8px; border-left: 4px solid #dc3545; margin: 0.5rem 0;">
                    {alerta}
                </div>
                """, unsafe_allow_html=True)
        
        # Alertas importantes
        if alertas_importantes:
            with st.expander("⚠️ Alertas Importantes", expanded=len(alertas_criticos) == 0):
                for alerta in alertas_importantes:
                    st.markdown(f"""
                    <div class="alert-card">
                        {alerta}
                    </div>
                    """, unsafe_allow_html=True)
        
        # Alertas informativos
        if alertas_informativos:
            with st.expander("ℹ️ Informações"):
                for alerta in alertas_informativos:
                    st.write(f"• {alerta}")
        
        # Se não há alertas
        if not any([alertas_criticos, alertas_importantes, alertas_informativos]):
            st.markdown(f"""
            <div class="success-card">
                <h3>✅ Sistema Operacional</h3>
                <p>Todos os equipamentos estão funcionando dentro dos parâmetros normais!</p>
            </div>
            """, unsafe_allow_html=True)

def pagina_adicionar_equipamento(supabase):
    """Página de equipamentos melhorada"""
    st.header("⚙️ Gestão de Equipamentos")
    
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Cadastrar", "📝 Gerenciar", "📊 Analítico", "🔍 Buscar"])
    
    # Aba 1 - Cadastrar (melhorada)
    with tab1:
        st.subheader("Cadastro de Novo Equipamento")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Seleção de setor com opção customizada
            setor_escolhido = st.selectbox(
                "🏢 Setor *", 
                SETORES_PADRAO + ["🔧 Outro"],
                help="Selecione o setor onde o equipamento será utilizado"
            )
            
            setor_final = setor_escolhido
            if setor_escolhido == "🔧 Outro":
                setor_custom = st.text_input(
                    "Nome do setor customizado", 
                    placeholder="Digite o nome do setor"
                )
                if setor_custom.strip():
                    setor_final = setor_custom.strip().title()
                else:
                    setor_final = None
        
        with col2:
            # Preview do setor selecionado
            if setor_final and setor_final != "🔧 Outro":
                st.success(f"✅ Setor selecionado: **{setor_final}**")
        
        # Formulário principal
        with st.form("form_equipamento", clear_on_submit=True):
            col_form1, col_form2 = st.columns(2)
            
            with col_form1:
                nome = st.text_input(
                    "📛 Nome do equipamento *", 
                    placeholder="Ex: Máquina de Hemodiálise A1"
                )
                numero_serie = st.text_input(
                    "🔢 Número de Série *", 
                    placeholder="Ex: HD001-2024"
                )
            
            with col_form2:
                marca = st.text_input(
                    "🏭 Marca", 
                    placeholder="Ex: Fresenius (opcional)"
                )
                modelo = st.text_input(
                    "📋 Modelo", 
                    placeholder="Ex: 4008S (opcional)"
                )
            
            observacoes = st.text_area(
                "📝 Observações",
                placeholder="Informações adicionais sobre o equipamento..."
            )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submitted = st.form_submit_button("✅ Cadastrar Equipamento", use_container_width=True)
            with col_btn2:
                st.form_submit_button("🔄 Limpar Campos", use_container_width=True)
        
        if submitted:
            if not setor_final:
                st.error("❌ Por favor, selecione ou informe um setor.")
            else:
                error = validate_equipment_data(nome, setor_final, numero_serie)
                if error:
                    st.error(error)
                else:
                    if insert_equipment(supabase, nome, setor_final, numero_serie):
                        st.success(f"✅ Equipamento **{nome}** cadastrado com sucesso!")
                        st.balloons()
                        st.cache_data.clear()
                        
                        # Mostrar resumo do cadastro
                        with st.expander("📋 Resumo do Cadastro", expanded=True):
                            st.write(f"**Nome:** {nome}")
                            st.write(f"**Setor:** {setor_final}")
                            st.write(f"**Série:** {numero_serie}")
                            if marca: st.write(f"**Marca:** {marca}")
                            if modelo: st.write(f"**Modelo:** {modelo}")
    
    # Aba 2 - Gerenciar Status (melhorada)
    with tab2:
        st.subheader("Gerenciamento de Status")
        
        equipamentos_data = fetch_equipamentos(supabase)
        if equipamentos_data:
            # Filtros
            col_filtro1, col_filtro2 = st.columns(2)
            with col_filtro1:
                setores_disponiveis = list(set([e['setor'] for e in equipamentos_data]))
                setor_filtro = st.selectbox("Filtrar por setor", ["Todos"] + setores_disponiveis)
            
            with col_filtro2:
                status_filtro = st.selectbox("Filtrar por status", ["Todos"] + STATUS_EQUIPAMENTOS)
            
            # Aplicar filtros
            equipamentos_filtrados = equipamentos_data
            if setor_filtro != "Todos":
                equipamentos_filtrados = [e for e in equipamentos_filtrados if e['setor'] == setor_filtro]
            if status_filtro != "Todos":
                equipamentos_filtrados = [e for e in equipamentos_filtrados if e['status'] == status_filtro]
            
            if equipamentos_filtrados:
                equipamento_dict = {
                    f"{e['nome']} | {e['setor']} | {e['status']}": e['id'] 
                    for e in equipamentos_filtrados
                }
                
                equipamento_selecionado = st.selectbox(
                    "Selecione um equipamento", 
                    [""] + list(equipamento_dict.keys())
                )
                
                if equipamento_selecionado:
                    equip_id = equipamento_dict[equipamento_selecionado]
                    equipamento_info = next(e for e in equipamentos_data if e['id'] == equip_id)
                    status_atual = equipamento_info['status']
                    
                    # Mostrar informações do equipamento
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.info(f"""
                        **📛 Nome:** {equipamento_info['nome']}
                        **🏢 Setor:** {equipamento_info['setor']}
                        **🔢 Série:** {equipamento_info['numero_serie']}
                        """)
                    
                    with col_info2:
                        status_color = {
                            "Ativo": "🟢",
                            "Em manutenção": "🟡",
                            "Inativo": "🔴",
                            "Aguardando peças": "🟠"
                        }
                        st.info(f"**📊 Status Atual:** {status_color.get(status_atual, '⚪')} {status_atual}")
                    
                    # Opções de alteração de status
                    st.markdown("### Alterar Status")
                    novo_status = st.selectbox(
                        "Novo status", 
                        [s for s in STATUS_EQUIPAMENTOS if s != status_atual]
                    )
                    
                    if novo_status:
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button(f"✅ Alterar para {novo_status}", use_container_width=True):
                                try:
                                    supabase.table("equipamentos").update({
                                        "status": novo_status
                                    }).eq("id", equip_id).execute()
                                    st.success(f"✅ Status alterado para **{novo_status}**")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao alterar status: {e}")
                        
                        with col_btn2:
                            if st.button("🔄 Cancelar", use_container_width=True):
                                st.rerun()
            else:
                st.info("🔍 Nenhum equipamento encontrado com os filtros aplicados.")
        else:
            st.warning("📋 Nenhum equipamento cadastrado ainda.")
    
    # Aba 3 - Analítico (melhorada)
    with tab3:
        st.subheader("Análise de Equipamentos")
        
        equipamentos_data = fetch_equipamentos(supabase)
        if equipamentos_data:
            df = pd.DataFrame(equipamentos_data)
            
            # Estatísticas gerais
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            
            with col_stats1:
                total = len(df)
                st.metric("📊 Total de Equipamentos", total)
            
            with col_stats2:
                ativos = len(df[df['status'] == 'Ativo'])
                percentual_ativo = (ativos / total * 100) if total > 0 else 0
                st.metric("✅ Equipamentos Ativos", ativos, f"{percentual_ativo:.1f}%")
            
            with col_stats3:
                manutencao = len(df[df['status'] == 'Em manutenção'])
                percentual_manutencao = (manutencao / total * 100) if total > 0 else 0
                st.metric("🔧 Em Manutenção", manutencao, f"{percentual_manutencao:.1f}%")
            
            # Gráficos
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                # Distribuição por setor
                setor_counts = df['setor'].value_counts()
                fig_setor = px.pie(
                    values=setor_counts.values, 
                    names=setor_counts.index,
                    title="📊 Distribuição por Setor",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_setor.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_setor, use_container_width=True)
            
            with col_graf2:
                # Status dos equipamentos
                status_counts = df['status'].value_counts()
                colors = {'Ativo': '#28a745', 'Em manutenção': '#ffc107', 'Inativo': '#dc3545', 'Aguardando peças': '#fd7e14'}
                fig_status = px.bar(
                    x=status_counts.index, 
                    y=status_counts.values,
                    title="📈 Status dos Equipamentos",
                    color=status_counts.index,
                    color_discrete_map=colors
                )
                fig_status.update_layout(showlegend=False)
                st.plotly_chart(fig_status, use_container_width=True)
            
            # Tabela detalhada
            st.markdown("### 📋 Lista Completa de Equipamentos")
            
            # Configurar colunas da tabela
            df_display = df[['nome', 'setor', 'numero_serie', 'status']].copy()
            df_display.columns = ['Nome', 'Setor', 'Número de Série', 'Status']
            
            # Aplicar cores aos status
            def highlight_status(val):
                colors = {
                    'Ativo': 'background-color: #d4edda',
                    'Em manutenção': 'background-color: #fff3cd',
                    'Inativo': 'background-color: #f8d7da',
                    'Aguardando peças': 'background-color: #ffeaa7'
                }
                return colors.get(val, '')
            
            styled_df = df_display.style.applymap(highlight_status, subset=['Status'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Opção de exportar dados
            csv = df_display.to_csv(index=False)
            st.download_button(
                label="📥 Exportar dados (CSV)",
                data=csv,
                file_name=f"equipamentos_hsc_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.info("📋 Nenhum equipamento cadastrado ainda.")
    
    # Aba 4 - Buscar (nova funcionalidade)
    with tab4:
        st.subheader("🔍 Busca Avançada")
        
        equipamentos_data = fetch_equipamentos(supabase)
        if equipamentos_data:
            # Campo de busca
            termo_busca = st.text_input(
                "🔍 Digite o termo de busca", 
                placeholder="Nome, setor, número de série..."
            )
            
            if termo_busca:
                # Filtrar equipamentos
                equipamentos_encontrados = []
                for equip in equipamentos_data:
                    if (termo_busca.lower() in equip['nome'].lower() or 
                        termo_busca.lower() in equip['setor'].lower() or
                        termo_busca.lower() in equip['numero_serie'].lower()):
                        equipamentos_encontrados.append(equip)
                
                if equipamentos_encontrados:
                    st.success(f"✅ {len(equipamentos_encontrados)} equipamento(s) encontrado(s)")
                    
                    for equip in equipamentos_encontrados:
                        with st.expander(f"📱 {equip['nome']}", expanded=False):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**🏢 Setor:** {equip['setor']}")
                                st.write(f"**🔢 Série:** {equip['numero_serie']}")
                            with col2:
                                status_icon = {"Ativo": "🟢", "Em manutenção": "🟡", "Inativo": "🔴"}.get(equip['status'], "⚪")
                                st.write(f"**📊 Status:** {status_icon} {equip['status']}")
                else:
                    st.warning("❌ Nenhum equipamento encontrado com esse termo.")
        else:
            st.info("📋 Nenhum equipamento cadastrado ainda.")

def pagina_registrar_manutencao(supabase):
    """Página de manutenções melhorada"""
    st.header("🔧 Gestão de Manutenções")
    
    tab1, tab2, tab3, tab4 = st.tabs(["🆕 Abrir", "✅ Finalizar", "📊 Analítico", "📋 Histórico"])
    
    # Aba 1 - Abrir manutenção (melhorada)
    with tab1:
        st.subheader("Abertura de Nova Manutenção")
        
        equipamentos_ativos = [e for e in fetch_equipamentos(supabase) if e['status'] == "Ativo"]
        
        if equipamentos_ativos:
            # Organizar equipamentos por setor
            equipamentos_por_setor = {}
            for equip in equipamentos_ativos:
                setor = equip['setor']
                if setor not in equipamentos_por_setor:
                    equipamentos_por_setor[setor] = []
                equipamentos_por_setor[setor].append(equip)
            
            with st.form("abrir_manut", clear_on_submit=True):
                col_form1, col_form2 = st.columns(2)
                
                with col_form1:
                    # Seleção por setor primeiro
                    setor_selecionado = st.selectbox(
                        "🏢 Selecione o setor", 
                        [""] + list(equipamentos_por_setor.keys())
                    )
                    
                    equipamento_selecionado = ""
                    if setor_selecionado:
                        equipamentos_setor = equipamentos_por_setor[setor_selecionado]
                        equipamento_dict = {f"{e['nome']}": e['id'] for e in equipamentos_setor}
                        equipamento_selecionado = st.selectbox(
                            "⚙️ Selecione o equipamento", 
                            [""] + list(equipamento_dict.keys())
                        )
                
                with col_form2:
                    tipo = st.selectbox(
                        "🔧 Tipo de manutenção *", 
                        [""] + TIPOS_MANUTENCAO,
                        help="Tipo de manutenção a ser realizada"
                    )
                    
                    prioridade = st.selectbox(
                        "⚡ Prioridade",
                        ["Normal", "Alta", "Crítica"],
                        help="Nível de prioridade da manutenção"
                    )
                
                # Descrição detalhada
                descricao = st.text_area(
                    "📝 Descrição detalhada *",
                    placeholder="Descreva o problema ou serviço a ser realizado...",
                    height=100
                )
                
                # Campos adicionais
                col_extra1, col_extra2 = st.columns(2)
                with col_extra1:
                    tecnico_responsavel = st.text_input(
                        "👨‍🔧 Técnico responsável",
                        placeholder="Nome do técnico (opcional)"
                    )
                
                with col_extra2:
                    data_prevista = st.date_input(
                        "📅 Conclusão prevista",
                        min_value=datetime.now().date(),
                        help="Data prevista para conclusão (opcional)"
                    )
                
                # Botões
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    submitted = st.form_submit_button("🔧 Abrir Manutenção", use_container_width=True)
                with col_btn2:
                    st.form_submit_button("🔄 Limpar", use_container_width=True)
                
                if submitted:
                    if not equipamento_selecionado or not tipo or not descricao.strip():
                        st.error("❌ Por favor, preencha todos os campos obrigatórios!")
                    else:
                        # Validação adicional
                        error = validate_maintenance_data(tipo, descricao)
                        if error:
                            st.error(error)
                        else:
                            equipamento_id = equipamento_dict[equipamento_selecionado]
                            if start_maintenance(supabase, equipamento_id, tipo, descricao):
                                st.success(f"✅ Manutenção aberta para **{equipamento_selecionado}**!")
                                st.balloons()
                                st.cache_data.clear()
                                
                                # Mostrar resumo
                                with st.expander("📋 Resumo da Manutenção", expanded=True):
                                    st.write(f"**⚙️ Equipamento:** {equipamento_selecionado}")
                                    st.write(f"**🏢 Setor:** {setor_selecionado}")
                                    st.write(f"**🔧 Tipo:** {tipo}")
                                    st.write(f"**⚡ Prioridade:** {prioridade}")
                                    st.write(f"**📝 Descrição:** {descricao}")
                                    if tecnico_responsavel:
                                        st.write(f"**👨‍🔧 Técnico:** {tecnico_responsavel}")
                            else:
                                st.error("❌ Erro ao abrir manutenção.")
        else:
            st.warning("⚠️ Nenhum equipamento ativo disponível para manutenção.")
            if st.button("🔄 Atualizar lista"):
                st.cache_data.clear()
                st.rerun()
    
    # Aba 2 - Finalizar (melhorada)
    with tab2:
        st.subheader("Finalização de Manutenções")
        
        manutencoes_abertas = [m for m in fetch_manutencoes(supabase) if m['status'] == "Em andamento"]
        
        if manutencoes_abertas:
            equipamentos_data = fetch_equipamentos(supabase)
            
            # Organizar manutenções com informações completas
            manutencoes_info = []
            for m in manutencoes_abertas:
                eq_info = next((e for e in equipamentos_data if e['id'] == m['equipamento_id']), None)
                if eq_info:
                    data_inicio = pd.to_datetime(m['data_inicio'])
                    duracao = (datetime.now() - data_inicio).days
                    
                    manutencoes_info.append({
                        'id': m['id'],
                        'equipamento_id': m['equipamento_id'],
                        'nome_equip': eq_info['nome'],
                        'setor': eq_info['setor'],
                        'tipo': m['tipo'],
                        'descricao': m['descricao'],
                        'data_inicio': data_inicio,
                        'duracao': duracao,
                        'display': f"{eq_info['nome']} | {eq_info['setor']} | {m['tipo']} | {duracao} dia(s)"
                    })
            
            # Ordenar por duração (mais antigas primeiro)
            manutencoes_info.sort(key=lambda x: x['duracao'], reverse=True)
            
            with st.form("finalizar_manut", clear_on_submit=True):
                # Seleção da manutenção
                manut_dict = {m['display']: m for m in manutencoes_info}
                manut_selecionada = st.selectbox(
                    "🔧 Selecione a manutenção para finalizar",
                    [""] + list(manut_dict.keys())
                )
                
                if manut_selecionada:
                    info_manut = manut_dict[manut_selecionada]
                    
                    # Mostrar detalhes da manutenção
                    col_det1, col_det2 = st.columns(2)
                    with col_det1:
                        st.info(f"""
                        **⚙️ Equipamento:** {info_manut['nome_equip']}
                        **🏢 Setor:** {info_manut['setor']}
                        **🔧 Tipo:** {info_manut['tipo']}
                        """)
                    
                    with col_det2:
                        st.info(f"""
                        **📅 Iniciado:** {info_manut['data_inicio'].strftime('%d/%m/%Y %H:%M')}
                        **⏱️ Duração:** {info_manut['duracao']} dia(s)
                        **📝 Descrição:** {info_manut['descricao'][:50]}...
                        """)
                
                # Campos para finalização
                col_final1, col_final2 = st.columns(2)
                with col_final1:
                    solucao = st.text_area(
                        "✅ Solução aplicada",
                        placeholder="Descreva a solução aplicada e serviços realizados...",
                        height=100
                    )
                
                with col_final2:
                    pecas_utilizadas = st.text_area(
                        "🔧 Peças utilizadas",
                        placeholder="Liste as peças/materiais utilizados (opcional)",
                        height=100
                    )
                
                observacoes_finais = st.text_area(
                    "📋 Observações finais",
                    placeholder="Observações adicionais, recomendações, etc."
                )
                
                # Botões
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    submitted = st.form_submit_button("✅ Finalizar Manutenção", use_container_width=True)
                with col_btn2:
                    st.form_submit_button("🔄 Cancelar", use_container_width=True)
                
                if submitted:
                    if not manut_selecionada:
                        st.error("❌ Selecione uma manutenção para finalizar")
                    else:
                        info = manut_dict[manut_selecionada]
                        if finish_maintenance(supabase, info['id'], info['equipamento_id']):
                            st.success(f"✅ Manutenção finalizada para **{info['nome_equip']}**!")
                            st.balloons()
                            st.cache_data.clear()
                            
                            # Mostrar resumo da finalização
                            with st.expander("📋 Resumo da Finalização", expanded=True):
                                st.write(f"**⚙️ Equipamento:** {info['nome_equip']}")
                                st.write(f"**⏱️ Duração total:** {info['duracao']} dia(s)")
                                if solucao:
                                    st.write(f"**✅ Solução:** {solucao}")
                        else:
                            st.error("❌ Erro ao finalizar manutenção.")
        else:
            st.info("ℹ️ Nenhuma manutenção em andamento no momento.")
    
    # Aba 3 - Analítico (nova)
    with tab3:
        st.subheader("📊 Análise de Manutenções")
        
        manutencoes_data = fetch_manutencoes(supabase)
        equipamentos_data = fetch_equipamentos(supabase)
        
        if manutencoes_data and equipamentos_data:
            df_manut = pd.DataFrame(manutencoes_data)
            df_equip = pd.DataFrame(equipamentos_data)
            
            # Converter datas
            df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
            df_manut['data_fim'] = pd.to_datetime(df_manut['data_fim'], errors='coerce')
            
            # Adicionar informações dos equipamentos
            df_manut = df_manut.merge(
                df_equip[['id', 'nome', 'setor']], 
                left_on='equipamento_id', 
                right_on='id', 
                suffixes=('', '_equip')
            )
            
            # Métricas principais
            col_metrics1, col_metrics2, col_metrics3, col_metrics4 = st.columns(4)
            
            with col_metrics1:
                total_manut = len(df_manut)
                st.metric("🔧 Total de Manutenções", total_manut)
            
            with col_metrics2:
                em_andamento = len(df_manut[df_manut['status'] == 'Em andamento'])
                st.metric("⏳ Em Andamento", em_andamento)
            
            with col_metrics3:
                concluidas = len(df_manut[df_manut['status'] == 'Concluída'])
                st.metric("✅ Concluídas", concluidas)
            
            with col_metrics4:
                # Taxa de conclusão
                taxa_conclusao = (concluidas / total_manut * 100) if total_manut > 0 else 0
                st.metric("📊 Taxa de Conclusão", f"{taxa_conclusao:.1f}%")
            
            # Gráficos
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                # Manutenções por tipo
                tipo_counts = df_manut['tipo'].value_counts()
                fig_tipo = px.pie(
                    values=tipo_counts.values,
                    names=tipo_counts.index,
                    title="📊 Manutenções por Tipo",
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig_tipo, use_container_width=True)
            
            with col_graf2:
                # Manutenções por setor
                setor_counts = df_manut['setor'].value_counts()
                fig_setor = px.bar(
                    x=setor_counts.index,
                    y=setor_counts.values,
                    title="📈 Manutenções por Setor",
                    color=setor_counts.values,
                    color_continuous_scale="Blues"
                )
                fig_setor.update_layout(showlegend=False)
                st.plotly_chart(fig_setor, use_container_width=True)
            
            # Timeline de manutenções (últimos 30 dias)
            st.markdown("### 📅 Timeline - Últimos 30 dias")
            ultimo_mes = datetime.now() - timedelta(days=30)
            df_ultimo_mes = df_manut[df_manut['data_inicio'] >= ultimo_mes].copy()
            
            if not df_ultimo_mes.empty:
                df_ultimo_mes['data'] = df_ultimo_mes['data_inicio'].dt.date
                timeline_counts = df_ultimo_mes.groupby(['data', 'tipo']).size().reset_index(name='count')
                
                fig_timeline = px.line(
                    timeline_counts,
                    x='data',
                    y='count',
                    color='tipo',
                    title="Manutenções por Dia",
                    markers=True
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
            else:
                st.info("📅 Nenhuma manutenção nos últimos 30 dias.")
        
        else:
            st.info("📋 Nenhuma manutenção registrada ainda.")
    
    # Aba 4 - Histórico (nova)
    with tab4:
        st.subheader("📋 Histórico Completo")
        
        manutencoes_data = fetch_manutencoes(supabase)
        equipamentos_data = fetch_equipamentos(supabase)
        
        if manutencoes_data:
            df_manut = pd.DataFrame(manutencoes_data)
            df_equip = pd.DataFrame(equipamentos_data)
            
            # Adicionar informações dos equipamentos
            for idx, row in df_manut.iterrows():
                eq = next((e for e in equipamentos_data if e['id'] == row['equipamento_id']), None)
                if eq:
                    df_manut.at[idx, 'nome_equip'] = eq['nome']
                    df_manut.at[idx, 'setor_equip'] = eq['setor']
            
            # Filtros
            col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
            
            with col_filtro1:
                setores_disponiveis = df_manut['setor_equip'].dropna().unique()
                setor_filtro = st.selectbox("Filtrar por setor", ["Todos"] + list(setores_disponiveis))
            
            with col_filtro2:
                tipos_disponiveis = df_manut['tipo'].unique()
                tipo_filtro = st.selectbox("Filtrar por tipo", ["Todos"] + list(tipos_disponiveis))
            
            with col_filtro3:
                status_disponiveis = df_manut['status'].unique()
                status_filtro = st.selectbox("Filtrar por status", ["Todos"] + list(status_disponiveis))
            
            # Aplicar filtros
            df_filtrado = df_manut.copy()
            if setor_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['setor_equip'] == setor_filtro]
            if tipo_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['tipo'] == tipo_filtro]
            if status_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['status'] == status_filtro]
            
            if not df_filtrado.empty:
                # Preparar dados para exibição
                df_display = df_filtrado[['nome_equip', 'setor_equip', 'tipo', 'descricao', 'data_inicio', 'status']].copy()
                df_display.columns = ['Equipamento', 'Setor', 'Tipo', 'Descrição', 'Data Início', 'Status']
                
                # Converter data para formato brasileiro
                df_display['Data Início'] = pd.to_datetime(df_display['Data Início']).dt.strftime('%d/%m/%Y %H:%M')
                
                # Limitar descrição
                df_display['Descrição'] = df_display['Descrição'].apply(
                    lambda x: x[:50] + "..." if len(str(x)) > 50 else x
                )
                
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                
                # Exportar dados
                csv = df_display.to_csv(index=False)
                st.download_button(
                    label="📥 Exportar histórico (CSV)",
                    data=csv,
                    file_name=f"historico_manutencoes_hsc_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                
                st.success(f"✅ Exibindo {len(df_filtrado)} registro(s)")
            else:
                st.info("🔍 Nenhum registro encontrado com os filtros aplicados.")
        else:
            st.info("📋 Nenhuma manutenção registrada ainda.")

def pagina_dashboard(supabase):
    """Dashboard melhorado com gráficos avançados"""
    st.header("📊 Dashboard Executivo")
    
    df_equip = pd.DataFrame(fetch_equipamentos(supabase))
    df_manut = pd.DataFrame(fetch_manutencoes(supabase))
    
    if df_equip.empty:
        st.warning("📋 Cadastre equipamentos primeiro para visualizar o dashboard.")
        return
    
    # Métricas principais no topo
    metricas = calcular_metricas_avancadas(df_equip, df_manut)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "⚙️ Total Equipamentos", 
            metricas.get('total_equipamentos', 0)
        )
    
    with col2:
        disponibilidade = metricas.get('disponibilidade_geral', 0)
        delta_color = "normal" if disponibilidade >= 80 else "inverse"
        st.metric(
            "📊 Disponibilidade", 
            f"{disponibilidade:.1f}%",
            delta_color=delta_color
        )
    
    with col3:
        st.metric(
            "✅ Ativos", 
            metricas.get('equipamentos_ativos', 0)
        )
    
    with col4:
        st.metric(
            "🔧 Em Manutenção", 
            metricas.get('equipamentos_manutencao', 0)
        )
    
    with col5:
        st.metric(
            "⏱️ Tempo Médio", 
            f"{metricas.get('tempo_medio_manutencao', 0):.1f} dias"
        )
    
    st.markdown("---")
    
    # Gráficos principais
    if not df_manut.empty:
        df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
        df_manut['data_fim'] = pd.to_datetime(df_manut['data_fim'], errors='coerce')
        
        # Adicionar informações dos equipamentos
        df_manut = df_manut.merge(
            df_equip[['id', 'nome', 'setor']], 
            left_on='equipamento_id', 
            right_on='id', 
            suffixes=('', '_equip')
        )
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            # Disponibilidade por setor com mais detalhes
            dispo_setor = df_equip.groupby('setor')['status'].apply(
                lambda x: (x == 'Ativo').sum() / len(x) * 100
            ).reset_index()
            dispo_setor.columns = ['Setor', 'Disponibilidade (%)']
            
            fig_dispo = px.bar(
                dispo_setor, 
                x='Setor', 
                y='Disponibilidade (%)',
                title="📊 Disponibilidade por Setor",
                color='Disponibilidade (%)',
                color_continuous_scale=[[0, '#dc3545'], [0.6, '#ffc107'], [0.8, '#28a745'], [1, '#20c997']],
                text='Disponibilidade (%)'
            )
            fig_dispo.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig_dispo.update_layout(
                xaxis_tickangle=-45,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_dispo, use_container_width=True)
        
        with col_graf2:
            # Evolução de manutenções nos últimos 6 meses
            seis_meses = datetime.now() - timedelta(days=180)
            df_ultimos_6m = df_manut[df_manut['data_inicio'] >= seis_meses].copy()
            
            if not df_ultimos_6m.empty:
                df_ultimos_6m['mes_ano'] = df_ultimos_6m['data_inicio'].dt.to_period('M')
                evolucao = df_ultimos_6m.groupby(['mes_ano', 'tipo']).size().reset_index(name='count')
                evolucao['mes_ano_str'] = evolucao['mes_ano'].astype(str)
                
                fig_evolucao = px.line(
                    evolucao,
                    x='mes_ano_str',
                    y='count',
                    color='tipo',
                    title="📈 Evolução de Manutenções (6 meses)",
                    markers=True
                )
                fig_evolucao.update_layout(xaxis_title="Mês/Ano", yaxis_title="Quantidade")
                st.plotly_chart(fig_evolucao, use_container_width=True)
            else:
                st.info("📅 Dados insuficientes para gráfico de evolução.")
        
        # Segunda linha de gráficos
        col_graf3, col_graf4 = st.columns(2)
        
        with col_graf3:
            # Top 10 equipamentos com mais manutenções
            top_equipamentos = df_manut.groupby('nome').size().sort_values(ascending=False).head(10)
            
            if not top_equipamentos.empty:
                fig_top = px.bar(
                    x=top_equipamentos.values,
                    y=top_equipamentos.index,
                    orientation='h',
                    title="🔧 Top 10 - Equipamentos com Mais Manutenções",
                    color=top_equipamentos.values,
                    color_continuous_scale="Reds"
                )
                fig_top.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    coloraxis_showscale=False,
                    xaxis_title="Quantidade de Manutenções"
                )
                st.plotly_chart(fig_top, use_container_width=True)
        
        with col_graf4:
            # Distribuição de tempo de manutenção
            manut_concluidas = df_manut[df_manut['status'] == 'Concluída'].copy()
            
            if not manut_concluidas.empty and not manut_concluidas['data_fim'].isna().all():
                manut_concluidas['duracao'] = (
                    manut_concluidas['data_fim'] - manut_concluidas['data_inicio']
                ).dt.days
                
                # Categorizar durações
                def categorizar_duracao(dias):
                    if dias <= 1:
                        return "≤ 1 dia"
                    elif dias <= 3:
                        return "2-3 dias"
                    elif dias <= 7:
                        return "4-7 dias"
                    elif dias <= 15:
                        return "8-15 dias"
                    else:
                        return "> 15 dias"
                
                manut_concluidas['categoria_duracao'] = manut_concluidas['duracao'].apply(categorizar_duracao)
                duracao_counts = manut_concluidas['categoria_duracao'].value_counts()
                
                fig_duracao = px.pie(
                    values=duracao_counts.values,
                    names=duracao_counts.index,
                    title="⏱️ Distribuição de Tempo de Manutenção",
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                st.plotly_chart(fig_duracao, use_container_width=True)
            else:
                st.info("📊 Dados insuficientes para análise de duração.")
    
    else:
        st.info("📋 Registre algumas manutenções para visualizar análises avançadas.")
        
        # Mostrar apenas disponibilidade por setor
        st.subheader("📊 Disponibilidade por Setor")
        dispo_setor = df_equip.groupby('setor')['status'].apply(
            lambda x: (x == 'Ativo').sum() / len(x) * 100
        ).reset_index()
        dispo_setor.columns = ['Setor', 'Disponibilidade (%)']
        
        fig_simples = px.bar(
            dispo_setor, 
            x='Setor', 
            y='Disponibilidade (%)',
            title="Disponibilidade de Equipamentos por Setor",
            color='Disponibilidade (%)',
            color_continuous_scale="RdYlGn",
            text='Disponibilidade (%)'
        )
        fig_simples.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig_simples, use_container_width=True)

def pagina_relatorios(supabase):
    """Nova página de relatórios"""
    st.header("📋 Relatórios e Análises")
    
    df_equip = pd.DataFrame(fetch_equipamentos(supabase))
    df_manut = pd.DataFrame(fetch_manutencoes(supabase))
    
    if df_equip.empty:
        st.warning("📋 Cadastre equipamentos primeiro para gerar relatórios.")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumo Executivo", "🔧 Relatório de Manutenções", "⚙️ Relatório de Equipamentos", "📈 Análise Preditiva"])
    
    # Tab 1 - Resumo Executivo
    with tab1:
        st.subheader("📊 Resumo Executivo")
        
        # Período de análise
        col_periodo1, col_periodo2 = st.columns(2)
        with col_periodo1:
            data_inicio = st.date_input(
                "📅 Data de início",
                value=datetime.now() - timedelta(days=30),
                max_value=datetime.now()
            )
        with col_periodo2:
            data_fim = st.date_input(
                "📅 Data de fim",
                value=datetime.now(),
                max_value=datetime.now()
            )
        
        if not df_manut.empty:
            df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
            df_periodo = df_manut[
                (df_manut['data_inicio'].dt.date >= data_inicio) & 
                (df_manut['data_inicio'].dt.date <= data_fim)
            ]
            
            # Métricas do período
            col_met1, col_met2, col_met3, col_met4 = st.columns(4)
            
            with col_met1:
                total_manut_periodo = len(df_periodo)
                st.metric("🔧 Manutenções", total_manut_periodo)
            
            with col_met2:
                urgentes_periodo = len(df_periodo[df_periodo['tipo'] == 'Urgente'])
                st.metric("🚨 Urgentes", urgentes_periodo)
            
            with col_met3:
                preventivas_periodo = len(df_periodo[df_periodo['tipo'] == 'Preventiva'])
                st.metric("🛡️ Preventivas", preventivas_periodo)
            
            with col_met4:
                if total_manut_periodo > 0:
                    preventivas_pct = (preventivas_periodo / total_manut_periodo) * 100
                    st.metric("📊 % Preventivas", f"{preventivas_pct:.1f}%")
                else:
                    st.metric("📊 % Preventivas", "0%")
            
            # Insights automáticos
            st.markdown("### 🧠 Insights Automáticos")
            
            insights = []
            
            # Insight 1: Taxa de manutenção preventiva
            if preventivas_pct < 30:
                insights.append("⚠️ Taxa de manutenção preventiva baixa. Recomenda-se aumentar para pelo menos 30%.")
            elif preventivas_pct >= 50:
                insights.append("✅ Excelente foco em manutenção preventiva!")
            
            # Insight 2: Manutenções urgentes
            if urgentes_periodo > 0:
                urgentes_pct = (urgentes_periodo / total_manut_periodo) * 100
                if urgentes_pct > 20:
                    insights.append(f"🚨 Alto índice de manutenções urgentes ({urgentes_pct:.1f}%). Investigar causas.")
            
            # Insight 3: Setores mais críticos
            if not df_periodo.empty:
                df_periodo = df_periodo.merge(df_equip[['id', 'setor']], left_on='equipamento_id', right_on='id')
                setor_counts = df_periodo['setor'].value_counts()
                setor_critico = setor_counts.index[0] if len(setor_counts) > 0 else None
                if setor_critico:
                    insights.append(f"🏢 Setor com mais demanda: {setor_critico} ({setor_counts.iloc[0]} manutenções)")
            
            for insight in insights:
                st.info(insight)
            
            if not insights:
                st.success("✅ Nenhum ponto de atenção identificado no período analisado.")
        else:
            st.info("📋 Nenhuma manutenção registrada no período selecionado.")
    
    # Tab 2 - Relatório de Manutenções
    with tab2:
        st.subheader("🔧 Relatório Detalhado de Manutenções")
        
        if not df_manut.empty:
            # Filtros avançados
            col_filt1, col_filt2, col_filt3 = st.columns(3)
            
            with col_filt1:
                tipos_selecionados = st.multiselect(
                    "🔧 Tipos de manutenção",
                    df_manut['tipo'].unique(),
                    default=df_manut['tipo'].unique()
                )
            
            with col_filt2:
                status_selecionados = st.multiselect(
                    "📊 Status",
                    df_manut['status'].unique(),
                    default=df_manut['status'].unique()
                )
            
            with col_filt3:
                # Adicionar informações de setor
                df_manut_setor = df_manut.merge(df_equip[['id', 'setor']], left_on='equipamento_id', right_on='id')
                setores_selecionados = st.multiselect(
                    "🏢 Setores",
                    df_manut_setor['setor'].unique(),
                    default=df_manut_setor['setor'].unique()
                )
            
            # Aplicar filtros
            df_filtrado = df_manut_setor[
                (df_manut_setor['tipo'].isin(tipos_selecionados)) &
                (df_manut_setor['status'].isin(status_selecionados)) &
                (df_manut_setor['setor'].isin(setores_selecionados))
            ]
            
            if not df_filtrado.empty:
                # Estatísticas do filtro
                st.markdown(f"**📊 Registros encontrados:** {len(df_filtrado)}")
                
                # Análises
                col_analise1, col_analise2 = st.columns(2)
                
                with col_analise1:
                    # Distribuição por mês
                    df_filtrado['mes'] = pd.to_datetime(df_filtrado['data_inicio']).dt.to_period('M')
                    mensal = df_filtrado.groupby('mes').size()
                    
                    fig_mensal = px.line(
                        x=mensal.index.astype(str),
                        y=mensal.values,
                        title="📅 Manutenções por Mês",
                        markers=True
                    )
                    st.plotly_chart(fig_mensal, use_container_width=True)
                
                with col_analise2:
                    # Top equipamentos
                    df_filtrado = df_filtrado.merge(df_equip[['id', 'nome']], left_on='equipamento_id', right_on='id', suffixes=('', '_eq'))
                    top_equip = df_filtrado['nome_eq'].value_counts().head(5)
                    
                    fig_top_eq = px.bar(
                        x=top_equip.values,
                        y=top_equip.index,
                        orientation='h',
                        title="🔧 Top 5 Equipamentos"
                    )
                    st.plotly_chart(fig_top_eq, use_container_width=True)
                
                # Tabela detalhada
                st.markdown("### 📋 Detalhamento")
                colunas_exibir = ['nome_eq', 'setor', 'tipo', 'status', 'data_inicio', 'descricao']
                df_display = df_filtrado[colunas_exibir].copy()
                df_display.columns = ['Equipamento', 'Setor', 'Tipo', 'Status', 'Data', 'Descrição']
                df_display['Data'] = pd.to_datetime(df_display['Data']).dt.strftime('%d/%m/%Y')
                df_display['Descrição'] = df_display['Descrição'].apply(lambda x: str(x)[:50] + "..." if len(str(x)) > 50 else x)
                
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                
                # Download
                csv = df_display.to_csv(index=False)
                st.download_button(
                    "📥 Baixar relatório (CSV)",
                    data=csv,
                    file_name=f"relatorio_manutencoes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("🔍 Nenhum registro encontrado com os filtros aplicados.")
        else:
            st.info("📋 Nenhuma manutenção registrada ainda.")
    
    # Tab 3 - Relatório de Equipamentos
    with tab3:
        st.subheader("⚙️ Relatório de Equipamentos")
        
        # Análise por setor
        st.markdown("### 🏢 Análise por Setor")
        analise_setor = df_equip.groupby('setor').agg({
            'status': ['count', lambda x: (x == 'Ativo').sum(), lambda x: (x == 'Em manutenção').sum()]
        }).round(2)
        
        analise_setor.columns = ['Total', 'Ativos', 'Em Manutenção']
        analise_setor['Disponibilidade %'] = (analise_setor['Ativos'] / analise_setor['Total'] * 100).round(1)
        
        st.dataframe(analise_setor, use_container_width=True)
        
        # Gráfico de disponibilidade
        fig_dispo_setor = px.bar(
            x=analise_setor.index,
            y=analise_setor['Disponibilidade %'],
            title="📊 Disponibilidade por Setor",
            color=analise_setor['Disponibilidade %'],
            color_continuous_scale="RdYlGn"
        )
        st.plotly_chart(fig_dispo_setor, use_container_width=True)
        
        # Lista completa
        st.markdown("### 📋 Lista Completa de Equipamentos")
        df_equip_display = df_equip[['nome', 'setor', 'numero_serie', 'status']].copy()
        df_equip_display.columns = ['Nome', 'Setor', 'Número de Série', 'Status']
        
        st.dataframe(df_equip_display, use_container_width=True, hide_index=True)
        
        # Download
        csv_equip = df_equip_display.to_csv(index=False)
        st.download_button(
            "📥 Baixar lista de equipamentos (CSV)",
            data=csv_equip,
            file_name=f"relatorio_equipamentos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    # Tab 4 - Análise Preditiva
    with tab4:
        st.subheader("📈 Análise Preditiva")
        
        if not df_manut.empty:
            df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
            
            # Previsão de manutenções baseada em histórico
            st.markdown("### 🔮 Previsões Baseadas em Histórico")
            
            # Equipamentos que podem precisar de manutenção em breve
            ultimo_mes = datetime.now() - timedelta(days=30)
            tres_meses = datetime.now() - timedelta(days=90)
            
            # Equipamentos ativos sem manutenção recente
            manut_recente = df_manut[df_manut['data_inicio'] >= ultimo_mes]['equipamento_id'].unique()
            equip_sem_manut_recente = df_equip[
                (~df_equip['id'].isin(manut_recente)) & 
                (df_equip['status'] == 'Ativo')
            ]
            
            if not equip_sem_manut_recente.empty:
                st.warning(f"⚠️ **{len(equip_sem_manut_recente)} equipamentos** podem precisar de atenção em breve:")
                for idx, row in equip_sem_manut_recente.head(10).iterrows():
                    # Verificar última manutenção
                    ultima_manut = df_manut[df_manut['equipamento_id'] == row['id']].sort_values('data_inicio').tail(1)
                    if not ultima_manut.empty:
                        dias_ultima = (datetime.now() - ultima_manut.iloc[0]['data_inicio']).days
                        st.write(f"• **{row['nome']}** ({row['setor']}) - Última manutenção há {dias_ultima} dias")
                    else:
                        st.write(f"• **{row['nome']}** ({row['setor']}) - Sem histórico de manutenção")
            
            # Tendência de manutenções por setor
            st.markdown("### 📊 Tendências por Setor")
            
            df_manut_completo = df_manut.merge(df_equip[['id', 'setor']], left_on='equipamento_id', right_on='id')
            df_manut_completo['mes'] = df_manut_completo['data_inicio'].dt.to_period('M')
            
            tendencia_setor = df_manut_completo.groupby(['setor', 'mes']).size().reset_index(name='count')
            tendencia_setor['mes_str'] = tendencia_setor['mes'].astype(str)
            
            if len(tendencia_setor) > 0:
                fig_tendencia = px.line(
                    tendencia_setor,
                    x='mes_str',
                    y='count',
                    color='setor',
                    title="Tendência de Manutenções por Setor",
                    markers=True
                )
                st.plotly_chart(fig_tendencia, use_container_width=True)
            
            # Recomendações automáticas
            st.markdown("### 💡 Recomendações")
            
            recomendacoes = []
            
            # Baseado na análise de alertas
            alertas_criticos, alertas_importantes, alertas_informativos = gerar_alertas_melhorados(df_equip, df_manut)
            
            if alertas_criticos:
                recomendacoes.append("🚨 **Ação Imediata:** Focar nos equipamentos com alertas críticos.")
            
            if len(equip_sem_manut_recente) > 5:
                recomendacoes.append("🔧 **Manutenção Preventiva:** Agendar manutenções preventivas para equipamentos sem atenção recente.")
            
            # Análise de eficiência
            preventivas = len(df_manut[df_manut['tipo'] == 'Preventiva'])
            urgentes = len(df_manut[df_manut['tipo'] == 'Urgente'])
            
            if urgentes > preventivas:
                recomendacoes.append("📊 **Estratégia:** Aumentar manutenções preventivas para reduzir urgências.")
            
            for rec in recomendacoes:
                st.info(rec)
            
            if not recomendacoes:
                st.success("✅ Sistema operando de forma eficiente!")
        
        else:
            st.info("📋 Registre manutenções para análises preditivas.")

# -------------------
# Main melhorado
# -------------------
def main():
    """Função principal melhorada"""
    main_login()
    
    supabase = init_supabase()
    if not supabase:
        st.error("❌ Erro de conexão com banco de dados. Contate o suporte técnico.")
        return
    
    # Sidebar com navegação
    pagina = show_sidebar()
    
    # Roteamento de páginas
    if pagina == "🏠 Página Inicial":
        pagina_inicial(supabase)
    elif pagina == "⚙️ Equipamentos":
        pagina_adicionar_equipamento(supabase)
    elif pagina == "🔧 Manutenções":
        pagina_registrar_manutencao(supabase)
    elif pagina == "📊 Dashboard":
        pagina_dashboard(supabase)
    elif pagina == "📋 Relatórios":
        pagina_relatorios(supabase)

if __name__ == "__main__":
    main()
