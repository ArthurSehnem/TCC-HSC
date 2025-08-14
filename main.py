import streamlit as st
import base64
from supabase import create_client
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List, Any

# -------------------
# Configuração inicial
# -------------------
st.set_page_config(
    page_title="Sistema de Manutenção | HSC",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_supabase():
    """Inicializa conexão com Supabase com cache para melhor performance."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        return None

@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_logo():
    """Carrega logo com cache e tratamento de erro."""
    try:
        with open("logo.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

# -------------------
# Funções auxiliares
# -------------------
def show_sidebar():
    """Configura sidebar com logo e navegação."""
    encoded_logo = load_logo()
    if encoded_logo:
        st.sidebar.markdown(
            f"""
            <div style='text-align: center; margin-bottom: 20px;'>
                <img src='data:image/png;base64,{encoded_logo}' width='120'>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.sidebar.markdown("---")
    return st.sidebar.radio(
        "🧭 Navegação",
        ["🏠 Página Inicial", "➕ Adicionar Equipamento", "🔧 Registrar Manutenção", "📊 Dashboard"],
        index=0
    )

def fetch_equipamentos(supabase) -> List[Dict]:
    """Busca equipamentos."""
    try:
        response = supabase.table("equipamentos").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Erro ao carregar equipamentos: {e}")
        return []

def fetch_manutencoes(supabase) -> List[Dict]:
    """Busca manutenções."""
    try:
        response = supabase.table("manutencoes").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Erro ao carregar manutenções: {e}")
        return []

def clear_form_state():
    """Limpa estado do formulário após sucesso."""
    for key in ["nome", "setor", "numero_serie"]:
        if key in st.session_state:
            del st.session_state[key]

def validate_equipment_data(nome: str, setor: str, numero_serie: str) -> Optional[str]:
    """Valida dados do equipamento."""
    if not nome.strip():
        return "Nome do equipamento é obrigatório"
    if not setor.strip():
        return "Setor é obrigatório"
    if not numero_serie.strip():
        return "Número de série é obrigatório"
    if len(nome.strip()) < 3:
        return "Nome deve ter pelo menos 3 caracteres"
    return None

def insert_equipment(supabase, nome: str, setor: str, numero_serie: str) -> bool:
    """Insere novo equipamento com tratamento de erro."""
    try:
        response = supabase.table("equipamentos").insert({
            "nome": nome.strip(),
            "setor": setor.strip(), 
            "numero_serie": numero_serie.strip(),
            "status": "Ativo",
            "created_at": datetime.now().isoformat()
        }).execute()
        return bool(response.data)
    except Exception as e:
        st.error(f"Erro ao cadastrar equipamento: {e}")
        return False

def start_maintenance(supabase, equipamento_id: int, tipo: str, descricao: str) -> bool:
    """Inicia manutenção com transação."""
    try:
        # Insere manutenção
        manut_response = supabase.table("manutencoes").insert({
            "equipamento_id": equipamento_id,
            "tipo": tipo,
            "descricao": descricao.strip(),
            "data_inicio": datetime.now().isoformat(),
            "status": "Em andamento"
        }).execute()
        
        if manut_response.data:
            # Atualiza status do equipamento
            supabase.table("equipamentos").update({
                "status": "Em manutenção"
            }).eq("id", equipamento_id).execute()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao abrir manutenção: {e}")
        return False

def finish_maintenance(supabase, manut_id: int, equipamento_id: int) -> bool:
    """Finaliza manutenção com transação."""
    try:
        # Atualiza manutenção
        manut_response = supabase.table("manutencoes").update({
            "data_fim": datetime.now().isoformat(),
            "status": "Concluída"
        }).eq("id", manut_id).execute()
        
        if manut_response.data:
            # Atualiza status do equipamento
            supabase.table("equipamentos").update({
                "status": "Ativo"
            }).eq("id", equipamento_id).execute()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao finalizar manutenção: {e}")
        return False

# -------------------
# Páginas
# -------------------
def pagina_inicial():
    """Página inicial melhorada."""
    st.title("🏥 Sistema de Manutenção | HSC")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Bem-vindo ao Sistema de Gestão de Manutenção
        
        Este sistema é fruto de uma **parceria entre o Hospital Santa Cruz (HSC) e a UNISC**, 
        desenvolvido para **apoiar o hospital na gestão e histórico das manutenções de equipamentos críticos**.
        
        #### 🎯 Funcionalidades Principais:
        - **📊 Dashboard Interativo**: Visualize status e métricas em tempo real
        - **🔧 Gestão de Manutenções**: Registre e acompanhe todas as intervenções
        - **➕ Cadastro de Equipamentos**: Mantenha inventário atualizado
        - **📈 Relatórios Avançados**: Análises detalhadas para tomada de decisão
        
        #### 🎯 Nossos Objetivos:
        Tornar a gestão de equipamentos **mais eficiente, segura e transparente** 
        para todos os profissionais envolvidos.
        """)
    
    with col2:
        st.info("""
        💡 **Dica de Navegação**
        
        Use a sidebar à esquerda para navegar entre as funcionalidades do sistema.
        
        Cada seção foi otimizada para facilitar seu trabalho diário.
        """)

def pagina_adicionar_equipamento(supabase):
    """Página de cadastro de equipamentos melhorada."""
    st.header("➕ Adicionar Novo Equipamento")
    
    with st.expander("ℹ️ Instruções", expanded=False):
        st.markdown("""
        **Informações importantes:**
        - Todos os campos são obrigatórios
        - O número de série deve ser único
        - As informações impactam diretamente nos relatórios
        - Equipamentos são criados com status "Ativo" por padrão
        """)
    
    with st.form("form_equipamento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input(
                "Nome do equipamento *", 
                placeholder="Ex: Respirador ABC-123",
                help="Nome descritivo do equipamento"
            )
            setor = st.text_input(
                "Setor *", 
                placeholder="Ex: UTI, Centro Cirúrgico",
                help="Localização do equipamento no hospital"
            )
        
        with col2:
            numero_serie = st.text_input(
                "Número de Série *", 
                placeholder="Ex: SN123456789",
                help="Número único de identificação"
            )
        
        submitted = st.form_submit_button("🚀 Cadastrar Equipamento", type="primary")
        
        if submitted:
            error = validate_equipment_data(nome, setor, numero_serie)
            if error:
                st.error(f"❌ {error}")
            else:
                with st.spinner("Cadastrando equipamento..."):
                    if insert_equipment(supabase, nome, setor, numero_serie):
                        st.success(f"✅ Equipamento '{nome}' cadastrado com sucesso!")
                        st.balloons()
                        # Limpa cache para atualizar dados
                        st.cache_data.clear()
                    else:
                        st.error("❌ Erro ao cadastrar equipamento. Tente novamente.")

def pagina_registrar_manutencao(supabase):
    """Página de manutenções melhorada."""
    st.header("🔧 Registrar Manutenção")
    
    tab1, tab2 = st.tabs(["🆕 Abrir Manutenção", "✅ Finalizar Manutenção"])
    
    with tab1:
        st.subheader("Abrir nova manutenção")
        
        equipamentos_data = fetch_equipamentos(supabase)
        
        if not equipamentos_data:
            st.warning("⚠️ Nenhum equipamento cadastrado. Cadastre um equipamento primeiro.")
            return
        
        # Filtrar apenas equipamentos ativos
        equipamentos_ativos = [e for e in equipamentos_data if e['status'] == 'Ativo']
        
        if not equipamentos_ativos:
            st.warning("⚠️ Nenhum equipamento ativo disponível para manutenção.")
            return
        
        with st.form("form_abrir_manutencao"):
            col1, col2 = st.columns(2)
            
            with col1:
                equipamento_dict = {f"{e['nome']} - {e['setor']}": e['id'] for e in equipamentos_ativos}
                equipamento_selecionado = st.selectbox(
                    "Equipamento *",
                    [""] + list(equipamento_dict.keys()),
                    help="Apenas equipamentos ativos são mostrados"
                )
                
                tipo = st.selectbox(
                    "Tipo de manutenção *", 
                    ["", "Preventiva", "Corretiva"],
                    help="Preventiva: programada | Corretiva: por falha"
                )
            
            with col2:
                descricao = st.text_area(
                    "Descrição da manutenção *",
                    placeholder="Descreva detalhadamente o trabalho a ser realizado...",
                    height=100
                )
            
            submitted = st.form_submit_button("🚀 Abrir Manutenção", type="primary")
            
            if submitted:
                if not equipamento_selecionado or not tipo or not descricao.strip():
                    st.error("❌ Todos os campos são obrigatórios!")
                else:
                    equipamento_id = equipamento_dict[equipamento_selecionado]
                    with st.spinner("Abrindo manutenção..."):
                        if start_maintenance(supabase, equipamento_id, tipo, descricao):
                            st.success(f"✅ Manutenção aberta com sucesso para {equipamento_selecionado}!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao abrir manutenção.")
    
    with tab2:
        st.subheader("Finalizar manutenção em andamento")
        
        manutencoes_data = fetch_manutencoes(supabase)
        manutencoes_abertas = [m for m in manutencoes_data if m['status'] == 'Em andamento']
        
        if not manutencoes_abertas:
            st.info("ℹ️ Não há manutenções em andamento no momento.")
            return
        
        equipamentos_data = fetch_equipamentos(supabase)
        
        with st.form("form_finalizar_manutencao"):
            manut_dict = {}
            for m in manutencoes_abertas:
                eq_nome = next((e['nome'] for e in equipamentos_data if e['id'] == m['equipamento_id']), "Desconhecido")
                manut_dict[f"{eq_nome} | {m['tipo']} | {m['descricao'][:50]}..."] = {
                    'manut_id': m['id'], 
                    'equip_id': m['equipamento_id']
                }
            
            manut_selecionada = st.selectbox(
                "Manutenção em andamento *",
                [""] + list(manut_dict.keys())
            )
            
            submitted = st.form_submit_button("✅ Finalizar Manutenção", type="primary")
            
            if submitted:
                if not manut_selecionada:
                    st.error("❌ Selecione uma manutenção para finalizar!")
                else:
                    manut_info = manut_dict[manut_selecionada]
                    with st.spinner("Finalizando manutenção..."):
                        if finish_maintenance(supabase, manut_info['manut_id'], manut_info['equip_id']):
                            st.success("✅ Manutenção finalizada com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao finalizar manutenção.")

def create_streamlit_charts(df_equip: pd.DataFrame, df_manut: pd.DataFrame):
    """Cria gráficos usando recursos nativos do Streamlit."""
    charts = {}
    
    # Dados para gráficos de equipamentos
    if not df_equip.empty:
        charts['setor_data'] = df_equip['setor'].value_counts()
        charts['status_data'] = df_equip['status'].value_counts()
    
    # Dados para gráficos de manutenções
    if not df_manut.empty:
        charts['manut_status_data'] = df_manut['status'].value_counts()
        charts['manut_tipo_data'] = df_manut['tipo'].value_counts()
    
    return charts

def pagina_dashboard(supabase):
    """Dashboard melhorado com visualizações interativas."""
    st.header("📊 Dashboard de Equipamentos e Manutenções")
    
    # Carrega dados
    equipamentos_data = fetch_equipamentos(supabase)
    manutencoes_data = fetch_manutencoes(supabase)
    
    if not equipamentos_data:
        st.warning("⚠️ Nenhum equipamento encontrado. Cadastre equipamentos primeiro.")
        return
    
    df_equip = pd.DataFrame(equipamentos_data)
    df_manut = pd.DataFrame(manutencoes_data) if manutencoes_data else pd.DataFrame()
    
    # KPIs principais
    st.subheader("📈 Indicadores Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_equip = len(df_equip)
    ativos = len(df_equip[df_equip['status'] == 'Ativo'])
    em_manut = len(df_equip[df_equip['status'] == 'Em manutenção'])
    
    col1.metric("Total de Equipamentos", total_equip)
    col2.metric("Ativos", ativos, delta=f"{(ativos/total_equip)*100:.1f}%")
    col3.metric("Em Manutenção", em_manut, delta=f"{(em_manut/total_equip)*100:.1f}%")
    
    # Disponibilidade
    disponibilidade = (ativos / total_equip) * 100 if total_equip > 0 else 0
    col4.metric("Disponibilidade", f"{disponibilidade:.1f}%")
    
    # KPIs de manutenção
    if not df_manut.empty:
        st.subheader("🔧 Indicadores de Manutenção")
        col1, col2, col3, col4 = st.columns(4)
        
        total_manut = len(df_manut)
        em_andamento = len(df_manut[df_manut['status'] == 'Em andamento'])
        concluidas = len(df_manut[df_manut['status'] == 'Concluída'])
        
        col1.metric("Total de Manutenções", total_manut)
        col2.metric("Em Andamento", em_andamento)
        col3.metric("Concluídas", concluidas)
        col4.metric("Taxa de Conclusão", f"{(concluidas/total_manut)*100:.1f}%")
    
    st.markdown("---")
    
    # Filtros
    st.subheader("🔍 Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        setores = ["Todos"] + sorted(df_equip['setor'].unique().tolist())
        filtro_setor = st.selectbox("Setor:", setores)
    
    with col2:
        status_list = ["Todos"] + sorted(df_equip['status'].unique().tolist())
        filtro_status = st.selectbox("Status:", status_list)
    
    with col3:
        if not df_manut.empty:
            tipos_manut = ["Todos"] + sorted(df_manut['tipo'].unique().tolist())
            filtro_tipo_manut = st.selectbox("Tipo de Manutenção:", tipos_manut)
    
    # Aplica filtros
    df_filtrado = df_equip.copy()
    if filtro_setor != "Todos":
        df_filtrado = df_filtrado[df_filtrado['setor'] == filtro_setor]
    if filtro_status != "Todos":
        df_filtrado = df_filtrado[df_filtrado['status'] == filtro_status]
    
    # Gráficos nativos do Streamlit
    st.subheader("📊 Visualizações")
    
    if not df_filtrado.empty:
        charts = create_streamlit_charts(df_filtrado, df_manut)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'setor_data' in charts:
                st.subheader("📊 Equipamentos por Setor")
                st.bar_chart(charts['setor_data'])
        
        with col2:
            if 'status_data' in charts:
                st.subheader("📈 Distribuição por Status")
                st.bar_chart(charts['status_data'])
        
        # Gráficos de manutenções
        if not df_manut.empty:
            col3, col4 = st.columns(2)
            
            with col3:
                if 'manut_status_data' in charts:
                    st.subheader("🔧 Manutenções por Status")
                    st.bar_chart(charts['manut_status_data'])
            
            with col4:
                if 'manut_tipo_data' in charts:
                    st.subheader("⚙️ Manutenções por Tipo")
                    st.bar_chart(charts['manut_tipo_data'])
    else:
        st.info("Nenhum equipamento encontrado com os filtros aplicados.")
    
    # Tabelas de dados
    with st.expander("📋 Dados Detalhados - Equipamentos", expanded=False):
        if not df_filtrado.empty:
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.info("Nenhum equipamento encontrado com os filtros aplicados.")
    
    if not df_manut.empty:
        with st.expander("📋 Dados Detalhados - Manutenções", expanded=False):
            # Merge com equipamentos para mostrar nomes
            df_manut_display = df_manut.merge(
                df_equip[['id', 'nome', 'setor']], 
                left_on='equipamento_id', 
                right_on='id', 
                how='left'
            )
            df_manut_display = df_manut_display.drop(['id_y', 'equipamento_id'], axis=1)
            df_manut_display = df_manut_display.rename(columns={'nome': 'equipamento'})
            st.dataframe(df_manut_display, use_container_width=True)

# -------------------
# Aplicação principal
# -------------------
def main():
    """Função principal da aplicação."""
    supabase = init_supabase()
    
    if not supabase:
        st.error("❌ Erro de conexão com o banco de dados. Verifique as configurações.")
        return
    
    pagina = show_sidebar()
    
    # Roteamento de páginas
    if pagina == "🏠 Página Inicial":
        pagina_inicial()
    elif pagina == "➕ Adicionar Equipamento":
        pagina_adicionar_equipamento(supabase)
    elif pagina == "🔧 Registrar Manutenção":
        pagina_registrar_manutencao(supabase)
    elif pagina == "📊 Dashboard":
        pagina_dashboard(supabase)

if __name__ == "__main__":
    main()
