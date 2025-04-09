import os
import subprocess

def descriptografar_arquivo(arquivo_cifrado, senha, diretorio_saida):
    # Define o caminho de saída do arquivo descriptografado
    arquivo_descriptografado = os.path.join(diretorio_saida, os.path.splitext(os.path.basename(arquivo_cifrado))[0])
    
    # Verifica se o arquivo descriptografado já existe
    if not os.path.exists(arquivo_descriptografado):
        try:
            # Executa o GnuPG para descriptografar o arquivo
            comando = [
                'gpg',
                '--batch',
                '--yes',
                '--passphrase', senha,
                '--output', arquivo_descriptografado,
                '--decrypt', arquivo_cifrado
            ]
            subprocess.run(comando, check=True)
            print(f'{arquivo_cifrado} descriptografado com sucesso em {diretorio_saida}.')
        except subprocess.CalledProcessError as e:
            print(f'Erro ao descriptografar {arquivo_cifrado}: {e}')
    else:
        print(f'{arquivo_descriptografado} já existe. Pulando...')

def descriptografar_diretorio(diretorio, senha, diretorio_saida):
    # Percorre os arquivos no diretório
    for arquivo_cifrado in os.listdir(diretorio):
        if arquivo_cifrado.endswith('.gpg'):
            descriptografar_arquivo(os.path.join(diretorio, arquivo_cifrado), senha, diretorio_saida)

if __name__ == "__main__":
    # Defina as variáveis diretamente aqui
    diretorio_alvo = r'CAMINHO'
    senha = 'SENHA'
    diretorio_saida = r'CAMINHO'

    # Verifica se o diretório de saída existe e cria-o se não existir
    if not os.path.exists(diretorio_saida):
        os.makedirs(diretorio_saida)
        print(f'Diretório de saída {diretorio_saida} criado com sucesso.')

    descriptografar_diretorio(diretorio_alvo, senha, diretorio_saida)
