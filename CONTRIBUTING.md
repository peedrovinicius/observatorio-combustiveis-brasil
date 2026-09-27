# Contribuindo

Contribuições são bem-vindas quando preservam a rastreabilidade dos dados, a metodologia documentada e a separação entre as camadas agregada e por posto.

## Antes de começar

1. Procure uma issue aberta relacionada ao tema.
2. Se a mudança não estiver registrada, abra uma issue descrevendo problema, motivação e escopo.
3. Informe se a proposta afeta fonte, granularidade, regra de qualidade, KPI, SQL, DAX ou visualização.

## Fluxo recomendado

1. Crie uma branch curta e específica a partir de `main`.
2. Faça uma alteração por tema.
3. Inclua ou atualize testes quando houver mudança de comportamento.
4. Execute as validações locais aplicáveis.
5. Abra um Pull Request descrevendo contexto, impacto e validação.

Validação principal:

```bash
python -m ruff check .
python -m pytest -q --cov=src --cov-report=term-missing
```

Para mudanças que afetem PostgreSQL:

```bash
docker compose up -d postgres
python -m pytest -q tests/integration/test_postgres_live.py
```

## Regras de qualidade

- não alterar resultados publicados sem evidência e validação;
- preservar a separação entre dados agregados e dados por posto;
- não misturar unidades de medida em cálculos;
- não versionar dados brutos ou processados;
- manter proveniência, manifests e auditorias quando aplicáveis;
- documentar mudanças em fontes, KPIs, modelo de dados, SQL ou DAX;
- manter commits e Pull Requests com escopo claro.

## Pull Requests

Inclua no PR:

- problema resolvido;
- arquivos ou componentes afetados;
- testes ou validações executados;
- impacto analítico ou metodológico, quando houver;
- evidência visual apenas quando a mudança for de relatório ou interface.

Mudanças pequenas e bem delimitadas são preferíveis a PRs muito amplos.
