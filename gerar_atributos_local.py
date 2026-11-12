#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador automático de atributos para "O Adivinho", usando:
  - Busca na web (DuckDuckGo, sem precisar de chave de API) para embasar as respostas
  - Um modelo de IA rodando localmente via Ollama (ex: llama3.1, mistral, qwen2.5)

O script:
  1. Lê uma lista de nomes de um arquivo .txt (um por linha)
  2. Para cada nome, busca um resumo na web
  3. Manda esse resumo + a lista de perguntas para o modelo local, pedindo um JSON
     com os 76 atributos (true/false/null)
  4. Ao final, mescla tudo automaticamente no PERSONAGENS do seu o_adivinho.html
     e salva um novo arquivo .html pronto pra usar

Veja o arquivo INSTRUCOES.md para o passo a passo de instalação e uso.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

OLLAMA_URL = "http://localhost:11434/api/generate"

# Ordem exata usada no o_adivinho.html (76 atributos)
ALL_KEYS = [
    "real", "homem", "vivo", "brasileiro", "americano", "europeu", "asiatico",
    "historico", "famoso_mundialmente", "artista", "musico", "ator", "cantor",
    "esportista", "jogador_futebol", "jogador_basquete", "jogador_tenis",
    "personagem_ficticio", "anime", "super_heroi", "vilao", "marvel", "dc",
    "video_game", "desenho_animado", "disney", "cientista", "politico",
    "escritor", "animal", "youtuber", "empresario", "one_piece", "naruto",
    "dragon_ball", "attack_on_titan", "mitologico", "pokemon",
    "harry_potter_universo", "star_wars", "senhor_dos_aneis",
    "religioso_mitico", "serie_tv", "jogador_ataque", "jogador_defesa",
    "ganhou_copa_do_mundo", "ativo_atualmente_esporte", "anime_acao_luta",
    "anime_fantasia_magia", "anime_misterio_ficcao", "anime_romance_comedia",
    "anime_esporte", "anime_terror", "jogo_rpg", "jogo_acao_aventura",
    "jogo_tiro_fps", "jogo_luta", "jogo_terror_sobrevivencia",
    "jogo_plataforma_familia", "friends_universo", "the_office_universo",
    "south_park_universo", "himym_universo", "got_universo",
    "musica_pagode_samba", "musica_sertanejo", "musica_funk_rap",
    "musica_gospel", "musica_mpb", "campo_fisica", "campo_biologia_medicina",
    "campo_exploracao", "campo_computacao", "ganhou_oscar", "genero_comedia",
    "ator_super_heroi_cinema",
]

