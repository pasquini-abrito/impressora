import os
import time
import hashlib
from datetime import datetime
import re

class PPLAParser:
    def __init__(self):
        self.etiquetas = []  # Lista para armazenar múltiplas etiquetas
        self.etiqueta_atual = None
        self.proximo_valor_para = None
    
    def parse_file(self, file_path):
        """Analisa um arquivo PPLA completo, identificando múltiplas etiquetas"""
        if not os.path.exists(file_path):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Dividir o conteúdo em etiquetas usando os delimitadores
            # O padrão: cada etiqueta começa com <xpml><page...> e termina com Q0001\nE
            # Mas também pode ter múltiplas etiquetas em sequência
            
            # Primeiro, vamos dividir por possíveis separadores de etiqueta
            # Podemos usar a tag <xpml><page quantity='0' como indicador de início de etiqueta
            padrao_etiqueta = r'(<xpml><page quantity=\'0\'[^>]*>.*?Q0001\s*E\s*<xpml></page></xpml><xpml><end/></xpml>)'
            
            # Encontrar todas as etiquetas no conteúdo
            etiquetas_raw = re.findall(padrao_etiqueta, content, re.DOTALL)
            
            if not etiquetas_raw:
                # Tentar outro padrão se o primeiro não encontrar
                padrao_alternativo = r'(n.*?Q0001\s*E\s*)'
                etiquetas_raw = re.findall(padrao_alternativo, content, re.DOTALL)
            
            self.etiquetas = []
            
            for i, etiqueta_raw in enumerate(etiquetas_raw):
                etiqueta_data = self._processar_etiqueta(etiqueta_raw, i+1)
                if etiqueta_data:
                    self.etiquetas.append(etiqueta_data)
            
            return len(self.etiquetas) > 0
            
        except Exception as e:
            print(f"Erro ao analisar arquivo: {e}")
            return False
    
    def _processar_etiqueta(self, etiqueta_raw, numero_etiqueta):
        """Processa uma única etiqueta raw e retorna seus dados"""
        # Limpar conteúdo - remover tags XML
        content = re.sub(r'<[^>]*>', '', etiqueta_raw)
        
        # Remover caracteres de controle (mantendo quebras de linha)
        content = re.sub(r'[\x00-\x09\x0B-\x1F\x7F]', ' ', content)
        
        # Dividir por linhas
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # Inicializar dados para esta etiqueta
        data = {
            'numero': numero_etiqueta,
            'tipo': '',
            'op': '',
            'referencia': '',
            'descricao': '',
            'faccao': '',
            'cidade': '',
            'regiao': '',
            'fracao': '',
            'codigos': [],
            'textos': [],
            'comandos': {
                'direcao': '',
                'alinhamento': '',
                'quantidade': '',
                'final': False
            },
            'posicoes_texto': [],
            'outros_comandos': []
        }
        
        self.proximo_valor_para = None
        
        # Primeiro, coletar todos os textos na ordem
        textos_coletados = []
        for line in lines:
            # Buscar comandos de texto que começam com "19"
            if line.startswith('19') and len(line) >= 15:
                # Extrair texto (começa na posição 15, índice 14)
                texto = line[15:].strip()
                if texto:
                    textos_coletados.append(texto)
            
            # Buscar por códigos específicos
            elif line.startswith('1e') and len(line) > 2:
                codigo = line[2:].strip()
                if codigo:
                    data['codigos'].append(codigo)
            
            # Buscar comandos de configuração
            else:
                self._processar_comando(line, data)
        
        # Processar textos na ordem correta
        self._processar_textos_sequencial(textos_coletados, data)
        
        return data
    
    def _processar_comando(self, linha, data):
        """Processa comandos de configuração da impressora"""
        linha = linha.strip()
        
        # Comando D - Direção do texto
        if linha.startswith('D') and len(linha) > 1 and linha[1:].isdigit():
            data['comandos']['direcao'] = linha[1:]
        
        # Comando A - Alinhamento
        elif linha.startswith('A') and len(linha) > 1 and linha[1:].isdigit():
            data['comandos']['alinhamento'] = linha[1:]
        
        # Comando Q - Quantidade
        elif linha.startswith('Q') and len(linha) > 1:
            data['comandos']['quantidade'] = linha[1:]
        
        # Comando E - Final
        elif linha == 'E':
            data['comandos']['final'] = True
        
        # Outros comandos importantes
        elif linha.startswith(('M', 'O', 'V', 'f', 'L', 'H', 'S', 'P', 'n')):
            if linha not in data['outros_comandos']:
                data['outros_comandos'].append(linha)
    
    def _processar_textos_sequencial(self, textos, data):
        """Processa os textos na ordem sequencial correta"""
        i = 0
        while i < len(textos):
            texto = textos[i]
            data['textos'].append(texto)
    
            # OP
            if texto == 'OP:' and i + 1 < len(textos):
                data['op'] = textos[i + 3]
    
            # Referência
            elif texto == 'Ref:' and i + 1 < len(textos):
                data['referencia'] = textos[i + 1]
    
            # Facção
            elif texto in ('Faccao:', 'Facção:') and i + 1 < len(textos):
                data['faccao'] = textos[i + 1]
    
            # Cidade
            elif texto == 'Cidade:' and i + 1 < len(textos):
                data['cidade'] = textos[i + 1]
    
            # Região
            elif texto in ('Regiao:', 'Região:') and i + 1 < len(textos):
                data['regiao'] = textos[i + 1]
    
            # Tipo
            elif 'CONSERTO' in texto:
                data['tipo'] = 'CONSERTO'
    
            # Descrição
            elif any(p in texto for p in ('CAMISETA', 'BLUSA', 'CALCA')):
                data['descricao'] = texto
    
            # Fração
            elif re.match(r'^\d+/\d+$', texto):
                data['fracao'] = texto
    
            # Códigos numéricos longos
            elif texto.isdigit() and len(texto) >= 8:
                if texto not in (data['op'], data['referencia']):
                    data['codigos'].append(texto)
    
            i += 1
    
    
    def formatar_etiqueta(self, etiqueta_data=None):
        """Formata uma etiqueta específica para exibição"""
        if etiqueta_data is None and self.etiquetas:
            etiqueta_data = self.etiquetas[0]
        elif etiqueta_data is None:
            return "Nenhuma etiqueta encontrada"
        
        largura = 42
        
        def linha(texto=""):
            return f"│ {texto.ljust(largura)} │"
        
        def centro(texto):
            return f"│ {texto.center(largura)} │"
        
        topo = "┌" + "─" * (largura + 2) + "┐"
        meio = "├" + "─" * (largura + 2) + "┤"
        base = "└" + "─" * (largura + 2) + "┘"
        
        linhas = []
        linhas.append(topo)
        
        # Tipo
        linhas.append(centro(etiqueta_data['tipo'] or ""))
        linhas.append(meio)
        
        # OP e REF
        op = ''.join(filter(str.isdigit, etiqueta_data['op']))[:9]
        ref = ''.join(filter(str.isdigit, etiqueta_data['referencia']))[:9]
        linhas.append(linha(f"OP: {op}".ljust(21) + f"REF: {ref}"))
        
        linhas.append(linha())
        
        # Descrição
        descricao = etiqueta_data['descricao']
        if len(descricao) > largura:
            # Quebrar descrição longa
            partes = [descricao[i:i+largura] for i in range(0, len(descricao), largura)]
            for parte in partes[:2]:  # Máximo 2 linhas
                linhas.append(linha(parte))
        else:
            linhas.append(linha(descricao))
        
        linhas.append(linha())
        
        # Facção
        linhas.append(linha("FACÇÃO:"))
        faccao = etiqueta_data['faccao']
        if len(faccao) > largura:
            partes = [faccao[i:i+largura] for i in range(0, len(faccao), largura)]
            for parte in partes[:2]:
                linhas.append(linha(parte))
        else:
            linhas.append(linha(faccao))
        
        linhas.append(linha())
        
        # Cidade / Região
        cidade = etiqueta_data['cidade']
        regiao = etiqueta_data['regiao']
        cidade_str = f"CIDADE: {cidade}"
        regiao_str = f"REGIÃO: {regiao}"
        
        if len(cidade_str) + len(regiao_str) + 3 <= largura:
            linhas.append(linha(f"{cidade_str}   {regiao_str}"))
        else:
            linhas.append(linha(cidade_str))
            linhas.append(linha(regiao_str))
        
        linhas.append(linha())
        
        # Fração
        if etiqueta_data['fracao']:
            linhas.append(centro(etiqueta_data['fracao']))
        
        linhas.append(base)
        linhas.append(f"Etiqueta {etiqueta_data['numero']} - 10 x 7,5 cm")
        
        return "\n".join(linhas)
    
    def print_summary(self):
        """Imprime um resumo de todas as etiquetas extraídas"""
        print("\n" + "="*60)
        print(f"RESUMO DO ARQUIVO - {len(self.etiquetas)} ETIQUETA(S) ENCONTRADA(S)")
        print("="*60)
        
        for i, etiqueta in enumerate(self.etiquetas):
            print(f"\n{'='*60}")
            print(f"ETIQUETA {i+1}/{len(self.etiquetas)}")
            print(f"{'='*60}")
            
            etiqueta_formatada = self.formatar_etiqueta(etiqueta)
            print(etiqueta_formatada)
            
            print(f"\n📋 INFORMAÇÕES DETALHADAS (Etiqueta {i+1}):")
            if etiqueta['tipo']:
                print(f"   • Tipo: {etiqueta['tipo']}")
            if etiqueta['op']:
                print(f"   • OP: {etiqueta['op']}")
            if etiqueta['referencia']:
                print(f"   • Referência: {etiqueta['referencia']}")
            if etiqueta['descricao']:
                print(f"   • Descrição: {etiqueta['descricao']}")
            if etiqueta['faccao']:
                print(f"   • Facção: {etiqueta['faccao']}")
            if etiqueta['cidade']:
                print(f"   • Cidade: {etiqueta['cidade']}")
            if etiqueta['regiao']:
                print(f"   • Região: {etiqueta['regiao']}")
            if etiqueta['fracao']:
                print(f"   • Fração: {etiqueta['fracao']}")
            if etiqueta['codigos']:
                print(f"   • Códigos: {', '.join(etiqueta['codigos'])}")
            
            # Comandos de impressão
            com = etiqueta['comandos']
            if any(com.values()):
                print(f"\n⚙️  COMANDOS DE IMPRESSÃO:")
                if com['direcao']:
                    print(f"   • Direção: D{com['direcao']}")
                if com['alinhamento']:
                    print(f"   • Alinhamento: A{com['alinhamento']}")
                if com['quantidade']:
                    print(f"   • Quantidade: Q{com['quantidade']}")
                if com['final']:
                    print(f"   • Comando Final: E")
            
            print(f"\n📝 TEXTOS EXTRAÍDOS (Etiqueta {i+1}):")
            for j, texto in enumerate(etiqueta['textos']):
                print(f"   {j+1:2d}. {texto}")

