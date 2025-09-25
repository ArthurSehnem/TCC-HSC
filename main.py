import streamlit as st
import base64
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import plotly.express as px

# -------------------
# Login único
# -------------------
ADMIN_EMAIL = st.secrets["login"]["email"]
ADMIN_PASSWORD = st.secrets["login"]["password"]

def login():
    st.title("Login - Sistema HSC")
    st.info(
        """
        ⚠ *Acesso restrito aos profissionais autorizados do Hospital Santa Cruz.*  
        Por favor, insira suas credenciais para continuar.
        """
    )

    with st.form("login_form"):
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        if email == ADMIN_EMAIL and senha == ADMIN_PASSWORD:
            st.success("Login realizado com sucesso!")
            st.session_state["user"] = email
        else:
            st.error("Email ou senha incorretos.\nSe você esqueceu a senha, contate o setor de TI do hospital.")

def main_login():
    if "user" not in st.session_state:
        login()
        st.stop()

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
        ["Página Inicial", "Equipamentos", "Manutenções", "Dashboard"],
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

def validate_equipment_data(nome: str, setor: str, numero_serie: str) -> Optional[str]:
    if not nome.strip(): return "Nome do equipamento é obrigatório"
    if not setor.strip(): return "Setor é obrigatório"
    if not numero_serie.strip(): return "Número de série é obrigatório"
    if len(nome.strip()) < 3: return "Nome deve ter pelo menos 3 caracteres"
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
# Alertas Inteligentes
# -------------------
def mostrar_alertas_inteligencia(supabase):
    equipamentos = fetch_equipamentos(supabase)
    manutencoes = fetch_manutencoes(supabase)

    if not equipamentos or not manutencoes:
        st.info("Não há dados suficientes para gerar alertas inteligentes.")
        return

    df_equip = pd.DataFrame(equipamentos)
    df_manut = pd.DataFrame(manutencoes)

    now = datetime.now()
    seis_meses_atras = now - timedelta(days=30*6)
    sete_dias_atras = now - timedelta(days=7)

    alertas_geral = []

    # Equipamentos Problemáticos
    df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
    manut_ult_6meses = df_manut[df_manut['data_inicio'] >= seis_meses_atras]
    manut_count = manut_ult_6meses.groupby('equipamento_id').size()
    problem_equip = manut_count[manut_count >= 3].index.tolist()
    if problem_equip:
        nomes = [e['nome'] for e in equipamentos if e['id'] in problem_equip]
        alertas_geral.append(f"⚠ Equipamentos problemáticos (3+ manutenções nos últimos 6 meses): {', '.join(nomes)}")

    # Manutenções Urgentes Recorrentes
    urgencias = df_manut[df_manut['tipo'].str.lower().str.contains("urgente", na=False)]
    urg_count = urgencias.groupby('equipamento_id').size()
    urg_equip = urg_count[urg_count >= 2].index.tolist()
    if urg_equip:
        nomes = [e['nome'] for e in equipamentos if e['id'] in urg_equip]
        alertas_geral.append(f"⚠ Equipamentos com manutenções urgentes recorrentes (2+): {', '.join(nomes)}")

    # Padrões de Falhas
    padrao_falha = []
    for eq_id in df_equip['id']:
        df_eq = df_manut[df_manut['equipamento_id']==eq_id].sort_values('data_inicio')
        tipos = df_eq['tipo'].tolist()
        count = 1
        for i in range(1, len(tipos)):
            if tipos[i] == tipos[i-1]:
                count += 1
            else:
                count = 1
            if count >= 3:
                padrao_falha.append(eq_id)
                break
    if padrao_falha:
        nomes = [e['nome'] for e in equipamentos if e['id'] in padrao_falha]
        alertas_geral.append(f"⚠ Padrões de falhas detectados (3+ manutenções consecutivas do mesmo tipo): {', '.join(nomes)}")

    # Baixa Disponibilidade por Setor
    dispon_por_setor = df_equip.groupby('setor')['status'].apply(lambda x: (x=='Ativo').sum()/len(x)*100)
    baixa_dispon = dispon_por_setor[dispon_por_setor < 80]
    if not baixa_dispon.empty:
        setores = ", ".join(baixa_dispon.index.tolist())
        alertas_geral.append(f"⚠ Setores com baixa disponibilidade (<80% ativos): {setores}")

    # Manutenções Longas
    longas = df_manut[(df_manut['status']=="Em andamento") & (df_manut['data_inicio'] <= sete_dias_atras)]
    if not longas.empty:
        nomes = [e['nome'] for e in equipamentos if e['id'] in longas['equipamento_id'].tolist()]
        alertas_geral.append(f"⚠ Manutenções em andamento há mais de 7 dias: {', '.join(nomes)}")

    # Exibir alertas
    if alertas_geral:
        st.warning("🔔 Alertas Inteligentes:")
        for alerta in alertas_geral:
            st.write(alerta)
    else:
        st.info("Nenhum alerta crítico identificado no momento.")

# -------------------
# Páginas
# -------------------
def pagina_inicial(supabase):
    st.title("Sistema de Manutenção | HSC")
    st.markdown("""
### Bem-vindo ao Sistema de Gestão de Manutenção
Sistema desenvolvido para **gestão e histórico das manutenções de equipamentos críticos** do hospital.
- Dashboard interativo
- Gestão de manutenções
- Cadastro de equipamentos
- Relatórios avançados
""")
    st.info("💡 Use a sidebar para navegar entre as funcionalidades.")
    # Chamar alertas inteligentes
    mostrar_alertas_inteligencia(supabase)

# -------------------
# As funções de páginas Equipamentos, Manutenções e Dashboard permanecem iguais
# -------------------

# -------------------
# Main
# -------------------
def main():
    main_login()
    supabase = init_supabase()
    if not supabase:
        st.error("Erro de conexão com banco de dados.")
        return
    pagina = show_sidebar()
    if pagina == "Página Inicial": pagina_inicial(supabase)
    elif pagina == "Equipamentos": pagina_adicionar_equipamento(supabase)
    elif pagina == "Manutenções": pagina_registrar_manutencao(supabase)
    elif pagina == "Dashboard": pagina_dashboard(supabase)

if __name__ == "__main__":
    main()
