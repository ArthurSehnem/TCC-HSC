import streamlit as st
import base64
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import plotly.express as px
import plotly.graph_objects as go

# -------------------
# Configuração inicial
# -------------------
st.set_page_config(
    page_title="Sistema de Manutenção | HSC",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🏥"
)

# -------------------
# Login único
# -------------------
def get_credentials():
    """Obter credenciais do Streamlit secrets ou usar valores padrão para teste"""
    try:
        return st.secrets["login"]["email"], st.secrets["login"]["password"]
    except:
        # Valores padrão para desenvolvimento/teste
        return "admin@hsc.com", "admin123"

def login():
    st.title("🏥 Login - Sistema HSC")
        
    # Texto explicativo
    st.info(
        """
        ⚠️ **Acesso restrito aos profissionais autorizados do Hospital Santa Cruz.**  
        Por favor, insira suas credenciais para continuar.
        """
    )

    # Formulário de login
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="seu.email@hsc.com")
        senha = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar", use_container_width=True)

    if submitted:
        admin_email, admin_password = get_credentials()
        if email == admin_email and senha == admin_password:
            st.success("Login realizado com sucesso!")
            st.session_state["user"] = email
            st.rerun()
        else:
            st.error(
                "Email ou senha incorretos.\n"
                "Se você esqueceu a senha, contate o setor de TI do hospital."
            )

# -------------------
# Inicialização do Supabase
# -------------------
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        st.info("Verifique se as credenciais do Supabase estão configuradas corretamente nos secrets.")
        return None

