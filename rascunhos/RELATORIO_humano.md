<!-- RASCUNHO LOCAL — NÃO ENTREGAR sem autorização explícita do autor. Gerado pelo humanizador (inspirado em StealthHumanizer). -->

# Relatório — Case: Classificação de Tópicos

> Esqueleto. Preencher após a execução real. Itens marcados com [PREENCHER] dependem dos resultados.

## a) Como pensei
- **Problema real:** a precisão na classificação é menos relevante do que *saber quando não classificar*. O objetivo é alcançar 95% de acertos no material publicado; o restante será encaminhado ao professor.
- **Hipóteses:** (1) um LLM isoladamente acerta "razoavelmente", mas apresenta inconsistências em casos limítrofes; (2) a discordância entre amostras/modelos indica erro; (3) o assunto de origem é uma pista útil, mas não confiável (pode gerar "lixeiras"); (4) apresentar ao modelo apenas candidatos reduz alucinações e custos.
- **O que testar:** limiares de acordo/confiança; 1 vs 3 vs 5 amostras; 1 vs 2 provedores; candidatos em quantidades de 20/40/80. [PREENCHER com a tabela de `comparativos/historico.csv`]
- **O que descartei e por quê:** [PREENCHER — becos sem saída reais]

## b) Diagnóstico
[PREENCHER após análise de `discordancias.csv` e dos erros da auditoria]. Pontos a verificar nos dados:
- Temas genéricos/introdutórios ("lixeiras"): quantos existem? Qual é a fração das questões que o modelo classifica como tais?
- Temas com nomes sobrepostos ou subtemas que se confundem.
- Questões que abrangem mais de um tema (justificando o campo `extras`).
- Enunciados com HTML inadequado, comandos isolados do enunciado, alternativas que só fazem sentido em relação ao texto-base.
- Questões relacionadas a leis recentemente alteradas.

## c) Produção (50 mil questões/semana)
| Etapa | Técnica | Justificativa |
|---|---|---|
| 1. Candidatos | Embeddings + busca vetorial | Custo acessível, rápido, reduz 377 temas a aproximadamente 40 |
| 2. Triagem inicial | Classificador treinado (com base nos rótulos aprovados pelo professor) | Resolve a maior parte a um custo quase nulo |
| 3. Casos duvidosos | LLM com votação (este pipeline) | Apenas para questões que o classificador não consegue resolver |
| 4. Revisão humana | Fila do professor, organizada por incerteza | Tempo escasso é alocado onde há maior necessidade |
| 5. Relatos de alunos | São utilizados como rótulo e alerta para temas "lixeira" | Completa o ciclo de feedback |

- **Custo por questão:** [PREENCHER: tokens médios × preço, ×N amostras ×N provedores; consultar `historico.csv`].
- **Qualidade contínua:** auditoria semanal de uma amostra aleatória das *publicadas* (intervalo de Wilson), taxa de reporte de alunos por tema, taxa de revisão que o professor contradiz, alerta de deriva (queda no acordo médio).
- **Fluxo:** importação → limpeza → pipeline → publicação/revisão/exclusão → professor corrige → correções se tornam dados de treino e teste fixo (nunca misturados).

## d) Memo para o professor (1 página)
[PREENCHER]. Estrutura sugerida: (1) o que foi realizado, em 3 linhas, sem jargão; (2) o que foi encontrado: quais temas foram considerados "lixeira" e o motivo; (3) recomendações de mudanças: temas a dividir, fundir ou renomear, com exemplos reais de questões; (4) o que se espera do professor: revisar aproximadamente 100 questões da amostra e decidir sobre os temas ambíguos (estimativa de ~X horas); (5) o que **não** se sabe.

## Limitações e o que faria com mais tempo
- A busca de candidatos por palavras falha com vocabulário diferente; melhorias em embeddings seriam benéficas.
- O acordo entre amostras do *mesmo* modelo mede consistência, não correção; a inclusão de um segundo provedor minimiza esse risco.
- Mais questões auditadas para estreitar o intervalo de confiança.
