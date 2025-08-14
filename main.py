import streamlit as st
import base64
from supabase import create_client
import pandas as pd
from datetime import datetime

# -------------------
# Conexão com Supabase
# -------------------
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# -------------------
# Carregar logo
# -------------------
logo_path = "logo.png"
with open(logo_path, "rb") as f:
    img_bytes = f.read()
encoded_logo = base64.b64encode(img_bytes).decode()

st.sidebar.markdown(
    f"""
    <div style='text-align: center;'>
        <img src='data:image/png;base64,{encoded_logo}' width='120'>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown("---")
pagina = st.sidebar.radio(
    "Navegue para:",
    ["Página Inicial", "Adicionar Equipamento", "Registrar Manutenção", "Dashboard"]
)

# -------------------
# Página Inicial
# -------------------
if pagina == "Página Inicial":
    st.title("Sistema de Manutenção | HSC")
    st.markdown("""
Este sistema é fruto de uma **parceria entre o Hospital Santa Cruz (HSC) e a UNISC**, desenvolvido para **apoiar o hospital na gestão e histórico das manutenções de equipamentos críticos**.

**Esta é a página inicial**, onde você encontra informações gerais sobre o sistema.  
Para navegar pelas funcionalidades, utilize a **sidebar à esquerda**, onde você poderá:  

- **Consultar o status atual** de todos os equipamentos;  
- **Registrar novas manutenções**, garantindo histórico completo;  
- **Cadastrar novos equipamentos**, otimizando o fluxo de informações;  
- **Acompanhar melhorias contínuas** no gerenciamento de recursos hospitalares.  

Nosso objetivo é tornar a gestão de equipamentos **mais eficiente, segura e transparente** para todos os profissionais envolvidos.
""")

# -------------------
# Página de cadastro de equipamentos
# -------------------
elif pagina == "Adicionar Equipamento":
    st.header("Adicionar Novo Equipamento")
    st.markdown("""
Nesta página, você pode cadastrar novos equipamentos. 
Manter o sistema atualizado é essencial, então solicitamos algumas informações básicas para registro em nosso banco de dados.  

Pedimos atenção ao preencher os campos, pois as informações inseridas impactam diretamente 
nos relatórios e no painel de Business Intelligence.
""")

    # Estado inicial
    for key in ["nome", "setor", "numero_serie"]:
        if key not in st.session_state:
            st.session_state[key] = ""

    nome = st.text_input("Nome do equipamento", value=st.session_state.nome)
    setor = st.text_input("Setor", value=st.session_state.setor)
    numero_serie = st.text_input("Número de Série", value=st.session_state.numero_serie)

    if st.button("Cadastrar Equipamento"):
        if not nome or not setor or not numero_serie:
            st.error("Por favor, preencha todos os campos obrigatórios!")
        else:
            resp = supabase.table("equipamentos").insert({
                "nome": nome,
                "setor": setor,
                "numero_serie": numero_serie,
                "status": "Ativo"
            }).execute()
            if resp.data:
                st.success(f"Equipamento '{nome}' cadastrado com sucesso! Status definido como Ativo.")
                st.session_state.nome = ""
                st.session_state.setor = ""
                st.session_state.numero_serie = ""
            else:
                st.error("Ocorreu um erro ao cadastrar o equipamento. Tente novamente.")

# -------------------
# Página de manutenções
# -------------------
elif pagina == "Registrar Manutenção":
    st.header("Registrar Manutenção")
    st.markdown("""
Nesta página, você pode registrar as manutenções realizadas nos equipamentos.  
Manter um histórico preciso é essencial para garantir a segurança, eficiência e confiabilidade do sistema.  

Ao abrir uma nova manutenção, o equipamento terá seu status alterado para **'Em Manutenção'**. 
Ao finalizar, o status retornará para **'Ativo'**.  
Esses registros ajudam a monitorar o tempo gasto em cada atendimento e melhoram nossos relatórios de gestão.
""")

    # -------- Abrir nova manutenção --------
    st.subheader("Abrir nova manutenção")
    equipamentos_resp = supabase.table("equipamentos").select("id, nome, status").execute()
    equipamentos_data = equipamentos_resp.data

    if equipamentos_data:
        equipamento_dict = {e['nome']: e['id'] for e in equipamentos_data}
        nomes_equipamentos = ["--"] + list(equipamento_dict.keys())
        equipamento_nome = st.selectbox("--", nomes_equipamentos, index=0)

        tipo = st.selectbox("Tipo de manutenção", ["--", "Preventiva", "Corretiva"], index=0)
        descricao = st.text_area("Descrição da manutenção")

        if st.button("Abrir Manutenção"):
            if equipamento_nome == "--" or tipo == "--":
                st.warning("Escolha um equipamento e um tipo de manutenção antes de registrar.")
            elif not descricao:
                st.error("Preencha a descrição da manutenção!")
            else:
                equipamento_id = equipamento_dict[equipamento_nome]
                resp = supabase.table("manutencoes").insert({
                    "equipamento_id": equipamento_id,
                    "tipo": tipo,
                    "descricao": descricao,
                    "data_inicio": datetime.now().isoformat(),
                    "data_fim": None,
                    "status": "Em andamento"
                }).execute()
                if resp.data:
                    supabase.table("equipamentos").update({"status": "Em manutenção"}).eq("id", equipamento_id).execute()
                    st.success(f"Manutenção para '{equipamento_nome}' aberta com sucesso!")
                else:
                    st.error("Erro ao abrir manutenção. Tente novamente.")
    else:
        st.info("Nenhum equipamento cadastrado. Cadastre um equipamento primeiro.")

    st.markdown("---")

    # -------- Finalizar manutenção --------
    st.subheader("Finalizar manutenção")
    manut_resp = supabase.table("manutencoes").select("id, equipamento_id, descricao").eq("status", "Em andamento").execute()
    manut_data = manut_resp.data

    if manut_data:
        manut_dict = {}
        for m in manut_data:
            eq_nome = next((e['nome'] for e in equipamentos_data if e['id'] == m['equipamento_id']), "Desconhecido")
            manut_dict[f"{eq_nome} | {m['descricao']}"] = m['id']

        manut_nome = st.selectbox("Selecione a manutenção em andamento", ["--"] + list(manut_dict.keys()), index=0)

        if st.button("Finalizar Manutenção"):
            if manut_nome == "--":
                st.warning("Escolha uma manutenção antes de finalizar.")
            else:
                manut_id = manut_dict[manut_nome]
                data_fim_completa = datetime.now().isoformat()
                resp = supabase.table("manutencoes").update({
                    "data_fim": data_fim_completa,
                    "status": "Concluída"
                }).eq("id", manut_id).execute()
                if resp.data:
                    equip_id = next((m['equipamento_id'] for m in manut_data if m['id'] == manut_id), None)
                    if equip_id:
                        supabase.table("equipamentos").update({"status": "Ativo"}).eq("id", equip_id).execute()
                    st.success("Manutenção finalizada com sucesso!")
                else:
                    st.error("Erro ao finalizar a manutenção. Tente novamente.")
    else:
        st.info("Não há manutenções em andamento no momento.")

# -------------------
# Dashboard
# -------------------
elif pagina == "Dashboard":
    st.header("Dashboard de Equipamentos e Manutenções")

    df_equip = pd.DataFrame(supabase.table("equipamentos").select("*").execute().data)
    df_manut = pd.DataFrame(supabase.table("manutencoes").select("*").execute().data)

    if not df_equip.empty:
        # KPIs Equipamentos
        col1, col2, col3, col4 = st.columns(4)
        total = len(df_equip)
        ativos = df_equip[df_equip['status'] == 'Ativo'].shape[0]
        em_manut = df_equip[df_equip['status'] == 'Em manutenção'].shape[0]
        col1.metric("Total de Equipamentos", total)
        col2.metric("Ativos", ativos)
        col3.metric("Em Manutenção", em_manut)
        col4.metric("Percentual de Ativos", f"{ativos/total*100:.1f}%")

        st.markdown("---")

        # KPIs Manutenções
        if not df_manut.empty:
            total_manut = len(df_manut)
            abertas = df_manut[df_manut['status'] == 'Em andamento'].shape[0]
            concluidas = df_manut[df_manut['status'] == 'Concluída'].shape[0]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Manutenções", total_manut)
            col2.metric("Em andamento", abertas)
            col3.metric("Concluídas", concluidas)
            col4.metric("Percentual Concluído", f"{concluidas/total_manut*100:.1f}%")

        st.markdown("---")

        # Filtros
        setores = ["--"] + list(df_equip['setor'].unique())
        status_list = ["--"] + list(df_equip['status'].unique())
        filtro_setor = st.selectbox("Filtrar por setor:", setores, index=0)
        filtro_status = st.selectbox("Filtrar por status:", status_list, index=0)

        df_equip_filtrado = df_equip.copy()
        if filtro_setor != "-- Selecione --":
            df_equip_filtrado = df_equip_filtrado[df_equip_filtrado['setor'] == filtro_setor]
        if filtro_status != "-- Selecione --":
            df_equip_filtrado = df_equip_filtrado[df_equip_filtrado['status'] == filtro_status]

        st.subheader("Equipamentos")
        st.dataframe(df_equip_filtrado)
        st.subheader("Equipamentos por Setor")
        st.bar_chart(df_equip_filtrado['setor'].value_counts())
        st.subheader("Equipamentos por Status")
        st.bar_chart(df_equip_filtrado['status'].value_counts())

        # Manutenções detalhadas
        if not df_manut.empty:
            equipamentos_options = ["--"] + list(df_equip['nome'])
            filtro_equip = st.selectbox("Filtrar por equipamento:", equipamentos_options, index=0)
            df_manut_filtrado = df_manut.copy()
            if filtro_equip != "-- Selecione --":
                df_manut_filtrado = df_manut_filtrado[df_manut_filtrado['equipamento_id'] == df_equip[df_equip['nome'] == filtro_equip]['id'].values[0]]

            st.subheader("Manutenções")
            st.dataframe(df_manut_filtrado)
            st.subheader("Manutenções por Status")
            st.bar_chart(df_manut_filtrado['status'].value_counts())

            st.subheader("Manutenções por Setor")
            df_manut_filtrado = df_manut_filtrado.merge(df_equip[['id','setor']], left_on='equipamento_id', right_on='id', how='left')
            st.bar_chart(df_manut_filtrado['setor'].value_counts())
    else:
        st.info("Nenhum equipamento encontrado.")