@st.cache_data(ttl=300)
def load_logo():
    try:
        with open("logo.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

# -------------------
# Funções auxiliares
# -------------------
def show_sidebar():
    with st.sidebar:
        st.markdown("# 🏥 HSC")
        
        encoded_logo = load_logo()
        if encoded_logo:
            st.markdown(
                f"<div style='text-align: center; margin-bottom: 20px;'><img src='data:image/png;base64,{encoded_logo}' width='120'></div>",
                unsafe_allow_html=True
            )
        
        st.markdown("---")
        
        # Informações do usuário logado
        if "user" in st.session_state:
            st.success(f"👤 Logado: {st.session_state['user']}")
            if st.button("Sair", use_container_width=True):
                del st.session_state["user"]
                st.rerun()
        
        st.markdown("---")
        
        return st.radio(
            "📋 Navegação",
            ["🏠 Página Inicial", "⚙️ Equipamentos", "🔧 Manutenções", "📊 Dashboard"],
            index=0
        )

@st.cache_data(ttl=60)  # Cache por 1 minuto
def fetch_equipamentos(supabase) -> List[Dict]:
    if not supabase:
        return []
    try:
        response = supabase.table("equipamentos").select("*").order("nome").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Erro ao carregar equipamentos: {e}")
        return []

@st.cache_data(ttl=60)  # Cache por 1 minuto
def fetch_manutencoes(supabase) -> List[Dict]:
    if not supabase:
        return []
    try:
        response = supabase.table("manutencoes").select("*").order("data_inicio", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Erro ao carregar manutenções: {e}")
        return []

def validate_equipment_data(nome: str, setor: str, numero_serie: str) -> Optional[str]:
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
    if not supabase:
        st.error("Conexão com banco de dados não disponível")
        return False
    
    try:
        response = supabase.table("equipamentos").insert({
            "nome": nome.strip(),
            "setor": setor.strip(),
            "numero_serie": numero_serie.strip(),
            "status": "Ativo",
        }).execute()
        
        if response.data:
            # Limpar cache para mostrar dados atualizados
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao cadastrar equipamento: {e}")
        return False

def start_maintenance(supabase, equipamento_id: int, tipo: str, descricao: str) -> bool:
    if not supabase:
        st.error("Conexão com banco de dados não disponível")
        return False
        
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
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao abrir manutenção: {e}")
        return False

def finish_maintenance(supabase, manut_id: int, equipamento_id: int) -> bool:
    if not supabase:
        st.error("Conexão com banco de dados não disponível")
        return False
        
    try:
        manut_response = supabase.table("manutencoes").update({
            "data_fim": datetime.now().isoformat(),
            "status": "Concluída"
        }).eq("id", manut_id).execute()
        
        if manut_response.data:
            supabase.table("equipamentos").update({"status": "Ativo"}).eq("id", equipamento_id).execute()
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao finalizar manutenção: {e}")
        return False

def mostrar_alertas_inteligencia(supabase):
    """
    Exibe alertas inteligentes baseados em histórico de manutenções e status de equipamentos.
    Funcionalidades:
    1. Detecção de equipamentos problemáticos (3+ manutenções em 6 meses)
    2. Análise de manutenções urgentes recorrentes (2+ urgências)
    3. Ranking de disponibilidade dos setores (<80% disponibilidade)
    4. Alertas baseados em padrões de falhas
    """
    if not supabase:
        return
        
    manutencoes_data = fetch_manutencoes(supabase)
    equipamentos_data = fetch_equipamentos(supabase)

    if not manutencoes_data and not equipamentos_data:
        return

    st.subheader("🚨 Alertas Inteligentes")
    alertas_encontrados = False

    # ------------------- 1️⃣ Equipamentos Problemáticos -------------------
    if manutencoes_data:
        df_manut = pd.DataFrame(manutencoes_data)
        seis_meses = datetime.now() - timedelta(days=180)
        
        # Converter data_inicio para datetime
        df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
        df_recente = df_manut[df_manut['data_inicio'] >= seis_meses]
        
        if not df_recente.empty:
            recorrentes = df_recente['equipamento_id'].value_counts()
            for eq_id, qtd in recorrentes.items():
                if qtd >= 3:  # Limite configurável
                    nome_eq = next((e['nome'] for e in equipamentos_data if e['id'] == eq_id), "Desconhecido")
                    setor_eq = next((e['setor'] for e in equipamentos_data if e['id'] == eq_id), "Desconhecido")
                    st.warning(f"⚠️ **Equipamento Problemático**: '{nome_eq}' ({setor_eq}) teve {qtd} manutenções nos últimos 6 meses!")
                    alertas_encontrados = True

        # ------------------- 2️⃣ Manutenções Urgentes Recorrentes -------------------
        urgentes = df_manut[df_manut['tipo'] == 'Urgente / Emergencial']
        if not urgentes.empty:
            contagem_urgente = urgentes['equipamento_id'].value_counts()
            for eq_id, qtd in contagem_urgente.items():
                if qtd >= 2:  # Limite configurável
                    nome_eq = next((e['nome'] for e in equipamentos_data if e['id'] == eq_id), "Desconhecido")
                    setor_eq = next((e['setor'] for e in equipamentos_data if e['id'] == eq_id), "Desconhecido")
                    st.error(f"🚨 **Alerta Crítico**: '{nome_eq}' ({setor_eq}) teve {qtd} manutenções urgentes! Necessária análise técnica.")
                    alertas_encontrados = True

        # ------------------- 3️⃣ Padrões de Falhas Consecutivas -------------------
        N = 3  # Limite de manutenções consecutivas do mesmo tipo
        for eq_id in df_manut['equipamento_id'].unique():
            df_eq = df_manut[df_manut['equipamento_id'] == eq_id].sort_values('data_inicio', ascending=False)
            tipos = df_eq['tipo'].tolist()
            if len(tipos) >= N and all(t == tipos[0] for t in tipos[:N]):
                nome_eq = next((e['nome'] for e in equipamentos_data if e['id'] == eq_id), "Desconhecido")
                setor_eq = next((e['setor'] for e in equipamentos_data if e['id'] == eq_id), "Desconhecido")
                st.warning(f"🔄 **Padrão Suspeito**: '{nome_eq}' ({setor_eq}) teve {N} manutenções consecutivas do tipo '{tipos[0]}'.")
                alertas_encontrados = True

    # ------------------- 4️⃣ Disponibilidade por Setor -------------------
    if equipamentos_data:
        df_equip = pd.DataFrame(equipamentos_data)
        limite_disponibilidade = 80  # Configurável
        
        for setor in df_equip['setor'].unique():
            total = len(df_equip[df_equip['setor'] == setor])
            ativos = len(df_equip[(df_equip['setor'] == setor) & (df_equip['status'] == 'Ativo')])
            dispon = (ativos / total) * 100 if total > 0 else 0
            
            if dispon < limite_disponibilidade:
                st.error(f"📉 **Baixa Disponibilidade**: Setor '{setor}' com apenas {dispon:.1f}% de equipamentos ativos ({ativos}/{total})")
                alertas_encontrados = True

    # ------------------- 5️⃣ Manutenções em Andamento há Muito Tempo -------------------
    if manutencoes_data:
        df_manut = pd.DataFrame(manutencoes_data)
        em_andamento = df_manut[df_manut['status'] == 'Em andamento']
        
        if not em_andamento.empty:
            limite_dias = 7  # Manutenções em andamento há mais de 7 dias
            agora = datetime.now()
            
            for _, manut in em_andamento.iterrows():
                data_inicio = pd.to_datetime(manut['data_inicio'])
                dias_em_andamento = (agora - data_inicio.to_pydatetime()).days
                
                if dias_em_andamento > limite_dias:
                    nome_eq = next((e['nome'] for e in equipamentos_data if e['id'] == manut['equipamento_id']), "Desconhecido")
                    st.warning(f"⏰ **Manutenção Demorada**: '{nome_eq}' está em manutenção há {dias_em_andamento} dias ({manut['tipo']})")
                    alertas_encontrados = True

    if not alertas_encontrados:
        st.success("✅ Nenhum alerta crítico no momento! Sistema operando dentro dos parâmetros normais.")

# -------------------
# Páginas
# -------------------
def pagina_inicial(supabase):
    """Página inicial com alertas e informações."""
    st.title("🏥 Sistema de Manutenção | HSC")
    
    # Mostrar alertas primeiro
    mostrar_alertas_inteligencia(supabase)
    
    st.markdown("---")
    
    st.markdown("""
### 👋 Bem-vindo ao Sistema de Gestão de Manutenção

Este sistema é fruto de uma **parceria entre o Hospital Santa Cruz (HSC) e a UNISC**, desenvolvido para **apoiar o hospital na gestão e histórico das manutenções de equipamentos críticos**.

#### 🚀 Funcionalidades Principais:
- **📊 Dashboard Interativo**: Visualize status e métricas em tempo real
- **🔧 Gestão de Manutenções**: Registre e acompanhe todas as intervenções
- **⚙️ Cadastro de Equipamentos**: Mantenha inventário atualizado
- **📈 Relatórios Avançados**: Análises detalhadas para tomada de decisão
- **🚨 Alertas Inteligentes**: Detecte equipamentos problemáticos automaticamente

#### 🎯 Nossos Objetivos:
Tornar a gestão de equipamentos **mais eficiente, segura e transparente** para todos os profissionais envolvidos.
""")

    # Estatísticas rápidas
    equipamentos_data = fetch_equipamentos(supabase)
    manutencoes_data = fetch_manutencoes(supabase)
    
    if equipamentos_data or manutencoes_data:
        st.markdown("### 📊 Resumo Rápido")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_equip = len(equipamentos_data) if equipamentos_data else 0
            st.metric("Total de Equipamentos", total_equip)
        
        with col2:
            if equipamentos_data:
                ativos = len([e for e in equipamentos_data if e['status'] == 'Ativo'])
                st.metric("Equipamentos Ativos", ativos)
            else:
                st.metric("Equipamentos Ativos", 0)
        
        with col3:
            total_manut = len(manutencoes_data) if manutencoes_data else 0
            st.metric("Total de Manutenções", total_manut)
        
        with col4:
            if manutencoes_data:
                em_andamento = len([m for m in manutencoes_data if m['status'] == 'Em andamento'])
                st.metric("Em Andamento", em_andamento)
            else:
                st.metric("Em Andamento", 0)

    st.info("💡 **Dica de Navegação**: Use a sidebar à esquerda para navegar entre as funcionalidades do sistema.")

def pagina_adicionar_equipamento(supabase):
    st.header("⚙️ Gestão de Equipamentos")

    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar", "📝 Gerenciar Status", "📋 Relatório"])

    # ------------------- Aba 1: Cadastrar Equipamento -------------------
    with tab1:
        st.subheader("Cadastrar Novo Equipamento")
        
        with st.expander("📋 Instruções", expanded=False):
            st.markdown("""
            - ✅ Todos os campos são obrigatórios
            - 🏷️ Número de série deve ser único
            - 🟢 Equipamentos são criados com status 'Ativo' por padrão
            """)

        setores_padrao = ["Hemodiálise", "Lavanderia", "Instrumentais Cirúrgicos", "UTI", "Centro Cirúrgico"]
        setor_escolhido = st.selectbox("🏢 Selecione o setor", setores_padrao + ["Outro"])

        setor_final = setor_escolhido
        if setor_escolhido == "Outro":
            setor_custom = st.text_input("Digite o nome do setor")
            if setor_custom.strip():
                setor_final = setor_custom.strip().title()
            else:
                setor_final = None

        with st.form("form_equipamento", clear_on_submit=True):
            nome = st.text_input("📋 Nome do equipamento *", placeholder="Ex: Respirador ABC-123")
            numero_serie = st.text_input("🔖 Número de Série *", placeholder="Ex: SN123456789")
            submitted = st.form_submit_button("✅ Cadastrar Equipamento", use_container_width=True)

        if submitted:
            if not setor_final:
                st.error("Por favor, selecione ou informe um setor.")
            else:
                error = validate_equipment_data(nome, setor_final, numero_serie)
                if error:
                    st.error(f"❌ {error}")
                else:
                    if insert_equipment(supabase, nome, setor_final, numero_serie):
                        st.success(f"✅ Equipamento '{nome}' cadastrado com sucesso!")
                        st.balloons()
                    else:
                        st.error("❌ Erro ao cadastrar equipamento.")

    # ------------------- Aba 2: Gerenciar Status -------------------
    with tab2:
        st.subheader("📝 Alterar Status dos Equipamentos")
        equipamentos_data = fetch_equipamentos(supabase)

        if equipamentos_data:
            # Agrupar por status para melhor visualização
            df_equip = pd.DataFrame(equipamentos_data)
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                setores = ["Todos"] + sorted(df_equip['setor'].unique().tolist())
                setor_filtro = st.selectbox("🏢 Filtrar por Setor", setores)
            with col2:
                status_options = ["Todos"] + sorted(df_equip['status'].unique().tolist())
                status_filtro = st.selectbox("📊 Filtrar por Status", status_options)
            
            # Aplicar filtros
            df_filtrado = df_equip.copy()
            if setor_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['setor'] == setor_filtro]
            if status_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['status'] == status_filtro]
            
            if not df_filtrado.empty:
                for _, equip in df_filtrado.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            status_icon = "🟢" if equip['status'] == "Ativo" else "🔧" if equip['status'] == "Em manutenção" else "🔴"
                            st.write(f"{status_icon} **{equip['nome']}** - {equip['setor']} | *{equip['status']}*")
                        
                        with col2:
                            novo_status = "Inativo" if equip['status'] == "Ativo" else "Ativo"
                            if st.button(f"→ {novo_status}", key=f"btn_{equip['id']}"):
                                try:
                                    supabase.table("equipamentos").update({"status": novo_status}).eq("id", equip['id']).execute()
                                    st.success(f"✅ Status alterado para {novo_status}")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao atualizar: {e}")
                        
                        st.divider()
            else:
                st.info("Nenhum equipamento encontrado com os filtros aplicados.")
        else:
            st.info("📋 Nenhum equipamento cadastrado ainda.")

    # ------------------- Aba 3: Relatório -------------------
    with tab3:
        st.subheader("📋 Relatório Analítico de Equipamentos")
        
        equipamentos_data = fetch_equipamentos(supabase)
        
        if equipamentos_data:
            df_equip = pd.DataFrame(equipamentos_data)
            
            # Estatísticas resumidas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Total", len(df_equip))
            with col2:
                ativos = len(df_equip[df_equip['status'] == 'Ativo'])
                st.metric("🟢 Ativos", ativos)
            with col3:
                em_manut = len(df_equip[df_equip['status'] == 'Em manutenção'])
                st.metric("🔧 Em Manutenção", em_manut)
            with col4:
                inativos = len(df_equip[df_equip['status'] == 'Inativo'])
                st.metric("🔴 Inativos", inativos)
            
            st.markdown("---")
            
            # Tabela detalhada com filtros
            col1, col2 = st.columns(2)
            with col1:
                setores = ["Todos"] + sorted(df_equip['setor'].unique().tolist())
                setor_filtro = st.selectbox("🏢 Filtrar Setor", setores, key="relatorio_setor")
            with col2:
                status_options = ["Todos"] + sorted(df_equip['status'].unique().tolist())
                status_filtro = st.selectbox("📊 Filtrar Status", status_options, key="relatorio_status")
            
            # Aplicar filtros
            df_filtrado = df_equip.copy()
            if setor_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['setor'] == setor_filtro]
            if status_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['status'] == status_filtro]
            
            # Exibir tabela
            st.dataframe(
                df_filtrado[['nome', 'setor', 'numero_serie', 'status']].sort_values(['status', 'setor', 'nome']), 
                use_container_width=True,
                hide_index=True
            )
                
        else:
            st.info("📋 Nenhum equipamento cadastrado para relatório.")

