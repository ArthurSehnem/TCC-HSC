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
        "⚠ Acesso restrito aos profissionais autorizados do Hospital Santa Cruz."
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
            st.error("Email ou senha incorretos.")

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
            f"<div style='text-align:center; margin-bottom:20px;'>"
            f"<img src='data:image/png;base64,{encoded_logo}' width='120'></div>",
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
# Alertas inteligentes
# -------------------
def gerar_alertas(df_equip, df_manut):
    alertas = []

    # Equipamentos problemáticos: 3+ manutenções em 6 meses
    seis_meses = datetime.now() - timedelta(days=180)
    manut_ult_6m = df_manut[df_manut['data_inicio'] >= seis_meses]
    contagem_equip = manut_ult_6m.groupby('equipamento_id').size()
    problem_equip = contagem_equip[contagem_equip >= 3]
    for eq_id, qtd in problem_equip.items():
        eq_nome = df_equip[df_equip['id'] == eq_id]['nome'].values[0]
        alertas.append(f"⚠ Equipamento problemático: {eq_nome} com {qtd} manutenções nos últimos 6 meses")

    # Manutenções urgentes recorrentes: 2+ urgências por equipamento
    urgencias = df_manut[df_manut['tipo'].str.lower() == 'urgente']
    cont_urg = urgencias.groupby('equipamento_id').size()
    urg_rec = cont_urg[cont_urg >= 2]
    for eq_id, qtd in urg_rec.items():
        eq_nome = df_equip[df_equip['id'] == eq_id]['nome'].values[0]
        alertas.append(f"⚠ Manutenções urgentes recorrentes: {eq_nome} com {qtd} ocorrências")

    # Padrões de falhas: 3+ consecutivas do mesmo tipo
    for eq_id, df_eq in df_manut.groupby('equipamento_id'):
        df_eq = df_eq.sort_values('data_inicio')
        tipos = df_eq['tipo'].tolist()
        count = 1
        for i in range(1, len(tipos)):
            if tipos[i] == tipos[i-1]:
                count += 1
                if count >= 3:
                    eq_nome = df_equip[df_equip['id'] == eq_id]['nome'].values[0]
                    alertas.append(f"⚠ Padrão de falha: {eq_nome} com {count} manutenções consecutivas do tipo '{tipos[i]}'")
                    break
            else:
                count = 1

    # Baixa disponibilidade por setor <80%
    dispo_setor = df_equip.groupby('setor')['status'].apply(lambda x: (x=='Ativo').sum()/len(x)*100)
    for setor, dispo in dispo_setor.items():
        if dispo < 80:
            alertas.append(f"⚠ Baixa disponibilidade no setor {setor}: {dispo:.1f}% ativos")

    # Manutenções longas: >7 dias em andamento
    em_andamento = df_manut[df_manut['status'] == 'Em andamento']
    for idx, row in em_andamento.iterrows():
        duracao = datetime.now() - row['data_inicio']
        if duracao.days > 7:
            eq_nome = df_equip[df_equip['id'] == row['equipamento_id']]['nome'].values[0]
            alertas.append(f"⚠ Manutenção longa: {eq_nome} em andamento há {duracao.days} dias")

    return alertas

# -------------------
# Páginas
# -------------------
def pagina_inicial(supabase):
    st.title("Sistema de Manutenção | HSC")
    st.markdown("Bem-vindo ao sistema de gestão de manutenção de equipamentos críticos.")
    df_equip = pd.DataFrame(fetch_equipamentos(supabase))
    df_manut = pd.DataFrame(fetch_manutencoes(supabase))

    if not df_equip.empty and not df_manut.empty:
        df_manut['data_inicio'] = pd.to_datetime(df_manut['data_inicio'])
        df_manut['data_fim'] = pd.to_datetime(df_manut['data_fim'], errors='coerce')
        alertas = gerar_alertas(df_equip, df_manut)
        if alertas:
            st.warning("### Alertas Inteligentes")
            for a in alertas:
                st.write(a)
        else:
            st.success("Nenhum alerta no momento.")

