"""
database.py
Camada de acesso a dados (SQLite) para o Sistema de Contabilização
de Visitantes da Igreja.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# Caminho do banco de dados: fica na mesma pasta do aplicativo
DB_PATH = Path(__file__).resolve().parent / "visitantes.db"


class DatabaseError(Exception):
    """Erro genérico da camada de banco de dados."""
    pass


def get_connection() -> sqlite3.Connection:
    """
    Cria e retorna uma conexão com o banco de dados SQLite.
    Ativa o suporte a chaves estrangeiras.
    """
    try:
        # timeout maior + modo WAL: permite que o app de cadastro e o
        # painel de relatórios acessem o mesmo arquivo .db ao mesmo tempo
        # sem erros de "database is locked".
        conn = sqlite3.connect(str(DB_PATH), timeout=15)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao conectar ao banco de dados: {e}") from e


def init_db() -> None:
    """
    Cria as tabelas do banco de dados caso ainda não existam.
    Deve ser chamada uma vez na inicialização do aplicativo.
    """
    schema = """
    CREATE TABLE IF NOT EXISTS eventos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        data_evento TEXT NOT NULL,
        UNIQUE(nome, data_evento)
    );

    CREATE TABLE IF NOT EXISTS visitantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        telefone TEXT NOT NULL,
        evento_id INTEGER,
        data_cadastro TEXT NOT NULL,
        observacoes TEXT,
        FOREIGN KEY (evento_id) REFERENCES eventos(id)
            ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_visitantes_nome ON visitantes(nome);
    CREATE INDEX IF NOT EXISTS idx_visitantes_evento ON visitantes(evento_id);
    """
    try:
        with get_connection() as conn:
            conn.executescript(schema)
            conn.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao inicializar o banco de dados: {e}") from e


# ---------------------------------------------------------------------------
# Eventos
# ---------------------------------------------------------------------------

def criar_ou_obter_evento(nome: str, data_evento: str) -> int:
    """
    Cria um evento se ele ainda não existir (mesmo nome + data),
    ou retorna o id do já existente.
    """
    nome = nome.strip()
    data_evento = data_evento.strip()
    if not nome:
        raise ValueError("O nome do evento não pode estar vazio.")

    try:
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT id FROM eventos WHERE nome = ? AND data_evento = ?",
                (nome, data_evento),
            )
            row = cur.fetchone()
            if row:
                return row["id"]

            cur = conn.execute(
                "INSERT INTO eventos (nome, data_evento) VALUES (?, ?)",
                (nome, data_evento),
            )
            conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao criar/obter evento: {e}") from e


def listar_eventos() -> List[sqlite3.Row]:
    """Retorna todos os eventos cadastrados, mais recentes primeiro."""
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "SELECT id, nome, data_evento FROM eventos "
                "ORDER BY data_evento DESC, nome ASC"
            )
            return cur.fetchall()
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao listar eventos: {e}") from e


# ---------------------------------------------------------------------------
# Visitantes
# ---------------------------------------------------------------------------

def cadastrar_visitante(
    nome: str,
    telefone: str,
    evento_id: Optional[int] = None,
    observacoes: str = "",
) -> int:
    """
    Cadastra um novo visitante no banco de dados.
    Retorna o id do registro criado.
    """
    nome = nome.strip()
    telefone = telefone.strip()

    if not nome:
        raise ValueError("O nome do visitante é obrigatório.")
    if not telefone:
        raise ValueError("O telefone do visitante é obrigatório.")

    data_cadastro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO visitantes (nome, telefone, evento_id, data_cadastro, observacoes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (nome, telefone, evento_id, data_cadastro, observacoes.strip()),
            )
            conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao cadastrar visitante: {e}") from e


def listar_visitantes(
    filtro_nome: str = "",
    evento_id: Optional[int] = None,
) -> List[sqlite3.Row]:
    """
    Lista visitantes cadastrados, com filtro opcional por nome
    (busca parcial, case-insensitive) e/ou por evento.
    """
    query = """
        SELECT v.id, v.nome, v.telefone, v.data_cadastro, v.observacoes,
               e.nome AS evento_nome, e.data_evento
        FROM visitantes v
        LEFT JOIN eventos e ON v.evento_id = e.id
        WHERE 1=1
    """
    params: List = []

    if filtro_nome.strip():
        query += " AND v.nome LIKE ?"
        params.append(f"%{filtro_nome.strip()}%")

    if evento_id is not None:
        query += " AND v.evento_id = ?"
        params.append(evento_id)

    query += " ORDER BY v.data_cadastro DESC"

    try:
        with get_connection() as conn:
            cur = conn.execute(query, params)
            return cur.fetchall()
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao listar visitantes: {e}") from e


def contar_visitantes(evento_id: Optional[int] = None) -> int:
    """Retorna a contagem total de visitantes (opcionalmente por evento)."""
    try:
        with get_connection() as conn:
            if evento_id is not None:
                cur = conn.execute(
                    "SELECT COUNT(*) AS total FROM visitantes WHERE evento_id = ?",
                    (evento_id,),
                )
            else:
                cur = conn.execute("SELECT COUNT(*) AS total FROM visitantes")
            return cur.fetchone()["total"]
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao contar visitantes: {e}") from e


def excluir_visitante(visitante_id: int) -> None:
    """Exclui um visitante pelo id."""
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM visitantes WHERE id = ?", (visitante_id,))
            conn.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Erro ao excluir visitante: {e}") from e
