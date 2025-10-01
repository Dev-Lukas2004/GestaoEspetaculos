# migrar_para_sqlite.py (CORRIGIDO)
import pandas as pd
from database import Database
import os

NOME_ARQUIVO_EXCEL = "ArquivoAnual_anaceci.xlsx"

def migrar():
    if not os.path.exists(NOME_ARQUIVO_EXCEL):
        print(f"Arquivo '{NOME_ARQUIVO_EXCEL}' não encontrado. Nenhum dado para migrar.")
        return

    db = Database()
    db.criar_tabela()

    print(f"Lendo dados de '{NOME_ARQUIVO_EXCEL}'...")
    try:
        xls = pd.ExcelFile(NOME_ARQUIVO_EXCEL)
        df_completo = pd.concat([pd.read_excel(xls, sheet_name=s) for s in xls.sheet_names], ignore_index=True)
        df_completo.dropna(how='all', inplace=True)
        
        # --- CORREÇÃO APLICADA AQUI ---
        # 1. Garante que a coluna 'Data' seja convertida para o formato de data do pandas
        #    O 'coerce' transforma qualquer erro de data em 'NaT' (Not a Time)
        df_completo['Data'] = pd.to_datetime(df_completo['Data'], errors='coerce', dayfirst=True)
        
        # 2. Remove linhas onde a data não pôde ser convertida
        df_completo.dropna(subset=['Data'], inplace=True)

        # 3. CONVERTE A COLUNA DE DATA PARA TEXTO no formato esperado (DD/MM/YYYY)
        df_completo['Data'] = df_completo['Data'].dt.strftime('%d/%m/%Y')
        # --- FIM DA CORREÇÃO ---

        # Renomeia as colunas do DataFrame para corresponder exatamente
        # às chaves que a função `adicionar_sessao` espera.
        df_completo.rename(columns={
            "Dia": "Dia", "Data": "Data", "Nome do Evento": "Nome_do_Evento", "Sala": "Sala", 
            "Publico PCG": "Publico_PCG", "Publico Comerciário": "Publico_Comerciario", 
            "Publico Adversos": "Publico_Adversos", "PCG+COM.": "PCG_COM", "Total": "Total", 
            "Observações": "Observacoes"
        }, inplace=True)

        # Garante que as colunas de público sejam numéricas e preenche valores nulos
        colunas_publico = ['Publico_PCG', 'Publico_Comerciario', 'Publico_Adversos', 'PCG_COM', 'Total']
        for col in colunas_publico:
            if col in df_completo.columns:
                df_completo[col] = pd.to_numeric(df_completo[col], errors='coerce').fillna(0).astype(int)
            else:
                df_completo[col] = 0
        
        # Garante que a coluna de observações exista
        if 'Observacoes' not in df_completo.columns:
            df_completo['Observacoes'] = ''
        df_completo['Observacoes'].fillna('', inplace=True)


        print(f"Encontrados {len(df_completo)} registros válidos para migrar.")

        for _, row in df_completo.iterrows():
            sessao_dict = row.to_dict()
            db.adicionar_sessao(sessao_dict)
            
        print("\nMigração concluída com sucesso!")
        print("Seus dados agora estão no arquivo 'gestao_espetaculos.db'.")

    except Exception as e:
        print(f"Ocorreu um erro durante a migração: {e}")

if __name__ == "__main__":
    migrar()