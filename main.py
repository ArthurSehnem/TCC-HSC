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
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes
SETORES_PADRAO = ["Hemodiálise", "Lavanderia", "Instrumentais Cirúrgicos", "Emergência"]
TIPOS_MANUTENCAO = ["Preventiva", "Corretiva", "Urgente", "Calibração", "Higienização", "Inspeção"]
STATUS_EQUIPAMENTOS = ["Ativo", "Inativo"]

# -------------------
# Sistema de Login
# -------------------
ADMIN_EMAIL = st.secrets["login"]["email"]
ADMIN_PASSWORD = st.secrets["login"]["password"]

def login():
    st.title("Sistema HSC - Login")
    st.info("Acesso restrito aos profissionais autorizados do Hospital Santa Cruz.")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("🔐 Entrar", use_container_width=True)
    
    if submitted:
        if not email or not senha:
            st.error("❌ Preencha todos os campos.")
        elif email == ADMIN_EMAIL and senha == ADMIN_PASSWORD:
            st.success("✅ Login realizado com sucesso!")
            st.session_state["user"] = email
            st.session_state["login_time"] = datetime.now()
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Email ou senha incorretos.")

def check_session():
    if "user" in st.session_state and "login_time" in st.session_state:
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
    st.session_state.clear()
    st.success("✅ Logout realizado!")
    st.rerun()

# -------------------
# Conexão com banco
# -------------------
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["SUPABASE_URL"]
        key = st.secrets["supabase"]["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Erro ao conectar com o banco: {e}")
        return None