# Texto de cada pergunta (o mesmo usado no jogo) — ajuda o modelo a entender
# exatamente o que cada atributo significa.
PERGUNTAS = {
    "real": "É uma pessoa real (não um personagem inventado)?",
    "homem": "É do gênero masculino?",
    "vivo": "Está vivo(a) atualmente (ou, se for fictício, é retratado como vivo)?",
    "brasileiro": "É brasileiro(a)?",
    "americano": "É das Américas (EUA, Canadá ou América Latina)?",
    "europeu": "É europeu(eia)?",
    "asiatico": "É asiático(a)?",
    "historico": "Marcou a história antes do século XX?",
    "famoso_mundialmente": "É famoso(a) no mundo inteiro?",
    "artista": "Trabalha ou trabalhou com arte (música, atuação ou escrita)?",
    "musico": "Faz ou fez música?",
    "ator": "Atua ou atuou em filmes/séries?",
    "cantor": "É cantor(a)?",
    "esportista": "Pratica ou praticou esporte profissionalmente?",
    "jogador_futebol": "Joga ou jogou futebol?",
    "jogador_basquete": "Joga ou jogou basquete?",
    "jogador_tenis": "Joga ou jogou tênis?",
    "personagem_ficticio": "É um personagem fictício, de livro, filme, jogo ou desenho?",
    "anime": "É de um anime?",
    "super_heroi": "É super-herói ou vilão de quadrinhos?",
    "vilao": "É um vilão?",
    "marvel": "É do universo Marvel?",
    "dc": "É do universo DC?",
    "video_game": "É personagem de video game?",
    "desenho_animado": "É de um desenho animado clássico?",
    "disney": "É da Disney?",
    "cientista": "É ou foi cientista?",
    "politico": "É ou foi político(a) ou líder de estado?",
    "escritor": "É ou foi escritor(a)?",
    "animal": "Tem forma ou aparência de animal?",
    "youtuber": "É youtuber ou influenciador digital?",
    "empresario": "Fundou ou dirige uma grande empresa de tecnologia ou negócios?",
    "one_piece": "É do anime/mangá One Piece?",
    "naruto": "É do anime/mangá Naruto?",
    "dragon_ball": "É do anime/mangá Dragon Ball?",
    "attack_on_titan": "É do anime/mangá Attack on Titan (Ataque dos Titãs)?",
    "mitologico": "É uma divindade ou ser mitológico?",
    "pokemon": "É do universo Pokémon?",
    "harry_potter_universo": "É do universo Harry Potter?",
    "star_wars": "É do universo Star Wars?",
    "senhor_dos_aneis": "É do universo O Senhor dos Anéis?",
    "religioso_mitico": "É uma figura religiosa importante?",
    "serie_tv": "É personagem de uma série de TV (não desenho, não anime)?",
    "jogador_ataque": "No futebol, joga (ou jogava) numa posição de ataque?",
    "jogador_defesa": "No futebol, joga (ou jogava) na defesa, meio-campo defensivo ou como goleiro?",
    "ganhou_copa_do_mundo": "Já foi campeão de uma Copa do Mundo de futebol?",
    "ativo_atualmente_esporte": "Ainda está ativo(a) como atleta profissional hoje em dia?",
    "anime_acao_luta": "O anime dele(a) é focado em lutas e ação (estilo shonen de combate)?",
    "anime_fantasia_magia": "O anime dele(a) envolve magia, poderes fantásticos ou mundos paralelos?",
    "anime_misterio_ficcao": "O anime dele(a) é de mistério, suspense ou ficção científica?",
    "anime_romance_comedia": "O anime dele(a) é mais comédia, romance ou vida escolar?",
    "anime_esporte": "O anime dele(a) é sobre esportes?",
    "anime_terror": "O anime dele(a) tem elementos de terror?",
    "jogo_rpg": "É de um jogo estilo RPG (evolução de personagem, magia, itens)?",
    "jogo_acao_aventura": "É de um jogo de ação e aventura em terceira pessoa?",
    "jogo_tiro_fps": "É de um jogo de tiro (FPS ou shooter)?",
    "jogo_luta": "É de um jogo de luta (tipo Street Fighter, Tekken, Mortal Kombat)?",
    "jogo_terror_sobrevivencia": "É de um jogo de terror ou sobrevivência?",
    "jogo_plataforma_familia": "É de um jogo de plataforma clássico ou mascote de videogame?",
    "friends_universo": "É personagem da série Friends?",
    "the_office_universo": "É personagem da série The Office?",
    "south_park_universo": "É personagem de South Park?",
    "himym_universo": "É personagem de How I Met Your Mother?",
    "got_universo": "É personagem de Game of Thrones?",
    "musica_pagode_samba": "O estilo musical dele(a) é pagode ou samba?",
    "musica_sertanejo": "O estilo musical dele(a) é sertanejo?",
    "musica_funk_rap": "O estilo musical dele(a) é funk ou rap?",
    "musica_gospel": "O estilo musical dele(a) é gospel?",
    "musica_mpb": "O estilo musical dele(a) é MPB ou bossa nova?",
    "campo_fisica": "A área principal dele(a) na ciência é física?",
    "campo_biologia_medicina": "A área principal dele(a) na ciência é biologia ou medicina?",
    "campo_exploracao": "Ficou famoso(a) por explorar ou viajar para lugares desconhecidos?",
    "campo_computacao": "A área principal dele(a) é computação ou matemática aplicada?",
    "ganhou_oscar": "Já ganhou um Oscar?",
    "genero_comedia": "É mais conhecido(a) por papéis de comédia?",
    "ator_super_heroi_cinema": "Já viveu um super-herói em um filme?",
}


