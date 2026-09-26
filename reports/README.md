# Relatórios de qualidade

Esta pasta recebe saídas de validação geradas pelo pipeline.

O arquivo `quality_2026.json` é produzido automaticamente por:

```bash
python -m src.quality
```

Relatórios gerados a partir dos dados não são versionados. As regras que os produzem permanecem em `src/quality.py`.
