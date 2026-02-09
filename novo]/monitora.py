import os
import time
import hashlib
import re
import win32print
import win32api
import unicodedata
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ====================== CONFIGURAÇÃO DA IMPRESSORA ======================
# Configura a impressora uma vez no início do programa
IMPRESSORA_SELECIONADA = None

def configurar_impressora():
    """Configura a impressora uma vez no início do programa"""
    global IMPRESSORA_SELECIONADA
    
    print("\n" + "="*60)
    print("🖨️  CONFIGURAÇÃO DA IMPRESSORA BPT-L42")
    print("="*60)
    
    # Verificar se pywin32 está instalado
    try:
        import win32print
        print("✅ pywin32 instalado")
    except ImportError:
        print("❌ pywin32 não está instalado!")
        print("   Instale com: pip install pywin32")
        return False
    
    # Verificar se watchdog está instalado
    try:
        from watchdog.observers import Observer
        print("✅ watchdog instalado")
    except ImportError:
        print("⚠️  watchdog não está instalado!")
        print("   Instale com: pip install watchdog")
        print("   (Necessário para monitoramento automático)")
    
    # Listar impressoras
    impressora = ImpressoraBPLB()
    impressoras = impressora.listar_impressoras()
    
    if not impressoras:
        print("❌ Nenhuma impressora encontrada!")
        print("   Verifique se a impressora está conectada e instalada.")
        return False
    
    print(f"\n📋 {len(impressoras)} impressora(s) encontrada(s):")
    for i, nome in enumerate(impressoras, 1):
        # Identificar possíveis BPT-L42
        if "BPT" in nome.upper() or "L42" in nome or "ELGIN" in nome.upper():
            print(f"  {i:2d}. ✅ {nome} (possível BPT-L42)")
        else:
            print(f"  {i:2d}.   {nome}")
    
    # Impressora padrão
    try:
        padrao = win32print.GetDefaultPrinter()
        print(f"\n📌 Impressora padrão do sistema: {padrao}")
    except:
        padrao = None
    
    print("\nEscolha uma opção:")
    print("  0. Usar impressora padrão do sistema")
    for i, nome in enumerate(impressoras, 1):
        print(f"  {i}. {nome}")
    
    while True:
        try:
            escolha = input(f"\nSelecione a impressora (0-{len(impressoras)}): ").strip()
            
            if escolha == "0" or escolha == "":
                if padrao:
                    IMPRESSORA_SELECIONADA = padrao
                    print(f"✅ Impressora configurada: {IMPRESSORA_SELECIONADA}")
                    return True
                else:
                    print("❌ Nenhuma impressora padrão encontrada!")
                    continue
            
            idx = int(escolha) - 1
            if 0 <= idx < len(impressoras):
                IMPRESSORA_SELECIONADA = impressoras[idx]
                print(f"✅ Impressora configurada: {IMPRESSORA_SELECIONADA}")
                return True
            else:
                print(f"❌ Opção inválida! Escolha entre 0 e {len(impressoras)}")
                
        except ValueError:
            print("❌ Digite um número válido!")
        except Exception as e:
            print(f"❌ Erro: {e}")

# ====================== CLASSES DO SISTEMA ======================

