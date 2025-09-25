import streamlit as st
import base64
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import re

# -------------------
# Configuração inicial
# -------------------
st.set_page_config(
    page_title="Sistema de Manutenção | HSC",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS simplificado
st.markdown("""
<style>
.header {background: linear-gradient(90deg, #1f4e79, #2d5aa0); padding: 1rem; border-radius: 10px; color: white; text-align: center;}
.metric-box {
    background: #f0f8ff; 
    padding: 1rem; 
    border-radius: 8px; 
    border-left: 4px solid #1f4e79; 
    margin: 0.5rem 0;
    height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
}
.metric-box h3 {margin: 0 0 0.5rem 0; font-size: 1rem;}
.metric-box h1 {margin: 0; font-size: 2rem;}
.alert-critical {background: #f8d7da; padding: 1rem; border-radius: 8px; border-left: 4px solid #dc3545; margin: 0.5rem 0;}
.alert-warning {background: #fff3cd; padding: 1rem; border-radius: 8px; border-left: 4px solid #ffc107; margin: 0.5rem 0;}
.alert-info {background: #d4edda; padding: 1rem; border-radius: 8px; border-left: 4px solid #28a745; margin: 0.5rem 0;}
</style>
""", unsafe_allow_html=True)

# Constantes
SETORES_PADRAO = ["Hemodiálise", "Lavanderia", "Instrumentais Cirúrgicos", "Emergência"]
TIPOS_MANUTENCAO = ["Preventiva", "Corretiva", "Urgente", "Calibração", "Higienização", "Inspeção"]
STATUS_EQUIPAMENTOS = ["Ativo", "Inativo", "Em manutenção", "Aguardando peças"]

# -------------------
# Sistema de Login Melhorado
# -------------------
ADMIN_EMAIL = st.secrets["login"]["email"]
ADMIN_PASSWORD = st.secrets["login"]["password"]

def login():
    st.markdown('<div class="header"><h1>Sistema HSC - Login</h1></div>', unsafe_allow_html=True)
    st.info("Acesso restrito aos profissionais autorizados do Hospital Santa Cruz.")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="seu.email@hsc.com.br")
        senha = st.text_input("Senha", type="password")
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Entrar", use_container_width=True)
        with col2:
            if st.form_submit_button("Esqueci a senha", use_container_width=True):
                st.info("Entre em contato com a TI do hospital.")
    
    if submitted:
        if not email or not senha:
            st.error("Preencha todos os campos.")
        elif email == ADMIN_EMAIL and senha == ADMIN_PASSWORD:
            st.success("Login realizado!")
            st.session_state["user"] = email
            st.session_state["login_time"] = datetime.now()
            st.balloons()
            st.rerun()
        else:
            st.error("Email ou senha incorretos.")

def check_session():
    if "user" in st.session_state and "login_time" in st.session_state:
        if datetime.now() - st.session_state["login_time"] > timedelta(hours=8):
            st.session_state.clear()
            st.warning("Sessão expirada. Faça login novamente.")
            st.rerun()
        return True
    return False

def main_login():
    if not check_session():
        login()
        st.stop()

def logout():
    st.session_state.clear()
    st.success("Logout realizado!")
    st.rerun()

# -------------------
# Inicialização (mantido original)
# -------------------
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["SUPABASE_URL"]
        key = st.secrets["supabase"]["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com o banco: {e}")
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
    encoded_logo = load_logo()
    if encoded_logo:
        st.sidebar.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{encoded_logo}' width='120'></div>", unsafe_allow_html=True)
    
    if "user" in st.session_state:
        st.sidebar.success(f"Bem-vindo: {st.session_state['user']}")
        if st.sidebar.button("Logout"):
            logout()
    
    st.sidebar.markdown("---")
    return st.sidebar.radio("Navegação", ["Início", "Equipamentos", "Manutenções", "Dashboard"])

# -------------------
# Funções de banco
# -------------------
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

def validate_equipment_data(nome: str, setor: str, numero_serie: str) -> Optional[str]:
    if not nome.strip(): return "❌ Nome obrigatório"
    if not setor.strip(): return "❌ Setor obrigatório"
    if not numero_serie.strip(): return "❌ Número de série obrigatório"
    if len(nome.strip()) < 3: return "❌ Nome muito curto"
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
        st.error(f"Erro ao cadastrar: {e}")
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
        st.error(f"Erro ao finalizar: {e}")
        return False

