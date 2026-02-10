import os
import time
import hashlib
from datetime import datetime
import re

class PPLAParser:
    def __init__(self):
        self.data = {
            'tipo': '',
            'op': '',
            'referencia': '',
            'descricao': '',
            'faccao': '',
            'cidade': '',
            'regiao': '',
            'codigos': [],
            'textos': [],
            'comandos': {
                'direcao': '',      # D11
                'alinhamento': '',  # A2
                'quantidade': '',   # Q0001
                'final': False      # E
            },
            'posicoes_texto': [],   # Lista de posições dos textos
            'outros_comandos': []   # Outros comandos encontrados
        }
    
    def parse_file(self, file_path):
        """Analisa um arquivo PPLA completo"""
        if not os.path.exists(file_path):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Limpar conteúdo - remover tags XML
            content = re.sub(r'<[^>]*>', '', content)
            
            # Remover caracteres de controle (mantendo quebras de linha)
            content = re.sub(r'[\x00-\x09\x0B-\x1F\x7F]', ' ', content)
            
            # Dividir por linhas
            lines = content.split('\n')
            
            # Resetar dados
            self.data = {
                'tipo': '',
                'op': '',
                'referencia': '',
                'descricao': '',
                'faccao': '',
                'cidade': '',
                'regiao': '',
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
            
            # Processar cada linha
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Buscar comandos de texto que começam com "19"
                # Formato: 19 + 13 caracteres de cabeçalho + texto
                if line.startswith('19') and len(line) >= 15:
                    # Extrair cabeçalho (13 caracteres após o '19')
                    cabecalho = line[2:15]  # posições 2 a 14 (13 caracteres)
                    # Extrair texto (começa na posição 15, índice 14)
                    texto = line[15:].strip()
                    if texto:
                        self._processar_texto(texto, cabecalho)
                
                # Buscar por códigos específicos
                elif line.startswith('1e') and len(line) > 2:
                    codigo = line[2:].strip()
                    if codigo:
                        self.data['codigos'].append(codigo)
                
                # Buscar comandos de configuração
                else:
                    self._processar_comando(line)
            
            return True
            
        except Exception as e:
            print(f"Erro ao analisar arquivo: {e}")
            return False
    
    def _processar_comando(self, linha):
        """Processa comandos de configuração da impressora"""
        linha = linha.strip()
        
        # Comando D - Direção do texto
        if linha.startswith('D') and len(linha) > 1:
            self.data['comandos']['direcao'] = linha[1:]  # Remove o 'D'
        
        # Comando A - Alinhamento
        elif linha.startswith('A') and len(linha) > 1:
            self.data['comandos']['alinhamento'] = linha[1:]  # Remove o 'A'
        
        # Comando Q - Quantidade
        elif linha.startswith('Q') and len(linha) > 1:
            self.data['comandos']['quantidade'] = linha[1:]  # Remove o 'Q'
        
        # Comando E - Final
        elif linha == 'E':
            self.data['comandos']['final'] = True
        
        # Outros comandos importantes
        elif linha.startswith(('M', 'O', 'V', 'f', 'L', 'H', 'S', 'P')):
            # M - Velocidade
            # O - Offset
            # V - Velocidade de impressão
            # f - Densidade térmica
            # L - Início de formato
            # H - Altura do caractere
            # S - Largura do caractere
            # P - Pitch
            if linha not in self.data['outros_comandos']:
                self.data['outros_comandos'].append(linha)
    
    def _analisar_cabecalho_posicao(self, cabecalho):
        """
        Analisa o cabeçalho de 13 caracteres para extrair informações de posição
        Sintaxe: 1XXXXX000XXXXX (13 caracteres)
        
        Baseado no exemplo: 122300001000200
        1 - orientacao
        22 - font
        30 - múltiplo altura e largura (3 para altura, 0 para largura)
        000 - código de barras (se texto, ignorar)
        0100 - coordenada Y (em pontos)
        0200 - coordenada X (em pontos)
        """
        if len(cabecalho) < 13:
            return None
        
        try:
            # Verificar se o cabeçalho contém apenas dígitos
            if cabecalho.isdigit():
                # Exemplo: 122300001000200
                orientacao = cabecalho[0]  # Primeiro dígito
                fonte = cabecalho[1:3]     # Dois dígitos seguintes
                multiplicador = cabecalho[3:5]  # Dois dígitos seguintes (altura e largura)
                codigo_barras = cabecalho[5:8]  # Três dígitos seguintes
                y_coord = cabecalho[8:12]  # Quatro dígitos seguintes (coordenada Y)
                x_coord = cabecalho[12:16] if len(cabecalho) >= 16 else cabecalho[12:]  # Quatro dígitos seguintes (coordenada X)
                
                return {
                    'orientacao': orientacao,
                    'fonte': fonte,
                    'multiplicador_altura': multiplicador[0] if len(multiplicador) > 0 else '',
                    'multiplicador_largura': multiplicador[1] if len(multiplicador) > 1 else '',
                    'codigo_barras': codigo_barras,
                    'y': y_coord,
                    'x': x_coord,
                    'y_pontos': int(y_coord) if y_coord.isdigit() else 0,
                    'x_pontos': int(x_coord) if x_coord.isdigit() else 0
                }
            else:
                # Tentar extrair informações mesmo com letras
                # Padrão comum: 11A1202510200
                # Pode conter letras na parte da fonte ou multiplicadores
                if len(cabecalho) >= 13:
                    # Tentar extrair coordenadas que geralmente são números
                    # As coordenadas geralmente estão no final
                    ultimos_8 = cabecalho[-8:] if len(cabecalho) >= 8 else cabecalho
                    
                    # Tentar extrair Y e X como últimos 8 caracteres (4+4)
                    if len(ultimos_8) >= 8 and ultimos_8[:4].isdigit() and ultimos_8[4:8].isdigit():
                        return {
                            'orientacao': cabecalho[0] if len(cabecalho) > 0 else '',
                            'fonte': cabecalho[1:3] if len(cabecalho) >= 3 else '',
                            'y': ultimos_8[:4],
                            'x': ultimos_8[4:8],
                            'y_pontos': int(ultimos_8[:4]),
                            'x_pontos': int(ultimos_8[4:8]),
                            'cabecalho_bruto': cabecalho
                        }
        
        except (ValueError, IndexError) as e:
            # Se houver erro na conversão, retornar None
            return None
        
        return None
    
    def _processar_texto(self, texto, cabecalho=None):
        """Processa e classifica o texto extraído, incluindo informações de posição"""
        # Limpar o texto
        texto_limpo = texto.strip()
        
        # Armazenar todos os textos para referência
        self.data['textos'].append(texto_limpo)
        
        # Analisar informações de posição do cabeçalho
        if cabecalho:
            info_posicao = self._analisar_cabecalho_posicao(cabecalho)
            if info_posicao:
                info_posicao['texto'] = texto_limpo
                info_posicao['cabecalho'] = cabecalho
                self.data['posicoes_texto'].append(info_posicao)
        
        # Identificar tipo de informação
        if not texto_limpo:
            return
        
        # Verificar padrões específicos
        if 'CONSERTO' in texto_limpo:
            self.data['tipo'] = texto_limpo
        elif texto_limpo.startswith('OP:'):
            # Extrair o valor após "OP:"
            partes = texto_limpo.split(':', 1)
            if len(partes) > 1:
                self.data['op'] = partes[1].strip()
        elif texto_limpo.startswith('Ref:'):
            partes = texto_limpo.split(':', 1)
            if len(partes) > 1:
                self.data['referencia'] = partes[1].strip()
        elif 'CAMISETA' in texto_limpo:
            self.data['descricao'] = texto_limpo
        elif texto_limpo.startswith('Faccao:') or texto_limpo.startswith('Facção:'):
            partes = texto_limpo.split(':', 1)
            if len(partes) > 1:
                self.data['faccao'] = partes[1].strip()
        elif texto_limpo.startswith('Cidade:'):
            partes = texto_limpo.split(':', 1)
            if len(partes) > 1:
                self.data['cidade'] = partes[1].strip()
        elif texto_limpo.startswith('Regiao:') or texto_limpo.startswith('Região:'):
            partes = texto_limpo.split(':', 1)
            if len(partes) > 1:
                self.data['regiao'] = partes[1].strip()
        elif texto_limpo.replace('/', '').isdigit() or len(texto_limpo) >= 8:
            # Possível código numérico (pelo menos 8 dígitos ou contém números)
            # Verificar se parece ser um código
            if any(c.isdigit() for c in texto_limpo) and len(texto_limpo) >= 5:
                self.data['codigos'].append(texto_limpo)
    
    def _interpretar_comandos(self):
        """Interpreta o significado dos comandos"""
        interpretacoes = []
        
        # Interpretar direção (D)
        direcao = self.data['comandos']['direcao']
        if direcao:
            if direcao == '11':
                interpretacoes.append("📐 Direção: 0° (normal)")
            elif direcao == '21':
                interpretacoes.append("📐 Direção: 90°")
            elif direcao == '31':
                interpretacoes.append("📐 Direção: 180°")
            elif direcao == '41':
                interpretacoes.append("📐 Direção: 270°")
            else:
                interpretacoes.append(f"📐 Direção: D{direcao}")
        
        # Interpretar alinhamento (A)
        alinhamento = self.data['comandos']['alinhamento']
        if alinhamento:
            if alinhamento == '2':
                interpretacoes.append("↔️ Alinhamento: Esquerda")
            elif alinhamento == '3':
                interpretacoes.append("↔️ Alinhamento: Centro")
            elif alinhamento == '4':
                interpretacoes.append("↔️ Alinhamento: Direita")
            else:
                interpretacoes.append(f"↔️ Alinhamento: A{alinhamento}")
        
        # Interpretar quantidade (Q)
        quantidade = self.data['comandos']['quantidade']
        if quantidade:
            try:
                qtd_num = int(quantidade)
                interpretacoes.append(f"🔢 Quantidade: {qtd_num:,} etiqueta(s)".replace(',', '.'))
            except:
                interpretacoes.append(f"🔢 Quantidade: Q{quantidade}")
        
        # Comando final
        if self.data['comandos']['final']:
            interpretacoes.append("🏁 Comando E: Fim do formato")
        
        return interpretacoes
    
    def _interpretar_posicoes(self):
        """Interpreta as posições dos textos"""
        interpretacoes = []
        
        for i, pos in enumerate(self.data['posicoes_texto']):
            # Interpretar orientação
            orientacao_map = {
                '1': "0° (normal)",
                '2': "90°",
                '3': "180°", 
                '4': "270°",
                '5': "0° espelhado",
                '6': "90° espelhado",
                '7': "180° espelhado",
                '8': "270° espelhado"
            }
            
            orientacao = orientacao_map.get(pos.get('orientacao', ''), f"Desconhecida ({pos.get('orientacao', '')})")
            
            # Interpretar fonte
            fonte_map = {
                '11': "Fonte padrão 1",
                '22': "Fonte 2",
                '33': "Fonte 3",
                '44': "Fonte 4"
            }
            
            fonte = fonte_map.get(pos.get('fonte', ''), f"Fonte {pos.get('fonte', '')}")
            
            # Criar interpretação
            interpretacao = f"📝 Texto {i+1}: '{pos.get('texto', '')[:30]}...'"
            
            if 'y_pontos' in pos and 'x_pontos' in pos:
                interpretacao += f"\n     📍 Posição: X={pos['x_pontos']}pts, Y={pos['y_pontos']}pts"
            
            if pos.get('orientacao'):
                interpretacao += f"\n     🧭 Orientação: {orientacao}"
            
            if pos.get('fonte'):
                interpretacao += f"\n     🔤 Fonte: {fonte}"
            
            if pos.get('multiplicador_altura') or pos.get('multiplicador_largura'):
                altura = pos.get('multiplicador_altura', '1')
                largura = pos.get('multiplicador_largura', '1')
                interpretacao += f"\n     ⚖️  Multiplicador: Altura={altura}x, Largura={largura}x"
            
            interpretacoes.append(interpretacao)
        
        return interpretacoes
    
    def print_summary(self):
        """Imprime um resumo dos dados extraídos"""
        print("\n" + "="*60)
        print("RESUMO DA ETIQUETA PPLA")
        print("="*60)
        
        if self.data['tipo']:
            print(f"📌 Tipo: {self.data['tipo']}")
        
        if self.data['op']:
            print(f"🔢 OP: {self.data['op']}")
        
        if self.data['referencia']:
            print(f"🏷️  Referência: {self.data['referencia']}")
        
        if self.data['descricao']:
            print(f"👕 Descrição: {self.data['descricao']}")
        
        if self.data['faccao']:
            print(f"🏭 Facção: {self.data['faccao']}")
        
        if self.data['cidade']:
            print(f"📍 Cidade: {self.data['cidade']}")
        
        if self.data['regiao']:
            print(f"🗺️  Região: {self.data['regiao']}")
        
        # Comandos de impressão
        print(f"\n⚙️  COMANDOS DE IMPRESSÃO:")
        interpretacoes = self._interpretar_comandos()
        for interpretacao in interpretacoes:
            print(f"   • {interpretacao}")
        
        # Mostrar comandos brutos
        comandos = self.data['comandos']
        if comandos['direcao']:
            print(f"     (D{comandos['direcao']})")
        if comandos['alinhamento']:
            print(f"     (A{comandos['alinhamento']})")
        if comandos['quantidade']:
            print(f"     (Q{comandos['quantidade']})")
        if comandos['final']:
            print(f"     (E)")
        
        # Posições dos textos
        if self.data['posicoes_texto']:
            print(f"\n🗺️  POSIÇÕES DOS TEXTOS:")
            pos_interpretacoes = self._interpretar_posicoes()
            for interpretacao in pos_interpretacoes:
                # Separar por linhas para melhor formatação
                linhas = interpretacao.split('\n')
                for linha in linhas:
                    print(f"   {linha}")
        
        # Outros comandos
        if self.data['outros_comandos']:
            print(f"\n🔧 Outros comandos identificados:")
            for cmd in self.data['outros_comandos']:
                print(f"   • {cmd}")
        
        if self.data['codigos']:
            print(f"\n🔢 Códigos identificados:")
            for codigo in self.data['codigos']:
                print(f"   • {codigo}")
        
        print("\n📝 Textos extraídos:")
        for texto in self.data['textos']:
            print(f"   • {texto}")
        
        print("\n" + "="*60)

def testar_exemplo():
    """Testa com o exemplo fornecido"""
    exemplo = """<xpml></page></xpml><xpml><page quantity='0' pitch='75.1 mm'></xpml>
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
    
    # Testar também com a sintaxe mencionada
    exemplo_sintaxe = """<xpml></page></xpml><xpml><page quantity='0' pitch='75.1 mm'></xpml>
L
D11
A2
19122300001000200EXAMPLE FOR TEXT
191100001000200OUTRO EXEMPLO
Q0001
E
<xpml></page></xpml><xpml><end/></xpml>"""
    
    # Salvar em arquivo temporário
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(exemplo_sintaxe)
        temp_file = f.name
    
    print("🧪 TESTANDO COM SINTEXE DE POSIÇÃO")
    print("-" * 60)
    
    parser = PPLAParser()
    if parser.parse_file(temp_file):
        parser.print_summary()
    
    # Limpar
    os.unlink(temp_file)
    
    print("\n" + "="*60)
    print("🧪 TESTANDO COM EXEMPLO FORNECIDO ANTERIORMENTE")
    print("-" * 60)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(exemplo)
        temp_file = f.name
    
    parser2 = PPLAParser()
    if parser2.parse_file(temp_file):
        parser2.print_summary()
    
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
        
        # Salvar resultado
        salvar_resultado(file_path, parser.data)
    else:
        print("❌ Falha ao processar arquivo")

def salvar_resultado(file_path, dados):
    """Salva os dados extraídos em um arquivo"""
    try:
        pasta_resultados = os.path.join(os.path.dirname(file_path), "resultados")
        if not os.path.exists(pasta_resultados):
            os.makedirs(pasta_resultados)
        
        nome_base = os.path.basename(file_path).replace('.txt', '')
        resultado_file = os.path.join(pasta_resultados, f"{nome_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        with open(resultado_file, 'w', encoding='utf-8') as f:
            f.write("RESULTADO DA ANÁLISE PPLA\n")
            f.write("="*50 + "\n")
            f.write(f"Arquivo: {file_path}\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write("="*50 + "\n\n")
            
            # Informações principais
            if dados['tipo']:
                f.write(f"TIPO: {dados['tipo']}\n")
            if dados['op']:
                f.write(f"OP: {dados['op']}\n")
            if dados['referencia']:
                f.write(f"REFERÊNCIA: {dados['referencia']}\n")
            if dados['descricao']:
                f.write(f"DESCRIÇÃO: {dados['descricao']}\n")
            if dados['faccao']:
                f.write(f"FACÇÃO: {dados['faccao']}\n")
            if dados['cidade']:
                f.write(f"CIDADE: {dados['cidade']}\n")
            if dados['regiao']:
                f.write(f"REGIÃO: {dados['regiao']}\n")
            
            # Comandos
            f.write(f"\nCOMANDOS DE IMPRESSÃO:\n")
            com = dados['comandos']
            if com['direcao']:
                f.write(f"  DIREÇÃO (D): {com['direcao']}\n")
            if com['alinhamento']:
                f.write(f"  ALINHAMENTO (A): {com['alinhamento']}\n")
            if com['quantidade']:
                f.write(f"  QUANTIDADE (Q): {com['quantidade']}\n")
            if com['final']:
                f.write(f"  COMANDO FINAL (E): SIM\n")
            
            # Posições dos textos
            if dados['posicoes_texto']:
                f.write(f"\nPOSIÇÕES DOS TEXTOS:\n")
                for i, pos in enumerate(dados['posicoes_texto']):
                    f.write(f"\n  Texto {i+1}: '{pos.get('texto', '')}'\n")
                    if 'cabecalho' in pos:
                        f.write(f"    Cabeçalho: {pos['cabecalho']}\n")
                    if 'x_pontos' in pos and 'y_pontos' in pos:
                        f.write(f"    Posição: X={pos['x_pontos']}pts, Y={pos['y_pontos']}pts\n")
                    if 'orientacao' in pos:
                        f.write(f"    Orientação: {pos['orientacao']}\n")
                    if 'fonte' in pos:
                        f.write(f"    Fonte: {pos['fonte']}\n")
                    if 'multiplicador_altura' in pos:
                        f.write(f"    Multiplicador Altura: {pos['multiplicador_altura']}\n")
                    if 'multiplicador_largura' in pos:
                        f.write(f"    Multiplicador Largura: {pos['multiplicador_largura']}\n")
            
            # Outros comandos
            if dados['outros_comandos']:
                f.write(f"\nOUTROS COMANDOS:\n")
                for cmd in dados['outros_comandos']:
                    f.write(f"  {cmd}\n")
            
            # Códigos
            if dados['codigos']:
                f.write(f"\nCÓDIGOS:\n")
                for codigo in dados['codigos']:
                    f.write(f"  {codigo}\n")
            
            # Textos
            if dados['textos']:
                f.write(f"\nTEXTOS EXTRAÍDOS:\n")
                for texto in dados['textos']:
                    f.write(f"  {texto}\n")
        
        print(f"✅ Resultado salvo em: {resultado_file}")
        
    except Exception as e:
        print(f"⚠️  Não foi possível salvar resultado: {e}")

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
    print("3. Testar com exemplo fornecido")
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