class BPLBGenerator:
    def __init__(self):
        self.comandos = []
        self.largura_etiqueta = 800
        self.altura_etiqueta = 550
        
    def remover_acentos(self, texto):
        """Remove acentos e caracteres especiais"""
        if not texto:
            return ""
        texto = unicodedata.normalize('NFKD', str(texto))
        texto = ''.join([c for c in texto if not unicodedata.combining(c)])
        texto = texto.replace('Ç', 'C').replace('ç', 'c')
        texto = texto.replace('Ã', 'A').replace('ã', 'a')
        texto = texto.replace('Õ', 'O').replace('õ', 'o')
        texto = texto.replace('Â', 'A').replace('â', 'a')
        texto = texto.replace('Ê', 'E').replace('ê', 'e')
        texto = texto.replace('Î', 'I').replace('î', 'i')
        texto = texto.replace('Ô', 'O').replace('ô', 'o')
        texto = texto.replace('Û', 'U').replace('û', 'u')
        return texto.upper()
    
    def iniciar_etiqueta(self):
        """Inicia uma nova etiqueta BPLB"""
        self.comandos = []
        self.comandos.append("N")
        self.comandos.append("D7")
        self.comandos.append("S3")
        self.comandos.append("JF")
        self.comandos.append(f"Q{self.altura_etiqueta}")
        self.comandos.append(f"q{self.largura_etiqueta}")
        
    def adicionar_texto(self, x, y, texto, fonte=1, tamanho_h=1, tamanho_v=1):
        """Adiciona comando de texto BPLB"""
        texto_limpo = self.remover_acentos(texto)
        cmd = f"A{x},{y},0,{fonte},{tamanho_h},{tamanho_v},N,\"{texto_limpo}\""
        self.comandos.append(cmd)
        
    def adicionar_linha_horizontal(self, x, y, comprimento, espessura=1):
        cmd = f"LE{x},{y},{comprimento},{espessura}"
        self.comandos.append(cmd)
    
    def adicionar_linha_vertical(self, x, y, comprimento, espessura=1):
        cmd = f"LE{x},{y},{espessura},{comprimento}"
        self.comandos.append(cmd)
    
    def adicionar_borda(self, x1, y1, x2, y2, espessura=2):
        self.comandos.append(f"LE{x1},{y1},{x2-x1},{espessura}")
        self.comandos.append(f"LE{x1},{y2},{x2-x1},{espessura}")
        self.comandos.append(f"LE{x1},{y1},{espessura},{y2-y1}")
        self.comandos.append(f"LE{x2-espessura},{y1},{espessura},{y2-y1}")
        
    def finalizar_etiqueta(self, quantidade=1):
        self.comandos.append(f"P{quantidade}")
        
    def obter_comandos(self):
        return "\n".join(self.comandos) + "\n"
    
    def obter_comandos_bytes(self):
        return self.obter_comandos().encode('utf-8', 'ignore')

