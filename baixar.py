import csv
import os
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Exibe mensagem de crédito
print("joaquina.py Script para baixar arquivos disponibilizados via CSV referente ao retorno de ofício judicial da APPLE, por Joaquim Ferreira.")

# Variáveis ajustáveis
downloads_simultaneos = 4
arquivo_input = r'CAMINHO'  # Arquivo CSV disponibilizado pela APPLE
diretorio_output = r'CAMINHO'  # Ajuste o caminho conforme necessário
arquivo_log = 'log.txt'  # Nome do arquivo de log

def download_arquivo(row):
    data_type, file_name, file_link, _, _, _, _ = row
    file_path = os.path.join(diretorio_output, file_name)

    if os.path.exists(file_path):
        log(f'{file_name} já existe, pulando o download')
        return

    log(f'Iniciando o download de {file_name} em {datetime.now().strftime("%H:%M:%S")}')

    try:
        with requests.get(file_link, stream=True) as response:
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)

        log(f'Download de {file_name} concluído em {datetime.now().strftime("%H:%M:%S")}')
    except Exception as e:
        log(f'Erro no download de {file_name}: {str(e)}')
        # Se ocorrer um erro, exclua o arquivo parcial, se existir
        if os.path.exists(file_path):
            os.remove(file_path)
            log(f'Arquivo parcial {file_name} removido')

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(arquivo_log, 'a', encoding='utf-8') as log_file:
        log_file.write(f'[{timestamp}] {message}\n')
    print(message)

if __name__ == "__main__":
    # Criar o diretório de output se não existir
    os.makedirs(diretorio_output, exist_ok=True)

    try:
        # Iniciar o contador de tempo
        start_time = datetime.now()

        # Ler o arquivo CSV
        with open(arquivo_input, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Ignorar o cabeçalho

            # Iniciar os downloads simultâneos
            with ThreadPoolExecutor(max_workers=downloads_simultaneos) as executor:
                executor.map(download_arquivo, reader)

        # Calcular e imprimir o tempo total
        end_time = datetime.now()
        total_time = end_time - start_time
        log(f'\nTodos os downloads foram concluídos em {total_time}')
    except KeyboardInterrupt:
        log("\nInterrompendo downloads...")
        # Se houver interrupção, exclua os arquivos parciais em andamento
        for row in reader:
            _, file_name, _, _, _, _, _ = row
            file_path = os.path.join(diretorio_output, file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
                log(f'Arquivo parcial {file_name} removido')
    finally:
        log("Downloads finalizados.")