def pagina_adicionar_equipamento(supabase):
    st.header("Equipamentos")
    tab1, tab2, tab3 = st.tabs(["Cadastrar", "Gerenciar Status", "Analítico"])
    # Aba 1 - Cadastrar
    with tab1:
        setores_padrao = ["Hemodiálise", "Lavanderia", "Instrumentais Cirúrgicos"]
        setor_escolhido = st.selectbox("Selecione o setor", setores_padrao + ["Outro"])
        setor_final = setor_escolhido
        if setor_escolhido == "Outro":
            setor_custom = st.text_input("Digite o nome do setor")
            if setor_custom.strip(): setor_final = setor_custom.strip().title()
            else: setor_final = None
        with st.form("form_equipamento", clear_on_submit=True):
            nome = st.text_input("Nome do equipamento *")
            numero_serie = st.text_input("Número de Série *")
            submitted = st.form_submit_button("Cadastrar")
        if submitted:
            if not setor_final: st.error("Selecione ou informe um setor.")
            else:
                error = validate_equipment_data(nome, setor_final, numero_serie)
                if error: st.error(error)
                else:
                    if insert_equipment(supabase, nome, setor_final, numero_serie):
                        st.success(f"Equipamento '{nome}' cadastrado!")
                        st.balloons()
                        st.cache_data.clear()
                    else: st.error("Erro ao cadastrar equipamento.")
    # Aba 2 - Gerenciar Status
    with tab2:
        equipamentos_data = fetch_equipamentos(supabase)
        if equipamentos_data:
            equipamento_dict = {f"{e['nome']} - {e['setor']} ({e['status']})": e['id'] for e in equipamentos_data}
            equipamento_selecionado = st.selectbox("Selecione um equipamento", [""] + list(equipamento_dict.keys()))
            if equipamento_selecionado:
                equip_id = equipamento_dict[equipamento_selecionado]
                status_atual = next(e['status'] for e in equipamentos_data if e['id'] == equip_id)
                novo_status = "Inativo" if status_atual == "Ativo" else "Ativo"
                if st.button(f"Alterar para {novo_status}"):
                    supabase.table("equipamentos").update({"status": novo_status}).eq("id", equip_id).execute()
                    st.success(f"Status alterado para {novo_status}")
                    st.cache_data.clear()
        else:
            st.info("Nenhum equipamento cadastrado.")
    # Aba 3 - Analítico
    with tab3:
        equipamentos_data = fetch_equipamentos(supabase)
        if equipamentos_data:
            df = pd.DataFrame(equipamentos_data)
            st.dataframe(df[['nome','setor','numero_serie','status']], use_container_width=True)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", len(df))
            col2.metric("Ativos", len(df[df['status']=='Ativo']))
            col3.metric("Em Manutenção", len(df[df['status']=='Em manutenção']))
        else:
            st.info("Nenhum equipamento cadastrado.")

def pagina_registrar_manutencao(supabase):
    st.header("Manutenções")
    tab1, tab2, tab3 = st.tabs(["Abrir", "Finalizar", "Analítico"])
    # Abrir
    with tab1:
        equipamentos_ativos = [e for e in fetch_equipamentos(supabase) if e['status']=="Ativo"]
        if equipamentos_ativos:
            equipamento_dict = {f"{e['nome']} - {e['setor']}": e['id'] for e in equipamentos_ativos}
            with st.form("abrir_manut", clear_on_submit=True):
                equipamento_selecionado = st.selectbox("Equipamento", [""] + list(equipamento_dict.keys()))
                tipo = st.selectbox("Tipo", ["", "Preventiva", "Urgente", "Calibração", "Higienização"])
                descricao = st.text_area("Descrição")
                submitted = st.form_submit_button("Abrir")
                if submitted:
                    if not equipamento_selecionado or not tipo or not descricao.strip():
                        st.error("Todos os campos obrigatórios!")
                    else:
                        equipamento_id = equipamento_dict[equipamento_selecionado]
                        if start_maintenance(supabase, equipamento_id, tipo, descricao):
                            st.success("Manutenção aberta!")
                            st.balloons()
                        else: st.error("Erro ao abrir manutenção.")
        else:
            st.warning("Nenhum equipamento ativo disponível.")
    # Finalizar
    with tab2:
        manutencoes_abertas = [m for m in fetch_manutencoes(supabase) if m['status']=="Em andamento"]
        if manutencoes_abertas:
            equipamentos_data = fetch_equipamentos(supabase)
            manut_dict = {}
            for m in manutencoes_abertas:
                eq_nome = next((e['nome'] for e in equipamentos_data if e['id']==m['equipamento_id']), "Desconhecido")
                manut_dict[f"{eq_nome} | {m['tipo']} | {m['descricao'][:50]}"] = {'manut_id': m['id'], 'equip_id': m['equipamento_id']}
            with st.form("finalizar_manut", clear_on_submit=True):
                manut_selecionada = st.selectbox("Manutenção", [""] + list(manut_dict.keys()))
                submitted = st.form_submit_button("Finalizar")
                if submitted:
                    if not manut_selecionada: st.error("Selecione uma manutenção")
                    else:
                        info = manut_dict[manut_selecionada]
                        if finish_maintenance(supabase, info['manut_id'], info['equip_id']):
                            st.success("Manutenção finalizada!")
                            st.balloons()
                        else: st.error("Erro ao finalizar manutenção.")
        else:
            st.info("Nenhuma manutenção em andamento.")
    # Analítico
    with tab3:
        manutencoes_data = fetch_manutencoes(supabase)
        equipamentos_data = fetch_equipamentos(supabase)
        if manutencoes_data:
            df = pd.DataFrame(manutencoes_data)
            for idx, row in df.iterrows():
                eq = next((e for e in equipamentos_data if e['id']==row['equipamento_id']), None)
                if eq:
                    df.at[idx, 'nome_equip'] = eq['nome']
                    df.at[idx, 'setor_equip'] = eq['setor']
            st.dataframe(df[['nome_equip','setor_equip','tipo','descricao','status']], use_container_width=True)
        else:
            st.info("Nenhuma manutenção registrada.")

def pagina_dashboard(supabase):
    st.header("Dashboard")
    df_equip = pd.DataFrame(fetch_equipamentos(supabase))
    df_manut = pd.DataFrame(fetch_manutencoes(supabase))
    if not df_equip.empty:
        st.subheader("Disponibilidade por setor")
        dispo = df_equip.groupby('setor')['status'].apply(lambda x: (x=='Ativo').sum()/len(x)*100).reset_index()
        dispo.columns = ['Setor','Disponibilidade (%)']
        fig = px.bar(dispo, x='Setor', y='Disponibilidade (%)', text='Disponibilidade (%)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Cadastre equipamentos primeiro.")

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