def buscar_membros_categoria(categoria, idioma="pt", limite=50):
    """
    Busca nomes de páginas dentro de uma categoria da Wikipédia
    (ex: categoria='Futebolistas do Brasil', idioma='pt').
    Usa a API pública da Wikipédia — não precisa de chave de API.
    """
    membros = []
    cmcontinue = None
    prefixo = "Categoria" if idioma == "pt" else "Category"
    base_url = f"https://{idioma}.wikipedia.org/w/api.php"

    while len(membros) < limite:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"{prefixo}:{categoria}",
            "cmtype": "page",
            "cmlimit": min(500, limite - len(membros)),
            "format": "json",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        try:
            resp = requests.get(base_url, params=params, timeout=30,
                                 headers={"User-Agent": "OAdivinho-Gerador/1.0"})
            resp.raise_for_status()
            dados = resp.json()
        except Exception as e:
            print(f"  [aviso] falha ao buscar categoria '{categoria}': {e}", file=sys.stderr)
            break

        pagina = dados.get("query", {}).get("categorymembers", [])
        if not pagina:
            break
        for p in pagina:
            titulo = p.get("title", "")
            if ":" in titulo:  # ignora "Wikipédia:", "Anexo:", subcategorias etc.
                continue
            if "desambiguação" in titulo or titulo.lower().startswith("lista de"):
                continue
            membros.append(titulo)

        cmcontinue = dados.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break

    return membros[:limite]


def descobrir_nomes(categorias, idioma, limite_por_categoria):
    """Junta os nomes de várias categorias da Wikipédia, sem repetir."""
    encontrados = []
    vistos = set()
    for categoria in categorias:
        categoria = categoria.strip()
        if not categoria:
            continue
        print(f"Buscando nomes na categoria da Wikipédia: '{categoria}' ({idioma})...")
        nomes = buscar_membros_categoria(categoria, idioma=idioma, limite=limite_por_categoria)
        novos = [n for n in nomes if n not in vistos]
        print(f"  {len(novos)} nome(s) encontrado(s).")
        for n in novos:
            vistos.add(n)
            encontrados.append(n)
    return encontrados


def buscar_contexto(nome, max_resultados=5):
    """Busca o nome na web (DuckDuckGo) e retorna um resumo em texto."""
    if DDGS is None:
        print("  [aviso] pacote de busca não instalado — rode: pip install ddgs",
              file=sys.stderr)
        return ""
    trechos = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(f"{nome} biografia wikipedia", max_results=max_resultados, region="br-pt"):
                titulo = r.get("title", "")
                corpo = r.get("body", "")
                if corpo:
                    trechos.append(f"- {titulo}: {corpo}")
    except Exception as e:
        print(f"  [aviso] busca na web falhou para '{nome}': {e}", file=sys.stderr)
    return "\n".join(trechos)


def montar_prompt(nome, contexto):
    perguntas_txt = "\n".join(f"- {k}: {v}" for k, v in PERGUNTAS.items())
    contexto_txt = contexto if contexto else "(nenhum resultado de busca encontrado — use seu próprio conhecimento)"
    return f"""Você é uma base de dados factual para o jogo "O Adivinho" (estilo Akinator).

Resumo de busca na web sobre "{nome}" (pode estar incompleto ou conter ruído):
{contexto_txt}

Com base nisso e no que você sabe, responda com um objeto JSON contendo EXATAMENTE estas chaves,
cada uma com valor true, false ou null (use null só quando o atributo genuinamente não se aplica,
como gênero de um objeto/robô sem gênero definido):

{perguntas_txt}

Regras:
- Responda SOMENTE com o objeto JSON puro, sem markdown, sem ```, sem texto antes ou depois.
- "real" e "personagem_ficticio" normalmente são opostos.
- Se não tiver certeza sobre um atributo bem específico, prefira false a inventar.
"""


