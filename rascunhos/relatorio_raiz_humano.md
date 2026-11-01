<!-- RASCUNHO LOCAL — NÃO ENTREGAR sem autorização explícita do autor. Gerado pelo humanizador (inspirado em StealthHumanizer). -->

# Relatório — Case: Classificação de Tópicos

> Esqueleto. Preencher após a execução real. Itens marcados com [PREENCHER] dependem dos resultados.

## a) Como pensei
- **Problema real:** A classificação correta é menos importante do que *saber quando não classificar*. O objetivo é 95% de acerto nas publicações; o restante será encaminhado ao professor.
- **Hipóteses:** (1) um LLM isoladamente atinge resultados "razoáveis", mas apresenta inconsistências em casos limítrofes; (2) a discordância entre amostras/modelos indica erro; (3) o assunto de origem é uma pista útil, mas não confiável (é a fonte das "lixeiras"); (4) apresentar ao modelo apenas candidatos reduz a alucinação e os custos.
- **O que testar:** limiares de acordo/confiança; comparação entre 1, 3 e 5 amostras; 1 ou 2 provedores; candidatos em quantidades de 20, 40 e 80. [PREENCHER com a tabela de `comparativos/historico.csv`]
- **O que descartei e por quê:** [PREENCHER — becos sem saída reais]

## b) Diagnóstico
[PREENCHER após análise do `discordancias.csv` e dos erros da auditoria]. Pontos a serem verificados nos dados:
- Temas genéricos/introdutórios ("lixeiras"): quantos? Qual a fração das questões enviadas para eles pelo modelo?
- Temas com nomes sobrepostos ou subtemas que se confundem.
- Questões que abrangem mais de um tema (por isso o campo `extras`).
- Enunciados com HTML desorganizado, comandos separados do enunciado, alternativas que fazem sentido apenas com o texto-base.
- Questões sobre leis que foram alteradas recentemente.

## c) Produção (50 mil questões/semana)
| Etapa | Técnica | Justificativa |
|---|---|---|
| 1. Candidatos | Embeddings + busca vetorial | Custo acessível, rápido e reduz 377 temas a aproximadamente 40 |
| 2. Triagem simples | Classificador treinado (baseado nos rótulos aprovados pelo professor) | Resolve a maior parte com custo quase nulo |
| 3. Casos duvidosos | LLM com votação (este pipeline) | Aplicado apenas nas questões que o classificador não resolve |
| 4. Revisão humana | Fila do professor, organizada por incerteza | O tempo escasso é direcionado para onde mais importa |
| 5. Relatos de alunos | Entram como rótulo e sinalização de tema "lixeira" | Fecham o ciclo |

- **Custo por questão:** [PREENCHER: tokens médios × preço, ×N amostras ×N provedores; ver `historico.csv`].
- **Qualidade contínua:** auditoria semanal de amostra aleatória das *publicadas* (intervalo de Wilson), taxa de reporte de alunos por tema, taxa de revisão que o professor contradiz e alerta de deriva (queda de acordo médio).
- **Fluxo:** importação → limpeza → pipeline → publicação/revisão/exclusão → correção pelo professor → correções se tornam dados de treino e teste fixos (nunca misturados).

## d) Memo para o professor (1 página)
[PREENCHER]. Estrutura sugerida: (1) o que foi feito, em 3 linhas, sem jargão; (2) o que foi encontrado: quais temas se tornaram "lixeira" e por quê; (3) recomendações de mudanças: temas a dividir, fundir ou renomear, com exemplos reais de questões; (4) o que é necessário do senhor/da senhora: revisar cerca de 100 questões da amostra e decidir sobre os temas ambíguos (leva aproximadamente ~X horas); (5) o que **não** é sabido.

## Limitações e o que faria com mais tempo
- A busca de candidatos por palavras apresenta falhas com vocabulário diferente; melhorias em embeddings seriam benéficas.
- O acordo entre amostras do *mesmo* modelo mede a consistência, não a correção; a inclusão de um segundo provedor minimiza esse risco.
- Mais questões auditadas para estreitar o intervalo.
