import streamlit as st
import base64
from supabase import create_client
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List
import plotly.express as px
import plotly.graph_objects as go

import streamlit as st

# -------------------
# Login único
# -------------------
ADMIN_EMAIL = st.secrets["login"]["email"]
ADMIN_PASSWORD = st.secrets["login"]["password"]

def login():
    st.title("Login - Sistema HSC")
        
    # Texto explicativo
    st.info(
        """
        ⚠️ **Acesso restrito aos profissionais autorizados do Hospital Santa Cruz.**  
        Por favor, insira suas credenciais para continuar.
        """
    )

    # Formulário de login
    with st.form("login_form"):
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        if email == ADMIN_EMAIL and senha == ADMIN_PASSWORD:
            st.success("Login realizado com sucesso!")
            st.session_state["user"] = email
        else:
            st.error(
                "Email ou senha incorretos.\n"
                "Se você esqueceu a senha, contate o setor de TI do hospital."
            )

def main():
    if "user" not in st.session_state:
        login()
        st.stop()  # impede que o restante do app carregue

if __name__ == "__main__":
    main()

# -------------------
# Configuração inicial
# -------------------
st.set_page_config(
    page_title="Sistema de Manutenção | HSC",
    layout="wide",
    initial_sidebar_state="expanded"
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
    """Página inicial melhorada."""
    st.title("Sistema de Manutenção | HSC") 
    st.markdown("""
### Bem-vindo ao Sistema de Gestão de Manutenção

Este sistema é fruto de uma **parceria entre o Hospital Santa Cruz (HSC) e a UNISC**, desenvolvido para **apoiar o hospital na gestão e histórico das manutenções de equipamentos críticos**.

#### Funcionalidades Principais:
- **Dashboard Interativo**: Visualize status e métricas em tempo real
- **Gestão de Manutenções**: Registre e acompanhe todas as intervenções
- **Cadastro de Equipamentos**: Mantenha inventário atualizado
- **Relatórios Avançados**: Análises detalhadas para tomada de decisão

#### Nossos Objetivos:
Tornar a gestão de equipamentos **mais eficiente, segura e transparente** para todos os profissionais envolvidos.
""")

    st.info(""" 💡 **Dica de Navegação** Use a sidebar à esquerda para navegar entre as funcionalidades do sistema. Cada seção foi otimizada para facilitar seu trabalho diário.""")

def pagina_adicionar_equipamento(supabase):
    st.header("Adicionar Novo Equipamento")
    with st.expander("Instruções", expanded=False):
        st.markdown("""
        - Todos os campos são obrigatórios
        - Número de série deve ser único
        - Equipamentos criados com status 'Ativo' por padrão
        """)

    # Lista padrão de setores
    setores_padrao = ["Hemodiálise", "Lavanderia", "Instrumentais Cirúrgicos"]

    # Campo de seleção fora do form para reatividade
    setor_escolhido = st.selectbox(
        "Selecione o setor",
        setores_padrao + ["Outro"]
    )

    # Se escolher "Outro", mostrar campo de texto
    setor_final = setor_escolhido
    if setor_escolhido == "Outro":
        setor_custom = st.text_input("Digite o nome do setor")
        if setor_custom.strip():
            setor_final = setor_custom.strip().title()
        else:
            setor_final = None

    with st.form("form_equipamento", clear_on_submit=True):
        nome = st.text_input("Nome do equipamento *", placeholder="Ex: Respirador ABC-123")
        numero_serie = st.text_input("Número de Série *", placeholder="Ex: SN123456789")
        submitted = st.form_submit_button("Cadastrar Equipamento")

    if submitted:
        if not setor_final:
            st.error("Por favor, selecione ou informe um setor.")
        else:
            error = validate_equipment_data(nome, setor_final, numero_serie)
            if error:
                st.error(error)
            else:
                if insert_equipment(supabase, nome, setor_final, numero_serie):
                    st.success(f"Equipamento '{nome}' cadastrado com sucesso!")
                    st.balloons()
                    st.cache_data.clear()
                else:
                    st.error("Erro ao cadastrar equipamento.")

def pagina_registrar_manutencao(supabase):
    st.header("Registrar Manutenção")
    tab1, tab2 = st.tabs(["Abrir Manutenção", "Finalizar Manutenção"])
    
    # ------------------- Abrir nova manutenção -------------------
    with tab1:
        st.subheader("Abrir nova manutenção")
        equipamentos_ativos = [e for e in fetch_equipamentos(supabase) if e['status'] == 'Ativo']
        if not equipamentos_ativos:
            st.warning("Nenhum equipamento ativo disponível.")
        else:
            equipamento_dict = {f"{e['nome']} - {e['setor']}": e['id'] for e in equipamentos_ativos}
            
            # Explicação das categorias
            with st.expander("Instruções: Tipos de manutenção", expanded=True):
                st.markdown("""
- **Preventiva**: Manutenção programada antes de falhas, rotina planejada.  
- **Urgente / Emergencial**: Para falhas críticas que exigem ação imediata.  
- **Calibração**: Ajustes periódicos de precisão em equipamentos (ex.: balanças, monitores).  
- **Higienização / Sanitização**: Limpeza ou desinfecção obrigatória para prevenir contaminação.  
                """)
            
            with st.form("form_abrir_manutencao", clear_on_submit=True):
                equipamento_selecionado = st.selectbox(
                    "Equipamento *", [""] + list(equipamento_dict.keys()), key="equipamento_selecionado"
                )
                tipo = st.selectbox(
                    "Tipo de manutenção *",
                    ["", "Preventiva", "Urgente / Emergencial", "Calibração", "Higienização / Sanitização"],
                    key="tipo_manut"
                )
                descricao = st.text_area(
                    "Descrição da manutenção *", height=100, key="descricao_manut"
                )
                submitted = st.form_submit_button("Abrir Manutenção")
                
                if submitted:
                    if not equipamento_selecionado or not tipo or not descricao.strip():
                        st.error("Todos os campos são obrigatórios!")
                    else:
                        equipamento_id = equipamento_dict[equipamento_selecionado]
                        if start_maintenance(supabase, equipamento_id, tipo, descricao):
                            st.success(f"Manutenção aberta com sucesso para {equipamento_selecionado}!")
                            st.balloons()
                        else:
                            st.error("Erro ao abrir manutenção.")

    # ------------------- Finalizar manutenção em andamento -------------------
    with tab2:
        st.subheader("Finalizar manutenção em andamento")
        manutencoes_abertas = [m for m in fetch_manutencoes(supabase) if m['status'] == 'Em andamento']
        if not manutencoes_abertas:
            st.info("Não há manutenções em andamento no momento.")
        else:
            equipamentos_data = fetch_equipamentos(supabase)
            manut_dict = {}
            for m in manutencoes_abertas:
                eq_nome = next((e['nome'] for e in equipamentos_data if e['id'] == m['equipamento_id']), "Desconhecido")
                manut_dict[f"{eq_nome} | {m['tipo']} | {m['descricao'][:50]}..."] = {
                    'manut_id': m['id'],
                    'equip_id': m['equipamento_id']
                }

            with st.form("form_finalizar_manutencao", clear_on_submit=True):
                manut_selecionada = st.selectbox(
                    "Manutenção em andamento *", [""] + list(manut_dict.keys()), key="manut_selecionada"
                )
                submitted = st.form_submit_button("Finalizar Manutenção")
                
                if submitted:
                    if not manut_selecionada:
                        st.error("Selecione uma manutenção para finalizar!")
                    else:
                        manut_info = manut_dict[manut_selecionada]
                        if finish_maintenance(supabase, manut_info['manut_id'], manut_info['equip_id']):
                            st.success("Manutenção finalizada com sucesso!")
                            st.balloons()
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
    """Dashboard completo com métricas, gráficos e análises detalhadas."""
    st.header("Dashboard de Equipamentos e Manutenções")
    
    # Carregar dados
    equipamentos_data = supabase.table("equipamentos").select("*").execute().data
    manutencoes_data = supabase.table("manutencoes").select("*").execute().data

    if not equipamentos_data:
        st.warning("Nenhum equipamento encontrado. Cadastre equipamentos primeiro.")
        return

    df_equip = pd.DataFrame(equipamentos_data)
    df_manut = pd.DataFrame(manutencoes_data) if manutencoes_data else pd.DataFrame()

    # --------------------------------------
    # 1️⃣ KPIs principais - Equipamentos
    # --------------------------------------
    st.subheader("Indicadores Principais - Equipamentos")
    total_equip = len(df_equip)
    ativos = len(df_equip[df_equip['status'] == 'Ativo'])
    em_manut = len(df_equip[df_equip['status'] == 'Em manutenção'])
    disponibilidade = (ativos / total_equip) * 100 if total_equip else 0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Equipamentos", total_equip)
    col2.metric("Ativos", ativos)
    col3.metric("Em Manutenção", em_manut)
    col4.metric("Disponibilidade (%)", f"{disponibilidade:.1f}%")
    st.markdown("---")

    # --------------------------------------
    # 2️⃣ TMA - Tempo Médio de Atendimento em dias
    # --------------------------------------
    st.subheader("Tempo Médio de Atendimento (TMA) em dias")
    if not df_manut.empty:
        df_concluidas = df_manut[df_manut['status'] == 'Concluída'].copy()
        if not df_concluidas.empty:
            df_concluidas['data_inicio'] = pd.to_datetime(df_concluidas['data_inicio'])
            df_concluidas['data_fim'] = pd.to_datetime(df_concluidas['data_fim'])
            df_concluidas['duracao_dias'] = (df_concluidas['data_fim'] - df_concluidas['data_inicio']).dt.total_seconds() / 86400
            tma = df_concluidas['duracao_dias'].mean()
            st.metric("TMA (dias)", f"{tma:.1f}")
        else:
            st.info("Não há manutenções concluídas para calcular TMA.")
    else:
        st.info("Nenhuma manutenção registrada.")
    st.markdown("---")

    # --------------------------------------
    # 3️⃣ Quantidade de atendimentos por tipo
    # --------------------------------------
    st.subheader("Quantidade de Atendimentos por Tipo")
    if not df_manut.empty:
        df_tipo_count = df_manut['tipo'].value_counts().reset_index()
        df_tipo_count.columns = ['Tipo', 'Quantidade']
        fig_tipo = px.bar(df_tipo_count, x='Tipo', y='Quantidade', text='Quantidade',
                          color='Tipo', color_discrete_sequence=px.colors.qualitative.Set2)
        fig_tipo.update_yaxes(range=[0, max(df_tipo_count['Quantidade'].max()+5, 5)])
        st.plotly_chart(fig_tipo, use_container_width=True)
    else:
        st.info("Nenhuma manutenção registrada.")
    st.markdown("---")

    # --------------------------------------
    # 4️⃣ Disponibilidade por setor
    # --------------------------------------
    st.subheader("Disponibilidade por Setor")
    dispon_por_setor = {}
    for setor in df_equip['setor'].unique():
        total_setor = len(df_equip[df_equip['setor']==setor])
        ativos_setor = len(df_equip[(df_equip['setor']==setor) & (df_equip['status']=='Ativo')])
        dispon_por_setor[setor] = (ativos_setor/total_setor)*100 if total_setor else 0
    df_dispon = pd.DataFrame({"Setor": list(dispon_por_setor.keys()), "Disponibilidade": list(dispon_por_setor.values())})
    fig_dispon = px.bar(df_dispon, x='Setor', y='Disponibilidade', text='Disponibilidade',
                        labels={'Disponibilidade':'%'}, title="Disponibilidade por Setor")
    fig_dispon.update_yaxes(range=[0,100])
    st.plotly_chart(fig_dispon, use_container_width=True)
    st.markdown("---")

    # --------------------------------------
    # 5️⃣ Manutenções por mês (MoM)
    # --------------------------------------
    st.subheader("Manutenções por Mês (MoM)")
    if not df_manut.empty:
        df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
        df_manut['mes_ano'] = df_manut['data_inicio'].dt.to_period('M')

        # Converter Period para string YYYY-MM
        df_manut['mes_ano_str'] = df_manut['mes_ano'].astype(str)

        df_mes = df_manut.groupby(['mes_ano_str', 'tipo']).size().reset_index(name='Quantidade')
        fig_mom = px.bar(
        df_mes,
        x='mes_ano_str',
        y='Quantidade',
        color='tipo',
        barmode='group',
        labels={'mes_ano_str':'Mês/Ano', 'Quantidade':'Atendimentos', 'tipo':'Tipo'}
    )
        st.plotly_chart(fig_mom, use_container_width=True)
    else:
        st.info("Nenhuma manutenção registrada.")

    # --------------------------------------
    # 6️⃣ Analítico dos Equipamentos
    # --------------------------------------
    st.subheader("Analítico dos Equipamentos")
    st.dataframe(df_equip.sort_values(['status','setor','nome']), use_container_width=True)
    st.markdown("---")

    # --------------------------------------
    # 7️⃣ Analítico das Manutenções
    # --------------------------------------
    st.subheader("Analítico das Manutenções")
    if not df_manut.empty:
        df_manut_analiatico = df_manut.copy()
        df_manut_analitico['data_inicio'] = pd.to_datetime(df_manut_analitico['data_inicio'])
        df_manut_analitico['data_fim'] = pd.to_datetime(df_manut_analitico['data_fim'])
        df_manut_analitico['duracao_dias'] = ((df_manut_analitico['data_fim'] - df_manut_analitico['data_inicio']).dt.total_seconds()/86400).fillna(0)
        df_manut_analitico = df_manut_analitico.merge(df_equip[['id','nome','setor']], left_on='equipamento_id', right_on='id', how='left')
        df_manut_analitico = df_manut_analitico.rename(columns={'nome':'Equipamento','setor':'Setor'})
        st.dataframe(df_manut_analitico[['Equipamento','Setor','tipo','descricao','status','data_inicio','data_fim','duracao_dias']], use_container_width=True)
    else:
        st.info("Nenhuma manutenção registrada.")

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

