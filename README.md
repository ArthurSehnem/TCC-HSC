**📄 README: Sistema de Gestão de Manutenção Hospitalar (HSC) 🏥**

O Sistema de Gestão de Manutenção do Hospital Santa Cruz (HSC) é uma aplicação web interativa desenvolvida com Streamlit e utilizando Supabase como backend (banco de dados e autenticação).

A aplicação tem como objetivo otimizar a gestão de ativos e o controle de manutenções hospitalares, oferecendo uma visão integrada do inventário de equipamentos, acompanhamento de ordens de serviço e indicadores de desempenho (KPIs) em tempo real.

**✨ Funcionalidades Principais**
**🔐 Sistema de Login Seguro**
Acesso restrito com credenciais de administrador via st.secrets.

**⚙️ Gestão de Equipamentos (CRUD)**
Cadastro de novos equipamentos (Nome, Setor, Número de Série).
Consulta e busca de equipamentos existentes.
Alteração de status (ex.: Ativo para Inativo).

**🔧 Gestão de Manutenções (Ordens de Serviço)**
Abertura de novas manutenções (Preventiva, Corretiva, Urgente) com registro de data/hora de início.
Finalização de manutenções com registro da resolução e cálculo do tempo de parada.
Visualização de manutenções em andamento.

**📊 Dashboard Executivo e Relatórios**
Métricas de desempenho (Disponibilidade Geral, Manutenções/Mês, etc.).
Gráficos dinâmicos (Plotly Express) de Equipamentos por Setor/Status e Tipos de Manutenção.
Análise de tempo de parada (Média, Máxima e Total por Equipamento/Setor/Tipo).
Exportação de dados para CSV.

**🚨 Alertas Inteligentes**
Avisos automáticos sobre situações críticas:
Equipamentos com alta recorrência de falhas (4+ em 3 meses).
Manutenções em andamento com longa duração (mais de 7 dias).
Setores com baixa disponibilidade.
Equipamentos sem manutenção preventiva em 6+ meses.

**🚀 Otimização de Performance**
Uso de vetorização do Pandas e recursos de cache do Streamlit (@st.cache_data, @st.cache_resource) para consultas rápidas ao banco de dados.

**🛠 Tecnologias e Dependências**
Linguagem: Python
Framework: Streamlit
Banco de dados: Supabase
Principais bibliotecas: pandas, plotly.express, plotly
