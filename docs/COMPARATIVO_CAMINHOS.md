# Comparativo de 4 caminhos — Case Vicio IA

Gerado em: 2026-11-01  
Experimento local (a versão standby no repositório permanece a V0).

| Caminho | Ideia | Publicar | Prec. folha | Prec. holdout | Cob. fora da folha |
|---------|--------|----------|-------------|---------------|--------------------|
| **V0 standby** | Gate embedding + holdout (atual) | 65 | 93,3% (14/15)* | 100% (6/6) | 8,9% |
| **V1 cobertura** | Mesmo cérebro, limiar só p/ maximizar ≥95% | 65 | 93,3% (14/15)* | 100% (6/6) | 8,9% |
| **V2 lexical+leis** | TF-IDF + leis + kNN | 75 | 57% (8/14) | 75% (3/4) | 10,9% |
| **V3 classificador** | Logística treinada (LOO) | 37 | 91% (10/11) | 100% (5/5) | 4,7% |

\*O caso a menos na V0/V1 é uma publicação de questão marcada como **fora** na folha-verdade.

## Detalhes

### V0_standby — Versão atual em standby
- Publicar/Revisar/Fora: **65 / 594 / 0**
- Limiares: `sim >= 0.65`, `margem >= 0.04`
- Gate embedding + endurecimento holdout

### V1_cobertura — Cobertura máxima sob 95%
- Publicar/Revisar/Fora: **65 / 594 / 0**
- Mesmo cérebro do standby; o melhor limiar sob ≥95% na folha coincidiu com o da V0

### V2_lexical_leis — TF-IDF + leis + kNN
- Publicar/Revisar/Fora: **75 / 584 / 0**
- Publicou mais porque a margem exigida ficou ~0 (trava mais frouxa), não porque acertou mais

### V3_classificador — Logística treinada (LOO)
- Publicar/Revisar/Fora: **37 / 622 / 0**
- Mais conservador; holdout limpo, porém menor cobertura

## Recomendação

**Seguir com V0_standby** como base.

Ranking sugerido: `V0_standby` > `V1_cobertura` > `V3_classificador` > `V2_lexical_leis`

- Meta do case (≥95% nas publicadas): priorize precisão estável; V0/V1 são as mais alinhadas.
- Volume sem qualidade (V2) prejudica a avaliação da vaga.
