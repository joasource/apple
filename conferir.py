import hashlib
import os
import csv
import datetime

# Exibe mensagem de crédito
print("joaquina.py Script para verificar integridade dos arquivos baixados via CSV referente ao retorno de ofício judicial da APPLE, por Joaquim Ferreira.")

# Defina as variáveis para o CSV, diretório e arquivo de log aqui
ARQUIVO_CSV = 'DOCUMENTO.csv'
DIRETORIO = 'CAMINHO'
ARQUIVO_LOG = 'GPG_log.txt'

# Função para calcular o hash de um arquivo
def calcular_hash_arquivo(nome_arquivo):
    hasher = hashlib.sha256()
    with open(nome_arquivo, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()

# Abre o arquivo de log
with open(ARQUIVO_LOG, 'a', encoding='utf-8') as log:
    log.write(f"Log gerado em: {datetime.datetime.now()}\n\n")
    
    # Abre o arquivo CSV
    log.write("Abrindo o arquivo CSV...\n")
    with open(ARQUIVO_CSV, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Extrai informações do CSV
            nome_arquivo = row['File_Name']
            hash_fornecido = row['GPG_SHA256']
            
            # Verifica se o arquivo existe no diretório
            caminho_arquivo = os.path.join(DIRETORIO, nome_arquivo)
            log.write(f"Verificando o arquivo: {caminho_arquivo}\n")
            if os.path.exists(caminho_arquivo):
                # Calcula o hash do arquivo no diretório
                log.write("Calculando o hash do arquivo...\n")
                hash_calculado = calcular_hash_arquivo(caminho_arquivo)
                
                # Compara os hashes
                if hash_calculado == hash_fornecido:
                    resultado = f'{nome_arquivo} COMPATÍVEL\n'
                else:
                    resultado = f'{nome_arquivo} ARQUIVO ERRADO!!!\n'
                
                log.write(resultado)
                print(resultado)
            else:
                log.write(f'O arquivo {nome_arquivo} não foi encontrado no diretório.\n')
