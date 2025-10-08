# database.py
import sqlite3
import pandas as pd

class Database:
    def __init__(self, db_name="gestao_espetaculos.db"):
        self.db_name = db_name

    def _conectar(self):
        """Cria e retorna uma nova conexão com o banco de dados."""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def criar_tabela(self):
        """Cria a tabela de sessoes se ela não existir."""
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dia_semana TEXT,
                data TEXT,
                nome_evento TEXT,
                sala TEXT,
                publico_pcg INTEGER,
                publico_comerciario INTEGER,
                publico_adversos INTEGER,
                pcg_com INTEGER,
                total INTEGER,
                observacoes TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def adicionar_sessao(self, sessao_data):
        """Adiciona uma nova sessão ao banco de dados."""
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sessoes (dia_semana, data, nome_evento, sala, publico_pcg, publico_comerciario, publico_adversos, pcg_com, total, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sessao_data.get("Dia"), sessao_data.get("Data"), sessao_data.get("Nome_do_Evento"),
            sessao_data.get("Sala"), sessao_data.get("Publico_PCG"), sessao_data.get("Publico_Comerciario"),
            sessao_data.get("Publico_Adversos"), sessao_data.get("PCG_COM"), sessao_data.get("Total"),
            sessao_data.get("Observacoes")
        ))
        conn.commit()
        conn.close()

    def buscar_todas_sessoes(self):
        """Busca todas as sessões e retorna como um DataFrame do Pandas."""
        conn = self._conectar()
        df = pd.read_sql_query("SELECT * FROM sessoes", conn)
        conn.close()
        return df

    def buscar_sessoes_filtradas(self, filtro_nome="", filtro_sala="", ano_selecionado=None):
        """Busca sessões com base nos filtros fornecidos."""
        conn = self._conectar()
        
        query = "SELECT * FROM sessoes"
        conditions = []
        params = []

        if filtro_nome:
            conditions.append("nome_evento LIKE ?")
            params.append(f'%{filtro_nome}%')
        
        if filtro_sala:
            conditions.append("sala = ?")
            params.append(filtro_sala)

        if ano_selecionado:
            conditions.append("data LIKE ?")
            params.append(f'%/{ano_selecionado}')

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        df = pd.read_sql_query(query, conn, params=tuple(params))
        conn.close()
        return df

    def buscar_anos_disponiveis(self):
        """Busca todos os anos únicos presentes no banco de dados."""
        conn = self._conectar()
        query = "SELECT DISTINCT SUBSTR(data, 7, 4) as ano FROM sessoes ORDER BY ano DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def buscar_sessao_por_id(self, sessao_id):
        """Busca uma sessão específica pelo seu ID."""
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessoes WHERE id = ?", (sessao_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def atualizar_sessao(self, sessao_id, dados):
        """Atualiza os dados de uma sessão existente."""
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE sessoes SET
                nome_evento = ?, data = ?, dia_semana = ?, sala = ?,
                publico_pcg = ?, publico_comerciario = ?, publico_adversos = ?,
                pcg_com = ?, total = ?, observacoes = ?
            WHERE id = ?
        ''', (
            dados['Nome do Evento'], dados['Data'], dados['Dia'], dados['Sala'],
            dados['Publico PCG'], dados['Publico Comerciário'], dados['Publico Adversos'],
            dados['PCG+COM.'], dados['Total'], dados['Observações'],
            sessao_id
        ))
        conn.commit()
        conn.close()

    def excluir_sessao_por_id(self, sessao_id):
        """Exclui uma sessão pelo seu ID."""
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessoes WHERE id = ?", (sessao_id,))
        conn.commit()
        conn.close()

    def excluir_evento_em_lote(self, nome_evento):
        """Exclui todas as sessões de um evento específico."""
        conn = self._conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessoes WHERE nome_evento = ?", (nome_evento,))
        conn.commit()
        conn.close()