# -------------------
# Sistema de alertas inteligentes
# -------------------
def gerar_alertas(df_equip, df_manut):
    if df_equip.empty or df_manut.empty:
        return [], [], []
    
    df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
    alertas_criticos, alertas_importantes, alertas_info = [], [], []
    
    # Equipamentos com 4+ manutenções em 3 meses
    tres_meses = datetime.now() - timedelta(days=90)
    manut_3m = df_manut[df_manut['data_inicio'] >= tres_meses]
    problem_equip = manut_3m.groupby('equipamento_id').size()
    for eq_id, qtd in problem_equip.items():
        if qtd >= 4:
            eq_nome = df_equip[df_equip['id'] == eq_id]['nome'].values
            if len(eq_nome) > 0:
                alertas_criticos.append(f"CRÍTICO: {eq_nome[0]} teve {qtd} manutenções em 3 meses")
    
    # Manutenções urgentes recorrentes (2+ urgentes no mesmo equipamento)
    urgentes = df_manut[df_manut['tipo'] == 'Urgente']
    urgentes_por_equip = urgentes.groupby('equipamento_id').size()
    for eq_id, qtd in urgentes_por_equip.items():
        if qtd >= 2:
            eq_nome = df_equip[df_equip['id'] == eq_id]['nome'].values
            if len(eq_nome) > 0:
                alertas_criticos.append(f"CRÍTICO: {eq_nome[0]} teve {qtd} manutenções urgentes")
    
    # Manutenções longas (mais de 7 dias em andamento)
    em_andamento = df_manut[df_manut['status'] == 'Em andamento']
    for idx, row in em_andamento.iterrows():
        dias = (datetime.now() - row['data_inicio']).days
        if dias > 7:
            eq_nome = df_equip[df_equip['id'] == row['equipamento_id']]['nome'].values
            if len(eq_nome) > 0:
                alertas_criticos.append(f"CRÍTICO: {eq_nome[0]} em manutenção há {dias} dias")
    
    # Baixa disponibilidade por setor (<75%)
    dispo_setor = df_equip.groupby('setor')['status'].apply(lambda x: (x == 'Ativo').sum() / len(x) * 100)
    for setor, dispo in dispo_setor.items():
        if dispo < 75:
            alertas_importantes.append(f"IMPORTANTE: {setor} com {dispo:.1f}% de disponibilidade")
    
    # Padrão de falhas consecutivas (3+ do mesmo tipo)
    for eq_id, df_eq in df_manut.groupby('equipamento_id'):
        df_eq_sorted = df_eq.sort_values('data_inicio')
        tipos = df_eq_sorted['tipo'].tolist()
        count = 1
        for i in range(1, len(tipos)):
            if tipos[i] == tipos[i-1]:
                count += 1
                if count >= 3:
                    eq_nome = df_equip[df_equip['id'] == eq_id]['nome'].values
                    if len(eq_nome) > 0:
                        alertas_importantes.append(f"IMPORTANTE: {eq_nome[0]} com {count} manutenções consecutivas tipo '{tipos[i]}'")
                    break
            else:
                count = 1
    
    # 6. Sem manutenção preventiva em 6 meses
    seis_meses = datetime.now() - timedelta(days=180)
    preventivas_6m = df_manut[(df_manut['tipo'] == 'Preventiva') & (df_manut['data_inicio'] >= seis_meses)]['equipamento_id'].unique()
    sem_preventiva = df_equip[(~df_equip['id'].isin(preventivas_6m)) & (df_equip['status'] == 'Ativo')]
    for idx, row in sem_preventiva.head(5).iterrows():
        alertas_info.append(f"INFO: {row['nome']} sem manutenção preventiva há 6+ meses")
    
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
    st.markdown('<div class="header"><h1>Sistema de Manutenção HSC</h1></div>', unsafe_allow_html=True)
    
    df_equip = pd.DataFrame(fetch_equipamentos(supabase))
    df_manut = pd.DataFrame(fetch_manutencoes(supabase))
    
    if df_equip.empty:
        st.warning("Nenhum equipamento cadastrado. Comece adicionando equipamentos!")
        return
    
    # Métricas
    metricas = calcular_metricas(df_equip, df_manut)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f'<div class="metric-box"><h3>Total de Equipamentos</h3><h1>{metricas["total"]}</h1></div>', unsafe_allow_html=True)
    with col2:
        color = "#28a745" if metricas["disponibilidade"] >= 80 else "#ffc107" if metricas["disponibilidade"] >= 60 else "#dc3545"
        st.markdown(f'<div class="metric-box"><h3>Disponibilidade</h3><h1 style="color:{color}">{metricas["disponibilidade"]:.1f}%</h1></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><h3>Em Manutenção</h3><h1>{metricas["manutencao"]}</h1></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-box"><h3>Manutenções/Mês</h3><h1>{metricas["manut_mes"]}</h1></div>', unsafe_allow_html=True)
    
    # Alertas
    if not df_manut.empty:
        criticos, importantes, info = gerar_alertas(df_equip, df_manut)
        
        st.markdown("---")
        st.subheader("Alertas Inteligentes")
        
        if criticos:
            st.markdown("#### Críticos")
            for alerta in criticos:
                st.markdown(f'<div class="alert-critical">{alerta}</div>', unsafe_allow_html=True)
        
        if importantes:
            with st.expander("Importantes", expanded=not criticos):
                for alerta in importantes:
                    st.markdown(f'<div class="alert-warning">{alerta}</div>', unsafe_allow_html=True)
        
        if info:
            with st.expander("Informativos"):
                for alerta in info:
                    st.write(f"• {alerta}")
        
        if not any([criticos, importantes, info]):
            st.markdown('<div class="alert-info"><h3>Sistema Operacional</h3><p>Todos os equipamentos funcionando normalmente!</p></div>', unsafe_allow_html=True)