class PPLAtoBPLBConverter:
    def __init__(self):
        self.parser = PPLAParser()
        self.generator = BPLBGenerator()
        
    def converter_etiqueta(self, etiqueta_data):
        self.generator.iniciar_etiqueta()
        largura = self.generator.largura_etiqueta
        altura = self.generator.altura_etiqueta
        
        self.generator.adicionar_borda(20, 20, largura-20, altura-20, espessura=2)
        y_pos = 50
        
        if etiqueta_data['tipo']:
            tipo = self.generator.remover_acentos(etiqueta_data['tipo'])
            x_pos = (largura - len(tipo) * 16) // 2
            self.generator.adicionar_texto(x_pos, y_pos, tipo, fonte=3, tamanho_h=3, tamanho_v=3)
            y_pos += 70
        
        self.generator.adicionar_linha_horizontal(30, y_pos-10, largura-60)
        y_pos += 20
        
        op_texto = ""
        if etiqueta_data['op']:
            op_numeros = ''.join(filter(str.isdigit, etiqueta_data['op']))
            op_texto = f"OP: {op_numeros[:9]}"
        
        ref_texto = ""
        if etiqueta_data['referencia']:
            ref_numeros = ''.join(filter(str.isdigit, etiqueta_data['referencia']))
            ref_texto = f"REF: {ref_numeros[:9]}"
        
        if op_texto and ref_texto:
            self.generator.adicionar_texto(40, y_pos, op_texto, fonte=3)
            ref_x = largura - len(ref_texto) * 20 - 40
            self.generator.adicionar_texto(ref_x, y_pos, ref_texto, fonte=3)
        elif op_texto:
            self.generator.adicionar_texto(40, y_pos, op_texto, fonte=3)
        elif ref_texto:
            self.generator.adicionar_texto(40, y_pos, ref_texto, fonte=3)
        
        y_pos += 50
        
        if etiqueta_data['descricao']:
            descricao = self.generator.remover_acentos(etiqueta_data['descricao'])
            if len(descricao) > 30:
                palavras = descricao.split()
                linha_atual = []
                comprimento_atual = 0
                partes = []
                
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
                
                for i, parte in enumerate(partes[:2]):
                    x_centro = (largura - len(parte) * 12) // 2
                    self.generator.adicionar_texto(x_centro, y_pos, parte, fonte=3)
                    y_pos += 40 if i == 0 else 30
            else:
                x_centro = (largura - len(descricao) * 12) // 2
                self.generator.adicionar_texto(x_centro, y_pos, descricao, fonte=3)
                y_pos += 50
        
        y_pos += 20
        
        if etiqueta_data['faccao']:
            faccao = self.generator.remover_acentos(etiqueta_data['faccao'])
            self.generator.adicionar_texto(40, y_pos, "FACCÃO:", fonte=3)
            y_pos += 40
            
            if len(faccao) > 30:
                partes = [faccao[i:i+30] for i in range(0, len(faccao), 30)]
                for parte in partes[:2]:
                    x_centro = (largura - len(parte) * 12) // 2
                    self.generator.adicionar_texto(x_centro, y_pos, parte, fonte=3)
                    y_pos += 30
            else:
                x_centro = (largura - len(faccao) * 12) // 2
                self.generator.adicionar_texto(x_centro, y_pos, faccao, fonte=3)
                y_pos += 40
        
        cidade_texto = ""
        if etiqueta_data['cidade']:
            cidade = self.generator.remover_acentos(etiqueta_data['cidade'])
            cidade_texto = f"CIDADE: {cidade}"
        
        regiao_texto = ""
        if etiqueta_data['regiao']:
            regiao = self.generator.remover_acentos(etiqueta_data['regiao'])
            regiao_texto = f"REGIAO: {regiao}"
        
        if cidade_texto and regiao_texto:
            comprimento_total = len(cidade_texto) + len(regiao_texto) + 3
            if comprimento_total * 8 <= largura - 80:
                self.generator.adicionar_texto(40, y_pos, cidade_texto, fonte=3)
                self.generator.adicionar_texto(40 + len(cidade_texto) * 8 + 150, y_pos, regiao_texto, fonte=3)
                y_pos += 40
            else:
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
        
        if etiqueta_data['fracao']:
            fracao = self.generator.remover_acentos(etiqueta_data['fracao'])
            x_centro = (largura - len(fracao) * 24) // 2
            self.generator.adicionar_texto(x_centro, y_pos + 20, fracao, fonte=4, tamanho_h=2, tamanho_v=2)
        
        self.generator.finalizar_etiqueta()
        return self.generator.obter_comandos()