def pagina_registrar_manutencao(supabase):
    st.header("🔧 Gestão de Manutenções")
    
    # Mostrar alertas primeiro
    mostrar_alertas_inteligencia(supabase)
    
    tab1, tab2, tab3 = st.tabs(["🔧 Abrir Manutenção", "✅ Finalizar", "📋 Relatório"])
    
    # ------------------- Abrir nova manutenção -------------------
    with tab1:
        st.subheader("🔧 Abrir Nova Manutenção")
        
        equipamentos_ativos = [e for e in fetch_equipamentos(supabase) if e['status'] == 'Ativo']
        
        if not equipamentos_ativos:
            st.warning("⚠️ Nenhum equipamento ativo disponível para manutenção.")
            return
        
        # Explicação das categorias
        with st.expander("📋 Tipos de Manutenção - Guia", expanded=True):
            st.markdown("""
            - **🔄 Preventiva**: Manutenção programada antes de falhas, rotina planejada
            - **🚨 Urgente / Emergencial**: Para falhas críticas que exigem ação imediata
            - **⚖️ Calibração**: Ajustes periódicos de precisão (balanças, monitores)
            - **🧽 Higienização / Sanitização**: Limpeza obrigatória para prevenir contaminação
            """)
        
        equipamento_dict = {f"🏥 {e['nome']} - {e['setor']}": e['id'] for e in equipamentos_ativos}
        
        with st.form("form_abrir_manutencao", clear_on_submit=True):
            equipamento_selecionado = st.selectbox(
                "⚙️ Selecione o Equipamento *", 
                [""] + list(equipamento_dict.keys())
            )
            
            tipo = st.selectbox(
                "🏷️ Tipo de Manutenção *",
                ["", "Preventiva", "Urgente / Emergencial", "Calibração", "Higienização / Sanitização"]
            )
            
            descricao = st.text_area(
                "📝 Descrição Detalhada *", 
                height=100,
                placeholder="Descreva o problema ou serviço a ser realizado..."
            )
            
            col1, col2 = st.columns([1, 1])
            with col2:
                submitted = st.form_submit_button("🔧 Abrir Manutenção", use_container_width=True)
                
            if submitted:
                if not equipamento_selecionado or not tipo or not descricao.strip():
                    st.error("❌ Todos os campos são obrigatórios!")
                else:
                    equipamento_id = equipamento_dict[equipamento_selecionado]
                    if start_maintenance(supabase, equipamento_id, tipo, descricao):
                        st.success(f"✅ Manutenção aberta com sucesso para {equipamento_selecionado.split(' - ')[0]}!")
                        st.balloons()
                    else:
                        st.error("❌ Erro ao abrir manutenção.")

    # ------------------- Finalizar manutenção em andamento -------------------
    with tab2:
        st.subheader("✅ Finalizar Manutenção em Andamento")
        
        manutencoes_abertas = [m for m in fetch_manutencoes(supabase) if m['status'] == 'Em andamento']
        
        if not manutencoes_abertas:
            st.info("✅ Não há manutenções em andamento no momento.")
        else:
            st.info(f"🔧 {len(manutencoes_abertas)} manutenção(ões) em andamento")
            
            equipamentos_data = fetch_equipamentos(supabase)
            
            for m in manutencoes_abertas:
                eq_nome = next((e['nome'] for e in equipamentos_data if e['id'] == m['equipamento_id']), "Desconhecido")
                eq_setor = next((e['setor'] for e in equipamentos_data if e['id'] == m['equipamento_id']), "")
                
                with st.container():
                    st.markdown(f"### 🔧 {eq_nome}")
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**🏢 Setor:** {eq_setor}")
                        st.write(f"**🏷️ Tipo:** {m['tipo']}")
                    
                    with col2:
                        data_inicio = pd.to_datetime(m['data_inicio'])
                        st.write(f"**📅 Início:** {data_inicio.strftime('%d/%m/%Y %H:%M')}")
                        duracao = datetime.now() - data_inicio.to_pydatetime()
                        st.write(f"**⏱️ Duração:** {duracao.days}d {duracao.seconds//3600}h")
                    
                    with col3:
                        if st.button(f"✅ Finalizar", key=f"finalizar_{m['id']}", use_container_width=True):
                            if finish_maintenance(supabase, m['id'], m['equipamento_id']):
                                st.success("✅ Manutenção finalizada!")
                                st.rerun()
                            else:
                                st.error("❌ Erro ao finalizar.")
                    
                    with st.expander("📝 Descrição", expanded=False):
                        st.write(m['descricao'])
                    
                    st.divider()

    # ------------------- Aba 3: Relatório -------------------
    with tab3:
        st.subheader("📋 Relatório de Manutenções")
        
        manutencoes_data = fetch_manutencoes(supabase)
        equipamentos_data = fetch_equipamentos(supabase)
        
        if manutencoes_data:
            df_manut = pd.DataFrame(manutencoes_data)
            
            # Enriquecer com dados dos equipamentos
            for idx, row in df_manut.iterrows():
                equipamento = next((e for e in equipamentos_data if e['id'] == row['equipamento_id']), None)
                if equipamento:
                    df_manut.at[idx, 'nome_equipamento'] = equipamento['nome']
                    df_manut.at[idx, 'setor_equipamento'] = equipamento['setor']
            
            # Processar datas
            df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
            df_manut['data_fim'] = pd.to_datetime(df_manut['data_fim'])
            
            # Estatísticas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Total", len(df_manut))
            with col2:
                em_andamento = len(df_manut[df_manut['status'] == 'Em andamento'])
                st.metric("🔧 Em Andamento", em_andamento)
            with col3:
                concluidas = len(df_manut[df_manut['status'] == 'Concluída'])
                st.metric("✅ Concluídas", concluidas)
            with col4:
                if concluidas > 0:
                    df_concluidas = df_manut[df_manut['status'] == 'Concluída'].copy()
                    df_concluidas['duracao_horas'] = (df_concluidas['data_fim'] - df_concluidas['data_inicio']).dt.total_seconds() / 3600
                    duracao_media = df_concluidas['duracao_horas'].mean()
                    st.metric("⏱️ Duração Média (h)", f"{duracao_media:.1f}")
                else:
                    st.metric("⏱️ Duração Média (h)", "N/A")
            
            st.markdown("---")
            
            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                setores = ["Todos"] + sorted([s for s in df_manut['setor_equipamento'].dropna().unique()])
                setor_filtro = st.selectbox("🏢 Filtrar Setor", setores, key="manut_setor")
            with col2:
                tipos = ["Todos"] + sorted(df_manut['tipo'].unique().tolist())
                tipo_filtro = st.selectbox("🏷️ Filtrar Tipo", tipos, key="manut_tipo")
            with col3:
                status_options = ["Todos"] + sorted(df_manut['status'].unique().tolist())
                status_filtro = st.selectbox("📊 Filtrar Status", status_options, key="manut_status")
            
            # Aplicar filtros
            df_filtrado = df_manut.copy()
            if setor_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['setor_equipamento'] == setor_filtro]
            if tipo_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['tipo'] == tipo_filtro]
            if status_filtro != "Todos":
                df_filtrado = df_filtrado[df_filtrado['status'] == status_filtro]
            
            # Preparar dados para exibição
            if not df_filtrado.empty:
                df_display = df_filtrado.copy()
                
                # Formatar datas
                df_display['data_inicio_fmt'] = df_display['data_inicio'].dt.strftime('%d/%m/%Y %H:%M')
                df_display['data_fim_fmt'] = df_display['data_fim'].dt.strftime('%d/%m/%Y %H:%M')
                df_display['data_fim_fmt'] = df_display['data_fim_fmt'].fillna('Em andamento')
                
                # Calcular duração
                mask_concluida = df_display['status'] == 'Concluída'
                df_display.loc[mask_concluida, 'duracao_horas'] = (
                    df_display.loc[mask_concluida, 'data_fim'] - df_display.loc[mask_concluida, 'data_inicio']
                ).dt.total_seconds() / 3600
                df_display['duracao_fmt'] = df_display['duracao_horas'].apply(
                    lambda x: f"{x:.1f}h" if pd.notna(x) else "Em andamento"
                )
                
                # Selecionar colunas para exibir
                colunas_display = {
                    'nome_equipamento': 'Equipamento',
                    'setor_equipamento': 'Setor', 
                    'tipo': 'Tipo',
                    'status': 'Status',
                    'data_inicio_fmt': 'Início',
                    'data_fim_fmt': 'Fim',
                    'duracao_fmt': 'Duração',
                    'descricao': 'Descrição'
                }
                
                df_final = df_display[list(colunas_display.keys())].rename(columns=colunas_display)
                
                # Exibir tabela
                st.dataframe(
                    df_final.sort_values(['Status', 'Início'], ascending=[True, False]), 
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhuma manutenção encontrada com os filtros aplicados.")
                
        else:
            st.info("📋 Nenhuma manutenção registrada para relatório.")

def pagina_dashboard(supabase):
    """Dashboard completo com métricas, gráficos e análises detalhadas."""
    st.header("📊 Dashboard - Equipamentos e Manutenções")
    
    if not supabase:
        st.error("❌ Conexão com banco de dados não disponível")
        return
    
    # Carregar dados
    equipamentos_data = fetch_equipamentos(supabase)
    manutencoes_data = fetch_manutencoes(supabase)

    if not equipamentos_data:
        st.warning("⚠️ Nenhum equipamento encontrado. Cadastre equipamentos primeiro.")
        return

    df_equip = pd.DataFrame(equipamentos_data)
    df_manut = pd.DataFrame(manutencoes_data) if manutencoes_data else pd.DataFrame()

    # --------------------------------------
    # KPIs principais - Equipamentos
    # --------------------------------------
    st.subheader("📊 Indicadores Principais - Equipamentos")
    
    total_equip = len(df_equip)
    ativos = len(df_equip[df_equip['status'] == 'Ativo'])
    em_manut = len(df_equip[df_equip['status'] == 'Em manutenção'])
    inativos = len(df_equip[df_equip['status'] == 'Inativo'])
    disponibilidade = (ativos / total_equip) * 100 if total_equip > 0 else 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📊 Total", total_equip)
    with col2:
        st.metric("🟢 Ativos", ativos, delta=f"{disponibilidade:.1f}%")
    with col3:
        st.metric("🔧 Em Manutenção", em_manut)
    with col4:
        st.metric("🔴 Inativos", inativos)
    with col5:
        cor_disponibilidade = "normal" if disponibilidade >= 80 else "inverse"
        st.metric("📈 Disponibilidade", f"{disponibilidade:.1f}%", delta_color=cor_disponibilidade)

    st.markdown("---")

    # --------------------------------------
    # KPIs de manutenção
    # --------------------------------------
    st.subheader("🔧 Indicadores de Manutenção")

    if not df_manut.empty:
        total_manut = len(df_manut)
        em_andamento = len(df_manut[df_manut['status'] == 'Em andamento'])
        concluidas = len(df_manut[df_manut['status'] == 'Concluída'])
        taxa_conclusao = (concluidas / total_manut) * 100 if total_manut > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Manutenções", total_manut)
        with col2:
            st.metric("🔧 Em Andamento", em_andamento)
        with col3:
            st.metric("✅ Concluídas", concluidas)
        with col4:
            st.metric("📈 Taxa Conclusão", f"{taxa_conclusao:.1f}%")
    else:
        st.info("📋 Nenhuma manutenção registrada ainda.")
        total_manut = em_andamento = concluidas = taxa_conclusao = 0

    st.markdown("---")

    # --------------------------------------
    # Tempo Médio de Atendimento (TMA)
    # --------------------------------------
    st.subheader("⏱️ Tempo Médio de Atendimento (TMA)")
    
    if not df_manut.empty:
        df_concluidas = df_manut[df_manut['status'] == 'Concluída'].copy()
        
        if not df_concluidas.empty:
            df_concluidas['data_inicio'] = pd.to_datetime(df_concluidas['data_inicio'])
            df_concluidas['data_fim'] = pd.to_datetime(df_concluidas['data_fim'])
            df_concluidas['duracao_dias'] = (df_concluidas['data_fim'] - df_concluidas['data_inicio']).dt.total_seconds() / 86400
            df_concluidas['duracao_horas'] = (df_concluidas['data_fim'] - df_concluidas['data_inicio']).dt.total_seconds() / 3600
            
            tma_dias = df_concluidas['duracao_dias'].mean()
            tma_horas = df_concluidas['duracao_horas'].mean()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📅 TMA (dias)", f"{tma_dias:.1f}")
            with col2:
                st.metric("⏰ TMA (horas)", f"{tma_horas:.1f}")
            with col3:
                mediana_dias = df_concluidas['duracao_dias'].median()
                st.metric("📊 Mediana (dias)", f"{mediana_dias:.1f}")
        else:
            st.info("📊 Não há manutenções concluídas para calcular TMA.")
    else:
        st.info("📋 Nenhuma manutenção registrada.")

    st.markdown("---")

    # --------------------------------------
    # Gráficos lado a lado
    # --------------------------------------
    col1, col2 = st.columns(2)

    # Gráfico 1: Distribuição por Tipo de Manutenção
    with col1:
        st.subheader("🏷️ Manutenções por Tipo")
        if not df_manut.empty:
            df_tipo_count = df_manut['tipo'].value_counts().reset_index()
            df_tipo_count.columns = ['Tipo', 'Quantidade']
            
            fig_tipo = px.pie(
                df_tipo_count, 
                values='Quantidade', 
                names='Tipo',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_tipo.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_tipo, use_container_width=True)
        else:
            st.info("📊 Nenhuma manutenção para análise.")

    # Gráfico 2: Status dos Equipamentos
    with col2:
        st.subheader("📊 Status dos Equipamentos")
        status_count = df_equip['status'].value_counts().reset_index()
        status_count.columns = ['Status', 'Quantidade']
        
        # Definir cores para cada status
        color_map = {
            'Ativo': '#2E8B57',      # Verde
            'Em manutenção': '#FF8C00', # Laranja
            'Inativo': '#DC143C'      # Vermelho
        }
        colors = [color_map.get(status, '#1f77b4') for status in status_count['Status']]
        
        fig_status = px.bar(
            status_count, 
            x='Status', 
            y='Quantidade', 
            text='Quantidade',
            color='Status',
            color_discrete_map=color_map
        )
        fig_status.update_layout(showlegend=False)
        fig_status.update_traces(textposition='outside')
        st.plotly_chart(fig_status, use_container_width=True)

    st.markdown("---")

    # --------------------------------------
    # Análise por Setor
    # --------------------------------------
    st.subheader("🏢 Análise por Setor")
    
    # Calcular disponibilidade por setor
    setor_stats = []
    for setor in df_equip['setor'].unique():
        df_setor = df_equip[df_equip['setor'] == setor]
        total_setor = len(df_setor)
        ativos_setor = len(df_setor[df_setor['status'] == 'Ativo'])
        em_manut_setor = len(df_setor[df_setor['status'] == 'Em manutenção'])
        disponib_setor = (ativos_setor / total_setor) * 100 if total_setor > 0 else 0
        
        setor_stats.append({
            'Setor': setor,
            'Total': total_setor,
            'Ativos': ativos_setor,
            'Em Manutenção': em_manut_setor,
            'Disponibilidade (%)': round(disponib_setor, 1)
        })
    
    df_setor_stats = pd.DataFrame(setor_stats)
    
    # Exibir tabela
    st.dataframe(
        df_setor_stats.sort_values('Disponibilidade (%)', ascending=False),
        use_container_width=True,
        hide_index=True
    )
    
    # Gráfico de disponibilidade por setor
    fig_dispon = px.bar(
        df_setor_stats.sort_values('Disponibilidade (%)', ascending=True), 
        x='Disponibilidade (%)', 
        y='Setor',
        orientation='h',
        text='Disponibilidade (%)',
        color='Disponibilidade (%)',
        color_continuous_scale='RdYlGn',
        range_color=[0, 100]
    )
    fig_dispon.update_traces(texttemplate='%{text}%', textposition='inside')
    fig_dispon.update_layout(
        title="📊 Disponibilidade por Setor (%)",
        xaxis_title="Disponibilidade (%)",
        yaxis_title="Setor"
    )
    st.plotly_chart(fig_dispon, use_container_width=True)

    # --------------------------------------
    # Timeline de Manutenções (se houver dados)
    # --------------------------------------
    if not df_manut.empty and len(df_manut) > 1:
        st.markdown("---")
        st.subheader("📈 Timeline de Manutenções")
        
        df_timeline = df_manut.copy()
        df_timeline['data_inicio'] = pd.to_datetime(df_timeline['data_inicio'])
        df_timeline['mes_ano'] = df_timeline['data_inicio'].dt.to_period('M')
        
        timeline_data = df_timeline.groupby(['mes_ano', 'tipo']).size().reset_index(name='quantidade')
        timeline_data['mes_ano_str'] = timeline_data['mes_ano'].astype(str)
        
        fig_timeline = px.line(
            timeline_data, 
            x='mes_ano_str', 
            y='quantidade',
            color='tipo',
            markers=True,
            title="Evolução das Manutenções por Tipo"
        )
        fig_timeline.update_layout(
            xaxis_title="Período",
            yaxis_title="Quantidade de Manutenções"
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

    # --------------------------------------
    # Top Equipamentos com Mais Manutenções
    # --------------------------------------
    if not df_manut.empty:
        st.markdown("---")
        st.subheader("🔧 Top 5 - Equipamentos com Mais Manutenções")
        
        # Enriquecer dados de manutenção com nomes dos equipamentos
        df_manut_enriched = df_manut.copy()
        for idx, row in df_manut_enriched.iterrows():
            equipamento = next((e for e in equipamentos_data if e['id'] == row['equipamento_id']), None)
            if equipamento:
                df_manut_enriched.at[idx, 'nome_equipamento'] = equipamento['nome']
                df_manut_enriched.at[idx, 'setor_equipamento'] = equipamento['setor']
        
        if 'nome_equipamento' in df_manut_enriched.columns:
            top_equipamentos = (df_manut_enriched['nome_equipamento']
                               .value_counts()
                               .head(5)
                               .reset_index())
            top_equipamentos.columns = ['Equipamento', 'Quantidade de Manutenções']
            
            fig_top = px.bar(
                top_equipamentos,
                x='Quantidade de Manutenções',
                y='Equipamento',
                orientation='h',
                text='Quantidade de Manutenções',
                color='Quantidade de Manutenções',
                color_continuous_scale='Reds'
            )
            fig_top.update_traces(textposition='inside')
            fig_top.update_layout(
                title="Equipamentos que Mais Demandam Manutenção",
                showlegend=False
            )
            st.plotly_chart(fig_top, use_container_width=True)

    # --------------------------------------
    # Alertas Resumidos no Dashboard
    # --------------------------------------
    st.markdown("---")
    st.subheader("🚨 Resumo de Alertas")
    
    if not df_manut.empty:
        # Contadores de alertas
        alertas_criticos = 0
        alertas_atencao = 0
        
        # Equipamentos com muitas manutenções
        seis_meses = datetime.now() - timedelta(days=180)
        df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
        df_recente = df_manut[df_manut['data_inicio'] >= seis_meses]
        
        if not df_recente.empty:
            recorrentes = df_recente['equipamento_id'].value_counts()
            alertas_atencao += len(recorrentes[recorrentes >= 3])
        
        # Manutenções urgentes
        urgentes = df_manut[df_manut['tipo'] == 'Urgente / Emergencial']
        if not urgentes.empty:
            contagem_urgente = urgentes['equipamento_id'].value_counts()
            alertas_criticos += len(contagem_urgente[contagem_urgente >= 2])
        
        # Setores com baixa disponibilidade
        baixa_disponibilidade = 0
        for setor in df_equip['setor'].unique():
            total = len(df_equip[df_equip['setor'] == setor])
            ativos = len(df_equip[(df_equip['setor'] == setor) & (df_equip['status'] == 'Ativo')])
            dispon = (ativos / total) * 100 if total > 0 else 0
            if dispon < 80:
                baixa_disponibilidade += 1
        
        alertas_criticos += baixa_disponibilidade
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🚨 Alertas Críticos", alertas_criticos)
        with col2:
            st.metric("⚠️ Alertas de Atenção", alertas_atencao)
        with col3:
            total_alertas = alertas_criticos + alertas_atencao
            st.metric("📊 Total de Alertas", total_alertas)
    
    else:
        st.info("📊 Aguardando dados de manutenção para análise de alertas.")

# -------------------
# Main
# -------------------
def main():
    # Verificar login primeiro
    if "user" not in st.session_state:
        login()
        return
    
    # Inicializar conexão com banco
    supabase = init_supabase()
    
    # Mostrar sidebar e obter página selecionada
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

if __name__ == "__main__":
    main()