def pagina_equipamentos(supabase):
    st.header("⚙️ Gestão de Equipamentos")
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar", "📝 Gerenciar", "📊 Análise"])
    
    # Tab 1 - Cadastrar
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            setor = st.selectbox("🏢 Setor", SETORES_PADRAO + ["Outro"])
            if setor == "Outro":
                setor_custom = st.text_input("Nome do setor")
                setor = setor_custom.strip().title() if setor_custom.strip() else None
        
        with st.form("cadastro_equip", clear_on_submit=True):
            nome = st.text_input("📛 Nome do equipamento")
            numero_serie = st.text_input("🔢 Número de Série")
            submitted = st.form_submit_button("✅ Cadastrar")
        
        if submitted and setor:
            error = validate_equipment_data(nome, setor, numero_serie)
            if error:
                st.error(error)
            elif insert_equipment(supabase, nome, setor, numero_serie):
                st.success(f"✅ {nome} cadastrado!")
                st.balloons()
                st.cache_data.clear()
    
    # Tab 2 - Gerenciar
    with tab2:
        equipamentos = fetch_equipamentos(supabase)
        if equipamentos:
            # Busca
            busca = st.text_input("🔍 Buscar equipamento")
            if busca:
                equipamentos = [e for e in equipamentos if busca.lower() in e['nome'].lower() or busca.lower() in e['setor'].lower()]
            
            if equipamentos:
                equip_dict = {f"{e['nome']} | {e['setor']} | {e['status']}": e for e in equipamentos}
                selecionado = st.selectbox("Equipamento", list(equip_dict.keys()))
                
                if selecionado:
                    equip = equip_dict[selecionado]
                    novo_status = st.selectbox("Novo status", [s for s in STATUS_EQUIPAMENTOS if s != equip['status']])
                    if st.button(f"Alterar para {novo_status}"):
                        supabase.table("equipamentos").update({"status": novo_status}).eq("id", equip['id']).execute()
                        st.success(f"Status alterado!")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.info("Nenhum equipamento encontrado.")
    
    # Tab 3 - Análise
    with tab3:
        equipamentos = fetch_equipamentos(supabase)
        if equipamentos:
            df = pd.DataFrame(equipamentos)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", len(df))
            col2.metric("Ativos", len(df[df['status'] == 'Ativo']))
            col3.metric("Em Manutenção", len(df[df['status'] == 'Em manutenção']))
            
            # Gráficos
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                setor_counts = df['setor'].value_counts()
                fig = px.pie(values=setor_counts.values, names=setor_counts.index, title="Por Setor")
                st.plotly_chart(fig, use_container_width=True)
            
            with col_g2:
                status_counts = df['status'].value_counts()
                fig = px.bar(x=status_counts.index, y=status_counts.values, title="Por Status")
                st.plotly_chart(fig, use_container_width=True)
            
            # Tabela
            st.dataframe(df[['nome', 'setor', 'numero_serie', 'status']], use_container_width=True)
            
            # Export
            csv = df.to_csv(index=False)
            st.download_button("📥 Exportar CSV", csv, f"equipamentos_{datetime.now().strftime('%Y%m%d')}.csv")