def chamar_ollama(prompt, modelo="llama3.1"):
    resp = requests.post(OLLAMA_URL, json={
        "model": modelo,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }, timeout=180)
    resp.raise_for_status()
    dados = resp.json()
    texto = dados.get("response", "").strip()
    texto = texto.replace("```json", "").replace("```", "").strip()
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ValueError(f"resposta sem JSON válido: {texto[:200]!r}")
    return json.loads(texto[inicio:fim + 1])


def normalizar(bruto):
    saida = {}
    for k in ALL_KEYS:
        v = bruto.get(k, False)
        saida[k] = v if v in (True, False, None) else False
    return saida


def gerar_para_nomes(nomes, modelo, pausa, checkpoint_path):
    resultados = {}
    if checkpoint_path.exists():
        resultados = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        print(f"Retomando checkpoint com {len(resultados)} nome(s) já processado(s).")

    for i, nome in enumerate(nomes, 1):
        if nome in resultados:
            continue
        print(f"[{i}/{len(nomes)}] Gerando: {nome}")
        contexto = buscar_contexto(nome)
        prompt = montar_prompt(nome, contexto)
        try:
            bruto = chamar_ollama(prompt, modelo)
            resultados[nome] = normalizar(bruto)
            print(f"  ok ({sum(1 for v in resultados[nome].values() if v is True)} atributos verdadeiros)")
        except Exception as e:
            print(f"  [erro] falha ao gerar '{nome}': {e}", file=sys.stderr)
        # salva progresso a cada nome, pra poder retomar se cair no meio do caminho
        checkpoint_path.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(pausa)

    return resultados


# ---------------------- mesclar no o_adivinho.html ----------------------

def extrair_balanceado(texto, inicio):
    """Extrai o objeto {...} balanceado a partir do índice de abertura, respeitando strings."""
    profundidade = 0
    dentro_string = False
    escape = False
    for i in range(inicio, len(texto)):
        ch = texto[i]
        if dentro_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                dentro_string = False
            continue
        if ch == '"':
            dentro_string = True
            continue
        if ch == "{":
            profundidade += 1
        elif ch == "}":
            profundidade -= 1
            if profundidade == 0:
                return texto[inicio:i + 1]
    raise ValueError("não encontrei o fechamento do objeto PERSONAGENS no HTML")


def formatar_entrada(nome, attrs):
    nome_seguro = nome.replace('"', '\\"')
    partes = []
    for k in ALL_KEYS:
        v = attrs.get(k, False)
        vs = "null" if v is None else ("true" if v else "false")
        partes.append(f'"{k}": {vs}')
    return f'"{nome_seguro}": {{{", ".join(partes)}}}'


def mesclar_no_html(html_path, novos, saida_path):
    conteudo = Path(html_path).read_text(encoding="utf-8")
    marcador = "const PERSONAGENS = "
    idx = conteudo.index(marcador)
    inicio_chave = conteudo.index("{", idx)
    texto_obj = extrair_balanceado(conteudo, inicio_chave)
    dados = json.loads(texto_obj)

    novos_validos = {}
    for nome, attrs in novos.items():
        if nome in dados:
            print(f"  (já existia na base, pulando) {nome}")
            continue
        novos_validos[nome] = attrs

    dados.update(novos_validos)

    linhas = [formatar_entrada(n, a) for n, a in dados.items()]
    novo_texto_obj = "{" + ", ".join(linhas) + "}"
    novo_conteudo = conteudo[:inicio_chave] + novo_texto_obj + conteudo[inicio_chave + len(texto_obj):]

    Path(saida_path).write_text(novo_conteudo, encoding="utf-8")
    print(f"\nArquivo salvo em: {saida_path}")
    print(f"Personagens novos adicionados: {len(novos_validos)}")
    print(f"Total de personagens na base: {len(dados)}")


