# Relatório — Case: classificação de tópicos

> Esqueleto. Preencher depois da execução real. Itens marcados com [PREENCHER] dependem dos resultados.

## a) Como pensei
- **Problema real:** classificar certo importa menos que *saber quando não classificar*. A meta é 95% de acerto no publicado; o resto vai para o professor.
- **Hipóteses:** (1) um LLM sozinho acerta "razoavelmente", mas é inconsistente nos casos limítrofes; (2) discordância entre amostras/modelos sinaliza erro; (3) o assunto de origem é pista útil, mas não confiável (é a fonte das "lixeiras"); (4) mostrar ao modelo só candidatos reduz alucinação e custo.
- **O que testar:** limiares de acordo/confiança; 1 vs 3 vs 5 amostras; 1 vs 2 provedores; candidatos 20/40/80. [PREENCHER com a tabela de `comparativos/historico.csv`]
- **O que descartei e por quê:** [PREENCHER — becos sem saída reais]

## b) Diagnóstico
[PREENCHER depois de olhar `discordancias.csv` e os erros da auditoria]. Pontos a verificar nos dados:
- Temas genéricos/introdutórios ("lixeiras"): quantos? Que fração das questões o modelo manda para eles?
- Temas com nomes sobrepostos ou subtemas que se confundem.
- Questões que cobrem mais de um tema (por isso o campo `extras`).
- Enunciados com HTML sujo, comando separado do enunciado, alternativas que só fazem sentido com o texto-base.
- Questões sobre lei alterada recentemente.

## c) Produção (50 mil questões/semana)
| Etapa | Técnica | Por quê |
|---|---|---|
| 1. Candidatos | Embeddings + busca vetorial | Barato, rápido, reduz 377 temas a ~40 |
| 2. Triagem barata | Classificador treinado (a partir dos rótulos aprovados pelo professor) | Resolve o grosso a custo quase zero |
| 3. Casos duvidosos | LLM com votação (este pipeline) | Só nas questões que o classificador não resolve |
| 4. Revisão humana | Fila do professor, ordenada por incerteza | Tempo escasso vai onde mais importa |
| 5. Reportes de alunos | Entram como rótulo e como alerta de tema "lixeira" | Fecham o ciclo |

- **Custo por questão:** [PREENCHER: tokens médios × preço, ×N amostras ×N provedores; ver `historico.csv`].
- **Qualidade contínua:** auditoria semanal de amostra aleatória das *publicadas* (intervalo de Wilson), taxa de reporte de alunos por tema, taxa de revisão que o professor contradiz, alerta de deriva (queda de acordo médio).
- **Fluxo:** importação → limpeza → pipeline → publicar/revisar/fora → professor corrige → correções viram dados de treino e de teste fixo (nunca misturados).

## d) Memo para o professor (1 página)
[PREENCHER]. Estrutura sugerida: (1) o que fiz, em 3 linhas, sem jargão; (2) o que encontrei: quais temas viraram "lixeira" e por quê; (3) o que recomendo mudar: temas a dividir, fundir ou renomear, com exemplos reais de questões; (4) o que preciso do senhor/da senhora: conferir ~100 questões da amostra e decidir os temas ambíguos (leva ~X horas); (5) o que **não** sei.

## Limitações e o que faria com mais tempo
- Busca de candidatos por palavras falha com vocabulário diferente; embeddings melhorariam.
- Acordo entre amostras do *mesmo* modelo mede consistência, não correção; o segundo provedor reduz esse risco.
- Mais questões auditadas para estreitar o intervalo.
