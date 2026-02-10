import os
import time
import hashlib
import re
import win32print
import win32api
import unicodedata
from datetime import datetime

class BPLBGenerator:
    def __init__(self):
        self.comandos = []
        # Configurações para etiqueta 10x7,5 cm conforme sua necessidade
        self.largura_etiqueta = 800    # 75mm em pontos (600/8 = 75mm)
        self.altura_etiqueta = 550     # 100mm em pontos (800/8 = 100mm)
        #self.espacamento = 0           # Sem espaçamento
        
    def remover_acentos(self, texto):
        """Remove acentos e caracteres especiais"""
        if not texto:
            return ""
        # Normaliza o texto e remove os acentos
        texto = unicodedata.normalize('NFKD', str(texto))
        texto = ''.join([c for c in texto if not unicodedata.combining(c)])
        # Substitui caracteres específicos
        texto = texto.replace('Ç', 'C').replace('ç', 'c')
        texto = texto.replace('Ã', 'A').replace('ã', 'a')
        texto = texto.replace('Õ', 'O').replace('õ', 'o')
        texto = texto.replace('Â', 'A').replace('â', 'a')
        texto = texto.replace('Ê', 'E').replace('ê', 'e')
        texto = texto.replace('Î', 'I').replace('î', 'i')
        texto = texto.replace('Ô', 'O').replace('ô', 'o')
        texto = texto.replace('Û', 'U').replace('û', 'u')
        return texto.upper()  # Tudo maiúsculo para consistência
    
    def iniciar_etiqueta(self):
        """Inicia uma nova etiqueta BPLB"""
        self.comandos = []
        # Comandos iniciais baseados no manual BPLB
        self.comandos.append("N")      # Limpar buffer (comando N)
        self.comandos.append("D7")     # Densidade 7 (mais suave que D9)
        self.comandos.append("S3")     # Velocidade 2 pol/seg (mais lento)
        self.comandos.append("JF")     # Desabilita backfeed (JB conforme manual)
        #self.comandos.append("ZT")     # Impressão começa do topo
        self.comandos.append(f"Q{self.altura_etiqueta}")  # Altura da etiqueta
        self.comandos.append(f"q{self.largura_etiqueta}")  # Largura da etiqueta
        
    def adicionar_texto(self, x, y, texto, fonte=1, tamanho_h=1, tamanho_v=1):
        """
        Adiciona comando de texto BPLB simplificado
        """
        # Remover acentos e caracteres especiais
        texto_limpo = self.remover_acentos(texto)
        cmd = f"A{x},{y},0,{fonte},{tamanho_h},{tamanho_v},N,\"{texto_limpo}\""
        self.comandos.append(cmd)
        
    def adicionar_linha_horizontal(self, x, y, comprimento, espessura=1):
        """Adiciona linha horizontal"""
        cmd = f"LE{x},{y},{comprimento},{espessura}"
        self.comandos.append(cmd)
    
    def adicionar_linha_vertical(self, x, y, comprimento, espessura=1):
        """Adiciona linha vertical"""
        cmd = f"LE{x},{y},{espessura},{comprimento}"
        self.comandos.append(cmd)
    
    def adicionar_borda(self, x1, y1, x2, y2, espessura=2):
        """Adiciona borda retangular"""
        # Linha superior
        self.comandos.append(f"LE{x1},{y1},{x2-x1},{espessura}")
        # Linha inferior
        self.comandos.append(f"LE{x1},{y2},{x2-x1},{espessura}")
        # Linha esquerda
        self.comandos.append(f"LE{x1},{y1},{espessura},{y2-y1}")
        # Linha direita
        self.comandos.append(f"LE{x2-espessura},{y1},{espessura},{y2-y1}")
        
    def finalizar_etiqueta(self, quantidade=1):
        """Finaliza a etiqueta com comando de impressão"""
        self.comandos.append(f"P{quantidade}")
        
    def obter_comandos(self):
        """Retorna os comandos BPLB como string"""
        return "\n".join(self.comandos) + "\n"
    
    def obter_comandos_bytes(self):
        """Retorna os comandos BPLB como bytes"""
        return self.obter_comandos().encode('utf-8', 'ignore')

