# Sistema de Visitantes - Igreja e Eventos

Conjunto de dois aplicativos desktop em Python (Tkinter + SQLite),
**interligados pelo mesmo banco de dados**:

1. **`app.py`** — App de Cadastro: cadastra visitantes (nome e telefone)
   em cultos/eventos.
2. **`dashboard.py`** — Painel de Relatórios: exibe os visitantes
   cadastrados no app 1 em tempo real, gera automaticamente um gráfico
   mensal de visitantes por evento/culto e monta uma tabela do ano
   inteiro.

Os dois apps **não precisam estar abertos ao mesmo tempo**, mas podem
ficar — eles apontam para o mesmo arquivo `visitantes.db`, então tudo
que é cadastrado no app 1 aparece automaticamente no app 2 (basta clicar
em "Atualizar" ou trocar de aba).

## Requisitos
- Python 3.9 ou superior (Tkinter já vem incluído)
- **matplotlib** para os gráficos do painel de relatórios:
  ```bash
  pip install matplotlib
  ```
  (o app de cadastro, `app.py`, não precisa do matplotlib)

## Como executar
```bash
python3 app.py          # App 1: cadastro de visitantes
python3 dashboard.py    # App 2: painel de relatórios
```

Ambos criam/usam o arquivo `visitantes.db` na mesma pasta.

## App 2 — Painel de Relatórios (`dashboard.py`)

### Aba "Visitantes"
Mostra, em tempo real, todos os visitantes cadastrados no App 1 (nome,
telefone, evento e data de cadastro). Botão "Atualizar agora" recarrega
a lista; ela também é recarregada automaticamente ao entrar na aba.

### Aba "Relatório Mensal"
- Escolha o **ano** e o **mês** e clique em **Visualizar** para pré-
  visualizar o gráfico de barras com a quantidade de visitantes por
  evento/culto daquele mês (o nome da igreja aparece no título).
- Clique em **Salvar / Atualizar relatório do mês** para gravar o
  gráfico como PNG em `relatorios/<ano>/<mês>_grafico.png` e marcar o
  mês como processado.
- **Geração automática de fim de mês**: toda vez que o painel é aberto,
  ele verifica se algum mês já encerrado (desde o primeiro visitante
  cadastrado) ainda não teve relatório gerado, e gera automaticamente
  para todos eles — isso cobre o caso de o programa ficar fechado
  justamente na virada do mês. Um aviso na tela informa quais meses
  foram processados.
- Meses sem nenhum visitante cadastrado exibem uma mensagem no gráfico
  em vez de um gráfico vazio, e ainda assim são salvos normalmente.

### Aba "Tabela do Ano"
Mostra os 12 meses do ano selecionado, com total de visitantes,
quantidade de eventos/cultos distintos e média de visitantes por
evento. Botão **Exportar CSV** salva a tabela completa (com nome da
igreja e ano no cabeçalho) para abrir no Excel/Google Sheets.

### Nome da igreja
Clique em **"Editar nome da igreja"** no topo do painel para definir ou
alterar o nome exibido nos gráficos e nas exportações. Fica salvo no
próprio banco de dados.

### Retenção de dados (regra aplicada)
Nenhum dado é apagado automaticamente em momento algum — todos os
gráficos gerados e a tabela anual continuam acessíveis para sempre.
A única coisa que muda com o tempo é **qual ano vem selecionado por
padrão** ao abrir o painel: o ano anterior continua aparecendo como
padrão até **31 de janeiro** (um mês de prazo após a virada do ano,
como pedido, para fechar o relatório anual com calma); a partir de
1º de fevereiro, o padrão passa a ser o ano corrente. Você pode trocar
de ano no seletor a qualquer momento, independente dessa regra.

## Estrutura dos arquivos
| Arquivo | Responsabilidade |
|---|---|
| `app.py` | App 1 — interface de cadastro de visitantes |
| `dashboard.py` | App 2 — painel de relatórios (visitantes, gráfico mensal, tabela anual) |
| `database.py` | Acesso ao banco SQLite compartilhado (visitantes/eventos) |
| `relatorios_db.py` | Consultas agregadas, configurações (nome da igreja) e controle de meses processados |
| `graficos.py` | Geração do gráfico mensal (matplotlib) |
| `validadores.py` | Validação de nome e telefone |
| `visitantes.db` | Banco de dados compartilhado (criado automaticamente) |
| `relatorios/<ano>/` | Gráficos mensais salvos em PNG, organizados por ano |

## Validações e tratamento de erros
- Nome e telefone seguem as mesmas validações do App 1.
- Ano/mês inválidos, matplotlib não instalado, pasta sem permissão de
  escrita, banco de dados bloqueado por acesso simultâneo (dois apps
  abertos ao mesmo tempo) e meses sem nenhum visitante são todos
  tratados com mensagens claras, sem travar o aplicativo.
- O banco usa modo WAL do SQLite para permitir que os dois apps sejam
  usados ao mesmo tempo sem erro de "database is locked".