def pagina_manutencoes(supabase):
    st.header("🔧 Gestão de Manutenções")
    tab1, tab2, tab3 = st.tabs(["🆕 Abrir", "✅ Finalizar", "📊 Análise"])
    
    # Tab 1 - Abrir
    with tab1:
        equipamentos_ativos = [e for e in fetch_equipamentos(supabase) if e['status'] == "Ativo"]
        if equipamentos_ativos:
            with st.form("abrir_manut", clear_on_submit=True):
                equip_dict = {f"{e['nome']} - {e['setor']}": e['id'] for e in equipamentos_ativos}
                equipamento = st.selectbox("⚙️ Equipamento", list(equip_dict.keys()))
                tipo = st.selectbox("🔧 Tipo", TIPOS_MANUTENCAO)
                descricao = st.text_area("📝 Descrição")
                submitted = st.form_submit_button("🔧 Abrir Manutenção")
                
                if submitted and equipamento and tipo and descricao.strip():
                    if start_maintenance(supabase, equip_dict[equipamento], tipo, descricao):
                        st.success("✅ Manutenção aberta!")
                        st.balloons()
                        st.cache_data.clear()
        else:
            st.warning("Nenhum equipamento ativo.")
    
    # Tab 2 - Finalizar
    with tab2:
        manutencoes_abertas = [m for m in fetch_manutencoes(supabase) if m['status'] == "Em andamento"]
        if manutencoes_abertas:
            equipamentos = fetch_equipamentos(supabase)
            manut_info = []
            for m in manutencoes_abertas:
                eq = next((e for e in equipamentos if e['id'] == m['equipamento_id']), None)
                if eq:
                    dias = (datetime.now() - pd.to_datetime(m['data_inicio'])).days
                    manut_info.append({
                        'display': f"{eq['nome']} | {m['tipo']} | {dias} dias",
                        'manut_id': m['id'],
                        'equip_id': m['equipamento_id']
                    })
            
            if manut_info:
                with st.form("finalizar_manut"):
                    manut_dict = {m['display']: m for m in manut_info}
                    selecionada = st.selectbox("🔧 Manutenção", list(manut_dict.keys()))
                    submitted = st.form_submit_button("✅ Finalizar")
                    
                    if submitted and selecionada:
                        info = manut_dict[selecionada]
                        if finish_maintenance(supabase, info['manut_id'], info['equip_id']):
                            st.success("✅ Manutenção finalizada!")
                            st.balloons()
                            st.cache_data.clear()
        else:
            st.info("Nenhuma manutenção em andamento.")
    
    # Tab 3 - Análise
    with tab3:
        manutencoes = fetch_manutencoes(supabase)
        if manutencoes:
            df = pd.DataFrame(manutencoes)
            equipamentos = fetch_equipamentos(supabase)
            
            # Adicionar nomes
            for idx, row in df.iterrows():
                eq = next((e for e in equipamentos if e['id'] == row['equipamento_id']), None)
                if eq:
                    df.at[idx, 'equipamento'] = eq['nome']
                    df.at[idx, 'setor'] = eq['setor']
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", len(df))
            col2.metric("Em Andamento", len(df[df['status'] == 'Em andamento']))
            col3.metric("Concluídas", len(df[df['status'] == 'Concluída']))
            
            # Gráficos
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                tipo_counts = df['tipo'].value_counts()
                fig = px.pie(values=tipo_counts.values, names=tipo_counts.index, title="Por Tipo")
                st.plotly_chart(fig, use_container_width=True)
            
            with col_g2:
                if 'setor' in df.columns:
                    setor_counts = df['setor'].value_counts()
                    fig = px.bar(x=setor_counts.index, y=setor_counts.values, title="Por Setor")
                    st.plotly_chart(fig, use_container_width=True)
            
            # Tabela
            colunas = ['equipamento', 'setor', 'tipo', 'status'] if 'equipamento' in df.columns else ['tipo', 'status']
            st.dataframe(df[colunas], use_container_width=True)