class PPLAtoBPLBConverter:
    def __init__(self):
        self.parser = PPLAParser()
        self.generator = BPLBGenerator()
        
    def converter_etiqueta(self, etiqueta_data):
        """Converte dados de etiqueta PPLA para comandos BPLB semelhante à visualização"""
        self.generator.iniciar_etiqueta()
        
        largura = self.generator.largura_etiqueta
        altura = self.generator.altura_etiqueta
        
        # Adicionar borda (similar à visualização)
        self.generator.adicionar_borda(20, 20, largura-20, altura-20, espessura=2)
        
        y_pos = 50  # Posição Y inicial
        
        # 1. TIPO (centralizado no topo)
        if etiqueta_data['tipo']:
            tipo = self.generator.remover_acentos(etiqueta_data['tipo'])
            # Calcular posição X para centralizar
            # Fonte 5 com tamanho maior (não tem minúsculas, tudo maiúsculo)
            x_pos = (largura - len(tipo) * 16) // 2  # Aproximação para fonte 2x
            self.generator.adicionar_texto(x_pos, y_pos, tipo, fonte=2, tamanho_h=2, tamanho_v=2)
            y_pos += 70
        
        # Linha separadora
        self.generator.adicionar_linha_horizontal(30, y_pos-10, largura-60)
        y_pos += 20
        
        # 2. OP e REF (na mesma linha)
        op_texto = ""
        if etiqueta_data['op']:
            # Extrair apenas números da OP
            op_numeros = ''.join(filter(str.isdigit, etiqueta_data['op']))
            op_texto = f"OP: {op_numeros[:9]}"  # Limitar a 9 dígitos
        
        ref_texto = ""
        if etiqueta_data['referencia']:
            # Extrair apenas números da referência
            ref_numeros = ''.join(filter(str.isdigit, etiqueta_data['referencia']))
            ref_texto = f"REF: {ref_numeros[:9]}"  # Limitar a 9 dígitos
        
        # Calcular posições para OP e REF
        if op_texto and ref_texto:
            # OP à esquerda
            self.generator.adicionar_texto(40, y_pos, op_texto, fonte=3)
            # REF à direita
            ref_x = largura - len(ref_texto) * 20 - 40
            self.generator.adicionar_texto(ref_x, y_pos, ref_texto, fonte=3)
        elif op_texto:
            self.generator.adicionar_texto(40, y_pos, op_texto, fonte=3)
        elif ref_texto:
            self.generator.adicionar_texto(40, y_pos, ref_texto, fonte=3)
        
        y_pos += 50
        
        # 3. DESCRIÇÃO (centro, pode quebrar)
        if etiqueta_data['descricao']:
            descricao = self.generator.remover_acentos(etiqueta_data['descricao'])
            # Quebrar descrição longa
            if len(descricao) > 30:
                partes = []
                palavras = descricao.split()
                linha_atual = []
                comprimento_atual = 0
                
                for palavra in palavras:
                    if comprimento_atual + len(palavra) + 1 <= 30:
                        linha_atual.append(palavra)
                        comprimento_atual += len(palavra) + 1
                    else:
                        if linha_atual:
                            partes.append(' '.join(linha_atual))
                        linha_atual = [palavra]
                        comprimento_atual = len(palavra)
                
                if linha_atual:
                    partes.append(' '.join(linha_atual))
                
                # Limitar a 2 linhas
                for i, parte in enumerate(partes[:2]):
                    x_centro = (largura - len(parte) * 12) // 2
                    self.generator.adicionar_texto(x_centro, y_pos, parte, fonte=3)
                    y_pos += 40 if i == 0 else 30
            else:
                x_centro = (largura - len(descricao) * 12) // 2
                self.generator.adicionar_texto(x_centro, y_pos, descricao, fonte=3)
                y_pos += 50
        
        y_pos += 20
        
        # 4. FACÇÃO (centro, pode quebrar)
        if etiqueta_data['faccao']:
            faccao = self.generator.remover_acentos(etiqueta_data['faccao'])
            self.generator.adicionar_texto(40, y_pos, "FACCÃO:", fonte=3)
            y_pos += 40
            
            # Quebrar facção longa
            if len(faccao) > 30:
                partes = [faccao[i:i+30] for i in range(0, len(faccao), 30)]
                for parte in partes[:2]:  # Máximo 2 linhas
                    x_centro = (largura - len(parte) * 12) // 2
                    self.generator.adicionar_texto(x_centro, y_pos, parte, fonte=3)
                    y_pos += 30
            else:
                x_centro = (largura - len(faccao) * 12) // 2
                self.generator.adicionar_texto(x_centro, y_pos, faccao, fonte=3)
                y_pos += 40
        
        # 5. CIDADE e REGIÃO
        cidade_texto = ""
        if etiqueta_data['cidade']:
            cidade = self.generator.remover_acentos(etiqueta_data['cidade'])
            cidade_texto = f"CIDADE: {cidade}"
        
        regiao_texto = ""
        if etiqueta_data['regiao']:
            regiao = self.generator.remover_acentos(etiqueta_data['regiao'])
            regiao_texto = f"REGIAO: {regiao}"
        
        if cidade_texto and regiao_texto:
            # Tentar colocar na mesma linha
            comprimento_total = len(cidade_texto) + len(regiao_texto) + 3
            if comprimento_total * 8 <= largura - 80:  # 80 pontos de margem
                self.generator.adicionar_texto(40, y_pos, cidade_texto, fonte=3)
                self.generator.adicionar_texto(40 + len(cidade_texto) * 8 + 150, y_pos, regiao_texto, fonte=3)
                y_pos += 40
            else:
                # Em linhas separadas
                self.generator.adicionar_texto(40, y_pos, cidade_texto, fonte=3)
                y_pos += 40
                self.generator.adicionar_texto(40, y_pos, regiao_texto, fonte=3)
                y_pos += 40
        elif cidade_texto:
            self.generator.adicionar_texto(40, y_pos, cidade_texto, fonte=3)
            y_pos += 40
        elif regiao_texto:
            self.generator.adicionar_texto(40, y_pos, regiao_texto, fonte=3)
            y_pos += 40
        
        # 6. FRAÇÃO (centro, fonte maior)
        if etiqueta_data['fracao']:
            fracao = self.generator.remover_acentos(etiqueta_data['fracao'])
            x_centro = (largura - len(fracao) * 24) // 2  # Fonte 2x maior
            self.generator.adicionar_texto(x_centro, y_pos + 20, fracao, fonte=4, tamanho_h=2, tamanho_v=2)
        
        self.generator.finalizar_etiqueta()
        return self.generator.obter_comandos()

