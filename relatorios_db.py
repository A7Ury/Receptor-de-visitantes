"""
relatorios_db.py
Camada de dados do Painel de Relatórios.

Usa o MESMO arquivo de banco de dados (visitantes.db) criado pelo
app de cadastro (database.py), acrescentando tabelas próprias para:
- configurações do painel (ex.: nome da igreja)
- controle de quais meses já tiveram relatório gerado
- resumo mensal (cache) por evento, usado para montar a tabela anual
  mesmo que seja consultado offline/rapidamente.

Não duplica dados de visitantes: sempre lê a tabela `visitantes`
do banco original em tempo real.
"""

import calendar
import sqlite3
from datetime import date
from typing import List, Optional, Tuple

from database import get_connection, DatabaseError  # reaproveita a mesma conexão/arquivo

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

NOME_IGREJA_PADRAO = "Minha Igreja"


def init_relatorios_db() -> None:
    """Cria as tabelas do painel de relatórios, se ainda não existirem."""
    schema = """
    CREATE TABLE IF NOT EXISTS configuracoes (
        chave TEXT PRIMARY KEY,
        valor TEXT
    );

    CREATE TABLE IF NOT EXISTS meses_processados (
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        data_processamento TEXT NOT NULL,
        caminho_grafico TEXT,
        PRIMARY KEY (ano, mes)
    );

    CREATE TABLE IF NOT EXISTS resumo_mensal (
        ano INTEGER NOT NULL,
        mes INTEGER NOT NULL,
        evento_nome TEXT NOT NULL,
        data_evento TEXT,
        total_visitantes INTEGER NOT NULL,
        PRIMARY KEY (ano, mes, evento_nome, data_evento)
    );
    """
    try:
        with get_connection() as conn:
            conn.executescript(schema)
            conn.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao inicializar banco de relatórios: {e}") from e


# ---------------------------------------------------------------------------
# Configurações (ex.: nome da igreja)
# ---------------------------------------------------------------------------

def obter_config(chave: str, padrao: str = "") -> str:
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,))
            row = cur.fetchone()
            return row["valor"] if row and row["valor"] else padrao
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao ler configuração: {e}") from e


def definir_config(chave: str, valor: str) -> None:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO configuracoes (chave, valor) VALUES (?, ?) "
                "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                (chave, valor),
            )
            conn.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao salvar configuração: {e}") from e


def obter_nome_igreja() -> str:
    return obter_config("nome_igreja", NOME_IGREJA_PADRAO)


# ---------------------------------------------------------------------------
# Consultas agregadas a partir dos dados reais de visitantes/eventos
# ---------------------------------------------------------------------------

def _intervalo_do_mes(ano: int, mes: int) -> Tuple[str, str]:
    """Retorna (data_inicio, data_fim) no formato 'YYYY-MM-DD HH:MM:SS' cobrindo o mês inteiro."""
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    inicio = f"{ano:04d}-{mes:02d}-01 00:00:00"
    fim = f"{ano:04d}-{mes:02d}-{ultimo_dia:02d} 23:59:59"
    return inicio, fim


def resumo_por_evento_do_mes(ano: int, mes: int) -> List[sqlite3.Row]:
    """
    Retorna, para o mês/ano informados, o total de visitantes agrupado por
    evento (nome do evento + data), com base em data_cadastro do visitante.
    Visitantes sem evento associado entram como 'Sem evento definido'.
    """
    if not (1 <= mes <= 12):
        raise ValueError("Mês inválido. Use um valor entre 1 e 12.")

    inicio, fim = _intervalo_do_mes(ano, mes)
    query = """
        SELECT
            COALESCE(e.nome, 'Sem evento definido') AS evento_nome,
            e.data_evento AS data_evento,
            COUNT(v.id) AS total
        FROM visitantes v
        LEFT JOIN eventos e ON v.evento_id = e.id
        WHERE v.data_cadastro BETWEEN ? AND ?
        GROUP BY evento_nome, data_evento
        ORDER BY total DESC, evento_nome ASC
    """
    try:
        with get_connection() as conn:
            cur = conn.execute(query, (inicio, fim))
            return cur.fetchall()
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao calcular resumo do mês: {e}") from e


def total_visitantes_do_mes(ano: int, mes: int) -> int:
    inicio, fim = _intervalo_do_mes(ano, mes)
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) AS total FROM visitantes WHERE data_cadastro BETWEEN ? AND ?",
                (inicio, fim),
            )
            return cur.fetchone()["total"]
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao contar visitantes do mês: {e}") from e


def anos_disponiveis() -> List[int]:
    """
    Retorna a lista de anos que possuem pelo menos um visitante cadastrado,
    sempre incluindo o ano atual (mesmo sem dados), para nunca ficar vazia.
    """
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT DISTINCT substr(data_cadastro, 1, 4) AS ano FROM visitantes "
                "ORDER BY ano"
            )
            anos = {int(r["ano"]) for r in cur.fetchall() if r["ano"]}
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao consultar anos disponíveis: {e}") from e

    anos.add(date.today().year)
    return sorted(anos)


# ---------------------------------------------------------------------------
# Cache de resumo mensal (usado para montar a tabela anual e o histórico)
# ---------------------------------------------------------------------------