def carregar_nomes_existentes(html_path):
    """Lê o o_adivinho.html e retorna o conjunto de nomes já cadastrados."""
    caminho = Path(html_path)
    if not caminho.exists():
        return set()
    conteudo = caminho.read_text(encoding="utf-8")
    marcador = "const PERSONAGENS = "
    if marcador not in conteudo:
        return set()
    idx = conteudo.index(marcador)
    inicio_chave = conteudo.index("{", idx)
    texto_obj = extrair_balanceado(conteudo, inicio_chave)
    return set(json.loads(texto_obj).keys())


def main():
    parser = argparse.ArgumentParser(
        description="Gera atributos para O Adivinho usando um modelo de IA local (Ollama) + busca na web."
    )
    parser.add_argument("--nomes", help="Arquivo .txt com um nome por linha (opcional se usar --categorias)")
    parser.add_argument("--categorias",
                         help="Categorias da Wikipédia separadas por vírgula, ex: "
                              "'Futebolistas do Brasil,Atores do Brasil' — descobre os nomes automaticamente")
    parser.add_argument("--idioma-wiki", default="pt", help="Idioma da Wikipédia a consultar (pt, en, es...)")
    parser.add_argument("--limite-por-categoria", type=int, default=50,
                         help="Máximo de nomes a puxar de cada categoria")
    parser.add_argument("--html", required=True, help="Arquivo o_adivinho.html original")
    parser.add_argument("--saida", default="o_adivinho_atualizado.html", help="Nome do arquivo .html de saída")
    parser.add_argument("--modelo", default="llama3.1", help="Nome do modelo no Ollama (ex: llama3.1, mistral, qwen2.5)")
    parser.add_argument("--pausa", type=float, default=2.0, help="Segundos de espera entre buscas na web")
    parser.add_argument("--checkpoint", default="checkpoint_personagens.json",
                         help="Arquivo de progresso (permite retomar se o processo for interrompido)")
    parser.add_argument("--somente-gerar", action="store_true",
                         help="Só gera o JSON de atributos, sem mesclar no HTML (útil pra revisar antes)")
    args = parser.parse_args()

    if not args.nomes and not args.categorias:
        parser.error("informe --nomes (arquivo .txt) ou --categorias (descoberta automática via Wikipédia)")

    nomes = []
    vistos = set()

    if args.nomes:
        do_arquivo = [l.strip() for l in Path(args.nomes).read_text(encoding="utf-8").splitlines() if l.strip()]
        print(f"{len(do_arquivo)} nome(s) carregado(s) de {args.nomes}")
        for n in do_arquivo:
            if n not in vistos:
                vistos.add(n)
                nomes.append(n)

    if args.categorias:
        categorias = args.categorias.split(",")
        descobertos = descobrir_nomes(categorias, args.idioma_wiki, args.limite_por_categoria)
        novos = [n for n in descobertos if n not in vistos]
        print(f"\nTotal descoberto nas categorias: {len(descobertos)} ({len(novos)} novo(s), sem contar repetidos)")
        for n in novos:
            vistos.add(n)
            nomes.append(n)

    existentes = carregar_nomes_existentes(args.html)
    if existentes:
        antes = len(nomes)
        nomes = [n for n in nomes if n not in existentes]
        pulados = antes - len(nomes)
        if pulados:
            print(f"{pulados} nome(s) já estavam na base do {args.html} — pulando pra não gastar tempo à toa.")

    print(f"\n{len(nomes)} nome(s) serão processados.\n")
    if not nomes:
        print("Nada a fazer — todos os nomes já estão na base ou nenhuma categoria retornou resultado.")
        return

    resultados = gerar_para_nomes(nomes, args.modelo, args.pausa, Path(args.checkpoint))

    if args.somente_gerar:
        print(f"\nAtributos gerados e salvos em {args.checkpoint}. Nenhum HTML foi tocado (--somente-gerar).")
        return

    mesclar_no_html(args.html, resultados, args.saida)


if __name__ == "__main__":
    main()