class ImpressoraBPLB:
    def __init__(self, nome_impressora=None):
        self.nome_impressora = nome_impressora or IMPRESSORA_SELECIONADA
        self.conexao_ativa = False
        
    def listar_impressoras(self):
        try:
            impressoras = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            return [printer[2] for printer in impressoras]
        except:
            return []
    
    def enviar_comandos(self, comandos_bplb):
        """Envia comandos BPLB para a impressora configurada"""
        if not self.nome_impressora:
            print("❌ Nenhuma impressora configurada!")
            return False
        
        try:
            if isinstance(comandos_bplb, str):
                dados = comandos_bplb.encode('utf-8', 'ignore')
            else:
                dados = comandos_bplb
            
            hprinter = win32print.OpenPrinter(self.nome_impressora)
            
            try:
                job_id = win32print.StartDocPrinter(hprinter, 1, ("Etiqueta BPLB", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, dados)
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

class PPLAParser:
    def __init__(self):
        self.etiquetas = []
    
    def parse_file(self, file_path):
        if not os.path.exists(file_path):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
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
        i = 0
        while i < len(textos):
            texto = textos[i]
            data['textos'].append(texto)
    
            if texto == 'OP:' and i + 1 < len(textos):
                data['op'] = textos[i + 3]
    
            elif texto == 'Ref:' and i + 1 < len(textos):
                data['referencia'] = textos[i + 1]
    
            elif texto in ('Faccao:', 'Facção:') and i + 1 < len(textos):
                data['faccao'] = textos[i + 1]
    
            elif texto == 'Cidade:' and i + 1 < len(textos):
                data['cidade'] = textos[i + 1]
    
            elif texto in ('Regiao:', 'Região:') and i + 1 < len(textos):
                data['regiao'] = textos[i + 1]
    
            elif 'CONSERTO' in texto:
                data['tipo'] = 'CONSERTO'
    
            elif any(p in texto for p in ('CAMISETA', 'BLUSA', 'CALCA')):
                data['descricao'] = texto
    
            elif re.match(r'^\d+/\d+$', texto):
                data['fracao'] = texto
    
            i += 1

# ====================== FUNÇÕES PRINCIPAIS ======================

def visualizar_etiqueta_bplb(comandos_bplb):
    print("\n📋 VISUALIZAÇÃO DA ETIQUETA BPLB:")
    print("=" * 50)
    
    textos = []
    for linha in comandos_bplb.split('\n'):
        if linha.startswith('A'):
            partes = linha.split('"')
            if len(partes) >= 2:
                textos.append(partes[1])
    
    largura = 50
    print("┌" + "─" * largura + "┐")
    
    for texto in textos:
        if texto:
            if len(texto) > largura:
                texto = texto[:largura-3] + "..."
            espacos = largura - len(texto)
            margem_esq = espacos // 2
            margem_dir = espacos - margem_esq
            print(f"│{' ' * margem_esq}{texto}{' ' * margem_dir}│")
    
    print("└" + "─" * largura + "┘")

def processar_e_imprimir(file_path, imprimir=True):
    """Processa arquivo PPLA e imprime usando a impressora configurada"""
    global IMPRESSORA_SELECIONADA
    
    print(f"\n📄 Processando: {file_path}")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🖨️  Impressora: {IMPRESSORA_SELECIONADA}")
    print("-" * 60)
    
    parser = PPLAParser()
    if not parser.parse_file(file_path):
        print("❌ Falha ao processar arquivo ou nenhuma etiqueta encontrada")
        return
    
    print(f"✅ {len(parser.etiquetas)} etiqueta(s) encontrada(s)")
    
    impressora = None
    if imprimir:
        if not IMPRESSORA_SELECIONADA:
            print("❌ Nenhuma impressora configurada!")
            print("   Use a opção 3 para configurar uma impressora.")
            imprimir = False
        else:
            impressora = ImpressoraBPLB(IMPRESSORA_SELECIONADA)
    
    converter = PPLAtoBPLBConverter()
    
    for i, etiqueta in enumerate(parser.etiquetas):
        print(f"\n🔄 Convertendo etiqueta {i+1}...")
        
        comandos_bplb = converter.converter_etiqueta(etiqueta)
        visualizar_etiqueta_bplb(comandos_bplb)
        
        nome_base = os.path.splitext(os.path.basename(file_path))[0]
        pasta_bplb = os.path.join(os.path.dirname(file_path), "bplb_output")
        
        if not os.path.exists(pasta_bplb):
            os.makedirs(pasta_bplb)
        
        arquivo_bplb = os.path.join(pasta_bplb, f"{nome_base}_etq{i+1}.bplb")
        
        try:
            with open(arquivo_bplb, 'w', encoding='utf-8') as f:
                f.write(comandos_bplb)
            print(f"💾 Comandos BPLB salvos em: {arquivo_bplb}")
            
            print("\n📄 PREVIEW DO ARQUIVO BPLB:")
            print("-" * 40)
            linhas = comandos_bplb.split('\n')[:15]
            for linha in linhas:
                if linha.strip():
                    print(f"  {linha[:60]}..." if len(linha) > 60 else f"  {linha}")
            print("-" * 40)
            
        except Exception as e:
            print(f"⚠️  Erro ao salvar arquivo BPLB: {e}")
        
        if imprimir and impressora:
            print(f"\n🖨️  Enviando etiqueta {i+1} para impressão...")
            if impressora.enviar_comandos(comandos_bplb):
                print(f"✅ Etiqueta {i+1} enviada com sucesso!")
            else:
                print(f"❌ Falha ao enviar etiqueta {i+1}")
            
            if i < len(parser.etiquetas) - 1:
                time.sleep(2)
    
    print("\n" + "="*60)
    print("✅ Processamento concluído!")
    if imprimir and impressora:
        print(f"📤 Total de {len(parser.etiquetas)} etiqueta(s) enviada(s) para {IMPRESSORA_SELECIONADA}")
    print("="*60)

# ====================== MONITORAMENTO ======================

class ArquivoAlteradoHandler(FileSystemEventHandler):
    def __init__(self):
        self.ultimo_hash = None
        self.arquivo_processando = False
        print(f"\n🔍 Monitorando alterações no arquivo...")
        print(f"📁 Pasta: C:\\Imp")
        print(f"📄 Arquivo: Imprime.txt")
        print(f"🖨️  Impressora: {IMPRESSORA_SELECIONADA}")
        print("⏳ Aguardando alterações...")
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('Imprime.txt'):
            print(f"\n🔄 Alteração detectada em: {event.src_path}")
            
            if self.arquivo_processando:
                print("⚠️  Já processando arquivo, aguarde...")
                return
                
            self.arquivo_processando = True
            
            try:
                time.sleep(0.5)
                hash_atual = self.calcular_hash(event.src_path)
                
                if hash_atual != self.ultimo_hash:
                    self.ultimo_hash = hash_atual
                    print(f"📊 Hash do arquivo: {hash_atual[:16]}...")
                    print("🔄 Iniciando processamento...")
                    processar_e_imprimir(event.src_path, imprimir=True)
                else:
                    print("ℹ️  Arquivo não mudou (mesmo hash), ignorando...")
                    
            except Exception as e:
                print(f"❌ Erro ao processar arquivo alterado: {e}")
            finally:
                self.arquivo_processando = False
    
    def calcular_hash(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return None

def iniciar_monitoramento():
    """Inicia o monitoramento da pasta C:\Imp"""
    global IMPRESSORA_SELECIONADA
    
    pasta_monitorada = r"C:\Imp"
    arquivo_alvo = "Imprime.txt"
    
    if not IMPRESSORA_SELECIONADA:
        print("❌ Nenhuma impressora configurada!")
        print("   Configure uma impressora antes de iniciar o monitoramento.")
        return
    
    if not os.path.exists(pasta_monitorada):
        print(f"📁 Criando pasta: {pasta_monitorada}")
        try:
            os.makedirs(pasta_monitorada, exist_ok=True)
        except Exception as e:
            print(f"❌ Erro ao criar pasta: {e}")
            return
    
    caminho_arquivo = os.path.join(pasta_monitorada, arquivo_alvo)
    
    if not os.path.exists(caminho_arquivo):
        print(f"📄 Criando arquivo: {arquivo_alvo}")
        try:
            with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                f.write("# Arquivo para impressão de etiquetas PPLA\n")
                f.write("# O sistema irá processar automaticamente\n")
        except Exception as e:
            print(f"❌ Erro ao criar arquivo: {e}")
    
    print(f"\n{'='*60}")
    print("🚀 INICIANDO MONITORAMENTO AUTOMÁTICO")
    print(f"{'='*60}")
    print(f"📁 Pasta: {pasta_monitorada}")
    print(f"📄 Arquivo: {arquivo_alvo}")
    print(f"🖨️  Impressora: {IMPRESSORA_SELECIONADA}")
    print(f"📅 Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"\n📝 O que fazer:")
    print(f"   1. Cole o conteúdo PPLA no arquivo {arquivo_alvo}")
    print(f"   2. Salve o arquivo (Ctrl+S)")
    print(f"   3. O sistema processará e imprimirá automaticamente")
    print(f"\n⚠️  Pressione Ctrl+C para parar")
    print(f"{'='*60}\n")
    
    event_handler = ArquivoAlteradoHandler()
    observer = Observer()
    observer.schedule(event_handler, pasta_monitorada, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Interrompendo monitoramento...")
        observer.stop()
    except Exception as e:
        print(f"❌ Erro no monitoramento: {e}")
    
    observer.join()
    print("👋 Monitoramento encerrado.")

def testar_exemplo():
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

def reconfigurar_impressora():
    """Permite reconfigurar a impressora"""
    global IMPRESSORA_SELECIONADA
    print("\n🔄 Reconfigurando impressora...")
    if configurar_impressora():
        print(f"✅ Nova impressora configurada: {IMPRESSORA_SELECIONADA}")
    else:
        print("❌ Falha ao reconfigurar impressora")

def menu_principal():
    """Menu interativo principal"""
    print("\n" + "="*60)
    print("CONVERSOR PPLA → BPLB - IMPRESSORA BPT-L42")
    print("="*60)
    print(f"🖨️  Impressora atual: {IMPRESSORA_SELECIONADA or 'Não configurada'}")
    print("\nOpções disponíveis:")
    print("1. Processar arquivo e imprimir")
    print("2. Processar arquivo (apenas converter)")
    print("3. Reconfigurar impressora")
    print("4. Testar exemplo com etiqueta CONSERTO")
    print("5. Iniciar monitoramento automático da pasta C:\\Imp")
    print("6. Sair")
    
    while True:
        try:
            opcao = input("\nEscolha uma opção (1-6): ").strip()
            
            if opcao == "1":
                if not IMPRESSORA_SELECIONADA:
                    print("❌ Nenhuma impressora configurada!")
                    print("   Use a opção 3 para configurar uma impressora.")
                    continue
                    
                caminho = input("Digite o caminho completo do arquivo PPLA: ").strip()
                if os.path.exists(caminho):
                    processar_e_imprimir(caminho, imprimir=True)
                else:
                    print("❌ Arquivo não encontrado!")
                    
            elif opcao == "2":
                caminho = input("Digite o caminho completo do arquivo PPLA: ").strip()
                if os.path.exists(caminho):
                    processar_e_imprimir(caminho, imprimir=False)
                else:
                    print("❌ Arquivo não encontrado!")
                    
            elif opcao == "3":
                reconfigurar_impressora()
                
            elif opcao == "4":
                testar_exemplo()
                
            elif opcao == "5":
                iniciar_monitoramento()
                
            elif opcao == "6":
                print("Saindo...")
                break
            else:
                print("Opção inválida! Escolha 1, 2, 3, 4, 5 ou 6.")
                
        except KeyboardInterrupt:
            print("\nSaindo...")
            break
        except Exception as e:
            print(f"Erro: {e}")

# ====================== EXECUÇÃO PRINCIPAL ======================

if __name__ == "__main__":
    # Configurar impressora uma vez no início
    if configurar_impressora():
        print(f"\n✅ Impressora configurada com sucesso!")
        print(f"🖨️  Usando: {IMPRESSORA_SELECIONADA}")
        
        # Iniciar menu principal
        menu_principal()
    else:
        print("\n❌ Falha ao configurar impressora.")
        print("   O programa não pode continuar sem uma impressora configurada.")
        input("Pressione Enter para sair...")