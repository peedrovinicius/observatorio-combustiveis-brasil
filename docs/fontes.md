# Fontes de dados

## Fonte principal

**Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP)**

### Levantamento de Preços de Combustíveis

Página oficial:

https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas

Uso no projeto:

- referência para as publicações semanais;
- conferência da cobertura temporal;
- validação das séries publicadas pela ANP.

### Série histórica do levantamento de preços

https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos

Uso no projeto:

- série semanal de Brasil;
- regiões;
- estados;
- municípios em 2026.

Os arquivos são validados pelo conteúdo antes de serem aceitos como XLSX. Uma resposta HTML intermediária não é salva como planilha.

Para cada escopo da série histórica, uma nova planilha válida substitui os arquivos locais antigos daquele mesmo escopo. A limpeza ocorre somente após a validação do novo download.

### Série Histórica de Preços de Combustíveis e de GLP

https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis

Uso no projeto:

- observações de preço por estabelecimento;
- produto e unidade de medida;
- CNPJ e identificação do posto;
- bandeira;
- distribuição municipal de preços.

O downloader identifica CSV, ZIP e XLSX pelo conteúdo real do arquivo. Isso cobre respostas do portal com `application/octet-stream` e impede que páginas HTML sejam tratadas como dados.

Quando uma publicação já existe localmente, a nova versão é preparada em staging antes de qualquer alteração no dataset anterior. Para ZIP, todos os CSVs internos são extraídos e validados no staging. Nomes de CSV que colidiriam em sistemas sem diferenciação entre maiúsculas e minúsculas também são rejeitados.

Somente depois de toda a preparação ter sucesso, os artefatos antigos do mesmo dataset lógico são movidos para backup temporário e a nova versão é instalada. Se a instalação falhar, o processo remove qualquer artefato novo já instalado e restaura o backup anterior.

A substituição cobre mudanças entre CSV e ZIP, incluindo diretórios de extração. Arquivos de outros datasets são preservados.

### Cadastro de revendedores varejistas

https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/dados-cadastrais-dos-revendedores-varejistas-de-combustiveis-automotivos

Possível uso futuro:

- enriquecimento cadastral;
- validação complementar de estabelecimentos;
- atributos não presentes na série de preços.

Essa fonte não é necessária para executar o pipeline atual.

## Rastreabilidade

Todo arquivo aceito pelo pipeline mantém registro de:

- URL da página oficial;
- URL descoberta;
- URL final do arquivo;
- data e hora da coleta em UTC;
- nome do arquivo salvo;
- formato detectado pelo conteúdo;
- tipo de conteúdo HTTP informado;
- tamanho em bytes;
- hash SHA-256.

Manifestos:

```text
data/raw/history_manifest.json
data/raw/open_data/manifest.json
```

## Política de dados

Os arquivos brutos não são modificados.

Qualquer limpeza, conversão de tipos, padronização, deduplicação ou criação de colunas produz saídas em `data/processed/` e relatórios em `reports/`.

A camada por posto também registra exclusões e sobreposições em:

```text
reports/station_ingestion_audit_2026.json
```