class ImpressoraBPLB:
    def __init__(self, nome_impressora=None):
        self.nome_impressora = nome_impressora
        self.conexao_ativa = False
        
    def listar_impressoras(self):
        """Lista todas as impressoras disponíveis"""
        try:
            impressoras = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            return [printer[2] for printer in impressoras]
        except:
            return []
    
    def selecionar_impressora(self):
        """Permite ao usuário selecionar uma impressora"""
        impressoras = self.listar_impressoras()
        
        if not impressoras:
            print("❌ Nenhuma impressora encontrada!")
            return False
        
        print("\n📋 Impressoras disponíveis:")
        for i, nome in enumerate(impressoras, 1):
            print(f"  {i:2d}. {nome}")
        
        try:
            escolha = input(f"\nSelecione a impressora (1-{len(impressoras)}) ou Enter para padrão: ").strip()
            
            if escolha == "":
                self.nome_impressora = win32print.GetDefaultPrinter()
                print(f"✅ Usando impressora padrão: {self.nome_impressora}")
            else:
                idx = int(escolha) - 1
                if 0 <= idx < len(impressoras):
                    self.nome_impressora = impressoras[idx]
                    print(f"✅ Impressora selecionada: {self.nome_impressora}")
                else:
                    print("❌ Seleção inválida!")
                    return False
            return True
        except ValueError:
            print("❌ Entrada inválida!")
            return False
    
    def enviar_comandos(self, comandos_bplb):
        """Envia comandos BPLB para a impressora"""
        if not self.nome_impressora:
            print("❌ Nenhuma impressora selecionada!")
            return False
        
        try:
            # Converter para bytes se necessário
            if isinstance(comandos_bplb, str):
                dados = comandos_bplb.encode('utf-8', 'ignore')
            else:
                dados = comandos_bplb
            
            # Abrir a impressora
            hprinter = win32print.OpenPrinter(self.nome_impressora)
            
            try:
                # Iniciar documento
                job_id = win32print.StartDocPrinter(hprinter, 1, ("Etiqueta BPLB", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                
                # Enviar dados
                win32print.WritePrinter(hprinter, dados)
                
                # Finalizar
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
                
                print(f"✅ Comandos enviados para {self.nome_impressora}")
                self.conexao_ativa = True
                return True
                
            except Exception as e:
                print(f"❌ Erro ao enviar para impressora: {e}")
                return False
            finally:
                win32print.ClosePrinter(hprinter)
                
        except Exception as e:
            print(f"❌ Erro de conexão com impressora: {e}")
            return False

# Classe PPLAParser (mantida similar à original)
class PPLAParser:
    def __init__(self):
        self.etiquetas = []
    
    def parse_file(self, file_path):
        """Analisa um arquivo PPLA completo"""
        if not os.path.exists(file_path):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Padrão para encontrar etiquetas PPLA
            padrao_etiqueta = r'(<xpml><page quantity=\'0\'[^>]*>.*?Q0001\s*E\s*<xpml></page></xpml><xpml><end/></xpml>)'
            etiquetas_raw = re.findall(padrao_etiqueta, content, re.DOTALL)
            
            if not etiquetas_raw:
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
        """Processa uma única etiqueta raw"""
        content = re.sub(r'<[^>]*>', '', etiqueta_raw)
        content = re.sub(r'[\x00-\x09\x0B-\x1F\x7F]', ' ', content)
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
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
            'textos': []
        }
        
        textos_coletados = []
        for line in lines:
            if line.startswith('19') and len(line) >= 15:
                texto = line[15:].strip()
                if texto:
                    textos_coletados.append(texto)
            elif line.startswith('1e') and len(line) > 2:
                codigo = line[2:].strip()
                if codigo:
                    data['codigos'].append(codigo)
        
        self._processar_textos_sequencial(textos_coletados, data)
        return data
    
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
    
            i += 1

def visualizar_etiqueta_bplb(comandos_bplb):
    """Exibe uma visualização aproximada da etiqueta BPLB"""
    print("\n📋 VISUALIZAÇÃO DA ETIQUETA BPLB:")
    print("=" * 50)
    
    # Extrair textos dos comandos
    textos = []
    for linha in comandos_bplb.split('\n'):
        if linha.startswith('A'):
            # Extrair texto entre aspas
            partes = linha.split('"')
            if len(partes) >= 2:
                textos.append(partes[1])
    
    # Simular layout
    largura = 50
    print("┌" + "─" * largura + "┐")
    
    for texto in textos:
        if texto:
            # Limitar texto à largura
            if len(texto) > largura:
                texto = texto[:largura-3] + "..."
            # Centralizar aproximadamente
            espacos = largura - len(texto)
            margem_esq = espacos // 2
            margem_dir = espacos - margem_esq
            print(f"│{' ' * margem_esq}{texto}{' ' * margem_dir}│")
    
    print("└" + "─" * largura + "┘")

def processar_e_imprimir(file_path, imprimir=True, impressora_personalizada=None):
    """Processa arquivo PPLA e imprime em BPLB"""
    print(f"\n📄 Processando: {file_path}")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("-" * 60)
    
    # 1. Analisar arquivo PPLA
    parser = PPLAParser()
    if not parser.parse_file(file_path):
        print("❌ Falha ao processar arquivo ou nenhuma etiqueta encontrada")
        return
    
    print(f"✅ {len(parser.etiquetas)} etiqueta(s) encontrada(s)")
    
    # 2. Configurar impressora se for imprimir
    impressora = None
    if imprimir:
        impressora = ImpressoraBPLB()
        
        if impressora_personalizada:
            impressora.nome_impressora = impressora_personalizada
            print(f"🔧 Usando impressora configurada: {impressora_personalizada}")
        else:
            if not impressora.selecionar_impressora():
                print("❌ Nenhuma impressora selecionada. Salvando apenas os comandos BPLB.")
                imprimir = False
    
    # 3. Converter e enviar cada etiqueta
    converter = PPLAtoBPLBConverter()
    
    for i, etiqueta in enumerate(parser.etiquetas):
        print(f"\n🔄 Convertendo etiqueta {i+1}...")
        
        # Converter para BPLB
        comandos_bplb = converter.converter_etiqueta(etiqueta)
        
        # Visualizar etiqueta
        visualizar_etiqueta_bplb(comandos_bplb)
        
        # Salvar comandos em arquivo
        nome_base = os.path.splitext(os.path.basename(file_path))[0]
        pasta_bplb = os.path.join(os.path.dirname(file_path), "bplb_output")
        
        if not os.path.exists(pasta_bplb):
            os.makedirs(pasta_bplb)
        
        arquivo_bplb = os.path.join(pasta_bplb, f"{nome_base}_etq{i+1}.bplb")
        
        try:
            with open(arquivo_bplb, 'w', encoding='utf-8') as f:
                f.write(comandos_bplb)
            print(f"💾 Comandos BPLB salvos em: {arquivo_bplb}")
            
            # Mostrar preview do arquivo
            print("\n📄 PREVIEW DO ARQUIVO BPLB:")
            print("-" * 40)
            linhas = comandos_bplb.split('\n')[:15]  # Mostrar primeiras 15 linhas
            for linha in linhas:
                if linha.strip():
                    print(f"  {linha[:60]}..." if len(linha) > 60 else f"  {linha}")
            print("-" * 40)
            
        except Exception as e:
            print(f"⚠️  Erro ao salvar arquivo BPLB: {e}")
        
        # Imprimir se solicitado
        if imprimir and impressora and impressora.nome_impressora:
            print(f"\n🖨️  Enviando etiqueta {i+1} para impressão...")
            if impressora.enviar_comandos(comandos_bplb):
                print(f"✅ Etiqueta {i+1} enviada com sucesso!")
            else:
                print(f"❌ Falha ao enviar etiqueta {i+1}")
            
            # Pequena pausa entre etiquetas
            if i < len(parser.etiquetas) - 1:
                time.sleep(2)
    
    print("\n" + "="*60)
    print("✅ Processamento concluído!")
    if imprimir and impressora and impressora.nome_impressora:
        print(f"📤 Total de {len(parser.etiquetas)} etiqueta(s) enviada(s) para {impressora.nome_impressora}")
    print("="*60)

def menu_principal():
    """Menu interativo principal"""
    print("\n" + "="*60)
    print("CONVERSOR PPLA → BPLB - IMPRESSORA BPT-L42")
    print("="*60)
    print("\nOpções disponíveis:")
    print("1. Processar arquivo e imprimir")
    print("2. Processar arquivo (apenas converter)")
    print("3. Configurar impressora específica")
    print("4. Testar exemplo com etiqueta CONSERTO")
    print("5. Sair")
    
    # Configuração de impressora
    impressora_configurada = None
    
    while True:
        try:
            opcao = input("\nEscolha uma opção (1-5): ").strip()
            
            if opcao == "1":
                caminho = input("Digite o caminho completo do arquivo PPLA: ").strip()
                if os.path.exists(caminho):
                    processar_e_imprimir(caminho, imprimir=True, impressora_personalizada=impressora_configurada)
                else:
                    print("❌ Arquivo não encontrado!")
                    
            elif opcao == "2":
                caminho = input("Digite o caminho completo do arquivo PPLA: ").strip()
                if os.path.exists(caminho):
                    processar_e_imprimir(caminho, imprimir=False)
                else:
                    print("❌ Arquivo não encontrado!")
                    
            elif opcao == "3":
                impressora = ImpressoraBPLB()
                impressoras = impressora.listar_impressoras()
                if impressoras:
                    print("\n📋 Impressoras disponíveis:")
                    for i, nome in enumerate(impressoras, 1):
                        print(f"  {i:2d}. {nome}")
                    
                    try:
                        escolha = input("\nSelecione o número da impressora ou Enter para cancelar: ").strip()
                        if escolha and escolha.isdigit():
                            idx = int(escolha) - 1
                            if 0 <= idx < len(impressoras):
                                impressora_configurada = impressoras[idx]
                                print(f"✅ Impressora configurada: {impressora_configurada}")
                            else:
                                print("❌ Número inválido!")
                        else:
                            print("❌ Configuração cancelada.")
                    except ValueError:
                        print("❌ Entrada inválida!")
                else:
                    print("❌ Nenhuma impressora encontrada!")
                    
            elif opcao == "4":
                testar_exemplo()
                
            elif opcao == "5":
                print("Saindo...")
                break
            else:
                print("Opção inválida! Escolha 1, 2, 3, 4 ou 5.")
                
        except KeyboardInterrupt:
            print("\nSaindo...")
            break
        except Exception as e:
            print(f"Erro: {e}")

def testar_exemplo():
    """Testa com um exemplo de etiqueta CONSERTO"""
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
<xpml></page></xpml><xpml><end/></xpml>"""
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(exemplo)
        temp_file = f.name
    
    print("\n🧪 TESTANDO CONVERSÃO PPLA → BPLB")
    print("=" * 60)
    
    processar_e_imprimir(temp_file, imprimir=False)
    
    os.unlink(temp_file)

# Função para configuração rápida
def configuracao_rapida():
    """Configuração rápida para uso com BPT-L42"""
    print("\n⚙️  CONFIGURAÇÃO RÁPIDA BPT-L42")
    print("-" * 40)
    
    # Verificar se pywin32 está instalado
    try:
        import win32print
        print("✅ pywin32 instalado")
    except ImportError:
        print("❌ pywin32 não está instalado!")
        print("   Instale com: pip install pywin32")
        return
    
    # Listar impressoras
    impressora = ImpressoraBPLB()
    impressoras = impressora.listar_impressoras()
    
    if impressoras:
        print(f"\n📋 {len(impressoras)} impressora(s) encontrada(s):")
        for nome in impressoras:
            if "BPT" in nome.upper() or "L42" in nome or "ELGIN" in nome.upper():
                print(f"  ✅ {nome} (possível BPT-L42)")
            else:
                print(f"  • {nome}")
        
        padrao = win32print.GetDefaultPrinter()
        print(f"\n📌 Impressora padrão: {padrao}")
        
        # Sugerir configuração
        usar_padrao = input("\nUsar impressora padrão? (S/N): ").strip().upper()
        if usar_padrao == 'S':
            print(f"✅ Configurado para usar: {padrao}")
            return padrao
    else:
        print("❌ Nenhuma impressora encontrada!")
    
    return None

if __name__ == "__main__":
    # Mostrar configuração rápida
    impressora_config = configuracao_rapida()
    
    # Iniciar menu principal
    menu_principal()