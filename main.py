import streamlit as st
import base64
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
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
TIPOS_MANUTENCAO = ["Preventiva", "Corretiva", "Urgente"]

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

@st.cache_data(ttl=600)  # 10 minutos (logo não muda)
def load_logo():
    try:
        with open("logo.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

# -------------------
# Funções de banco com cache
# -------------------
@st.cache_data(ttl=60, show_spinner=False)
def fetch_equipamentos_cached(_supabase) -> List[Dict]:
    """Cache de 1 minuto para equipamentos"""
    try:
        response = _supabase.table("equipamentos").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Erro ao carregar equipamentos: {e}")
        return []

@st.cache_data(ttl=60, show_spinner=False)
def fetch_manutencoes_cached(_supabase) -> List[Dict]:
    """Cache de 1 minuto para manutenções"""
    try:
        response = _supabase.table("manutencoes").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Erro ao carregar manutenções: {e}")
        return []

def clear_cache():
    """Limpa todos os caches de dados"""
    fetch_equipamentos_cached.clear()
    fetch_manutencoes_cached.clear()

# -------------------
# Funções auxiliares otimizadas
# -------------------
def preparar_dataframes(supabase) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Carrega e prepara DataFrames com conversões de tipo otimizadas"""
    df_equip = pd.DataFrame(fetch_equipamentos_cached(supabase))
    df_manut = pd.DataFrame(fetch_manutencoes_cached(supabase))
    
    # Converter datas uma única vez
    if not df_manut.empty and 'data_inicio' in df_manut.columns:
        df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'], errors='coerce')
        if 'data_fim' in df_manut.columns:
            df_manut['data_fim'] = pd.to_datetime(df_manut['data_fim'], errors='coerce')
    
    return df_equip, df_manut

def adicionar_info_equipamentos(df_manut: pd.DataFrame, df_equip: pd.DataFrame) -> pd.DataFrame:
    """Adiciona informações de equipamentos usando merge (vetorizado)"""
    if df_manut.empty or df_equip.empty:
        return df_manut
    
    return df_manut.merge(
        df_equip[['id', 'nome', 'setor']], 
        left_on='equipamento_id', 
        right_on='id', 
        how='left',
        suffixes=('', '_equip')
    ).rename(columns={'nome': 'equipamento'}).drop(columns=['id_equip'], errors='ignore')

def calcular_tempo_parada_vetorizado(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula tempo de parada usando operações vetorizadas do Pandas"""
    if df.empty:
        return df
    
    # Garantir que datas estão no formato correto
    df['data_inicio'] = pd.to_datetime(df['data_inicio'], errors='coerce')
    df['data_fim'] = pd.to_datetime(df['data_fim'], errors='coerce')
    
    # Usar data_fim se existe, senão usar now()
    df['data_fim_calc'] = df['data_fim'].fillna(pd.Timestamp.now())
    
    # Calcular delta
    delta = df['data_fim_calc'] - df['data_inicio']
    
    # Extrair componentes (vetorizado)
    df['tempo_parada_horas'] = delta.dt.total_seconds() / 3600
    
    # Formatar string de tempo
    dias = delta.dt.days
    segundos_restantes = delta.dt.seconds
    horas = segundos_restantes // 3600
    minutos = (segundos_restantes % 3600) // 60
    
    # Criar strings formatadas condicionalmente
    def formatar_tempo(d, h, m):
        if d > 0:
            return f"{d}d {h}h {m}min"
        elif h > 0:
            return f"{h}h {m}min"
        else:
            return f"{m}min"
    
    df['tempo_parada'] = [formatar_tempo(d, h, m) for d, h, m in zip(dias, horas, minutos)]
    
    # Limpar coluna temporária
    df.drop(columns=['data_fim_calc'], inplace=True, errors='ignore')
    
    return df

# -------------------
# Sidebar
# -------------------
def show_sidebar():
    encoded_logo = load_logo()
    if encoded_logo:
        st.sidebar.markdown(
            f"""
            <div style="text-align: center;">
                <img src="data:image/png;base64,{encoded_logo}" width="120">
            </div>
            """,
            unsafe_allow_html=True
        )
        
    st.sidebar.markdown("---")
    
    # Menu principal
    menu = st.sidebar.radio(
        "Menu Principal", 
        ["🏠 Início", "⚙️ Equipamentos", "🔧 Manutenções", "📊 Dashboard"],
        index=0
    )
    
    return menu.split(" ", 1)[1]  # Remove emoji do retorno

# -------------------
# Funções de validação e banco
# -------------------
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
        st.error(f"❌ Erro ao abrir manutenção: {e}")
        return False

def finish_maintenance(supabase, manut_id: int, equipamento_id: int, resolucao: str) -> bool:
    try:
        manut_response = supabase.table("manutencoes").update({
            "data_fim": datetime.now().isoformat(),
            "status": "Concluída",
            "resolucao": resolucao.strip()
        }).eq("id", manut_id).execute()
        
        if manut_response.data:
            supabase.table("equipamentos").update({"status": "Ativo"}).eq("id", equipamento_id).execute()
            return True
        return False
    except Exception as e:
        st.error(f"❌ Erro ao finalizar manutenção: {e}")
        return False

# -------------------
# Sistema de alertas otimizado
# -------------------
def gerar_alertas(df_equip: pd.DataFrame, df_manut: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    if df_equip.empty or df_manut.empty:
        return [], [], []
    
    alertas_criticos, alertas_importantes, alertas_info = [], [], []
    
    # 1. Equipamentos com muitas manutenções (4+ em 3 meses) - vetorizado
    tres_meses = datetime.now() - timedelta(days=90)
    manut_3m = df_manut[df_manut['data_inicio'] >= tres_meses]
    problem_equip = manut_3m.groupby('equipamento_id').size()
    
    # Criar lookup dict para nomes (mais rápido que .values)
    equip_dict = df_equip.set_index('id')['nome'].to_dict()
    
    for eq_id, qtd in problem_equip.items():
        if qtd >= 4 and eq_id in equip_dict:
            alertas_criticos.append(f"🚨 **{equip_dict[eq_id]}** teve {qtd} manutenções em 3 meses")
    
    # 2. Manutenções urgentes recorrentes
    urgentes_por_equip = df_manut[df_manut['tipo'] == 'Urgente'].groupby('equipamento_id').size()
    for eq_id, qtd in urgentes_por_equip.items():
        if qtd >= 2 and eq_id in equip_dict:
            alertas_criticos.append(f"🚨 **{equip_dict[eq_id]}** teve {qtd} manutenções urgentes")
    
    # 3. Manutenções longas (mais de 7 dias)
    em_andamento = df_manut[df_manut['status'] == 'Em andamento'].copy()
    if not em_andamento.empty:
        em_andamento['dias'] = (datetime.now() - em_andamento['data_inicio']).dt.days
        longas = em_andamento[em_andamento['dias'] > 7]
        for _, row in longas.iterrows():
            if row['equipamento_id'] in equip_dict:
                alertas_criticos.append(f"🚨 **{equip_dict[row['equipamento_id']]}** em manutenção há {row['dias']} dias")
    
    # 4. Baixa disponibilidade por setor
    dispo_setor = df_equip.groupby('setor')['status'].apply(lambda x: (x == 'Ativo').sum() / len(x) * 100)
    for setor, dispo in dispo_setor.items():
        if dispo < 75:
            alertas_importantes.append(f"⚠️ **{setor}**: {dispo:.1f}% de disponibilidade")
    
    # 5. Sem manutenção preventiva há muito tempo
    seis_meses = datetime.now() - timedelta(days=180)
    preventivas_6m = df_manut[(df_manut['tipo'] == 'Preventiva') & (df_manut['data_inicio'] >= seis_meses)]['equipamento_id'].unique()
    sem_preventiva = df_equip[(~df_equip['id'].isin(preventivas_6m)) & (df_equip['status'] == 'Ativo')]
    for _, row in sem_preventiva.head(5).iterrows():
        alertas_info.append(f"💡 **{row['nome']}** sem manutenção preventiva há 6+ meses")
    
    return alertas_criticos, alertas_importantes, alertas_info

def calcular_metricas(df_equip: pd.DataFrame, df_manut: pd.DataFrame) -> Dict:
    if df_equip.empty:
        return {}
    
    total = len(df_equip)
    ativos = (df_equip['status'] == 'Ativo').sum()
    manutencao = (df_equip['status'] == 'Em manutenção').sum()
    disponibilidade = (ativos / total * 100) if total > 0 else 0
    
    # Manutenções último mês
    if not df_manut.empty:
        ultimo_mes = datetime.now() - timedelta(days=30)
        manut_mes = (df_manut['data_inicio'] >= ultimo_mes).sum()
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
    
    df_equip, df_manut = preparar_dataframes(supabase)
    
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
        
        if criticos:
            st.error("**CRÍTICOS - Ação Imediata Necessária:**")
            for alerta in criticos:
                st.write(f"• {alerta}")
        
        if importantes:
            with st.expander("⚠️ **Alertas Importantes**", expanded=not criticos):
                for alerta in importantes:
                    st.write(f"• {alerta}")
        
        if info:
            with st.expander("💡 **Alertas Informativos**"):
                for alerta in info:
                    st.write(f"• {alerta}")
        
        if not any([criticos, importantes, info]):
            st.success("🎉 **Sistema Operacional** - Todos os equipamentos funcionando normalmente!")

def pagina_equipamentos(supabase):
    st.title("Gestão de Equipamentos")
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Novo", "📝 Gerenciar Existentes", "📊 Relatórios"])
    
    # Tab 1 - Cadastrar
    with tab1:
        st.subheader("Cadastrar Novo Equipamento")
        
        with st.form("cadastro_equip", clear_on_submit=True):
            nome = st.text_input("Nome do Equipamento")
            setor = st.selectbox("Setor", SETORES_PADRAO + ["Outro"])
            numero_serie = st.text_input("Número de Série")
    
            if setor == "Outro":
                setor_custom = st.text_input("Nome do Setor")
                setor = setor_custom.strip().title() if setor_custom.strip() else setor
    
            submitted = st.form_submit_button("✅ Cadastrar")
    
            if submitted:
                error = validate_equipment_data(nome, setor, numero_serie)
                if error:
                    st.error(error)
                else:
                    if insert_equipment(supabase, nome, setor, numero_serie):
                        st.success(f"✅ **{nome}** cadastrado com sucesso!")
                        st.balloons()
                        clear_cache()
                        st.rerun()
    
    # Tab 2 - Gerenciar
    with tab2:
        st.subheader("Gerenciar Equipamentos Existentes")

        equipamentos = fetch_equipamentos_cached(supabase)
        if equipamentos:
            busca = st.text_input("🔍 Buscar equipamento", placeholder="Digite nome ou setor...")

            if busca:
                equipamentos = [e for e in equipamentos if 
                               busca.lower() in e['nome'].lower() or 
                               busca.lower() in e['setor'].lower() or 
                               busca.lower() in e['numero_serie'].lower()]

            if equipamentos:
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
                        if equip['status'] != 'Inativo':
                            if st.button("🔄 Marcar como Inativo", use_container_width=True):
                                try:
                                    supabase.table("equipamentos").update({"status": "Inativo"}).eq("id", equip['id']).execute()
                                    st.success("✅ Status alterado para **Inativo**!")
                                    clear_cache()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao alterar status: {e}")
                        else:
                            st.info("⚠️ Este equipamento já está inativo.")

    # Tab 3 - Relatórios
    with tab3:
        st.subheader("Relatórios de Equipamentos")
        
        df_equip, _ = preparar_dataframes(supabase)
        if not df_equip.empty:
            # Métricas
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", len(df_equip))
            col2.metric("Ativos", (df_equip['status'] == 'Ativo').sum())
            col3.metric("Em Manutenção", (df_equip['status'] == 'Em manutenção').sum())
            
            # Gráficos
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                setor_counts = df_equip['setor'].value_counts().reset_index()
                setor_counts.columns = ['Setor', 'Quantidade']
                fig1 = px.bar(setor_counts, x='Setor', y='Quantidade', 
                              title="Equipamentos por Setor")
                st.plotly_chart(fig1, use_container_width=True)
            
            with col_g2:
                status_counts = df_equip['status'].value_counts().reset_index()
                status_counts.columns = ['Status', 'Quantidade']
                fig2 = px.bar(status_counts, x='Status', y='Quantidade', 
                              title="Equipamentos por Status")
                st.plotly_chart(fig2, use_container_width=True)
            
            # Tabela
            st.subheader("Lista Completa")
            st.dataframe(df_equip[['nome', 'setor', 'numero_serie', 'status']], use_container_width=True, hide_index=True)
            
            # Export
            csv = df_equip.to_csv(index=False)
            st.download_button("📥 Baixar Relatório CSV", csv, 
                             f"equipamentos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                             use_container_width=True)

def pagina_manutencoes(supabase):
    st.title("Gestão de Manutenções")
    
    tab1, tab2, tab3 = st.tabs(["🆕 Abrir Manutenção", "✅ Finalizar Manutenção", "📊 Relatórios"])
    
    # Tab 1 - Abrir
    with tab1:
        st.subheader("Abrir Nova Manutenção")
        
        equipamentos_ativos = [e for e in fetch_equipamentos_cached(supabase) if e['status'] == "Ativo"]
        
        if equipamentos_ativos:
            with st.form("abrir_manut", clear_on_submit=True):
                equip_options = [f"{e['nome']} - {e['setor']}" for e in equipamentos_ativos]
                equip_dict = {opt: equipamentos_ativos[i]['id'] for i, opt in enumerate(equip_options)}
                equipamento = st.selectbox("Selecionar Equipamento:", equip_options)
                tipo = st.selectbox("Tipo de Manutenção:", TIPOS_MANUTENCAO)
                descricao = st.text_area("Descrição do Problema:", 
                                           placeholder="Descreva o problema ou serviço necessário...",
                                           height=100)
                
                submitted = st.form_submit_button("🔧 Abrir Manutenção", use_container_width=True)
                
                if submitted and equipamento and tipo and descricao.strip():
                    if start_maintenance(supabase, equip_dict[equipamento], tipo, descricao):
                        st.success(f"✅ Manutenção **{tipo}** aberta para **{equipamento.split(' - ')[0]}**!")
                        st.balloons()
                        clear_cache()
                        st.rerun()
                elif submitted:
                    st.error("❌ Preencha todos os campos obrigatórios.")
        else:
            st.warning("⚠️ Nenhum equipamento ativo disponível para manutenção.")
    
    # Tab 2 - Finalizar
    with tab2:
        st.subheader("Finalizar Manutenções em Andamento")
        
        df_equip, df_manut = preparar_dataframes(supabase)
        manutencoes_abertas = df_manut[df_manut['status'] == "Em andamento"]
        
        if not manutencoes_abertas.empty:
            # Adicionar info de equipamentos
            manut_com_equip = adicionar_info_equipamentos(manutencoes_abertas, df_equip)
            
            # Calcular dias decorridos
            manut_com_equip['dias'] = (datetime.now() - manut_com_equip['data_inicio']).dt.days
            manut_com_equip['status_icon'] = manut_com_equip['dias'].apply(lambda x: "🚨" if x > 7 else "🔧")
            
            # Criar opções para selectbox
            manut_com_equip['display'] = manut_com_equip.apply(
                lambda row: f"{row['status_icon']} {row['equipamento']} | {row['tipo']} | {row['dias']} dias", 
                axis=1
            )
            
            manut_dict = manut_com_equip.set_index('display').to_dict('index')
            selecionada = st.selectbox("🔧 Selecionar Manutenção:", list(manut_dict.keys()))
            
            if selecionada:
                info = manut_dict[selecionada]
                
                # Calcular tempo decorrido usando função vetorizada
                df_temp = pd.DataFrame([info])
                df_temp = calcular_tempo_parada_vetorizado(df_temp)
                tempo_parada = df_temp['tempo_parada'].iloc[0]
                
                data_inicio_fmt = pd.to_datetime(info['data_inicio']).strftime('%d/%m/%Y %H:%M')
                
                # Exibir informações
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.info(f"**Equipamento:** {info['equipamento']}\n\n"
                           f"**Tipo:** {info['tipo']}\n\n"
                           f"**Data Abertura:** {data_inicio_fmt}")
                
                with col_info2:
                    tempo_class = "🚨" if info['dias'] > 7 else "⏱️"
                    st.warning(f"{tempo_class} **Tempo de Parada**\n\n"
                              f"# {tempo_parada}")
                
                st.info(f"**Problema Relatado:** {info.get('descricao', 'Sem descrição')}")
                
                st.markdown("---")
                st.markdown("### 📝 Descreva o Reparo Realizado")
                
                resolucao = st.text_area(
                    "O que foi feito para resolver o problema?",
                    placeholder="Ex: Substituída peça X, realizado ajuste Y, testado e aprovado funcionando...",
                    height=150,
                    key=f"resolucao_{info['id']}",
                    help="Descreva detalhadamente os procedimentos realizados"
                )
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    if st.button("✅ Finalizar Manutenção", type="primary", use_container_width=True, key=f"btn_finalizar_{info['id']}"):
                        if resolucao and resolucao.strip():
                            if finish_maintenance(supabase, info['id'], info['equipamento_id'], resolucao):
                                st.success(f"✅ Manutenção de **{info['equipamento']}** finalizada com sucesso!")
                                st.balloons()
                                clear_cache()
                                st.rerun()
                        else:
                            st.error("❌ Por favor, descreva o que foi realizado antes de finalizar.")
        else:
            st.info("ℹ️ Nenhuma manutenção em andamento no momento.")
    
    # Tab 3 - Relatórios
    with tab3:
        st.subheader("Relatórios de Manutenções")
        
        df_equip, df_manut = preparar_dataframes(supabase)
        
        if not df_manut.empty:
            # Adicionar informações de equipamentos (vetorizado)
            df_completo = adicionar_info_equipamentos(df_manut, df_equip)
            
            # Calcular tempo de parada (vetorizado)
            df_completo = calcular_tempo_parada_vetorizado(df_completo)
            
            # Métricas
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", len(df_completo))
            col2.metric("Em Andamento", (df_completo['status'] == 'Em andamento').sum())
            col3.metric("Concluídas", (df_completo['status'] == 'Concluída').sum())
            
            # Gráficos
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                tipo_counts = df_completo['tipo'].value_counts().reset_index()
                tipo_counts.columns = ['Tipo', 'Quantidade']
                fig1 = px.bar(tipo_counts, x='Tipo', y='Quantidade', 
                              title="Manutenções por Tipo")
                st.plotly_chart(fig1, use_container_width=True)

            with col_g2:
                if 'setor' in df_completo.columns:
                    setor_counts = df_completo['setor'].value_counts().reset_index()
                    setor_counts.columns = ['Setor', 'Quantidade']
                    fig2 = px.bar(setor_counts, x='Setor', y='Quantidade', 
                                  title="Manutenções por Setor")
                    st.plotly_chart(fig2, use_container_width=True)
            
            # Tabela detalhada
            st.subheader("📋 Histórico Completo de Manutenções")

            # Preparar DataFrame para exibição
            df_display = df_completo.copy()

            # Formatar datas
            df_display['data_inicio'] = df_display['data_inicio'].dt.strftime('%d/%m/%Y %H:%M')
            df_display['data_fim'] = df_display['data_fim'].dt.strftime('%d/%m/%Y %H:%M')

            # Selecionar e renomear colunas
            colunas_exibir = ['equipamento', 'setor', 'tipo', 'status', 'data_inicio', 'data_fim', 'tempo_parada', 'descricao']
            if 'resolucao' in df_display.columns:
                colunas_exibir.append('resolucao')

            rename_dict = {
                'equipamento': 'Equipamento',
                'setor': 'Setor',
                'tipo': 'Tipo',
                'status': 'Status',
                'data_inicio': 'Data Início',
                'data_fim': 'Data Conclusão',
                'tempo_parada': 'Tempo de Parada',
                'descricao': 'Problema Relatado',
                'resolucao': 'Solução Aplicada'
            }

            df_display_final = df_display[colunas_exibir].copy()
            df_display_final = df_display_final.rename(columns=rename_dict)

            # Preencher valores vazios
            df_display_final['Data Conclusão'] = df_display_final['Data Conclusão'].fillna('(Em andamento)')
            if 'Solução Aplicada' in df_display_final.columns:
                df_display_final['Solução Aplicada'] = df_display_final['Solução Aplicada'].fillna('(Em andamento)')

            # Métricas de tempo
            col_m1, col_m2, col_m3 = st.columns(3)
            concluidas = df_display[df_display['status'] == 'Concluída']
            if not concluidas.empty:
                tempo_medio = concluidas['tempo_parada_horas'].mean()
                tempo_max = concluidas['tempo_parada_horas'].max()
                total_horas = concluidas['tempo_parada_horas'].sum()
                col_m1.metric("⏱️ Tempo Médio de Parada", f"{tempo_medio:.1f}h")
                col_m2.metric("⏱️ Maior Tempo de Parada", f"{tempo_max:.1f}h")
                col_m3.metric("📊 Total de Horas Paradas", f"{total_horas:.1f}h")

            st.dataframe(df_display_final, use_container_width=True, hide_index=True)
            
            # Export
            csv = df_display_final.to_csv(index=False)
            st.download_button("📥 Baixar Relatório Completo CSV", csv, 
                             f"manutencoes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                             use_container_width=True)
        else:
            st.warning("⚠️ Nenhuma manutenção registrada.")

def pagina_dashboard(supabase):
    st.title("Dashboard Executivo")
    
    df_equip, df_manut = preparar_dataframes(supabase)
    
    if df_equip.empty:
        st.warning("⚠️ Cadastre equipamentos primeiro para visualizar o dashboard.")
        return
    
    # Métricas principais
    metricas = calcular_metricas(df_equip, df_manut)
    
    st.subheader("📈 Métricas Principais")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Total de Equipamentos", metricas["total"])
    col2.metric("Disponibilidade Geral", f"{metricas['disponibilidade']:.1f}%", 
                delta=f"{metricas['disponibilidade']-75:.1f}%" if metricas['disponibilidade'] != 75 else None)
    col3.metric("Equipamentos Ativos", metricas["ativos"])
    col4.metric("Manutenções/Mês", metricas["manut_mes"])
    
    st.markdown("---")
    
    # Gráfico principal - Disponibilidade por setor
    dispo_setor = df_equip.groupby('setor')['status'].apply(
        lambda x: (x == 'Ativo').sum() / len(x) * 100
    ).reset_index()
    dispo_setor.columns = ['Setor', 'Disponibilidade (%)']
    
    fig_dispo = px.bar(dispo_setor, x='Setor', y='Disponibilidade (%)', 
                       title="Disponibilidade por Setor (%)",
                       color='Disponibilidade (%)',
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
            df_recente = df_manut[df_manut['data_inicio'] >= seis_meses]
            
            if not df_recente.empty:
                tipo_counts = df_recente['tipo'].value_counts().reset_index()
                tipo_counts.columns = ['Tipo', 'Quantidade']
                fig_tipos = px.bar(tipo_counts, x='Tipo', y='Quantidade', 
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

    # Análise de tempo de parada
    if not df_manut.empty:
        st.markdown("---")
        st.subheader("⏱️ Análise de Tempo de Parada")
        
        # Calcular tempos de parada (vetorizado)
        df_manut_completo = calcular_tempo_parada_vetorizado(df_manut.copy())
        
        # Apenas manutenções concluídas
        df_concluidas = df_manut_completo[df_manut_completo['status'] == 'Concluída'].copy()
        
        if not df_concluidas.empty:
            # Adicionar informações de equipamentos (vetorizado)
            df_concluidas = adicionar_info_equipamentos(df_concluidas, df_equip)
            
            col_t1, col_t2 = st.columns(2)
            
            with col_t1:
            # Tempo médio por tipo de manutenção 
                tempo_por_tipo = df_concluidas.groupby('tipo')['tempo_parada_horas'].mean().reset_index() 
                tempo_por_tipo.columns = ['Tipo', 'Tempo Médio (horas)'] 
                tempo_por_tipo['Tempo Médio (horas)'] = tempo_por_tipo['Tempo Médio (horas)'].round(1) 
            
                fig_tempo_tipo = px.bar(tempo_por_tipo, x='Tipo', y='Tempo Médio (horas)', 
                title="Tempo Médio de Parada por Tipo", 
                color='Tempo Médio (horas)') 
            
                st.plotly_chart(fig_tempo_tipo, use_container_width=True)
            
            with col_t2:
                # Tempo médio por setor
                if 'setor' in df_concluidas.columns:
                    tempo_por_setor = df_concluidas.groupby('setor')['tempo_parada_horas'].mean().reset_index()
                    tempo_por_setor.columns = ['Setor', 'Tempo Médio (horas)']
                    tempo_por_setor['Tempo Médio (horas)'] = tempo_por_setor['Tempo Médio (horas)'].round(1)
                    
                    fig_tempo_setor = px.bar(tempo_por_setor, x='Setor', y='Tempo Médio (horas)',
                                            title="Tempo Médio de Parada por Setor",
                                            color='Tempo Médio (horas)')
                    st.plotly_chart(fig_tempo_setor, use_container_width=True)
            
            # Top 5 equipamentos com maior tempo de parada total
            st.subheader("🔴 Equipamentos com Maior Tempo de Parada (Total)")
            tempo_por_equip = df_concluidas.groupby('equipamento')['tempo_parada_horas'].sum().reset_index()
            tempo_por_equip.columns = ['Equipamento', 'Tempo Total (horas)']
            tempo_por_equip = tempo_por_equip.sort_values('Tempo Total (horas)', ascending=False).head(5)
            tempo_por_equip['Tempo Total (horas)'] = tempo_por_equip['Tempo Total (horas)'].round(1)
            
            fig_top_parada = px.bar(tempo_por_equip, x='Equipamento', y='Tempo Total (horas)',
                                   title="Top 5 Equipamentos - Maior Tempo Parado",
                                   color='Tempo Total (horas)')
            st.plotly_chart(fig_top_parada, use_container_width=True)

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
