# Pacote offline — Case Vicio IA

Para o recrutador / time técnico analisar a classificação **sem internet e sem LLM**.

## Como usar o executável

1. Abra a pasta `dist/CaseVicio_Offline_Recrutador/`
2. Execute `CaseVicioOffline.exe` (ou `ABRIR_TESTE_OFFLINE.bat`)
3. Leia o resumo no terminal
4. Abra `saida_offline/`

## O que está embutido

| Item | Função |
|------|--------|
| `dados/` | 659 questões, 377 temas, folha-verdade |
| `artifacts/embeddings/` | Vetores já gerados (cache) |
| `CaseVicioOffline.exe` | Roda classificação local |

**Zero** chamada a OpenAI/Jev/ChatGPT nesta execução.

## Como gerar de novo (desenvolvedor)

```bash
python scripts/build_offline_exe.py
```

## Relação com o repo

- O pipeline normal (`python -m src.v2.pipeline_v2`) continua igual.
- Este executável é um **extra** para demonstração offline.
