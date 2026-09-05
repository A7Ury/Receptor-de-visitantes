"""
app.py
Sistema de Contabilização de Visitantes - Igreja e Eventos.

Interface gráfica (Tkinter) para cadastrar visitantes (nome e telefone),
associá-los a eventos e visualizar/exportar a lista cadastrada.

Executar com:  python3 app.py
"""

import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date

import database as db
from validadores import validar_nome, validar_telefone, formatar_telefone


class VisitantesApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Contabilização de Visitantes - Igreja e Eventos")
        self.geometry("880x600")
        self.minsize(760, 520)

        try:
            db.init_db()
        except db.DatabaseError as e:
            messagebox.showerror("Erro no banco de dados", str(e))
            self.destroy()
            return

        self.evento_atual_id: int | None = None
        self._construir_interface()
        self._atualizar_lista()

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------

    def _construir_interface(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        self._construir_bloco_evento(container)
        self._construir_bloco_cadastro(container)
        self._construir_bloco_lista(container)
        self._construir_barra_status(container)

    def _construir_bloco_evento(self, pai: ttk.Frame) -> None:
        frame = ttk.LabelFrame(pai, text="Evento", padding=10)
        frame.pack(fill="x", pady=(0, 10))

        ttk.Label(frame, text="Nome do evento:").grid(row=0, column=0, sticky="w")
        self.entry_evento_nome = ttk.Entry(frame, width=30)
        self.entry_evento_nome.grid(row=0, column=1, padx=6, sticky="w")
        self.entry_evento_nome.insert(0, "Culto de Domingo")

        ttk.Label(frame, text="Data (AAAA-MM-DD):").grid(row=0, column=2, sticky="w", padx=(12, 0))
        self.entry_evento_data = ttk.Entry(frame, width=14)
        self.entry_evento_data.grid(row=0, column=3, padx=6, sticky="w")
        self.entry_evento_data.insert(0, date.today().isoformat())

        ttk.Button(
            frame, text="Definir evento ativo", command=self._definir_evento_ativo
        ).grid(row=0, column=4, padx=(12, 0))

        self.label_evento_ativo = ttk.Label(
            frame, text="Nenhum evento ativo definido.", foreground="#555"
        )
        self.label_evento_ativo.grid(row=1, column=0, columnspan=5, sticky="w", pady=(8, 0))

    def _construir_bloco_cadastro(self, pai: ttk.Frame) -> None:
        frame = ttk.LabelFrame(pai, text="Cadastrar visitante", padding=10)
        frame.pack(fill="x", pady=(0, 10))

        ttk.Label(frame, text="Nome:").grid(row=0, column=0, sticky="w")
        self.entry_nome = ttk.Entry(frame, width=32)
        self.entry_nome.grid(row=0, column=1, padx=6, sticky="w")

        ttk.Label(frame, text="Telefone:").grid(row=0, column=2, sticky="w", padx=(12, 0))
        self.entry_telefone = ttk.Entry(frame, width=20)
        self.entry_telefone.grid(row=0, column=3, padx=6, sticky="w")

        ttk.Label(frame, text="Observações:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.entry_obs = ttk.Entry(frame, width=60)
        self.entry_obs.grid(row=1, column=1, columnspan=3, padx=6, sticky="we", pady=(6, 0))

        ttk.Button(
            frame, text="Cadastrar visitante", command=self._cadastrar_visitante
        ).grid(row=0, column=4, rowspan=2, padx=(12, 0), sticky="ns")

        self.entry_nome.bind("<Return>", lambda e: self.entry_telefone.focus())
        self.entry_telefone.bind("<Return>", lambda e: self._cadastrar_visitante())

    def _construir_bloco_lista(self, pai: ttk.Frame) -> None:
        frame = ttk.LabelFrame(pai, text="Visitantes cadastrados", padding=10)
        frame.pack(fill="both", expand=True)

        barra_busca = ttk.Frame(frame)
        barra_busca.pack(fill="x", pady=(0, 8))

        ttk.Label(barra_busca, text="Buscar por nome:").pack(side="left")
        self.entry_busca = ttk.Entry(barra_busca, width=30)
        self.entry_busca.pack(side="left", padx=6)
        self.entry_busca.bind("<KeyRelease>", lambda e: self._atualizar_lista())

        ttk.Button(barra_busca, text="Excluir selecionado", command=self._excluir_selecionado).pack(
            side="left", padx=(12, 0)
        )
        ttk.Button(barra_busca, text="Exportar CSV", command=self._exportar_csv).pack(
            side="left", padx=(6, 0)
        )

        colunas = ("nome", "telefone", "evento", "data_cadastro", "observacoes")
        self.tree = ttk.Treeview(frame, columns=colunas, show="headings", height=14)
        for col, titulo, largura in [
            ("nome", "Nome", 160),
            ("telefone", "Telefone", 130),
            ("evento", "Evento", 160),
            ("data_cadastro", "Cadastrado em", 150),
            ("observacoes", "Observações", 200),
        ]:
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=largura, anchor="w")

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # guarda o id real do banco por linha (iid da Treeview == id do visitante)

    def _construir_barra_status(self, pai: ttk.Frame) -> None:
        self.label_status = ttk.Label(pai, text="", foreground="#333")
        self.label_status.pack(fill="x", pady=(8, 0))

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def _definir_evento_ativo(self) -> None:
        nome = self.entry_evento_nome.get()
        data_evento = self.entry_evento_data.get().strip()

        if not nome.strip():
            messagebox.showwarning("Evento", "Informe o nome do evento.")
            return

        try:
            date.fromisoformat(data_evento)
        except ValueError:
            messagebox.showwarning("Evento", "Data inválida. Use o formato AAAA-MM-DD.")
            return

        try:
            evento_id = db.criar_ou_obter_evento(nome, data_evento)
        except (db.DatabaseError, ValueError) as e:
            messagebox.showerror("Erro", str(e))
            return

        self.evento_atual_id = evento_id
        self.label_evento_ativo.config(
            text=f"Evento ativo: {nome.strip()} ({data_evento})", foreground="#0a6"
        )
        self._atualizar_lista()

    def _cadastrar_visitante(self) -> None:
        try:
            nome = validar_nome(self.entry_nome.get())
            telefone_digitos = validar_telefone(self.entry_telefone.get())
        except ValueError as e:
            messagebox.showwarning("Dados inválidos", str(e))
            return

        observacoes = self.entry_obs.get().strip()

        try:
            db.cadastrar_visitante(
                nome=nome,
                telefone=telefone_digitos,
                evento_id=self.evento_atual_id,
                observacoes=observacoes,
            )
        except (db.DatabaseError, ValueError) as e:
            messagebox.showerror("Erro ao cadastrar", str(e))
            return

        self.entry_nome.delete(0, tk.END)
        self.entry_telefone.delete(0, tk.END)
        self.entry_obs.delete(0, tk.END)
        self.entry_nome.focus()

        self._atualizar_lista()
        self.label_status.config(text=f"Visitante '{nome}' cadastrado com sucesso.")

    def _atualizar_lista(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        filtro = self.entry_busca.get() if hasattr(self, "entry_busca") else ""

        try:
            registros = db.listar_visitantes(filtro_nome=filtro)
            total = db.contar_visitantes()
        except db.DatabaseError as e:
            messagebox.showerror("Erro ao carregar dados", str(e))
            return

        for r in registros:
            evento_txt = r["evento_nome"] or "-"
            self.tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    r["nome"],
                    formatar_telefone(r["telefone"]),
                    evento_txt,
                    r["data_cadastro"],
                    r["observacoes"] or "",
                ),
            )

        self.label_status.config(text=f"Total de visitantes cadastrados: {total}")

    def _excluir_selecionado(self) -> None:
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showinfo("Excluir", "Selecione um visitante na lista primeiro.")
            return

        if not messagebox.askyesno("Confirmar exclusão", "Deseja realmente excluir o visitante selecionado?"):
            return

        visitante_id = int(selecionado[0])
        try:
            db.excluir_visitante(visitante_id)
        except db.DatabaseError as e:
            messagebox.showerror("Erro ao excluir", str(e))
            return

        self._atualizar_lista()

    def _exportar_csv(self) -> None:
        caminho = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Arquivo CSV", "*.csv")],
            initialfile="visitantes.csv",
            title="Exportar visitantes para CSV",
        )
        if not caminho:
            return

        try:
            registros = db.listar_visitantes(filtro_nome=self.entry_busca.get())
        except db.DatabaseError as e:
            messagebox.showerror("Erro ao exportar", str(e))
            return

        try:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Nome", "Telefone", "Evento", "Data do evento", "Cadastrado em", "Observações"])
                for r in registros:
                    writer.writerow(
                        [
                            r["nome"],
                            formatar_telefone(r["telefone"]),
                            r["evento_nome"] or "",
                            r["data_evento"] or "",
                            r["data_cadastro"],
                            r["observacoes"] or "",
                        ]
                    )
        except OSError as e:
            messagebox.showerror("Erro ao salvar arquivo", str(e))
            return

        messagebox.showinfo("Exportação concluída", f"Arquivo salvo em:\n{caminho}")


def main() -> None:
    app = VisitantesApp()
    app.mainloop()


if __name__ == "__main__":
    main()