def testar_exemplo():
    """Testa com o exemplo fornecido contendo múltiplas etiquetas"""
    exemplo = """<xpml><page quantity='0' pitch='75.1 mm'></xpml>
M0739
O0220
V0
f324
D
<xpml></page></xpml><xpml><page quantity='1' pitch='75.1 mm'></xpml>
L
D11
A2
1911A1202510200CONSERTO
1911A1202510044OP:
1911A1202250044Ref:
1911A1202250089121302105
1911A140248008921301507
1911A1201810044CAMISETA CASUAL MASC MC
1911A1201390044Faccao:
1911A1401360118LP ACABAMENTOS E TRANSPORTES
1911A1201130044Cidade:
1911A1201130118GUABIRUBA
1911A1200920044Regiao:
1911A1200920118SC - MEIO VALE
1e8405000330142C2130150727411
1911A12001401832130150727411
1911A14024203381/2
Q0001
E
<xpml></page></xpml><xpml><end/></xpml>
<xpml><page quantity='0' pitch='75.1 mm'></xpml>
M0739
O0220
V0
f324
D
<xpml></page></xpml><xpml><page quantity='1' pitch='75.1 mm'></xpml>
L
D11
A2
1911A1202510200CONSERTO
1911A1202510044OP:
1911A1202250044Ref:
1911A1202250089121302105
1911A140248008921301507
1911A1201810044CAMISETA CASUAL MASC MC
1911A1201390044Faccao:
1911A1401360118LP ACABAMENTOS E TRANSPORTES
1911A1201130044Cidade:
1911A1201130118GUABIRUBA
1911A1200920044Regiao:
1911A1200920118SC - MEIO VALE
1e8405000330142C2130150727412
1911A12001401832130150727412
1911A14024203382/2
Q0001
E
<xpml></page></xpml><xpml><end/></xpml>"""
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(exemplo)
        temp_file = f.name
    
    print("🧪 TESTANDO COM EXEMPLO DE MÚLTIPLAS ETIQUETAS")
    print("-" * 60)
    
    parser = PPLAParser()
    if parser.parse_file(temp_file):
        parser.print_summary()
    else:
        print("❌ Nenhuma etiqueta encontrada no arquivo")
    
    os.unlink(temp_file)

