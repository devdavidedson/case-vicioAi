# Classificador de tópicos de questões de concurso

Este projeto lê questões de concurso e decide, para cada uma, uma de três coisas:

| Decisão | O que significa |
|---|---|
| **publicar** | A máquina tem certeza. A questão vai direto para o aluno, no tema escolhido. |
| **revisar** | A máquina tem dúvida. Vai para a fila do professor, já com uma sugestão. |
| **fora** | Nenhum tema da lista serve. |

**A ideia principal:** a máquina pergunta ao modelo de IA **mais de uma vez** para cada questão. Só publica quando as respostas **concordam entre si** e o modelo diz estar **confiante**. Se houver dúvida, vai para o professor. Isso troca um pouco de quantidade por muita segurança, o que importa quando a meta é acertar 95% do que for publicado.

---

## Você vai precisar de

1. Um computador com **Python 3.9 ou mais novo**. Para saber se já tem, abra o terminal (no Windows, o "Prompt de Comando") e digite `python --version`. Se não tiver, baixe em python.org e instale.
2. Uma **chave de API** do provedor de IA (a Jev, ou outro). É uma senha longa que você gera no site do provedor.
3. Os 3 arquivos do desafio: `questoes.jsonl`, `temas.csv` e `LEIA-ME.md`.

Não precisa instalar mais nada. O projeto usa apenas o que já vem com o Python.

---

## Passo a passo

### 1. Baixe o projeto
No GitHub, clique em **Code → Download ZIP** e descompacte. Abra o terminal dentro da pasta descompactada.

### 2. Teste sem gastar nada
```
python src/pipeline.py --demo
```
Isso roda com 3 questões de mentira e uma "IA de mentira". Se aparecer `FINAL ... publicar` no fim, está tudo instalado certo.

### 3. Coloque a sua chave
1. Copie o arquivo `.env.example` e renomeie a cópia para `.env`.
2. Abra o `.env` no Bloco de Notas e troque `cole_sua_chave_aqui` pela sua chave.
3. Salve.

> **Cuidado:** a chave é como a senha do seu banco. O arquivo `.env` **nunca** vai para o GitHub (o projeto já bloqueia isso). Nunca cole a chave em e-mail, chat ou documento. Se vazou, apague-a no site do provedor e crie outra.

### 4. Diga ao projeto qual modelo usar
Abra o `config.json` e, no bloco `"jev"`, preencha:
- `base_url`: o endereço da API (está na documentação do provedor, normalmente termina em `/v1`)
- `modelo`: o nome do modelo
- `custo_entrada_por_milhao` e `custo_saida_por_milhao`: os preços por 1 milhão de "tokens" (para o projeto calcular quanto gastou)

### 5. Coloque os arquivos do desafio
Copie `questoes.jsonl` e `temas.csv` para a pasta **`dados/`**.

Se o desafio usar nomes de colunas diferentes dos que o projeto espera, o programa avisa. Corrija em `config.json`, na parte `campos_questao` e `temas`. É só trocar o nome entre aspas pelo nome que está no arquivo.

### 6. Faça um teste pequeno e barato (10 questões)
```
python src/pipeline.py --limite 10 --execucao teste1
```

### 7. Rode tudo
```
python src/pipeline.py --execucao final
```
O resultado fica em `runs/final/publicacao.csv`. Se a internet cair ou você fechar a janela, rode **o mesmo comando** de novo: ele continua de onde parou e **não paga duas vezes** pelo que já foi respondido.

---

## Usar mais de uma IA e comparar

1. No `config.json`, o segundo provedor já está de exemplo. Preencha os dados dele e troque `"ativo": false` para `"ativo": true`.
2. Coloque a chave dele no `.env`.
3. Rode normalmente. O projeto consulta os dois e só publica quando os dois concordam.
4. Para ver as diferenças:
```
python src/comparar.py final
```
Isso cria `runs/final/comparativo.md` (resumo) e `runs/final/discordancias.csv` (as questões em que as IAs discordaram, ótimas para o professor olhar).

Para rodar **só um** provedor: `python src/pipeline.py --provedores jev`

O arquivo `comparativos/historico.csv` guarda **todas** as execuções (quantas publicadas, quanto custou, quanto tempo levou, quantos erros), para você comparar modelos ao longo do tempo.

