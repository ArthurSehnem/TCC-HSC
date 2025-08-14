import streamlit as st
import base64
from supabase import create_client
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List

# -------------------
# Configuração inicial
# -------------------
st.set_page_config(
    page_title="Sistema de Manutenção | HSC",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplicando CSS para cores de interação azul
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #1f77b4 !important;
        color: white !important;
    }
    div.stButton > button:hover {
        background-color: #155a8a !important;
    }
    /* Ajustes em selectbox, radio, checkboxes */
    .stSelectbox select, .stRadio input[type="radio"] + label, .stCheckbox input[type="checkbox"] + label {
        color: #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

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
    encoded_logo = load_logo()
    if encoded_logo:
        st.sidebar.markdown(
            f"<div style='text-align: center; margin-bottom: 20px;'><img src='data:image/png;base64,{encoded_logo}' width='120'></div>",
            unsafe_allow_html=True
        )
    st.sidebar.markdown("---")
    return st.sidebar.radio(
        "Navegação",
        ["Página Inicial", "Adicionar Equipamento", "Registrar Manutenção", "Dashboard"],
        index=0
    )

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

def clear_form_state():
    for key in ["nome", "setor", "numero_serie"]:
        if key in st.session_state:
            del st.session_state[key]

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
# Páginas
# -------------------
def pagina_inicial():
    st.title("Sistema de Manutenção | HSC")
    st.markdown("""
    ### Bem-vindo ao Sistema de Gestão de Manutenção
    Este sistema é fruto de uma **parceria entre o Hospital Santa Cruz (HSC) e a UNISC**.
    """)
    st.info("💡 Use a sidebar à esquerda para navegar entre as funcionalidades do sistema.")

def pagina_adicionar_equipamento(supabase):
    st.header("Adicionar Novo Equipamento")
    with st.expander("Instruções", expanded=False):
        st.markdown("""
        - Todos os campos são obrigatórios
        - Número de série deve ser único
        - Equipamentos criados com status 'Ativo' por padrão
        """)
    
    with st.form("form_equipamento", clear_on_submit=True):
        nome = st.text_input("Nome do equipamento *", placeholder="Ex: Respirador ABC-123")
        setor = st.text_input("Setor *", placeholder="Ex: UTI, Centro Cirúrgico")
        numero_serie = st.text_input("Número de Série *", placeholder="Ex: SN123456789")
        
        submitted = st.form_submit_button("Cadastrar Equipamento")
        if submitted:
            error = validate_equipment_data(nome, setor, numero_serie)
            if error:
                st.error(error)
            else:
                if insert_equipment(supabase, nome, setor, numero_serie):
                    st.success(f"✅ Equipamento '{nome}' cadastrado com sucesso!")
                    st.balloons()
                    st.cache_data.clear()
                else:
                    st.error("Erro ao cadastrar equipamento.")

def pagina_registrar_manutencao(supabase):
    st.header("Registrar Manutenção")
    tab1, tab2 = st.tabs(["Abrir Manutenção", "Finalizar Manutenção"])
    
    with tab1:
        st.subheader("Abrir nova manutenção")
        equipamentos_ativos = [e for e in fetch_equipamentos(supabase) if e['status'] == 'Ativo']
        if not equipamentos_ativos:
            st.warning("Nenhum equipamento ativo disponível.")
            return
        with st.form("form_abrir_manutencao"):
            equipamento_dict = {f"{e['nome']} - {e['setor']}": e['id'] for e in equipamentos_ativos}
            equipamento_selecionado = st.selectbox("Equipamento *", [""] + list(equipamento_dict.keys()))
            tipo = st.selectbox("Tipo de manutenção *", ["", "Preventiva", "Corretiva"])
            descricao = st.text_area("Descrição da manutenção *", height=100)
            submitted = st.form_submit_button("Abrir Manutenção")
            if submitted:
                if not equipamento_selecionado or not tipo or not descricao.strip():
                    st.error("Todos os campos são obrigatórios!")
                else:
                    equipamento_id = equipamento_dict[equipamento_selecionado]
                    if start_maintenance(supabase, equipamento_id, tipo, descricao):
                        st.success(f"Manutenção aberta com sucesso para {equipamento_selecionado}!")
                        st.rerun()
                    else:
                        st.error("Erro ao abrir manutenção.")
    
    with tab2:
        st.subheader("Finalizar manutenção em andamento")
        manutencoes_abertas = [m for m in fetch_manutencoes(supabase) if m['status'] == 'Em andamento']
        if not manutencoes_abertas:
            st.info("Não há manutenções em andamento no momento.")
            return
        equipamentos_data = fetch_equipamentos(supabase)
        with st.form("form_finalizar_manutencao"):
            manut_dict = {}
            for m in manutencoes_abertas:
                eq_nome = next((e['nome'] for e in equipamentos_data if e['id'] == m['equipamento_id']), "Desconhecido")
                manut_dict[f"{eq_nome} | {m['tipo']} | {m['descricao'][:50]}..."] = {'manut_id': m['id'], 'equip_id': m['equipamento_id']}
            manut_selecionada = st.selectbox("Manutenção em andamento *", [""] + list(manut_dict.keys()))
            submitted = st.form_submit_button("Finalizar Manutenção")
            if submitted:
                if not manut_selecionada:
                    st.error("Selecione uma manutenção para finalizar!")
                else:
                    manut_info = manut_dict[manut_selecionada]
                    if finish_maintenance(supabase, manut_info['manut_id'], manut_info['equip_id']):
                        st.success("Manutenção finalizada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao finalizar manutenção.")

def create_streamlit_charts(df_equip, df_manut):
    charts = {}
    if not df_equip.empty:
        charts['setor_data'] = df_equip['setor'].value_counts()
        charts['status_data'] = df_equip['status'].value_counts()
    if not df_manut.empty:
        charts['manut_status_data'] = df_manut['status'].value_counts()
        charts['manut_tipo_data'] = df_manut['tipo'].value_counts()
    return charts

def pagina_dashboard(supabase):
    """Dashboard completo com métricas e gráficos em coluna única."""
    st.header("Dashboard de Equipamentos e Manutenções")
    
    # Carrega dados
    equipamentos_data = supabase.table("equipamentos").select("*").execute().data
    manutencoes_data = supabase.table("manutencoes").select("*").execute().data

    if not equipamentos_data:
        st.warning("Nenhum equipamento encontrado. Cadastre equipamentos primeiro.")
        return

    # Transformar em DataFrame
    df_equip = pd.DataFrame(equipamentos_data)
    df_manut = pd.DataFrame(manutencoes_data) if manutencoes_data else pd.DataFrame()

    # --------------------------------------
    # 1 a 4: KPIs principais (cartões)
    # --------------------------------------
    st.subheader("Indicadores Principais - Equipamentos")
    
    total_equip = len(df_equip)
    ativos = len(df_equip[df_equip['status'] == 'Ativo'])
    em_manut = len(df_equip[df_equip['status'] == 'Em manutenção'])
    disponibilidade = (ativos / total_equip) * 100 if total_equip else 0

    # Cartões em linha
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Equipamentos", total_equip)
    col2.metric("Ativos", ativos, delta=f"{(ativos/total_equip)*100:.1f}%")
    col3.metric("Em Manutenção", em_manut, delta=f"{(em_manut/total_equip)*100:.1f}%")
    col4.metric("Disponibilidade (%)", f"{disponibilidade:.1f}%")

    st.markdown("---")
    
    # --------------------------------------
    # 5 a 8: KPIs de manutenção (cartões)
    # --------------------------------------
    st.subheader("Indicadores de Manutenção")
    
    if not df_manut.empty:
        total_manut = len(df_manut)
        em_andamento = len(df_manut[df_manut['status'] == 'Em andamento'])
        concluidas = len(df_manut[df_manut['status'] == 'Concluída'])
        taxa_conclusao = (concluidas / total_manut) * 100 if total_manut else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Manutenções", total_manut)
        col2.metric("Em Andamento", em_andamento)
        col3.metric("Concluídas", concluidas)
        col4.metric("Taxa de Conclusão (%)", f"{taxa_conclusao:.1f}%")
    else:
        st.info("Nenhuma manutenção registrada ainda.")
        total_manut = em_andamento = concluidas = taxa_conclusao = 0

    st.markdown("---")
    
    # --------------------------------------
    # 9: Tempo Médio para Reparo (corretivas concluídas)
    # --------------------------------------
    st.subheader("Tempo Médio para Reparo (Corretivas Concluídas)")
    if not df_manut.empty:
        df_corretivas = df_manut[(df_manut['tipo'] == 'Corretiva') & (df_manut['status'] == 'Concluída')].copy()
        if not df_corretivas.empty:
            df_corretivas['data_inicio'] = pd.to_datetime(df_corretivas['data_inicio'])
            df_corretivas['data_fim'] = pd.to_datetime(df_corretivas['data_fim'])
            df_corretivas['duracao'] = (df_corretivas['data_fim'] - df_corretivas['data_inicio']).dt.total_seconds() / 3600  # horas
            tempo_medio = df_corretivas['duracao'].mean()
            st.metric("Tempo Médio (horas)", f"{tempo_medio:.1f}")
        else:
            st.info("Não há manutenções corretivas concluídas.")
    else:
        st.info("Nenhuma manutenção registrada.")

    st.markdown("---")
    
    # --------------------------------------
    # 10: Taxa de Preventiva vs Corretiva
    # --------------------------------------
    st.subheader("Taxa de Manutenção Preventiva vs Corretiva")
    if not df_manut.empty:
        count_preventiva = len(df_manut[df_manut['tipo'] == 'Preventiva'])
        count_corretiva = len(df_manut[df_manut['tipo'] == 'Corretiva'])
        total_tipo = count_preventiva + count_corretiva
        taxa_preventiva = (count_preventiva / total_tipo) * 100 if total_tipo else 0
        taxa_corretiva = 100 - taxa_preventiva
        st.bar_chart(pd.DataFrame({
            "Tipo": ["Preventiva", "Corretiva"],
            "Percentual": [taxa_preventiva, taxa_corretiva]
        }).set_index("Tipo"))
    else:
        st.info("Nenhuma manutenção registrada.")

    st.markdown("---")
    
    # --------------------------------------
    # 11: Volume de Manutenções por Período (mensal)
    # --------------------------------------
    st.subheader("Volume de Manutenções por Mês")
    if not df_manut.empty:
        df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
        manut_por_mes = df_manut.groupby(df_manut['data_inicio'].dt.to_period('M')).size()
        st.bar_chart(manut_por_mes)
    else:
        st.info("Nenhuma manutenção registrada.")

    st.markdown("---")
    
    # --------------------------------------
    # 12: Disponibilidade por Setor
    # --------------------------------------
    st.subheader("Disponibilidade por Setor")
    setores = df_equip['setor'].unique()
    dispon_por_setor = {}
    for setor in setores:
        total_setor = len(df_equip[df_equip['setor'] == setor])
        ativos_setor = len(df_equip[(df_equip['setor'] == setor) & (df_equip['status'] == 'Ativo')])
        dispon_por_setor[setor] = (ativos_setor / total_setor) * 100 if total_setor else 0
    st.bar_chart(pd.Series(dispon_por_setor, name="Disponibilidade (%)"))

    st.markdown("---")
    
    # --------------------------------------
    # 13: Distribuição por Status
    # --------------------------------------
    st.subheader("Distribuição de Equipamentos por Status")
    st.bar_chart(df_equip['status'].value_counts())

    st.markdown("---")
    
    # --------------------------------------
    # 14: Manutenções por Tipo
    # --------------------------------------
    st.subheader("Manutenções por Tipo")
    if not df_manut.empty:
        st.bar_chart(df_manut['tipo'].value_counts())
# -------------------
# Main
# -------------------
def main():
    supabase = init_supabase()
    if not supabase:
        st.error("Erro de conexão com o banco de dados.")
        return
    pagina = show_sidebar()
    if pagina == "Página Inicial":
        pagina_inicial()
    elif pagina == "Adicionar Equipamento":
        pagina_adicionar_equipamento(supabase)
    elif pagina == "Registrar Manutenção":
        pagina_registrar_manutencao(supabase)
    elif pagina == "Dashboard":
        pagina_dashboard(supabase)

if __name__ == "__main__":
    main()
