# Gerador Local de Personagens — O Adivinho

Este script roda **inteiramente na sua máquina**: busca um resumo de cada nome na web
(DuckDuckGo, sem precisar de chave de API) e manda esse resumo para um **modelo de IA
local** (via [Ollama](https://ollama.com)), que devolve os 76 atributos do personagem.
No final, ele já mescla tudo no seu `o_adivinho.html`.

## 1. Instalar o Ollama (o "modelo local")

O Ollama é um programa que baixa e roda modelos de linguagem (LLMs) direto no seu
computador, sem precisar de internet nem de chave de API depois de baixado.

- **Windows/Mac**: baixe o instalador em https://ollama.com/download e instale normalmente.
- **Linux**:
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```

Depois de instalar, baixe um modelo (a primeira vez demora, baixa alguns GB):

```bash
ollama pull llama3.1
```

Modelos menores/mais rápidos (rodam bem em notebooks sem placa de vídeo dedicada):
```bash
ollama pull llama3.2:3b
```
Modelos maiores/mais precisos (precisam de mais RAM/GPU):
```bash
ollama pull qwen2.5:14b
```

Teste se está funcionando:
```bash
ollama run llama3.1 "Olá, tudo bem?"
```
Se responder, está tudo certo. Pode fechar esse teste (Ctrl+D) — o Ollama fica
rodando em segundo plano como um servidor local automaticamente.

## 2. Instalar o Python e as dependências

Você precisa do Python 3.9 ou mais recente. Depois, na pasta onde estão os arquivos
deste gerador, rode:

```bash
pip install -r requirements.txt
```

Isso instala:
- `requests` — para conversar com o Ollama
- `duckduckgo-search` — para buscar informações na web sobre cada nome

## 3. Preparar a lista de nomes

Crie (ou edite) um arquivo `.txt` com um nome por linha. Já tem um exemplo pronto:
`nomes_exemplo.txt`.

## 4. Rodar o gerador

Você pode alimentar o script de duas formas — com uma lista manual, ou deixando
ele **descobrir os nomes sozinho** a partir de categorias da Wikipédia.

### Opção A — lista manual (como antes)

Coloque o seu `o_adivinho.html` na mesma pasta (ou passe o caminho completo) e rode:

```bash
python gerar_atributos_local.py --nomes nomes_exemplo.txt --html o_adivinho.html --saida o_adivinho_atualizado.html
```

### Opção B — descoberta automática por categoria (sem digitar nomes)

O script consulta a API pública da Wikipédia e puxa os nomes de dentro de uma
categoria automaticamente — você só passa o nome da categoria:

```bash
python gerar_atributos_local.py --categorias "Futebolistas do Brasil" --html o_adivinho.html --saida o_adivinho_atualizado.html
```

Dá pra combinar várias categorias de uma vez (separadas por vírgula):

```bash
python gerar_atributos_local.py --categorias "Atores do Brasil,Cantores do Brasil,Cientistas do Brasil" --html o_adivinho.html --saida o_adivinho_atualizado.html --limite-por-categoria 30
```

Como descobrir nomes de categorias: abra a página de qualquer pessoa na Wikipédia
em português, role até o rodapé — as categorias aparecem ali (ex: na página do
Neymar tem "Futebolistas do Brasil", "Futebolistas do Santos Futebol Clube" etc.).
Copie o nome da categoria exatamente como aparece lá (sem o prefixo "Categoria:").

Para categorias em outro idioma, use `--idioma-wiki en` (ou `es`, etc.) e o nome
da categoria em inglês, ex: `--categorias "American film actors" --idioma-wiki en`.

O script já pula automaticamente qualquer nome que já esteja na sua base do
`o_adivinho.html`, então pode rodar de novo com categorias maiores sem duplicar
ninguém nem gastar tempo reprocessando quem já existe.

Você pode combinar as duas opções ao mesmo tempo (`--nomes` e `--categorias`
juntos) — o script junta tudo numa lista só, sem repetir.

O script vai, para cada nome:
1. Buscar um resumo na web
2. Perguntar ao modelo local (Ollama) os 76 atributos
3. Salvar o progresso em `checkpoint_personagens.json` (assim, se cair a energia ou
   você cancelar no meio, é só rodar o mesmo comando de novo que ele continua de
   onde parou)

No final, gera o arquivo `o_adivinho_atualizado.html` já com os personagens novos
inseridos — sem duplicar quem já existia na base.

### Opções úteis

| Parâmetro | Para que serve | Padrão |
|---|---|---|
| `--categorias` | categorias da Wikipédia pra descobrir nomes automaticamente (separadas por vírgula) | — |
| `--idioma-wiki` | idioma da Wikipédia a consultar (`pt`, `en`, `es`...) | `pt` |
| `--limite-por-categoria` | quantos nomes puxar de cada categoria | `50` |
| `--modelo` | qual modelo do Ollama usar | `llama3.1` |
| `--pausa` | segundos de espera entre buscas na web (evita bloqueio) | `2.0` |
| `--checkpoint` | nome do arquivo de progresso | `checkpoint_personagens.json` |
| `--somente-gerar` | só gera o JSON de atributos, sem tocar no HTML (bom pra revisar antes) | desligado |

Exemplo revisando antes de aplicar:
```bash
python gerar_atributos_local.py --nomes meus_nomes.txt --html o_adivinho.html --somente-gerar
# revise o arquivo checkpoint_personagens.json manualmente...
python gerar_atributos_local.py --nomes meus_nomes.txt --html o_adivinho.html --saida o_adivinho_atualizado.html
# (na segunda vez ele reaproveita o checkpoint já gerado, sem chamar o modelo de novo)
```

## Limitações importantes

- **Nomes da Wikipédia podem ter formatação diferente** dos que já estão na sua
  base — por exemplo, a Wikipédia pode listar "Ronaldo (futebolista)" enquanto
  seu jogo já tem "Ronaldo Fenômeno". Como os textos não são idênticos, o
  script não reconhece que é a mesma pessoa e cadastra os dois. Vale dar uma
  olhada na lista antes de aplicar (`--somente-gerar`) pra evitar esse tipo de
  quase-duplicata.
- **Modelos locais menores erram mais** que modelos como o Claude ou GPT-4 — quanto
  menor o modelo (ex: `llama3.2:3b`), maior a chance de atributos errados,
  especialmente para pessoas/personagens menos conhecidos. Modelos maiores
  (`qwen2.5:14b`, `llama3.1:70b` se sua máquina aguentar) tendem a acertar mais.
- **A busca na web pode falhar ou vir vazia** às vezes (bloqueios temporários,
  nome muito genérico, etc.) — quando isso acontece, o modelo cai para o próprio
  conhecimento dele, que pode estar desatualizado.
- **Sempre revise** os resultados antes de usar em produção — use `--somente-gerar`
  e dê uma olhada no `checkpoint_personagens.json` se quiser conferir antes de
  aplicar no jogo.
- Fazer buscas em massa e muito rápido pode fazer o DuckDuckGo bloquear
  temporariamente seu IP — por isso o `--pausa` existe; se acontecer, espere
  alguns minutos e rode de novo (o checkpoint garante que não perde o progresso).
