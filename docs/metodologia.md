# Metodologia

## 1. Aquisição

A série principal é obtida diretamente da página oficial da ANP para o Levantamento de Preços.

Para 2026, o pipeline histórico localiza dinamicamente os arquivos semanais modernos publicados para:

- Brasil;
- regiões;
- estados;
- municípios de 2026.

Os links não são fixados manualmente no código. A descoberta é feita a partir da estrutura atual da página oficial, reduzindo a dependência de nomes de arquivo.

## 2. Rastreabilidade

Cada download registra:

- URL da página de origem;
- URL descoberta;
- URL final após redirecionamentos;
- data e hora da coleta em UTC;
- nome local;
- tipo de conteúdo;
- tamanho em bytes;
- hash SHA-256.

O manifesto histórico é salvo em `data/raw/history_manifest.json`.

## 3. Camada raw

A camada `data/raw/` contém os arquivos exatamente como recebidos da ANP.

Arquivos brutos nunca são alterados.

## 4. Inspeção

Antes do tratamento são registrados:

- formato;
- abas da planilha;
- número de linhas e colunas;
- nomes originais das colunas;
- quantidade de valores ausentes.

O relatório local é salvo em `data/raw/inspection.json`.

## 5. Transformação

O pipeline:

1. detecta automaticamente a linha real do cabeçalho;
2. remove colunas sem nome;
3. padroniza nomes de campos;
4. converte datas;
5. converte preços com suporte a vírgula decimal brasileira e ponto decimal;
6. preserva campos adicionais publicados pela ANP;
7. adiciona identificação do arquivo e da planilha de origem.

Cada tabela reconhecida gera um CSV em `data/processed/`.

Antes de substituir arquivos processados de um escopo histórico, o pipeline lê a nova planilha e confirma que existe pelo menos uma aba reconhecível. Somente depois dessa validação são removidos CSVs antigos do mesmo escopo, como Brasil, regiões, estados ou municípios.

Essa limpeza por escopo impede que uma mudança no nome remoto do XLSX deixe duas versões transformadas válidas sendo consolidadas ao mesmo tempo. Arquivos processados de outros escopos e produtos derivados do pipeline são preservados.

## 6. Consolidação de 2026

A consolidação seleciona tabelas agregadas com preço médio de revenda e:

- registra quantas linhas foram lidas por arquivo;
- identifica arquivos que não pertencem ao schema agregado;
- contabiliza datas iniciais inválidas;
- contabiliza registros fora de 2026;
- filtra registros elegíveis de 2026;
- identifica o nível geográfico;
- adiciona ano, mês e semana ISO;
- alinha schemas;
- contabiliza e remove duplicidades pela chave analítica disponível;
- gera `data/processed/precos_semanais_2026.csv`;
- grava `reports/aggregate_ingestion_audit_2026.json`.

Registros fora de 2026 são uma exclusão esperada para o recorte anual. Datas iniciais inválidas deixam a auditoria com status `review`, preservando visibilidade sobre linhas que não chegaram à base final.

## 7. Qualidade

A validação verifica:

- presença de colunas obrigatórias;
- preços ausentes ou inválidos;
- preços não positivos;
- duplicidades pela chave de negócio;
- preço mínimo maior que preço máximo.

A qualidade da base final é classificada como:

- `passed`: nenhuma inconsistência bloqueante foi encontrada;
- `failed`: existe pelo menos uma inconsistência bloqueante.

O status `review` é reservado às auditorias de ingestão, nas quais uma ocorrência pode exigir inspeção sem necessariamente alterar a integridade da base final.

Nenhum outlier é removido automaticamente.

## 8. Agregação

A metodologia oficial deve ser respeitada. A média municipal pode ser calculada por média aritmética simples, enquanto os níveis estadual, regional e nacional publicados pela ANP possuem metodologia própria de ponderação.

Por isso, o projeto preserva os agregados oficiais e não trata uma média simples das médias municipais como equivalente ao indicador nacional oficial.

## 9. Reprodutibilidade

A execução completa pode ser iniciada por:

```bash
python -m src.pipeline
```

Resultados analíticos não devem ser digitados manualmente. Métricas e visuais devem ser derivados das camadas processadas pelo pipeline.
