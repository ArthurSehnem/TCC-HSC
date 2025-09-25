import streamlit as st
import base64
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

import plotly.express as px

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
    try:
        return st.secrets["login"]["email"], st.secrets["login"]["password"]
    except:
        return "admin@hsc.com", "admin123"

def login():
    st.title("🏥 Login - Sistema HSC")
    st.info("⚠️ **Acesso restrito aos profissionais autorizados do Hospital Santa Cruz.**\nPor favor, insira suas credenciais para continuar.")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="seu.email@hsc.com")
        senha = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar", use_container_width=True)

    if submitted:
        admin_email, admin_password = get_credentials()
        if email == admin_email and senha == admin_password:
            st.session_state["user"] = email
            st.success("Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("Email ou senha incorretos. Se esqueceu a senha, contate o setor de TI do hospital.")

# -------------------
# Inicialização do Supabase
# -------------------
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

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
                f"<div style='text-align:center;margin-bottom:20px;'><img src='data:image/png;base64,{encoded_logo}' width='120'></div>",
                unsafe_allow_html=True
            )
        st.markdown("---")
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

@st.cache_data(ttl=60)
def fetch_equipamentos():
    response = supabase.table("equipamentos").select("*").execute()
    return response.data if response.data else []

@st.cache_data(ttl=60)
def fetch_manutencoes():
    response = supabase.table("manutencoes").select("*").execute()
    return response.data if response.data else []

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

def insert_equipment(nome: str, setor: str, numero_serie: str) -> bool:
    try:
        response = supabase.table("equipamentos").insert({
            "nome": nome.strip(),
            "setor": setor.strip(),
            "numero_serie": numero_serie.strip(),
            "status": "Ativo"
        }).execute()
        st.cache_data.clear()
        return bool(response.data)
    except Exception as e:
        st.error(f"Erro ao cadastrar equipamento: {e}")
        return False

def start_maintenance(equipamento_id: int, tipo: str, descricao: str) -> bool:
    try:
        response = supabase.table("manutencoes").insert({
            "equipamento_id": equipamento_id,
            "tipo": tipo,
            "descricao": descricao.strip(),
            "data_inicio": datetime.now().isoformat(),
            "status": "Em andamento"
        }).execute()
        if response.data:
            supabase.table("equipamentos").update({"status": "Em manutenção"}).eq("id", equipamento_id).execute()
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao abrir manutenção: {e}")
        return False

def finish_maintenance(manut_id: int, equipamento_id: int) -> bool:
    try:
        response = supabase.table("manutencoes").update({
            "data_fim": datetime.now().isoformat(),
            "status": "Concluída"
        }).eq("id", manut_id).execute()
        if response.data:
            supabase.table("equipamentos").update({"status": "Ativo"}).eq("id", equipamento_id).execute()
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao finalizar manutenção: {e}")
        return False

# -------------------
# Alertas Inteligentes
# -------------------
def mostrar_alertas_inteligencia():
    manutencoes_data = fetch_manutencoes()
    equipamentos_data = fetch_equipamentos()
    alertas_encontrados = False

    if not manutencoes_data and not equipamentos_data:
        st.success("✅ Nenhum alerta crítico no momento!")
        return

    # Equipamentos problemáticos
    if manutencoes_data:
        df_manut = pd.DataFrame(manutencoes_data)
        seis_meses = datetime.now() - timedelta(days=180)
        df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
        df_recente = df_manut[df_manut['data_inicio'] >= seis_meses]
        if not df_recente.empty:
            recorrentes = df_recente['equipamento_id'].value_counts()
            for eq_id, qtd in recorrentes.items():
                if qtd >= 3:
                    nome_eq = next((e['nome'] for e in equipamentos_data if e['id']==eq_id), "Desconhecido")
                    setor_eq = next((e['setor'] for e in equipamentos_data if e['id']==eq_id), "Desconhecido")
                    st.warning(f"⚠️ Equipamento Problemático: '{nome_eq}' ({setor_eq}) teve {qtd} manutenções nos últimos 6 meses")
                    alertas_encontrados = True

    # Manutenções urgentes
    if manutencoes_data:
        urgentes = [m for m in manutencoes_data if m['tipo']=='Urgente / Emergencial']
        df_urgentes = pd.DataFrame(urgentes)
        if not df_urgentes.empty:
            contagem_urgente = df_urgentes['equipamento_id'].value_counts()
            for eq_id, qtd in contagem_urgente.items():
                if qtd >=2:
                    nome_eq = next((e['nome'] for e in equipamentos_data if e['id']==eq_id), "Desconhecido")
                    setor_eq = next((e['setor'] for e in equipamentos_data if e['id']==eq_id), "Desconhecido")
                    st.error(f"🚨 Alerta Crítico: '{nome_eq}' ({setor_eq}) teve {qtd} manutenções urgentes")
                    alertas_encontrados = True

    if not alertas_encontrados:
        st.success("✅ Nenhum alerta crítico no momento!")

