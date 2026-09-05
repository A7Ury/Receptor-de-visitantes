"""
graficos.py
Geração do gráfico mensal (visitantes por evento/culto) usando matplotlib.

Este módulo isola toda a dependência do matplotlib, para que o restante
do app trate um eventual erro de importação de forma controlada.
"""

from pathlib import Path
from typing import List, Optional

try:
    import matplotlib
    matplotlib.use("Agg")  # backend seguro para salvar arquivo sem precisar de tela
    import matplotlib.pyplot as plt
    MATPLOTLIB_DISPONIVEL = True
except ImportError:
    MATPLOTLIB_DISPONIVEL = False


class GraficoError(Exception):
    """Erro ao gerar ou salvar um gráfico."""
    pass


def _verificar_matplotlib() -> None:
    if not MATPLOTLIB_DISPONIVEL:
        raise GraficoError(
            "A biblioteca 'matplotlib' não está instalada. "
            "Instale com: pip install matplotlib"
        )


def gerar_figura_mensal(
    nome_igreja: str,
    ano: int,
    mes: int,
    nome_mes: str,
    linhas,
):
    """
    Monta e retorna uma Figure do matplotlib com o gráfico de barras de
    visitantes por evento/culto do mês. Não salva em disco (isso é feito
    por `salvar_grafico_mensal` ou pela tela que embute a figura).
    `linhas` é uma lista de objetos com 'evento_nome', 'data_evento' e 'total'
    (aceita sqlite3.Row ou dict).
    """
    _verificar_matplotlib()

    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=110)

    if not linhas:
        ax.text(
            0.5, 0.5,
            "Nenhum visitante cadastrado neste mês.",
            ha="center", va="center", fontsize=13, color="#666",
            transform=ax.transAxes,
        )
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        rotulos = []
        totais = []
        for linha in linhas:
            evento_nome = linha["evento_nome"] if not isinstance(linha, dict) else linha.get("evento_nome")
            data_evento = linha["data_evento"] if not isinstance(linha, dict) else linha.get("data_evento")
            total = linha["total"] if not isinstance(linha, dict) else linha.get("total")
            rotulo = evento_nome if not data_evento else f"{evento_nome}\n({data_evento})"
            rotulos.append(rotulo)
            totais.append(total)

        cores = ["#2e7d32" if t == max(totais) else "#4a90d9" for t in totais]
        barras = ax.bar(rotulos, totais, color=cores)
        ax.set_ylabel("Nº de visitantes")
        ax.set_ylim(0, max(totais) * 1.2 + 1)

        for barra, total in zip(barras, totais):
            ax.annotate(
                str(total),
                xy=(barra.get_x() + barra.get_width() / 2, barra.get_height()),
                xytext=(0, 4), textcoords="offset points",
                ha="center", va="bottom", fontsize=10, fontweight="bold",
            )

        plt.setp(ax.get_xticklabels(), rotation=20, ha="right", fontsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    total_geral = sum(
        (linha["total"] if not isinstance(linha, dict) else linha.get("total", 0))
        for linha in linhas
    ) if linhas else 0

    ax.set_title(
        f"{nome_igreja}\nVisitantes por evento/culto — {nome_mes}/{ano}  "
        f"(total do mês: {total_geral})",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout()
    return fig


def salvar_grafico_mensal(
    nome_igreja: str,
    ano: int,
    mes: int,
    nome_mes: str,
    linhas,
    pasta_saida: Path,
) -> str:
    """Gera o gráfico do mês e salva como PNG. Retorna o caminho salvo (string)."""
    _verificar_matplotlib()

    try:
        pasta_saida.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise GraficoError(f"Não foi possível criar a pasta de relatórios: {e}") from e

    fig = gerar_figura_mensal(nome_igreja, ano, mes, nome_mes, linhas)
    caminho = pasta_saida / f"{mes:02d}_{nome_mes.lower()}_grafico.png"

    try:
        fig.savefig(str(caminho))
    except OSError as e:
        raise GraficoError(f"Não foi possível salvar o gráfico: {e}") from e
    finally:
        plt.close(fig)

    return str(caminho)