---

## Como saber se acertou 95% (sem gabarito)

O desafio não dá as respostas certas, então medimos assim:
```
python src/auditoria.py sortear final 100
```
Isso cria `runs/final/auditoria.csv` com 100 questões publicadas, sorteadas. Abra no Excel, confira se o tema está certo e escreva **S** (certo) ou **N** (errado) na coluna `correto`. Depois:
```
python src/auditoria.py calcular final
```
Isso gera `runs/final/previsao.txt` com a precisão estimada e a margem de erro. Se a margem for larga demais, confira mais questões. Se a precisão ficou abaixo de 95%, deixe o projeto mais rígido (veja abaixo) e rode de novo.

---

## Deixar mais rígido ou mais solto

No `config.json`, em `classificacao`:
- `limiar_acordo` (0 a 1): quanto as respostas precisam concordar. **Suba** para publicar menos e errar menos.
- `limiar_confianca` (0 a 1): quão confiante o modelo precisa estar. Mesma lógica.
- `amostras_por_provedor`: quantas vezes perguntar. Mais vezes = mais seguro e mais caro.

---

## Proteções embutidas

Tudo configurável em `protecoes` no `config.json`:

| Proteção | O que faz |
|---|---|
| Sem loop infinito | Todo laço tem limite. Não existe "tentar para sempre". |
| `max_tentativas_por_chamada` | Se uma chamada falha, tenta de novo poucas vezes, esperando cada vez mais. |
| `max_erros_seguidos` | Se o provedor errar várias vezes seguidas, ele é desligado para não gastar à toa. |
| `max_chamadas_total`, `max_custo_usd`, `max_minutos_total` | Teto de chamadas, de dinheiro e de tempo. Ao atingir, para e salva o que já fez. |
| Retomada | Respostas já obtidas ficam salvas e não são cobradas de novo. |
| Log de erros | Todo erro vai para `runs/<execucao>/<provedor>/erros.log`, com data e hora. |

---

## O que aparece em cada pasta

```
runs/final/
├── publicacao.csv         ← resultado final (todos os provedores juntos)
├── comparativo.md         ← resumo da comparação
├── discordancias.csv      ← onde as IAs discordaram
├── auditoria.csv          ← amostra para você conferir
├── previsao.txt           ← precisão e cobertura estimadas
└── jev/
    ├── publicacao.csv     ← resultado só deste provedor
    ├── respostas.jsonl    ← todas as respostas brutas da IA
    └── erros.log          ← erros deste provedor
comparativos/historico.csv ← histórico de todas as execuções
```

## Problemas comuns

| Mensagem | O que fazer |
|---|---|
| `chave JEV_API_KEY nao encontrada` | O arquivo `.env` não existe, está com outro nome, ou a linha está errada. |
| `preencha base_url e modelo` | Falta preencher o `config.json` (passo 4). |
| `Arquivo nao encontrado: dados/questoes.jsonl` | Copie os arquivos do desafio para a pasta `dados/` (passo 5). |
| `HTTP 401` no `erros.log` | Chave errada ou expirada. |
| `HTTP 429` no `erros.log` | Muitas chamadas rápidas. O projeto espera e tenta de novo. Se persistir, tente mais tarde. |
| `abortado por erros seguidos` | Leia o `erros.log` para ver o motivo. Corrija e rode o mesmo comando para retomar. |

---

## Para quem é técnico

- **Pipeline:** carga e limpeza de HTML → sugestão de 40 temas candidatos por busca TF-IDF (evita que o modelo veja os 377 temas e reduz custo) → N amostras por provedor (a primeira com temperatura 0, as demais com 0,7) → votação → regra de decisão em `decidir()` (acordo ≥ limiar e confiança média ≥ limiar). Falhas de chamada contam como voto ausente e **reduzem o acordo**.
- **Decisões feitas à mão:** nenhuma no código. A auditoria (`auditoria.py`) exige conferência humana de uma amostra; registre no relatório quem conferiu.
- **Modelos, custo e tempo:** ficam em `comparativos/historico.csv`.
- **Relatório do case:** `docs/RELATORIO.md`.
- Para trocar a busca por embeddings, substitua a classe `Indice` em `src/pipeline.py`.