def salvar_resumo_mensal(ano: int, mes: int, linhas: List[sqlite3.Row]) -> None:
    """Substitui o cache de resumo mensal daquele mês pelos dados atuais (idempotente)."""
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM resumo_mensal WHERE ano = ? AND mes = ?", (ano, mes))
            conn.executemany(
                "INSERT INTO resumo_mensal (ano, mes, evento_nome, data_evento, total_visitantes) "
                "VALUES (?, ?, ?, ?, ?)",
                [(ano, mes, r["evento_nome"], r["data_evento"], r["total"]) for r in linhas],
            )
            conn.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao salvar resumo mensal: {e}") from e


def marcar_mes_processado(ano: int, mes: int, caminho_grafico: Optional[str]) -> None:
    data_processamento = date.today().isoformat()
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO meses_processados (ano, mes, data_processamento, caminho_grafico) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(ano, mes) DO UPDATE SET "
                "data_processamento = excluded.data_processamento, "
                "caminho_grafico = excluded.caminho_grafico",
                (ano, mes, data_processamento, caminho_grafico),
            )
            conn.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao marcar mês como processado: {e}") from e


def meses_ja_processados() -> set:
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT ano, mes FROM meses_processados")
            return {(r["ano"], r["mes"]) for r in cur.fetchall()}
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao consultar meses processados: {e}") from e


def caminho_grafico_do_mes(ano: int, mes: int) -> Optional[str]:
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT caminho_grafico FROM meses_processados WHERE ano = ? AND mes = ?",
                (ano, mes),
            )
            row = cur.fetchone()
            return row["caminho_grafico"] if row else None
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao consultar gráfico do mês: {e}") from e


def tabela_anual(ano: int) -> List[dict]:
    """
    Monta a tabela do ano inteiro (12 meses), com total de visitantes e
    quantidade de eventos/cultos distintos por mês, usando os dados reais
    e mais atualizados de `visitantes` (não depende do cache ter rodado).
    """
    linhas = []
    for mes in range(1, 13):
        inicio, fim = _intervalo_do_mes(ano, mes)
        try:
            with get_connection() as conn:
                cur = conn.execute(
                    """
                    SELECT
                        COUNT(v.id) AS total_visitantes,
                        COUNT(DISTINCT COALESCE(e.id, -v.id)) AS qtd_eventos
                    FROM visitantes v
                    LEFT JOIN eventos e ON v.evento_id = e.id
                    WHERE v.data_cadastro BETWEEN ? AND ?
                    """,
                    (inicio, fim),
                )
                row = cur.fetchone()
        except sqlite3.Error as e:
            raise DatabaseError(f"Erro ao montar tabela anual ({MESES_PT[mes-1]}): {e}") from e

        total = row["total_visitantes"] or 0
        qtd_eventos = row["qtd_eventos"] or 0
        media = round(total / qtd_eventos, 1) if qtd_eventos else 0.0

        linhas.append(
            {
                "mes": mes,
                "nome_mes": MESES_PT[mes - 1],
                "total_visitantes": total,
                "qtd_eventos": qtd_eventos,
                "media_por_evento": media,
            }
        )
    return linhas


# ---------------------------------------------------------------------------
# Retenção / ano padrão de exibição
# ---------------------------------------------------------------------------

def ano_padrao_exibicao(hoje: Optional[date] = None) -> int:
    """
    Regra de retenção: o ano fechado (anterior) continua sendo exibido por
    padrão até 31/01 do ano novo (um mês de 'graça' para fechamento do
    relatório anual). A partir de 1º de fevereiro, o painel passa a exibir
    o ano corrente por padrão. Nenhum dado é apagado em nenhum momento;
    isso afeta apenas qual ano aparece selecionado ao abrir o painel —
    o usuário pode trocar de ano livremente a qualquer momento.
    """
    hoje = hoje or date.today()
    if hoje.month == 1:
        return hoje.year - 1
    return hoje.year


def _primeiro_mes_com_dados() -> Optional[Tuple[int, int]]:
    """Retorna (ano, mes) do primeiro visitante cadastrado, ou None se não houver nenhum."""
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT MIN(data_cadastro) AS primeira FROM visitantes"
            )
            row = cur.fetchone()
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao consultar primeiro cadastro: {e}") from e

    if not row or not row["primeira"]:
        return None
    ano = int(row["primeira"][0:4])
    mes = int(row["primeira"][5:7])
    return ano, mes


def meses_pendentes_de_processamento(hoje: Optional[date] = None) -> List[Tuple[int, int]]:
    """
    Retorna a lista de (ano, mes) de meses já COMPLETOS (terminaram antes de
    hoje) que ainda não têm relatório processado, para o app gerar
    automaticamente ao abrir ('todo final de mês'). O ponto de partida é o
    mês do primeiro visitante já cadastrado (nunca antes disso, para não
    gerar dezenas de gráficos vazios em uma instalação nova); no máximo
    olha 24 meses para trás, como limite de segurança.
    """
    hoje = hoje or date.today()

    inicio = _primeiro_mes_com_dados()
    if inicio is None:
        return []  # nenhum visitante cadastrado ainda: nada a processar

    processados = meses_ja_processados()
    pendentes = []

    ano, mes = hoje.year, hoje.month
    for _ in range(24):
        mes -= 1
        if mes == 0:
            mes = 12
            ano -= 1
        if (ano, mes) < inicio:
            break
        if (ano, mes) not in processados:
            pendentes.append((ano, mes))

    pendentes.reverse()  # do mais antigo para o mais recente
    return pendentes