def pagina_dashboard(supabase):
    st.header("📊 Dashboard")
    df_equip = pd.DataFrame(fetch_equipamentos(supabase))
    df_manut = pd.DataFrame(fetch_manutencoes(supabase))
    
    if df_equip.empty:
        st.warning("Cadastre equipamentos primeiro.")
        return
    
    # Métricas principais
    metricas = calcular_metricas(df_equip, df_manut)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⚙️ Total", metricas['total'])
    col2.metric("📊 Disponibilidade", f"{metricas['disponibilidade']:.1f}%")
    col3.metric("✅ Ativos", metricas['ativos'])
    col4.metric("🔧 Em Manutenção", metricas['manutencao'])
    
    # Gráfico principal
    dispo_setor = df_equip.groupby('setor')['status'].apply(lambda x: (x == 'Ativo').sum() / len(x) * 100).reset_index()
    dispo_setor.columns = ['Setor', 'Disponibilidade (%)']
    
    fig = px.bar(dispo_setor, x='Setor', y='Disponibilidade (%)', 
                 title="📊 Disponibilidade por Setor",
                 color='Disponibilidade (%)', 
                 color_continuous_scale="RdYlGn")
    st.plotly_chart(fig, use_container_width=True)

def pagina_relatorios(supabase):
    st.header("📋 Relatórios")
    df_equip = pd.DataFrame(fetch_equipamentos(supabase))
    df_manut = pd.DataFrame(fetch_manutencoes(supabase))
    
    if df_equip.empty:
        st.warning("Nenhum dado para relatório.")
        return
    
    tab1, tab2 = st.tabs(["📊 Resumo", "📈 Análise Preditiva"])
    
    # Tab 1 - Resumo
    with tab1:
        # Período
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data início", datetime.now() - timedelta(days=30))
        with col2:
            data_fim = st.date_input("Data fim", datetime.now())
        
        if not df_manut.empty:
            df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
            df_periodo = df_manut[(df_manut['data_inicio'].dt.date >= data_inicio) & 
                                 (df_manut['data_inicio'].dt.date <= data_fim)]
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Manutenções", len(df_periodo))
            col2.metric("Urgentes", len(df_periodo[df_periodo['tipo'] == 'Urgente']))
            col3.metric("Preventivas", len(df_periodo[df_periodo['tipo'] == 'Preventiva']))
            
            # Insights
            st.subheader("💡 Insights")
            if len(df_periodo) > 0:
                preventivas_pct = len(df_periodo[df_periodo['tipo'] == 'Preventiva']) / len(df_periodo) * 100
                if preventivas_pct < 30:
                    st.warning("⚠️ Baixa taxa de manutenção preventiva.")
                else:
                    st.success("✅ Boa estratégia de manutenção preventiva.")
        else:
            st.info("Nenhuma manutenção no período.")
    
    # Tab 2 - Análise Preditiva
    with tab2:
        if not df_manut.empty:
            st.subheader("🔮 Equipamentos que Podem Precisar de Atenção")
            
            # Sem manutenção recente
            ultimo_mes = datetime.now() - timedelta(days=30)
            df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
            manut_recente = df_manut[df_manut['data_inicio'] >= ultimo_mes]['equipamento_id'].unique()
            sem_manut_recente = df_equip[(~df_equip['id'].isin(manut_recente)) & (df_equip['status'] == 'Ativo')]
            
            if not sem_manut_recente.empty:
                st.warning(f"⚠️ {len(sem_manut_recente)} equipamentos sem manutenção recente:")
                for idx, row in sem_manut_recente.head(10).iterrows():
                    st.write(f"• **{row['nome']}** ({row['setor']})")
            else:
                st.success("✅ Todos os equipamentos ativos tiveram manutenção recente.")
            
            # Recomendações
            st.subheader("💡 Recomendações")
            criticos, importantes, _ = gerar_alertas(df_equip, df_manut)
            
            if criticos:
                st.error("🚨 Focar em equipamentos críticos.")
            if len(sem_manut_recente) > 5:
                st.warning("🔧 Agendar manutenções preventivas.")
            if not criticos and len(sem_manut_recente) <= 5:
                st.success("✅ Sistema operando eficientemente!")
        else:
            st.info("Registre manutenções para análises preditivas.")

# -------------------
# Main
# -------------------
def main():
    main_login()
    
    supabase = init_supabase()
    if not supabase:
        st.error("❌ Erro de conexão com banco de dados.")
        return
    
    pagina = show_sidebar()
    
    if pagina == "Início":
        pagina_inicial(supabase)
    elif pagina == "Equipamentos":
        pagina_equipamentos(supabase)
    elif pagina == "Manutenções":
        pagina_manutencoes(supabase)
    elif pagina == "Dashboard":
        pagina_dashboard(supabase)
    elif pagina == "Relatórios":
        pagina_relatorios(supabase)

if __name__ == "__main__":
    main()