@st.cache_data(ttl=300)
def load_logo():
    try:
        with open("logo.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

# -------------------
# Sidebar
# -------------------
def show_sidebar():
    # Logo se existir
    encoded_logo = load_logo()
    if encoded_logo:
        st.sidebar.image(f"data:image/png;base64,{encoded_logo}", width=120)
        
    st.sidebar.markdown("---")
    
    # Menu principal
    menu = st.sidebar.radio(
        "Menu Principal", 
        ["🏠 Início", "⚙️ Equipamentos", "🔧 Manutenções", "📊 Dashboard"],
        index=0
    )
    
    return menu.split(" ", 1)[1]  # Remove emoji do retorno

# -------------------
# Funções de banco
# -------------------
def fetch_equipamentos(supabase) -> List[Dict]:
    try:
        response = supabase.table("equipamentos").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Erro ao carregar equipamentos: {e}")
        return []

def fetch_manutencoes(supabase) -> List[Dict]:
    try:
        response = supabase.table("manutencoes").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Erro ao carregar manutenções: {e}")
        return []

def validate_equipment_data(nome: str, setor: str, numero_serie: str) -> Optional[str]:
    if not nome.strip(): return "❌ Nome é obrigatório"
    if not setor.strip(): return "❌ Setor é obrigatório"
    if not numero_serie.strip(): return "❌ Número de série é obrigatório"
    if len(nome.strip()) < 3: return "❌ Nome muito curto (mínimo 3 caracteres)"
    return None

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
        st.error(f"❌ Erro ao cadastrar equipamento: {e}")
        return False

def start_maintenance(supabase, equipamento_id: int, tipo: str, descricao: str) -> bool:
    try:
        # Inserir manutenção
        manut_response = supabase.table("manutencoes").insert({
            "equipamento_id": equipamento_id,
            "tipo": tipo,
            "descricao": descricao.strip(),
            "data_inicio": datetime.now().isoformat(),
            "status": "Em andamento"
        }).execute()
        
        if manut_response.data:
            # Atualizar status do equipamento
            supabase.table("equipamentos").update({"status": "Em manutenção"}).eq("id", equipamento_id).execute()
            return True
        return False
    except Exception as e:
        st.error(f"❌ Erro ao abrir manutenção: {e}")
        return False

def finish_maintenance(supabase, manut_id: int, equipamento_id: int) -> bool:
    try:
        # Finalizar manutenção
        manut_response = supabase.table("manutencoes").update({
            "data_fim": datetime.now().isoformat(),
            "status": "Concluída"
        }).eq("id", manut_id).execute()
        
        if manut_response.data:
            # Retornar equipamento para ativo
            supabase.table("equipamentos").update({"status": "Ativo"}).eq("id", equipamento_id).execute()
            return True
        return False
    except Exception as e:
        st.error(f"❌ Erro ao finalizar manutenção: {e}")
        return False

# -------------------
# Sistema de alertas
# -------------------
def gerar_alertas(df_equip, df_manut):
    if df_equip.empty or df_manut.empty:
        return [], [], []
    
    df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
    alertas_criticos, alertas_importantes, alertas_info = [], [], []
    
    # 1. Equipamentos com muitas manutenções (4+ em 3 meses)
    tres_meses = datetime.now() - timedelta(days=90)
    manut_3m = df_manut[df_manut['data_inicio'] >= tres_meses]
    problem_equip = manut_3m.groupby('equipamento_id').size()
    for eq_id, qtd in problem_equip.items():
        if qtd >= 4:
            eq_nome = df_equip[df_equip['id'] == eq_id]['nome'].values
            if len(eq_nome) > 0:
                alertas_criticos.append(f"🚨 **{eq_nome[0]}** teve {qtd} manutenções em 3 meses")
    
    # 2. Manutenções urgentes recorrentes
    urgentes = df_manut[df_manut['tipo'] == 'Urgente']
    urgentes_por_equip = urgentes.groupby('equipamento_id').size()
    for eq_id, qtd in urgentes_por_equip.items():
        if qtd >= 2:
            eq_nome = df_equip[df_equip['id'] == eq_id]['nome'].values
            if len(eq_nome) > 0:
                alertas_criticos.append(f"🚨 **{eq_nome[0]}** teve {qtd} manutenções urgentes")
    
    # 3. Manutenções longas (mais de 7 dias)
    em_andamento = df_manut[df_manut['status'] == 'Em andamento']
    for idx, row in em_andamento.iterrows():
        dias = (datetime.now() - row['data_inicio']).days
        if dias > 7:
            eq_nome = df_equip[df_equip['id'] == row['equipamento_id']]['nome'].values
            if len(eq_nome) > 0:
                alertas_criticos.append(f"🚨 **{eq_nome[0]}** em manutenção há {dias} dias")
    
    # 4. Baixa disponibilidade por setor
    dispo_setor = df_equip.groupby('setor')['status'].apply(lambda x: (x == 'Ativo').sum() / len(x) * 100)
    for setor, dispo in dispo_setor.items():
        if dispo < 75:
            alertas_importantes.append(f"⚠️ **{setor}**: {dispo:.1f}% de disponibilidade")
    
    # 5. Sem manutenção preventiva há muito tempo
    seis_meses = datetime.now() - timedelta(days=180)
    preventivas_6m = df_manut[(df_manut['tipo'] == 'Preventiva') & (df_manut['data_inicio'] >= seis_meses)]['equipamento_id'].unique()
    sem_preventiva = df_equip[(~df_equip['id'].isin(preventivas_6m)) & (df_equip['status'] == 'Ativo')]
    for idx, row in sem_preventiva.head(5).iterrows():
        alertas_info.append(f"💡 **{row['nome']}** sem manutenção preventiva há 6+ meses")
    
    return alertas_criticos, alertas_importantes, alertas_info

def calcular_metricas(df_equip, df_manut):
    if df_equip.empty:
        return {}
    
    total = len(df_equip)
    ativos = len(df_equip[df_equip['status'] == 'Ativo'])
    manutencao = len(df_equip[df_equip['status'] == 'Em manutenção'])
    disponibilidade = (ativos / total * 100) if total > 0 else 0
    
    # Manutenções último mês
    if not df_manut.empty:
        df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
        ultimo_mes = datetime.now() - timedelta(days=30)
        manut_mes = len(df_manut[df_manut['data_inicio'] >= ultimo_mes])
    else:
        manut_mes = 0
    
    return {
        'total': total, 'ativos': ativos, 'manutencao': manutencao,
        'disponibilidade': disponibilidade, 'manut_mes': manut_mes
    }

# -------------------
# Páginas
# -------------------
def pagina_inicial(supabase):
    st.title("Sistema de Manutenção HSC")
    
    # Carregar dados
    df_equip = pd.DataFrame(fetch_equipamentos(supabase))
    df_manut = pd.DataFrame(fetch_manutencoes(supabase))
    
    if df_equip.empty:
        st.warning("⚠️ Nenhum equipamento cadastrado. Comece adicionando equipamentos na aba **Equipamentos**!")
        return
    
    st.markdown(
        """
        Bem-vindo ao **Sistema de Manutenção do HSC** 👨‍⚕️🏥  

        Esta plataforma foi desenvolvida para otimizar a gestão dos equipamentos hospitalares, oferecendo **visão integrada do inventário, acompanhamento das manutenções e indicadores de desempenho**.  
        Aqui você pode **cadastrar equipamentos**, registrar e consultar manutenções realizadas, além de monitorar a **disponibilidade e o status dos ativos em tempo real**.  

        O sistema também conta com um módulo de **alertas inteligentes**, classificados em três níveis:  
        - 🚨 **Críticos**: situações que exigem **ação imediata**, como equipamentos vitais inativos ou manutenção atrasada.  
        - ⚠️ **Importantes**: avisos que demandam atenção em breve, como revisões programadas próximas do vencimento.  
        - 💡 **Informativos**: lembretes gerais e recomendações úteis para o acompanhamento da frota de equipamentos.  

        Dessa forma, o sistema garante **segurança, eficiência e transparência** na gestão hospitalar, apoiando decisões rápidas e assertivas.  
        """
    )
        
    # Métricas principais
    metricas = calcular_metricas(df_equip, df_manut)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("⚙️ Total de Equipamentos", metricas["total"])
    with col2:
        color = "normal" if metricas["disponibilidade"] >= 80 else "inverse"
        st.metric("📊 Disponibilidade", f"{metricas['disponibilidade']:.1f}%")
    with col3:
        st.metric("✅ Equipamentos Ativos", metricas["ativos"])
    with col4:
        st.metric("🔧 Em Manutenção", metricas["manutencao"])
    
    st.markdown("---")
    
    # Alertas do sistema
    if not df_manut.empty:
        criticos, importantes, info = gerar_alertas(df_equip, df_manut)
        
        st.subheader("🚨 Alertas Inteligentes")
        
        # Alertas críticos
        if criticos:
            st.error("**CRÍTICOS - Ação Imediata Necessária:**")
            for alerta in criticos:
                st.write(f"• {alerta}")
        
        # Alertas importantes
        if importantes:
            with st.expander("⚠️ **Alertas Importantes**", expanded=not criticos):
                for alerta in importantes:
                    st.write(f"• {alerta}")
        
        # Alertas informativos
        if info:
            with st.expander("💡 **Alertas Informativos**"):
                for alerta in info:
                    st.write(f"• {alerta}")
        
        # Sistema OK
        if not any([criticos, importantes, info]):
            st.success("🎉 **Sistema Operacional** - Todos os equipamentos funcionando normalmente!")
    

def pagina_equipamentos(supabase):
    st.title("⚙️ Gestão de Equipamentos")
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Novo", "📝 Gerenciar Existentes", "📊 Relatórios"])
    
    # Tab 1 - Cadastrar
    with tab1:
        st.subheader("Cadastrar Novo Equipamento")
        
        with st.form("cadastro_equip", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("📛 Nome do Equipamento", placeholder="Ex: Monitor Cardíaco")
                setor = st.selectbox("🏢 Setor", SETORES_PADRAO + ["Outro"])
                if setor == "Outro":
                    setor_custom = st.text_input("✏️ Nome do Setor")
                    setor = setor_custom.strip().title() if setor_custom.strip() else setor
            
            with col2:
                numero_serie = st.text_input("🔢 Número de Série", placeholder="Ex: HSC-2024-001")
                st.write("")  # Espaço
                st.write("")  # Espaço
            
            submitted = st.form_submit_button("✅ Cadastrar Equipamento", use_container_width=True)
            
            if submitted and setor != "Outro":
                error = validate_equipment_data(nome, setor, numero_serie)
                if error:
                    st.error(error)
                elif insert_equipment(supabase, nome, setor, numero_serie):
                    st.success(f"✅ **{nome}** cadastrado com sucesso!")
                    st.balloons()
                    st.cache_data.clear()
    
    # Tab 2 - Gerenciar
    with tab2:
        st.subheader("Gerenciar Equipamentos Existentes")
        
        equipamentos = fetch_equipamentos(supabase)
        if equipamentos:
            # Busca
            busca = st.text_input("🔍 Buscar equipamento", placeholder="Digite nome ou setor...")
            
            if busca:
                equipamentos = [e for e in equipamentos if 
                               busca.lower() in e['nome'].lower() or 
                               busca.lower() in e['setor'].lower() or 
                               busca.lower() in e['numero_serie'].lower()]
            
            if equipamentos:
                # Criar dicionário para seleção
                equip_options = []
                for e in equipamentos:
                    status_icon = "🟢" if e['status'] == 'Ativo' else "🔴" if e['status'] == 'Em manutenção' else "🟡"
                    equip_options.append(f"{status_icon} {e['nome']} | {e['setor']} | {e['status']}")
                
                equip_dict = {opt: equipamentos[i] for i, opt in enumerate(equip_options)}
                
                selecionado = st.selectbox("Selecionar Equipamento:", equip_options)
                
                if selecionado:
                    equip = equip_dict[selecionado]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"**Equipamento:** {equip['nome']}\n\n**Setor:** {equip['setor']}\n\n**Série:** {equip['numero_serie']}\n\n**Status Atual:** {equip['status']}")
                    
                    with col2:
                        novo_status = st.selectbox("Alterar Status:", [s for s in STATUS_EQUIPAMENTOS if s != equip['status']])
                        if st.button(f"🔄 Alterar para {novo_status}", use_container_width=True):
                            try:
                                supabase.table("equipamentos").update({"status": novo_status}).eq("id", equip['id']).execute()
                                st.success(f"✅ Status alterado para **{novo_status}**!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao alterar status: {e}")
            else:
                st.warning("⚠️ Nenhum equipamento encontrado com esse termo de busca.")
        else:
            st.warning("⚠️ Nenhum equipamento cadastrado.")
    
    # Tab 3 - Relatórios
    with tab3:
        st.subheader("Relatórios de Equipamentos")
        
        equipamentos = fetch_equipamentos(supabase)
        if equipamentos:
            df = pd.DataFrame(equipamentos)
            
            # Métricas
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", len(df))
            col2.metric("Ativos", len(df[df['status'] == 'Ativo']))
            col3.metric("Em Manutenção", len(df[df['status'] == 'Em manutenção']))
            
            # Gráficos
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                setor_counts = df['setor'].value_counts()
                fig1 = px.pie(values=setor_counts.values, names=setor_counts.index, 
                             title="📊 Equipamentos por Setor")
                st.plotly_chart(fig1, use_container_width=True)
            
            with col_g2:
                status_counts = df['status'].value_counts()
                fig2 = px.bar(x=status_counts.index, y=status_counts.values, 
                             title="📈 Equipamentos por Status")
                st.plotly_chart(fig2, use_container_width=True)
            
            # Tabela
            st.subheader("📋 Lista Completa")
            st.dataframe(df[['nome', 'setor', 'numero_serie', 'status']], use_container_width=True)
            
            # Export
            csv = df.to_csv(index=False)
            st.download_button("📥 Baixar Relatório CSV", csv, 
                             f"equipamentos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                             use_container_width=True)

def pagina_manutencoes(supabase):
    st.title("🔧 Gestão de Manutenções")
    
    tab1, tab2, tab3 = st.tabs(["🆕 Abrir Manutenção", "✅ Finalizar Manutenção", "📊 Relatórios"])
    
    # Tab 1 - Abrir
    with tab1:
        st.subheader("Abrir Nova Manutenção")
        
        equipamentos_ativos = [e for e in fetch_equipamentos(supabase) if e['status'] == "Ativo"]
        
        if equipamentos_ativos:
            with st.form("abrir_manut", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    equip_options = [f"{e['nome']} - {e['setor']}" for e in equipamentos_ativos]
                    equip_dict = {opt: equipamentos_ativos[i]['id'] for i, opt in enumerate(equip_options)}
                    equipamento = st.selectbox("⚙️ Selecionar Equipamento:", equip_options)
                    tipo = st.selectbox("🔧 Tipo de Manutenção:", TIPOS_MANUTENCAO)
                
                with col2:
                    descricao = st.text_area("📝 Descrição da Manutenção:", 
                                           placeholder="Descreva o problema ou serviço necessário...",
                                           height=100)
                
                submitted = st.form_submit_button("🔧 Abrir Manutenção", use_container_width=True)
                
                if submitted and equipamento and tipo and descricao.strip():
                    if start_maintenance(supabase, equip_dict[equipamento], tipo, descricao):
                        st.success(f"✅ Manutenção **{tipo}** aberta para **{equipamento.split(' - ')[0]}**!")
                        st.balloons()
                        st.cache_data.clear()
                elif submitted:
                    st.error("❌ Preencha todos os campos obrigatórios.")
        else:
            st.warning("⚠️ Nenhum equipamento ativo disponível para manutenção.")
    
    # Tab 2 - Finalizar
    with tab2:
        st.subheader("Finalizar Manutenções em Andamento")
        
        manutencoes_abertas = [m for m in fetch_manutencoes(supabase) if m['status'] == "Em andamento"]
        
        if manutencoes_abertas:
            equipamentos = fetch_equipamentos(supabase)
            
            # Preparar informações das manutenções
            manut_info = []
            for m in manutencoes_abertas:
                eq = next((e for e in equipamentos if e['id'] == m['equipamento_id']), None)
                if eq:
                    dias = (datetime.now() - pd.to_datetime(m['data_inicio'])).days
                    status_icon = "🚨" if dias > 7 else "🔧"
                    manut_info.append({
                        'display': f"{status_icon} {eq['nome']} | {m['tipo']} | {dias} dias",
                        'manut_id': m['id'],
                        'equip_id': m['equipamento_id'],
                        'descricao': m.get('descricao', 'Sem descrição')
                    })
            
            if manut_info:
                manut_dict = {m['display']: m for m in manut_info}
                selecionada = st.selectbox("🔧 Selecionar Manutenção:", list(manut_dict.keys()))
                
                if selecionada:
                    info = manut_dict[selecionada]
                    
                    # Mostrar detalhes
                    st.info(f"**Descrição:** {info['descricao']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Finalizar Manutenção", use_container_width=True):
                            if finish_maintenance(supabase, info['manut_id'], info['equip_id']):
                                st.success("✅ Manutenção finalizada com sucesso!")
                                st.balloons()
                                st.cache_data.clear()
                                st.rerun()
                    
                    with col2:
                        st.write("")  # Espaço para alinhamento
        else:
            st.info("ℹ️ Nenhuma manutenção em andamento no momento.")
    
    # Tab 3 - Relatórios
    with tab3:
        st.subheader("Relatórios de Manutenções")
        
        manutencoes = fetch_manutencoes(supabase)
        if manutencoes:
            df = pd.DataFrame(manutencoes)
            equipamentos = fetch_equipamentos(supabase)
            
            # Adicionar nomes dos equipamentos
            for idx, row in df.iterrows():
                eq = next((e for e in equipamentos if e['id'] == row['equipamento_id']), None)
                if eq:
                    df.at[idx, 'equipamento'] = eq['nome']
                    df.at[idx, 'setor'] = eq['setor']
            
            # Métricas
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", len(df))
            col2.metric("Em Andamento", len(df[df['status'] == 'Em andamento']))
            col3.metric("Concluídas", len(df[df['status'] == 'Concluída']))
            
            # Gráficos
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                tipo_counts = df['tipo'].value_counts()
                fig1 = px.pie(values=tipo_counts.values, names=tipo_counts.index, 
                             title="📊 Manutenções por Tipo")
                st.plotly_chart(fig1, use_container_width=True)
            
            with col_g2:
                if 'setor' in df.columns:
                    setor_counts = df['setor'].value_counts()
                    fig2 = px.bar(x=setor_counts.index, y=setor_counts.values, 
                                 title="📈 Manutenções por Setor")
                    st.plotly_chart(fig2, use_container_width=True)
            
            # Tabela
            st.subheader("📋 Histórico de Manutenções")
            colunas_exibir = ['equipamento', 'setor', 'tipo', 'status'] if 'equipamento' in df.columns else ['tipo', 'status']
            st.dataframe(df[colunas_exibir], use_container_width=True)
        else:
            st.warning("⚠️ Nenhuma manutenção registrada.")

def pagina_dashboard(supabase):
    st.title("📊 Dashboard Executivo")
    
    df_equip = pd.DataFrame(fetch_equipamentos(supabase))
    df_manut = pd.DataFrame(fetch_manutencoes(supabase))
    
    if df_equip.empty:
        st.warning("⚠️ Cadastre equipamentos primeiro para visualizar o dashboard.")
        return
    
    # Métricas principais
    metricas = calcular_metricas(df_equip, df_manut)
    
    st.subheader("📈 Métricas Principais")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("⚙️ Total de Equipamentos", metricas["total"])
    col2.metric("📊 Disponibilidade Geral", f"{metricas['disponibilidade']:.1f}%", 
                delta=f"{metricas['disponibilidade']-75:.1f}%" if metricas['disponibilidade'] != 75 else None)
    col3.metric("✅ Equipamentos Ativos", metricas["ativos"])
    col4.metric("🔧 Manutenções/Mês", metricas["manut_mes"])
    
    st.markdown("---")
    
    # Gráfico principal - Disponibilidade por setor
    st.subheader("📊 Disponibilidade por Setor")
    dispo_setor = df_equip.groupby('setor')['status'].apply(
        lambda x: (x == 'Ativo').sum() / len(x) * 100
    ).reset_index()
    dispo_setor.columns = ['Setor', 'Disponibilidade (%)']
    
    fig_dispo = px.bar(dispo_setor, x='Setor', y='Disponibilidade (%)', 
                       title="Disponibilidade por Setor (%)",
                       color='Disponibilidade (%)', 
                       color_continuous_scale="RdYlGn",
                       range_color=[0, 100])
    fig_dispo.add_hline(y=75, line_dash="dash", line_color="red", 
                        annotation_text="Meta: 75%")
    st.plotly_chart(fig_dispo, use_container_width=True)
    
    # Gráficos complementares
    if not df_manut.empty:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Manutenções por tipo (últimos 6 meses)
            seis_meses = datetime.now() - timedelta(days=180)
            df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
            df_recente = df_manut[df_manut['data_inicio'] >= seis_meses]
            
            if not df_recente.empty:
                tipo_counts = df_recente['tipo'].value_counts()
                fig_tipos = px.pie(values=tipo_counts.values, names=tipo_counts.index, 
                                  title="Tipos de Manutenção (6 meses)")
                st.plotly_chart(fig_tipos, use_container_width=True)
        
        with col_g2:
            # Tendência mensal
            df_manut['mes'] = df_manut['data_inicio'].dt.to_period('M')
            manut_mensal = df_manut.groupby('mes').size().reset_index()
            manut_mensal.columns = ['Mês', 'Quantidade']
            manut_mensal['Mês'] = manut_mensal['Mês'].astype(str)
            
            if len(manut_mensal) > 1:
                fig_tendencia = px.line(manut_mensal.tail(12), x='Mês', y='Quantidade', 
                                       title="Tendência de Manutenções (12 meses)")
                st.plotly_chart(fig_tendencia, use_container_width=True)
    
    # Resumo por setor
    st.markdown("---")
    st.subheader("📋 Resumo por Setor")
    
    resumo_setor = df_equip.groupby('setor').agg({
        'id': 'count',
        'status': lambda x: (x == 'Ativo').sum()
    }).reset_index()
    resumo_setor.columns = ['Setor', 'Total', 'Ativos']
    resumo_setor['Disponibilidade (%)'] = (resumo_setor['Ativos'] / resumo_setor['Total'] * 100).round(1)
    resumo_setor['Em Manutenção'] = resumo_setor['Total'] - resumo_setor['Ativos']
    
    st.dataframe(resumo_setor, use_container_width=True, hide_index=True)

# -------------------
# Main
# -------------------
def main():
    main_login()
    
    supabase = init_supabase()
    if not supabase:
        st.error("❌ Erro de conexão com banco de dados. Verifique as configurações.")
        return
    
    # Sidebar e navegação
    pagina = show_sidebar()
    
    # Roteamento de páginas
    if pagina == "Início":
        pagina_inicial(supabase)
    elif pagina == "Equipamentos":
        pagina_equipamentos(supabase)
    elif pagina == "Manutenções":
        pagina_manutencoes(supabase)
    elif pagina == "Dashboard":
        pagina_dashboard(supabase)
    
    # Rodapé
    st.markdown("---")
    st.markdown(
        "**Sistema de Manutenção HSC** | "
        f"Usuário: {st.session_state.get('user', 'N/A').split('@')[0]} | "
        f"Sessão: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

if __name__ == "__main__":
    main()
