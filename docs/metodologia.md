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

Antes de substituir arquivos processados, o pipeline lê todas as planilhas históricas e confirma que cada uma possui pelo menos uma aba reconhecível. Os CSVs novos são produzidos em staging antes de qualquer alteração em `data/processed/`.

Brasil, regiões, estados e municípios são então substituídos como um único lote. Os CSVs históricos anteriores ficam em backup temporário até a instalação terminar. Em caso de falha, o lote anterior completo é restaurado.

Essa estratégia impede mistura entre transformações de execuções diferentes e também evita que uma mudança no nome remoto do XLSX deixe versões antigas sendo consolidadas junto com as novas.

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
- prepara `data/processed/precos_semanais_2026.csv`;
- prepara `reports/aggregate_ingestion_audit_2026.json`;
- publica base consolidada e auditoria juntas, com rollback do par anterior se a instalação falhar.

Registros fora de 2026 são uma exclusão esperada para o recorte anual. Datas iniciais inválidas deixam a auditoria com status `review`, preservando visibilidade sobre linhas que não chegaram à base final.

## 7. Qualidade

A validação verifica:

- presença de colunas obrigatórias;
- preços ausentes ou inválidos;
- preços não positivos;
- duplicidades pela chave de negócio;
- identidade geográfica mínima compatível com o nível informado;
- preço mínimo maior que preço máximo;
- preços mínimo e máximo não positivos, quando publicados;
- média fora do intervalo mínimo/máximo;
- desvio padrão ou coeficiente de variação negativos;
- quantidade de postos inválida, fracionária ou negativa.

Para identidade geográfica, a validação exige:

- nível `regiao`: campo `regiao` preenchido;
- nível `estado`: pelo menos `uf` ou `estado` preenchido;
- nível `municipio`: `municipio` preenchido e pelo menos `uf` ou `estado` preenchido;
- nível `brasil`: nenhum identificador geográfico adicional obrigatório.

A regra exige somente o mínimo necessário para identificar a localidade e não pressupõe que todos os campos geográficos estejam presentes em todos os níveis.

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


## 10. Atomicidade da aquisição por posto

Os dados abertos por posto são baixados e validados integralmente antes de qualquer substituição em `data/raw/open_data/`.

A publicação local trata todos os datasets descobertos na execução e o respectivo `manifest.json` como um único bundle. Uma falha de download, validação ou instalação preserva integralmente o snapshot anterior.

A descoberta também valida a cobertura mínima das famílias de 2026 e rejeita identidades lógicas duplicadas, evitando aceitar silenciosamente uma página oficial parcialmente alterada.


## 11. Verificação ativa da proveniência

Os hashes registrados na aquisição são verificados novamente antes do uso da camada raw.

Para a série histórica, cada arquivo XLSX precisa corresponder ao tamanho e SHA-256 do `history_manifest.json`, e não pode existir arquivo histórico adicional fora do manifesto.

Para os dados por posto, a validação cobre tanto o CSV ou ZIP original quanto cada CSV extraído. A consolidação é bloqueada se houver arquivo ausente, alterado, adicional ou com caminho incompatível com o manifesto.

Essa barreira impede que uma alteração local, corrupção de arquivo ou resíduo de execução anterior seja propagado silenciosamente para `data/processed/`.