def processar_arquivo(file_path):
    """Processa um arquivo PPLA específico"""
    if not os.path.exists(file_path):
        print(f"❌ Arquivo não encontrado: {file_path}")
        return
    
    parser = PPLAParser()
    print(f"\n📄 Processando: {file_path}")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("-" * 60)
    
    if parser.parse_file(file_path):
        parser.print_summary()
        
        # Salvar resultado formatado
        salvar_resultado_formatado(file_path, parser)
    else:
        print("❌ Falha ao processar arquivo ou nenhuma etiqueta encontrada")

def salvar_resultado_formatado(file_path, parser):
    """Salva as etiquetas formatadas em arquivos separados"""
    try:
        pasta_resultados = os.path.join(os.path.dirname(file_path), "etiquetas_formatadas")
        if not os.path.exists(pasta_resultados):
            os.makedirs(pasta_resultados)
        
        nome_base = os.path.basename(file_path).replace('.txt', '')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Salvar um arquivo com todas as etiquetas
        resultado_completo = os.path.join(pasta_resultados, f"{nome_base}_TODAS_{timestamp}.txt")
        
        with open(resultado_completo, 'w', encoding='utf-8') as f:
            f.write(f"ARQUIVO: {file_path}\n")
            f.write(f"DATA PROCESSAMENTO: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"TOTAL DE ETIQUETAS: {len(parser.etiquetas)}\n")
            f.write("="*60 + "\n\n")
            
            for i, etiqueta in enumerate(parser.etiquetas):
                f.write(f"ETIQUETA {i+1}/{len(parser.etiquetas)}\n")
                f.write("-"*40 + "\n")
                f.write(parser.formatar_etiqueta(etiqueta))
                f.write("\n\n")
        
        print(f"✅ Resultados salvos em: {resultado_completo}")
        
        # Também salvar cada etiqueta individualmente
        for i, etiqueta in enumerate(parser.etiquetas):
            resultado_individual = os.path.join(pasta_resultados, f"{nome_base}_ETQ{i+1}_{timestamp}.txt")
            with open(resultado_individual, 'w', encoding='utf-8') as f:
                f.write(parser.formatar_etiqueta(etiqueta))
            
            print(f"   • Etiqueta {i+1}: {os.path.basename(resultado_individual)}")
        
    except Exception as e:
        print(f"⚠️  Não foi possível salvar resultados: {e}")

def monitorar_pasta(pasta=r"C:\\Imp"):
    """Monitora uma pasta por alterações no arquivo Imprime.txt"""
    arquivo = os.path.join(pasta, "Imprime.txt")
    
    # Criar pasta se não existir
    if not os.path.exists(pasta):
        print(f"📁 Criando pasta: {pasta}")
        os.makedirs(pasta, exist_ok=True)
    
    print(f"🖨️  Monitor PPLA Iniciado")
    print(f"📂 Pasta: {pasta}")
    print(f"📄 Arquivo: Imprime.txt")
    print("⏳ Monitorando... (Ctrl+C para parar)")
    print("-" * 60)
    
    ultimo_hash = ""
    
    try:
        while True:
            if os.path.exists(arquivo):
                # Calcular hash atual
                try:
                    with open(arquivo, 'rb') as f:
                        hash_atual = hashlib.md5(f.read()).hexdigest()
                except:
                    hash_atual = ""
                
                # Se o hash mudou, processar
                if hash_atual and hash_atual != ultimo_hash:
                    print(f"\n📊 [{datetime.now().strftime('%H:%M:%S')}] Arquivo modificado!")
                    processar_arquivo(arquivo)
                    ultimo_hash = hash_atual
            else:
                # Arquivo não existe, resetar hash
                if ultimo_hash != "":
                    print(f"\n⚠️  [{datetime.now().strftime('%H:%M:%S')}] Arquivo removido")
                    ultimo_hash = ""
            
            # Aguardar 1 segundo antes de verificar novamente
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoramento interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro no monitoramento: {e}")

def menu_principal():
    """Menu interativo para o usuário"""
    print("\n" + "="*60)
    print("ANALISADOR PPLA - IMPRESSORAS ARGOX")
    print("="*60)
    print("\nOpções disponíveis:")
    print("1. Monitorar pasta C:\\Imp continuamente")
    print("2. Processar arquivo específico")
    print("3. Testar com exemplo fornecido (múltiplas etiquetas)")
    print("4. Sair")
    
    while True:
        try:
            opcao = input("\nEscolha uma opção (1-4): ").strip()
            
            if opcao == "1":
                monitorar_pasta()
                break
            elif opcao == "2":
                caminho = input("Digite o caminho completo do arquivo: ").strip()
                processar_arquivo(caminho)
                break
            elif opcao == "3":
                testar_exemplo()
                break
            elif opcao == "4":
                print("Saindo...")
                break
            else:
                print("Opção inválida! Escolha 1, 2, 3 ou 4.")
        except KeyboardInterrupt:
            print("\nSaindo...")
            break
        except Exception as e:
            print(f"Erro: {e}")

if __name__ == "__main__":
    menu_principal()