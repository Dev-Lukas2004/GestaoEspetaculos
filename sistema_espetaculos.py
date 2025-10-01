# sistema_espetaculos.py
import customtkinter as ctk
import pandas as pd
from tkinter import messagebox, filedialog
from datetime import datetime, timedelta
import os
import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import shutil
from PIL import Image
import threading

from database import Database

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, "assets", relative_path)

NOME_ARQUIVO_EXCEL_PADRAO = "ArquivoAnual_anaceci.xlsx"
NOME_BANCO_DADOS = "gestao_espetaculos.db"

DIAS_SEMANA_MAP = {
    "Segunda": 0, "Terça": 1, "Quarta": 2,
    "Quinta": 3, "Sexta": 4, "Sábado": 5, "Domingo": 6
}
DIAS_SEMANA_PT = {
    0: "segunda-feira", 1: "terça-feira", 2: "quarta-feira", 3: "quinta-feira",
    4: "sexta-feira", 5: "sábado", 6: "domingo"
}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.db = Database()
        self.db.criar_tabela()
        self.title("ShowManager - Sistema de Gestão de Espetáculos")
        self.geometry("1300x850")

        ctk.set_appearance_mode("dark")

        self.COLORS = {
            "bg_dark": "#202124", "bg_light": "#2D2F34", "frame": "#2D2F34",
            "text": "#EAEAEA", "text_secondary": "#B0B0B0", "primary": "#42B883",
            "primary_hover": "#4FD89D", "danger": "#E57373", "danger_hover": "#EF5350",
            "header": "#37393F", "status_bar": "#37393F"
        }
        self.FONTS = {
            "title": ctk.CTkFont(family="Poppins", size=24, weight="bold"),
            "header": ctk.CTkFont(family="Poppins", size=14, weight="bold"),
            "body": ctk.CTkFont(family="Poppins", size=13),
            "body_bold": ctk.CTkFont(family="Poppins", size=13, weight="bold"),
        }
        self.configure(fg_color=self.COLORS["bg_dark"])

        self.ICONS = self._load_icons()
        self.figura_atual = None
        self.status_bar_job = None
        self.debounce_job = None

        self._criar_interface()

    def _load_icons(self):
        icons = {}
        icon_files = {
            "register": "register_icon.png", "history": "history_icon.png", "charts": "charts_icon.png",
            "search": "search_icon.png", "clear": "clear_icon.png", "excel": "excel_icon.png",
            "backup": "backup_icon.png", "delete": "delete_icon.png", "edit": "edit_icon.png",
            "pdf": "pdf_icon.png", "add": "add_icon.png"
        }
        for name, filename in icon_files.items():
            try:
                path = resource_path(filename)
                icons[name] = ctk.CTkImage(Image.open(path), size=(20, 20))
            except FileNotFoundError:
                print(f"Aviso: Ícone '{filename}' não encontrado.")
                icons[name] = None
        return icons

    def _criar_interface(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=(20, 0))

        self.tab_view = ctk.CTkTabview(
            self.main_frame, corner_radius=10, fg_color=self.COLORS["bg_light"],
            segmented_button_fg_color=self.COLORS["bg_light"],
            segmented_button_selected_color=self.COLORS["primary"],
            segmented_button_selected_hover_color=self.COLORS["primary_hover"],
            segmented_button_unselected_color=self.COLORS["frame"],
        )
        self.tab_view.pack(fill="both", expand=True)

        self.status_bar = ctk.CTkLabel(self, text="Pronto", font=self.FONTS["body"],
                                       text_color=self.COLORS["text_secondary"], height=25,
                                       fg_color=self.COLORS["status_bar"])
        self.status_bar.pack(side="bottom", fill="x", padx=1, pady=1)

        self.tab_view.add("Registrar Evento")
        self.tab_view.add("Histórico de Sessões")
        self.tab_view.add("Painel de Gráficos")

        self.criar_aba_registro()
        self.criar_aba_historico()
        self.criar_aba_graficos()
        self.tab_view.set("Registrar Evento")

    def update_status(self, message, clear_after=5000):
        self.status_bar.configure(text=message)
        if self.status_bar_job:
            self.status_bar.after_cancel(self.status_bar_job)
        self.status_bar_job = self.status_bar.after(clear_after, self.clear_status)

    def clear_status(self):
        self.status_bar.configure(text="Pronto")

    def _formatar_data(self, event):
        entry = event.widget
        pos = entry.index(ctk.INSERT)
        text = entry.get()
        digits_before_cursor = len("".join(filter(str.isdigit, text[:pos])))
        digits = "".join(filter(str.isdigit, text))[:8]
        new_text = ""
        if len(digits) > 0: new_text += digits[:2]
        if len(digits) > 2: new_text += "/" + digits[2:4]
        if len(digits) > 4: new_text += "/" + digits[4:]
        if new_text != text:
            new_pos = 0
            digits_counted = 0
            for char in new_text:
                if digits_counted == digits_before_cursor: break
                if char.isdigit(): digits_counted += 1
                new_pos += 1
            entry.delete(0, 'end')
            entry.insert(0, new_text)
            entry.icursor(new_pos)

    def _on_filtro_key_release(self, event=None):
        if self.debounce_job:
            self.after_cancel(self.debounce_job)
        if self.filtro_nome.get().strip():
             self.debounce_job = self.after(500, self.atualizar_historico)
        else:
            self.limpar_resultados_historico()


    def criar_aba_registro(self):
        frame = self.tab_view.tab("Registrar Evento")
        frame.configure(fg_color="transparent")
        ctk.CTkLabel(frame, text="Registrar Novo Espetáculo", font=self.FONTS["title"], text_color=self.COLORS["text"]).pack(pady=(10, 20))
        input_frame = ctk.CTkFrame(frame, corner_radius=10, fg_color=self.COLORS["frame"])
        input_frame.pack(padx=10, pady=10, fill="x", expand=True)
        self.entry_nome_evento = ctk.CTkEntry(input_frame, placeholder_text="Nome do Evento", font=self.FONTS["body"], height=40, corner_radius=8)
        self.entry_nome_evento.pack(pady=10, padx=10, fill="x")
        self.combo_sala = ctk.CTkComboBox(input_frame, values=["Arena", "Multiuso", "Mezanino"], font=self.FONTS["body"], height=40, state="readonly", corner_radius=8, button_color=self.COLORS["primary"])
        self.combo_sala.set("Selecione a Sala")
        self.combo_sala.pack(pady=10, padx=10, fill="x")
        datas_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        datas_frame.pack(pady=10, padx=10, fill="x", expand=True)
        datas_frame.grid_columnconfigure((0, 1), weight=1)
        self.entry_data_inicio = ctk.CTkEntry(datas_frame, placeholder_text="Data de Início (DD/MM/AAAA)", font=self.FONTS["body"], height=40, corner_radius=8)
        self.entry_data_inicio.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.entry_data_inicio.bind("<KeyRelease>", self._formatar_data)
        self.entry_data_fim = ctk.CTkEntry(datas_frame, placeholder_text="Data de Fim (DD/MM/AAAA)", font=self.FONTS["body"], height=40, corner_radius=8)
        self.entry_data_fim.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        self.entry_data_fim.bind("<KeyRelease>", self._formatar_data)
        dias_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        dias_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(dias_frame, text="Selecione os dias da semana:", font=self.FONTS["header"], text_color=self.COLORS["text_secondary"]).pack(pady=(10, 5))
        self.vars_dias = {dia: ctk.BooleanVar() for dia in DIAS_SEMANA_MAP}
        checkbox_container = ctk.CTkFrame(dias_frame, fg_color="transparent")
        checkbox_container.pack(pady=5)
        for dia in self.vars_dias:
            ctk.CTkCheckBox(checkbox_container, text=dia, variable=self.vars_dias[dia], font=self.FONTS["body"], fg_color=self.COLORS["primary"], hover_color=self.COLORS["primary_hover"]).pack(side="left", padx=10)
        ctk.CTkButton(frame, text="Definir Públicos por Sessão", height=45, font=self.FONTS["header"], corner_radius=8, command=self.abrir_janela_edicao_publico, image=self.ICONS.get("add"), fg_color=self.COLORS["primary"], hover_color=self.COLORS["primary_hover"]).pack(pady=20)

    def abrir_janela_edicao_publico(self):
        try:
            nome = self.entry_nome_evento.get().strip()
            sala = self.combo_sala.get()
            data_inicio = datetime.strptime(self.entry_data_inicio.get().strip(), "%d/%m/%Y")
            data_fim = datetime.strptime(self.entry_data_fim.get().strip(), "%d/%m/%Y")
            dias_int = [DIAS_SEMANA_MAP[dia] for dia, var in self.vars_dias.items() if var.get()]
        except ValueError:
            messagebox.showerror("Erro de Formato", "Preencha todos os campos corretamente. Datas devem estar no formato DD/MM/AAAA.")
            return
        if not nome or sala == "Selecione a Sala" or not dias_int:
            messagebox.showerror("Campos Obrigatórios", "Preencha o nome do evento, sala e selecione ao menos um dia da semana.")
            return
        if data_inicio > data_fim:
            messagebox.showerror("Erro de Data", "A data de início não pode ser posterior à data de fim.")
            return
        sessoes_datas = [data_inicio + timedelta(days=x) for x in range((data_fim - data_inicio).days + 1) if (data_inicio + timedelta(days=x)).weekday() in dias_int]
        if not sessoes_datas:
            messagebox.showwarning("Aviso", "Nenhuma sessão encontrada para os dias selecionados no período informado.")
            return

        win_edicao = ctk.CTkToplevel(self)
        win_edicao.title("Editar Público por Sessão")
        win_edicao.geometry("800x650")
        win_edicao.transient(self)
        win_edicao.grab_set()

        sessoes_entries = []

        def aplicar_preenchimento_rapido(tipo_publico, valor_str):
            try:
                valor = int(valor_str)
                for item in sessoes_entries:
                    item[tipo_publico].delete(0, 'end')
                    item[tipo_publico].insert(0, str(valor))
            except ValueError:
                messagebox.showerror("Erro", "Por favor, insira um número válido.", parent=win_edicao)

        quick_fill_frame = ctk.CTkFrame(win_edicao)
        quick_fill_frame.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(quick_fill_frame, text="Preenchimento Rápido:").pack(side="left", padx=10)
        quick_fill_entry = ctk.CTkEntry(quick_fill_frame, placeholder_text="Valor", width=80)
        quick_fill_entry.pack(side="left", padx=5)
        ctk.CTkButton(quick_fill_frame, text="Aplicar a PCG", height=25, command=lambda: aplicar_preenchimento_rapido('entry_pcg', quick_fill_entry.get())).pack(side="left", padx=5)
        ctk.CTkButton(quick_fill_frame, text="Aplicar a Com.", height=25, command=lambda: aplicar_preenchimento_rapido('entry_com', quick_fill_entry.get())).pack(side="left", padx=5)
        ctk.CTkButton(quick_fill_frame, text="Aplicar a Adv.", height=25, command=lambda: aplicar_preenchimento_rapido('entry_adv', quick_fill_entry.get())).pack(side="left", padx=5)

        scroll_frame = ctk.CTkScrollableFrame(win_edicao, label_text=f"Sessões para: {nome}")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
        headers = ["Data", "Dia da Semana", "Público PCG", "Público Comerciário", "Público Adversos"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(scroll_frame, text=h, font=self.FONTS["header"]).grid(row=0, column=i, padx=10, pady=5)

        for idx, data_sessao in enumerate(sessoes_datas):
            row = idx + 1
            ctk.CTkLabel(scroll_frame, text=data_sessao.strftime('%d/%m/%Y')).grid(row=row, column=0, padx=10, pady=5)
            ctk.CTkLabel(scroll_frame, text=DIAS_SEMANA_PT[data_sessao.weekday()]).grid(row=row, column=1, padx=10, pady=5)
            entry_pcg = ctk.CTkEntry(scroll_frame, width=120); entry_pcg.grid(row=row, column=2, padx=5); entry_pcg.insert(0, "0")
            entry_com = ctk.CTkEntry(scroll_frame, width=120); entry_com.grid(row=row, column=3, padx=5); entry_com.insert(0, "0")
            entry_adv = ctk.CTkEntry(scroll_frame, width=120); entry_adv.grid(row=row, column=4, padx=5); entry_adv.insert(0, "0")
            sessoes_entries.append({"data": data_sessao, "entry_pcg": entry_pcg, "entry_com": entry_com, "entry_adv": entry_adv})

        ctk.CTkLabel(win_edicao, text="Observações Gerais:").pack(pady=(10,0))
        entry_obs = ctk.CTkEntry(win_edicao, width=400)
        entry_obs.pack(pady=5)
        btn_salvar = ctk.CTkButton(win_edicao, text="Salvar Todas as Sessões", command=lambda: self.salvar_sessoes_editadas(win_edicao, sessoes_entries, nome, sala, entry_obs.get().strip()))
        btn_salvar.pack(pady=20)

    def salvar_sessoes_editadas(self, win_edicao, sessoes_entries, nome, sala, obs):
        try:
            sessoes_para_salvar = []
            for item in sessoes_entries:
                pcg = int(item['entry_pcg'].get() or 0)
                com = int(item['entry_com'].get() or 0)
                adv = int(item['entry_adv'].get() or 0)
                data = item['data']
                sessoes_para_salvar.append({
                    "Dia": DIAS_SEMANA_PT[data.weekday()], "Data": data.strftime("%d/%m/%Y"),
                    "Nome_do_Evento": nome, "Sala": sala, "Publico_PCG": pcg, "Publico_Comerciario": com,
                    "Publico_Adversos": adv, "PCG_COM": pcg + com, "Total": pcg + com + adv, "Observacoes": obs
                })

            for sessao in sessoes_para_salvar:
                self.db.adicionar_sessao(sessao)

            self.update_status(f"{len(sessoes_para_salvar)} sessões registradas com sucesso.")
            win_edicao.destroy()

            # Limpa filtros e mostra apenas o evento recém-cadastrado
            self.filtro_sala.set("Todas as Salas")
            self.filtro_ano.set("")
            self.filtro_nome.delete(0, 'end')
            self.filtro_nome.insert(0, nome)

            self.tab_view.set("Histórico de Sessões")
            self.atualizar_historico()
            self.limpar_campos_registro()

        except ValueError:
            messagebox.showerror("Erro de Valor", "Os campos de público devem ser números inteiros.", parent=win_edicao)
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro ao salvar: {e}", parent=win_edicao)

    def limpar_campos_registro(self):
        self.entry_nome_evento.delete(0, 'end')
        self.combo_sala.set("Selecione a Sala")
        self.entry_data_inicio.delete(0, 'end')
        self.entry_data_fim.delete(0, 'end')
        for dia_var in self.vars_dias.values():
            dia_var.set(False)
        self.entry_nome_evento.focus()

    def criar_aba_historico(self):
        frame = self.tab_view.tab("Histórico de Sessões")
        frame.configure(fg_color="transparent")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        controles_frame = ctk.CTkFrame(frame, fg_color=self.COLORS["frame"], corner_radius=10)
        controles_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        filtros_frame = ctk.CTkFrame(controles_frame, fg_color="transparent")
        filtros_frame.pack(fill="x", padx=5, pady=5)

        self.filtro_nome = ctk.CTkEntry(filtros_frame, placeholder_text="Digite o nome do evento para buscar...", height=35, corner_radius=8)
        self.filtro_nome.pack(side="left", padx=5, pady=5, expand=True, fill="x")
        self.filtro_nome.bind("<KeyRelease>", self._on_filtro_key_release)

        self.filtro_sala = ctk.CTkComboBox(filtros_frame, values=["Todas as Salas", "Arena", "Multiuso", "Mezanino"], state="readonly", height=35, corner_radius=8, command=lambda x: self.atualizar_historico(), button_color=self.COLORS["primary"])
        self.filtro_sala.set("Todas as Salas")
        self.filtro_sala.pack(side="left", padx=5, pady=5)

        ctk.CTkLabel(filtros_frame, text="Ano:", font=self.FONTS["body"]).pack(side="left", padx=(10, 5), pady=5)
        self.filtro_ano = ctk.CTkComboBox(filtros_frame, state="readonly", height=35, width=120, corner_radius=8, command=lambda x: self.atualizar_historico(), button_color=self.COLORS["primary"])
        self.filtro_ano.pack(side="left", padx=(0, 5), pady=5)

        botoes_acao_frame = ctk.CTkFrame(controles_frame, fg_color="transparent")
        botoes_acao_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkButton(botoes_acao_frame, text="Pesquisar", height=35, command=self.atualizar_historico, image=self.ICONS.get("search"), fg_color=self.COLORS["primary"], hover_color=self.COLORS["primary_hover"]).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(botoes_acao_frame, text="Limpar", height=35, command=self.limpar_filtros, image=self.ICONS.get("clear")).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(botoes_acao_frame, text="Gerar Planilha", height=35, command=self.exportar_excel, image=self.ICONS.get("excel")).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(botoes_acao_frame, text="Backup", height=35, command=self.fazer_backup, image=self.ICONS.get("backup")).pack(side="left", padx=5, pady=5)

        exclusao_frame = ctk.CTkFrame(controles_frame, fg_color="transparent")
        exclusao_frame.pack(fill="x", padx=5, pady=(5, 5))

        ctk.CTkLabel(exclusao_frame, text="Excluir Evento (visível na busca):", font=self.FONTS["header"]).pack(side="left", padx=(5, 10))
        self.combo_excluir_evento = ctk.CTkComboBox(exclusao_frame, width=300, height=35, state="readonly", values=["Selecione um evento"], corner_radius=8, button_color=self.COLORS["primary"])
        self.combo_excluir_evento.set("Selecione um evento")
        self.combo_excluir_evento.pack(side="left", padx=5)
        ctk.CTkButton(exclusao_frame, text="Excluir Evento", height=35, command=self.excluir_evento_em_lote, image=self.ICONS.get("delete"), fg_color=self.COLORS["danger"], hover_color=self.COLORS["danger_hover"]).pack(side="left", padx=5)

        self.historico_scroll = ctk.CTkScrollableFrame(frame, label_text="Resultados da Busca", label_font=self.FONTS["header"], fg_color=self.COLORS["frame"], corner_radius=10)
        self.historico_scroll.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        # CORREÇÃO: Usa .grid() para a mensagem inicial
        label_inicial = ctk.CTkLabel(self.historico_scroll, text="Use os filtros acima e clique em 'Pesquisar' para buscar um evento.", font=self.FONTS["body"])
        label_inicial.grid(row=0, column=0, pady=20, padx=20)


    def limpar_resultados_historico(self):
        for w in self.historico_scroll.winfo_children():
            w.destroy()
        # CORREÇÃO: Usa .grid() para a mensagem de limpeza
        label_limpo = ctk.CTkLabel(self.historico_scroll, text="Use os filtros e clique em 'Pesquisar' para buscar.", font=self.FONTS["body"])
        label_limpo.grid(row=0, column=0, pady=20)
        self.combo_excluir_evento.configure(values=["Nenhum evento na busca"])
        self.combo_excluir_evento.set("Nenhum evento na busca")

    def limpar_filtros(self):
        self.filtro_nome.delete(0, 'end')
        self.filtro_sala.set("Todas as Salas")
        self.filtro_ano.set('')
        self.limpar_resultados_historico()
        self.update_status("Filtros limpos.")


    def fazer_backup(self):
        if not os.path.exists(NOME_BANCO_DADOS):
            messagebox.showwarning("Backup", "Nenhum banco de dados encontrado.")
            return
        try:
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_base, extensao = os.path.splitext(NOME_BANCO_DADOS)
            backup_path = os.path.join(backup_dir, f"{nome_base}_backup_{timestamp}{extensao}")
            shutil.copy(NOME_BANCO_DADOS, backup_path)
            self.update_status("Backup do banco de dados criado com sucesso.")
            messagebox.showinfo("Backup", f"Backup criado com sucesso em:\n{os.path.abspath(backup_path)}")
        except Exception as e:
            messagebox.showerror("Erro de Backup", f"Não foi possível criar o backup: {e}")

    def carregar_dados(self, filtro_nome="", filtro_sala="", ano_selecionado=None):
        if self.tab_view.get() == "Painel de Gráficos":
            df = self.db.buscar_todas_sessoes()
        else:
            df = self.db.buscar_sessoes_filtradas(filtro_nome, filtro_sala, ano_selecionado)

        if not df.empty:
            df['Data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
            df.dropna(subset=['Data'], inplace=True)
            df['__sheet'] = 'db'
            df['__sheet_idx'] = df['id']
            df['sala'] = df['sala'].replace('Sala Multiuso', 'Multiuso')
            df.rename(columns={
                "dia_semana": "Dia", "nome_evento": "Nome do Evento", "sala": "Sala",
                "publico_pcg": "Publico PCG", "publico_comerciario": "Publico Comerciário",
                "publico_adversos": "Publico Adversos", "pcg_com": "PCG+COM.", "total": "Total",
                "observacoes": "Observações"}, inplace=True)
            cols_num = ['Publico PCG', 'Publico Comerciário', 'Publico Adversos', 'PCG+COM.', 'Total']
            for col in cols_num:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df

    def atualizar_historico(self, event=None):
        for w in self.historico_scroll.winfo_children():
            w.destroy()

        filtro_nome = self.filtro_nome.get().strip()
        filtro_sala = self.filtro_sala.get()
        ano_selecionado_str = self.filtro_ano.get()

        if not filtro_nome and filtro_sala == "Todas as Salas" and not ano_selecionado_str:
            self.limpar_resultados_historico()
            return

        filtro_sala_db = filtro_sala if filtro_sala != "Todas as Salas" else ""
        ano_selecionado = int(ano_selecionado_str) if ano_selecionado_str and ano_selecionado_str.isdigit() else None

        df = self.carregar_dados(filtro_nome, filtro_sala_db, ano_selecionado)

        anos_df = self.db.buscar_anos_disponiveis()
        if not anos_df.empty:
            anos_disponiveis = sorted(anos_df['ano'].unique(), reverse=True)
            if self.filtro_ano.cget("values") != [str(ano) for ano in anos_disponiveis]:
                self.filtro_ano.configure(values=[str(ano) for ano in anos_disponiveis])
            if ano_selecionado_str not in [str(a) for a in anos_disponiveis]:
                 self.filtro_ano.set(ano_selecionado_str if ano_selecionado_str else '')

        if not df.empty:
            eventos_unicos = sorted(df["Nome do Evento"].unique())
            self.combo_excluir_evento.configure(values=["Selecione um evento"] + eventos_unicos)
            self.combo_excluir_evento.set("Selecione um evento")
        else:
            self.combo_excluir_evento.configure(values=["Nenhum evento encontrado"])
            self.combo_excluir_evento.set("Nenhum evento encontrado")

        if df.empty:
            # CORREÇÃO: Usa .grid() para a mensagem de "nenhum dado"
            label_vazio = ctk.CTkLabel(self.historico_scroll, text="Nenhum dado encontrado para os filtros selecionados.", font=self.FONTS["body"])
            label_vazio.grid(row=0, column=0, pady=20)
            return

        df = df.sort_values(by="Data", ascending=False).reset_index(drop=True)

        headers = ["Data", "Dia", "Evento", "Sala", "PCG", "Com.", "Geral", "Total", "Ações"]
        column_configs = [
            {'weight': 0, 'minsize': 90}, {'weight': 0, 'minsize': 100}, {'weight': 1, 'minsize': 300},
            {'weight': 0, 'minsize': 90}, {'weight': 0, 'minsize': 40}, {'weight': 0, 'minsize': 40},
            {'weight': 0, 'minsize': 40}, {'weight': 0, 'minsize': 50}, {'weight': 0, 'minsize': 110},
        ]
        for i, config in enumerate(column_configs):
            self.historico_scroll.grid_columnconfigure(i, weight=config['weight'], minsize=config['minsize'])

        header_bg_color = self.COLORS["header"]
        for i, h in enumerate(headers):
            cell_frame = ctk.CTkFrame(self.historico_scroll, fg_color=header_bg_color, corner_radius=0)
            cell_frame.grid(row=0, column=i, sticky="nsew", padx=(0,1), pady=(0,2))
            label = ctk.CTkLabel(cell_frame, text=h, font=self.FONTS["header"])
            label.pack(padx=10, pady=5, expand=True, fill="both")

        alt_row_color = ("#f2f2f2", self.COLORS["bg_light"])
        for idx, row_data in df.iterrows():
            row_color = alt_row_color[1] if idx % 2 == 0 else "transparent"
            unique_id = f"db|{int(row_data['__sheet_idx'])}"
            data_map = {
                0: row_data['Data'].strftime('%d/%m/%Y'), 1: row_data['Dia'], 2: row_data['Nome do Evento'],
                3: row_data['Sala'], 4: str(int(row_data['Publico PCG'])), 5: str(int(row_data['Publico Comerciário'])),
                6: str(int(row_data['Publico Adversos'])), 7: str(int(row_data['Total'])),
            }
            for col_idx in range(len(headers)):
                cell_frame = ctk.CTkFrame(self.historico_scroll, fg_color=row_color, corner_radius=0)
                cell_frame.grid(row=idx + 1, column=col_idx, sticky="nsew", padx=(0,1), pady=(0,1))
                if col_idx in data_map:
                    font = self.FONTS["body_bold"] if col_idx == 7 else self.FONTS["body"]
                    label = ctk.CTkLabel(cell_frame, text=data_map[col_idx], font=font)
                    anchor = "w" if col_idx < 4 else "center"
                    label.pack(padx=10, pady=3, expand=True, fill="both", anchor=anchor)
                elif col_idx == 8:
                    action_frame = ctk.CTkFrame(cell_frame, fg_color="transparent")
                    action_frame.pack(expand=True, fill="both", pady=2, padx=5)

                    edit_icon = self.ICONS.get("edit")
                    edit_text = "" if edit_icon else "✏️"
                    delete_icon = self.ICONS.get("delete")
                    delete_text = "" if delete_icon else "🗑️"

                    ctk.CTkButton(action_frame, text=edit_text, width=30, image=edit_icon, command=lambda uid=unique_id: self.editar_evento(uid)).pack(side='left', padx=3, expand=True)
                    ctk.CTkButton(action_frame, text=delete_text, width=30, image=delete_icon, fg_color=self.COLORS["danger"], hover_color=self.COLORS["danger_hover"], command=lambda uid=unique_id: self.excluir_evento(uid)).pack(side='left', padx=3, expand=True)

    def exportar_excel(self):
        df = self.db.buscar_todas_sessoes()
        if df.empty:
            messagebox.showwarning("Aviso", "Nenhum dado no banco de dados para exportar.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=NOME_ARQUIVO_EXCEL_PADRAO
        )
        if not file_path:
            return
        df['ano'] = pd.to_datetime(df['data'], dayfirst=True).dt.year
        df.rename(columns={
            "dia_semana": "Dia", "data": "Data", "nome_evento": "Nome do Evento",
            "sala": "Sala", "publico_pcg": "Publico PCG",
            "publico_comerciario": "Publico Comerciário", "publico_adversos": "Publico Adversos",
            "pcg_com": "PCG+COM.", "total": "Total", "observacoes": "Observações"
        }, inplace=True)
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                for ano, grupo in df.groupby('ano'):
                    sheet_name = f"Ano_{ano}"
                    grupo_final = grupo.drop(columns=['id', 'ano'])
                    grupo_final.to_excel(writer, sheet_name=sheet_name, index=False)
            self.update_status("Planilha Excel gerada com sucesso.")
            messagebox.showinfo("Sucesso", f"Planilha gerada com sucesso em:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Erro ao Exportar", f"Ocorreu um erro ao gerar a planilha: {e}")

    def excluir_evento_em_lote(self):
        evento_selecionado = self.combo_excluir_evento.get()
        if not evento_selecionado or evento_selecionado in ["Selecione um evento", "Nenhum evento encontrado", "Nenhum evento na busca"]:
            messagebox.showwarning("Aviso", "Por favor, selecione um evento válido para excluir.")
            return
        if not messagebox.askyesno("Confirmar Exclusão em Lote", f"Você tem CERTEZA que deseja excluir TODAS as sessões do evento:\n\n'{evento_selecionado}'?\n\nEsta ação não pode ser desfeita."):
            return
        try:
            self.db.excluir_evento_em_lote(evento_selecionado)
            self.update_status(f"Evento '{evento_selecionado}' excluído com sucesso.")
            self.limpar_filtros()
        except Exception as e:
            messagebox.showerror("Erro ao Excluir", f"Ocorreu um erro durante a exclusão em lote: {e}")

    def editar_evento(self, unique_id: str):
        try:
            _, id_str = unique_id.split('|')
            sessao_id = int(id_str)
        except (ValueError, IndexError):
            messagebox.showerror("Erro", "ID inválido para edição.")
            return
        row_data = self.db.buscar_sessao_por_id(sessao_id)
        if not row_data:
            messagebox.showerror("Erro", "Registro não encontrado. O histórico foi atualizado.")
            self.atualizar_historico()
            return

        win = ctk.CTkToplevel(self)
        win.title("Editar Sessão")
        win.geometry("520x350")
        win.transient(self)
        win.grab_set()

        def mk_entry(label_text, initial, rown):
            ctk.CTkLabel(win, text=label_text).grid(row=rown, column=0, sticky='w', padx=10, pady=6)
            ent = ctk.CTkEntry(win, width=300)
            ent.grid(row=rown, column=1, padx=10, pady=6)
            ent.insert(0, str(initial) if initial is not None else "")
            return ent
        e_nome = mk_entry("Nome do Evento:", row_data['nome_evento'], 0)
        e_data = mk_entry("Data (DD/MM/AAAA):", row_data['data'], 1)
        e_sala = mk_entry("Sala:", row_data['sala'], 2)
        e_pcg = mk_entry("Público PCG:", row_data['publico_pcg'], 3)
        e_com = mk_entry("Público Comerciário:", row_data['publico_comerciario'], 4)
        e_adv = mk_entry("Público Adversos:", row_data['publico_adversos'], 5)
        e_obs = mk_entry("Observações:", row_data['observacoes'], 6)

        def salvar_alteracoes():
            try:
                nova_data = datetime.strptime(e_data.get().strip(), '%d/%m/%Y')
                novo_pcg = int(e_pcg.get())
                novo_com = int(e_com.get())
                novo_adv = int(e_adv.get())
            except ValueError:
                messagebox.showerror("Erro", "Verifique o formato dos campos (datas DD/MM/AAAA e números).", parent=win)
                return
            dados_atualizados = {
                "Nome do Evento": e_nome.get().strip(), "Data": nova_data.strftime('%d/%m/%Y'),
                "Dia": DIAS_SEMANA_PT[nova_data.weekday()], "Sala": e_sala.get().strip(),
                "Publico PCG": novo_pcg, "Publico Comerciário": novo_com,
                "Publico Adversos": novo_adv, "PCG+COM.": novo_pcg + novo_com,
                "Total": novo_pcg + novo_com + novo_adv, "Observações": e_obs.get().strip()
            }
            try:
                self.db.atualizar_sessao(sessao_id, dados_atualizados)
                win.destroy()
                self.update_status("Sessão alterada com sucesso.")
                self.atualizar_historico()
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao salvar alterações: {e}", parent=win)
        ctk.CTkButton(win, text="Salvar", command=salvar_alteracoes).grid(row=8, column=0, pady=12, padx=10)
        ctk.CTkButton(win, text="Cancelar", command=win.destroy).grid(row=8, column=1, pady=12, padx=10)

    def excluir_evento(self, unique_id: str):
        try:
            _, id_str = unique_id.split('|')
            sessao_id = int(id_str)
        except Exception:
            messagebox.showerror("Erro", "ID inválido para exclusão.")
            return
        if not messagebox.askyesno("Confirmar", "Confirma exclusão desta sessão?"):
            return
        try:
            self.db.excluir_sessao_por_id(sessao_id)
            self.update_status("Sessão excluída com sucesso.")
            self.atualizar_historico()
        except Exception as e:
            messagebox.showerror("Erro ao excluir", f"Ocorreu um erro: {e}")

    def criar_aba_graficos(self):
        frame = self.tab_view.tab("Painel de Gráficos")
        frame.configure(fg_color="transparent")
        
        self.resumo_label = ctk.CTkLabel(frame, text="Visão Geral dos Dados", font=self.FONTS["title"], text_color=self.COLORS["text"])
        self.resumo_label.pack(pady=10)
        
        filtros_frame = ctk.CTkFrame(frame, fg_color=self.COLORS["frame"], corner_radius=10)
        filtros_frame.pack(fill="x", padx=10, pady=10)
        
        self.combo_tipo = ctk.CTkComboBox(filtros_frame, height=35, corner_radius=8, button_color=self.COLORS["primary"], values=[
            "Comparativo Mensal", "Comparativo Semestral", "Comparativo Anual",
            "Comparativo de Domingos", "Comparativo por Sala", "Comparativo de Salas por Mês"
        ])
        self.combo_tipo.pack(side="left", padx=5, pady=5)
        
        self.entry_ano1 = ctk.CTkEntry(filtros_frame, placeholder_text="Ano 1", width=100, height=35, corner_radius=8)
        self.entry_ano1.pack(side="left", padx=5, pady=5)
        
        self.entry_ano2 = ctk.CTkEntry(filtros_frame, placeholder_text="Ano 2", width=100, height=35, corner_radius=8)
        self.entry_ano2.pack(side="left", padx=5, pady=5)
        
        self.btn_gerar_grafico = ctk.CTkButton(filtros_frame, text="Gerar Gráficos", height=35, command=self.gerar_grafico, image=self.ICONS.get("charts"),
                      fg_color=self.COLORS["primary"], hover_color=self.COLORS["primary_hover"])
        self.btn_gerar_grafico.pack(side="left", padx=10, pady=5)
        
        ctk.CTkButton(filtros_frame, text="Exportar PDF", height=35, command=self.exportar_grafico_pdf, image=self.ICONS.get("pdf")).pack(side="left", padx=10, pady=5)
        
        self.graficos_container = ctk.CTkFrame(frame, fg_color=self.COLORS["frame"], corner_radius=10)
        self.graficos_container.pack(fill="both", expand=True, padx=10, pady=10)

    def gerar_grafico(self):
        self.btn_gerar_grafico.configure(state="disabled", text="Gerando...")
        for w in self.graficos_container.winfo_children():
            w.destroy()
        
        ctk.CTkLabel(self.graficos_container, text="Gerando gráficos, por favor aguarde...", font=self.FONTS["header"]).pack(pady=20)
        self.update_status("Carregando dados dos gráficos...", clear_after=10000)

        thread = threading.Thread(target=self._gerar_grafico_thread)
        thread.daemon = True
        thread.start()

    def _gerar_grafico_thread(self):
        try:
            ano1_str = self.entry_ano1.get()
            ano2_str = self.entry_ano2.get()
            if not ano1_str or not ano2_str:
                self.after(0, lambda: messagebox.showerror("Erro", "Por favor, digite os dois anos."))
                self.after(0, self.btn_gerar_grafico.configure, {"state": "normal", "text": "Gerar Gráficos"})
                return
            ano1 = int(ano1_str)
            ano2 = int(ano2_str)

            df = self.carregar_dados()
            if df.empty:
                self.after(0, lambda: messagebox.showerror("Erro", "Nenhum dado disponível."))
                self.after(0, self.btn_gerar_grafico.configure, {"state": "normal", "text": "Gerar Gráficos"})
                return

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            fig.patch.set_facecolor(self.COLORS["frame"])
            tipo = self.combo_tipo.get()
            
            self.plotar(ax1, df, ano1, tipo)
            self.plotar(ax2, df, ano2, tipo)
            fig.tight_layout(pad=3.0)
            self.figura_atual = fig

            self.after(0, self._exibir_grafico_concluido, fig, df)

        except ValueError:
            self.after(0, lambda: messagebox.showerror("Erro", "Digite anos válidos."))
            self.after(0, self.btn_gerar_grafico.configure, {"state": "normal", "text": "Gerar Gráficos"})
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erro Inesperado", f"Ocorreu um erro: {e}"))
            self.after(0, self.btn_gerar_grafico.configure, {"state": "normal", "text": "Gerar Gráficos"})
            self.after(0, self.clear_status)

    def _exibir_grafico_concluido(self, fig, df):
        self.btn_gerar_grafico.configure(state="normal", text="Gerar Gráficos")
        for w in self.graficos_container.winfo_children():
            w.destroy()
        
        total_publico = int(df['Total'].sum())
        sala_mais = df['Sala'].mode().iloc[0] if not df['Sala'].empty else 'N/A'
        resumo = f"Total de Registros: {len(df)} | Público Total (Geral): {total_publico} | Sala Mais Usada: {sala_mais}"
        self.resumo_label.configure(text=resumo, font=self.FONTS["header"])

        canvas = FigureCanvasTkAgg(fig, master=self.graficos_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self.update_status("Gráficos gerados com sucesso.")

    def exportar_grafico_pdf(self):
        if self.figura_atual is None:
            messagebox.showwarning("Aviso", "Nenhum gráfico foi gerado ainda. Gere um gráfico primeiro.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="grafico_espetaculos.pdf"
        )
        if not file_path:
            return
        try:
            self.figura_atual.savefig(file_path, format='pdf', bbox_inches='tight', facecolor=self.COLORS["frame"])
            self.update_status("Gráfico exportado para PDF com sucesso.")
            messagebox.showinfo("Sucesso", f"Gráfico exportado com sucesso para:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Erro ao Exportar", f"Ocorreu um erro ao exportar o gráfico: {e}")

    def plotar(self, ax, df, ano, tipo):
        df_ano = df[df['Data'].dt.year == ano]
        ax.clear()

        ax.set_facecolor(self.COLORS["frame"])
        ax.tick_params(colors=self.COLORS["text"], labelsize=10)
        for spine in ax.spines.values():
            spine.set_edgecolor(self.COLORS["text_secondary"])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.label.set_color(self.COLORS["text"])
        ax.xaxis.label.set_color(self.COLORS["text"])
        ax.title.set_color(self.COLORS["text"])

        if df_ano.empty:
            ax.text(0.5, 0.5, f"Sem dados para {ano}", ha='center', va='center', color=self.COLORS["text"])
            ax.set_title(f"Análise {ano}", color=self.COLORS["text"])
            return

        colors = ['#42B883', '#5E81AC', '#BF616A', '#D08770', '#EBCB8B']

        if tipo == "Comparativo de Salas por Mês":
            if 'Data' not in df_ano.columns: return
            df_ano.loc[:, 'Mes'] = df_ano['Data'].dt.month
            pivot_df = df_ano.pivot_table(index='Mes', columns='Sala', values='Total', aggfunc='sum', fill_value=0)
            
            todas_salas = ['Arena', 'Multiuso', 'Mezanino']
            for sala in todas_salas:
                if sala not in pivot_df.columns:
                    pivot_df[sala] = 0
            
            pivot_df = pivot_df[todas_salas].reindex(range(1, 13), fill_value=0)
            pivot_df.plot(kind='bar', ax=ax, stacked=False, color=colors[:len(todas_salas)], width=0.75)

            max_val = pivot_df.to_numpy().max()
            if max_val > 0:
                ax.set_ylim(top=max_val * 1.18)

            for container in ax.containers:
                ax.bar_label(container, labels=[f'{int(v)}' if v > 0 else '' for v in container.datavalues],
                             color=self.COLORS["text"], fontsize=8, rotation=90, padding=5)

            ax.set_title(f"Público por Sala/Mês - {ano}")
            ax.set_xlabel("Mês")
            ax.set_ylabel("Total de Público")
            meses_nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
            ax.set_xticklabels(meses_nomes, rotation=45, ha="right")
            leg = ax.legend(title="Salas", labelcolor=self.COLORS["text"], facecolor=self.COLORS["frame"], edgecolor='none')
            leg.get_title().set_color(self.COLORS["text"])

        elif tipo == "Comparativo Anual":
            totais = df_ano[['Publico PCG', 'Publico Comerciário', 'Publico Adversos']].sum()
            totais.index = ['PCG', 'Comerciário', 'Adversos']
            bars = totais.plot(kind='bar', ax=ax, rot=0, color=colors)
            ax.set_title(f"Público Total em {ano}")
            ax.set_ylabel("Total de Público")
            ax.bar_label(bars.containers[0], color=self.COLORS["text"], fontsize=10, padding=3)

        elif tipo == "Comparativo Mensal":
            totais_mes = df_ano.groupby(df_ano['Data'].dt.month)['Total'].sum().reindex(range(1,13), fill_value=0)
            bars = totais_mes.plot(kind='bar', ax=ax, color=colors[0])
            ax.set_title(f"Público Mensal em {ano}")
            ax.set_xlabel("Mês")
            ax.set_xticklabels(['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'], rotation=45, ha="right")
            ax.bar_label(bars.containers[0], color=self.COLORS["text"], fontsize=10, padding=3)

        elif tipo == "Comparativo Semestral":
            df_ano.loc[:, 'Sem'] = df_ano['Data'].dt.month.apply(lambda m: 1 if m <= 6 else 2)
            sem_totais = df_ano.groupby('Sem')['Total'].sum().reindex([1,2], fill_value=0)
            sem_totais.index = ['1º Semestre', '2º Semestre']
            bars = sem_totais.plot(kind='bar', ax=ax, rot=0, color=colors[:2])
            ax.set_title(f"Comparativo Semestral {ano}")
            ax.set_xlabel("")
            ax.bar_label(bars.containers[0], color=self.COLORS["text"], fontsize=10, padding=3)

        elif tipo == "Comparativo de Domingos":
            domingos = df_ano[df_ano['Data'].dt.weekday == 6]
            if domingos.empty:
                ax.text(0.5, 0.5, "Sem dados para domingos", color=self.COLORS["text"], ha='center')
            else:
                totais = domingos[['Publico PCG', 'Publico Comerciário', 'Publico Adversos']].sum()
                totais.index = ['PCG', 'Comerciário', 'Adversos']
                bars = totais.plot(kind='bar', ax=ax, rot=0, color=colors)
                ax.bar_label(bars.containers[0], color=self.COLORS["text"], fontsize=10, padding=3)
            ax.set_title(f"Público nos Domingos em {ano}")

        elif tipo == "Comparativo por Sala":
            sala_tot = df_ano.groupby('Sala')['Total'].sum()
            if sala_tot.empty:
                ax.text(0.5, 0.5, "Sem dados de sala", color=self.COLORS["text"], ha='center')
            else:
                def format_pie_labels(pct, allvals):
                    absolute = int(round(pct/100.*allvals.sum()))
                    return f"{absolute}\n({pct:.1f}%)"
                wedges, _, _ = ax.pie(sala_tot,
                                      autopct=lambda pct: format_pie_labels(pct, sala_tot),
                                      startangle=90, colors=colors, pctdistance=0.80,
                                      textprops={'color':"white", 'weight':"bold", 'fontsize':10})
                leg = ax.legend(wedges, sala_tot.index, title="Salas", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1),
                                     labelcolor=self.COLORS["text"], facecolor=self.COLORS["frame"], edgecolor='none')
                leg.get_title().set_color(self.COLORS["text"])
            ax.set_title(f"Distribuição por Sala {ano}")

if __name__ == "__main__":
    app = App()
    app.mainloop()