# -------------------
# Páginas
# -------------------
def pagina_inicial():
    st.title("🏥 Sistema de Manutenção | HSC")
    mostrar_alertas_inteligencia()
    st.info("💡 Use a sidebar à esquerda para navegar entre as funcionalidades.")

def pagina_adicionar_equipamento():
    st.header("⚙️ Gestão de Equipamentos")
    st.subheader("Cadastrar Novo Equipamento")
    setores = ["Hemodiálise", "Lavanderia", "UTI", "Centro Cirúrgico"]
    setor_escolhido = st.selectbox("🏢 Selecione o setor", setores + ["Outro"])
    setor_final = setor_escolhido
    if setor_escolhido == "Outro":
        setor_final = st.text_input("Digite o nome do setor")
    nome = st.text_input("Nome do equipamento")
    numero_serie = st.text_input("Número de Série")
    if st.button("✅ Cadastrar"):
        error = validate_equipment_data(nome, setor_final, numero_serie)
        if error:
            st.error(error)
        else:
            if insert_equipment(nome, setor_final, numero_serie):
                st.success(f"Equipamento '{nome}' cadastrado!")
                st.balloons()
            else:
                st.error("Erro ao cadastrar equipamento.")

def pagina_registrar_manutencao():
    st.header("🔧 Gestão de Manutenções")
    mostrar_alertas_inteligencia()
    st.subheader("Abrir Manutenção")
    equipamentos_ativos = [e for e in fetch_equipamentos() if e['status']=="Ativo"]
    if not equipamentos_ativos:
        st.warning("Nenhum equipamento ativo disponível para manutenção.")
        return
    equip_escolhido = st.selectbox("Selecione o equipamento", [f"{e['nome']} ({e['setor']})" for e in equipamentos_ativos])
    tipo = st.selectbox("Tipo de manutenção", ["Preventiva", "Corretiva", "Urgente / Emergencial"])
    descricao = st.text_area("Descrição")
    if st.button("🛠 Abrir Manutenção"):
        eq_index = [f"{e['nome']} ({e['setor']})" for e in equipamentos_ativos].index(equip_escolhido)
        equipamento_id = equipamentos_ativos[eq_index]['id']
        if start_maintenance(equipamento_id, tipo, descricao):
            st.success("Manutenção registrada com sucesso!")
        else:
            st.error("Erro ao registrar manutenção.")

def pagina_dashboard():
    st.header("📊 Dashboard")
    df_manut = pd.DataFrame(fetch_manutencoes())
    if df_manut.empty:
        st.info("Nenhuma manutenção registrada.")
        return
    df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
    df_manut['data_fim'] = pd.to_datetime(df_manut['data_fim'], errors='coerce')
    df_manut['duracao_dias'] = (df_manut['data_fim'] - df_manut['data_inicio']).dt.days.fillna(0)
    fig = px.bar(df_manut, x='tipo', y='duracao_dias', color='status', title="Manutenções por Tipo e Status")
    st.plotly_chart(fig, use_container_width=True)

# -------------------
# Main
# -------------------
def main():
    if "user" not in st.session_state:
        login()
        return

    pagina = show_sidebar()
    if pagina == "🏠 Página Inicial":
        pagina_inicial()
    elif pagina == "⚙️ Equipamentos":
        pagina_adicionar_equipamento()
    elif pagina == "🔧 Manutenções":
        pagina_registrar_manutencao()
    elif pagina == "📊 Dashboard":
        pagina_dashboard()

if __name__ == "__main__":
    main()
